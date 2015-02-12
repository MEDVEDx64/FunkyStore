import rcon

class TransactionDriver(object):
	def process(self, address, item, amount, data = None):
		return None # Returning an object means failure state

class MinecraftRCONDriver(TransactionDriver):
	def process(self, address, item, amount, data = None):
		rcon.ItemSender(address, item, amount, data).start()
		return None

default_driver = MinecraftRCONDriver()