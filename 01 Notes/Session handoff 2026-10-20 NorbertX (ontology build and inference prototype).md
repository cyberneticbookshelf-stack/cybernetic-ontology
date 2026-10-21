# Session handoff — 19–20 October 2026, NorbertX (Cybernetics Ontology: build and inference prototype)

*Cloud session linked to NorbertX. Model as configured: claude-opus-5-5 (serving model may differ). Covers the sessions of 19 Oct (afternoon) and 20 Oct (05:00–06:30).*

## Where things stand

The Cybernetics Ontology is a new vault project, created on 19 Oct at Paul's request, separate from the CyberneticsNLP repo. It has:
- a core ontology (`02 Ontology/cybonto.ttl`, v0.1.0) with SHACL shapes and six example queries;
- a build script and a validator (`_code/build_rdf.py`, `_code/validate_rdf.py`);
- a validated graph of the full collection, build 2026-10-20 (`03 Outputs/cyb-bibliographic 2026-10-20.ttl` and `cyb-index 2026-10-20.ttl`, about 1.36M triples, no publisher blurbs);
- a 50-book prototype testing inference over mixed ontologies (`04 Prototype/2026-10-20/`).

Paul has not yet reviewed the model. Start with `01 Notes/Design note 2026-10-20.md`, then `04 Prototype/2026-10-20/Inference prototype report 2026-10-20.md`.

## What was done

**19 Oct.**
- Surveyed `metadata.db` and the index files.
- Agreed the design with Paul through four choices:
  - ontology plus population script;
  - own `cyb:` namespace aligned by subclassing;
  - index entry kept separate from the entity it denotes;
  - a new vault project.
- Froze the inputs as `00 Inputs/snapshot 2026-10-19/`. They are byte-identical to the repo's 20 Sep files; checksums are in its MANIFEST.
- Built and validated the graph: SHACL, vocabulary closure, random spot checks against the sources.
- Replicated 09b's name merges and verified them against 09b's own output.
- Found four upstream issues in CyberneticsNLP (below).

**20 Oct.**
- Recapped the four-level model for Paul.
- Tested uuid stability (design note 2026-10-20 §"Book identity").
- Rebuilt without publisher blurbs.
- Answered questions on:
  - feasibility and extensibility;
  - whether to merge name variants first (yes, at the entity level, as a reversible resolution step);
  - which other entity kinds the indexes contain;
  - public ontologies, and how to mix them.
- Built and ran the 50-book inference prototype.

## Decisions (with reasons)

- **Index layer has four levels:** entry → term → classification → entity. The step from string to entity is a provisional judgement, so it carries method, confidence and provenance (principle of context). Entity kinds are not disjoint.
- **Alignment by subclass only**, never `owl:equivalentClass`, to loose vocabularies (DC Terms, BIBO, FOAF, SKOS, PROV; in the prototype also CIDOC-CRM, LRMoo, schema.org). This keeps the `cyb:` terms narrowable and avoids inferences running backwards. The prototype showed that a strict upper ontology (BFO) conflicts with non-disjoint kinds.
- **Book IRIs from the Calibre uuid.**
  - uuids survived the July rebuild: 537 books verified from OPFs written before July, 190 more inferred because their ids are unchanged.
  - Removing and re-adding a book mints a new id and a new uuid, and Calibre reuses ids for different books. A uuid IRI fails safe (it dangles); an id can silently point at the wrong book.
- **No publisher blurbs in the graph** (Paul, 20 Oct). Claude read "publisher" as the blurbs; publisher names were kept. Confirm this reading.
- **Namespace deliberately undecided** (Paul, 20 Oct). `https://w3id.org/cybernetic-bookshelf/` stays a placeholder.
- **Source of `metadata.db`** (Paul, 20 Oct). The reference is the CyberneticsNLP copy (`data/inputs/calibre/metadata.db`). Paul intends GitHub to hold the reference, but the file is gitignored and not on GitHub, and the repo is public. Options were set out (cleaned copy plus manifest, or manifest only); no decision yet.
- **The Desktop Calibre library** (`~/Desktop/Cybernetic-Bookshelf/`) is Paul's running library. It hasn't been imported into CyberneticsNLP, and Paul is not syncing it now. It was used only as read-only evidence for the uuid test.

