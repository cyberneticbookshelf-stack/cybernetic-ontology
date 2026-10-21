# Snapshot 2026-10-19

Copied 19 Oct 2026 (NorbertX) from the local copy of the CyberneticsNLP repo (`~/cybersonic/CyberneticsNLP/`, state of 20 Sep 2026), because the sshfs mount was stale at the time. When the mount came back the same day, all four files were confirmed **byte-identical (sha256) to the live repo**.

They are the outputs of the 20 September 2026 growth run: 755 Calibre books; canonical run `run_20260920_k9_s5` analysed 575.

| File | Repo path | sha256 |
|---|---|---|
| `metadata.db` | `data/inputs/calibre/metadata.db` | `9fae4a496a67895ccbb2fd9a7825231c8a7d169c1679d60b25479100ee29cd91` |
| `index_terms.json` | `json/index_terms.json` (09_extract_index.py) | `150ce726a089fdb1d9b741e38c5c6240d188236e435a22e118c70351270eee38` |
| `index_vocab.json` | `json/index_vocab.json` (09_extract_index.py) | `eafd052e04d636072f29e90d4fd112ada1c46c381ca5e12bd6de06b1f1e0cf2b` |
| `entity_types_cache.json` | `json/entity_types_cache.json` (15_entity_classify.py) | `c1801b106163eda28313cb90f4a990c943ad2fd72bac9147022ca1d15290c9c6` |

Code replicated in `_code/build_rdf.py`: `src/09b_build_index_analysis.py`, sha256 `cc41d741cdef2ae6484cf84d6b6702c498a9cd191d7f2105697d8841e88d69b3` (identical in the local copy and the live repo).

Not used: `entity_network.json`. The local copy (20 Sep, 11:50) differs from the live one, which was rebuilt that evening. The ontology does not depend on it; the cross-check that all network nodes have a classification was run on the local copy.

## Public copy of `metadata.db` (21 Oct 2026, AshbyX)

`metadata-public.db` is the copy of `metadata.db` published on GitHub (Paul, 21 Oct). It is a cleaned copy of the file above (sha256 `9fae4a49…`):

- Removed: publisher blurbs (`comments`), ratings (`ratings`, `books_ratings_link`), reading position (`last_read_positions`), annotations, `conversion_options`, and personal Calibre GUI settings in `preferences` (saved searches, virtual libraries, user categories, view state, plugin settings).
- Kept: everything else, unchanged. That is books, authors, publishers, identifiers, tags, languages, series, pages, formats and custom columns. Integrity check: ok. VACUUMed.
- sha256 `334b7a1e9bac03afce1be42d25b1f5f4ca7e0d376136669259592b44f695d7a7`.

Check (21 Oct): `build_rdf.py` was run on both copies. The index graph is identical. The bibliographic graph differs only by the 144 `cyb:rating` triples (43,837 vs 43,693 triples).

To build from the public copy, rename it to `metadata.db` in a snapshot folder with the three index JSONs. They are not published, as in CyberneticsNLP.
