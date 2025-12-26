#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dayton Audio Receiver Device Class

Manages serial communication with a Dayton Audio zone receiver (DAX66).
This class handles serial port communication, command queuing, response parsing,
and state updates for the main receiver device.

Protocol reference: The DAX66 uses a serial protocol where commands are sent
as ASCII strings and responses are received in a fixed format.

Command format: <XXYYZZ where XX=receiver+zone, YY=command, ZZ=value
Query format: ?XY where X=receiver number, Y=zone number (0 for all)
Response format: #>XYCCZZZZZZZZZZZZ where fields represent various status values
"""

# region Python Imports
import math
import re
import serial
import threading
import time
from dataclasses import dataclass
from enum import Enum
from queue import Queue, Empty
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import indigo

if TYPE_CHECKING:
    from plugin import Plugin
    from dayton_zone import DaytonZone
# endregion


class CommandType(Enum):
    """Types of commands that can be queued."""
    WRITE = "write"
    POLL_ALL = "poll_all"
    POLL_ZONE = "poll_zone"


@dataclass
class Command:
    """A command to be executed on the receiver."""
    command_type: CommandType
    payload: str = ""
    zone_number: int = 0


class DaytonReceiver:
    """
    Manages communication with a Dayton Audio zone receiver.
    
    Features:
    - Serial port communication at 9600 baud
    - Threaded command processing via queue
    - Status polling for all zones
    - Zone state tracking and updates
    
    The receiver protocol uses zone addressing where:
    - Zone number format: XY where X=receiver (1-3), Y=zone (1-6)
    - Zone 10 means "all zones on receiver 1"
    - Physical zone numbers 1-6 are on receiver 1, 7-12 on receiver 2, 13-18 on receiver 3
    """
    
    # Serial port configuration
    BAUD_RATE = 9600
    BYTE_SIZE = serial.EIGHTBITS
    PARITY = serial.PARITY_NONE
    STOP_BITS = serial.STOPBITS_ONE
    READ_TIMEOUT = 0.5
    WRITE_TIMEOUT = 1.0
    
    # Command timing
    COMMAND_PAUSE = 0.1

    def __init__(self, plugin: 'Plugin', device: indigo.Device):
        """
        Initialize the Dayton receiver manager.
        
        Args:
            plugin: Reference to the main plugin instance
            device: The Indigo device this manager controls
        """
        self.host_plugin = plugin
        self.device = device
        self.logger = plugin.logger
        
        # Serial port configuration
        self.serial_port_name = device.pluginProps.get('serialPort', '')
        self.connected_slave_units = int(device.pluginProps.get('connectedSlaveUnits', '0'))
        
        # Serial connection
        self.serial_conn: Optional[serial.Serial] = None
        
        # Threading infrastructure
        self.queue: Queue = Queue()
        self.thread: Optional[threading.Thread] = None
        self._stop_thread = False
        self._lock = threading.Lock()
        
        # Zone tracking - maps zone number (string) to DaytonZone instance
        self.registered_zones: Dict[str, 'DaytonZone'] = {}
        
        # Status tracking
        self.last_poll_time: float = 0
        self.is_connected: bool = False
        
        # Response parsing regex
        # Response format: #>XYCCZZZZZZZZZZZZ
        # X=receiver, Y=zone, CC=control status, then pairs for power, mute, DT, volume, treble, bass, balance, source
        self.response_pattern = re.compile(
            r'^\s*#>(?P<RecvNum>\d{1})(?P<ZoneNum>\d{1})(?P<ControlStatus>\d{2})'
            r'(?P<Power>\d{2})(?P<Mute>\d{2})(?P<DT>\d{2})(?P<Volume>\d{2})'
            r'(?P<Treble>\d{2})(?P<Bass>\d{2})(?P<Balance>\d{2})(?P<Source>\d{2})\d{2}\s*$',
            re.MULTILINE
        )
        
        self.logger.debug(f"DaytonReceiver initialized for {device.name}")

    # ========================================================================
    # region Lifecycle Methods
    # ========================================================================
    def start(self) -> None:
        """Start the device communication thread and open serial port."""
        self._stop_thread = False
        
        # Open serial connection
        if not self._open_serial():
            self.device.updateStateOnServer('connectionState', value='Error')
            self.device.updateStateOnServer('isConnected', value=False)
            return
        
        # Start processing thread
        self.thread = threading.Thread(
            target=self._process_queue,
            name=f"Dayton-{self.device.id}",
            daemon=True
        )
        self.thread.start()
        
        self.logger.debug(f"Receiver thread started for {self.device.name}")
        
        # Queue initial poll
        self.poll_all_zones()

    def stop(self) -> None:
        """Stop the device communication thread and close serial port."""
        self._stop_thread = True
        
        # Add a None command to wake up the thread
        self.queue.put(None)
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        # Close serial connection
        self._close_serial()
        
        self.logger.debug(f"Receiver thread stopped for {self.device.name}")

    def _open_serial(self) -> bool:
        """
        Open the serial port connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port_name,
                baudrate=self.BAUD_RATE,
                bytesize=self.BYTE_SIZE,
                parity=self.PARITY,
                stopbits=self.STOP_BITS,
                timeout=self.READ_TIMEOUT,
                write_timeout=self.WRITE_TIMEOUT
            )
            
            self.is_connected = True
            self.device.updateStateOnServer('connectionState', value='Connected')
            self.device.updateStateOnServer('isConnected', value=True)
            self.logger.info(f"Serial port {self.serial_port_name} opened for {self.device.name}")
            return True
            
        except serial.SerialException as e:
            self.logger.error(f"Failed to open serial port {self.serial_port_name}: {e}")
            self.is_connected = False
            return False

    def _close_serial(self) -> None:
        """Close the serial port connection."""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                self.logger.debug(f"Serial port {self.serial_port_name} closed")
            except Exception as e:
                self.logger.warning(f"Error closing serial port: {e}")
        
        self.serial_conn = None
        self.is_connected = False
        self.device.updateStateOnServer('isConnected', value=False)

    def _process_queue(self) -> None:
        """Main thread loop - processes commands from queue."""
        while not self._stop_thread:
            try:
                command = self.queue.get(timeout=0.5)
                
                if command is None:
                    continue
                
                self._execute_command(command)
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing queue for {self.device.name}: {e}")

    def _execute_command(self, command: Command) -> None:
        """
        Execute a command from the queue.
        
        Args:
            command: The command to execute
        """
        try:
            if command.command_type == CommandType.WRITE:
                self._do_write(command.payload)
                
            elif command.command_type == CommandType.POLL_ALL:
                self._do_poll_all()
                
            elif command.command_type == CommandType.POLL_ZONE:
                self._do_poll_zone(command.zone_number)
                
        except Exception as e:
            self.logger.error(f"Error executing {command.command_type}: {e}")

    # endregion
    # ========================================================================
    
    # ========================================================================
    # region Zone Registration
    # ========================================================================
    def register_zone(self, dev: indigo.Device, zone: 'DaytonZone') -> None:
        """
        Register a zone device with this receiver.
        
        Args:
            dev: The Indigo zone device
            zone: The DaytonZone instance
        """
        zone_number = dev.pluginProps.get('zoneNumber', '0')
        self.registered_zones[zone_number] = zone
        self.logger.debug(f"Registered zone {zone_number} ({dev.name})")

    def unregister_zone(self, dev: indigo.Device) -> None:
        """
        Unregister a zone device from this receiver.
        
        Args:
            dev: The Indigo zone device
        """
        zone_number = dev.pluginProps.get('zoneNumber', '0')
        if zone_number in self.registered_zones:
            del self.registered_zones[zone_number]
            self.logger.debug(f"Unregistered zone {zone_number} ({dev.name})")

    # endregion
    # ========================================================================
    
    # ========================================================================
    # region Public Command Methods
    # ========================================================================
    def send_command(self, command: str) -> None:
        """
        Queue a raw command to send to the receiver.
        
        Args:
            command: The raw command string
        """
        self.queue.put(Command(CommandType.WRITE, payload=command))
        self.logger.debug(f"Queued command: {command}")

    def poll_all_zones(self) -> None:
        """Queue a poll command for all zones."""
        self.queue.put(Command(CommandType.POLL_ALL))
        self.logger.debug("Queued poll for all zones")

    def poll_zone(self, zone_number: int) -> None:
        """
        Queue a poll command for a specific zone.
        
        Args:
            zone_number: The zone number (1-18)
        """
        self.queue.put(Command(CommandType.POLL_ZONE, zone_number=zone_number))

    # Zone Control Methods
    def set_zone_power(self, zone_number: int, power_on: bool) -> None:
        """Set power state for a specific zone."""
        addr = self._zone_to_address(zone_number)
        power_val = "01" if power_on else "00"
        self.send_command(f"<{addr}PR{power_val}")
        self.poll_zone(zone_number)

    def set_zone_volume(self, zone_number: int, volume: int) -> None:
        """Set volume for a specific zone (0-38)."""
        addr = self._zone_to_address(zone_number)
        volume = max(0, min(38, volume))
        self.send_command(f"<{addr}VO{volume:02d}")
        self.poll_zone(zone_number)

    def set_zone_source(self, zone_number: int, source: int) -> None:
        """Set source for a specific zone (1-6)."""
        addr = self._zone_to_address(zone_number)
        source = max(1, min(6, source))
        self.send_command(f"<{addr}CH0{source}")
        self.poll_zone(zone_number)

    def set_zone_mute(self, zone_number: int, muted: bool) -> None:
        """Set mute state for a specific zone."""
        addr = self._zone_to_address(zone_number)
        mute_val = "01" if muted else "00"
        self.send_command(f"<{addr}MU{mute_val}")
        self.poll_zone(zone_number)

    def set_zone_treble(self, zone_number: int, treble: int) -> None:
        """Set treble for a specific zone (0-14)."""
        addr = self._zone_to_address(zone_number)
        treble = max(0, min(14, treble))
        self.send_command(f"<{addr}TR{treble:02d}")
        self.poll_zone(zone_number)

    def set_zone_bass(self, zone_number: int, bass: int) -> None:
        """Set bass for a specific zone (0-14)."""
        addr = self._zone_to_address(zone_number)
        bass = max(0, min(14, bass))
        self.send_command(f"<{addr}BS{bass:02d}")
        self.poll_zone(zone_number)

    def set_zone_balance(self, zone_number: int, balance: int) -> None:
        """Set balance for a specific zone (0-20)."""
        addr = self._zone_to_address(zone_number)
        balance = max(0, min(20, balance))
        self.send_command(f"<{addr}BL{balance:02d}")
        self.poll_zone(zone_number)

    # Receiver-wide Control Methods
    def set_all_zones_power(self, power_on: bool) -> None:
        """Set power state for all zones."""
        power_val = "01" if power_on else "00"
        self.send_command(f"<10PR{power_val}")
        self.poll_all_zones()

    def set_all_zones_source(self, source: int) -> None:
        """Set source for all zones (1-6)."""
        source = max(1, min(6, source))
        self.send_command(f"<10CH0{source}")
        self.poll_all_zones()

    def set_all_zones_mute(self, muted: bool) -> None:
        """Set mute state for all zones."""
        mute_val = "01" if muted else "00"
        self.send_command(f"<10MU{mute_val}")
        self.poll_all_zones()

    # endregion
    # ========================================================================
    
    # ========================================================================
    # region Command Implementations
    # ========================================================================
    def _do_write(self, command: str) -> None:
        """
        Write a command to the serial port.
        
        Args:
            command: The command string to write
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            self.logger.warning("Serial port not open, cannot send command")
            return
        
        try:
            with self._lock:
                # Send command with carriage return
                cmd_bytes = (command + "\r").encode('ascii')
                self.serial_conn.write(cmd_bytes)
                self.logger.debug(f"Sent: {command}")
                
                # Small pause after write
                time.sleep(self.COMMAND_PAUSE)
                
                # Read any response
                self._read_response()
                
        except serial.SerialException as e:
            self.logger.error(f"Serial write error: {e}")
            self._handle_connection_error()

    def _do_poll_all(self) -> None:
        """Poll status for all zones on all connected receivers."""
        # Poll each receiver's zones
        for recv_num in range(1, self.connected_slave_units + 2):
            query = f"?{recv_num}0"
            self._do_write(query)
        
        self.last_poll_time = time.time()

    def _do_poll_zone(self, zone_number: int) -> None:
        """
        Poll status for a specific zone.
        
        Args:
            zone_number: The zone number (1-18)
        """
        addr = self._zone_to_address(zone_number)
        self._do_write(f"?{addr}")

    def _read_response(self) -> None:
        """Read and process response from serial port."""
        if not self.serial_conn or not self.serial_conn.is_open:
            return
        
        try:
            # Read available data
            response = ""
            while self.serial_conn.in_waiting > 0:
                chunk = self.serial_conn.read(self.serial_conn.in_waiting).decode('ascii', errors='ignore')
                response += chunk
                time.sleep(0.05)  # Small delay to allow more data to arrive
            
            if response:
                self.logger.debug(f"Received: {response.strip()}")
                self._parse_response(response)
                
        except serial.SerialException as e:
            self.logger.error(f"Serial read error: {e}")

    def _parse_response(self, response: str) -> None:
        """
        Parse zone status response from the receiver.
        
        Response format: #>XYCCZZZZZZZZZZZZ
        Where:
        - X = Receiver number (1-3)
        - Y = Zone number (1-6)
        - CC = Control status
        - Then pairs for: Power, Mute, DT, Volume, Treble, Bass, Balance, Source
        
        Args:
            response: The response string from the receiver
        """
        for match in self.response_pattern.finditer(response):
            status = match.groupdict()
            
            # Calculate the logical zone number (1-18) from receiver and zone
            recv_num = int(status["RecvNum"])
            zone_in_recv = int(status["ZoneNum"])
            zone_number = (recv_num - 1) * 6 + zone_in_recv
            
            self.logger.debug(f"Parsed status for Zone {zone_number}: {status}")
            
            # Find and update the zone device
            zone_key = str(zone_number)
            if zone_key in self.registered_zones:
                zone = self.registered_zones[zone_key]
                self._update_zone_states(zone, status)
            else:
                self.logger.debug(f"Zone {zone_number} not registered, skipping update")

    def _update_zone_states(self, zone: 'DaytonZone', status: Dict[str, str]) -> None:
        """
        Update zone device states from parsed response.
        
        Args:
            zone: The DaytonZone instance to update
            status: Dictionary of parsed status values
        """
        dev = zone.device
        
        # Build state updates
        states = []
        
        # Power state
        is_powered = status["Power"] == "01"
        states.append({"key": "isPoweredOn", "value": is_powered})
        states.append({"key": "onOffState", "value": is_powered})
        
        # Volume (0-38) and brightness level (0-100 scaled)
        volume = int(status["Volume"])
        states.append({"key": "volume", "value": volume})
        
        if is_powered:
            brightness = int(math.floor(volume * (100.0 / 38.0)))
        else:
            brightness = 0
        states.append({"key": "brightnessLevel", "value": brightness})
        
        # Other states
        states.append({"key": "isMuted", "value": status["Mute"] == "01"})
        states.append({"key": "trebleLevel", "value": int(status["Treble"])})
        states.append({"key": "bassLevel", "value": int(status["Bass"])})
        states.append({"key": "balanceStatus", "value": int(status["Balance"])})
        states.append({"key": "source", "value": int(status["Source"])})
        
        # Update all states on server
        dev.updateStatesOnServer(states)
        self.logger.debug(f"Updated states for {dev.name}")

    # endregion
    # ========================================================================
    
    # ========================================================================
    # region Helper Methods
    # ========================================================================
    def _zone_to_address(self, zone_number: int) -> str:
        """
        Convert logical zone number (1-18) to receiver address format.
        
        Args:
            zone_number: Zone number 1-18
            
        Returns:
            Address string like "11" for zone 1, "26" for zone 12
        """
        # Zones 1-6 are on receiver 1, 7-12 on receiver 2, 13-18 on receiver 3
        receiver = ((zone_number - 1) // 6) + 1
        zone_in_receiver = ((zone_number - 1) % 6) + 1
        return f"{receiver}{zone_in_receiver}"

    def _handle_connection_error(self) -> None:
        """Handle serial connection error."""
        self.is_connected = False
        self.device.updateStateOnServer('connectionState', value='Error')
        self.device.updateStateOnServer('isConnected', value=False)
        
        # Try to reconnect
        self._close_serial()
        time.sleep(1)
        self._open_serial()

    # endregion
    # ========================================================================
