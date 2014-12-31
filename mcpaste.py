#!/usr/bin/env python

"""

MCPaste - import mcedit .schematic files
directly into your vanilla Minecraft server via rcon

Requirements:
- PyYaml
- https://github.com/mcedit/pymclevel
- https://github.com/barneygale/MCRcon

MEDVEDx64, 2014-11-04

"""

import sys
import time
from pymclevel import schematic
from mcrcon import MCRcon
import yaml

coords = [0, 0, 0]
rcon = None
lib = None
skip_air = False

def make_command(block, data, x, y, z):
	if block == 0 and skip_air:
		return ''

	idStr = 'air'
	if block > 0 and block < 256:
		try:
			idStr = lib['blocks'][block]['idStr']
		except (IndexError, KeyError):
			pass
	elif block == 0:
		idStr = 'stone'
	else:
		idStr = 'air'
	return 'setblock ' + str(coords[0]+x) + ' ' + str(coords[1]+z) + ' ' + str(coords[2]+y) + \
		' ' + idStr + ' ' + str(data)

def trip(schm):
	for x in range(schm.Width):
		for y in range(schm.Length):
			for z in range(schm.Height):

				rcon.send(make_command(schm.Blocks[x,y,z]-1, schm.Data[x,y,z], x, y, z))
			time.sleep(0.1)

if __name__ == '__main__':
	lib = yaml.load(open('pymclevel/minecraft.yaml'))

	addr = None
	port = 25575
	filename = None
	passwd = None

	try:
		addr = sys.argv[1]
		if ':' in addr:
			spl = addr.split(':')
			addr = spl[0]
			port = int(spl[1])

		passwd = sys.argv[2]
		filename = sys.argv[3]
		coords[0] = int(sys.argv[4])
		coords[1] = int(sys.argv[5])
		coords[2] = int(sys.argv[6])
		if 'air' in sys.argv:
			skip_air = True

	except IndexError:
		print("Usage: mcpaste.py rcon_host[:port] rcon_passwordcd schematic_file x y z [air]")
		sys.exit(1)

	schm = schematic.MCSchematic(filename = filename)
	print('Schematic length ' + str(schm.Length) + ' width ' + str(schm.Width) + ' height ' + str(schm.Height))
	rcon = MCRcon(addr, port, passwd)
	trip(schm)

