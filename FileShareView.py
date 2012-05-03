#!/usr/bin/env python

#example base.py

import httplib
import avahi
import dbus
import socket
import gobject
import gtk
import uuid
import sys
import os
import pynotify
from os					import curdir, sep
from threading 			import Thread
from BaseHTTPServer 	import BaseHTTPRequestHandler, HTTPServer
from piper     			import PiperService
from dbus.mainloop.glib import DBusGMainLoop

SERVICE_NAME = "piper.fileshare:"
SERVICE_TYPE = "_piper._tcp"
SERVICE_TEXT = "Piper File Sharing Service"
SERVICE_PORT = 10285

class RequestHandler(BaseHTTPRequestHandler):
	"""Handling the transport using HTTP"""
	def do_GET(self):
		try:
			path = curdir + sep + self.path
			print("fetching %s" % path)
			f = open(curdir + sep + self.path)
			self.send_response(200)
			self.end_headers()
			self.wfile.write(f.read())
			f.close()
		except IOError:
			self.send_error(404, 'File Not Found: %s' % self.path)
		return

class FileShareServiceWorker(Thread):
	"""File Request Handler"""
	def __init__(self):
		Thread.__init__(self)
		self.server = None
		
	def run(self):
		try:
			self.server = HTTPServer(('', SERVICE_PORT), RequestHandler)
			print("starting file server")
			self.server.serve_forever()
		except KeyboardInterrupt:
			print('^c received.. shutting down file server')
				
class FileShareService():
	"""
	FileShare service which serves files: videos, audio and doc files
	"""
		
	def publish(self):
		from socket import gethostname
		name = SERVICE_NAME + gethostname()
		self.service = PiperService(name, 
						SERVICE_PORT,
						SERVICE_TYPE)
		status = self.service.publish()
		if(status == 1):
			print("service published :)")
		return status
	
	def start(self):
		self.s = FileShareServiceWorker() 
		self.s.start()
		while(True):
			if(self.s.server != None):
				break
		
	def stop(self):
		print("server shutting down")
		self.s.server.shutdown()
		
	def unpublish(self):
		print("service unpublished :(")
		self.service.unpublish()


