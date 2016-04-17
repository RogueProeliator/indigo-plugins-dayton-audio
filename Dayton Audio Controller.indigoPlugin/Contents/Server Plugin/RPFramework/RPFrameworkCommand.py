#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkCommand by RogueProeliator <adam.d.ashe@gmail.com>
# 	Class for all RogueProeliator's commands that request that an action be executed
#	on a processing thread.
#	
#	Version 1.0.0 [10-18-2013]:
#		Initial release of the device framework
#	Version 1.0.8 [5/2014]:
#		Added reconnect to device command (CMD_DEVICE_RECONNECT)
#	Version 1.0.17:
#		Changed command constants to unicode
#		Added getPayloadAsList function
#
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
# Constants and configuration variables
#/////////////////////////////////////////////////////////////////////////////////////////
# standard command names common to many plugins
CMD_INITIALIZE_CONNECTION = u'INITIALIZECONNECTION'
CMD_TERMINATE_PROCESSING_THREAD = u'TERMINATEPROCESSING'
CMD_PAUSE_PROCESSING = u'PAUSEPROCESSING'

CMD_UPDATE_DEVICE_STATUS_FULL = u'UPDATEDEVICESTATUS_FULL'
CMD_UPDATE_DEVICE_STATE = u'UPDATEDEVICESTATE'

CMD_NETWORKING_WOL_REQUEST = u'SENDWOLREQUEST'
CMD_DEVICE_RECONNECT = u'RECONNECTDEVICE'

CMD_DEBUG_LOGUPNPDEVICES = u'LOGUPNPDEVICES'


#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkCommand
#	Class that allows communication of an action request between the plugin device and
#	its processing thread that is executing the actions/requests/communications
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class RPFrameworkCommand(object):
	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the command
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, commandName, commandPayload=None, postCommandPause=0.0, parentAction=u''):
		self.commandName = commandName
		self.commandPayload = commandPayload
		self.postCommandPause = postCommandPause
		self.parentAction = parentAction
		
		
	#/////////////////////////////////////////////////////////////////////////////////////
	# Utility methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Routine to return a list for the payload, converting a string to a list using the
	# provided delimiter when necessary
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getPayloadAsList(self, delim=u'|*|'):
		if isinstance(self.commandPayload, basestring):
			return self.commandPayload.split(delim)
		else:
			return self.commandPayload
