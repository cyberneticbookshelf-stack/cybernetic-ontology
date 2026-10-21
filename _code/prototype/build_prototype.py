#!/usr/bin/env python3
"""
build_prototype.py - 50-book prototype for testing inference over mixed ontologies.

Reads the full build (03 Outputs/cyb-*.ttl for --tag) and the snapshot, then writes
to 04 Prototype/<tag>/:
  selection.md              which books and why (seeded, reproducible)
  asserted.ttl              subgraph for the 50 books + prototype classifications
                            of new kinds (event, project, work, artefact, period, group)
                            + work -> collection-copy links
  resolution-sameas.ttl     stand-in name resolver: 09b initials merges promoted to
                            owl:sameAs between person entities (scenario C)
  same-term-identity.ttl    stress test: one entity per term across kinds (scenario D)

Usage: python3 "_code/prototype/build_prototype.py" --snapshot "snapshot 2026-10-19" --tag 2026-10-20
Relative paths only; project root = two levels above this file.
"""
import argparse, collections, json, random, re, sqlite3, sys
from pathlib import Path
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS, PROV, SKOS

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "_code"))
import build_rdf as core                                   # slug + 09b merge rules

BASE = core.BASE
CYB, ID = core.CYB, core.ID
N_TOTAL, SEED = 50, 99

ARTEFACTS = {"homeostat", "perceptron", "eniac", "analytical engine", "difference engine",
             "colossus", "univac", "edvac", "memex", "machina speculatrix", "whirlwind",
             "turing machine", "universal turing machine", "musicolour", "differential analyzer"}
PERIODS = {"enlightenment", "enlightenment, the", "renaissance", "information age",
           "middle ages", "stone age", "industrial age", "victorian era", "space age"}
EVENT_RE   = re.compile(r"^[\w'’\- ]{2,40} (war|revolution|crisis|conferences?|congress|symposium|olympics)$")
PROJECT_RE = re.compile(r"^(project [\w'’\- ]{2,30}|[\w'’\- ]{2,30} (project|programme|plan))$")
GROUP_RE   = re.compile(r"^[\w'’\- ]{2,40} (circle|school|club|movement)$")
NOT_GROUP  = {"vicious circle"}
WORK_RE    = re.compile(r"^(.+?)\s*\(([a-z][a-z'\- .]{2,30})\)$")

