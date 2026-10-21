# Cybernetics Ontology

An RDF/OWL ontology (`cyb:`, v0.1.0) and a graph-building pipeline for the Cybernetics Bookshelf, a collection of about 750 books on cybernetics. It has two layers:

- **Layer A, bibliographic:** books, creators, publishers and dates, from the Calibre `metadata.db`.
- **Layer B, index:** the books' back-of-book indexes, as extracted by [CyberneticsNLP](https://github.com/cyberneticbookshelf-stack/cyberneticsNLP).

The index layer keeps a string apart from what it refers to: **IndexEntry** (a heading in one book) → **IndexTerm** (the normalised key across the corpus) → **EntityClassification** (method, confidence, provenance) → **Entity**. Classifications are provisional, and entity kinds are deliberately not disjoint. Alignment to standard vocabularies (DC Terms, BIBO, FOAF, SKOS, PROV; CIDOC-CRM, LRMoo and schema.org in the prototype) is by `rdfs:subClassOf` / `rdfs:subPropertyOf` only.

The namespace `https://w3id.org/cybernetic-bookshelf/` is a placeholder and not yet registered.

## Layout

| Folder | Contents |
|---|---|
| `00 Inputs/` | Frozen input snapshots. Only each snapshot's `MANIFEST.md` (sources and sha256) is published; see below. |
| `01 Notes/` | Design notes (`.md`, with `.html` copies) and session handoffs. |
| `02 Ontology/` | `cybonto.ttl` (core), `cybonto-shapes.ttl` (SHACL), alignment and extended-kinds modules, example SPARQL queries. `stress-test-bfo.ttl` is a test only; never load it in a real build. |
| `03 Outputs/` | Build reports, validation results, query results. The generated graphs are not published. |
| `04 Prototype/` | A 50-book inference prototype over mixed ontologies: report, selection, query results. |
| `_code/` | `build_rdf.py`, `validate_rdf.py`, `prototype/`. |

`CLAUDE.md` is the project's working memory for AI-assisted sessions. `Cybernetics Ontology.md` is the project hub (an Obsidian note).

## What is not in this repository

The Calibre catalogue is published as a cleaned copy, `00 Inputs/snapshot 2026-10-19/metadata-public.db`. It leaves out the publisher blurbs, ratings, reading positions, annotations and personal GUI settings; the MANIFEST lists what was removed and the checksums of both copies. The index files (`index_terms.json`, `index_vocab.json`, `entity_types_cache.json`) and the graphs built from them are kept out, as in CyberneticsNLP. To rebuild, place a snapshot with `metadata.db` and those three files under `00 Inputs/<snapshot>/` and check the files against its MANIFEST.

## Running

All paths are relative to the repository root. Requires Python 3 with `rdflib`, `pyshacl`, `owlrl` and `reasonable`.

```
python3 "_code/build_rdf.py" --snapshot "snapshot 2026-10-19" --tag <YYYY-MM-DD>
python3 "_code/validate_rdf.py" --snapshot "snapshot 2026-10-19" --tag <YYYY-MM-DD>
python3 "_code/prototype/build_prototype.py"
python3 "_code/prototype/infer_prototype.py" --reasoner owlrl
```

## Licence

MIT (see `LICENSE`), for the code and the ontology files.
