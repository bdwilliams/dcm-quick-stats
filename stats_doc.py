#!/usr/bin/env python

import os.path, json, sys, time, collections, webbrowser
from sqlalchemy.engine import create_engine
from sqlalchemy import schema, types, Table
from datetime import datetime
from operator import attrgetter
from mixcoatl.admin.account import Account
from mixcoatl.infrastructure.server import Server
from mixcoatl.settings.load_settings import settings as mixcoatl_settings

if os.environ['SQL_USER'] is not None:
	metadata = schema.MetaData()
	sql_creds = os.environ['SQL_USER']

	if os.environ['SQL_PASSWORD'] is not None:
		sql_creds += ":"+os.environ['SQL_PASSWORD']

	engine = create_engine('mysql://'+sql_creds+'@127.0.0.1/poc')
	metadata.bind = engine
	conn = engine.connect()

	poc = Table('poc', metadata, autoload=True)
	s = poc.select().where(poc.c.active == 'Y' and poc.c.trial_start is not None)
	rs = s.execute()
	msg = "<table border=\"1\" cellpadding=\"8\" cellspacing=\"0\" style=\"font-size: 10pt; border: 1px solid #000000\">\n"
	msg += "\t<tr>\n"
	msg += "\t\t<th style=\"background-color: #1F4A7A; color: #FFFFFF;\">Customer</th>\n"
	msg += "\t\t<th style=\"background-color: #1F4A7A; color: #FFFFFF;\">SE</th>\n"
	msg += "\t\t<th style=\"background-color: #1F4A7A; color: #FFFFFF;\">AE</th>\n"
	#msg += "\t\t<th style=\"background-color: #1F4A7A; color: #FFFFFF;\">Delivery Phase</th>\n"
	msg += "\t\t<th style=\"background-color: #1F4A7A; color: #FFFFFF;\">Start Date</th>\n"
	msg += "\t\t<th style=\"background-color: #1F4A7A; color: #FFFFFF;\">End Date</th>\n"
	msg += "\t\t<th style=\"background-color: #1F4A7A; color: #FFFFFF;\">Active Servers</th>\n"
	msg += "\t\t<th style=\"background-color: #1F4A7A; color: #FFFFFF;\">Total Servers</th>\n"
	msg += "\t</tr>\n"

	for row in rs.fetchall():
		mixcoatl_settings.set_endpoint('http://'+row['server_host']+':15000/api/enstratus/2013-12-07')
		mixcoatl_settings.set_api_version('2013-12-07')
		mixcoatl_settings.set_access_key(row['api_key'])
		mixcoatl_settings.set_secret_key(row['secret_key'])

		for account in Account.all():
			params = {'activeOnly':'false', 'accountId':account.account_id}
			servers = sorted(Server.all(params=params), key=attrgetter('start_date'))
			running = 0
			launches_count = 0
			launches = dict()

			for server in servers:
				datekey = datetime.strptime(server.start_date, '%Y-%m-%dT%H:%M:%S.%f+0000').strftime("%Y-%m-%d")
				trial_start_formatted = datetime.strptime(str(row['trial_start']), '%Y-%m-%d 00:00:00').strftime("%Y-%m-%d")

				if datekey > trial_start_formatted:
					launches_count += 1

					if datekey in launches:
						launches[datekey] += 1
					else:
						launches[datekey] = 1

					if server.status != 'TERMINATED':
						running += 1

			if row['trial_start'] is not None:
				trial_start_formatted = datetime.strptime(str(row['trial_start']), '%Y-%m-%d 00:00:00').strftime("%Y-%m-%d")
			else:
				trial_start_formatted = "N/A"

			if row['trial_end'] is not None:
				trial_end_formatted = datetime.strptime(str(row['trial_end']), '%Y-%m-%d 00:00:00').strftime("%Y-%m-%d")
			else:
				trial_end_formatted = "N/A"

		msg += "\t<tr>\n"
		msg += "\t\t<td>"+str(row['client_name'])+"</td>\n"
		msg += "\t\t<td>"+str(row['se_name'])+"</td>\n"
		msg += "\t\t<td>"+str(row['ae_name'])+"</td>\n"
		#msg += "\t\t<td>Test</td>\n"
		msg += "\t\t<td>"+str(trial_start_formatted)+"</td>\n"
		msg += "\t\t<td>"+str(trial_end_formatted)+"</td>\n"
		msg += "\t\t<td>"+str(running)+"</td>\n"
		msg += "\t\t<td>"+str(launches_count)+"</td>\n"
		msg += "\t</tr>\n"

msg += "</table>"

if os.path.exists('index.html'):
	os.remove('index.html')

f = open("index.html", "w")
f.write(msg)
f.close()

webbrowser.open("file://" + os.path.realpath('index.html'))
#print msg
