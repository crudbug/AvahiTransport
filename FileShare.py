from os				import curdir, sep
from threading 		import Thread
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from piper     		import PiperService
import time
import string
import cgi

SERVICE_NAME = "piper.fileshare:"
SERVICE_TYPE = "_piper._tcp"
SERVICE_TEXT = "Piper File Sharing Service"
SERVICE_PORT = 10285

class RequestHandler(BaseHTTPRequestHandler):
	
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

class FileServer(Thread):
	def run(self):
		try:
			server = HTTPServer(('', SERVICE_PORT), RequestHandler)
			print("started file server")
			server.serve_forever()
		except KeyboardInterrupt:
			print('^c received.. shutting down file server')	

class FileShare:
	"""
	FileShare service which serves files: videos, audio and text files
	"""

	def publish(self):
		from socket import gethostname
		name = SERVICE_NAME + gethostname()
		self.service = PiperService(name, 
						SERVICE_PORT,
						SERVICE_TYPE)
		self.service.publish()
	
	def start(self):
		fileserver = FileServer()
		fileserver.start()

	def unpublish(self):
		self.service.unpublish()

def test():
	pass

def main():
	try:
		service = FileShare()
		service.publish()
		service.start()	
		while (True):
			pass
	except KeyboardInterrupt:
		service.unpublish()
		print("unpublishing FileServe service")

if __name__ == "__main__":
	main()
