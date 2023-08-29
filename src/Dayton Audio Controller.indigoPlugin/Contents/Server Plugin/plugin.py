#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# Dayton Audio Receiver Plugin by RogueProeliator <rp@rogueproeliator.com>
# Indigo plugin designed to allow full control of a Dayton Audio zone receiver such
# as the DAX66
#######################################################################################

# region Python Imports
import daytonAudioDevices

from RPFramework.RPFrameworkPlugin import RPFrameworkPlugin
# endregion


class Plugin(RPFrameworkPlugin):
	
	#######################################################################################
	# region Class construction and destruction methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class creation; setup the device tracking
	# variables for later use
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs, managed_device_class_module=daytonAudioDevices)

	# endregion
	#######################################################################################

	#######################################################################################
	# region Actions object callback handlers/routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called from the user executing the menu item action to send
	# an arbitrary command code to the Dayton Audio receiver
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def sendArbitraryCommand(self, valuesDict, typeId):
		try:
			device_id    = valuesDict.get(u'targetDevice', u'0')
			command_code = valuesDict.get(u'commandToSend', u'').strip()
		
			if device_id == "" or device_id == "0":
				# no device was selected
				error_dict = indigo.Dict()
				error_dict["targetDevice"] = "Please select a device"
				return False, valuesDict, error_dict
			elif command_code == u'':
				error_dict = indigo.Dict()
				error_dict["commandToSend"] = "Enter command to send"
				return False, valuesDict, error_dict
			else:
				# send the code using the normal action processing...
				action_params = indigo.Dict()
				action_params["commandCode"] = command_code
				self.execute_action(pluginAction=None, indigoActionId="SendArbitraryCommand", indigoDeviceId=int(device_id), paramValues=action_params)
				return True, valuesDict
		except:
			self.logger.exception("Failed to send command to device")
			return False, valuesDict

	# endregion
	#######################################################################################
