""" Copyright (C) MX4J.
 All rights reserved.

 This software is distributed under the terms of the MX4J License version 1.0.
 See the terms of the MX4J License in the documentation provided with this software.

 author <a href="mailto:tibu@users.sourceforge.net">Carlos Quiroz</a>
 version $Revision: 1.3 $
 """

from javax.management import *
from javax.management.monitor import *
from javax.management.timer import *
from javax.management.loading import *
from javax.management.relation import *
from javax.management.modelmbean import *

class OperationProxy:
	def __init__(self, objectname, operation):
		self.objectname = objectname
		self.operation = operation

	def invoke(self, **kw):
		server.invoke(self.objectname, self.operation, None, None)

class proxy:
	def __init__(self, objectname):
		self.__dict__["objectname"] = objectname
		info = server.getMBeanInfo(objectname)
		for o in info.operations:
			self.__dict__[o.name] = OperationProxy(objectname, o.name).invoke

	def __getattr__(self, name):
		return server.getAttribute(self.objectname, name)

	def __setattr__(self, name, value):
		from javax.management import Attribute
		return server.setAttribute(self.objectname, Attribute(name, value))

	def __repr__(self):
		return "Proxy of MBean: %s " % (self.__dict__["objectname"], )

	def invoke(self, name, arguments=None, types=None):
		return server.invoke(self.objectname, name, arguments, types)

def mbeans(query=None):
	"""
		Returns a list of all the available MBeans in the server. The optional
		query parameter will filter the list by objectname
	"""
	return server.getQueryMBeans(ObjectName(query), None)

def instances(classname, query=None):
	"""
		Returns a list of all the available MBeans in the server which are instances
		of classname. It accepts a query parameter to filter by objectname
	"""
	return [x for x in mbeans(query) if server.isInstanceOf(classname)]
