"""South County Week builder.

Usage:
  python3 -I build.py TEMPLATE EVENTS_DIR OUT_HTML RANGE_START RANGE_END "UPDATED LABEL" [META_JSON]

EVENTS_DIR holds any number of *.json files, each a JSON array of events:
  {"title","date":"YYYY-MM-DD","end_date":"","time","city":"Boca Raton|Delray Beach|Boynton Beach",
   "venue","address","category","price","url","source","desc","tags":["kids","outdoor"] optional}
"tags" may be given explicitly; the script also adds "kids" (parents & children) and
"outdoor" from the category and keywords.
META_JSON (optional) = {"sources":[site names checked], "notes":[short lines], "share_url": (optional, the public app link),
  "picks":[{"title":"words from the event title","date":"YYYY-MM-DD (optional)","city":"(optional)",
            "note":"one short line on why it's worth going"}]}
  Picks are matched to events by title words (+date/city when given); unmatched picks are
  reported in the printed JSON as "picks_unmatched" so you can fix them.

Other modes:
  python3 -I build.py --extract PAGE.html OUT.json
      Dump the events inside a built page (e.g. the live artifact) as an events file,
      so a mid-week refresh can merge new finds into what is already published.

Each event gets a stable "id" (from city, date and title) used for share links (#e-<id>).

The script keeps only the three cities and events that touch the date range,
merges duplicates (same city + overlapping date + similar title, or same single-day
date + identical full URL including its query string; same-venue fuzzy matches
only on the same single day),
keeping the richest record and listing the other sources under "also",
then writes the page and prints counts as JSON.
"""
import json, re, sys, glob, os, difflib, unicodedata, hashlib

CITIES = {"boca raton": "Boca Raton", "boca": "Boca Raton", "west boca": "Boca Raton", "west boca raton": "Boca Raton",
          "delray beach": "Delray Beach", "delray": "Delray Beach",
          "boynton beach": "Boynton Beach", "boynton": "Boynton Beach"}
FIELDS = ["title", "date", "end_date", "time", "city", "venue", "address", "category", "price", "url", "source", "desc"]
STOP = {"the", "a", "an", "at", "in", "of", "and", "&", "with", "presents", "live", "event", "2026", "boca", "raton",
        "delray", "beach", "boynton", "fl", "florida"}


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return " ".join(w for w in t.split() if w not in STOP)


def ok_date(s):
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s or ""))


def tag(e, given):
    """Tags: "kids" = aimed at children and/or parents (family events, kids' classes, storytimes,
    teen/tween programs, expectant/new-parent classes). "outdoor" = mainly held outside (parks,
    beaches, nature centers, outdoor markets/festivals/shows, walks, self-guided outdoor hunts).
    Explicit tags from the input win; the category adds the obvious ones."""
    tags = {t for t in given if t in ("kids", "outdoor")}
    if e["category"] == "Family & Kids":
        tags.add("kids")
    if e["category"] == "Outdoors & Nature":
        tags.add("outdoor")
    return sorted(tags)


def score(e):
    return sum(1 for f in FIELDS if e.get(f)) + (len(e.get("desc", "")) > 20)


def eid(e):
    return hashlib.sha1(f"{e['city']}|{e['date']}|{norm(e['title'])}".encode()).hexdigest()[:8]


def extract(page, out):
    h = open(page, encoding="utf-8").read()
    m = re.search(r"/\*__DATA__\*/(.*?)/\*__END__\*/", h, re.S)
    d = json.loads(m.group(1).replace("<\\/", "</"))
    evs = [{k: e.get(k, "") for k in FIELDS + ["tags"]} for e in d["events"]]
    json.dump(evs, open(out, "w"), ensure_ascii=False, indent=0)
    print(json.dumps({"extracted": len(evs), "range": [d.get("range_start"), d.get("range_end")],
                      "picks": d.get("picks", [])}))


def resolve_picks(picks, events):
    out, miss = [], []
    for p in picks:
        words = norm(p.get("title", "")).split()
        best = None
        for e in events:
            if p.get("city") and e["city"] != p["city"]:
                continue
            if p.get("date") and not (e["date"] <= p["date"] <= (e["end_date"] or e["date"])):
                continue
            t = norm(e["title"])
            if words and all(w in t.split() or w in t for w in words):
                best = e
                break
        if best and best["id"] not in [o["id"] for o in out]:
            out.append({"id": best["id"], "note": p.get("note", "")})
        elif not best:
            miss.append(p.get("title", ""))
    return out, miss


