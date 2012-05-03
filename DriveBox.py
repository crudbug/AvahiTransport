from os	import curdir, sep
from dbus.mainloop.glib import DBusGMainLoop
import httplib
import avahi
import dbus
import socket
import gobject

SERVICE_TYPE = '_piper._tcp'

class DriveBox():

	def service_resolved(self, *args):
		print 'service resolved'
		print 'name:', 		args[2]
		print 'address:', 	args[7]
		print 'port:', 		args[8]
		self.connectToService(args[7],args[8])

	def print_error(self, *args):
		print 'error_handler'
		print args[0]

	def serviceHandler(self, interface, protocol, name, stype, domain, flags):
		print "Found service '%s' type '%s' domain '%s' " % (name, stype, domain)
		if flags & avahi.LOOKUP_RESULT_LOCAL:
			pass
		
		self.avahi_server.ResolveService(interface, 
	    								protocol, name, stype, 
	        							domain, avahi.PROTO_UNSPEC, 
	        							dbus.UInt32(0), 
	        							reply_handler=self.service_resolved, 
	        							error_handler=self.print_error)


	def serviceLookup(self):
		self.loop= DBusGMainLoop()
		self.bus 			= dbus.SystemBus(mainloop=self.loop)
		self.host_name 		= socket.gethostname()
		
		self.avahi_server 	= dbus.Interface( self.bus.get_object(avahi.DBUS_NAME,
								avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)

		self.sbrowser 		= dbus.Interface(self.bus.get_object(
									avahi.DBUS_NAME,
        							self.avahi_server.ServiceBrowserNew(
        									avahi.IF_UNSPEC,
            								avahi.PROTO_UNSPEC, 
            								SERVICE_TYPE, 
            								'local', 
            								dbus.UInt32(0))),
        						avahi.DBUS_INTERFACE_SERVICE_BROWSER)

		self.sbrowser.connect_to_signal("ItemNew", self.serviceHandler)
		gobject.MainLoop().run()


	def connectToService(self, address , port):
		print("connecting to %s:%s ..." %(address, port))
		conn = httplib.HTTPConnection(address, port)
		conn.request("GET","/overview.png")
		r = conn.getresponse()
		print(r.status, r.reason)

		file = open(curdir + sep + "test.png", "wb")
		file.write(r.read())

def main():
	client = DriveBox()
	client.serviceLookup()

if __name__ == "__main__":
	main()