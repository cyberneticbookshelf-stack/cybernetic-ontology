---
title: Inference over mixed ontologies - 50-book prototype
date: 2026-10-20
status: prototype findings for Paul
---

# Inference over mixed ontologies: a 50-book prototype (20 October 2026)

## What was tested

The question was what a reasoner does with the Cybernetics Bookshelf graph once its own `cyb:` terms are aligned to several public ontologies at once. The ontologies were CIDOC-CRM, LRMoo, schema.org, PROV-O, FOAF and SKOS. The test took 50 books from the 2026-10-20 build:

- 16 purposive: copies of works that other indexes name, and books whose indexes mention Project Cybersyn, the Cold War, the Macy Conferences or "Wiener, N.";
- 34 drawn at random (seed 99), stratified by decade, from the 253 books whose index extracted cleanly ("ok", at least 100 headings).

The purposive books overrepresent the cases under test, so the counts below illustrate behaviour; they are not estimates for the collection. The full list is in `selection.md`.

New entity kinds were added to the 50-book subgraph by crude heading-pattern rules (confidence 0.5): event, project, work, artefact, period and group. Works named in indexes were linked to their copy in the collection where title and author surname both match. Three ontology modules sit beside the core: `cybonto-extended-kinds.ttl` (new kinds and derived relations defined by property chains), `cybonto-alignments.ttl` (subclass-only alignments, plus a marked excerpt of the external axioms the reasoner needs) and `stress-test-bfo.ttl` (a strict upper ontology, used only in scenario D).

