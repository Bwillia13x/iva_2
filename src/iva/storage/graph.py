# Placeholder for Neo4j integration
from ..config import settings


def enabled() -> bool:
    return settings.use_neo4j and bool(settings.neo4j_uri)
