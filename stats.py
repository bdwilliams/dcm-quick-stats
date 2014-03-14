#!/usr/bin/env python

import os.path, configparser
from operator import attrgetter
from mixcoatl.infrastructure.server import Server
from mixcoatl.settings.load_settings import settings as mixcoatl_settings

config = configparser.ConfigParser()

if os.path.isfile('config.ini'):
	config.read('config.ini')
	
	for section in config.sections():
		mixcoatl_settings.set_endpoint('http://'+str(config[section]['hostname'])+':15000/api/enstratus/2013-12-07')
		mixcoatl_settings.set_api_version('2013-12-07')
		mixcoatl_settings.set_access_key(str(config[section]['access_key']))
		mixcoatl_settings.set_secret_key(str(config[section]['secret_key']))

		terms = 0
		running = 0
		active_only = 'false'
		
		servers = sorted(Server.all(active_only), key=attrgetter('start_date'))
	
		for server in servers:
			if server.status == 'TERMINATED':
				terms = terms + 1
			else:
				running = running + 1

		print config[section],"has "+str(running)+" running server(s) and "+str(terms)+" terminated.  Last Launch: "+server.start_date
else:
	print "No config.ini file exists."