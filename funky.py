#!/usr/bin/env python2.7

import BaseHTTPServer
import SocketServer
import pymongo
from config import config
import urlparse
import urllib
from os import urandom
import random as rnd
import base64
import hashlib
from datetime import datetime
from driver import default_driver
from time import sleep
import money
import magic
import subprocess
import binascii
import rcon
import cgi
import os

PORT = config['port']
HOST = config['host']
# if not PORT == 80:
# HOST += ':' + str(PORT)
db = None

COPY = '2014-2022 MEDVEDx64. Thanks to dmitro and AlexX.'

class FunkyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def html_start(self):
		self.wfile.write(
			'<html><head><title>Funky Store</title><link rel="stylesheet" type="text/css" href="storage/style.css" />'
			+ '<meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head>')
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
			'<table><tr><td>Username:</td><td><input type="text" size="24" name="login"></td></tr>'
			+ '<tr><td>Password:</td><td><input name="pwd" type="password" size="24"></td></tr></table>')
		self.wfile.write('<input type="submit" value="Login"></form><a href="register">Create an account</a>')

	def html_bad_login(self):
		self.html_redirect('/message?m=Invalid%20login')

	def html_redirect(self, url):
		self.wfile.write(
			'<html><head><meta http-equiv="refresh" content="1;url=' + url + '"><script type="text/javascript">')
		self.wfile.write('window.location.href = "' + url + '"</script></head></html>\n')

	def html_main_menu(self, user='__WHO__'):
		mining = ""
		if 'mining' in config and config['mining']['enabled']:
			mining = '<a href="/mining">Mining</a> '

		self.wfile.write('<a href="/">Home</a> <a href="/print">Print</a> '
						+ '<a href="/money">Transfer</a> <a href="/sell">Sell</a> '
						+ '<a href="/magic">Redeem a code</a> '
						+ '<a href="/vouchers">My Vouchers</a> ' + mining
						+ '<a href="/money?action=list">History</a> '
						+ '<a href="/settings">Settings</a>')
		if user_is_admin(user):
			self.wfile.write(' <a style="color: #fba" href="/admin">Admin</a>')
		self.wfile.write('<hr>\n')

	def html_generic(self, username = None, url_query = None):
		u = username
		if not u:
			if 'cookie' in self.headers:
				u = get_user_by_cookie(self.headers['cookie'])

		self.wfile.write('<a href="/"><img style="margin: 8px" src="storage/funky.png"></img></a><br>\n'
			+ '<i style="font-size: 7pt">Funky Store &copy; ' + COPY + '<br>\n')
		if u:
			motd = db['motd'].find().sort('timestamp', -1).limit(1)
			if motd.count():
				motd = motd.next()
				if 'text' in motd:
					self.wfile.write('<b>' + motd['text'] + '</b><br>\n')
		self.wfile.write('</i>\n')

		if not u:
			self.wfile.write('<i>Welcome, Stranger!</i>\n')
			return

		self.wfile.write('<b>Account</b>: ' + u + ', <b>Balance:</b> ' + money.get_str(money.get_balance(db, u)) + 'f\n')
		self.wfile.write(' (<a href="/logout">Logout</a>) | ')

		if 'mining' in config and config['mining']['enabled'] and config['mining']['allowDynamicReward']:
			value = magic.compute_reward(db) # ensure to use the actual values
			tail = []
			for x in db.reward.find().sort('timestamp', -1).limit(2):
				tail.append(x['value'])

			self.wfile.write('&#x2692; ' + money.get_str(value) + 'f')
			last = config['mining']['reward']
			if len(tail) == 2:
				last = tail[1]
			if len(tail) > 0:
				if tail[0] > last:
					self.wfile.write(' <x style="color: #2f2">&#x25CF;</x>')
				elif tail[0] < last:
					self.wfile.write(' <x style="color: #f22">&#x25CF</x>')

			self.wfile.write(' | ')

		self.wfile.write('<a style="color: #ef8" href="/get-to-the-kernel"<a>Get to the Kernel!</a><hr>\n')
		self.html_main_menu(u)

		if url_query:
			q = urlparse.parse_qs(url_query)
			if 'm' in q:
				self.wfile.write('<div style="background-color: #e82"><b>' + q['m'][0] + '</b></div><hr>\n')

	def do_GET(self):
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
			is_sold_items_hidden = False

			for h in self.headers:
				if h == 'cookie':
					cookie = self.headers['cookie']

			username = get_user_by_cookie(cookie)
			self.html_generic(username, url.query)
			if username:
				self.wfile.write('Buy a voucher: <form name="cashout" method="post" action="cashout">'
				+ '<input type="text" size="8" name="amount" value="0.0"> '
				+ '<input type="submit" value="Submit"></form>')
				self.wfile.write("<h5><b style=\"color: #e11\">Warning:</b> "
					+ "your order won't be delivered, unless you're in game! (this doesn't affect vouchers above)</h5>")
				is_admin = user_is_admin(username)
				query = {'in_stock': True}
				if is_admin:
					query = {}
				for i in db['items'].find(query).sort('timestamp', 1):
					userobj = db['accounts'].find_one({'login': username})
					if not is_admin and 'hide_sold' in userobj and userobj['hide_sold'] and 'left' in i and i['left'] == 0:
						is_sold_items_hidden = True
						# Skipping sold stuff
						continue
					self.html_block_start()
					# modified buy form
					self.wfile.write('<form name="buy" style="margin: 0" method="post" action="buy?itemid=' + str(
						i['item_id']) + '">')
					self.wfile.write('<div class="inner inner-item-name">' + i['text'])
					if 'left' in i:
						self.wfile.write(' <x style="')
						if i['left'] <= 0:
							self.wfile.write('color: #f11; ')
						self.wfile.write('font-size: 9pt">(' + str(i['left']) + ')</x>')
					price = 'Free'
					if i['price']:
						price = str(i['price']) + 'f'
					self.wfile.write(' &ndash; <b>' + price + '</b></div>')
					self.wfile.write('<div class="inner inner-inputs"><input type="text" size="4"'
						+ 'name="amount" value="1"> <input type="submit" value="Buy"></div></form>\n')
					if is_admin:
						in_stock = ''
						if i['in_stock']:
							in_stock = 'checked="checked"'
						restock = ''
						if 'restock' in i and i['restock']:
							restock = 'checked="checked"'
						left = ''
						if 'left' in i:
							left = str(i['left'])
						text = i['text'].replace('"', '&#34;')
						self.wfile.write('<form name="item-update" style="margin: 4px" method="post" ' \
										 + 'action="item?do=update&itemid=' + i['item_id'] + '">' \
										 + 'text <input type="text" size="50" name="text" value="' + text + '">' \
										 + ' price <input type="text" size="8" name="price" value="' + str(
											i['price']) + '">' \
										 + ' left <input type="text" name="left" size="6" value="' + left +'">'
										 + ' in stock <input type="checkbox" name="in_stock" ' + in_stock + '>' \
										 + ' restock <input type="checkbox" name="restock" ' + restock + '>' \
										 + ' <input type="submit" value="Update"></form><x style="color: #335">[' + i[
											 'item_id'] + ']</x>' \
										 + ' <a href="/item?do=delete&itemid=' + i['item_id'] \
										 + '" style="color: #e44" method="post">Delete</a>\n')
					self.html_block_end()

				if is_admin:
					self.html_block_start()
					self.wfile.write('<form name="item-insert" style="margin: 0" method="post" ' \
									 + 'action="item?do=insert">' \
									 + 'item_id <input type="text" size="24" name="itemid">' \
									 + ' text <input type="text" size="32" name="text">' \
									 + ' price <input type="text" size="8" name="price">' \
									 + ' left <input type="text" name="left" size="6">'
									 + ' in stock <input type="checkbox" name="in_stock" checked="true">' \
									 + ' restock <input type="checkbox" name="restock">' \
									 + ' <input type="submit" value="Add"></form>\n')
					self.html_block_end()

			else:
				self.html_login()

			self.html_block_end()
			if is_sold_items_hidden:
				self.html_block_start()
				self.wfile.write('<i style="font-size: 10pt">Some sold-out item entries are not shown, '
					+ 'check your <a style="color: #436" href="/settings">settings</a> if you want to see them.</i>')
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
			self.html_generic(url_query = url.query)

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

			self.html_end()

		elif url.path == '/sell':
			username = self.get_user_by_cookie()
			if not username:
				self.html_redirect('/')
				return

			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic(url_query = url.query)

			self.wfile.write('<b><i>The marketplaces allows you to sell blocks. Visit one of the marketplaces'
				+ ' listed below and place your blocks on markers (usually made of Dark Prismarine),'
				+ " then get back to this page and click the marketplace's title link.</i></b><hr>")
			has_markets = False

			q = urlparse.parse_qs(url.query)
			if 'market' in q:
				# Sell ban is disabled just because it is useless (user can freely register and sell things again).
				# Uncomment lines below if you really need this feature.

				#if 'sell_banned' in db['accounts'].find_one({'login': username}, {'flags': 1})['flags']:
				#	self.html_redirect('/message?m=You have been banned from selling items on markets.')
				#	self.html_end()
				#	return

				reward = 0.0
				r = rcon.get_rcon()
				m = db['markets'].find_one({'short_name': q['market'][0]})
				for c in m['blocks']:
					b = str(int(c[0])) + ' ' + str(int(c[1])) + ' ' + str(int(c[2]))
					for name in m['accept']:
						resp = r.command('execute if block ' + b + ' ' + m['accept'][name]['itemid'] + ' run summon minecraft:experience_orb ' + b)
						if resp and resp.startswith('Summoned'):
							if 'reward_low' in m['accept'][name]:
								rnd.seed()
								reward += round(rnd.random() * (m['accept'][name]['reward']
									- m['accept'][name]['reward_low']) + m['accept'][name]['reward_low'], 2)
							else:
								reward += m['accept'][name]['reward']
							r.command('setblock ' + b + ' air')
							db['deals'].insert({'short_name': m['short_name'], 'block': name,
								'who': username, 'reward': m['accept'][name]['reward'], 'when': datetime.now()})

							if 'restock_id' in m['accept'][name]:
								restock_item = db['items'].find_one({'restock': True,
									'item_id': m['accept'][name]['restock_id'], 'left': {'$exists': True}})
								if restock_item:
									db['items'].update({'_id': restock_item['_id']},
										{'$set': {'left': int(restock_item['left'] + m['accept'][name]['restock_mul'])}})

							sleep(0.25)
							break

				if reward > 0:
					money.transfer(db, '__RESERVE__', username, reward)
				self.html_redirect('/sell?m=You have earned ' + str(reward) + ' funks.')

			markets = db['markets'].find().sort('text', 1)
			for e in markets:
				if 'disabled' in e and e['disabled']:
					continue

				if not has_markets: has_markets = True
				self.html_block_start()
				self.wfile.write('<a style="color: #123" href="/sell?market=' + e['short_name'] + '">')
				self.wfile.write(e['text'].encode('utf-8'))
				self.wfile.write('</a>')
				if 'xcoord' in e and 'zcoord' in e and 'markets' in config:
					self.wfile.write('&nbsp;<a href="' + config['markets']['googleMapUri'] + '#/' + str(int(e['xcoord'])) + '/64/' + str(int(e['zcoord']))
						+ '/max/' + config['markets']['googleMapLayerName'] + '/0"><img src="/storage/items/map.png" width="16px"></a>')
				self.wfile.write('<br><x style="font-size: 8pt">')
				self.wfile.write('<i>' + str(len(e['blocks'])) + ' slots available</i><br>')
				for a in e['accept']:
					big = e['accept'][a]['reward'] >= 1000.0
					if big: self.wfile.write('<b>')
					if 'reward_low' in e['accept'][a]:
						self.wfile.write(a + ' <b style="color: #438">(from ' + str(e['accept'][a]['reward_low'])
							+ 'f to ' + str(e['accept'][a]['reward']) + 'f)</b>')
					else:
						self.wfile.write(a + ' (' + str(e['accept'][a]['reward']) + 'f)')
					if big: self.wfile.write('</b>')
					self.wfile.write('<br>')
				self.wfile.write('</x>')
				self.html_block_end()

			if not has_markets:
				self.wfile.write('<h4>No marketplaces available.</h4>')

			self.html_end()

		elif url.path == '/mining':
			if not self.get_user_by_cookie():
				self.html_redirect('/')
				return

			if not 'mining' in config or not config['mining']['enabled']:
				self.send_error(404, 'Not Found')
				return

			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic()

			self.wfile.write('Mining allows users to generate voucher codes by performing computation work, '
				+ 'just like Bitcoin does, but much more simple. Refer to <a href="https://github.com/MEDVEDx64/FunkyMiner">'
				+ 'FunkyMiner</a> software.')
			self.wfile.write('<div style="width: 20%; margin: 4px"><div class="code_list"><center>'
				+ '<b>This store instance code is:</b><br>'
				+ '<x style="font-size: 22pt; color: white">' + config['mining']['instanceCode'] + '</x><br>'
				+ 'Current reward is ' + money.get_str(magic.compute_reward(db)) + ' funks.</center></div></div>')

			self.html_end()

		elif url.path == '/vouchers':
			username = self.get_user_by_cookie()
			if not username:
				self.html_redirect('/')
				return

			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic()

			self.html_block_start()
			self.wfile.write("<h4>Your voucher codes goes here, feel free to give 'em to anybody you want. "
				+ 'Once a code is being used by someone, it disappears from this list.</h4>'
				+ '<div class="code_list"><center><table style="border-spacing: 40px 0">')
			has_codes = False
			for c in db[magic.COLLECTION_NAME].find({'owner': username, 'left': {'$ne': 0}}).sort('value'):
				has_codes = True
				self.wfile.write('<tr><td><b>' + magic.build_code(c['head'], c['ident'], c['data'])
					+ '</b></td><td><i style="color: #889">' + str(c['value']) + 'f</i></td></tr>\n')

			if not has_codes:
				self.wfile.write("You didn't bought any vouchers yet.")
			self.wfile.write('</table></center></div>')
			self.html_block_end()
			self.html_end()

		elif url.path == '/print':
			username = self.get_user_by_cookie()
			if not username:
				self.html_redirect('/')
				return

			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic()

			u = db['accounts'].find_one({'login': username})
			if not 'print' in u['flags']:
				self.wfile.write('You have no permissions to print schematics.\n')
				self.html_end()
				return

			self.wfile.write('Schematic printer<form action="print" method="post" enctype="multipart/form-data">'
				+ 'X: <input name="x" type="text" size="6"><br>'
				+ 'Y: <input name="y" type="text" size="6"><br>'
				+ 'Z: <input name="z" type="text" size="6"><br>'
				+ 'Schematic file: <input type="file" name="schematic" id="schematic"> '
				+ '<input type="submit" value="Upload"></form>\n')

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
				self.wfile.write('<form name="register" method="post" action="account?do=register"><h2>Create an account:</h2>'
					+'<table><tr><td>Username:</td><td><input type="text" size="24" name="login"></td></tr><tr><td>Nickname:</td><td><input type="text" size="24" '
					+ 'name="nickname"></td></tr><tr><td>Password:</td><td><input name="pwd" type="password" '
					+ 'size="24"></td></tr></table><input type="submit" value="Sign up"></form>')

			self.html_end()

		elif url.path == '/logout':
			self.send_response(200, 'OK')
			self.end_headers()
			q = urlparse.parse_qs(url.query)
			if 'cookie' in self.headers:
				cookie = self.headers['cookie'].split(';')[-1].strip()
				if 'uber' in q:
					db['sessions'].update({'login': get_user_by_cookie(cookie)}, {'$set': {'open': False}}, multi = True)
				else:
					db['sessions'].update({'cookie': cookie}, {'$set': {'open': False}})
				self.html_redirect('/')
			else:
				self.wfile.write('Huh?\n')
			self.html_end()

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
			self.html_end()

		elif url.path == '/get-to-the-kernel':
			username = self.get_user_by_cookie()
			u = get_user_account(username)
			if not username or not u:
				self.html_redirect('/')
				return
			if not 'nickname' in u:
				self.html_redirect('/?m=Nickname not defined. Check you account settings.')
				return
			if not 'tp_kernel' in u['flags']:
				self.html_redirect('/?m=Permission denied.')
				return
			rcon.teleport_to_kernel(u['nickname'])
			self.html_redirect('/?m=Success')

		elif url.path == '/magic':
			username = self.get_user_by_cookie()
			if not username:
				self.html_redirect('/')
				return

			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic()

			self.wfile.write('Input single code:<br>'
				+ '<form method="post" name="magic" action="magic">'
				+ '<input type="text" name="code" size="40"><input type="submit" value="Submit"></form>')

			if 'magic' in config and config['magic']['fileUploadEnabled']:
				self.wfile.write('... or upload a text file (with one code per line)'
					+ '<form method="post" action="magic-file?m=Your request has been processed. See detailed report below." '
					+ 'enctype="multipart/form-data"><input type="file" name="text" id="text"> '
					+ '<input type="submit" value="Upload"></form>')

			self.wfile.write('<i style="font-size: 8pt">\'1st generation\' code format is accepted (xx-111111-1234567890)<br>'
				+ 'Append "~" to beginning of a code to verify it.</i>\n')

			q = urlparse.parse_qs(url.query)
			if len(q) > 0:
				self.wfile.write('<hr><div>\n')
				s = q['status'][0].split(' ')[0]
				if 'status' in q and (s.isdigit() or s[0] == '-'):
					s = int(s)
					self.wfile.write('<img style="width: 48px; margin: 8px" src="storage/')
					if s:
						self.wfile.write('fail')
					else:
						self.wfile.write('okay')
					self.wfile.write('.png"><br>\n')
				self.wfile.write('<div class="code_list" style="text-align: center">')
				for e in q:
					self.wfile.write('<b style="color: #ccd">' + e + ':</b> ' + q[e][0] + '<br>\n')
				self.wfile.write('</div></div>\n')
			self.html_end()

		elif url.path == '/settings':
			username = self.get_user_by_cookie()
			if not username:
				self.html_redirect('/')
				return

			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic()

			nick = db['accounts'].find_one({'login': username}, {'nickname': 1, 'hide_sold': 1})
			if not nick:
				nick = 'Steve'
			hide_sold = ''
			if 'hide_sold' in nick and nick['hide_sold']:
				hide_sold = 'checked="checked"'
			self.wfile.write('<form name="settings" method="post" action="settings">')
			self.wfile.write('Nickname: <input type="text" size="32" value="' + nick['nickname'] + '" name="nickname"/><br>')
			self.wfile.write('Old password: <input type="password" size="32" name="oldpassword"/><br>')
			self.wfile.write('New password: <input type="password" size="32" name="password"/><br>')
			if not user_is_admin(username):
				self.wfile.write('Hide sold items from store: <input type="checkbox" name="hide_sold" ' + hide_sold + '/><br>')
			self.wfile.write('<input type="submit" value="Submit"/></form>\n')
			self.wfile.write('<a href="/logout?uber=1">Close all sessions</a>\n')

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

				elif q['go'][0] == 'accounts_list':
					text = ''
					for a in db['accounts'].find({}, {'login': 1}).sort('login', 1):
						text += '<a href="admin?go=accounts&login=' + a['login'] + '">' + a['login'] + '</a> '
					self.wfile.write('<h2>All Accounts</h2>' + text[:-1] + '\n')

				elif q['go'][0] == 'bought':
					self.wfile.write('<h2>Who Bought What</h2><div><div class="code_list">\n')
					for e in db['sold'].find().sort('when', -1).limit(1024):
						self.wfile.write('<b>who:</b> ' + e['who'] + ', <b>what:</b> ' + e['what'] +
							', <b>when:</b> ' + str(e['when']) + ', <b>amount:</b> ' + str(e['amount']) + '<br>\n')
					self.wfile.write('</div></div>\n')

				elif q['go'][0] == 'transactions':
					self.wfile.write('<h2>Recent Transactions</h2><div><div class="code_list">\n')
					for e in db['transactions'].find().sort('timestamp', -1).limit(1024):
						self.wfile.write('<b>src:</b> ' + e['source'] + ', <b>dst:</b> '
							+ e['destination'] + ', <b>timestamp:</b> ' + str(e['timestamp'])
							+ ', <b>amount:</b> ' + str(e['amount']) + '<br>\n')
					self.wfile.write('</div></div>\n')

				elif q['go'][0] == 'motd':
					text = ''
					d = db['motd'].find().sort('timestamp', -1).limit(1)
					if d.count():
						d = d.next()
						if 'text' in d:
							text = d['text']
					self.wfile.write('<h2>Message of the Day</h2><form method="post" action="admin?go=motd" name="motd">'
						+ '<input name="motd_text" type="text" size="86" value="' + text + '"><br>'
						+ '<input type="submit" value="Submit"></form>')

				elif q['go'][0] == 'create-a-voucher':
					self.wfile.write('<h2>Create-a-Voucher</h2>'
						+ '<p><i>Create a freeform voucher and assign it to someone. '
						+ 'Please refer to "magic.py" file of the FunkyStore source for origin codes.</i></p>'
						+ '<div><form method="post" action="admin?go=create-a-voucher" name="create-a-voucher">'
						+ 'Heading number: <input name="head_digit" type="text" size="3"/><br>'
						+ 'Origin code: <input name="origin" type="text" size="6"/><br>'
						+ 'Data: <input name="data" type="text" size="36"/><br>'
						+ 'Owner: <input name="owner" type="text" size="36" value="' + username + '"/><br>'
						+ 'Value: <input name="value" type="text" size="16"/><br>'
						+ 'Left: <input name="left" type="text" size="16"/><br>'
						+ '<input type="submit" value="Submit"></form></div>')

				else:
					self.wfile.write('No such console (or not yet implemented).\n')

			else:
				self.wfile.write('<h2>The Admin Cheat Console</h2><a href="/admin?go=accounts">Account Editor</a><br>')
				self.wfile.write('<a href="/admin?go=accounts_list">Explore Accounts</a><br>')
				self.wfile.write('<a href="/admin?go=bought">Who Bought What</a><br>')
				self.wfile.write('<a href="/admin?go=transactions">Recent Transactions</a><br>')
				self.wfile.write('<a href="/admin?go=motd">Message of the Day</a><br>')
				self.wfile.write('<a href="/admin?go=create-a-voucher">Create-a-Voucher</a><br>')

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
					acc = db.accounts.find_one({'login': data['login'][0], 'password': cook_password(data['pwd'][0],
						data['login'][0]),'locked': False})
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
						db['accounts'].insert({'login': data['login'][0], 'password': cook_password(data['pwd'][0],
												data['login'][0]), 'money': 0.0,
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
			self.html_redirect('/money?m=' + msg)

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

					if amount > 0 and amount <= config['store']['maxAmount']:  # WARNING: high values may knock MC server out (minecraft bug?)
						d = db['items'].find_one({'item_id': itemid}, {'price': 1, 'left': 1})
						if d:
							if 'left' in d:
								if d['left'] <= 0:
									self.html_redirect('/message?m=Out of stock')
									return
								if amount > d['left']:
									amount = d['left']
							bank_user = '__BANK__'
							if not db['accounts'].find_one({'login': bank_user}):
								db['accounts'].insert({'login': bank_user, 'nickname': 'Steve', 'money': 0.0, 'password': '0',
													   'locked': True, 'flags': ['money_recv']})
							ok, message = True, 'Success'
							if d['price']:
								ok, message = money.transfer(db, u, bank_user, d['price'] * amount)
							if ok:
								if 'left' in d:
									db['items'].update({'item_id': itemid}, {'$set': {'left': d['left'] - amount}})
								rcon.ItemSender(nick, itemid, amount).start()
								db['sold'].insert({'who': nick, 'what': itemid, 'when': datetime.now(),
												   'amount': amount, 'price': d['price']})
							self.html_redirect('/?m=' + message)
						else:
							self.html_redirect('/message?m=No%20such%20item')
					else:
						self.html_redirect('/message?m=Invalid amount (must not exceed '
							+ str(config['store']['maxAmount']) + ')')
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
				restock = False
				if 'restock' in data and data['restock'][0] == 'on':
					restock = True

				if q['do'][0] == 'insert':
					d = {'item_id': data['itemid'][0], 'text': data['text'][0], 'price': float(data['price'][0]),
							 'in_stock': in_stock, 'restock': restock, 'timestamp': datetime.now()}
					if 'left' in data:
						d['left'] = int(data['left'][0])
					try:
						db['items'].insert(d)
						self.html_redirect('/')
					except (KeyError, TypeError):
						self.html_redirect(missing_data_url)

				elif q['do'][0] == 'update':
					set_query = {'in_stock': in_stock, 'restock': restock}
					unset_query = {}
					if 'text' in data:
						set_query['text'] = data['text'][0]
					if 'price' in data:
						set_query['price'] = float(data['price'][0])
					if 'left' in data:
						set_query['left'] = int(data['left'][0])
					else:
						unset_query['left'] = ''
					if 'itemid' in q:
						db['items'].update({'item_id': q['itemid'][0]}, {'$set': set_query, '$unset': unset_query})
						self.html_redirect('/')
					else:
						self.html_redirect('/message?m=No item ID specified')

				else:
					self.send_error(400, 'Bad Request')

		elif url.path == '/print':
			try:
				username = self.get_user_by_cookie()
				if username:
					u = db.accounts.find_one({'login': username})
				if not username or not 'print' in u['flags']:
					self.send_error(404, 'Not Found')
					return

				if not self.validate_multipart():
					self.send_error(400, 'Bad Request')
					return

				boundary = self.headers['content-type'].split('=')[1].strip()
				upload = cgi.parse_multipart(self.rfile, {'boundary': boundary})
				if not os.path.exists('tmp'):
					os.mkdir('tmp')
				fn = 'tmp/' + get_some_random_string()
				schematic = open(fn, 'wb')
				schematic.write(upload['schematic'][0])
				schematic.close()

				rcfg = config['rconServer']
				subprocess.Popen(['./mcpaste.py', rcfg['host'] + ':' + str(rcfg['port']), rcfg['password'], fn,
					str(int(upload['x'][0])), str(int(upload['y'][0])), str(int(upload['z'][0]))])

			except:
				self.send_error(500, 'Internal Server Error')
				raise

			self.send_response(200, 'OK.')
			self.end_headers()
			self.html_redirect('/message?m=Print task successfully submitted')

		elif url.path == '/cashout':
			username = self.get_user_by_cookie()
			if not username:
				self.send_error(404, 'Not Found')
				return

			data, l = self.get_post_data()
			if not 'amount' in data or float(data['amount'][0]) <= 0:
				self.html_redirect('/?m=Invalid amount')
				return

			amount = float(data['amount'][0])
			ok, msg = money.transfer(db, username, '__BANK__', amount)
			if not ok:
				self.html_redirect('/?m=' + msg)
				return
			voucher = magic.gen_single_order(db, amount, username)
			if not voucher:
				money.transfer(db, '__BANK__', username, amount)
				self.html_redirect('/?m=Voucher cannot be generated')

			self.html_redirect('/?m=Success! Check My Vouchers tab for new codes.')

		elif url.path == '/settings':
			username = self.get_user_by_cookie()
			if not username:
				self.send_error(404, 'Not Found')
				return

			data, l = self.get_post_data()
			set_query = {}
			if 'nickname' in data:
				set_query['nickname'] = data['nickname'][0]
			h = False
			if 'hide_sold' in data and data['hide_sold'][0] == 'on':
				h = True
			set_query['hide_sold'] = h
			if 'password' in data:
				acc = db['accounts'].find_one({'login': username}, {'password': 1})
				if 'oldpassword' in data and acc and cook_password(data['oldpassword'][0], username) == acc['password']:
					set_query['password'] = cook_password(data['password'][0], username)
				else:
					self.html_redirect('/message?m=Cannot change password: old password is not valid.')
					return
			db['accounts'].update({'login': username}, {'$set': set_query})
			self.html_redirect('/message?m=Success')

		elif url.path == '/magic':
			u = None
			if 'cookie' in self.headers:
				u = get_user_by_cookie(self.headers['cookie'])
			if not u:
				self.html_redirect('/message?m=Who Are You?')
				return
			data, l = self.get_post_data()
			if 'code' in data:
				self.html_redirect('/magic?' + urllib.urlencode(magic.process(data['code'][0], db, u)))
			else:
				self.html_redirect('/magic?status=Empty code')

		elif url.path == '/magic-file':
			u = self.get_user_by_cookie()
			if not u or not 'magic' in config or not config['magic']['fileUploadEnabled']:
				self.send_error(404, "Not Found")
				return

			if not self.validate_multipart():
				self.send_error(400, 'Bad Request')
				return

			boundary = self.headers['content-type'].split('=')[1].strip()
			raw = cgi.parse_multipart(self.rfile, {'boundary': boundary})['text'][0].split('\n')

			lines = []
			count = 0

			for line in raw:
				entry = line.replace('\r', '').strip()
				if len(entry) > 0:
					lines.append(entry)
					count += 1

			report = ''

			if count == 0:
				report += 'Nothing to process'

			elif count > config['magic']['maxLinesPerFile']:
				report += 'The count of applicable lines exceeds the valid limit ('
				+ str(config['magic']['maxLinesPerFile']) + ')'

			else:
				for x in lines:
					r = magic.process(x, db, u)
					report += str(r) + '<br>\n'

				last = 'Processed ' + str(count) + ' lines'
				report += '<br>\n' + ''.join(['-' for x in last]) + '<br>\n' + last

			self.send_response(200, 'OK')
			self.end_headers()
			self.html_start()
			self.html_generic(u, url_query = urlparse.urlparse(self.path).query)
			self.html_block_start()
			self.wfile.write('<div class="code_list">\n')

			self.wfile.write(report)

			self.wfile.write('\n</div>\n')
			self.html_block_end()
			self.html_end()

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
			elif 'go' in q:
				if q['go'][0] == 'accounts' and 'action' in q \
					and q['action'][0] == 'update' and 'login' in q:
						d = {'nickname': data['nickname'][0], 'money': float(data['money'][0]),
							 'flags': data['flags'][0].strip().split(' '), 'locked': False}
						if 'locked' in data and data['locked'][0] == 'on':
							d['locked'] = True
						if 'password' in data:
							d['password'] = cook_password(data['password'][0], q['login'][0])
						db['accounts'].update({'login': q['login'][0]}, {'$set': d})
						self.html_redirect('/admin?go=accounts&login=' + q['login'][0])
				elif q['go'][0] == 'motd':
					d = {'timestamp': datetime.now()}
					if 'motd_text' in data:
						d['text'] = data['motd_text'][0]
					db['motd'].insert(d)
					self.html_redirect('/admin?go=motd')
				elif q['go'][0] == 'create-a-voucher':
					origin = None
					if 'origin' in data and len(data['origin'][0]) > 0:
						origin = int(data['origin'][0])

					if magic.create_freeform_voucher(db,
						int(data['head_digit'][0]),
						origin,
						data['data'][0],
						data['owner'][0],
						float(data['value'][0]),
						int(data['left'][0])):
						self.html_redirect('/message?m=Success')
					else:
						self.html_redirect('/message?m=Error')
				else:
					self.send_error(400, 'Bad Request')
			else:
				self.send_error(400, 'Bad Request')

		else:
			self.send_error(404, 'Not Found')

	def validate_multipart(self):
		return 'content-type' in self.headers and 'multipart/form-data' in self.headers['content-type']

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

def get_user_account(username):
	return db['accounts'].find_one({'login': username})

def get_nickname(username):
	try:
		return db['accounts'].find_one({'login': username}, {'nickname': 1})['nickname']
	except KeyError:
		return None

def user_is_admin(username):
	try:
		if 'admin' in (db['accounts'].find_one({'login': username}, {'flags': 1}))['flags']:
			return True
	except (KeyError, TypeError):
		pass
	return False

def get_some_random_string():
	return binascii.hexlify(os.urandom(16))

def cook_password(password, login):
	passwordhash = hashlib.sha256(password).digest()
	superpassword = bytearray(passwordhash)
	loginhash = hashlib.sha256(login).digest()
	superlogin = bytearray(loginhash)
	for x in range(0, 32):
		superpassword[x] ^= superlogin[x]
	return base64.b64encode(superpassword)

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
