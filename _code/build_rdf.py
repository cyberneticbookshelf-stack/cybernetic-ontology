#!/usr/bin/env python3
"""
build_rdf.py - generate RDF instance data for the Cybernetics Bookshelf
Ontology (02 Ontology/cybonto.ttl) from a frozen input snapshot.

Inputs (one snapshot folder, see 00 Inputs/<snapshot>/MANIFEST.md):
  metadata.db              Calibre library database (read-only, immutable)
  index_terms.json         per-book index headings   (09_extract_index.py)
  index_vocab.json         corpus index vocabulary   (09_extract_index.py)
  entity_types_cache.json  term classifications      (15_entity_classify.py)

Outputs (03 Outputs/):
  cyb-bibliographic <tag>.ttl   books, creators, publishers, tags, types ...
  cyb-index <tag>.ttl           index entries, terms, classifications, entities
  build report <tag>.md         counts, skipped items, input checksums

All paths are relative to the project root (the folder above _code/), so the
project runs unchanged on any machine.

Usage (from anywhere):
  python3 "_code/build_rdf.py" --snapshot "snapshot 2026-10-19" --tag 2026-10-19
  Publisher blurbs (Calibre 'comments') are NOT included (Paul, 20 Oct 2026).
  options: --include-descriptions   add them (local use only; never in a shared graph)

Requires: rdflib (pip install rdflib).
"""
import argparse, collections, datetime as dt, hashlib, json, re, sqlite3, sys
import unicodedata
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS, XSD, DCTERMS, FOAF, PROV

ROOT = Path(__file__).resolve().parent.parent          # project root
BASE = "https://w3id.org/cybernetic-bookshelf/"         # PLACEHOLDER namespace
CYB  = Namespace(BASE + "ontology#")
ID   = Namespace(BASE + "id/")
BIBO = Namespace("http://purl.org/ontology/bibo/")
ISO639 = "http://id.loc.gov/vocabulary/iso639-2/"

# ── helpers ─────────────────────────────────────────────────────────────────

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def _slug(s: str, maxlen: int = 80) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:maxlen].strip("-")

def slug_map(keys):
    """Deterministic key -> IRI-safe slug. Colliding keys (and empty slugs)
    all receive a short hash suffix, so no key silently takes another's IRI."""
    groups = collections.defaultdict(list)
    for k in keys:
        groups[_slug(k)].append(k)
    out = {}
    for s, ks in groups.items():
        if s and len(ks) == 1:
            out[ks[0]] = s
        else:
            for k in ks:
                h = hashlib.sha1(k.encode("utf-8")).hexdigest()[:8]
                out[k] = f"{s}-{h}" if s else f"x-{h}"
    return out

def year_of(ts):
    """Calibre pubdate -> gYear literal, or None for Calibre's 'undefined'
    sentinel (year 0101). Only the year is treated as meaningful."""
    if not ts or ts.startswith("0101"):
        return None
    return Literal(ts[:4], datatype=XSD.gYear)

def dt_lit(ts):
    if not ts:
        return None
    try:
        return Literal(dt.datetime.fromisoformat(ts).isoformat(), datatype=XSD.dateTime)
    except ValueError:
        return None

# ── term merges: REPLICATES src/09b_build_index_analysis.py (sha256 cc41d741…,
#    verified identical to the live repo on 2026-10-19). 09b does not persist its
#    merge rules; if 09b changes, this block must be re-synced (upstream fix:
#    have 09b write json/index_merge_rules.json and read that here). ───────────

