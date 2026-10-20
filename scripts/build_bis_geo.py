#!/usr/bin/env python3
"""BIS geo-tagging — geometry fields + seeded coordinates.

Fields (map interface):
  bis_puroks.location        geometry.Point        (centroid / map label)
  bis_puroks.boundary        geometry.MultiPolygon (purok boundary)
  bis_households.location    geometry.Point        (dwelling pin)
  bis_blotter.incident_point geometry.Point        (incident pin)
  bis_business_permits.location geometry.Point     (business pin)

Values are GeoJSON objects. Demo geometry is synthesized around a barangay
center in Quezon City — replace with surveyed data later.
"""
import json, math, os, random, urllib.request, urllib.error, urllib.parse

BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ.get("DIRECTUS_TOKEN", "RBzmMVX7UP9baKtLiHV6RmmTx9s9tmFZ")
HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0"}
random.seed(11)

# Barangay Poblacion, San Fabian, Pangasinan demo center — lng, lat
# (shifted slightly inland from the town plaza so pins don't land in Lingayen Gulf)
CTR_LNG, CTR_LAT = 120.4150, 16.1300
# 7 purok cluster centers spread ~300-500m around center (lng, lat offsets in degrees)
PUROK_CENTER = [(-0.0018, 0.0016), (0.0022, 0.0008), (-0.0024, -0.0018),
                (0.0006, 0.0024), (-0.0004, -0.0028), (0.0026, -0.0020),
                (0.0010, -0.0004)]
VIEW = {"center": {"lat": CTR_LAT, "lng": CTR_LNG}, "zoom": 16}


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=HDRS)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        print(f"  !! {method} {path} -> {e.code}: {e.read().decode()[:260]}")
        return e.code, {}


def ensure_field(col, spec):
    s, d = req("GET", f"/fields/{col}?limit=-1")
    names = {f["field"] for f in d.get("data", [])} if s == 200 else set()
    if spec["field"] in names:
        req("PATCH", f"/fields/{col}/{spec['field']}", {"meta": spec["meta"]})
        print(f"  = {col}.{spec['field']} (patched)")
    else:
        s, _ = req("POST", f"/fields/{col}", spec)
        print(("  + " if s in (200, 201) else "  !! ") + f"{col}.{spec['field']}")


def point(lng, lat):
    return {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]}


def square(cx, cy, half):  # rough purok polygon (axis-aligned ~half-degree box)
    ring = [[cx - half, cy - half], [cx + half, cy - half],
            [cx + half, cy + half], [cx - half, cy + half], [cx - half, cy - half]]
    return {"type": "MultiPolygon", "coordinates": [[ring]]}


def jitter(c_lng, c_lat, meters=90):
    dlat = meters / 111320.0
    dlng = meters / (111320.0 * math.cos(math.radians(c_lat)))
    return c_lng + random.uniform(-dlng, dlng), c_lat + random.uniform(-dlat, dlat)


def build():
    print("== geo fields ==")
    geo_fields = [
        ("bis_puroks", "location", "geometry.Point", "Purok centroid", None),
        ("bis_puroks", "boundary", "geometry.MultiPolygon", "Purok boundary", None),
        ("bis_households", "location", "geometry.Point", "Dwelling location", "grp_details"),
        ("bis_blotter", "incident_point", "geometry.Point", "Incident geo-tag", "grp_incident"),
        ("bis_business_permits", "location", "geometry.Point", "Business location", None),
        ("bis_residents", "field_point", "geometry.Point",
         "Field-verified location (home visit / outreach) — household pin is the "
         "canonical residential location", "grp_residency"),
    ]
    for col, fld, gtype, note, grp in geo_fields:
        meta = {"interface": "map", "note": note, "width": "full",
                "options": {"basemap": "OpenStreetMap", "defaultView": VIEW}}
        if grp:
            meta["group"] = grp
        ensure_field(col, {"field": fld, "type": gtype, "schema": {}, "meta": meta})

    # --- purok centroids + boundaries ---
    s, d = req("GET", "/items/bis_puroks?fields=id,name&limit=-1")
    puroks = sorted(d.get("data", []), key=lambda r: r["name"])
    center_of = {}
    for i, p in enumerate(puroks):
        cx, cy = PUROK_CENTER[i % len(PUROK_CENTER)]
        c_lng, c_lat = CTR_LNG + cx, CTR_LAT + cy
        center_of[p["id"]] = (c_lng, c_lat)
        if not p.get("skip"):
            req("PATCH", f"/items/bis_puroks/{p['id']}",
                {"location": point(c_lng, c_lat),
                 "boundary": square(c_lng, c_lat, 0.0009)})
    print(f"  puroks geo-tagged: {len(center_of)}")

    # --- households: jitter inside their purok ---
    s, d = req("GET", "/items/bis_households?fields=id,purok&limit=-1")
    n = 0
    for h in d.get("data", []):
        c = center_of.get(h.get("purok"))
        if not c:
            continue
        lng, lat = jitter(*c, meters=110)
        req("PATCH", f"/items/bis_households/{h['id']}", {"location": point(lng, lat)})
        n += 1
    print(f"  households geo-tagged: {n}")

    # --- blotters: derive purok from `location` text ---
    s, d = req("GET", "/items/bis_blotter?fields=id,location&limit=-1")
    name_to_center = {p["name"]: center_of[p["id"]] for p in puroks}
    n = 0
    for b in d.get("data", []):
        loc = b.get("location") or ""
        c = next((v for k, v in name_to_center.items() if k.split(" - ")[0] in loc), None)
        c = c or center_of[puroks[0]["id"]]
        lng, lat = jitter(*c, meters=140)
        req("PATCH", f"/items/bis_blotter/{b['id']}", {"incident_point": point(lng, lat)})
        n += 1
    print(f"  blotters geo-tagged: {n}")

    # --- permits: jitter inside their purok ---
    s, d = req("GET", "/items/bis_business_permits?fields=id,purok&limit=-1")
    n = 0
    for p in d.get("data", []):
        c = center_of.get(p.get("purok")) or center_of[puroks[0]["id"]]
        lng, lat = jitter(*c, meters=120)
        req("PATCH", f"/items/bis_business_permits/{p['id']}", {"location": point(lng, lat)})
        n += 1
    print(f"  permits geo-tagged: {n}")

    # --- residents: field-verified points for vulnerable residents only ---
    # (senior / pwd / evacuation-priority / pregnant). Household pin remains the
    # canonical residential location — this is what BDRRM uses at response time.
    s, d = req("GET", "/items/bis_residents?fields=id,sector_tags,household&limit=-1")
    hh_loc = {}
    s, hd = req("GET", "/items/bis_households?fields=id,location&limit=-1")
    for h in hd.get("data", []):
        if h.get("location"):
            hh_loc[h["id"]] = h["location"]["coordinates"]
    n = 0
    for r in d.get("data", []):
        tags = r.get("sector_tags") or ""
        if not any(t in tags for t in ("senior_citizen", "pwd", "evacuation_priority",
                                       "pregnant_lactating")):
            continue
        base = hh_loc.get(r.get("household"))
        if base:
            lng, lat = jitter(base[0], base[1], meters=40)
        else:
            c = center_of[puroks[0]["id"]]
            lng, lat = jitter(*c, meters=300)
        req("PATCH", f"/items/bis_residents/{r['id']}", {"field_point": point(lng, lat)})
        n += 1
    print(f"  vulnerable residents field-pointed: {n}")
    print("done.")


if __name__ == "__main__":
    build()
