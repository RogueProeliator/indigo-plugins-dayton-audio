#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Dayton Audio Receiver Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	See plugin.py for more plugin details and information
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
# Python imports
#/////////////////////////////////////////////////////////////////////////////////////////
import os
import Queue
import math
import re
import string
import sys
import threading

import indigo
import RPFramework


#/////////////////////////////////////////////////////////////////////////////////////////
# Constants and configuration variables
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# DaytonAudioReceiver
#	Handles the communications and status of a Dayton audio receiver which is connected
#	via the serial port
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class DaytonAudioReceiverDevice(RPFramework.RPFrameworkTelnetDevice.RPFrameworkTelnetDevice):
	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super(DaytonAudioReceiverDevice, self).__init__(plugin, device, connectionType=RPFramework.RPFrameworkTelnetDevice.CONNECTIONTYPE_SERIAL)
		self.activeControlZone = 0
		
		
	#/////////////////////////////////////////////////////////////////////////////////////
	# Processing and command functions
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process the commands that are not processed automatically by the
	# base class; it will be called on a concurrent thread
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handleUnmanagedCommandInQueue(self, ipConnection, rpCommand):
		if rpCommand.commandName == u'createAllZonesStatusRequestCommands':
			# create a set of commands to update the status of all zones defined by the
			# plugin (as child devices)
			updateCommandList = []
			for idx in range(1,int(self.indigoDevice.pluginProps.get(u'connectedSlaveUnits', '0')) + 2):
				self.hostPlugin.logDebugMessage(u'Creating update request for unit ' + RPFramework.RPFrameworkUtils.to_unicode(idx), RPFramework.RPFrameworkPlugin.DEBUGLEVEL_HIGH)
				updateCommandList.append(self.createZoneStatusRequestCommand(str(idx) + '0'))
			
			# queue up all of the commands at once (so they will run back to back)
			self.queueDeviceCommands(updateCommandList)
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called in order to generate the commands necessary to update
	# the status of a zone defined for this receiver
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def createZoneStatusRequestCommand(self, zoneNumber):
		return RPFramework.RPFrameworkCommand.RPFrameworkCommand(RPFramework.RPFrameworkTelnetDevice.CMD_WRITE_TO_DEVICE, commandPayload="?" + zoneNumber, postCommandPause=0.1)
				

	#/////////////////////////////////////////////////////////////////////////////////////
	# Validation and GUI functions
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of elements for an action (or
	# other ConfigUI based) routine
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogMenuItems(self, filter, valuesDict, typeId, targetId):
		# we need the parent (receiver) device in order to get the list of
		# available sources...
		#parentReceiver = self.hostPlugin.managedDevices[int(self.indigoDevice.pluginProps["sourceReceiver"])]
		
		# List of available sources
		sourceOptions = []
		for x in range(1,7):
			sourcePropName = u'source' + RPFramework.RPFrameworkUtils.to_unicode(x) + u'Label'
			if self.indigoDevice.pluginProps[sourcePropName] != "":
				sourceOptions.append((RPFramework.RPFrameworkUtils.to_unicode(x), u'Source ' + RPFramework.RPFrameworkUtils.to_unicode(x) + u': ' + self.indigoDevice.pluginProps[sourcePropName]))
			
		return sourceOptions
		

	#/////////////////////////////////////////////////////////////////////////////////////
	# Custom Response Handlers
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This callback is made whenever the plugin has received the response to a status
	# request for a particular zone
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def zoneStatusResponseReceived(self, responseObj, rpCommand):
		# the response format is a string of numbers in pairs
		responseParser = re.compile(r'^\s*#>(?P<RecvNum>\d{1})(?P<ZoneNum>\d{1})(?P<ControlStatus>\d{2})(?P<Power>\d{2})(?P<Mute>\d{2})(?P<DT>\d{2})(?P<Volume>\d{2})(?P<Treble>\d{2})(?P<Bass>\d{2})(?P<Balance>\d{2})(?P<Source>\d{2})\d{2}\s*$', re.I)
		statusObj = responseParser.match(responseObj)
		statusInfo = statusObj.groupdict()
		
		# calculate the zone number based on the receiver and zone found
		zoneNumber = (int(statusInfo["RecvNum"]) - 1) * 6 + int(statusInfo["ZoneNum"])
		self.hostPlugin.logDebugMessage(u'Received status update for Zone ' + RPFramework.RPFrameworkUtils.to_unicode(zoneNumber) + u': ' + RPFramework.RPFrameworkUtils.to_unicode(responseObj), RPFramework.RPFrameworkPlugin.DEBUGLEVEL_MED)
		
		# attempt to find the zone within the child devices
		if str(zoneNumber) in self.childDevices:
			self.hostPlugin.logDebugMessage(u'Found zone as child device, updating states...', RPFramework.RPFrameworkPlugin.DEBUGLEVEL_HIGH)
			zoneDevice = self.childDevices[str(zoneNumber)]
			
			zoneDevice.indigoDevice.updateStateOnServer(key=u'isPoweredOn', value=statusInfo["Power"] == "01")
			zoneDevice.indigoDevice.updateStateOnServer(key=u'onOffState', value=statusInfo["Power"] == "01")
			
			# volume will be an absolute value where as brightnessLevel is a scaled value to allow
			# sliders (0-38 => 0-100)
			zoneDevice.indigoDevice.updateStateOnServer(key=u'volume', value=int(statusInfo["Volume"]))
			
			if statusInfo["Power"] == "01":
				zoneDevice.indigoDevice.updateStateOnServer(key=u'brightnessLevel', value=int(math.floor(int(statusInfo["Volume"])*(100.0/38.0))))
			else:
				zoneDevice.indigoDevice.updateStateOnServer(key=u'brightnessLevel', value=0)
			
			zoneDevice.indigoDevice.updateStateOnServer(key=u'isMuted', value=(statusInfo["Mute"] == "01"))
			zoneDevice.indigoDevice.updateStateOnServer(key=u'trebleLevel', value=int(statusInfo["Treble"]))
			zoneDevice.indigoDevice.updateStateOnServer(key=u'bassLevel', value=int(statusInfo["Bass"]))
			zoneDevice.indigoDevice.updateStateOnServer(key=u'balanceStatus', value=int(statusInfo["Balance"]))
			zoneDevice.indigoDevice.updateStateOnServer(key=u'source', value=int(statusInfo["Source"]))
				
		
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# DaytonAudioZone
#	Handles the status and representation of a zone associated with a Dayton Audio multi-
#	zone receiver
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class DaytonAudioZone(RPFramework.RPFrameworkNonCommChildDevice.RPFrameworkNonCommChildDevice):

	#/////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super(DaytonAudioZone, self).__init__(plugin, device)
		
		
	#/////////////////////////////////////////////////////////////////////////////////////
	# Validation and GUI functions
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of elements for an action (or
	# other ConfigUI based) routine
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogMenuItems(self, filter, valuesDict, typeId, targetId):
		# we need the parent (receiver) device in order to get the list of
		# available sources...
		parentReceiver = self.hostPlugin.managedDevices[int(self.indigoDevice.pluginProps["sourceReceiver"])]
		
		sourceOptions = []
		for x in range(1,7):
			sourcePropName = u'source' + RPFramework.RPFrameworkUtils.to_unicode(x) + u'Label'
			if parentReceiver.indigoDevice.pluginProps[sourcePropName] != "":
				sourceOptions.append((RPFramework.RPFrameworkUtils.to_unicode(x), u'Source ' + RPFramework.RPFrameworkUtils.to_unicode(x) + u': ' + parentReceiver.indigoDevice.pluginProps[sourcePropName]))
			
		return sourceOptions
		
	