def classify_new_kind(key, cached, surnames):
    """Heading-pattern rules (prototype). Returns a kind or None. Deliberately crude."""
    words = key.split()
    m = WORK_RE.match(key)
    if m:
        title, inner = m.group(1).strip(" ,"), m.group(2).strip()
        initials = "".join(w[0] for w in re.findall(r"[a-z]+", title))
        surname = inner.split()[-1]
        if inner.replace(".", "") != initials and surname in surnames and len(title.split()) >= 2:
            return "work"                     # parenthetical is a known person surname
    if cached and cached.get("note") == "work_title":
        return "work"
    if key in ARTEFACTS:
        return "artefact"
    if key in PERIODS:
        return "period"
    if "," in key or " see " in key or len(words) > 6:                # names, cross-refs, fragments
        return None
    if EVENT_RE.match(key):
        return "event"
    if PROJECT_RE.match(key) and "agency" not in key:
        return "project"
    if GROUP_RE.match(key) and key not in NOT_GROUP:
        return "group"
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True); ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    snap = ROOT / "00 Inputs" / a.snapshot
    out = ROOT / "04 Prototype" / a.tag
    out.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(f"file:{snap / 'metadata.db'}?mode=ro&immutable=1", uri=True)
    books = {i: (u, t, (p or "")[:4]) for i, u, t, p in db.execute("select id, uuid, title, pubdate from books")}
    authors = collections.defaultdict(list)
    for b, n in db.execute("select l.book, a.name from books_authors_link l join authors a on a.id=l.author"):
        authors[b].append(n.lower())
    it = json.load(open(snap / "index_terms.json", encoding="utf-8"))
    iv = json.load(open(snap / "index_vocab.json", encoding="utf-8"))
    et = json.load(open(snap / "entity_types_cache.json", encoding="utf-8"))
    terms_of = {int(b): {t.lower() for t in d["terms"]} for b, d in it.items()}

    # ── 1. selection ───────────────────────────────────────────────────────
    pool = sorted(b for b, d in it.items() if d["status"] == "ok" and d["n_terms"] >= 100)
    pool = [int(b) for b in pool]
    reasons = collections.OrderedDict()
    def add(b, why):
        if b not in reasons and len(reasons) < N_TOTAL:
            reasons[b] = why
    copies = {2440: "Design for a Brain (Ashby)", 2706: "Steps to an Ecology of Mind (Bateson)",
              2726: "The Human Use of Human Beings (Wiener)"}
    for b, w in copies.items():
        add(b, f"purposive: collection copy of a work other indexes name ({w})")
    probes = [("design for a brain (ashby)", 2), ("steps to an ecology of mind (bateson)", 2),
              ("the human use of human beings (wiener)", 2), ("human use of human beings, the (wiener)", 1),
              ("project cybersyn", 2), ("cold war", 2), ("macy conferences", 2),
              ("wiener, n.", 2), ("homeostat", 1), ("vienna circle", 1)]
    for key, k in probes:
        for b in [b for b in pool if key in terms_of.get(b, set())][:k]:
            add(b, f"purposive: index contains '{key}'")
    rnd = random.Random(SEED)
    by_dec = collections.defaultdict(list)
    for b in pool:
        if b not in reasons:
            by_dec[books[b][2][:3] + "0s"].append(b)
    need = N_TOTAL - len(reasons)
    total = sum(len(v) for v in by_dec.values())
    alloc = {d: max(1, round(need * len(v) / total)) for d, v in by_dec.items()}
    while sum(alloc.values()) > need:
        alloc[max(alloc, key=alloc.get)] -= 1
    while sum(alloc.values()) < need:
        alloc[max(by_dec, key=lambda d: len(by_dec[d]) - alloc[d])] += 1
    for d in sorted(by_dec):
        for b in rnd.sample(by_dec[d], min(alloc[d], len(by_dec[d]))):
            add(b, f"stratified random (seed {SEED}), decade {d}")
    sel = list(reasons)
    sel_uuid = {books[b][0] for b in sel}

    # ── 2. subgraph from the full build ────────────────────────────────────
    full = Graph()
    for f in [f"cyb-bibliographic {a.tag}.ttl", f"cyb-index {a.tag}.ttl"]:
        full.parse(ROOT / "03 Outputs" / f)
    g = Graph()
    for p, ns in [("cyb", CYB), ("id", ID), ("dcterms", DCTERMS), ("skos", SKOS), ("prov", PROV), ("owl", OWL)]:
        g.bind(p, ns)
    def copy_node(s, depth=1):
        for p, o in full.predicate_objects(s):
            g.add((s, p, o))
            if depth and isinstance(o, URIRef) and str(o).startswith(str(ID)) and "/book/" in str(o) and str(o) != str(s):
                copy_node(o, depth - 1)
    book_iris = [ID[f"book/{books[b][0]}"] for b in sel]
    for bu in book_iris:
        for p, o in full.predicate_objects(bu):
            g.add((bu, p, o))
            if isinstance(o, URIRef) and str(o).startswith(str(ID)):
                for p2, o2 in full.predicate_objects(o):       # authorship, files, creators, pubtype ...
                    g.add((o, p2, o2))
                    if p2 == CYB.agent:
                        for t in full.triples((o2, None, None)): g.add(t)
    terms = set()
    for bu in book_iris:
        for e in full.subjects(CYB.inIndexOf, bu):
            for t in full.triples((e, None, None)): g.add(t)
            terms.add(full.value(e, CYB.normalisesTo))
    for t in terms:
        for tr in full.triples((t, None, None)): g.add(tr)
        for c in full.subjects(CYB.classifies, t):
            for tr in full.triples((c, None, None)): g.add(tr)
            x = full.value(c, CYB.denotes)
            if x is not None:
                for tr in full.triples((x, None, None)): g.add(tr)
    key_of = {t: str(full.value(t, CYB.termKey)) for t in terms}
    tslug = {k: str(t).rsplit("/", 1)[1] for t, k in key_of.items()}

    # ── 3. prototype classifications of new kinds ──────────────────────────
    new = collections.Counter(); examples = collections.defaultdict(list)
    new_entities = {}
    surnames = {k.split(",")[0].strip() for k, v in et.items() if v["kind"] == "person" and "," in k}
    for t, k in key_of.items():
        kind = classify_new_kind(k, et.get(k), surnames)
        if not kind:
            continue
        cu = ID[f"classification/{tslug[k]}/{kind}"]
        xu = ID[f"{kind}/{tslug[k]}"]
        g.add((cu, RDF.type, CYB.EntityClassification)); g.add((cu, CYB.classifies, t))
        g.add((cu, CYB.assignedKind, CYB[f"kind_{kind}"])); g.add((cu, PROV.wasAttributedTo, CYB.method_prototype_rules))
        g.add((cu, CYB.confidence, Literal("0.5", datatype=XSD.decimal))); g.add((cu, CYB.denotes, xu))
        g.add((xu, RDF.type, CYB[kind.capitalize()])); g.add((xu, RDFS.label, Literal(iv[k]["term"])))
        g.add((xu, CYB.hasLabelSource, t)); g.add((t, CYB.possiblyDenotes, xu))
        new[kind] += 1; new_entities[(kind, k)] = xu
        if len(examples[kind]) < 8: examples[kind].append(iv[k]["term"])

    # work -> collection copy (title prefix AND author surname)
    def norm_title(s):
        s = re.sub(r",\s*the$", "", s.strip(" ,")); s = re.sub(r"^the\s+", "", s)
        return re.sub(r"[^a-z0-9 ]", "", s)
    copies_found = []
    for (kind, k), xu in new_entities.items():
        if kind != "work":
            continue
        m = WORK_RE.match(k)
        if not m:
            continue
        title, surname = norm_title(m.group(1)), m.group(2).split()[-1]
        for b, (u, bt, y) in books.items():
            nt = norm_title(bt.lower())
            rest = bt.lower()[len(bt.lower()) - len(bt.lower().lstrip()):]
            ok_title = nt == title or re.match(re.escape(title) + r"(\s*:|\s+or\s)", re.sub(r"^the\s+", "", bt.lower().strip()))
            if ok_title and any(surname in n for n in authors[b]):
                bu = ID[f"book/{u}"]
                g.add((xu, CYB.hasCopyInCollection, bu))
                if (bu, RDF.type, CYB.Book) not in g:
                    g.add((bu, RDF.type, CYB.Book)); g.add((bu, DCTERMS.title, Literal(bt)))
                copies_found.append((iv[k]["term"], bt, b, b in sel))
    g.serialize(out / "asserted.ttl", format="turtle")

    # ── 4. stand-in resolver: 09b initials merges -> owl:sameAs ────────────
    r = Graph(); r.bind("owl", OWL); r.bind("id", ID)
    pm = core.person_merge_rules(iv)
    person_x = {key_of[t]: x for t in terms for c in g.subjects(CYB.classifies, t)
                for x in [g.value(c, CYB.denotes)] if x is not None and (x, RDF.type, CYB.Person) in g}
    same = []
    for var, can in pm.items():
        if var in person_x and can in person_x:
            r.add((person_x[var], OWL.sameAs, person_x[can])); same.append((var, can))
    r.serialize(out / "resolution-sameas.ttl", format="turtle")

    # ── 5. stress test: one entity per term across kinds ───────────────────
    s = Graph(); s.bind("owl", OWL); s.bind("id", ID)
    multi = []
    for t in terms:
        xs = [g.value(c, CYB.denotes) for c in g.subjects(CYB.classifies, t)]
        xs = [x for x in xs if x is not None]
        for x in xs[1:]:
            s.add((xs[0], OWL.sameAs, x))
        if len(xs) > 1:
            multi.append((key_of[t], sorted(str(x).split("/id/")[1].split("/")[0] for x in xs)))
    s.serialize(out / "same-term-identity.ttl", format="turtle")

    # ── selection + build notes ────────────────────────────────────────────
    L = [f"# Prototype selection and build notes ({a.tag})", "",
         f"Snapshot `00 Inputs/{a.snapshot}/`, full build `03 Outputs/cyb-* {a.tag}.ttl`. "
         f"{len(sel)} books: {sum(1 for w in reasons.values() if w.startswith('purposive'))} purposive, the rest a decade-stratified random draw (seed {SEED}) "
         "from the books whose index extracted cleanly ('ok', at least 100 headings). Purposive books overrepresent the cases the prototype is meant to test, so counts here are illustrative, not estimates for the collection.", "",
         "| id | year | title | why |", "|---|---|---|---|"]
    for b in sel:
        L.append(f"| {b} | {books[b][2]} | {books[b][1][:70]} | {reasons[b]} |")
    L += ["", f"Subgraph: {len(g)} asserted triples; {len(terms)} index terms.", "",
          "## Prototype classifications of new kinds (heading-pattern rules, confidence 0.5)", ""]
    for kind, n in new.most_common():
        L.append(f"- {kind}: {n} - e.g. " + "; ".join(examples[kind]))
    L += ["", "## Works matched to a copy in the collection (title prefix + author surname)", ""]
    L += [f"- {w} -> [{b}] {t[:60]}{' (in the 50)' if ins else ''}" for w, t, b, ins in copies_found] or ["- none"]
    L += ["", f"## Stand-in resolver: {len(same)} owl:sameAs between person entities (09b initials rule)", ""]
    L += [f"- {v} = {c}" for v, c in same]
    L += ["", f"## Terms with more than one kind ({len(multi)})", ""]
    L += [f"- {k}: {', '.join(ks)}" for k, ks in sorted(multi)[:40]]
    (out / "selection.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:6])); print(f"asserted triples {len(g)}; new kinds {dict(new)}; copies {len(copies_found)}; sameAs {len(same)}; multi-kind {len(multi)}")

if __name__ == "__main__":
    main()