def main():
    if sys.argv[1] == "--extract":
        return extract(sys.argv[2], sys.argv[3])
    tpl, edir, out, rs, re_, label = sys.argv[1:7]
    meta = json.load(open(sys.argv[7])) if len(sys.argv) > 7 and os.path.exists(sys.argv[7]) else {}
    raw, bad = [], 0
    for f in sorted(glob.glob(os.path.join(edir, "*.json"))):
        try:
            data = json.load(open(f))
        except Exception:
            bad += 1
            continue
        if isinstance(data, dict):
            data = data.get("events", [])
        for e in data:
            if not isinstance(e, dict):
                continue
            given = e.get("tags") if isinstance(e.get("tags"), list) else []
            e = {k: str(e.get(k) or "").strip() for k in FIELDS}
            e["tags"] = tag(e, given)
            city = CITIES.get(e["city"].lower())
            if re.search(r"\b(cancel+ed|postponed)\b", e["title"] + " " + e["time"], re.I):
                bad += 1
                continue
            if not city or not e["title"] or not ok_date(e["date"]):
                bad += 1
                continue
            e["city"] = city
            if not ok_date(e["end_date"]) or e["end_date"] < e["date"]:
                e["end_date"] = ""
            end = e["end_date"] or e["date"]
            if end < rs or e["date"] > re_:
                continue
            if e["url"] and not e["url"].startswith("http"):
                e["url"] = ""
            raw.append(e)

    merged = []
    for e in sorted(raw, key=score, reverse=True):
        ne = norm(e["title"])
        hit = None
        for m in merged:
            if m["city"] != e["city"]:
                continue
            same_url = e["url"] and e["url"].rstrip("/") == m["url"].rstrip("/")
            overlap = not ((e["end_date"] or e["date"]) < m["date"] or e["date"] > (m["end_date"] or m["date"]))
            if same_url and e["date"] == m["date"] and not m["end_date"] and not e["end_date"]:
                hit = m; break
            if overlap and (e["date"] == m["date"] or m["end_date"] or e["end_date"]):
                nm = norm(m["title"])
                if not (ne and nm):
                    continue
                ratio = difflib.SequenceMatcher(None, ne, nm).ratio()
                same_venue = norm(e["venue"]) and norm(e["venue"]) == norm(m["venue"])
                # same-venue fuzzy matching only when both run on exactly the same dates,
                # so a one-night event never merges into an exhibit or a show's run
                same_dates = e["date"] == m["date"] and e["end_date"] == m["end_date"]
                ta, tb = set(ne.split()), set(nm.split())
                contain = len(ta & tb) / min(len(ta), len(tb))
                short = min(len(ne), len(nm))
                if ne == nm or ratio > 0.82 or ((ne in nm or nm in ne) and short >= 8) \
                        or (same_venue and same_dates and contain >= 0.6):
                    hit = m; break
        if hit:
            lo = min(hit["date"], e["date"])
            hi = max(hit["end_date"] or hit["date"], e["end_date"] or e["date"])
            hit["date"], hit["end_date"] = lo, (hi if hi > lo else "")
            hit["tags"] = sorted(set(hit.get("tags", [])) | set(e.get("tags", [])))
            for k in FIELDS:
                if not hit.get(k) and e.get(k):
                    hit[k] = e[k]
            if e["url"] and e["url"] != hit["url"]:
                hit.setdefault("also", []).append({"source": e["source"], "url": e["url"]})
        else:
            merged.append(dict(e))

    merged.sort(key=lambda e: (e["date"], e["city"], e["title"].lower()))
    for e in merged:
        e["id"] = eid(e)
        if e.get("also"):
            seen, al = {e["url"]}, []
            for a in e["also"]:
                if a["url"] not in seen:
                    seen.add(a["url"]); al.append(a)
            e["also"] = al[:4]
    picks, miss = resolve_picks(meta.get("picks", []), merged)
    data = {"generated": label, "range_start": rs, "range_end": re_, "events": merged, "picks": picks,
            "share_url": meta.get("share_url", "https://justinhimmelbaum-glitch.github.io/south-county-week/"),
            "sources": meta.get("sources", []), "notes": meta.get("notes", [])}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = open(tpl).read()
    html = re.sub(r"/\*__DATA__\*/.*?/\*__END__\*/", lambda m: "/*__DATA__*/" + blob + "/*__END__*/", html, flags=re.S)
    open(out, "w").write(html)
    counts = {}
    for e in merged:
        counts[e["city"]] = counts.get(e["city"], 0) + 1
    print(json.dumps({"raw": len(raw), "events": len(merged), "dupes_merged": len(raw) - len(merged),
                      "rejected": bad, "by_city": counts, "picks": len(picks), "picks_unmatched": miss}))


if __name__ == "__main__":
    main()