| Scenario | Contents | Triples before → after OWL RL (owlrl) | Time |
|---|---|---|---|
| A core | data + core ontology | 71,468 → 144,890 | 49 s |
| B aligned | A + new kinds + alignments | 71,582 → 165,546 | 74 s |
| C resolved | B + stand-in name resolver (30 `owl:sameAs` between person variants, from 09b's initials rule) | 71,612 → 166,100 | 96 s |
| D strict | B + "one entity per heading across kinds" + BFO upper ontology | 71,623 → 171,024 | 74 s |

The reasoning ran on the slice of the subgraph that carries entities: 3,195 classified headings and their 4,960 index entries. The other 85% of headings in these books (17,753) have no classification, so no alignment or chain applies to them. Including them pushed OWL RL materialisation past 7 GB of memory.

## What inference added

**One graph, several vocabularies.** With the alignments loaded (B), the same data answers queries in each vocabulary's own terms, with nothing extra asserted:

- CIDOC-CRM: 676 E21 Person, 975 E39 Actor, 79 E5 Event, 33 E7 Activity, 6 E22 Human-Made Object;
- LRMoo: 226 F1 Work and 60 F3 Manifestation (the 50 books, plus 10 collection copies of indexed works);
- schema.org: 79 Event and 286 CreativeWork.

Scenario A, without the alignments, yields none of these; only the FOAF and SKOS types that the core ontology already declares appear.

**Derived relations.** The property chains produced 4,761 book → entity "index mentions". They also produced **30 book → book links**, where one book's index names a work held as another book in the collection. Some examples:

- *Whole Earth: The Many Lives of Stewart Brand* links to nine collection books, including *Laws of Form*, *Mind and Nature* and *Cybernetics*;
- *Think Tank Aesthetics* links to six, including *Design for a Brain*, *Brain of the Firm* and *Cybernetic Revolutionaries*;
- *Angels Fear* links to *Steps to an Ecology of Mind*.

This is a within-collection reference network built from indexes alone, without parsing bibliographies. Spot checks of four links against the raw indexes all matched.

**Name resolution.** Before resolution (B), "Wiener, Norbert" appears in 16 of the 50 books and "Wiener, N." in 5 others, as two separate persons. With the 30 `owl:sameAs` links (C), they become one person mentioned in **21** books. The same happens to Turing (3 → 5) and Minsky (2 → 3). Counting the raw index files for the same books gives exactly these figures. This is the reason to resolve identity before any entity-level counting. It also shows the cost: `owl:sameAs` copies every statement across the pair, so one wrong merge would contaminate both persons wholesale.

## What inference did not catch: three lessons about mixing

**Consistent nonsense.** In schema.org, Project is a subclass of Organization; in CIDOC-CRM, a project is an Activity, which is an Event, which is a Period. After inference, Project Cybersyn is simultaneously a `schema:Organization`, a `crm:E7_Activity`, a `crm:E5_Event`, a `crm:E4_Period` and a `prov:Activity`. Nothing is formally contradicted, because neither vocabulary declares the relevant classes disjoint, so the reasoner raises no flag. Yet a query for "organisations" in schema.org terms now returns projects. More broadly, a query for CIDOC "periods" returns 86 resources: 7 periods and all 79 events. Mixed alignments need review queries or SHACL checks for this kind of drift; consistency checking alone won't find it.

**Strict upper ontologies break non-disjoint kinds.** Scenario D merges the per-kind entities of each heading into one entity: "Cold War" as concept and as event become the same resource. The concept entity also inherits the BFO alignment as a continuant and the event entity as an occurrent, which BFO declares disjoint. That gives **24 clashes**, the concept/event pairs of 12 headings: Cold War, Cuban Missile Crisis, Industrial Revolution, Macy Conferences, Project Cybersyn, Marshall Plan, the world wars and others. CIDOC-CRM accepts the same merged resources silently.

The current design mints one entity per kind and per heading, so the clash cannot arise. But it means "Cold War the concept" and "Cold War the event" are two resources. Whether they should be one is a modelling decision, and a strict upper ontology would forbid it.

**Reasoners differ in what they implement.** `reasonable` (Rust) completes each scenario in 8–9 s but silently skips property chains (OWL 2 RL rule prp-spo2), so every derived relation came out as zero. `owlrl` (the Python reference implementation) does chains but takes 50–100 s on 72k triples, about 10× slower. Neither reported the BFO clash itself: `owlrl` collects inconsistencies as messages rather than failing, and `reasonable` skips the disjointness rule. The 24 clashes were found by an explicit query. Verifying a reasoner's coverage on a toy case before trusting its output turned out to be necessary.

## Quality of the rule-based new kinds

A random sample of 40 of the 356 rule-based classifications was checked by reading the headings (Claude's judgement, not yours):

- **Overall:** 35 were plausible.
- **Works:** almost all right, because the rule requires the parenthetical to be a known person surname.
- **Events:** the weakest kind. "Freudian Revolution" and "Automatization of War" are concepts or topics; "Humanitarian Crisis" is generic; "pre-cold war" is a period fragment.

The same work can also appear under two headings, e.g. *Steps to an Ecology of Mind* "(G. Bateson)" and "(Bateson)". Works need the same name resolution as persons.

## What this suggests

- **Keep the alignments subclass-only, to loose vocabularies.** CIDOC-CRM, LRMoo, schema.org, PROV and SKOS combine without contradiction. Avoid tying to a strict upper ontology such as BFO or DOLCE unless the non-disjoint-kinds principle is given up.
- **Materialise simple derived relations in the build script.** These are the index-mention chain and the book → book network; doing them in Python is cheap. Keep a reasoner for alignment views and consistency checks rather than for everything. At full collection scale (about 1.4M triples) `owlrl` would be slow. A triple store with OWL RL rules (GraphDB, RDFox, Jena) is the practical route.
- **Add review checks for cross-vocabulary drift**, such as "anything that is both an Organization and an Event". Inference won't raise these itself.
- **The name resolver stays the priority.** It decides what gets counted, and an `owl:sameAs` mistake propagates everywhere. The book → book network is the most promising new output, and its quality depends on resolving works as well as persons.

## Files (in `04 Prototype/2026-10-20/` unless noted)

- `selection.md`: books, reasons, rule-based classifications, work → copy matches, sameAs list.
- `asserted.ttl`: the 50-book subgraph plus prototype classifications.
- `resolution-sameas.ttl` and `same-term-identity.ttl`: the inputs to scenarios C and D.
- `results-owlrl.json` and `results-reasonable.json`: all measurements per scenario.
- `inferred-B-owlrl.ttl`: the closure for scenario B.
- Ontology modules: `02 Ontology/cybonto-extended-kinds.ttl`, `cybonto-alignments.ttl`, `stress-test-bfo.ttl`.
- Code: `_code/prototype/build_prototype.py`, `_code/prototype/infer_prototype.py`.

To rerun, from the project root (needs rdflib, owlrl, reasonable):

```
python3 "_code/prototype/build_prototype.py" --snapshot "snapshot 2026-10-19" --tag 2026-10-20
python3 "_code/prototype/infer_prototype.py" --tag 2026-10-20 --reasoner owlrl
```
