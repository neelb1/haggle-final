import logging
from typing import Optional

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

import config

logger = logging.getLogger(__name__)


class Neo4jService:
    def __init__(self):
        self.driver = None

    def connect(self):
        if not config.NEO4J_URI:
            logger.warning("NEO4J_URI not set — graph features disabled")
            return
        try:
            self.driver = GraphDatabase.driver(
                config.NEO4J_URI,
                auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
            )
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j")
        except (Neo4jError, ServiceUnavailable, Exception) as e:
            logger.error("Neo4j connection failed: %s", e)
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    @property
    def available(self) -> bool:
        return self.driver is not None

    # ── Graph Operations ─────────────────────────────────────

    def seed_demo_data(self):
        """Pre-populate graph with demo scenario."""
        if not self.available:
            return
        with self.driver.session() as session:
            session.execute_write(lambda tx: tx.run("""
                MERGE (user:Person {name: 'Neel'})
                MERGE (comcast:Service {name: 'Comcast', type: 'internet', monthlyRate: 85})
                MERGE (planet:Service {name: 'Planet Fitness', type: 'gym', monthlyRate: 25})
                MERGE (user)-[:SUBSCRIBES_TO {since: '2023-01-15', status: 'active'}]->(comcast)
                MERGE (user)-[:SUBSCRIBES_TO {since: '2022-06-01', status: 'active'}]->(planet)
            """))
            logger.info("Demo data seeded")

    def update_service_rate(
        self, service_name: str, old_rate: float, new_rate: float, confirmation: str
    ) -> dict:
        if not self.available:
            return {"status": "neo4j_unavailable"}
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    "MATCH (s:Service {name: $name}) "
                    "SET s.monthlyRate = $new_rate, s.previousRate = $old_rate "
                    "MERGE (n:Negotiation {confirmation: $conf}) "
                    "SET n.date = datetime(), n.oldRate = $old_rate, "
                    "    n.newRate = $new_rate, n.savings = $old_rate - $new_rate "
                    "MERGE (s)<-[:NEGOTIATED]-(n) "
                    "RETURN s.name AS service, n.savings AS savings",
                    name=service_name,
                    old_rate=old_rate,
                    new_rate=new_rate,
                    conf=confirmation,
                ).single()
            )
            if result:
                return {"service": result["service"], "savings": result["savings"]}
            return {"status": "not_found"}

    def cancel_service(
        self, user_name: str, service_name: str, confirmation: str
    ) -> dict:
        if not self.available:
            return {"status": "neo4j_unavailable"}
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    "MATCH (p:Person {name: $user})-[r:SUBSCRIBES_TO]->(s:Service {name: $service}) "
                    "SET r.status = 'cancelled', r.cancelledAt = datetime(), "
                    "    r.confirmation = $conf "
                    "RETURN p.name AS person, s.name AS service",
                    user=user_name,
                    service=service_name,
                    conf=confirmation,
                ).single()
            )
            if result:
                return {"person": result["person"], "service": result["service"]}
            return {"status": "not_found"}

    def add_entity(
        self, entity_type: str, value: str, context: str, call_id: Optional[str] = None
    ) -> dict:
        """No-op: Entity nodes removed to keep graph clean. Data lives on Task objects."""
        return {"entity": value, "type": entity_type, "note": "stored on task only"}

    def get_graph_data(self) -> dict:
        """Return only meaningful nodes (Person, Service, Negotiation) for visualization."""
        if not self.available:
            return {"nodes": [], "links": []}
        with self.driver.session() as session:
            # Only fetch Person, Service, Negotiation — skip Entity noise
            result = session.run(
                "MATCH (n) WHERE n:Person OR n:Service OR n:Negotiation "
                "OPTIONAL MATCH (n)-[r]->(m) WHERE m:Person OR m:Service OR m:Negotiation "
                "RETURN n, labels(n) AS labels, r, type(r) AS rel_type, "
                "       m, labels(m) AS m_labels"
            )
            nodes = {}
            links = []
            for record in result:
                n = record["n"]
                n_id = str(n.element_id)
                if n_id not in nodes:
                    props = dict(n)
                    label = record["labels"][0] if record["labels"] else "Node"
                    nodes[n_id] = {
                        "id": n_id,
                        "label": label,
                        "name": props.get("name") or props.get("value") or label,
                        "properties": {k: str(v) for k, v in props.items()},
                    }
                if record["m"] is not None:
                    m = record["m"]
                    m_id = str(m.element_id)
                    if m_id not in nodes:
                        m_props = dict(m)
                        m_label = record["m_labels"][0] if record["m_labels"] else "Node"
                        nodes[m_id] = {
                            "id": m_id,
                            "label": m_label,
                            "name": m_props.get("name") or m_props.get("value") or m_label,
                            "properties": {k: str(v) for k, v in m_props.items()},
                        }
                    if record["r"] is not None:
                        r_props = dict(record["r"])
                        links.append({
                            "source": n_id,
                            "target": m_id,
                            "type": record["rel_type"],
                            "properties": {k: str(v) for k, v in r_props.items()},
                        })
            return {"nodes": list(nodes.values()), "links": links}

    def get_subscription_profile(self, user_name: str = "Neel") -> list[dict]:
        """
        Return all active subscriptions for a user from the knowledge graph.
        Each entry: {service, service_type, monthly_cost, previous_cost, since, status}
        Returns [] if Neo4j is unavailable (caller should fall back to hardcoded data).
        """
        if not self.available:
            return []
        try:
            with self.driver.session() as session:
                result = session.run(
                    "MATCH (p:Person {name: $user})-[r:SUBSCRIBES_TO]->(s:Service) "
                    "WHERE r.status = 'active' "
                    "RETURN s.name AS service, s.type AS service_type, "
                    "       s.monthlyRate AS monthly_cost, s.previousRate AS previous_cost, "
                    "       r.since AS since",
                    user=user_name,
                )
                return [
                    {
                        "service": rec["service"],
                        "service_type": rec["service_type"] or "subscription",
                        "monthly_cost": float(rec["monthly_cost"] or 0),
                        "previous_cost": float(rec["previous_cost"]) if rec["previous_cost"] else None,
                        "since": rec["since"],
                    }
                    for rec in result
                ]
        except Exception as e:
            logger.warning("get_subscription_profile failed: %s", e)
            return []

    def update_status(self, service_name: str, details: str) -> dict:
        if not self.available:
            return {"status": "neo4j_unavailable"}
        with self.driver.session() as session:
            session.execute_write(
                lambda tx: tx.run(
                    "MATCH (s:Service {name: $name}) "
                    "SET s.lastUpdate = datetime(), s.details = $details "
                    "RETURN s.name AS service",
                    name=service_name,
                    details=details,
                )
            )
            return {"service": service_name, "updated": True}


# Singleton
neo4j_service = Neo4jService()
