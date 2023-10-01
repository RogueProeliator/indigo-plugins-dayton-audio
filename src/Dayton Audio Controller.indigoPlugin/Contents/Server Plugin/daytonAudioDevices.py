#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# Dayton Audio Receiver Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	See plugin.py for more plugin details and information
#######################################################################################

# region Python Imports
import math
import re

import indigo

from RPFramework.RPFrameworkTelnetDevice import RPFrameworkTelnetDevice
from RPFramework.RPFrameworkNonCommChildDevice import RPFrameworkNonCommChildDevice
from RPFramework.RPFrameworkCommand import RPFrameworkCommand
# endregion


class DaytonAudioReceiverDevice(RPFrameworkTelnetDevice):

	#######################################################################################
	# region Class construction and destruction methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super().__init__(plugin, device, connection_type=RPFrameworkTelnetDevice.CONNECTIONTYPE_SERIAL)
		self.activeControlZone = 0

	# endregion
	#######################################################################################

	#######################################################################################
	# region Processing and command functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process the commands that are not processed automatically by the
	# base class; it will be called on a concurrent thread
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle_unmanaged_command_in_queue(self, ip_connection, rp_command):
		if rp_command.command_name == "createAllZonesStatusRequestCommands":
			# create a set of commands to update the status of all zones defined by the
			# plugin (as child devices)
			update_command_list = []
			for idx in range(1, int(self.indigoDevice.pluginProps.get("connectedSlaveUnits", "0")) + 2):
				self.host_plugin.logger.threaddebug(f"Creating update request for unit {idx}")
				update_command_list.append(self.create_zone_status_request_command(f"{idx}0"))
			
			# queue up all the commands at once (so they will run back to back)
			self.queue_device_commands(update_command_list)
	
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called in order to generate the commands necessary to update
	# the status of a zone defined for this receiver
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def create_zone_status_request_command(self, zone_number):
		return RPFrameworkCommand(RPFrameworkTelnetDevice.CMD_WRITE_TO_DEVICE, command_payload=f"?{zone_number}", post_command_pause=0.1)

	# endregion
	#######################################################################################
		
	#######################################################################################
	# region Validation and GUI functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of elements for an action (or
	# other ConfigUI based) routine
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogMenuItems(self, filter, valuesDict, typeId, targetId):
		source_options = []
		for x in range(1, 7):
			source_prop_name = f"source{x} Label"
			if self.indigoDevice.pluginProps[source_prop_name] != "":
				source_options.append((f"{x}", f"Source {x}: {self.indigoDevice.pluginProps[source_prop_name]}"))
			
		return source_options

	# endregion
	#######################################################################################

	#######################################################################################
	# region Custom Response Handlers
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This callback is made whenever the plugin has received the response to a status
	# request for a particular zone
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def zone_status_response_received(self, response_obj, rp_command):
		# the response format is a string of numbers in pairs
		response_parser = re.compile(r'^\s*#>(?P<RecvNum>\d{1})(?P<ZoneNum>\d{1})(?P<ControlStatus>\d{2})(?P<Power>\d{2})(?P<Mute>\d{2})(?P<DT>\d{2})(?P<Volume>\d{2})(?P<Treble>\d{2})(?P<Bass>\d{2})(?P<Balance>\d{2})(?P<Source>\d{2})\d{2}\s*$', re.M)
		for status_obj in response_parser.finditer(response_obj):
			status_info = status_obj.groupdict()

			# calculate the zone number based on the receiver and zone found
			zone_number = (int(status_info["RecvNum"]) - 1) * 6 + int(status_info["ZoneNum"])
			self.host_plugin.logger.debug(f"Received status update for Zone {zone_number}: {response_obj}")

			# attempt to find the zone within the child devices
			if f"{zone_number}" in self.child_devices:
				self.host_plugin.logger.threaddebug("Found zone as child device, updating states...")
				zone_device = self.child_devices[f"{zone_number}"]

				zone_device.indigoDevice.updateStateOnServer(key="isPoweredOn", value=status_info["Power"] == "01")
				zone_device.indigoDevice.updateStateOnServer(key="onOffState", value=status_info["Power"] == "01")

				# volume will be an absolute value wherein brightnessLevel is a scaled value to allow
				# sliders (0-38 => 0-100)
				zone_device.indigoDevice.updateStateOnServer(key="volume", value=int(status_info["Volume"]))

				if status_info["Power"] == "01":
					zone_device.indigoDevice.updateStateOnServer(key="brightnessLevel", value=int(math.floor(int(status_info["Volume"])*(100.0/38.0))))
				else:
					zone_device.indigoDevice.updateStateOnServer(key="brightnessLevel", value=0)

				zone_device.indigoDevice.updateStateOnServer(key="isMuted", value=(status_info["Mute"] == "01"))
				zone_device.indigoDevice.updateStateOnServer(key="trebleLevel", value=int(status_info["Treble"]))
				zone_device.indigoDevice.updateStateOnServer(key="bassLevel", value=int(status_info["Bass"]))
				zone_device.indigoDevice.updateStateOnServer(key="balanceStatus", value=int(status_info["Balance"]))
				zone_device.indigoDevice.updateStateOnServer(key="source", value=int(status_info["Source"]))

	# endregion
	#######################################################################################


class DaytonAudioZone(RPFrameworkNonCommChildDevice):

	#######################################################################################
	# region Class construction and destruction methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super().__init__(plugin, device)

	# endregion
	#######################################################################################

	#######################################################################################
	# region Validation and GUI functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of elements for an action (or
	# other ConfigUI based) routine
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogMenuItems(self, filter, valuesDict, typeId, targetId):
		# we need the parent (receiver) device in order to get the list of
		# available sources...
		parent_receiver = self.host_plugin.managedDevices[int(self.indigoDevice.pluginProps["sourceReceiver"])]
		
		source_options = []
		for x in range(1, 7):
			source_prop_name = f"source{x}Label"
			if parent_receiver.indigoDevice.pluginProps[source_prop_name] != "":
				source_options.append((f"{x}", f"Source {x}: {parent_receiver.indigoDevice.pluginProps[source_prop_name]}"))
			
		return source_options

	# endregion
	#######################################################################################
	