import mcrcon
import threading
from config import config
from time import sleep

def get_rcon():
	rcfg = config['rconServer']
	r = mcrcon.MCRcon()
	r.connect(rcfg['host'], rcfg['port'])
	r.login(rcfg['password'])
	return r

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
			self.rcon.disconnect()

class AnyCommandExecutor(DetachedRconExecutor):
	def __init__(self, cmd):
		super(AnyCommandExecutor, self).__init__()
		self.cmd = cmd

	def execute(self):
		self.rcon.command(self.cmd)

class Teleporter(AnyCommandExecutor):
	def __init__(self, nick, x, y, z):
		super(Teleporter, self).__init__('tp ' + nick + ' ' + str(x) + ' ' + str(y) + ' ' + str(z))

def teleport_to_kernel(nick):
	Teleporter(nick, -157, 59, 15).start()

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
			self.rcon.command('give ' + self.nick + ' ' + self.item_id + ' ' + str(c) + ' ' + self.data)
			sleep(0.5)
