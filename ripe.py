#!/usr/bin/env python3
import os
import socket
import json
import argparse
from urllib.parse import urlencode
import requests
import requests.packages.urllib3.util.connection as urllib3_cn
import neo4j

import http.client
http.client.HTTPConnection.debuglevel = 1

ripe_api_url = "https://rest.db.ripe.net/search"

neo4j_driver = neo4j.GraphDatabase.driver(
	os.getenv("NEO4J_URL"),
	auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASS"))
)

def query(search):
	req = requests.get(
		ripe_api_url,
		params=urlencode({
			"query-string": search,
			"type-filter": "inetnum"
		}),
		headers={
			"Accept": "application/json" 
		}
	)

	if req.ok:
		content = req.content.decode("utf-8")
		data = json.loads(content)
		return data

	raise Exception(f"RIPE API HTTP Error: {req.status_code}")

def neo4j_add_network(tx, ip, inetnum, properties):
	tx.run(
		"""
		MERGE (n:Network { inetnum: $inetnum })
		ON CREATE
			SET
				n.created = datetime(),
				n.source_name = "RIPE",
				n += $properties
		ON MATCH
			SET
				n += $properties
		WITH n
		MATCH (a:Address { ip: $ip })
		MERGE (n)-[r:net]-(a)
		""",
		ip=ip,
		inetnum=inetnum,
		properties=properties
	)

def neo4j_find_network(tx, ip):
	results = tx.run(
		"""
		MATCH (n:Network)
		RETURN n
		""",
		ip=ip
	)
	
	def _match_ip(result):
		from_ip = socket.inet_aton(result[0]["from_ip"])
		to_ip = socket.inet_aton(result[0]["to_ip"])
		_ip = socket.inet_aton(ip)
		return from_ip <= _ip <= to_ip

	try:
		return next(filter(_match_ip, results))
	except StopIteration:
		return None

def neo4j_relate_network_ip(tx, ip, inetnum):
	tx.run(
		"""
		MATCH (n:Network { inetnum: $inetnum })
        MATCH (a:Address { ip: $ip })
        MERGE (n)-[r:net]-(a)
		""",
		ip=ip,
		inetnum=inetnum
	)


def neo4j_find_unrelated_ips(tx):
	"""
	Find Addresses in database that are not related to a Network.
	"""
	result = tx.run(
		"""
		MATCH (a:Address)
		WHERE NOT (a)-[:net]-(:Network)
		RETURN a.ip
		"""
	)

	if result is None:
		return []

	return [record[0] for record in result]

def run(session, ip):

	existing_network = session.write_transaction(
		neo4j_find_network,
		ip=ip
	)

	if existing_network is not None:
		# Relate IP to existing Network
		session.write_transaction(
			neo4j_relate_network_ip,
			ip=ip,
			inetnum=existing_network[0]["inetnum"]
		)
	else:
		# Create new Network and relate IP
		result = query(ip)
		inetnum_attributes = next(filter(
			lambda obj: obj["type"] == "inetnum",
			result["objects"]["object"]
		))["attributes"]["attribute"]

		inetnum = next(filter(
			lambda attribute: attribute["name"] == "inetnum",
			inetnum_attributes
		))["value"]
		netname = next(filter(
			lambda attribute: attribute["name"] == "netname",
			inetnum_attributes
		))["value"]
		country = next(filter(
			lambda attribute: attribute["name"] == "country",
			inetnum_attributes
		))["value"]
		from_ip, to_ip = inetnum.replace(" ", "").split("-")
	
		session.write_transaction(
			neo4j_add_network,
			ip=ip,
			inetnum=inetnum,
			properties=dict(
				netname=netname,
				from_ip=from_ip,
				to_ip=to_ip,
				country=country
			)
		)

if __name__ == "__main__":

	parser = argparse.ArgumentParser(
		description='Query RIPE database.'
	)
	group = parser.add_mutually_exclusive_group()
	group.add_argument("search", type=str, nargs="?", default=None)
	group.add_argument(
		"--scan-existing",
		default=False,
		action=argparse.BooleanOptionalAction
	)
	args = parser.parse_args()

	with neo4j_driver.session() as session:
		
		if args.scan_existing is True:
			ips = session.write_transaction(neo4j_find_unrelated_ips)
		elif args.search is not None:
			ips = [args.search]
		else:
			raise Exception("Invalid input.")

		for curr in ips:
			run(session, curr)
