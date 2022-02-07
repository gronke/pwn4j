from flask import Flask, request
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import neo4j

neo4j_driver = neo4j.GraphDatabase.driver("bolt://172.16.53.130:7687",
    auth=("neo4j", "fnord")
)

# CREATE CONSTRAINT ON (n:Domain) ASSERT n.domain IS UNIQUE
# CREATE CONSTRAINT ON (n:IPv4) ASSERT n.address IS UNIQUE
# CREATE CONSTRAINT ON (n:IPv6) ASSERT n.address IS UNIQUE
# CREATE CONSTRAINT ON (n:Service) ASSERT (n.address_family, n.port) IS UNIQUE

app = Flask(__name__)
app.config["DEBUG"] = True

@app.route("/", methods=["GET"])
def home():
    return "<h1>Neo4j API</p>"

@app.route("/Address", methods=["POST"])
def create_interface():
    if request.method != 'POST':
        return

    properties = request.json["properties"]
    def _neo4j_create_ipv4(tx, properties):
        tx.run(
            """
            MERGE (n:Address { ip: $ip })
            ON CREATE
                SET
                    n.created = timestamp(),
                    n += $properties
            ON MATCH
                SET n += $properties
            """,
            ip=properties["ip"],
            properties=properties,
        )

        reverse_dns_hostname = properties.get("reverse_dns_hostname") or None
        target_name = properties.get("target_name") or None
        domains = set.union(
            { reverse_dns_hostname },
            { target_name }
        )
        if None in domains:
            domains.remove(None)

        for domain in domains:
            domain_parts = [None]
            if domain is not None:
                domain_parts = domain.split(".")
                subdomain = domain_parts.pop(0)

                if (domain == target_name):
                    relation = "(d)-[r:dns]->(a)"
                else:
                    relation = "(a)-[r:reverse_dns]->(d)"

                parent = tx.run(
                    f"""
                    MATCH (a:Address {{ ip: $ip }})
                    MERGE (d:Domain {{ domain: $domain }})
                    ON CREATE
                        SET
                            d.created = timestamp(),
                            d.name = $subdomain
                    ON MATCH
                        SET d.name = $subdomain
                    MERGE {relation}
                    RETURN d.domain
                    """,
                    ip=properties["ip"],
                    subdomain=subdomain,
                    domain=domain
                ).single()[0]

                while len(domain_parts) > 1:
                    current = ".".join(domain_parts)
                    subdomain = domain_parts.pop(0)
                    if len(domain_parts) == 1:
                        subdomain = current
                    parent = tx.run(
                        """
                        MATCH (p:Domain { domain: $parent })
                        MERGE (d:Domain { domain: $domain })
                        ON CREATE
                            SET
                                d.created = timestamp(),
                                d.name = $subdomain
                        ON MATCH
                            SET d.name = $subdomain
                        MERGE (p)-[r:subdomain]->(d)
                        RETURN d.domain
                        """,
                        parent=parent,
                        domain=current,
                        subdomain=subdomain
                    ).single()[0]

        return "OK"

    with neo4j_driver.session() as session:
        transaction = session.write_transaction(
            _neo4j_create_ipv4,
            properties
        )
        return str(transaction)


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
