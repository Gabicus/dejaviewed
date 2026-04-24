# Keyword Association Engine · primer

Updated: 2026-04-24 12:45am EDT

## Current status

Project initialized. Plan finalized. No code written yet. Working directory: `keywords/` subdirectory of dejaviewed-plugin repo.

## What this is

Universal scientific keyword taxonomy engine. Ingests authoritative keyword hierarchies from 6 global sources ("pillars"), normalizes into unified schema, stores in DuckDB+Parquet, enables semantic matching against publication text, and cross-links concepts across taxonomies.

End goal: multi-modal analysis tool (VOSviewer x1000) that maps publication keywords, author keywords, and abstract-extracted terms into a navigable knowledge graph. Future integration with Web of Science, Scopus, Google Scholar, OpenAlex publication data.

## Architecture

```
Sources (6 pillars)
  ├── NASA GCMD (CSV) ─────────┐
  ├── UNESCO Thesaurus (SKOS) ─┤
  ├── NCBI Taxonomy (FTP dump) ┤
  ├── LoC Subject Headings ────┤──→ Parsers ──→ Unified Schema ──→ DuckDB + Parquet
  ├── DOE OSTI (API/flat list) ┤
  └── OpenAlex Topics (API) ───┘
                                        │
                              ┌─────────┴──────────┐
                              │  Association Engine │
                              │  (spaCy + embeddings)
                              └─────────┬──────────┘
                                        │
                              Cross-taxonomy alignment
                              (embeddings + manual top-level mapping)
```

### Unified schema
| Field | Type | Description |
|---|---|---|
| id | string | Source system unique ID |
| label | string | Primary keyword name |
| definition | string | Official definition/scope note |
| parent_id | string | Direct parent in hierarchy |
| source | string | Origin pillar |
| type | string | Category within source |
| uri | string | Persistent link |
| full_path | string | Hierarchical path |
| aliases | list[str] | Synonyms, abbreviations |
| level | int | Depth in hierarchy |
| cross_refs | list[str] | Equivalent concepts in other taxonomies |
| last_updated | datetime | Ingestion timestamp |
| version | string | Source version/revision |

### Tech stack
- **Storage:** DuckDB (primary, ACID transactions) + Parquet (export/interchange)
- **Matching:** spaCy PhraseMatcher (tier 1, exact) + sentence-transformers (tier 2, semantic)
- **Graph:** NetworkX (prototype) → Neo4j/SQLite recursive CTEs (production)
- **Data access:** PyAlex (OpenAlex), rdflib (SKOS/RDF), requests-cache (HTTP caching)
- **Analysis:** PyBibX (keyword co-occurrence), GROBID (PDF extraction, future)
- **Query:** DuckDB SQL for cross-taxonomy joins and pivoting

### Key dependencies (pip)
```
duckdb pyarrow spacy rdflib pyalex requests requests-cache networkx sentence-transformers
```

## Execution plan (5 phases)

### Phase 1: Foundation
- [ ] Project structure (dirs, requirements.txt, config)
- [ ] DuckDB schema + Parquet export utilities
- [ ] Upsert logic (atomic, with file locks or DuckDB transactions)
- [ ] Schema validation framework (record count checks, header drift detection)
- [ ] HTTP session helper (per-source CA bundles, requests-cache, User-Agent, retries)
- [ ] NASA GCMD parser (CSV, dynamic headers, all keyword types)
- [ ] UNESCO Thesaurus parser (SKOS/RDF via rdflib, English filter, hierarchy)
- [ ] Tests for parsers + storage

### Phase 2: Expansion
- [ ] LoC Subject Headings parser (Linked Data API, MARCXML bulk fallback)
- [ ] NCBI Taxonomy parser (FTP dump, depth cap at rank ≥ Order, ~1,200 nodes)
- [ ] DOE OSTI parser (subject categories, flat list ~300 items)
- [ ] OpenAlex Topics parser (4-level hierarchy, 26K keywords via PyAlex)
- [ ] Validation: all 6 pillars ingested, record counts verified

### Phase 2.5: Alignment
- [ ] Manual crosswalk for top ~200 root/branch nodes across taxonomies
- [ ] Embedding-based similarity for remaining nodes (sentence-transformers)
- [ ] LLM spot-check for ambiguous mappings
- [ ] Populate cross_refs field in unified schema
- [ ] Pivot query proof-of-concept (find NASA terms related to LoC heading)

### Phase 3: Intelligence (Association Engine)
- [ ] Keyword loader from DuckDB into spaCy PhraseMatcher
- [ ] AssociationEngine class (find_keywords, return matches with metadata + hierarchy)
- [ ] Embedding-based fallback for semantic matches
- [ ] Graph traversal (get_full_path, ancestors, descendants)
- [ ] Tests against real publication abstracts

### Phase 4: Integration
- [ ] CLI driver (update-datalake, associate-text, pivot-query)
- [ ] Publication keyword ingestion hooks (WoS, Scopus, OpenAlex works)
- [ ] Grant/funding number extractor (regex per agency pattern, separate module)
- [ ] Abstract NLP processing pipeline
- [ ] Cross-taxonomy pivoting module
- [ ] Documentation

## Key tools from existing ecosystem
| Tool | Role |
|---|---|
| PyAlex | OpenAlex API — 250M works, topic hierarchy, free |
| Pybliometrics | Scopus API (needs institutional access) |
| GROBID | PDF metadata extraction (Phase 4+) |
| PyBibX | Keyword co-occurrence analysis |
| Scholarly | Google Scholar scraper (fragile, gap-filler) |
| rdflib | SKOS/RDF parsing for UNESCO, LoC |
| requests-cache | HTTP caching for rate-limited APIs |

## Critical risks & mitigations
| Risk | Mitigation |
|---|---|
| Cross-taxonomy alignment takes 3x longer | Start manual mapping in Phase 1 for top nodes |
| LoC API flaky/slow | Bulk MARCXML download fallback |
| NCBI data too large | Depth cap at Order rank, stream processing |
| PhraseMatcher accuracy too low | Embedding fallback ready from Phase 3 start |
| Scope creep into publications | Hard boundary: no pub data until Phase 3 done |
| Parquet race conditions | DuckDB as primary store (ACID), Parquet as export |

## Don't forget
- ALWAYS be devil's advocate — challenge assumptions, no glass castles
- Audit between large steps for errors and gaps
- No `verify=False` blanket — pin CA bundles per source
- NCBI depth cap is configurable but default to Order rank
- OpenAlex is Pillar 6 — don't skip it
- Grant number extraction is SEPARATE module, not keyword engine
- Test parsers against real data, not mocks
- Push before destructive operations (always)

## Next up
1. Set up project directory structure
2. Write requirements.txt
3. Implement DuckDB schema + storage utilities
4. Build NASA GCMD parser (easiest pillar, best data quality)
