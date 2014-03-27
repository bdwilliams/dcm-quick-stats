#!/usr/bin/env python

import os.path, json, sys, time, collections, smtplib
from email.MIMEText import MIMEText
from sqlalchemy.engine import create_engine
from sqlalchemy import schema, types, Table
from datetime import datetime
from operator import attrgetter
from mixcoatl.admin.billing_code import BillingCode
from mixcoatl.infrastructure.server import Server
from mixcoatl.settings.load_settings import settings as mixcoatl_settings

if os.environ['SQL_USER'] is not None and os.environ['TO_ADDRESS'] is not None:
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
		sql_creds = os.environ['SQL_USER']
		
		if os.environ['SQL_PASSWORD'] is not None:
			sql_creds += ":"+os.environ['SQL_PASSWORD']

		engine = create_engine('mysql://'+sql_creds+'@127.0.0.1/poc')
		metadata.bind = engine
		conn = engine.connect()
		
		poc = Table('poc', metadata, autoload=True)
		s = poc.select().where(poc.c.active == 'Y')
		rs = s.execute()
	
		for row in rs.fetchall():
			mixcoatl_settings.set_endpoint('http://'+row['server_host']+':15000/api/enstratus/2013-12-07')
			mixcoatl_settings.set_api_version('2013-12-07')
			mixcoatl_settings.set_access_key(row['api_key'])
			mixcoatl_settings.set_secret_key(row['secret_key'])
		
			active_only = 'false'
			servers = sorted(Server.all(active_only), key=attrgetter('start_date'))
			running = 0
			launches_count = 0
			launches = dict()
			msg = ""
	
			for server in servers:
				datekey = datetime.strptime(server.start_date, '%Y-%m-%dT%H:%M:%S.%f+0000').strftime("%Y-%m-%d")
				
				launches_count += 1
	
				if datekey in launches:
					launches[datekey] += 1
				else:
					launches[datekey] = 1
		
				if server.status != 'TERMINATED':
					running += 1
		
			msg += str(row['client_name'])+"\n\n"
			msg += "Launched Server(s): "+str(launches_count)+"\n"
			msg += "Running Server(s): "+str(running)+"\n"
	
			launch_list = collections.OrderedDict(sorted(launches.items()))

			msg += "\n"

			msg += "Daily breakdown:"+"\n"
			
			for l in launch_list:
				msg += "\tDate:"+l+" Launches:"+str(launches[l])+"\n"
	
			msg += "\n"
			
			if row['se_name'] is not None:
				msg += "Sales Engineer: "+row['se_name']+"\n"

			if row['ae_name'] is not None:
				msg += "Account Executive: "+row['ae_name']+"\n"
	
			if row['ready_date'] is not None:
				msg += "Date Managed Trial created by CSE: "+row['ready_date']+"\n"
	
			if row['handed_to_sales'] is not None:
				msg += "Date Managed Trial handed to Sales :"+row['handed_to_sales']+"\n"
	
			if row['trial_start'] is not None:
				msg += "Date Managed Trial handed to Client: "+row['trial_start']+"\n"
	
			if row['trial_end'] is not None and row['trial_end'] > 0:
				msg += "Date Managed Trial completes: "+str(row['trial_end'])+"\n"
		
			for b in budgets:
				if row['budget_id'] == b.billing_code_id:
					if b.current_usage and b.current_usage['value']:
						msg += "Current Cost: $"+str(round(b.current_usage['value'],2))+"\n"
			
			msg_body = MIMEText(msg)

			if row['se_email'] is not None and row['ae_email'] is not None:
				to = [os.environ['TO_ADDRESS'], row['se_email'], row['ae_email']]
			elif row['se_email'] is not None and row['ae_email'] is None:
				to = [os.environ['TO_ADDRESS'], row['se_email']]
			elif row['se_email'] is  None and row['ae_email'] is not None:
				to = [os.environ['TO_ADDRESS'], row['ae_email']]
			else:
				to = os.environ['TO_ADDRESS']

			msg_body['To'] = ", ".join(to)
			msg_body['Subject'] = str(row['client_name'])+" Managed Trial Stats"

			try:
				smtpObj = smtplib.SMTP("localhost")				
				smtpObj.sendmail('poc-notifications@enstratius.com', to, msg_body.as_string())
				print "Sent Email..."
				smtpObj.quit()
			except SMTPException:
				print "Error: unable to send email."
		
		if os.path.exists('tmpfile'):
			os.remove('tmpfile')
else:
	print "You must set the SQL_USER and SQL_PASSWORD environment variables."