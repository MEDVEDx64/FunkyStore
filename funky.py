import BaseHTTPServer
import SocketServer
import pymongo
from config import config
import urlparse
from os import urandom
import base64
from datetime import datetime
import cookielib

PORT = config['port']
HOST = config['host']
#if not PORT == 80:
#	HOST += ':' + str(PORT)
db = None

class FunkyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def html_start(self):
		self.wfile.write('<html><head><title>Funky Trade</title></head>')
		self.wfile.write('<body><center>\n')

	def html_end(self):
		self.wfile.write('</center></body></html>\n')

	def html_block_start(self):
		self.wfile.write("<div>\n")

	def html_block_end(self):
		self.wfile.write("</div>\n")

	def html_login(self):
		self.wfile.write('<form name="login" method="post" action="account?do=login">')
		self.wfile.write('Login: <input type="text" size="40" name="login"><br>Password: <input name="pwd" type="password" size="40"><br>')
		self.wfile.write('<input type="submit" value="Login"></form><a href="register">Create an account</a>')

	def html_bad_login(self):
		self.send_response(200, 'OK')
		self.end_headers()
		self.html_block_start()
		self.wfile.write("Bad login/password.")
		self.html_end()

	def html_redirect(self, url):
		self.wfile.write('<html><head><meta http-equiv="refresh" content="1;url=' + url +'"><script type="text/javascript">')
		self.wfile.write('window.location.href = "' + url +'"</script></head></html>\n')

	def do_GET(self):
		if not self.headers['host'] == HOST:
			self.send_error(404, 'Nothing')
			return

		url = urlparse.urlparse(self.path)

		if url.path == '/':
			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			
			username = None
			cookie = None

			for h in self.headers:
				if h == 'cookie':
					cookie = self.headers['cookie']

			if cookie:
				cs = cookie.split(';')
				cookie = []
				for c in cs:
					cookie.append(c.strip())
				d = db['sessions'].find_one({'cookie': cookie[-1], 'open': True})
				if d:
					username = d['login']

			if username:
				self.wfile.write('good<br><a href="/logout">Log out</a>\n')
			else:
				self.html_login()

			self.html_block_end()
			self.html_end()

		elif url.path == '/register':
			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			
			q = urlparse.parse_qs(url.query)
			if 'error' in q:
				if int(q['error'][0]) == 0:
					self.wfile.write('<b>You have successfully created an account.</b><br><a href="/">Proceed</a>\n')
				else:
					self.wfile.write('<b>Failed to create an account.</b>\n')
					if 'message' in q:
						self.wfile.write('<br>Message: <i>' + q['message'][0] + '</i>\n')

			else:
				self.wfile.write('<form name="register" method="post" action="account?do=register">Create an account:<br>')
				self.wfile.write('Login: <input type="text" size="40" name="login"><br>Password: <input name="pwd" type="password" ')
				self.wfile.write('size="40"><br><input type="submit" value="Sign up"></form><h3>ACHTUNG! In this raw in-development version ')
				self.wfile.write('we store your passwords in plain text form, so do not use your regular passwords you already ')
				self.wfile.write('using on another web sites.</h3>')

			self.html_end()

		elif url.path == '/logout':
			self.send_response(200, 'OK')
			self.end_headers()
			if 'cookie' in self.headers:
				cookie = self.headers['cookie'].split(';')[-1].strip()
				db['sessions'].update({'cookie': cookie}, {'$set': {'open': False}})
				self.html_redirect('/')
			else:
				self.wfile.write('Huh?\n')

		else:
			self.send_error(404, 'Not Found')

	def do_POST(self):
		url = urlparse.urlparse(self.path)
		q = urlparse.parse_qs(url.query)
		if url.path == '/account':
			l = int(self.headers['content-length'])
			data = self.rfile.read(l)
			data = urlparse.parse_qs(data)
			if 'login' in data and 'pwd' in data:
				if q['do'][0] == 'login':
					acc = db.accounts.find_one({'login': data['login'][0], 'password': data['pwd'][0]})
					if acc:
						self.send_response(200, 'OK')
						cookie = base64.b64encode(urandom(32))
						self.send_header('Set-Cookie', cookie)
						db.sessions.insert({'cookie': cookie, 'open': True, 'created': datetime.now(), 'login': data['login'][0]})
						self.end_headers()
						self.html_redirect('/')
					else:
						self.html_bad_login()
				elif q['do'][0] == 'register':
					acc = db.accounts.find_one({'login': data['login'][0]})
					if acc:
						self.html_redirect('/register?error=1&message="Account ' + data['login'][0] + ' already exist."')
					else:
						db['accounts'].insert({'login': data['login'][0], 'password': data['pwd'][0]})
						self.html_redirect('/register?error=0')

				else:
					self.send_error(400, 'Bad Request')
			else:
				self.html_bad_login()
		else:
			self.send_error(404, 'Not Found')

if __name__ == '__main__':
	dbclient = pymongo.MongoClient(config['dbUri'])
	db = dbclient.funky
	try:
		httpd = SocketServer.TCPServer(("", PORT), FunkyHTTPRequestHandler)
		httpd.serve_forever()
	except KeyboardInterrupt:
		print('Interrupted.')
		httpd.socket.close()