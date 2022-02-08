# pwn4j

Neo4j reporting for pentest assignments.

## Database Constraints
```
CREATE CONSTRAINT ON (n:Domain) ASSERT n.domain IS UNIQUE
CREATE CONSTRAINT ON (n:IPv4) ASSERT n.address IS UNIQUE
CREATE CONSTRAINT ON (n:IPv6) ASSERT n.address IS UNIQUE
CREATE CONSTRAINT ON (n:Service) ASSERT (n.address_family, n.port) IS UNIQUE
```