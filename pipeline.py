from flask import Flask, request
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import neo4j

import helper

neo4j_driver = neo4j.GraphDatabase.driver("bolt://172.16.53.130:7687",
    auth=("neo4j", "fnord")
)

app = Flask(__name__)
app.config["DEBUG"] = True

@app.route("/", methods=["GET"])
def home():
    return "<h1>Neo4j API</p>"

@app.route("/Address", methods=["POST"])
def create_interface():
    if request.method != 'POST':
        return

    ip = request.json["ip"]
    properties = request.json["properties"]

    with neo4j_driver.session() as session:
        session.write_transaction(
            helper.add_address,
            ip=ip,
            properties=properties
        )

    reverse_dns_hostname = properties.get("reverse_dns_hostname") or None
    target_name = properties.get("target_name") or None
    
    if reverse_dns_hostname is not None:
        session.write_transaction(
            helper.add_domain,
            domain=reverse_dns_hostname
        )
        session.write_transaction(
            helper.relate_domain_address,
            domain=reverse_dns_hostname,
            ip=ip,
            relation="reverse_dns"
        )
    if target_name is not None:
        session.write_transaction(
            helper.add_domain,
            domain=target_name
        )
        session.write_transaction(
            helper.relate_domain_address,
            domain=target_name,
            ip=ip,
            relation="dns"
        )
    return "OK"

@app.route("/Service", methods=["POST"])
def create_service():
    if request.method == 'POST':
        properties = request.json["properties"]
        address = request.json["address"]
        def _neo4j_create_ipv4(tx, properties, address):
            result = tx.run(
                """
                MATCH (i:Address {
                    ip: $address.ip,
                    family: $address.family
                })
                MERGE (n:Service {
                    address: id(i),
                    protocol: $protocol,
                    port: $port
                })
                ON CREATE
                    SET
                        n.created = timestamp(),
                        n.state = $state,
                        n.label = $label,
                        n.service = $service,
                        n.software = $service
                ON MATCH
                    SET
                        n.state = $state,
                        n.label = $label,
                        n.service = $service,
                        n.software = $software
                MERGE (i)-[r:listens]->(n)
                RETURN n
                """,
                address=address,
                protocol=properties["protocol"],
                port=properties["port"],
                state=properties.get("state", "open"),
                service=properties["service"],
                software=properties["software"],
                label=f"{properties.get('service', properties['protocol'])}/{properties['port']}"
            )
            return "OK"

        with neo4j_driver.session() as session:
            transaction = session.write_transaction(
                _neo4j_create_ipv4,
                properties,
                address
            )
            return str(transaction)

app.run()
