# CLAUDE.md — Cybernetics Ontology

## Protocol
Project-level working memory; takes precedence over the vault CLAUDE.md inside this folder. Follow `04 Resources/Claude Working Protocol.md` (trigger: "Update CLAUDE.md"). Latest handoff: `01 Notes/Session handoff 2026-10-20 NorbertX (ontology build and inference prototype).md`.

## Project snapshot
- **What:** RDF/OWL ontology (`02 Ontology/cybonto.ttl`, prefix `cyb:`, v0.1.0) and a generated graph for the Cybernetics Bookshelf.
  - Layer A is bibliographic, from the Calibre `metadata.db` schema.
  - Layer B is the index layer, from the CyberneticsNLP back-of-book indexes.
- **Notes:** hub `Cybernetics Ontology.md`; design `01 Notes/Design note 2026-10-20.md` (current; the 2026-10-19 note records the first build); prototype report `04 Prototype/2026-10-20/Inference prototype report 2026-10-20.md`.
- **Current build:** `03 Outputs/cyb-bibliographic 2026-10-20.ttl` + `cyb-index 2026-10-20.ttl`, about 1.36M triples, no publisher blurbs, from `00 Inputs/snapshot 2026-10-19/`.
  - The snapshot is the CyberneticsNLP repo's 20 Sep files: 755 books; canonical run analysed 575.
  - Validation: SHACL plus spot checks, `03 Outputs/validation 2026-10-20.txt`.
- **Run:** `python3 "_code/build_rdf.py" --snapshot "snapshot 2026-10-19" --tag <date>` (~2 min), then `_code/validate_rdf.py` with the same arguments (~3 min).
- **Prototype:** `_code/prototype/build_prototype.py`, then `infer_prototype.py --reasoner owlrl`.
- **Needs:** rdflib, pyshacl, owlrl, reasonable.