## Prototype findings (summary; full detail in the report)

- **Per-vocabulary views:** with the alignments loaded, the same data answers queries in CIDOC-CRM, LRMoo and schema.org terms, with nothing extra asserted.
- **A book-to-book network from indexes:** property chains derived 30 links among the 50 books where one book's index names a work held in the collection. Examples: the Stewart Brand biography links to nine books; *Angels Fear* links to *Steps to an Ecology of Mind*. Spot-checked against the raw indexes.
- **Identity resolution changes the counts:** Wiener goes from 16 + 5 books under two name forms to 21 as one person; Turing 3 → 5. All of these match the raw indexes.
- **Consistent nonsense:** Project Cybersyn becomes both `schema:Organization` and `crm:E7_Activity`. No reasoner flags this, so review queries are needed.
- **BFO stress test:** the concept/event pairs of 12 headings give 24 clashes.
- **Reasoner differences:** `reasonable` silently skips property chains; `owlrl` handles them but is about 10× slower. OWL RL on the full 50-book subgraph exceeded 7 GB, so reasoning ran on the slice that carries entities.
- **Rule-based new kinds:** about 35 of 40 sampled looked right (Claude's reading). Works were strong and events weak, and works need name resolution too.

## Upstream issues found in CyberneticsNLP (reported, not fixed)

1. `src/train_monograph_classifier.py:99` hard-codes `PUBLICATION_TYPE_COL = 5`. Since July, column 5 is Theme, so any retraining since then has used the wrong labels.
2. `src/14_entity_network.py:314-327` keeps one person per surname. Mary Catherine Bateson and Julian Huxley are missing from the network as a result.
3. `src/09b_build_index_analysis.py:242-251`: the accent merge reads `n_books`, which `index_vocab.json` doesn't have, so the accented form always wins (`system` → `systém`). It also merges words across languages (`regulation`/`régulation`).
4. 09b doesn't persist its merge rules; the ontology build re-implements them.
5. (20 Oct) Calibre reuses ids. On the next re-export, every artefact keyed by book id must be regenerated from the same export.

## Next session agenda (in order)

1. Paul reviews the model and the prototype report. Decisions needed: should "Cold War" as concept and as event be one entity or two? Is the publisher reading right?
2. Build the name/entity resolver:
   - persons first, then works;
   - candidate generation, scoring with book context, two thresholds;
   - a review list for Paul;
   - decisions recorded as classifications.
3. Decide where the reference `metadata.db` lives (GitHub manifest and/or cleaned copy).
4. Fix the upstream CyberneticsNLP issues 1–5, in a repo session.
5. Reconcile re-added books between snapshots (match on title + date added, or a PDF content hash).
6. Extended kinds: tighten the event rules; extend classifier coverage (half of multi-book headings have no classification); reconcile against Wikidata.
7. Move the chain-derived relations into `build_rdf.py`; after review, promote the alignment module into the core.

## How to resume

- Read the project `CLAUDE.md` first.
- The repo is on the sshfs mount at vault root `cybersonic/CyberneticsNLP/`, which goes stale often; ask Paul to run `mcyber`.
- Build: `python3 "_code/build_rdf.py" --snapshot "snapshot 2026-10-19" --tag <date>` (about 2 min), then `_code/validate_rdf.py` (about 3 min).
- Prototype: `_code/prototype/build_prototype.py`, then `infer_prototype.py --reasoner owlrl`.
- Needs rdflib, pyshacl, owlrl and reasonable. Builds don't fit in a single 3-minute call on NorbertX's Linux VM, so either Paul runs them on a Mac with Anaconda, or Claude builds in the cloud and transfers the output (large files compressed; verify sha256 on disk).
- Same-day second sessions use a letter suffix (`2026-10-20a`).
- `_to_delete/Cybernetics Ontology 2026-10-19` and `… 2026-10-20` (vault root) hold transfer copies and the superseded 19 Oct graph files, which contained blurbs. Paul can delete both.
