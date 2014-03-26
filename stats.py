#!/usr/bin/env python

import os.path, json, sys, time, collections
from sqlalchemy.engine import create_engine
from sqlalchemy import schema, types, Table
from datetime import datetime
from operator import attrgetter
from mixcoatl.admin.billing_code import BillingCode
from mixcoatl.infrastructure.server import Server
from mixcoatl.settings.load_settings import settings as mixcoatl_settings

budgets = None

try:
	budgets = BillingCode.all()
except:
	print "Get Billing Codes didn't finish."

while budgets is None:
	print "waiting..."
	time.sleep(5)
else:
	with open('tmpfile', 'w') as outfile:
		json.dump(str(budgets), outfile)
	metadata = schema.MetaData()
	engine = create_engine('mysql://root@127.0.0.1/poc')
	metadata.bind = engine
	conn = engine.connect()
	
	poc = Table('poc', metadata, autoload=True)
	s = poc.select().where(poc.c.active == 'Y')
	rs = s.execute()

	for row in rs.fetchall():
		mixcoatl_settings.set_endpoint('http://'+row['poc_host']+':15000/api/enstratus/2013-12-07')
		mixcoatl_settings.set_api_version('2013-12-07')
		mixcoatl_settings.set_access_key(row['api_key'])
		mixcoatl_settings.set_secret_key(row['secret_key'])
	
		active_only = 'false'
		servers = sorted(Server.all(active_only), key=attrgetter('start_date'))
		running = 0
		launches_count = 0
		launches = dict()
			
		for server in servers:
			datekey = datetime.strptime(server.start_date, '%Y-%m-%dT%H:%M:%S.%f+0000').strftime("%Y-%m-%d")
			
			launches_count += 1

			if datekey in launches:
				launches[datekey] += 1
			else:
				launches[datekey] = 1
	
			if server.status != 'TERMINATED':
				running += 1
	
		print str(row['client_name']),"has launched",launches_count,"and has",str(running),"running server(s)."

		launch_list = collections.OrderedDict(sorted(launches.items()))

		print "Daily breakdown:"
		
		for l in launch_list:
			print "\tDate:",l," Launches:",launches[l]

		#print "Sales/Engineer:",row['sales_name']
		#print "Sales Email:",row['sales_email']
		#print "Date POC completed by CSE:",row['poc_ready_date']
		#print "POC Ownership: CSE or Sales:",row['poc_ownership']
		#print "Date POC handed to Sales:",row['handed_to_sales']
		#print "Date POC handed to Client:",row['handed_to_client']
		#print "Length of POC:",row['length_of_poc']
	
		for b in budgets:
			if row['budget_id'] == b.billing_code_id:
				if b.current_usage and b.current_usage['value']:
					print "Current Cost: $",str(round(b.current_usage['value'],2))
	
		print " --- "
	
	if os.path.exists('tmpfile'):
		os.remove('tmpfile')