## Model rules (decided with Paul)
- Own `cyb:` namespace, aligned to standard vocabularies by subClassOf/subPropertyOf only (never equivalentClass) (19 Oct).
- Index layer: IndexEntry (string in one book) → IndexTerm (lowercased corpus key) → EntityClassification (method, confidence, provenance) → Entity. Kinds and publication types are non-disjoint; never add disjointness axioms, and never align to a strict upper ontology (BFO/DOLCE) (19 Oct; BFO clash shown 20 Oct).
- Classifications are provisional (CyberneticsNLP standing principle). Merges are recorded (`cyb:mergedInto`), never applied as identity; identity is to come from a reviewable resolver (20 Oct).
- No publisher blurbs (Calibre `comments`) in the graph (Paul, 20 Oct); `--include-descriptions` is for local use only. Publisher names stay (Claude's reading; to confirm).
- Namespace deliberately undecided (Paul, 20 Oct). Don't push for a decision.
- Book IRIs from the Calibre uuid. Tested 20 Oct: uuids survived the July rebuild, but a remove-and-re-add mints a new id and uuid, and Calibre reuses ids for different books. Never join index data and metadata from different snapshots.

## Current sprint
Awaiting Paul's review of the model and the prototype. Then: the name/entity resolver (persons first, then works) with a review list.

## Active issues
- No identity resolution yet: one entity per heading. "Wiener, N." and "Wiener, Norbert" are two persons, joined only by `cyb:mergedInto` in the core graph (prototype `resolution-sameas.ttl` shows the effect).
- Reference `metadata.db`: Paul intends GitHub, but the file is gitignored and not there, and the repo is public. Options (cleaned copy + manifest, or manifest only) not yet decided.

## Files modified this session (19–20 Oct 2026)
- 19 Oct: project created. `00 Inputs/snapshot 2026-10-19/` (+ MANIFEST); `02 Ontology/cybonto.ttl`, `cybonto-shapes.ttl`, `queries/01–06`; `_code/build_rdf.py`, `_code/validate_rdf.py`; `03 Outputs/* 2026-10-19` (graph files moved to `_to_delete`, as they contain blurbs); `01 Notes/Design note 2026-10-19.md/.html`.
- 20 Oct: `_code/build_rdf.py` (blurbs off by default); `03 Outputs/* 2026-10-20`; `01 Notes/Design note 2026-10-20.md/.html`; `02 Ontology/cybonto-extended-kinds.ttl`, `cybonto-alignments.ttl`, `stress-test-bfo.ttl`; `_code/prototype/`; `04 Prototype/2026-10-20/`; this file; hub; handoff note. Outside the project: `02 Projects/Human-AI Collaborative Practice/journal/Practice journal 2026-10.md` (entries 19 and 20 Oct); vault `CLAUDE.md` (project row).

## Next session agenda
1. Paul reviews the model + prototype report. Decide "Cold War" concept/event: one entity or two; confirm the publisher reading.
2. Name/entity resolver: candidate generation, scoring with book context, two thresholds, review list, decisions recorded as classifications. Persons first, then works.
3. Reference `metadata.db` location decision (GitHub manifest and/or cleaned copy).
4. Upstream CyberneticsNLP fixes (see Known issues U1–U5), in a repo session.
5. Re-add reconciliation between snapshots (title + date added, or PDF content hash).
6. Extended kinds: tighten event rules; extend classifier coverage; Wikidata reconciliation.
7. Move chain-derived relations into `build_rdf.py`; after review, promote the alignment module into the core.

## Infrastructure notes
- Source of `metadata.db` (Paul, 20 Oct): the CyberneticsNLP repo, `data/inputs/calibre/metadata.db`, via the sshfs mount at vault root `cybersonic/CyberneticsNLP/`. The mount goes stale often; ask Paul to run `mcyber`. Snapshots are taken from there, never from the Calibre library.
- `~/cybersonic/CyberneticsNLP/` on NorbertX is an older local copy (20 Sep). The repo's own CLAUDE.md wrongly gives the mount path as `02 Projects/CyberneticsNLP/cybersonic/`.
- The Calibre running library is on NorbertX at `~/Desktop/Cybernetic-Bookshelf/` (`metadata.db` of 14 Oct, newer than the repo's). Paul is not syncing it into CyberneticsNLP now. Read-only; it was used only for the uuid test via per-book OPFs.
- There is no Zhared drive on NorbertX. calibre-web's stale `/Volumes/Zhared` setting must not be followed.
- GitHub `cyberneticbookshelf-stack/cyberneticsNLP` is public and at the same commit as cybersonic (`1df4045`, 21 Sep). This session can read it but not push.
- Inputs are frozen snapshots with a sha256 MANIFEST; never read the live repo from the build script.
- Relative paths only: scripts resolve the project root from `_code/`'s parent.
- Calibre custom columns are bound by name (cc4/cc5 swapped in July 2026).
- The 09b merge-rule code in `_code/build_rdf.py` replicates `src/09b_build_index_analysis.py` (sha256 cc41d741…); re-verify if 09b changes.
- Prototype modules are not part of the core. `stress-test-bfo.ttl` is a test only; never load it in a real build.
- Reasoning: `owlrl` implements property chains; `reasonable` does not, silently. Reason over the entity-bearing slice only; the full 50-book subgraph (231k triples) exceeded 7 GB in OWL RL.
- Builds don't fit in one 3-minute call on NorbertX's Linux VM. Either Paul runs them on a Mac, or Claude builds in the cloud and transfers (compress files over 30 MB; verify sha256 on disk).
- Same-day second-session outputs get a letter suffix (`2026-10-20a`).

## Known issues (active)
| ID | Issue | Status |
|---|---|---|
| O1 | No entity identity resolution (one entity per heading) | Open — resolver is next |
| O2 | Rule-based new kinds noisy, esp. events (~35/40 plausible); duplicate work headings | Prototype only |
| O3 | Only about half of multi-book headings have a classification; none of the 118k single-book ones | Open (upstream classifier coverage) |
| O4 | Cross-vocabulary drift (e.g. Project Cybersyn as schema:Organization) is not flagged by reasoners | Needs review queries/SHACL |
| O5 | Snapshot (20 Sep) is older than the running library (9 re-adds, 1 new book) | Accepted; Paul not syncing now |
| U1 | `src/train_monograph_classifier.py:99` reads cc5 (Theme) as Publication Type | Reported, not fixed |
| U2 | `src/14_entity_network.py:314-327` collapses persons sharing a surname | Reported, not fixed |
| U3 | `src/09b_build_index_analysis.py:242-251` accent merge: wrong direction (`n_books` absent) + cross-language false merges | Reported, not fixed |
| U4 | 09b doesn't persist merge rules | Reported, not fixed |
| U5 | Calibre id reuse: id-keyed artefacts must be regenerated from one export | Reported |

*Last updated: 20 October 2026, 06:35 (NorbertX).*
