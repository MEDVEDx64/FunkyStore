import BaseHTTPServer
import SocketServer
import pymongo

PORT = 8000
HOST = 'localhost'
if not PORT == 80:
	HOST += ':' + str(PORT)
db = None

class FunkyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def html_start(self):
		self.wfile.write('<html><head><title>Funky Trade</title></head>')
		self.wfile.write('<body><center>\n')

	def html_end(self):
		self.wfile.write('</center></body></html>\n')

	def do_GET(self):
		if not self.headers['host'] == HOST:
			self.send_error(404, 'Nothing')
			return

		if self.path == '/':
			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.wfile.write('Funky Trade\n')
			self.html_end()

		else:
			self.send_error(404, 'Not Found')

if __name__ == '__main__':
	dbclient = pymongo.MongoClient()
	db = dbclient.funky
	httpd = SocketServer.TCPServer(("", PORT), FunkyHTTPRequestHandler)
	httpd.serve_forever()