def _accent_key(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def _is_clean_name(term):
    if ',' not in term: return False
    first = term.split(',', 1)[1].strip()
    if re.search(r'\d', first): return False
    if re.search(r'[;:]', first): return False
    if len(first) > 30: return False
    return True

def _firstname_fullwords(term):
    first = term.split(',', 1)[1].strip() if ',' in term else ''
    return sum(1 for w in first.split() if len(w) > 2 and not w.endswith('.') and w.isalpha())

def _is_initial_of(vfirst, cfirst):
    vw, cw = vfirst.split(), cfirst.split()
    if len(vw) > len(cw): return False
    return all(v == c or (len(v.rstrip('.')) == 1 and v.rstrip('.') == c[0]) for v, c in zip(vw, cw))

def person_merge_rules(IV):
    PERSON_PAT = re.compile(r'^[A-Z][\w\-]+(?:\s+[A-Z][\w\-]+)*,\s', re.UNICODE)
    groups = collections.defaultdict(list)
    for tl, v in IV.items():
        nb = v.get('n_books', v.get('count', 0))
        if nb < 2: continue
        if PERSON_PAT.match(v['term']):
            groups[tl.split(',')[0].strip()].append((tl, v['term'], nb))
    merge = {}
    for surname, entries in groups.items():
        clean = [(tl, t, nb) for tl, t, nb in entries if _is_clean_name(t)]
        if len(clean) <= 1: continue
        max_nb = max(nb for _, _, nb in clean)
        def _score(e):
            _, t, nb = e
            fw = _firstname_fullwords(t)
            return (fw if (nb / max_nb) >= 0.08 else max(fw - 1, 0), nb)
        clean.sort(key=lambda x: (-_score(x)[0], -_score(x)[1]))
        ctl, cterm, _ = clean[0]
        cfirst = cterm.split(',', 1)[1].strip()
        for tl, term, nb in clean[1:]:
            if tl == ctl: continue
            if _is_initial_of(term.split(',', 1)[1].strip(), cfirst):
                merge[tl] = ctl
    return merge

def accent_merge_rules(IV):
    merge = {}
    for tl, v in IV.items():
        norm = _accent_key(tl)
        if norm != tl and norm in IV:
            if v.get("n_books", 0) >= IV[norm].get("n_books", 0):
                merge[norm] = tl
            else:
                merge[tl] = norm
    return merge

# ── main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True, help="folder name under '00 Inputs/'")
    ap.add_argument("--tag", required=True, help="date tag for output names, e.g. 2026-10-19")
    ap.add_argument("--include-descriptions", action="store_true")
    a = ap.parse_args()

    snap = ROOT / "00 Inputs" / a.snapshot
    outd = ROOT / "03 Outputs"
    outd.mkdir(exist_ok=True)
    inputs = ["metadata.db", "index_terms.json", "index_vocab.json", "entity_types_cache.json"]
    for f in inputs:
        if not (snap / f).exists():
            sys.exit(f"missing input: 00 Inputs/{a.snapshot}/{f}")

    report = collections.OrderedDict()
    notes = []

    # ── A. bibliographic layer ─────────────────────────────────────────────
    g = Graph()
    for p, ns in [("cyb", CYB), ("id", ID), ("bibo", BIBO), ("dcterms", DCTERMS),
                  ("skos", SKOS), ("foaf", FOAF), ("prov", PROV)]:
        g.bind(p, ns)

    db = sqlite3.connect(f"file:{snap / 'metadata.db'}?mode=ro&immutable=1", uri=True)
    q = lambda sql, *args: db.execute(sql, args).fetchall()

    lib_uuid = q("select uuid from library_id")[0][0]
    LIB = ID[f"library/{lib_uuid}"]
    g.add((LIB, RDF.type, CYB.CalibreLibrary))
    g.add((LIB, RDFS.label, Literal("Cybernetics Bookshelf Calibre library")))

    books = q("select id,title,sort,timestamp,pubdate,series_index,author_sort,path,uuid,has_cover,last_modified from books")
    B = {}                                   # calibre id -> (IRI, uuid)
    for (bid, title, sort, ts, pub, sidx, asort, path, uuid, cover, lm) in books:
        u = ID[f"book/{uuid}"]
        B[bid] = (u, uuid)
        g.add((u, RDF.type, CYB.Book))
        g.add((u, CYB.inLibrary, LIB))
        g.add((u, CYB.calibreId, Literal(bid, datatype=XSD.integer)))
        g.add((u, CYB.calibreUuid, Literal(uuid)))
        g.add((u, DCTERMS.title, Literal(title)))
        if sort and sort != title:
            g.add((u, CYB.sortTitle, Literal(sort)))
        if asort:
            g.add((u, CYB.authorSort, Literal(asort)))
        y = year_of(pub)
        if y is not None:
            g.add((u, DCTERMS.issued, y))
        for p_, v in [(CYB.addedToLibrary, ts), (DCTERMS.modified, lm)]:
            l = dt_lit(v)
            if l is not None:
                g.add((u, p_, l))
        g.add((u, CYB.hasCover, Literal(bool(cover))))
        g.add((u, CYB.libraryPath, Literal(path)))
    report["books"] = len(B)
    report["books without a usable pubdate"] = sum(1 for b in books if year_of(b[4]) is None)

    # creators + authorship order (link-row id order = Calibre author order)
    authors = q("select id,name,sort from authors")
    aslug = slug_map([n for _, n, _ in authors])
    A = {}
    for aid, name, sort in authors:
        u = ID[f"creator/{aslug[name]}"]
        A[aid] = (u, name, sort)
        g.add((u, RDF.type, CYB.Creator))
        g.add((u, FOAF.name, Literal(name)))
        if sort:
            g.add((u, CYB.sortName, Literal(sort)))
    pos = collections.Counter()
    for _, book, author in q("select id,book,author from books_authors_link order by book,id"):
        if book not in B or author not in A:
            continue
        pos[book] += 1
        bu, buuid = B[book]
        au = ID[f"book/{buuid}/authorship/{pos[book]}"]
        g.add((bu, CYB.hasAuthorship, au))
        g.add((au, RDF.type, CYB.Authorship))
        g.add((au, CYB.agent, A[author][0]))
        g.add((au, CYB.position, Literal(pos[book], datatype=XSD.positiveInteger)))
        g.add((bu, DCTERMS.creator, A[author][0]))
    report["creators"] = len(A)
    report["authorship links"] = sum(pos.values())

    def lookup_table(table, link, cls, prop, prefix, scheme=None, label_prop=None):
        rows = q(f"select id,name from {table}")
        sm = slug_map([n for _, n in rows])
        M = {}
        for i, n in rows:
            u = ID[f"{prefix}/{sm[n]}"]
            M[i] = u
            g.add((u, RDF.type, cls))
            g.add((u, label_prop or RDFS.label, Literal(n)))
            if scheme is not None:
                g.add((u, SKOS.inScheme, scheme))
        n_links = 0
        for book, val in q(f"select book,{link[1]} from {link[0]}"):
            if book in B and val in M:
                g.add((B[book][0], prop, M[val])); n_links += 1
        return len(M), n_links

    report["publishers"], report["publisher links"] = lookup_table(
        "publishers", ("books_publishers_link", "publisher"), CYB.Publisher, CYB.publishedBy, "publisher", label_prop=FOAF.name)
    report["tags"], report["tag links"] = lookup_table(
        "tags", ("books_tags_link", "tag"), CYB.Tag, CYB.hasTag, "tag", CYB.TagScheme, SKOS.prefLabel)
    report["series"], report["series links"] = lookup_table(
        "series", ("books_series_link", "series"), CYB.Series, CYB.inSeries, "series")
    for bid, sidx in q("select b.id, b.series_index from books b join books_series_link l on l.book=b.id"):
        g.add((B[bid][0], CYB.seriesIndex, Literal(str(sidx), datatype=XSD.decimal)))

    # languages -> ISO 639-2 IRIs (Calibre lang_code is NOT reliable; see design note)
    for book, code in q("select l.book, g.lang_code from books_languages_link l join languages g on g.id=l.lang_code"):
        if book in B:
            g.add((B[book][0], DCTERMS.language, URIRef(ISO639 + code)))

    # ratings (0-10)
    for book, r in q("select l.book, r.rating from books_ratings_link l join ratings r on r.id=l.rating"):
        if book in B and r is not None:
            g.add((B[book][0], CYB.rating, Literal(r, datatype=XSD.integer)))

    # page counts (0 = not counted)
    for book, pages in q("select book, pages from books_pages_link"):
        if book in B and pages:
            g.add((B[book][0], CYB.pageCount, Literal(pages, datatype=XSD.integer)))

    # descriptions (publisher blurbs; HTML)
    if a.include_descriptions:
        n = 0
        for book, text in q("select book, text from comments"):
            if book in B and text and text.strip():
                g.add((B[book][0], DCTERMS.description, Literal(text))); n += 1
        report["descriptions"] = n
    else:
        report["descriptions"] = "not included (default; publisher blurbs excluded by decision 20 Oct 2026)"

    # identifiers
    n_id = 0
    for book, typ, val in q("select book, type, val from identifiers"):
        if book not in B:
            continue
        bu, buuid = B[book]
        iu = ID[f"book/{buuid}/identifier/{_slug(typ) or 'x'}"]
        g.add((bu, CYB.hasIdentifier, iu))
        g.add((iu, RDF.type, CYB.Identifier))
        g.add((iu, CYB.identifierScheme, Literal(typ)))
        g.add((iu, CYB.identifierValue, Literal(val)))
        if typ == "isbn":
            g.add((bu, BIBO.isbn, Literal(val)))
        elif typ == "doi":
            g.add((bu, BIBO.doi, Literal(val)))
        n_id += 1
    report["identifiers"] = n_id

    # files
    n_f = 0
    for book, fmt, size, name in q("select book, format, uncompressed_size, name from data"):
        if book not in B:
            continue
        bu, buuid = B[book]
        fu = ID[f"book/{buuid}/file/{_slug(fmt)}"]
        g.add((bu, CYB.hasFile, fu))
        g.add((fu, RDF.type, CYB.BookFile))
        g.add((fu, CYB.fileFormat, Literal(fmt)))
        g.add((fu, CYB.fileName, Literal(f"{name}.{fmt.lower()}")))
        g.add((fu, CYB.byteSize, Literal(size, datatype=XSD.integer)))
        n_f += 1
    report["book files"] = n_f

    # custom columns - bound by NAME, never by number (cc4/cc5 swapped in July 2026)
    cc = {name: (cid, normalized) for cid, name, normalized in q("select id, name, normalized from custom_columns")}
    def cc_values(name):
        if name not in cc:
            notes.append(f"custom column {name!r} not found; skipped")
            return []
        cid, normalized = cc[name]
        if normalized:
            return q(f"select l.book, t.value from books_custom_column_{cid}_link l join custom_column_{cid} t on t.id=l.value")
        return q(f"select book, value from custom_column_{cid}")
    report["custom column ids (by name)"] = {k: v[0] for k, v in cc.items()}

    n = 0
    for book, url in cc_values("URL"):
        if book in B and url and url.strip():
            g.add((B[book][0], CYB.sourceUrl, Literal(url.strip(), datatype=XSD.anyURI))); n += 1
    report["source URLs"] = n

    def concept_column(name, cls, scheme, prop, prefix, split=False):
        vals = collections.defaultdict(set)
        for book, v in cc_values(name):
            if book not in B or not v:
                continue
            parts = [p.strip().lower() for p in v.split(",")] if split else [v.strip()]
            for p_ in parts:
                if p_:
                    vals[p_].add(book)
        sm = slug_map(list(vals))
        for v, bs in vals.items():
            u = ID[f"{prefix}/{sm[v]}"]
            g.add((u, RDF.type, cls)); g.add((u, SKOS.prefLabel, Literal(v)))
            g.add((u, SKOS.inScheme, scheme))
            for b in bs:
                g.add((B[b][0], prop, u))
        return {v: len(bs) for v, bs in sorted(vals.items(), key=lambda kv: -len(kv[1]))}

    report["publication types (books per type; non-disjoint)"] = concept_column(
        "Publication Type", CYB.PublicationType, CYB.PublicationTypeScheme, CYB.hasPublicationType, "pubtype", split=True)
    report["themes"] = concept_column("Theme", CYB.Theme, CYB.ThemeScheme, CYB.hasTheme, "theme")
    report["sources (Available at)"] = concept_column("Available at", CYB.Source, CYB.SourceScheme, CYB.availableAt, "source")

    # ── B. index layer ─────────────────────────────────────────────────────
    h = Graph()
    for p, ns in [("cyb", CYB), ("id", ID), ("skos", SKOS), ("prov", PROV), ("foaf", FOAF)]:
        h.bind(p, ns)

    it = json.load(open(snap / "index_terms.json", encoding="utf-8"))
    iv = json.load(open(snap / "index_vocab.json", encoding="utf-8"))
    et = json.load(open(snap / "entity_types_cache.json", encoding="utf-8"))

    tslug = slug_map(list(iv))
    T = {k: ID[f"term/{tslug[k]}"] for k in iv}
    for k, v in iv.items():
        u = T[k]
        h.add((u, RDF.type, CYB.IndexTerm))
        h.add((u, SKOS.inScheme, CYB.CorpusIndexVocabulary))
        h.add((u, CYB.termKey, Literal(k)))
        h.add((u, SKOS.prefLabel, Literal(v["term"])))
        h.add((u, CYB.bookCount, Literal(len(set(v["books"])), datatype=XSD.integer)))
    report["index terms"] = len(T)

    pm, am = person_merge_rules(iv), accent_merge_rules(iv)
    for rules, prop in [(pm, CYB.mergedByInitials), (am, CYB.mergedByAccent)]:
        for var, can in rules.items():
            h.add((T[var], prop, T[can]))
            h.add((T[var], CYB.mergedInto, T[can]))      # super-property, materialised
    report["term merges (09b): person initials"] = len(pm)
    report["term merges (09b): accents"] = len(am)

    status_iri = {"ok": CYB.status_ok, "truncated": CYB.status_truncated,
                  "garbled": CYB.status_garbled, "no_index": CYB.status_no_index}
    n_entries, unknown_book, unknown_term = 0, [], 0
    for bid_s, d in it.items():
        bid = int(bid_s)
        if bid not in B:
            unknown_book.append(bid_s); continue
        bu, buuid = B[bid]
        g.add((bu, CYB.hasIndexStatus, status_iri[d["status"]]))
        g.add((bu, CYB.indexTermCount, Literal(d["n_terms"], datatype=XSD.integer)))
        for t in d["terms"]:
            k = t.lower()
            if k not in T:
                unknown_term += 1; continue
            eu = ID[f"entry/{buuid}/{tslug[k]}"]
            h.add((eu, RDF.type, CYB.IndexEntry))
            h.add((eu, CYB.inIndexOf, bu))
            h.add((eu, CYB.normalisesTo, T[k]))
            h.add((eu, CYB.entryLabel, Literal(t)))
            n_entries += 1
    report["index entries"] = n_entries
    report["index_terms books not in metadata.db"] = unknown_book
    report["entries whose term is missing from index_vocab"] = unknown_term
    report["books with no index_terms record"] = len(set(B) - {int(b) for b in it})

    kind_iri = {"person": CYB.kind_person, "concept": CYB.kind_concept,
                "organisation": CYB.kind_organisation, "location": CYB.kind_location,
                "suppress": CYB.kind_suppress}
    kind_cls = {"person": CYB.Person, "concept": CYB.Concept,
                "organisation": CYB.Organisation, "location": CYB.Location}
    method_iri = {"heuristic": CYB.method_heuristic, "spacy": CYB.method_spacy,
                  "default": CYB.method_default, "manual": CYB.PaulWong}
    kinds = collections.Counter(); methods = collections.Counter(); stale = []
    E = {}                                    # (kind, key) -> entity IRI
    for k, v in et.items():
        if k not in T:
            stale.append(k); continue
        kind, src = v["kind"], v["source"]
        if kind not in kind_iri or src not in method_iri:
            notes.append(f"unexpected kind/source {kind}/{src} for {k!r}; skipped"); continue
        cu = ID[f"classification/{tslug[k]}/{kind}"]
        h.add((cu, RDF.type, CYB.EntityClassification))
        h.add((cu, CYB.classifies, T[k]))
        h.add((cu, CYB.assignedKind, kind_iri[kind]))
        h.add((cu, PROV.wasAttributedTo, method_iri[src]))
        h.add((cu, CYB.confidence, Literal(str(v["confidence"]), datatype=XSD.decimal)))
        if v.get("spacy_label"):
            h.add((cu, CYB.nerLabel, Literal(v["spacy_label"])))
        if v.get("note"):
            h.add((cu, CYB.classificationNote, Literal(v["note"])))
        kinds[kind] += 1; methods[src] += 1
        if kind == "suppress":
            continue
        xu = ID[f"{kind}/{tslug[k]}"]
        E[(kind, k)] = xu
        h.add((xu, RDF.type, kind_cls[kind]))
        h.add((xu, RDFS.label, Literal(v.get("label") or iv[k]["term"])))
        h.add((xu, CYB.hasLabelSource, T[k]))
        h.add((cu, CYB.denotes, xu))
        h.add((T[k], CYB.possiblyDenotes, xu))
    report["classifications by kind"] = dict(kinds)
    report["classifications by method"] = dict(methods)
    report["entities"] = len(E)
    report["stale cache entries (term absent from index_vocab; skipped)"] = len(stale)

    # candidate creator <-> index-person matches: Calibre author sort == person term key
    person_by_key = {k: u for (kind, k), u in E.items() if kind == "person"}
    n_m = 0
    for aid, (au, name, sort) in A.items():
        key = (sort or "").lower().strip()
        if key in person_by_key:
            pu = person_by_key[key]
            mu = ID[f"namematch/{au.split('/')[-1]}--{pu.split('/')[-1]}"]
            h.add((mu, RDF.type, CYB.NameMatch))
            h.add((mu, CYB.matchesCreator, au))
            h.add((mu, CYB.matchesPerson, pu))
            h.add((mu, RDFS.comment, Literal("Calibre author_sort equals index person heading (case-insensitive). Candidate only.")))
            n_m += 1
    report["creator-person name matches (candidates)"] = n_m

    # ── write ──────────────────────────────────────────────────────────────
    f1 = outd / f"cyb-bibliographic {a.tag}.ttl"
    f2 = outd / f"cyb-index {a.tag}.ttl"
    hdr = (f"# Generated by _code/build_rdf.py on {dt.date.today().isoformat()} "
           f"from '00 Inputs/{a.snapshot}'.\n# Ontology: 02 Ontology/cybonto.ttl. "
           "Index-derived classifications are provisional.\n")
    for graph, f in [(g, f1), (h, f2)]:
        data = graph.serialize(format="turtle")
        f.write_text(hdr + data, encoding="utf-8")
    report["triples (bibliographic)"] = len(g)
    report["triples (index)"] = len(h)

    rp = outd / f"build report {a.tag}.md"
    lines = [f"# Build report {a.tag}", "",
             f"Snapshot: `00 Inputs/{a.snapshot}/` · generated {dt.datetime.now().isoformat(timespec='minutes')}", "",
             "## Input checksums (sha256)", ""]
    lines += [f"- `{f}` {sha256(snap / f)}" for f in inputs]
    lines += ["", "## Counts", ""]
    for k, v in report.items():
        lines.append(f"- {k}: {v}")
    if notes:
        lines += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    if stale:
        lines += ["", "## Stale cache entries (first 30)", ""] + [f"- `{s}`" for s in sorted(stale)[:30]]
    rp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
