#!/usr/bin/env python2.7

import pymongo

from config import config

if __name__ == '__main__':
	dbclient = pymongo.MongoClient(config['dbUri'])
	db = dbclient.funky
	
	bank_user = '__BANK__'
	reserve_user = '__RESERVE__'

	if not db['accounts'].find_one({'login': bank_user}):
		print('Creating bank account')
		db['accounts'].insert({
			'login': bank_user, 'nickname': 'Steve', 'money': 0.0, 'password': '0',
			'locked': True, 'flags': ['money_recv']})

	if not db['accounts'].find_one({'login': reserve_user}):
		print('Creating reserve account')
		db['accounts'].insert({
			'login': reserve_user, 'nickname': 'Steve', 'money': 1000000000.0, 'password': '0',
			'locked': True, 'flags': ['money_send']})
