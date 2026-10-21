#!/usr/bin/env python3
"""
validate_rdf.py - checks for the generated RDF (relative paths only).

  1. every cyb: term used in the data is declared in 02 Ontology/cybonto.ttl
  2. SHACL validation against 02 Ontology/cybonto-shapes.ttl (pyshacl)
  3. random spot checks: N books and N index entries re-derived from the
     snapshot sources and compared with the graph

Usage:
  python3 "_code/validate_rdf.py" --snapshot "snapshot 2026-10-19" --tag 2026-10-19 [--sample 25] [--seed 99]
Requires: rdflib, pyshacl.
"""
import argparse, json, random, sqlite3, sys
from pathlib import Path
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS

ROOT = Path(__file__).resolve().parent.parent
CYB = Namespace("https://w3id.org/cybernetic-bookshelf/ontology#")
ID  = Namespace("https://w3id.org/cybernetic-bookshelf/id/")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True); ap.add_argument("--tag", required=True)
    ap.add_argument("--sample", type=int, default=25); ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--skip-shacl", action="store_true")
    a = ap.parse_args()
    snap = ROOT / "00 Inputs" / a.snapshot
    tbox = Graph().parse(ROOT / "02 Ontology" / "cybonto.ttl")
    data = Graph()
    for f in [f"cyb-bibliographic {a.tag}.ttl", f"cyb-index {a.tag}.ttl"]:
        data.parse(ROOT / "03 Outputs" / f)
    print(f"tbox {len(tbox)} triples; data {len(data)} triples")
    fails = 0

    # 1. vocabulary closure
    declared = {s for s in tbox.subjects() if isinstance(s, URIRef) and str(s).startswith(str(CYB))}
    used = set()
    for s, p, o in data:
        for t in (p, o):
            if isinstance(t, URIRef) and str(t).startswith(str(CYB)):
                used.add(t)
    undeclared = sorted(used - declared)
    print(f"[1] cyb: terms used {len(used)}, undeclared {len(undeclared)} {undeclared[:10]}")
    fails += bool(undeclared)

    # 2. SHACL
    if not a.skip_shacl:
        from pyshacl import validate
        shapes = Graph().parse(ROOT / "02 Ontology" / "cybonto-shapes.ttl")
        conforms, _, text = validate(data + tbox, shacl_graph=shapes, inference="none",
                                     allow_infos=True, allow_warnings=True)
        print(f"[2] SHACL conforms: {conforms}")
        if not conforms:
            print(text[:3000]); fails += 1

    # 3. spot checks against the sources
    rnd = random.Random(a.seed)
    db = sqlite3.connect(f"file:{snap / 'metadata.db'}?mode=ro&immutable=1", uri=True)
    books = db.execute("select id, uuid, title from books").fetchall()
    bad = 0
    for bid, uuid, title in rnd.sample(books, a.sample):
        u = ID[f"book/{uuid}"]
        ok = (u, DCTERMS.title, Literal(title)) in data
        src_auth = [r[0] for r in db.execute(
            "select a.name from books_authors_link l join authors a on a.id=l.author where l.book=? order by l.id", (bid,))]
        rdf_auth = []
        for au in data.objects(u, CYB.hasAuthorship):
            pos = int(data.value(au, CYB.position)); ag = data.value(au, CYB.agent)
            rdf_auth.append((pos, str(data.value(ag, URIRef("http://xmlns.com/foaf/0.1/name")))))
        rdf_auth = [n for _, n in sorted(rdf_auth)]
        ok &= (src_auth == rdf_auth)
        if not ok:
            bad += 1; print("   MISMATCH book", bid, title, src_auth, rdf_auth)
    print(f"[3a] books spot-checked {a.sample}, mismatches {bad}")
    fails += bool(bad)

    it = json.load(open(snap / "index_terms.json", encoding="utf-8"))
    uuid_of = {str(b): u for b, u, _ in books}
    pairs = [(b, t) for b, d in it.items() for t in d["terms"]]
    bad = 0
    for b, t in rnd.sample(pairs, a.sample):
        bu = ID[f"book/{uuid_of[b]}"]
        hits = [e for e in data.subjects(CYB.inIndexOf, bu) if (e, CYB.entryLabel, Literal(t)) in data]
        if len(hits) != 1:
            bad += 1; print("   MISMATCH entry", b, t, hits); continue
        term = data.value(hits[0], CYB.normalisesTo)
        if str(data.value(term, CYB.termKey)) != t.lower():
            bad += 1; print("   MISMATCH term key", b, t)
    print(f"[3b] index entries spot-checked {a.sample}, mismatches {bad}")
    fails += bool(bad)

    print("RESULT:", "PASS" if not fails else f"FAIL ({fails} check groups)")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
