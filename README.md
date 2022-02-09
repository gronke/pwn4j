# pwn4j

Neo4j reporting for pentest assignments.

## Config
```sh
export NEO4J_URL=bolt://127.0.0.1:7687
export NEO4J_USER=neo4j
export NEO4J_PASS=fnord
````

## Database Constraints
```
CREATE CONSTRAINT ON (n:Domain) ASSERT n.domain IS UNIQUE
CREATE CONSTRAINT ON (n:IPv4) ASSERT n.address IS UNIQUE
CREATE CONSTRAINT ON (n:IPv6) ASSERT n.address IS UNIQUE
CREATE CONSTRAINT ON (n:Service) ASSERT (n.address_family, n.port) IS UNIQUE
```