class FileShareClientWorker(Thread):
	"""FileShare client for listening to service announcements"""
	
	def __init__(self, view):
		# device list store 
		Thread.__init__(self)
		self.view = view
		
	def run(self):
		self.service_lookup()
		
	def service_resolved(self, *args):
		print 'service resolved'
		print 'name:', 		args[2]
		print 'address:', 	args[7]
		print 'port:', 		args[8]
		self.view.call_notify("Found device : %s" % args[2])
		
		self.connect_service(args[7],args[8])
		
	def connect_service(self, address , port):
		print("connecting to %s:%s ..." %(address, port))
		conn = httplib.HTTPConnection(address, port)
		conn.request("GET","/overview.png")
		r = conn.getresponse()
		print(r.status, r.reason)
		file1 = open(curdir + sep + "test.png", "wb")
		file1.write(r.read())
		
	def print_error(self, *args):
		print 'error_handler'
		print args[0]

	def service_handler(self, interface, protocol, name, stype, domain, flags):
		print "Found service '%s' type '%s' domain '%s' " % (name, stype, domain)
		if flags & avahi.LOOKUP_RESULT_LOCAL:
			pass
		
		self.avahi_server.ResolveService(interface, 
	    								protocol, name, stype, 
	        							domain, avahi.PROTO_UNSPEC, 
	        							dbus.UInt32(0), 
	        							reply_handler=self.service_resolved, 
	        							error_handler=self.print_error)


	def service_lookup(self):
		self.loop			= DBusGMainLoop()
		self.bus 			= dbus.SystemBus(mainloop=self.loop)
		self.host_name 		= socket.gethostname()
		
		self.avahi_server 	= dbus.Interface(self.bus.get_object(avahi.DBUS_NAME,
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

		self.sbrowser.connect_to_signal("ItemNew", self.service_handler)
		gobject.MainLoop().run()
		
class ShareFile:
	"""
	This class stores the meta data for each file.
	"""
	def __init__(self, fileId=None, folderId=None, name=None, ext=None):
		self.fileId = fileId
		self.folderId = folderId
		self.name = name
		self.ext = ext
		
class FileShareView():
	"""
	This class is the file drop target
	"""
	VIDEO_EXTENSIONS = ".mp4:.avi:.3gp:.mkv"
	AUDIO_EXTENSIONS = ".mp3:.aac"
	videoExt = set(VIDEO_EXTENSIONS.split(":"))
	audioExt = set(AUDIO_EXTENSIONS.split(":"))

	def __init__(self, service=None):
		self.file_service = service
		# main window
		self.w_main = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.w_main.set_title("FileDrop")
		self.w_main.set_position(gtk.WIN_POS_CENTER)
		self.w_main.connect("delete_event", self.delete)
		self.w_main.set_border_width(10)
		self.w_main.set_size_request(400,400)

		# file/folder share window
		self.w_share = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.w_share.set_title("Share Files & Folders")
		self.w_share.set_keep_above(True)
		self.w_share.set_position(gtk.WIN_POS_CENTER)
		self.w_share.set_border_width(10)
		self.w_share.set_size_request(250,150)
		self.share_image = gtk.Image()
		self.share_image.set_from_file("box_small.png")
		self.w_share.add(self.share_image)

		#Drag and Drop for the share window
		self.share_image.drag_dest_set(0,[],0)
		self.share_image.connect('drag_motion', self.share_motion_cb)
		self.share_image.connect('drag_drop', self.share_drop_cb)
		self.share_image.connect('drag_data_received', self.share_got_data_cb)
		
		# file/folder send window
		self.w_send = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.w_send.set_title("Send Files")
		self.w_send.set_keep_above(True)
		self.w_send.set_position(gtk.WIN_POS_CENTER)
		self.w_send.set_border_width(10)
		self.w_send.set_size_request(250,150)
		self.send_image = gtk.Image()
		self.send_image.set_from_file("send_box.jpg")
		self.w_send.add(self.send_image)
		
		#Drag and Drop for the send window
		self.send_image.drag_dest_set(0,[],0)
		self.send_image.connect('drag_motion', self.send_motion_cb)
		self.send_image.connect('drag_drop', self.send_drop_cb)
		self.send_image.connect('drag_data_received', self.send_got_data_cb)
		
		# Create a bunch of buttons
		hbox = gtk.HBox(False, 0)
		self.b_start = gtk.Button("Start")
		self.b_start.connect("clicked", self.start_service)
		hbox.pack_start(self.b_start, False, False, 5)

		self.b_stop = gtk.Button("Stop")
		self.b_stop.connect("clicked", self.stop_service)
		self.b_stop.set_sensitive(False)
		hbox.pack_start(self.b_stop, False, False, 5)

		b_share = gtk.Button("Share")
		b_share.connect("clicked", self.share_files)
		hbox.pack_start(b_share, False, False, 5)

		b_send = gtk.Button("Send")
		b_send.connect("clicked", self.send_file)
		hbox.pack_start(b_send, False, False, 5)

		button = gtk.Button("Quit")
		button.connect("clicked", self.delete)
		hbox.pack_start(button, False, False, 5)

		table = gtk.Table(3,6,False)
		v_box = gtk.VBox(False, 0)
		v_box.pack_start(hbox, False, False, 10)
		v_box.pack_start(table, True, True, 10)
		self.w_main.add(v_box)

		# Create a new notebook, place the position of the tabs
		self.notebook = gtk.Notebook()
		self.notebook.set_tab_pos(gtk.POS_TOP)
		table.attach(self.notebook, 0,6,0,2)
		self.show_tabs = True
		self.show_border = True
		
		self.create_folder_table()
		self.create_device_table()
		
		# GUI Logic
		self.w_main.show_all()

		# File Management
		self.videoFiles = set({})
		self.audioFiles = set({})
		self.allFiles   = set({})
		self.fileMap	= {}
		

	def create_folder_table(self):
		# Treeview for the folders
		frame = gtk.Frame()
		frame.set_border_width(10)
		self.l_store = gtk.ListStore(str, str, 'gboolean')
		self.f_treeview = gtk.TreeView(self.l_store)
		# create the TreeViewColumns to display the data
		tvcolumn = gtk.TreeViewColumn()
		# add columns to treeview
		self.f_treeview.append_column(tvcolumn)
		# create a CellRenderers to render the data
		cellpb = gtk.CellRendererPixbuf()
		cell = gtk.CellRendererText()
		# add the cells to the columns - 2 in the first
		tvcolumn.pack_start(cellpb, False)
		tvcolumn.pack_start(cell, True)
		tvcolumn.set_attributes(cellpb, stock_id=1)
		tvcolumn.set_attributes(cell, text=0)
		tvcolumn.set_sort_column_id(0)
		scrollTree = gtk.ScrolledWindow()
		scrollTree.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		scrollTree.add(self.f_treeview)
		frame.add(scrollTree)
		label = gtk.Label("Folders")
		self.notebook.append_page(frame, label)
		
	def create_device_table(self):
		# Treeview for the folders
		frame = gtk.Frame()
		frame.set_border_width(10)
		self.d_store = gtk.ListStore(str, str, 'gboolean')
		self.d_treeview = gtk.TreeView(self.d_store)
		# create the TreeViewColumns to display the data
		tvcolumn = gtk.TreeViewColumn()
		# add columns to treeview
		self.d_treeview.append_column(tvcolumn)
		# create a CellRenderers to render the data
		cellpb = gtk.CellRendererPixbuf()
		cell = gtk.CellRendererText()
		# add the cells to the columns - 2 in the first
		tvcolumn.pack_start(cellpb, False)
		tvcolumn.pack_start(cell, True)
		tvcolumn.set_attributes(cellpb, stock_id=1)
		tvcolumn.set_attributes(cell, text=0)
		tvcolumn.set_sort_column_id(0)
		scrollTree = gtk.ScrolledWindow()
		scrollTree.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		scrollTree.add(self.d_treeview)
		frame.add(scrollTree)
		label = gtk.Label("Devices")
		self.notebook.append_page(frame, label)
	
	def send_file(self, widget, data=None):
		self.w_send.show_all()
				
	def delete(self, widget, event=None):
		gtk.main_quit()
		return False

	def start_service(self, widget, data=None):
		# publish and start server
		self.file_service.publish()
		self.file_service.start()
		# start listening on service client
		client = FileShareClientWorker(self)
		client.start()
		# change the state of the UI
		widget.set_sensitive(False)
		self.b_stop.set_sensitive(True)
		

	def stop_service(self, widget, data=None):
		# stop publishing and server
		self.file_service.stop()
		self.file_service.unpublish()
		# stop the client
		
		# change the UI state
		widget.set_sensitive(False)
		self.b_start.set_sensitive(True)
		

	def share_files(self, widget, data=None):
		self.w_share.show_all()

	def selection_change(self, treeview):
		(model, iter) = treeview.get_selected()
		path = model.get_path(iter)
		filename = model.get_value(iter, 2)
		print (filename)
		print(path)
		print(model, iter)
		
	def share_motion_cb(self, wid, context, x, y, time):
		context.drag_status(gtk.gdk.ACTION_COPY, time)
		return True

	def share_drop_cb(self, wid, context, x, y, time):
		print("drop_cb")
		wid.drag_get_data(context, context.targets[-1], time)
		return True

	def share_got_data_cb(self, wid, context, x, y, data, info, time):
		# Got data.
		print(data.get_text()) 
		context.finish(True, False, time)
		self.process_path(data.get_text())

	def send_motion_cb(self, wid, context, x, y, time):
		context.drag_status(gtk.gdk.ACTION_COPY, time)
		return True

	def send_drop_cb(self, wid, context, x, y, time):
		print("drop_cb")
		wid.drag_get_data(context, context.targets[-1], time)
		return True

	def send_got_data_cb(self, wid, context, x, y, data, info, time):
		# Got data.
		print(data.get_text()) 
		context.finish(True, False, time)
		self.prepare_send(data.get_text())
		
	def list_all_files(self, path, folderId):
		if(os.path.isdir(path)):
			files = os.listdir(path)
			for f in files:
				self.list_all_files(path +os.sep+ f, folderId)
		else:
			name = os.path.splitext(os.path.basename(path))
			fileId =  uuid.uuid4()
			share_file = ShareFile(name=name[0], ext= name[1],
							folderId= folderId, fileId = fileId)
			if name[1] in FileShareView.videoExt:
				self.videoFiles.add(fileId)
				self.turn_video += 1
			elif name[1] in FileShareView.audioExt:
				self.audioFiles.add(fileId)
				self.turn_audio += 1

			self.allFiles.add(fileId)
			self.turn_file += 1
			self.fileMap[fileId] = share_file
			print("file added: %s" % path)
			return


	def call_notify(self, msg):
		n = pynotify.Notification("FileDrop", msg)
		n.set_urgency(pynotify.URGENCY_NORMAL)
		n.set_timeout(5000)
		n.show()
		
	def process_path(self, paths):
		self.turn_video = 0
		self.turn_audio = 0
		self.turn_file 	= 0
		
		for v in FileShareView.videoExt:
			print(v)
		for a in FileShareView.audioExt:
			print(a)

		for p in paths.split(None):
			p = p[7:]
			if(os.path.isdir(p)):
				print("processing path : %s" % p)
				folderId = uuid.uuid4()
				self.list_all_files(p, folderId)
				self.ls_folders.append([p,gtk.STOCK_DIRECTORY,True])
			else:
				print("file cannot be processed %s" % p)
		
		msg = 	"Total video files added : %d \n"\
				"Total audio files added: %d \n"\
				"Total Files added: %d"
		msg = msg % (self.turn_video, self.turn_audio, self.turn_file)
		print(msg);
		self.call_notify(msg)
	
	def prepare_send(self, path):
		print("preparing to send %s" % path)
		pass
		
	def show(self):
		gtk.main()

def test():
	pass

def main():
	try:
		service = FileShareService()
		view 	= FileShareView(service)
		view.show()
	except KeyboardInterrupt:
		service.unpublish()
		print("unpublishing FileServe service")
		sys.exit(0)

if __name__ == "__main__":
	main()