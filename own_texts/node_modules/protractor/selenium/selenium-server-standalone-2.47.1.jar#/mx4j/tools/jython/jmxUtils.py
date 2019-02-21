""" Copyright (C) MX4J.
 All rights reserved.

 This software is distributed under the terms of the MX4J License version 1.0.
 See the terms of the MX4J License in the documentation provided with this software.

 author <a href="mailto:tibu@users.sourceforge.net">Carlos Quiroz</a>
 version $Revision: 1.1 $
 
 Adapted by Martin Fuzzey for testing use.
 For this we need to communicate with a REMOTE server (the orignal code
 always ran in the same process as the JMX server and was intended to be
 used as helpers for python scripts in the python MBean
 
 """

import sys,java
sys.add_package("javax.management")
sys.add_package("javax.management.loading");
sys.add_package("javax.management.modelmbean");
sys.add_package("javax.management.monitor");
sys.add_package("javax.management.openmbean");
sys.add_package("javax.management.relation");
sys.add_package("javax.management.remote");
sys.add_package("javax.management.remote.rmi");
sys.add_package("javax.management.timer");
from javax.management import *
from javax.management.loading import *
from javax.management.modelmbean import *
from javax.management.monitor import *
from javax.management.openmbean import *
from javax.management.relation import *
from javax.management.remote import *
from javax.management.remote.rmi import *
from javax.management.timer import *

class ServerConnection:
    def __init__(self, connection) :
        self.server = connection
        
    def createProxy(self, objectname) :
        """
        Creates a proxy for the named MBean in this server.
        The objectname may either be an instance of javax.management.ObjectName
        or a string
        
        The MBeans attributes and methods may be then accessed directly as in :
            proxy = server.createProxy("myDomain:myType=toto")
            print "val=",proxy.val
            proxy.doSomething()
        """ 
        if (isinstance(objectname, ObjectName) == 0) :
            objectname = ObjectName(objectname)
            
        return Proxy(self.server, objectname)
        
    def getMBeanNames(self, query="*:*"):
        """
        Returns a list of all the available MBeans in the server. The optional
        query parameter will filter the list by objectname
        """
        names = []
        for n in self.server.queryNames(ObjectName(query), None) :
          names.append(n) ;# To python collection
        return names

    def getInstanceNames(self, classname, query="*:*"):
        """
        Returns a list of all the available MBeans in the server which are instances
        of classname. It accepts a query parameter to filter by objectname
        """
        return [x for x in self.getMBeanNames(query) if self.server.isInstanceOf(x, classname)]
                        
    
class OperationProxy:
    def __init__(self, server, objectname, opInfo):
        self.server = server
        self.objectname = objectname
        self.operation = opInfo.name
        self.sig = []
        for s in opInfo.signature :
          self.sig.append(s.type)
    
    def invoke(self, *args):
      if (len(args) != len(self.sig)) :
        raise "argument list / sig mismatch" + str(args) + str(self.sig)
        
      # Manually map Boolean
      nargs = []    
      for i in range(len(args)) :
        arg = args[i]
        if (self.sig[i] == "boolean") :
          arg = java.lang.Boolean(arg)
        nargs.append(arg) 

      return self.server.invoke(self.objectname, self.operation, nargs, self.sig)

class Proxy:
    def __init__(self, server, objectname):
      # Need the syntax below to avoid infinite recursion betweed setattr + getattr
        self.__dict__["server"] = server
        self.__dict__["objectname"] = objectname
        
        info = self.server.getMBeanInfo(objectname)
        for o in info.operations:
            self.__dict__[o.name] = OperationProxy(self.server, objectname, o).invoke
#            print "op:", o.name

    def __getattr__(self, name):
        return self.server.getAttribute(self.objectname, name)

    def __setattr__(self, name, value):
        from javax.management import Attribute
        return self.server.setAttribute(self.objectname, Attribute(name, value))

    def __repr__(self):
        return "Proxy of MBean: %s " % (self.__dict__["objectname"], )

    def invoke(self, name, arguments=None, types=None):
        return self.server.invoke(self.objectname, name, arguments, types)

    def addListener(self, l, filter=None, handback=None) :
        self.server.addNotificationListener(self.objectname, l, filter, handback)

class proxy (Proxy): # For backwards compatibility
  pass

def mbeans(query=None):
  """
    Returns a list of all the available MBeans in the server. The optional
    query parameter will filter the list by objectname
  """
  if query:
    return server.queryMBeans(ObjectName(query), None)
  else:
    return server.queryMBeans(None, None)

def instances(classname, query=None):
  """
    Returns a list of all the available MBeans in the server which are instances
    of classname. It accepts a query parameter to filter by objectname
  """
  return [x for x in mbeans(query) if server.isInstanceOf(x.getObjectName(),classname)]
