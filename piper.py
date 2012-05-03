import avahi
import dbus
 
__all__ = ["PiperService"]
 
class PiperService:
    """
    A simple class to publish a network service using avahi.
    """
    def __init__(self, name, port, stype="_piper._tcp",
                 domain="", host="", text="",DEBUG=False):
        self.name   = name
        self.type   = stype
        self.domain = domain
        self.host   = host
        self.port   = port
        self.text   = text
        self.DEBUG  = DEBUG
 
    def publish(self):
        bus     = dbus.SystemBus()
        server  = dbus.Interface(
                        bus.get_object(
                                 avahi.DBUS_NAME,
                                 avahi.DBUS_PATH_SERVER),
                        avahi.DBUS_INTERFACE_SERVER)
        g = dbus.Interface(
                    bus.get_object(avahi.DBUS_NAME,
                                   server.EntryGroupNew()),
                    avahi.DBUS_INTERFACE_ENTRY_GROUP)
        
        g.AddService(
            avahi.IF_UNSPEC,                #interface
            avahi.PROTO_UNSPEC,             #protocol
            dbus.UInt32(0),                 #flags
            self.name, self.type,           
            self.domain, self.host,
            dbus.UInt16(self.port),
            avahi.string_array_to_txt_array(self.text))

        g.Commit()
        self.group = g
        if(self.DEBUG):
            print("service : %s, unpublished :(" % self.name)
        return 1
 
    def unpublish(self):
        self.group.Reset()
        if(self.DEBUG):
            print("service : %s, published :)" % self.name)
 
 
def test():
    service = PiperService(name="TestService", port=3000,DEBUG=True)
    service.publish()
    raw_input("Press any key to unpublish the service ")
    service.unpublish()
 
if __name__ == "__main__":
    test()
