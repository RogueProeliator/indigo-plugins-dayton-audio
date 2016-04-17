#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Dayton Audio Receiver Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	Indigo plugin designed to allow full control of a Dayton Audio zone receiver such 
#	as the DAX66
#	
#	Command structure based on Dayton Audio's published specification found in the DAX66
#	instruction manual
#
#	Version 1.0:
#		* Initial release of the plugin to Indigo users
#
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
# Python imports
#/////////////////////////////////////////////////////////////////////////////////////////
import re
import string
import os

import RPFramework
import daytonAudioDevices


#/////////////////////////////////////////////////////////////////////////////////////////
# Constants and configuration variables
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Plugin
#	Primary Indigo plugin class that is universal for all receiver devices to be
#	controlled (this represents the master receiver)
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class Plugin(RPFramework.RPFrameworkPlugin.RPFrameworkPlugin):
	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class creation; setup the device tracking
	# variables for later use
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		# RP framework base class's init method
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs, u'http://www.duncanware.com/Downloads/IndigoHomeAutomation/Plugins/DaytonAudioReceiver/DaytonAudioReceiverVersionInfo.html', managedDeviceClassModule=daytonAudioDevices)
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-	
	# This routine will be called from the user executing the menu item action to send
	# an arbitrary command code to the Dayton Audio receiver
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-	
	def sendArbitraryCommand(self, valuesDict, typeId):
		try:
			deviceId = valuesDict.get(u'targetDevice', u'0')
			commandCode = valuesDict.get(u'commandToSend', u'').strip()
		
			if deviceId == u'' or deviceId == u'0':
				# no device was selected
				errorDict = indigo.Dict()
				errorDict[u'targetDevice'] = u'Please select a device'
				return (False, valuesDict, errorDict)
			elif commandCode == u'':
				errorDict = indigo.Dict()
				errorDict[u'commandToSend'] = u'Enter command to send'
				return (False, valuesDict, errorDict)
			else:
				# send the code using the normal action processing...
				actionParams = indigo.Dict()
				actionParams[u'commandCode'] = commandCode
				self.executeAction(pluginAction=None, indigoActionId=u'SendArbitraryCommand', indigoDeviceId=int(deviceId), paramValues=actionParams)
				return (True, valuesDict)
		except:
			self.exceptionLog()
			return (False, valuesDict)
			