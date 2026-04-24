"""Tests for Library of Congress Subject Headings parser."""

import pytest
from unittest.mock import MagicMock, patch

from src.parsers.loc import (
    _extract_id_from_uri,
    _extract_label,
    _extract_scope_note,
    _extract_narrower_ids,
    _extract_aliases,
    _find_resource,
    _crawl_subject,
    parse_loc,
)


# --- Sample JSON-LD data mimicking LoC API responses ---

SAMPLE_RESOURCE = {
    "@id": "http://id.loc.gov/authorities/subjects/sh85118553",
    "http://www.loc.gov/mads/rdf/v1#authoritativeLabel": [
        {"@value": "Science", "@language": "en"}
    ],
    "http://www.w3.org/2004/02/skos/core#prefLabel": [
        {"@value": "Science", "@language": "en"}
    ],
    "http://www.w3.org/2004/02/skos/core#note": [
        {"@value": "General works on science", "@language": "en"}
    ],
    "http://www.loc.gov/mads/rdf/v1#hasNarrowerAuthority": [
        {"@id": "http://id.loc.gov/authorities/subjects/sh85009003"},
        {"@id": "http://id.loc.gov/authorities/subjects/sh85014203"},
    ],
    "http://www.w3.org/2004/02/skos/core#altLabel": [
        {"@value": "Natural science", "@language": "en"},
    ],
}

SAMPLE_CHILD_RESOURCE = {
    "@id": "http://id.loc.gov/authorities/subjects/sh85009003",
    "http://www.loc.gov/mads/rdf/v1#authoritativeLabel": [
        {"@value": "Astronomy", "@language": "en"}
    ],
}

SAMPLE_JSON_LD = [
    SAMPLE_RESOURCE,
    SAMPLE_CHILD_RESOURCE,
]


class TestExtractIdFromUri:
    def test_full_uri(self):
        assert _extract_id_from_uri("http://id.loc.gov/authorities/subjects/sh85118553") == "sh85118553"

    def test_trailing_slash(self):
        assert _extract_id_from_uri("http://id.loc.gov/authorities/subjects/sh85118553/") == "sh85118553"

    def test_plain_id(self):
        assert _extract_id_from_uri("sh85118553") == "sh85118553"


class TestFindResource:
    def test_finds_by_http_uri(self):
        result = _find_resource(SAMPLE_JSON_LD, "sh85118553")
        assert result is not None
        assert result["@id"] == "http://id.loc.gov/authorities/subjects/sh85118553"

    def test_returns_none_for_missing(self):
        result = _find_resource(SAMPLE_JSON_LD, "sh00000000")
        assert result is None


class TestExtractLabel:
    def test_authoritative_label(self):
        assert _extract_label(SAMPLE_RESOURCE) == "Science"

    def test_preflabel_fallback(self):
        resource = {
            "http://www.w3.org/2004/02/skos/core#prefLabel": [
                {"@value": "FallbackLabel"}
            ],
        }
        assert _extract_label(resource) == "FallbackLabel"

    def test_empty_resource(self):
        assert _extract_label({}) == ""


class TestExtractScopeNote:
    def test_has_note(self):
        assert _extract_scope_note(SAMPLE_RESOURCE) == "General works on science"

    def test_no_note(self):
        assert _extract_scope_note({}) is None


class TestExtractNarrowerIds:
    def test_narrower_authorities(self):
        ids = _extract_narrower_ids(SAMPLE_RESOURCE, SAMPLE_JSON_LD)
        assert "sh85009003" in ids
        assert "sh85014203" in ids

    def test_no_narrower(self):
        ids = _extract_narrower_ids({}, [])
        assert ids == []


class TestExtractAliases:
    def test_alt_labels(self):
        aliases = _extract_aliases(SAMPLE_RESOURCE, SAMPLE_JSON_LD)
        assert "Natural science" in aliases

    def test_no_aliases(self):
        aliases = _extract_aliases({}, [])
        assert aliases == []


