#!/usr/bin/env python3
"""
infer_prototype.py - run OWL 2 RL inference over the 50-book prototype under four
scenarios and report what inference adds.

  A  core      asserted data + core ontology (cybonto.ttl)
  B  aligned   A + extended kinds + alignments (CIDOC-CRM, LRMoo, schema.org, PROV, SKOS)
  C  resolved  B + stand-in name resolver (owl:sameAs between person variants)
  D  strict    B + "one entity per term" identity + BFO upper-ontology stress test

Reasoner: `reasonable` (OWL 2 RL, Rust); a cross-check of scenario B on a sample
uses `owlrl` (pure Python reference implementation).
Writes 04 Prototype/<tag>/inferred-B.ttl and results.json.

Usage: python3 "_code/prototype/infer_prototype.py" --tag 2026-10-20
"""
import argparse, collections, json, time
from pathlib import Path
import reasonable
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

REASONER = "owlrl"
ROOT = Path(__file__).resolve().parent.parent.parent
ONT = ROOT / "02 Ontology"
CYB = "https://w3id.org/cybernetic-bookshelf/ontology#"
ID = "https://w3id.org/cybernetic-bookshelf/id/"

SCENARIOS = {
    "A": ["cybonto.ttl"],
    "B": ["cybonto.ttl", "cybonto-extended-kinds.ttl", "cybonto-alignments.ttl"],
    "C": ["cybonto.ttl", "cybonto-extended-kinds.ttl", "cybonto-alignments.ttl", "+resolution-sameas.ttl"],
    "D": ["cybonto.ttl", "cybonto-extended-kinds.ttl", "cybonto-alignments.ttl", "+same-term-identity.ttl", "stress-test-bfo.ttl"],
}
VIEW_CLASSES = {
    "CIDOC-CRM": ["E21_Person", "E74_Group", "E39_Actor", "E53_Place", "E5_Event", "E7_Activity", "E4_Period",
                  "E22_Human-Made_Object", "E55_Type"],
    "LRMoo": ["F1_Work", "F3_Manifestation"],
    "schema.org": ["Person", "Organization", "Place", "Event", "Project", "CreativeWork", "Book"],
    "PROV / FOAF / SKOS": ["prov:Activity", "foaf:Person", "foaf:Organization", "skos:Concept"],
}
NS = {"CIDOC-CRM": "http://www.cidoc-crm.org/cidoc-crm/", "LRMoo": "http://iflastandards.info/ns/lrm/lrmoo/",
      "schema.org": "https://schema.org/", "prov": "http://www.w3.org/ns/prov#",
      "foaf": "http://xmlns.com/foaf/0.1/", "skos": "http://www.w3.org/2004/02/skos/core#"}

def cls(view, c):
    if ":" in c:
        p, n = c.split(":"); return URIRef(NS[p] + n)
    return URIRef(NS[view] + c)

def run(tag, scen):
    d = ROOT / "04 Prototype" / tag
    g = Graph().parse(d / "asserted.ttl")
    # entity-bearing slice: keep only classified terms and their entries. Unclassified
    # terms (about 85%) carry no entity, so no alignment or chain axiom applies to them;
    # dropping them keeps OWL RL materialisation within memory.
    cyb = lambda n: URIRef(CYB + n)
    classified = {g.value(c, cyb("classifies")) for c in g.subjects(cyb("classifies"), None)}
    for t in set(g.subjects(cyb("termKey"), None)) - classified:
        for e in list(g.subjects(cyb("normalisesTo"), t)):
            g.remove((e, None, None))
        g.remove((t, None, None)); g.remove((None, None, t))
    for f in SCENARIOS[scen]:
        g.parse(d / f[1:] if f.startswith("+") else ONT / f)
    n0 = len(g)
    t = time.time()
    if REASONER == "owlrl":
        import owlrl
        h = Graph()
        for tr in g: h.add(tr)
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False,
                               datatype_axioms=False).expand(h)
    else:
        r = reasonable.PyReasoner(); r.from_graph(g)
        h = Graph()
        for tr in r.reason(): h.add(tr)
    return g, h, n0, time.time() - t

def count_type(h, c):
    return len(set(h.subjects(RDF.type, c)))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", required=True); ap.add_argument("--only", default="ABCD"); ap.add_argument("--reasoner", default="owlrl", choices=["owlrl", "reasonable"]); a = ap.parse_args()
    global REASONER; REASONER = a.reasoner
    d = ROOT / "04 Prototype" / a.tag
    res = {}
    for scen in a.only:
        g, h, n0, dt = run(a.tag, scen)
        R = {"asserted_plus_ontology": n0, "after_inference": len(h), "seconds": round(dt, 1)}
        R["views"] = {v: {c: count_type(h, cls(v, c)) for c in cs} for v, cs in VIEW_CLASSES.items()}
        R["cyb_counts"] = {k: count_type(h, URIRef(CYB + k)) for k in
                           ["Person", "Organisation", "Location", "Concept", "Event", "Activity", "Project",
                            "Work", "Artefact", "Period", "Group", "Entity"]}
        # derived relations
        R["indexes (book->term, inverse chain)"] = len(list(h.triples((None, URIRef(CYB + "indexes"), None))))
        R["indexMentions (book->entity, chain)"] = len(list(h.triples((None, URIRef(CYB + "indexMentions"), None))))
        imb = sorted({(str(s), str(o)) for s, o in h.subject_objects(URIRef(CYB + "indexMentionsBook")) if s != o})
        title = lambda u: str(h.value(URIRef(u), URIRef("http://purl.org/dc/terms/title")) or u)[:50]
        R["indexMentionsBook (book->book, chain)"] = [[title(s), title(o)] for s, o in imb]
        # Wiener: books whose index mentions the Norbert Wiener person entity
        def entity_for(key, cls_):
            for t in h.subjects(URIRef(CYB + "termKey"), Literal(key)):
                for x in h.objects(t, URIRef(CYB + "possiblyDenotes")):
                    if (x, RDF.type, URIRef(CYB + cls_)) in h:
                        return x
        for key in ["wiener, norbert", "wiener, n.", "turing, alan", "minsky, marvin"]:
            x = entity_for(key, "Person")
            R[f"books mentioning person '{key}'"] = len(set(h.subjects(URIRef(CYB + "indexMentions"), x))) if x is not None else None
        R["sameAs triples (non-reflexive)"] = sum(1 for s, o in h.subject_objects(OWL.sameAs) if s != o)
        # Project Cybersyn: every type it ends up with
        cy = URIRef(ID + "project/project-cybersyn")
        R["types of project/project-cybersyn"] = sorted(str(t).split("/")[-1].split("#")[-1] for t in h.objects(cy, RDF.type))
        # inconsistency: an individual typed with two classes declared disjoint
        clash = []
        for c1, c2 in h.subject_objects(OWL.disjointWith):
            both = set(h.subjects(RDF.type, c1)) & set(h.subjects(RDF.type, c2))
            clash += [(str(x), str(c1).split("/")[-1], str(c2).split("/")[-1]) for x in both]
        R["disjointness clashes"] = len(clash)
        R["clash examples"] = [[x.replace(ID, ""), a_, b_] for x, a_, b_ in sorted(clash)[:12]]
        nothing = set(h.subjects(RDF.type, OWL.Nothing))
        R["typed owl:Nothing"] = len(nothing)
        res[scen] = R
        print(scen, R["after_inference"], R["seconds"], "s; clashes", R["disjointness clashes"])
        if scen == "B":
            h.serialize(d / f"inferred-B-{a.reasoner}.ttl", format="turtle")
    (d / f"results-{a.reasoner}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
