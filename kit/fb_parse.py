"""Turn Facebook Events search dumps into South County Week events.

Usage: python3 -I fb_parse.py OUT.json RANGE_START RANGE_END RAW1.txt [RAW2.txt ...]
Each RAW line: "<event id> :: <DATE LINE> | <title> | <where...>" as fb_grab.js prints it.
Facebook shows times in the browser's own time zone (e.g. "AT 7 PM CST"); they are
converted to Eastern. Only events whose text places them in Boca Raton, Delray Beach
or Boynton Beach are kept (by city name, ZIP code or known venue). Review the output:
drop private club events and anything clearly out of area, fix categories and tags.
"""
import json, re, sys
MON = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}
OFF = {"EST": 0, "EDT": 0, "CST": 1, "CDT": 1, "MST": 2, "MDT": 2, "PST": 3, "PDT": 3}
CITY = [("Boynton Beach", ("boynton", "33435", "33436", "33437", "33426", "33472", "33473")),
        ("Delray Beach", ("delray", "33444", "33445", "33446", "33483", "old school square", "gulfstream park", "sandoway", "double roads", "deck 84", "thrōw social delray", "doghouse theater", "cason")),
        ("Boca Raton", ("boca", "33431", "33432", "33433", "33434", "33428", "33486", "33487", "33496", "33498", "daggerwing", "mizner", "sanborn", "sunset cove"))]
CATS = [(("chanukah", "hanukkah", "christmas", "santa", "holiday", "tree lighting", "thanksgiving", "menorah", "gelt", "new year"), "Holiday"),
        (("dj ", "band", "concert", "tribute", "music", "trio", "live at", "live music"), "Music"),
        (("comedy", "comedian", "improv", "theater", "theatre", "ballet", "nutcracker", "museum", "art show", "gallery"), "Arts & Theater"),
        (("networking", "business", "chamber", "brews", "schmooze"), "Networking & Business"),
        (("5k", "10k", "yoga", "pilates", "run ", "dive", "archery", "pickleball", "golf", "tennis"), "Sports & Fitness"),
        (("market", "sale", "shop", "fair", "flea", "art walk", "festival"), "Festivals & Markets"),
        (("brunch", "wine", "dinner", "banquet", "bar crawl", "beer", "tasting"), "Food & Drink")]
def main(out, rs, re_, *raws):
    yr = int(rs[:4]); res, seen = [], set()
    for f in raws:
        for line in open(f, encoding="utf-8"):
            if " :: " not in line: continue
            eid, rest = line.strip().split(" :: ", 1)
            if eid in seen: continue
            parts = [p.strip() for p in rest.split(" | ")]
            if len(parts) < 2: continue
            dt, title, where = parts[0], parts[1], " | ".join(parts[2:])
            m = re.match(r"(?:[A-Z]{3}, )?([A-Z]{3}) (\d+)(?:, (\d{4}))?(?: AT (\d+)(?::(\d+))? (AM|PM) ([A-Z]{3}))?", dt)
            if not m or m[1] not in MON: continue
            y = int(m[3]) if m[3] else (yr + 1 if MON[m[1]] < int(rs[5:7]) - 6 else yr)
            date = f"{y}-{MON[m[1]]:02d}-{int(m[2]):02d}"
            m2 = re.search(r"- (?:[A-Z]{3}, )?([A-Z]{3}) (\d+)", dt)
            end = f"{y}-{MON[m2[1]]:02d}-{int(m2[2]):02d}" if m2 and m2[1] in MON else ""
            if (end or date) < rs or date > re_: continue
            time = ""
            if m[4]:
                h = int(m[4]) % 12 + (12 if m[6] == "PM" else 0) + OFF.get(m[7], 0); mi = int(m[5] or 0)
                time = f"{(h % 12) or 12}:{mi:02d} {'AM' if h % 24 < 12 else 'PM'}"
            blob = (title + " " + where).lower()
            city = next((c for c, keys in CITY if any(k in blob for k in keys)), None)
            if not city: continue
            intr = re.search(r"([\d,]+) people interested", where)
            venue = re.sub(r"^[\d,]+ (people interested|person going|people going) · ", "", where).strip()
            tl = title.lower()
            cat = next((c for keys, c in CATS if any(k in tl for k in keys)), "Other")
            tags = set()
            if any(k in tl for k in ("santa", "kids", "family", "children", "toddler", "pre-k", "carnival", "storytime", "teen")): tags.add("kids")
            if any(k in blob for k in ("tree lighting", "amphitheater", " park", "beach yoga", "flea", "art walk", "art fair", "sidewalk", "outdoor", "5k", "cars & coffee", "bar crawl", "parade")): tags.add("outdoor")
            seen.add(eid)
            res.append({"title": title, "date": date, "end_date": end, "time": time, "city": city,
                        "venue": venue.split(",")[0][:60], "address": venue if "," in venue else "", "category": cat, "price": "",
                        "url": f"https://www.facebook.com/events/{eid}/", "source": "Facebook Events",
                        "desc": "Public Facebook event" + (f" with {intr[1]} people interested." if intr else "."), "tags": sorted(tags)})
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"events": len(res)}))
if __name__ == "__main__":
    main(*sys.argv[1:])
