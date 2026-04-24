"""Library of Congress Subject Headings parser.

Fetches Science and Technology branches from the LoC Linked Data API,
recursively following narrower-term relationships up to a configurable depth.
"""

import time
import uuid
import logging

from ..config import SOURCES
from ..http_client import get_session

logger = logging.getLogger(__name__)

BASE_URL = SOURCES["loc"]["base_url"]
ROOT_IDS = SOURCES["loc"]["root_ids"]

# Delay between API requests (seconds) to respect rate limits
REQUEST_DELAY = 0.2


def _extract_id_from_uri(uri: str) -> str:
    """Extract LoC subject ID from a URI like http://id.loc.gov/authorities/subjects/sh85118553."""
    if "/" in uri:
        return uri.rstrip("/").rsplit("/", 1)[-1]
    return uri


def _fetch_subject_json(subject_id: str, session) -> dict | None:
    """Fetch JSON-LD data for a single LoC subject. Returns None on failure."""
    url = f"{BASE_URL}{subject_id}.json"
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 404:
            logger.warning("LoC subject %s not found (404)", subject_id)
            return None
        if resp.status_code == 429:
            logger.warning("LoC rate limited on %s, waiting 5s", subject_id)
            time.sleep(5)
            resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Failed to fetch LoC subject %s: %s", subject_id, e)
        return None


def _find_resource(data: list[dict], subject_id: str) -> dict | None:
    """Find the main resource node in the JSON-LD array."""
    target_uris = [
        f"http://id.loc.gov/authorities/subjects/{subject_id}",
        f"https://id.loc.gov/authorities/subjects/{subject_id}",
    ]
    for item in data:
        item_id = item.get("@id", "")
        if item_id in target_uris:
            return item
    return None


def _extract_label(resource: dict) -> str:
    """Extract the authoritative label from a resource node."""
    # Try madsrdf:authoritativeLabel
    for key in ("http://www.loc.gov/mads/rdf/v1#authoritativeLabel",
                "madsrdf:authoritativeLabel"):
        val = resource.get(key)
        if val:
            if isinstance(val, list):
                for v in val:
                    if isinstance(v, dict) and "@value" in v:
                        return v["@value"]
                    if isinstance(v, str):
                        return v
            if isinstance(val, dict) and "@value" in val:
                return val["@value"]
            if isinstance(val, str):
                return val

    # Fallback to skos:prefLabel
    for key in ("http://www.w3.org/2004/02/skos/core#prefLabel",
                "skos:prefLabel"):
        val = resource.get(key)
        if val:
            if isinstance(val, list):
                for v in val:
                    if isinstance(v, dict) and "@value" in v:
                        return v["@value"]
            if isinstance(val, dict) and "@value" in val:
                return val["@value"]
            if isinstance(val, str):
                return val

    return ""


def _extract_scope_note(resource: dict) -> str | None:
    """Extract scope note (definition) if available."""
    for key in ("http://www.w3.org/2004/02/skos/core#note",
                "http://www.w3.org/2004/02/skos/core#scopeNote",
                "skos:note", "skos:scopeNote"):
        val = resource.get(key)
        if val:
            if isinstance(val, list):
                for v in val:
                    if isinstance(v, dict) and "@value" in v:
                        return v["@value"]
                    if isinstance(v, str):
                        return v
            if isinstance(val, dict) and "@value" in val:
                return val["@value"]
            if isinstance(val, str):
                return val
    return None


def _extract_narrower_ids(resource: dict, data: list[dict]) -> list[str]:
    """Extract IDs of narrower subjects."""
    ids = set()

    # Direct narrower references on the resource
    for key in ("http://www.loc.gov/mads/rdf/v1#hasNarrowerAuthority",
                "madsrdf:hasNarrowerAuthority",
                "http://www.w3.org/2004/02/skos/core#narrower",
                "skos:narrower"):
        val = resource.get(key)
        if not val:
            continue
        if not isinstance(val, list):
            val = [val]
        for item in val:
            if isinstance(item, dict):
                uri = item.get("@id", "")
                if uri:
                    sid = _extract_id_from_uri(uri)
                    if sid.startswith("sh"):
                        ids.add(sid)

    # Also scan the full JSON-LD array for madsrdf:hasNarrowerAuthority
    # nodes that reference component nodes containing the actual subject URI
    resource_id = resource.get("@id", "")
    for item in data:
        # Look for nodes that have isMemberOfMADSCollection or broader pointing to our resource
        for key in ("http://www.w3.org/2004/02/skos/core#broader",
                    "http://www.loc.gov/mads/rdf/v1#hasBroaderAuthority"):
            val = item.get(key)
            if not val:
                continue
            if not isinstance(val, list):
                val = [val]
            for v in val:
                if isinstance(v, dict) and v.get("@id") == resource_id:
                    child_id = _extract_id_from_uri(item.get("@id", ""))
                    if child_id.startswith("sh"):
                        ids.add(child_id)

    return list(ids)


