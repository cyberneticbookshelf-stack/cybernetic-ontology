# Cybernetics Ontology

**Started:** 19 October 2026 (NorbertX) · **Status:** v0.1.0 draft, awaiting Paul's review
**Program:** [[Cybernetics Bookshelf]] · **Feeds from:** [[CyberneticsNLP]] · **May feed:** [[CyberneticsAR]]
**Latest handoff:** `01 Notes/Session handoff 2026-10-20 NorbertX (ontology build and inference prototype).md`
**Archive after:** the ontology is adopted into CyberneticsNLP or published → `05 Archive/`

An RDF/OWL ontology and generated knowledge graph for the Cybernetics Bookshelf. It has a bibliographic layer derived from the Calibre `metadata.db` schema, and an index layer for the back-of-book indexes (persons, concepts, organisations, locations). In the index layer, an index entry (what a book prints) is kept separate from the entity it is judged to denote. The judgement is reified with its method and confidence.

## Layout

| Folder | Contents |
|---|---|
| `00 Inputs/snapshot YYYY-MM-DD/` | Frozen copies of `metadata.db`, `index_terms.json`, `index_vocab.json`, `entity_types_cache.json` + `MANIFEST.md` (sha256, source) |
| `01 Notes/` | Design note (md + html), session handoffs |
| `02 Ontology/` | `cybonto.ttl` (ontology), `cybonto-shapes.ttl` (SHACL), `queries/*.rq` |
| `03 Outputs/` | `cyb-bibliographic <date>.ttl`, `cyb-index <date>.ttl`, `build report <date>.md`, `validation <date>.txt` |
| `_code/` | `build_rdf.py`, `validate_rdf.py` (relative paths; needs rdflib, pyshacl) |
| `04 Prototype/<date>/` | Inference prototypes (50 books, mixed-ontology alignments, OWL RL); code in `_code/prototype/` |

## Current state (20 Oct 2026)

Build 2026-10-20 is from the 20 Sep inputs (confirmed identical to the repo): 755 books, 154,568 index entries, 128,108 terms, 5,053 entities, ~1.36M triples, no publisher blurbs. It passes SHACL and random spot checks. Read `01 Notes/Design note 2026-10-20.md` first; the 19 Oct note records the first build.

## Prototype (20 Oct 2026)

50-book test of inference over mixed ontologies (CIDOC-CRM, LRMoo, schema.org, PROV, SKOS): `04 Prototype/2026-10-20/Inference prototype report 2026-10-20.md`. Main findings: alignments give per-vocabulary views; property chains give a within-collection book-to-book network from indexes (30 links among 50 books); sameAs resolution changes counts (Wiener 16+5 -> 21); mixing produces consistent nonsense (Project Cybersyn as schema:Organization and crm:Event); a strict upper ontology (BFO) clashes with non-disjoint kinds; `reasonable` skips property chains, `owlrl` is about 10x slower.

## Decisions

- Publisher blurbs (`comments`) are not in the graph (Paul, 20 Oct). Publisher names stay.
- Namespace: left undecided (Paul, 20 Oct); `https://w3id.org/cybernetic-bookshelf/` is a placeholder.
- uuid stability tested 20 Oct. uuids survived the July rebuild (537 verified, 190 inferred). A remove-and-re-add mints a new id and uuid, and Calibre reuses ids. So uuid IRIs stay; reconciliation of re-added books between snapshots is still to build.

## Open

1. Whether the model (entry / term / classification / entity) is right before anything else builds on it.
2. Re-add reconciliation: title + date-added matching, or a PDF content hash as book key.

## Upstream issues raised (CyberneticsNLP)

See the design note §"Upstream issues": the classifier reads Theme as Publication Type (cc5); the entity network collapses persons who share a surname; 09b's accent merge goes in the wrong direction and makes cross-language false merges; 09b doesn't persist its merge rules.

## Next steps

Wikidata reconciliation, a PROV run layer and topic layer, persisting locators and sub-entries upstream, loading into a triple store.
