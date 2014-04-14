#!/usr/bin/env python

import os.path, json, sys, time, collections, smtplib
from email.MIMEText import MIMEText
from sqlalchemy.engine import create_engine
from sqlalchemy import schema, types, Table
from datetime import datetime
from operator import attrgetter
from mixcoatl.admin.account import Account
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
		s = poc.select().where(poc.c.active == 'Y' and poc.c.trial_start is not None)
		rs = s.execute()

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
				msg = ""

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
					ready_date_formatted = datetime.strptime(str(row['ready_date']), '%Y-%m-%d 00:00:00').strftime("%Y-%m-%d")
					msg += "Date Managed Trial created by CSE: "+str(ready_date_formatted)+"\n"

				if row['handed_to_sales'] is not None:
					handed_to_sales_formatted = datetime.strptime(str(row['handed_to_sales']), '%Y-%m-%d 00:00:00').strftime("%Y-%m-%d")
					msg += "Date Managed Trial handed to Sales :"+str(handed_to_sales_formatted)+"\n"

				if row['trial_start'] is not None:
					trial_start_formatted = datetime.strptime(str(row['trial_start']), '%Y-%m-%d 00:00:00').strftime("%Y-%m-%d")
					msg += "Date Managed Trial handed to Client: "+str(trial_start_formatted)+"\n"

				if row['trial_end'] is not None:
					trial_end_formatted = datetime.strptime(str(row['trial_end']), '%Y-%m-%d 00:00:00').strftime("%Y-%m-%d")
					msg += "Date Managed Trial completes: "+str(trial_end_formatted)+"\n"

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
					to = [os.environ['TO_ADDRESS']]

				msg_body['To'] = ", ".join(to)
				msg_body['Subject'] = str(row['client_name'])+" Managed Trial Stats ("+str(time.strftime("%Y-%m-%d"))+")"

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
	print "You must set the SQL_USER and TO_ADDRESS environment variables."
