#!/usr/bin/env python3
import sys
import argparse
from urllib.parse import urlencode
import requests
import json
import datetime

import http.client
http.client.HTTPConnection.debuglevel = 1

import neo4j
import helper

api_url = "https://crt.sh/"
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36"
date_format = "%Y-%m-%dT%H:%M:%S"

def query(domain, expired=False):
	params = dict(
		output="json",
		q=domain
	)
	if expired is True:
		params["expired"] = "true"

	req = requests.get(
		api_url,
		params=urlencode(params),
		headers={ "User-Agent": ua }
	)

	if req.ok:
		try:
			content = req.content.decode('utf-8')
			data = json.loads(content)
			return data
		except Exception as err:
			raise Exception("Error retrieving information.")

	raise Exception("request failed")

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Lookup domains on crt.sh.')
	parser.add_argument('domain', type=str, nargs=1)
	parser.add_argument('--expired', default=False, action=argparse.BooleanOptionalAction)
	parser.add_argument('--resolve', default=False, action=argparse.BooleanOptionalAction)
	args = parser.parse_args()

	neo4j_driver = neo4j.GraphDatabase.driver(
		os.getenv("NEO4J_URL"),
		auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASS"))
	)

	results = query(
		domain=args.domain[0],
		expired=args.expired
	)
	domains = dict()

	for certificate in results:
		common_name = certificate["common_name"]
		not_before = datetime.datetime.strptime(
			certificate["not_before"],
			date_format
		)
		not_after = datetime.datetime.strptime(
			certificate["not_after"],
			date_format
		)

		domain = dict()
		if common_name in domains.keys():
			domain["not_before"] = min(
				domains[common_name]["not_before"],
				not_before
			)
			domain["not_after"] = max(
				domains[common_name]["not_after"],
				not_after
			)
		else:
			domain = dict(
				not_before=not_before,
				not_after=not_after
			)
		domains[common_name] = domain

		# ToDo: add name_value domains
		# name_value = crt["name_value"]

	with neo4j_driver.session() as session:
		for [domain, properties] in domains.items():
			print(domain)
			session.write_transaction(
				helper.add_domain,
				domain=domain,
				not_before=properties["not_before"],
				not_after=properties["not_after"]
			)

			if args.resolve is True:
				for ip in helper.resolve_dns(domain):
					session.write_transaction(
						helper.add_address,
						ip=ip
					)
					session.write_transaction(
						helper.relate_domain_address,
						domain=domain,
						ip=ip,
						relation="dns"
					)
