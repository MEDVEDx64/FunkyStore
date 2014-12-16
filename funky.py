import BaseHTTPServer
import SocketServer
import pymongo
from config import config
import urlparse
from os import urandom
import base64
from datetime import datetime
import threading
import cookielib
import money
from time import sleep
import os

import mcrcon

PORT = config['port']
HOST = config['host']
# if not PORT == 80:
# HOST += ':' + str(PORT)
db = None


class FunkyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def html_start(self):
		self.wfile.write(
			'<html><head><title>Funky Trade</title><link rel="stylesheet" type="text/css" href="storage/style.css" /></head>')
		self.wfile.write('<body><center>\n')

	def html_end(self):
		self.wfile.write('</center></body></html>\n')

	def html_block_start(self):
		self.wfile.write("<div>\n")

	def html_block_end(self):
		self.wfile.write("</div>\n")

	def html_login(self):
		self.wfile.write('<form name="login" method="post" action="account?do=login">')
		self.wfile.write(
			'Login: <input type="text" size="40" name="login"><br>Password: <input name="pwd" type="password" size="40"><br>')
		self.wfile.write('<input type="submit" value="Login"></form><a href="register">Create an account</a>')

	def html_bad_login(self):
		self.html_redirect('/message?m=Invalid%20login')

	def html_redirect(self, url):
		self.wfile.write(
			'<html><head><meta http-equiv="refresh" content="1;url=' + url + '"><script type="text/javascript">')
		self.wfile.write('window.location.href = "' + url + '"</script></head></html>\n')

	def html_main_menu(self, user='__WHO__'):
		self.wfile.write('<a href="/">Home</a> <a href="/money">Transfer</a> <a href="/money?action=list">History</a> ' \
						 + '<a href="/settings">Settings</a>')
		if user_is_admin(user):
			self.wfile.write(' <a style="color: #fba" href="/admin">Admin</a>')
		self.wfile.write('<hr>\n')

	def html_generic(self, username=None):
		self.wfile.write('<img style="margin: 8px" src="storage/funky.png"></img><br>\n')

		u = username
		if not u:
			if 'cookie' in self.headers:
				u = get_user_by_cookie(self.headers['cookie'])

		if not u:
			self.wfile.write('<i>Welcome, Stranger!</i>\n')
			return

		self.wfile.write('<b>Account</b>: ' + u + ', <b>Balance:</b> ' + str(money.get_balance(db, u)) + 'f\n')
		self.wfile.write(' (<a href="/logout">Logout</a>)<hr>\n')
		self.html_main_menu(u)

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
				is_admin = user_is_admin(username)
				query = {'in_stock': True}
				if is_admin:
					query = {}
				for i in db['items'].find(query):
					self.html_block_start()
					self.wfile.write('<form name="buy" style="margin: 0" method="post" action="buy?itemid=' + str(
						i['item_id']) + '">')
					self.wfile.write(
						i['text'] + ' &ndash; <b>' + str(i['price']) + 'f</b> &ndash; <input type="text" size="4"')
					self.wfile.write('name="amount" value="1"> <input type="submit" value="Buy"></form>\n')
					if is_admin:
						in_stock = ''
						if i['in_stock']:
							in_stock = 'checked="checked"'
						self.wfile.write('<form name="item-update" style="margin: 4px" method="post" ' \
										 + 'action="item?do=update&itemid=' + i['item_id'] + '">' \
										 + 'text <input type="text" size="32" name="text">' \
										 + ' price <input type="text" size="4" name="price" value="' + str(
							i['price']) + '">' \
										 + ' in stock <input type="checkbox" name="in_stock" ' + in_stock + '>' \
										 + ' <input type="submit" value="Update"></form><x style="color: #335">[' + i[
											 'item_id'] + ']</x>' \
										 + ' <a href="/item?do=delete&itemid=' + i['item_id'] \
										 + '" style="color: #e44" method="post">Delete</a>\n')
					self.html_block_end()

				if is_admin:
					self.html_block_start()
					self.wfile.write('<form name="item-insert" style="margin: 0" method="post" ' \
									 + 'action="item?do=insert">' \
									 + 'item_id[ data] <input type="text" size="24" name="itemid">' \
									 + ' text <input type="text" size="32" name="text">' \
									 + ' price <input type="text" size="4" name="price">' \
									 + ' in stock <input type="checkbox" name="in_stock" checked="true">' \
									 + ' <input type="submit" value="Add"></form>\n')
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
					PAGESIZE = 250
					self.html_block_start()
					self.wfile.write('Transactions:<div class="code_list">\n')
					page = 0
					if 'page' in q:
						page = int(q['page'][0])
					c = db['transactions'].find({'$or': [{'source': u}, {'destination': u}]}).sort('timestamp', -1) \
						.skip(page * PAGESIZE).limit(PAGESIZE)

					for d in c:
						self.wfile.write('<b>' + str(d['amount']) + 'f</b> from <b>' + d['source'] + '</b> to <b>')
						self.wfile.write(d['destination'] + '</b> at <i>' + str(d['timestamp']) + '</i><br>\n')
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
				self.wfile.write(
					'<form name="register" method="post" action="account?do=register">Create an account:<br>')
				self.wfile.write(
					'Login: <input type="text" size="40" name="login"><br>Nickname: <input type="text" size="40" ')
				self.wfile.write('name="nickname"><br>Password: <input name="pwd" type="password" ')
				self.wfile.write(
					'size="40"><br><input type="submit" value="Sign up"></form><h3>ACHTUNG! In this raw in-development version ')
				self.wfile.write(
					'we store your passwords in plain text form, so do not use your regular passwords you already ')
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

		elif url.path == '/item':
			q = urlparse.parse_qs(url.query)
			if 'do' in q and q['do'][0] == 'delete':
				if 'itemid' in q:
					db['items'].remove({'item_id': q['itemid'][0]})
					self.html_redirect('/')
				else:
					self.html_redirect('/message?m=No item ID specified')
			else:
				self.send_error(400, 'Bad Request')

		elif url.path == '/settings':
			username = self.get_user_by_cookie()
			if not username:
				self.send_error(404, 'Not Found')
				return

			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic()

			nick = db['accounts'].find_one({'login': username}, {'nickname': 1})
			if not nick:
				nick = 'Steve?'
			self.wfile.write('<form name="settings" method="post" action="settings">')
			self.wfile.write('Nickname: <input type="text" size="32" value="' + nick['nickname'] + '" name="nickname"><br>')
			self.wfile.write('<input type="submit" value="Submit"></form>\n')

			self.html_end()

		elif url.path == '/admin':
			username = self.get_user_by_cookie()
			if not user_is_admin(username):
				self.send_error(404, 'Not Found')
				return

			q = urlparse.parse_qs(url.query)

			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic(username)

			if 'go' in q:
				if q['go'][0] == 'accounts':
					login = None
					if 'login' in q:
						login = q['login'][0]
					if not login:
						login = ''

					self.wfile.write('<h2>Account Editor</h2>')
					self.html_block_start()
					self.wfile.write('<form style="margin: 4px" name="admin_edit_account" method="post" ' \
									+ 'action="admin?do=account_editor_redirect">Login: <input type="text" size="40" '
									+ 'name="login" value="' + login + '"> <input type="submit" value="Select"></form>\n')
					self.html_block_end()

					if len(login) > 0:
						if 'action' in q:
							if q['action'][0] == 'create':
								if not db['accounts'].find_one({'login': login}):
									db['accounts'].insert({'login': login, 'password': 'password', 'money': 0.0,
										'locked': True, 'nickname': 'Steve', 'flags': ['money_recv', 'money_send']})
							elif q['action'][0] == 'delete':
								db['accounts'].remove({'login': login})

						self.html_block_start()
						acc = db['accounts'].find_one({'login': login})
						if acc:
							checked = ''
							if acc['locked']:
								checked = 'checked="checked"'
							flags = ''
							for f in acc['flags']:
								flags += ' ' + f
							flags = flags.strip()
							self.wfile.write('<a href="/admin?go=accounts&action=delete&login=' + acc['login']
											 + '" style="color: #e44">Delete</a>')
							self.wfile.write('<br><form name="edit_account" method="post" action="/admin'
								+ '?go=accounts&action=update&login=' + acc['login'] + '">'
								+ 'Nickname: <input name="nickname" type="text" size="32" value="'
								+ acc['nickname'] + '"><br>New password: <input type="password" size="24"'
								+ 'name="password"><br>Locked: <input type="checkbox" ' + checked + ' name="locked">'
								+ '<br>Money: <input type+"text" name="money" size="16" value="' + str(acc['money']) + '">'
								+ '<br>Flags (space-separated): <input type="text" size="50" name="flags" value="'
								+ flags + '"><br><input type="submit" value="Update"></form>\n')
						else:
							self.wfile.write('<a href="/admin?go=accounts&action=create&login=' + login
									+ '" style="color: #76a">Create</a>\n')

						self.html_block_end()

				else:
					self.wfile.write('No such console (or not yet implemented).\n')

			else:
				self.wfile.write('<h2>The Admin Console</h2><a href="/admin?go=accounts">Account Editor</a><br>')
				self.wfile.write('<a href="/admin?go=transactions">All Transactions</a><br>')
				self.wfile.write('<a href="/admin?go=bought">Who Bought What</a>\n')

			self.html_end()

		else:
			self.send_error(404, 'Not Found')

	def do_POST(self):
		missing_data_url = '/message?m=Missing some required fields, make sure you filled the form correctly.'
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
						db.sessions.insert(
							{'cookie': cookie, 'open': True, 'created': datetime.now(), 'login': data['login'][0]})
						self.end_headers()
						self.html_redirect('/')
					else:
						self.html_bad_login()
				elif q['do'][0] == 'register':
					if not 'nickname' in data or data['login'][0][0:2] == '__':
						self.html_redirect(missing_data_url)
						return
					acc = db.accounts.find_one({'login': data['login'][0]})
					if acc:
						self.html_redirect('/register?error=1&message=Account ' + data['login'][0] + ' already exist.')
					else:
						db['accounts'].insert({'login': data['login'][0], 'password': data['pwd'][0], 'money': 0.0, \
											   'locked': False, 'nickname': data['nickname'][0],
											   'flags': ['money_recv', 'money_send']})
						self.html_redirect('/register?error=0')

				else:
					self.send_error(400, 'Bad Request')
			else:
				if q['do'][0] == 'login':
					self.html_bad_login()
				else:
					self.html_redirect(missing_data_url)

		elif url.path == '/transfer':
			self.send_response(200, 'OK')
			self.end_headers()
			if not 'cookie' in self.headers:
				self.html_redirect('/message?m=Not logged in.\n')
				return

			data, l = self.get_post_data()
			if not 'destination' in data or not 'amount' in data:
				self.html_redirect(missing_data_url)
				return

			ok, msg = money.transfer(db, get_user_by_cookie(self.headers['cookie']), data['destination'][0],
									 float(data['amount'][0]))
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

					if amount > 0 and amount < 64:  # WARNING: high values may knock MC server out (minecraft bug?)
						d = db['items'].find_one({'item_id': itemid}, {'price': 1})
						if d:
							bank_user = '__BANK__'
							if not db['accounts'].find_one({'login': bank_user}):
								db['accounts'].insert({'login': bank_user, 'money': 0.0, 'password': '0',
													   'locked': True, 'flags': ['money_recv', 'system']})
							ok, message = money.transfer(db, u, bank_user, d['price'] * amount)
							if ok:
								item = itemid
								data = '0'
								if ' ' in itemid:
									s = itemid.strip().split(' ')
									item = s[0]
									data = s[1]
								ItemSender(nick, item, amount, data).start()
								db['sold'].insert({'who': nick, 'what': itemid, 'when': datetime.now(),
												   'amount': amount, 'price': d['price']})
							self.html_redirect('/message?m=' + message)
						else:
							self.html_redirect('/message?m=No%20such%20item')
					else:
						self.html_redirect('/message?m=Invalid%20amount')
				else:
					self.html_redirect('/message?m=Item%20not%20specified')
			else:
				self.html_redirect('/message?m=Who%20Are%20You%3F')

		elif url.path == '/item':
			u = None
			if 'cookie' in self.headers:
				u = get_user_by_cookie(self.headers['cookie'])
			if not u or not user_is_admin(u):
				self.send_error(404, 'Not Found')
				return

			data, l = self.get_post_data()
			if 'do' in q:
				in_stock = False
				if 'in_stock' in data and data['in_stock'][0] == 'on':
					in_stock = True

				if q['do'][0] == 'insert':
					try:
						db['items'].insert(
							{'item_id': data['itemid'][0], 'text': data['text'][0], 'price': float(data['price'][0]), \
							 'in_stock': in_stock})
						self.html_redirect('/')
					except (KeyError, TypeError):
						self.html_redirect(missing_data_url)

				elif q['do'][0] == 'update':
					set_query = {'in_stock': in_stock}
					if 'text' in data:
						set_query['text'] = data['text'][0]
					if 'text' in data:
						set_query['price'] = float(data['price'][0])
					if 'itemid' in q:
						db['items'].update({'item_id': q['itemid'][0]}, {'$set': set_query})
						self.html_redirect('/')
					else:
						self.html_redirect('/message?m=No item ID specified')

				else:
					self.send_error(400, 'Bad Request')

		elif url.path == '/settings':
			username = self.get_user_by_cookie()
			if not username:
				self.send_error(404, 'Not Found')
				return

			data, l = self.get_post_data()
			if 'nickname' in data:
				db['accounts'].update({'login': username}, {'$set': {'nickname': data['nickname'][0]}})
				self.html_redirect('/message?m=Success')

		elif url.path == '/admin':
			username = self.get_user_by_cookie()
			if not user_is_admin(username):
				self.send_error(404, 'Not Found')
				return

			data, l = self.get_post_data()
			if 'do' in url.query and q['do'][0] == 'account_editor_redirect':
				if 'login' in data:
					self.html_redirect('/admin?go=accounts&login=' + data['login'][0])
				else:
					self.html_redirect('/admin?go=accounts')
			elif 'go' in q and q['go'][0] == 'accounts' and 'action' in q \
				and q['action'][0] == 'update' and 'login' in q:
					d = {'nickname': data['nickname'][0], 'money': float(data['money'][0]),
						 'flags': data['flags'][0].strip().split(' '), 'locked': False}
					if 'locked' in data and data['locked'][0] == 'on':
						d['locked'] = True
					if 'password' in data:
						d['password'] = data['password'][0]
					db['accounts'].update({'login': q['login'][0]}, {'$set': d})
					self.html_redirect('/admin?go=accounts&login=' + q['login'][0])
			else:
				self.send_error(400, 'Bad Request')

		else:
			self.send_error(404, 'Not Found')

	def get_post_data(self):
		l = int(self.headers['content-length'])
		data = self.rfile.read(l)
		data = urlparse.parse_qs(data)
		return (data, l)

	def get_user_by_cookie(self):
		cookie = None
		if 'cookie' in self.headers:
			cookie = self.headers['cookie']
		username = get_user_by_cookie(cookie)
		return username


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