def _extract_aliases(resource: dict, data: list[dict]) -> list[str]:
    """Extract variant forms / alternative labels."""
    aliases = []

    # skos:altLabel
    for key in ("http://www.w3.org/2004/02/skos/core#altLabel", "skos:altLabel"):
        val = resource.get(key)
        if val:
            if not isinstance(val, list):
                val = [val]
            for v in val:
                if isinstance(v, dict) and "@value" in v:
                    aliases.append(v["@value"])
                elif isinstance(v, str):
                    aliases.append(v)

    # madsrdf:hasVariant — these are blank nodes in the array
    for key in ("http://www.loc.gov/mads/rdf/v1#hasVariant", "madsrdf:hasVariant"):
        val = resource.get(key)
        if val:
            if not isinstance(val, list):
                val = [val]
            for v in val:
                if isinstance(v, dict):
                    variant_id = v.get("@id", "")
                    # Find the blank node in data
                    for node in data:
                        if node.get("@id") == variant_id:
                            label = _extract_label(node)
                            if label:
                                aliases.append(label)

    return list(set(aliases))


def _crawl_subject(
    subject_id: str,
    session,
    parent_id: str | None,
    parent_path: str,
    depth: int,
    max_depth: int,
    visited: set,
    records: list,
):
    """Recursively crawl a subject and its narrower terms."""
    if depth > max_depth or subject_id in visited:
        return
    visited.add(subject_id)

    time.sleep(REQUEST_DELAY)

    data = _fetch_subject_json(subject_id, session)
    if not data or not isinstance(data, list):
        return

    resource = _find_resource(data, subject_id)
    if not resource:
        # Sometimes the response wraps differently; try first item
        logger.warning("Could not find resource node for %s", subject_id)
        return

    label = _extract_label(resource)
    if not label:
        label = subject_id

    full_path = f"{parent_path} > {label}" if parent_path else label
    definition = _extract_scope_note(resource)
    aliases = _extract_aliases(resource, data)
    narrower_ids = _extract_narrower_ids(resource, data)

    record = {
        "id": subject_id,
        "label": label,
        "definition": definition,
        "parent_id": parent_id,
        "type": "subject_heading",
        "uri": f"https://id.loc.gov/authorities/subjects/{subject_id}",
        "full_path": full_path,
        "level": depth,
        "aliases": aliases,
        "cross_refs": [],
        "version": None,
    }
    records.append(record)

    logger.info("LoC [depth=%d] %s: %s (%d narrower)", depth, subject_id, label, len(narrower_ids))

    for child_id in narrower_ids:
        _crawl_subject(
            child_id, session, subject_id, full_path,
            depth + 1, max_depth, visited, records,
        )


def parse_loc(session=None, max_depth: int = 6) -> list[dict]:
    """Fetch and parse Library of Congress Science & Technology subject headings.

    Starts from root nodes (Science sh85118553, Technology sh85133067) and
    recursively fetches narrower subjects via the JSON-LD API.

    Args:
        session: Optional requests session (created if not provided).
        max_depth: Maximum recursion depth (default 6).

    Returns:
        List of unified schema records.
    """
    session = session or get_session(cache_name="loc_cache")
    records: list[dict] = []
    visited: set[str] = set()

    for root_id in ROOT_IDS:
        print(f"  LoC: crawling root {root_id}...")
        _crawl_subject(
            root_id, session, None, "", 0, max_depth, visited, records,
        )

    print(f"  LoC total: {len(records)} subject headings across {len(ROOT_IDS)} roots")
    return records
