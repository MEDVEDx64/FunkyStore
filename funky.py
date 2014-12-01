import BaseHTTPServer
import SocketServer
import pymongo
from config import config
import urlparse
from os import urandom
import base64
from datetime import datetime
import cookielib
import money
import os

import mcrcon

PORT = config['port']
HOST = config['host']
#if not PORT == 80:
#	HOST += ':' + str(PORT)
db = None
rcon = None

class FunkyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def html_start(self):
		self.wfile.write('<html><head><title>Funky Trade</title><link rel="stylesheet" type="text/css" href="storage/style.css" /></head>')
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
		self.html_redirect('/message?m=Invalid%20login')

	def html_redirect(self, url):
		self.wfile.write('<html><head><meta http-equiv="refresh" content="1;url=' + url +'"><script type="text/javascript">')
		self.wfile.write('window.location.href = "' + url +'"</script></head></html>\n')

	def html_main_menu(self):
		self.wfile.write('<a href="/">Home</a> <a href="/money">Transfer</a> <a href="/money?action=list">History</a><hr>\n')

	def html_generic(self, username = None):
		u = username
		if not u:
			if 'cookie' in self.headers:
				u = get_user_by_cookie(self.headers['cookie'])

		if not u:
			self.wfile.write('<i>Welcome, Stranger!</i>\n')
			return

		self.wfile.write('<b>Account</b>: ' + u +', <b>Balance:</b> ' + str(money.get_balance(db, u)) + '\n')
		self.wfile.write(' (<a href="/logout">Logout</a>)<hr>\n')
		self.html_main_menu()

	def do_GET(self):
		if not self.headers['host'] == HOST:
			self.send_error(404, 'Nothing')
			return

		url = urlparse.urlparse(self.path)

		if url.path.startswith('/storage'):
			p = url.path[1:]
			if '/..' in p or '\\..' in p:
				self.send_error(400, 'WTF')
				return

			if os.path.exists(p) and os.path.isfile(p):
				self.send_response(200, 'OK')
				self.end_headers()
				self.wfile.write(open(p, 'rb').read())
			else:
				self.send_error(404, 'Not Found')

		elif url.path == '/':
			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			
			username = None
			cookie = None

			for h in self.headers:
				if h == 'cookie':
					cookie = self.headers['cookie']

			username = get_user_by_cookie(cookie)
			self.html_generic(username)
			if username:
				for i in db['items'].find({'in_stock': True}):
					self.html_block_start()
					self.wfile.write('<form name="buy" style="margin: 0" method="post" action="buy?itemid=' + str(i['item_id']) + '">')
					self.wfile.write(i['text'] + ' &ndash; <b>' + str(i['price']) + 'f</b> &ndash; <input type="text" size="4"')
					self.wfile.write('name="amount" value="1"> <input type="submit" value="Buy"></form>\n')
					self.html_block_end()

			else:
				self.html_login()

			self.html_block_end()
			self.html_end()

		elif url.path == '/message':
			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()

			q = urlparse.parse_qs(url.query)
			if 'm' in q:
				self.wfile.write(q['m'][0])
			else:
				self.wfile.write('Nothing!')

			self.wfile.write('<p><a href="javascript:history.back()">Back</a> | <a href="/">Home</a></p>')
			self.html_end()

		elif url.path == '/money':
			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic()

			if not 'cookie' in self.headers:
				self.html_redirect('/')
				self.html_end()
				return

			u = None
			if 'cookie' in self.headers:
				u = get_user_by_cookie(self.headers['cookie'])
			if not u:
				self.html_redirect('/')
				self.html_end()
				return

			q = urlparse.parse_qs(url.query)
			if 'action' in q:
				if q['action'][0] == 'list':
					PAGESIZE = 50
					self.html_block_start()
					self.wfile.write('Transactions:<div class="code_list">\n')
					page = 0
					if 'page' in q:
						page = int(q['page'][0])
					c = db['transactions'].find({'$or': [{'source': u}, {'destination': u}]}).sort('timestamp', -1) \
						.skip(page*PAGESIZE).limit(PAGESIZE)

					for d in c:
						self.wfile.write('<b>From</b> ' + d['source'] + ' <b>to</b> ' + d['destination'] + ' <b>transfered</b> ')
						self.wfile.write(str(d['amount']) + ' Funks at ' + str(d['timestamp']) + '<br>\n')
					self.wfile.write('</div>\n')

				self.html_block_end()

			else:
				self.wfile.write('Transfer some Funks to another account\n')
				self.wfile.write('<form name="transfer" method="post" action="transfer">')
				self.wfile.write('Target account: <input type="text" size="60" name="destination">')
				self.wfile.write('<br>Amount: <input name="amount" type="text" size="20"><br>')
				self.wfile.write('<input type="submit" value="Transfer"></form>\n')

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
				self.wfile.write('Login: <input type="text" size="40" name="login"><br>Nickname: <input type="text" size="40" ')
				self.wfile.write('name="nickname"><br>Password: <input name="pwd" type="password" ')
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
			data, l = self.get_post_data()
			if 'login' in data and 'pwd' in data:
				if q['do'][0] == 'login':
					acc = db.accounts.find_one({'login': data['login'][0], 'password': data['pwd'][0], 'locked': False})
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
						self.html_redirect('/register?error=1&message=Account ' + data['login'][0] + ' already exist.')
					else:
						db['accounts'].insert({'login': data['login'][0], 'password': data['pwd'][0], 'money': 0.0, \
							'locked': False, 'nickname': data['nickname'][0], 'flags': ['money_recv', 'money_send']})
						self.html_redirect('/register?error=0')

				else:
					self.send_error(400, 'Bad Request')
			else:
				self.html_bad_login()

		elif url.path == '/transfer':
			self.send_response(200, 'OK')
			self.end_headers()
			if not 'cookie' in self.headers:
				self.wfile.write('Not logged in.\n')
				return

			data, l = self.get_post_data()
			ok, msg = money.transfer(db, get_user_by_cookie(self.headers['cookie']), data['destination'][0], float(data['amount'][0]))
			self.html_redirect('/message?m=' + msg)

		elif url.path == '/buy':
			u = None
			if 'cookie' in self.headers:
				u = get_user_by_cookie(self.headers['cookie'])

			if u:
				nick = u
				nd = db['accounts'].find_one({'login': u}, {'nickname': 1})
				if nd:
					nick = nd['nickname']

				if 'itemid' in q:
					itemid = q['itemid'][0]
					data, l = self.get_post_data()
					amount = 1
					if 'amount' in data:
						amount = int(data['amount'][0])

					if amount > 0 and amount < 65:
						d = db['items'].find_one({'item_id': itemid}, {'price': 1})
						if d:
							if not db['accounts'].find_one({'login': '__OM_NOM_NOM'}):
								db['accounts'].insert({'login': '__OM_NOM_NOM', 'money': 0.0, 'password': '0', \
									'locked': True, 'flags': ['money_recv']})
							ok, message = money.transfer(db, u, '__OM_NOM_NOM', d['price']*amount)
							if ok:
								rcon.send('give ' + nick + ' ' + itemid + ' ' + str(amount))
							self.html_redirect('/message?m=' + message)
						else:
							self.html_redirect('/message?m=Item%20not%20found')
					else:
						self.html_redirect('/message?m=Invalid%20amount')
				else:
					self.html_redirect('/message?m=Item%20not%20specified')
			else:
				self.html_redirect('/message?m=Who%20Are%20You%3F')

		else:
			self.send_error(404, 'Not Found')

	def get_post_data(self):
		l = int(self.headers['content-length'])
		data = self.rfile.read(l)
		data = urlparse.parse_qs(data)
		return (data, l)

def get_user_by_cookie(cookie):
	if cookie:
		cs = cookie.split(';')
		cookie = []
		for c in cs:
			cookie.append(c.strip())
		d = db['sessions'].find_one({'cookie': cookie[-1], 'open': True})
		if d:
			return d['login']

	return None

if __name__ == '__main__':
	dbclient = pymongo.MongoClient(config['dbUri'])
	db = dbclient.funky
	rcfg = config['rconServer']
	rcon = mcrcon.MCRcon(rcfg['host'], rcfg['port'], rcfg['password'])
	try:
		httpd = SocketServer.TCPServer(("", PORT), FunkyHTTPRequestHandler)
		httpd.serve_forever()
	except KeyboardInterrupt:
		print('Interrupted.')
		rcon.close()
		httpd.socket.close()
