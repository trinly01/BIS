#!/usr/bin/env python3
"""BIS heatmap panels — likhaHeatmap-panel (id 'likhaHeatmap-panel').

Unlike echarts-panel, this panel does NOT take a flow reference. It queries a
collection directly (limit 1000) via options:
  collection   - data collection (required)
  geoField     - geometry/geo field name, plain name (required)
  field        - numeric metric field for intensity (optional; omit = weight 1)
  filter       - Directus JSON filter (optional)
  popupFields  - array of field paths incl. dot-notation nested (e.g. purok.name)
  + map/styling keys: showHeader, autoFitBounds, defaultCenter (GeoJSON Point),
    defaultZoom, defaultBearing, colorScheme (coolwarm|viridis|plasma|grayscale|
    spectral), heatmapRadius, heatmapIntensity, showCircleLayer, heatmapMaxZoom,
    circleMinZoom, transitionRange, enableClustering, clusterRadius,
    clusterAggregation (count|sum|avg|min|max), clusterCategories

NOTE: the panel's options UI crashes on some clicks (extension bug:
'Cannot read properties of undefined (reading query)'). Configure via PATCH
/panels/{id} instead — this script does that.
"""
import json, os, urllib.request, urllib.error, urllib.parse

BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ["DIRECTUS_TOKEN"]
HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0"}
Q = urllib.parse.quote

PANEL_TYPE = "likhaHeatmap-panel"
# Barangay Poblacion, San Fabian, Pangasinan (GeoJSON [lng, lat])
CENTER = {"type": "Point", "coordinates": [120.4156, 16.1324]}


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=HDRS)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        print(f"  !! {method} {path} -> {e.code}: {e.read().decode()[:260]}")
        return e.code, {}


def panel_options(collection, geo_field, popups, scheme, extra=None):
    o = {
        "collection": collection,
        "geoField": geo_field,
        "popupFields": popups,
        "showHeader": True,
        "autoFitBounds": True,
        "defaultCenter": CENTER,
        "defaultZoom": 13.5,
        "defaultBearing": 0,
        "colorScheme": scheme,
        "heatmapRadius": 25,
        "heatmapIntensity": 1.2,
        "showCircleLayer": True,
        "heatmapMaxZoom": 14,
        "circleMinZoom": 12,
        "transitionRange": 2,
        "enableClustering": True,
        "clusterRadius": 50,
        "clusterAggregation": "count",
        "clusterCategories": 5,
    }
    if extra:
        o.update(extra)
    return o


PANELS = [
    ("Incident Heatmap", panel_options(
        "bis_blotter", "incident_point",
        ["blotter_no", "incident_type", "incident_datetime", "location", "status"],
        "coolwarm",
        {"filter": {"incident_point": {"_nnull": True}}})),
    ("Household & Risk Density", panel_options(
        "bis_households", "location",
        ["household_no", "purok.name", "address_line", "dwelling_type", "risk_tags"],
        "viridis",
        {"filter": {"location": {"_nnull": True}}})),
    ("Vulnerable Residents", panel_options(
        "bis_residents", "field_point",
        ["first_name", "last_name", "sector_tags", "household.household_no",
         "emergency_contact_phone"],
        "plasma",
        {"filter": {"field_point": {"_nnull": True}}})),
]


def ensure_panel(dash_id, name, spec):
    s, d = req("GET", f"/panels?filter%5Bdashboard%5D%5B_eq%5D={dash_id}"
               f"&filter%5Bname%5D%5B_eq%5D={Q(name)}&limit=1")
    if d.get("data"):
        req("PATCH", f"/panels/{d['data'][0]['id']}", spec)
        print(f"  ~ panel {name} (patched)")
        return
    s, _ = req("POST", "/panels", dict(spec, dashboard=dash_id, name=name,
                                       show_header=True))
    print(f"  + panel {name}" if s in (200, 201) else f"  !! panel {name}: {s}")


def build():
    s, d = req("GET", "/dashboards?filter%5Bname%5D%5B_eq%5D=BIS%20Dashboard&limit=1")
    dash = (d.get("data") or [{}])[0].get("id")
    if not dash:
        print("  !! BIS Dashboard not found")
        return
    positions = [(1, 78), (29, 78), (1, 100)]
    for (name, options), (x, y) in zip(PANELS, positions):
        ensure_panel(dash, name, {
            "type": PANEL_TYPE, "options": options,
            "position_x": x, "position_y": y, "width": 27, "height": 22})
    print("done.")


if __name__ == "__main__":
    build()
