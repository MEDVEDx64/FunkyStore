import BaseHTTPServer
import SocketServer

PORT = 8000

class FunkyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def do_GET(self):
		self.send_response(200)
		self.end_headers()
		self.wfile.write("Funky Trade\n")

if __name__ == '__main__':
	httpd = SocketServer.TCPServer(("", PORT), FunkyHTTPRequestHandler)
	httpd.serve_forever()