class TestCrawlSubject:
    @patch("src.parsers.loc._fetch_subject_json")
    @patch("src.parsers.loc.time")
    def test_single_subject_no_children(self, mock_time, mock_fetch):
        """Crawl a leaf node with no narrower terms."""
        leaf = {
            "@id": "http://id.loc.gov/authorities/subjects/sh85009003",
            "http://www.loc.gov/mads/rdf/v1#authoritativeLabel": [
                {"@value": "Astronomy"}
            ],
        }
        mock_fetch.return_value = [leaf]

        records = []
        visited = set()
        _crawl_subject("sh85009003", MagicMock(), None, "", 0, 6, visited, records)

        assert len(records) == 1
        assert records[0]["id"] == "sh85009003"
        assert records[0]["label"] == "Astronomy"
        assert records[0]["parent_id"] is None
        assert records[0]["level"] == 0
        assert records[0]["type"] == "subject_heading"

    @patch("src.parsers.loc._fetch_subject_json")
    @patch("src.parsers.loc.time")
    def test_respects_max_depth(self, mock_time, mock_fetch):
        """Should not crawl beyond max_depth."""
        records = []
        visited = set()
        _crawl_subject("sh85009003", MagicMock(), None, "", 7, 6, visited, records)
        assert len(records) == 0
        mock_fetch.assert_not_called()

    @patch("src.parsers.loc._fetch_subject_json")
    @patch("src.parsers.loc.time")
    def test_skips_visited(self, mock_time, mock_fetch):
        """Should not re-crawl visited subjects."""
        records = []
        visited = {"sh85009003"}
        _crawl_subject("sh85009003", MagicMock(), None, "", 0, 6, visited, records)
        assert len(records) == 0
        mock_fetch.assert_not_called()

    @patch("src.parsers.loc._fetch_subject_json")
    @patch("src.parsers.loc.time")
    def test_builds_full_path(self, mock_time, mock_fetch):
        """Full path should include parent chain."""
        leaf = {
            "@id": "http://id.loc.gov/authorities/subjects/sh85009003",
            "http://www.loc.gov/mads/rdf/v1#authoritativeLabel": [
                {"@value": "Astronomy"}
            ],
        }
        mock_fetch.return_value = [leaf]

        records = []
        _crawl_subject("sh85009003", MagicMock(), "sh85118553", "Science", 1, 6, set(), records)

        assert records[0]["full_path"] == "Science > Astronomy"
        assert records[0]["parent_id"] == "sh85118553"
        assert records[0]["level"] == 1


class TestParseLoc:
    @patch("src.parsers.loc._crawl_subject")
    def test_calls_both_roots(self, mock_crawl):
        """Should attempt to crawl both Science and Technology roots."""
        session = MagicMock()
        parse_loc(session=session, max_depth=2)
        assert mock_crawl.call_count == 2
        call_ids = [call.args[0] for call in mock_crawl.call_args_list]
        assert "sh85118553" in call_ids
        assert "sh85133067" in call_ids

    @patch("src.parsers.loc._crawl_subject")
    def test_returns_list(self, mock_crawl):
        result = parse_loc(session=MagicMock(), max_depth=1)
        assert isinstance(result, list)

    def test_record_schema(self):
        """Verify record has all required fields using a mocked single-node crawl."""
        with patch("src.parsers.loc._fetch_subject_json") as mock_fetch, \
             patch("src.parsers.loc.time"):
            mock_fetch.return_value = [SAMPLE_RESOURCE]
            # Only crawl one root to keep it simple
            with patch("src.parsers.loc.ROOT_IDS", ["sh85118553"]):
                # Prevent recursion into children
                with patch("src.parsers.loc._extract_narrower_ids", return_value=[]):
                    records = parse_loc(session=MagicMock(), max_depth=1)

        assert len(records) == 1
        r = records[0]
        required_keys = {"id", "label", "definition", "parent_id", "type", "uri",
                         "full_path", "level", "aliases", "cross_refs", "version"}
        assert required_keys.issubset(set(r.keys()))
        assert r["type"] == "subject_heading"
        assert r["uri"].startswith("https://id.loc.gov/")