def user_is_admin(username):
	try:
		if 'admin' in (db['accounts'].find_one({'login': username}, {'flags': 1}))['flags']:
			return True
	except (KeyError, TypeError):
		pass
	return False


def get_rcon():
	return mcrcon.MCRcon(rcfg['host'], rcfg['port'], rcfg['password'])


class DetachedRconExecutor(threading.Thread):
	def __init__(self):
		super(DetachedRconExecutor, self).__init__()
		self.rcon = get_rcon()

	def execute(self):
		pass

	def run(self):
		try:
			self.execute()
		finally:
			self.rcon.close()


class ItemSender(DetachedRconExecutor):
	def __init__(self, nick, item_id, amount=1, data=0):
		super(ItemSender, self).__init__()
		self.nick = nick
		self.item_id = item_id
		self.amount = amount
		self.data = data

	def execute(self):
		amount_left = self.amount
		while amount_left > 0:
			c = 64
			if amount_left < 64:
				c = amount_left
			amount_left -= c
			self.rcon.send('give ' + self.nick + ' ' + self.item_id + ' ' + str(c) + ' ' + self.data)
			sleep(0.25)


if __name__ == '__main__':
	dbclient = pymongo.MongoClient(config['dbUri'])
	db = dbclient.funky
	rcfg = config['rconServer']
	try:
		httpd = SocketServer.TCPServer(("", PORT), FunkyHTTPRequestHandler)
		httpd.serve_forever()
	except KeyboardInterrupt:
		print('Interrupted.')
		httpd.socket.close()
