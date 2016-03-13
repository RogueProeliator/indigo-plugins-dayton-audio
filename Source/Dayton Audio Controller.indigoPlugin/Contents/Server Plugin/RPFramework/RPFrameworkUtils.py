#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkUtils by RogueProeliator <adam.d.ashe@gmail.com>
# 	Non-class utility functions for use across the framework
#	
#	Version 1.0.17:
#		Initial release of the plugin framework with unicode support
#
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
# Python imports
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
# Data Type Conversions
#/////////////////////////////////////////////////////////////////////////////////////////
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# This routine ensures that the given string is a unicode string (if it is a string based
# variable), encoding to unicode if necessary
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def to_unicode(obj, encoding="utf-8"):
	if obj is None:
		return u''
	elif isinstance(obj, basestring):
		if isinstance(obj, unicode):
			return obj
		elif isinstance(obj, str):
			return unicode(obj, encoding)
	return unicode(obj)
	
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# This routine ensures that the given string is a string object (not unicode), converting
# as necessary
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def to_str(obj, encoding="utf-8"):
	if obj is None:
		return ""
	elif isinstance(obj, basestring):
		if isinstance(obj, str):
			return obj
		elif isinstance(obj, unicode):
			return obj.encode(encoding)
	return str(obj)
