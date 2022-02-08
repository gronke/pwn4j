import socket

def resolve_dns(domain, family=None):
    try:
        return list(
            filter(
                lambda addr: (family is None) or (addr[0] == family),
                map(
                    lambda addr: addr[4][0],
                    socket.getaddrinfo(domain, 80)
                )
            )
        )
    except socket.gaierror:
        return []

def relate_domain_address(tx, domain, ip, relation="dns"):
    if relation == "reverse_dns":
        relation_query = "(a)-[r:reverse_dns]->(d)"
    elif relation == "dns":
        relation_query = "(d)-[r:dns]->(a)"
    else:
        raise Exception(f"Unknown relation: {relation}")
    tx.run(
        f"""
        MATCH (a:Address {{ ip: $ip }})
        MATCH (d:Domain {{ domain: $domain }})
        MERGE {relation_query}
        """,
        domain=domain,
        ip=ip
    )

def add_domain(tx, domain, source_name=None, **properties):
    domain_parts = [None]
    if domain is None:
        return

    domain_parts = domain.split(".")
    current = ".".join(domain_parts)
    subdomain = domain_parts.pop(0)
    if len(domain_parts) == 1:
        subdomain = current
        extra_labels = ":TLD"
    else:
        extra_labels = ""

    parent = tx.run(
        f"""
        MERGE (d:Domain{extra_labels} {{ domain: $domain }})
        ON CREATE
            SET
                d.created = datetime(),
                d.source_name = $source_name,
                d.name = $name,
                d += $properties
        ON MATCH
            SET
                d.name = $name,
                d += $properties
        RETURN d.domain
        """,
        name=subdomain,
        domain=domain,
        source_name=source_name,
        properties=properties
    ).single()[0]

    while len(domain_parts) > 1:
        current = ".".join(domain_parts)
        subdomain = domain_parts.pop(0)
        if len(domain_parts) == 1:
            extra_labels = ":TLD"
            subdomain = current
        else:
            extra_labels = ""
        parent = tx.run(
            f"""
            MATCH (p:Domain {{ domain: $parent }})
            MERGE (d:Domain{extra_labels} {{ domain: $domain }})
            ON CREATE
                SET
                    d.created = datetime(),
                    d.source_name = $source_name,
                    d.name = $name
            ON MATCH
                SET
                    d.name = $name
            MERGE (p)-[r:subdomain]->(d)
            RETURN d.domain
            """,
            parent=parent,
            domain=current,
            name=subdomain,
            source_name=source_name
        ).single()[0]


def add_address(tx, ip, properties={}):
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
        ip=ip,
        properties=properties,
    )
    return "OK"
