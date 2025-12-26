#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dayton Audio Zone Device Class

Represents a single audio zone on a Dayton Audio receiver.
Zone devices are dimmer devices that use brightness level for volume control.

Zones are child devices that depend on a parent receiver device for communication.
The zone device maintains its own state but all commands are sent through the receiver.
"""

# region Python Imports
from typing import TYPE_CHECKING

import indigo

if TYPE_CHECKING:
    from plugin import Plugin
# endregion


class DaytonZone:
    """
    Represents a single zone on a Dayton Audio receiver.
    
    The zone is a child device that delegates all communication to its
    parent receiver device. It maintains state information that is
    updated when the receiver parses status responses.
    
    Zone states include:
    - Power on/off
    - Volume (0-38)
    - Source (1-6)
    - Mute status
    - Treble level (0-14)
    - Bass level (0-14)
    - Balance (0-20)
    """

    def __init__(self, plugin: 'Plugin', device: indigo.Device):
        """
        Initialize the Dayton zone.
        
        Args:
            plugin: Reference to the main plugin instance
            device: The Indigo device this zone represents
        """
        self.host_plugin = plugin
        self.device = device
        self.logger = plugin.logger
        
        # Zone configuration from device properties
        self.zone_number = int(device.pluginProps.get('zoneNumber', '1'))
        self.receiver_id = int(device.pluginProps.get('sourceReceiver', '0'))
        
        self.logger.debug(f"DaytonZone initialized: {device.name} (Zone {self.zone_number})")

    @property
    def is_powered_on(self) -> bool:
        """Get the current power state."""
        return self.device.states.get("isPoweredOn", False)

    @property
    def volume(self) -> int:
        """Get the current volume level (0-38)."""
        return self.device.states.get("volume", 0)

    @property
    def source(self) -> int:
        """Get the current source number (1-6)."""
        return self.device.states.get("source", 1)

    @property
    def is_muted(self) -> bool:
        """Get the current mute state."""
        return self.device.states.get("isMuted", False)

    @property
    def treble_level(self) -> int:
        """Get the current treble level (0-14)."""
        return self.device.states.get("trebleLevel", 7)

    @property
    def bass_level(self) -> int:
        """Get the current bass level (0-14)."""
        return self.device.states.get("bassLevel", 7)

    @property
    def balance_status(self) -> int:
        """Get the current balance setting (0-20, 10=center)."""
        return self.device.states.get("balanceStatus", 10)
