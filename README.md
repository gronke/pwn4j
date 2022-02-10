# pwn4j

Neo4j reporting for pentest assignments.

## Install
```sh
python3 -m pip install requirements.txt
````

## Config
```sh
export NEO4J_URL=bolt://127.0.0.1:7687
export NEO4J_USER=neo4j
export NEO4J_PASS=fnord
````

Or alternatively loaded from .env file:

```sh
cat - > .env <<EOF
NEO4J_URL=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASS=fnord
EOF
export $(cat .env | xargs)
```

## Database Constraints
```
CREATE CONSTRAINT ON (n:Domain) ASSERT n.domain IS UNIQUE
CREATE CONSTRAINT ON (n:IPv4) ASSERT n.address IS UNIQUE
CREATE CONSTRAINT ON (n:IPv6) ASSERT n.address IS UNIQUE
CREATE CONSTRAINT ON (n:Service) ASSERT (n.address_family, n.port) IS UNIQUE
```

## Data Ingress

### nmap

Run the Neo4j API Server
```sh
python3 pipeline.py
````

The log4j.nse Script will send the output to the REST API endpoint:
```sh
nmap <TARGET> --script ./log4j.nse
````

## Useful Queries

### Show everything, but no expired Domains (via CRT.sh)

```
MATCH(n)
WHERE NOT (n:Network) AND ((n:Domain AND (datetime(n.not_after) > datetime()) OR NOT EXISTS (n.not_after)) OR NOT n:Domain) RETURN n
```