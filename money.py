from datetime import datetime

def transfer(db, login_src, login_dest, amount = 0.0):
	"Transfer some $$$ from account to account, return True on success, False on failure (not enough money, etc.)"
	acc = db['accounts'].find_one({'login': login_src})
	if not acc:
		return (False, 'Source account does not exist')
	if not 'money' in acc:
		return (False, 'Source account have no money')
	if not 'flags' in acc or not 'money_send' in acc['flags']:
		return (False, 'Source account have no permissions to send money')

	acc_dst = db['accounts'].find_one({'login': login_dest})
	if not acc_dst:
		return (False, 'Destination account does not exist')
	if not 'flags' in acc_dst or not 'money_recv' in acc_dst['flags']:
		return (False, 'Destination account have no permissions to receive money')

	if amount > acc['money']:
		return (False, 'Not enough money')

	db['accounts'].update({'login': login_src}, {'$set': {'money': acc['money'] - amount}})
	if 'money' in acc_dst:
		db['accounts'].update({'login': login_dest}, {'$set': {'money': acc_dst['money'] + amount}})
	else:
		db['accounts'].update({'login': login_dest}, {'$set': {'money': amount}})
	db['transactions'].insert({'source': login_src, 'destination': login_dest, 'amount': amount, 'timestamp': datetime.now()})
	return (True, 'Success')

def get_balance(db, login):
	"Return None when requested account does not exist"
	acc = db['accounts'].find_one({'login': login})
	if acc:
		if 'money' in acc:
			return acc['money']
		else:
			return 0.0
	else:
		return None