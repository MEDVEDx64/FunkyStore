from datetime import datetime

def transfer(db, login_src, login_dest, amount = 0.0):
	"Transfer some $$$ from account to account, return True on success, False on failure (not enough money, etc.)"
	if amount < 0:
		return (False, 'Invalid amount')
	if login_src == login_dest:
		return (False, 'Destination and source are the same account')

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

def get_str(v):
	if v == 0:
		return '0.0'

	if v < 0.0000000001 and v >= 1:
		return str(v)

	s = list('{0:.10f}'.format(v))
	for i in range(len(s) - 1, -1, -1):
		if s[i] == '0':
			s[i] = ' '
		else:
			break

	return ''.join(s).strip()
