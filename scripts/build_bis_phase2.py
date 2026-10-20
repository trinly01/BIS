#!/usr/bin/env python3
"""BIS Phase 2 — print templates + Insights dashboard (echarts flows/panels).

- print_template rows (LiquidJS HTML) + `print` alias fields w/ templateSelection
- `settings` M2O on bis_document_requests -> bis_settings + create-flow that stamps
  the singleton id (so letterhead renders) + backfill existing rows
- "BIS Dashboard" w/ 6 metric panels + 5 echarts panels powered by
  webhook flows (likha_sql -> exec returning an ECharts option object)

Idempotent: safe to re-run. NOTE: the exec op code contains `$` tokens —
always edit this file, never inline via `python -c "..."` (skill rule 17).
"""
import json, os, sys, urllib.request, urllib.error, urllib.parse

BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ.get("DIRECTUS_TOKEN", "RBzmMVX7UP9baKtLiHV6RmmTx9s9tmFZ")
HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0"}
DRY = "--dry-run" in sys.argv


def req(method, path, body=None, quiet=False):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=HDRS)
    if DRY and method != "GET":
        print(f"  DRY {method} {path}")
        return 0, {}
    try:
        with urllib.request.urlopen(r) as resp:
            txt = resp.read().decode()
            return resp.status, json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        try:
            j = json.loads(txt)
        except Exception:
            j = {"raw": txt[:400]}
        if not quiet:
            print(f"  !! {method} {path} -> {e.code}: {json.dumps(j)[:400]}")
        return e.code, j


def find_item(col, filter_q):
    s, d = req("GET", f"/items/{col}?{filter_q}", quiet=True)
    return d["data"][0] if s == 200 and d.get("data") else None


def find_flow(name):
    s, d = req("GET", f"/flows?filter%5Bname%5D%5B_eq%5D={urllib.parse.quote(name)}&limit=1",
               quiet=True)
    return d["data"][0] if s == 200 and d.get("data") else None


def ensure_field(col, spec):
    s, d = req("GET", f"/fields/{col}?limit=-1", quiet=True)
    names = {f["field"] for f in d.get("data", [])} if s == 200 else set()
    if spec["field"] in names:
        req("PATCH", f"/fields/{col}/{spec['field']}", {"meta": spec.get("meta", {})})
        return
    req("POST", f"/fields/{col}", spec)


def ensure_relation(col, field, related, one_field=None):
    s, d = req("GET", f"/relations/{col}", quiet=True)
    if s == 200 and any(r["field"] == field for r in d.get("data", [])):
        return
    body = {"collection": col, "field": field, "related_collection": related}
    if one_field:
        body["meta"] = {"one_field": one_field}
    s, _ = req("POST", "/relations", body)
    if s not in (200, 201):
        print(f"  !! rel {col}.{field}")


def ensure_template(name, code):
    row = find_item("print_template", f"filter%5Bname%5D%5B_eq%5D={urllib.parse.quote(name)}&fields=id")
    if row:
        req("PATCH", f"/items/print_template/{row['id']}", {"name": name, "code": code})
        print(f"  = template {name}")
        return row["id"]
    s, d = req("POST", "/items/print_template", {"name": name, "code": code, "status": "published"})
    tid = (d.get("data") or {}).get("id")
    print(f"  + template {name}" if tid else f"  !! template {name}")
    return tid


def ensure_print_field(col, group, template_id):
    spec = {"field": "print", "type": "alias", "meta": {
        "special": ["alias", "no-data"], "interface": "print", "width": "half",
        "group": group,
        "options": {"templateSelection": {"collection": "print_template",
                                          "key": template_id},
                    "fields": ["*.*.*"]}}}
    ensure_field(col, spec)
    print(f"  = print field {col}.print")


def ensure_op(flow_id, spec):
    s, d = req("GET", f"/flows/{flow_id}", quiet=True)
    ops = (d.get("data") or {}).get("operations", [])
    if ops:
        s, od = req("GET", f"/operations/{ops[0]}", quiet=True) if False else (0, {})
    # create
    s, d = req("POST", "/operations", dict(spec, flow=flow_id))
    op = (d.get("data") or {})
    if s not in (200, 201):
        print(f"  !! op {spec.get('key')} on {flow_id}: {s}")
        return None
    return op.get("id")


def ensure_chart_flow(name, sql, exec_code):
    """webhook flow: likha_sql (key sql_1) -> exec (key chart) returning option."""
    fl = find_flow(name)
    if fl:
        print(f"  = flow {name}")
        return fl["id"]
    s, d = req("POST", "/flows", {
        "name": name, "icon": "bar_chart", "color": "#26A69A", "status": "active",
        "trigger": "webhook", "accountability": "all",
        "options": {"error_on_reject": True}})
    fid = (d.get("data") or {}).get("id")
    if not fid:
        print(f"  !! flow {name}")
        return None
    op1 = ensure_op(fid, {"name": "SQL", "key": "sql_1", "type": "likha_sql",
                          "position_x": 21, "position_y": 1,
                          "options": {"sql": sql, "binding": []}})
    op2 = ensure_op(fid, {"name": "Build Option", "key": "chart", "type": "exec",
                          "position_x": 39, "position_y": 1,
                          "options": {"code": exec_code}})
    if op1 and op2:
        req("PATCH", f"/operations/{op1}", {"resolve": op2})
        req("PATCH", f"/flows/{fid}", {"operation": op1})
        print(f"  + flow {name}")
    return fid


def ensure_dashboard(name):
    s, d = req("GET", f"/dashboards?filter%5Bname%5D%5B_eq%5D={urllib.parse.quote(name)}&limit=1",
               quiet=True)
    if s == 200 and d.get("data"):
        print(f"  = dashboard {name}")
        return d["data"][0]["id"]
    s, d = req("POST", "/dashboards",
               {"name": name, "icon": "space_dashboard", "color": "#26A69A",
                "note": "Barangay Information System overview"})
    did = (d.get("data") or {}).get("id")
    print(f"  + dashboard {name}" if did else f"  !! dashboard {name}")
    return did


def ensure_panel(dash_id, name, spec):
    s, d = req("GET", f"/panels?filter%5Bdashboard%5D%5B_eq%5D={dash_id}"
               f"&filter%5Bname%5D%5B_eq%5D={urllib.parse.quote(name)}&limit=1", quiet=True)
    if s == 200 and d.get("data"):
        req("PATCH", f"/panels/{d['data'][0]['id']}", spec)
        return
    s, _ = req("POST", "/panels", dict(spec, dashboard=dash_id, name=name, show_header=True))
    if s not in (200, 201):
        print(f"  !! panel {name}: {s}")


# ============================ TEMPLATES ============================

CERT_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 16mm 18mm; }
  * { box-sizing: border-box; }
  body { font-family: 'Times New Roman', Times, serif; font-size: 13px; color: #111; margin: 0; }
  .head { text-align: center; line-height: 1.35; }
  .head .rep { font-size: 12px; }
  .head .lgu { font-size: 12px; }
  .head .brgy { font-size: 16px; font-weight: 700; letter-spacing: 1px; }
  .head .office { font-size: 11px; font-style: italic; margin-top: 2px; }
  .rule { border: 0; border-top: 2.5px solid #111; margin: 8px 0 2px; }
  .rule2 { border: 0; border-top: 1px solid #111; margin: 0 0 14px; }
  .title { text-align: center; font-size: 19px; font-weight: 700; letter-spacing: 3px; margin: 18px 0 4px; }
  .subtitle { text-align: center; font-size: 11px; color: #444; margin-bottom: 22px; }
  .body { text-align: justify; line-height: 1.7; }
  .body p { margin: 10px 0; text-indent: 40px; }
  .to { text-indent: 0 !important; font-weight: 700; }
  .sig { margin-top: 56px; width: 100%; }
  .sig .cell { display: inline-block; width: 49%; vertical-align: top; }
  .sig .name { font-weight: 700; text-transform: uppercase; text-align: center; }
  .sig .lbl { text-align: center; font-size: 11px; border-top: 1px solid #111; width: 70%; margin: 0 auto; padding-top: 2px; }
  .foot { margin-top: 40px; font-size: 10.5px; border-top: 1px solid #999; padding-top: 6px; color: #333; }
  .foot td { padding: 1px 10px 1px 0; vertical-align: top; }
  .seal { float: right; width: 90px; height: 90px; border: 1px dashed #888; border-radius: 50%;
          text-align: center; font-size: 8px; color: #888; padding-top: 34px; }
  .muted { color: #555; }
</style>
</head>
<body>

<div class="head">
  <div class="rep">Republic of the Philippines</div>
  <div class="lgu">Province of {{ settings.province | default: '__________' }}</div>
  <div class="lgu">{{ settings.city_municipality | default: '__________' }}</div>
  <div class="brgy">{{ settings.barangay_name | default: 'BARANGAY __________' | upcase }}</div>
  <div class="office">Office of the Punong Barangay</div>
</div>
<hr class="rule"><hr class="rule2">

<div class="title">{{ document_type.name | default: 'BARANGAY CERTIFICATION' | upcase }}</div>
<div class="subtitle">
  {% if serial_no %}Control No. {{ serial_no }}{% endif %}
</div>

<div class="body">
  <p class="to">TO WHOM IT MAY CONCERN:</p>

  {% assign full_name = resident.first_name | append: ' ' %}
  {% if resident.middle_name %}{% assign full_name = full_name | append: resident.middle_name | append: ' ' %}{% endif %}
  {% assign full_name = full_name | append: resident.last_name %}
  {% if resident.suffix %}{% assign full_name = full_name | append: ' ' | append: resident.suffix %}{% endif %}

  {% case document_type.code %}
  {% when 'indigency' %}
    <p>This is to certify that <b>{{ full_name | upcase }}</b>,
    {{ resident.civil_status | default: '' }}, of legal age, is a bonafide indigent resident of
    {{ resident.address_line | default: 'this barangay' }}{% if resident.purok.name %}, {{ resident.purok.name }}{% endif %},
    {{ settings.barangay_name }}, {{ settings.city_municipality }}.</p>
    <p>This certification is issued upon the request of the above-named person for
    <b>{{ purpose | default: 'whatever legal purpose it may serve' }}</b>.</p>
  {% when 'residency' %}
    <p>This is to certify that <b>{{ full_name | upcase }}</b>,
    {{ resident.civil_status | default: '' }}, is a bonafide resident of
    {{ resident.address_line | default: 'this barangay' }}{% if resident.purok.name %}, {{ resident.purok.name }}{% endif %},
    {{ settings.barangay_name }}, {{ settings.city_municipality }}{% if resident.residency_start %},
    and has been residing therein since {{ resident.residency_start | date: '%B %Y' }}{% endif %}.</p>
    <p>This certification is issued upon request for
    <b>{{ purpose | default: 'whatever legal purpose it may serve' }}</b>.</p>
  {% when 'business_clearance' %}
    <p>This is to certify that the business applied for by <b>{{ full_name | upcase }}</b>,
    to be located at {{ resident.address_line | default: 'this barangay' }},
    {{ settings.barangay_name }}, {{ settings.city_municipality }}, has been inspected and found
    to be in conformity with existing barangay regulations, and is hereby granted
    <b>BARANGAY BUSINESS CLEARANCE</b> to operate.</p>
    <p>Purpose: <b>{{ purpose | default: 'Business permit application/renewal' }}</b>.</p>
  {% when 'good_moral' %}
    <p>This is to certify that <b>{{ full_name | upcase }}</b>,
    {{ resident.civil_status | default: '' }}, a resident of
    {{ resident.address_line | default: 'this barangay' }}, {{ settings.barangay_name }},
    {{ settings.city_municipality }}, is personally known to this office to be of
    <b>good moral character</b> and has no derogatory record on file in this barangay.</p>
    <p>This certification is issued upon request for
    <b>{{ purpose | default: 'whatever legal purpose it may serve' }}</b>.</p>
  {% when 'first_time_jobseeker' %}
    <p>This is to certify that <b>{{ full_name | upcase }}</b>, a resident of
    {{ resident.address_line | default: 'this barangay' }}, {{ settings.barangay_name }},
    {{ settings.city_municipality }}, is a <b>first-time jobseeker</b> as defined under
    Republic Act No. 11261, and is entitled to the fee waiver privileges thereof.</p>
    <p>This certification is issued free of charge pursuant to RA 11261.</p>
  {% else %}
    <p>This is to certify that <b>{{ full_name | upcase }}</b>,
    {{ resident.civil_status | default: '' }}, of legal age,
    {% if resident.birthdate %}born on {{ resident.birthdate | date: '%B %e, %Y' }},{% endif %}
    is a bonafide resident of {{ resident.address_line | default: 'this barangay' }}{% if resident.purok.name %},
    {{ resident.purok.name }}{% endif %}, {{ settings.barangay_name }}, {{ settings.city_municipality }}.</p>
    <p>Per available records, the above-named person has no pending case or derogatory
    record filed in this barangay.</p>
    <p>This <b>{{ document_type.name | default: 'certification' }}</b> is issued upon the request
    of the above-named person for <b>{{ purpose | default: 'whatever legal purpose it may serve' }}</b>.</p>
  {% endcase %}

  <p>Issued this <b>{{ issued_date | default: date_requested | date: '%e day of %B, %Y' }}</b>
  at {{ settings.barangay_name }}, {{ settings.city_municipality }}, Philippines.</p>
  {% if valid_until %}<p style="text-indent:40px">Valid until <b>{{ valid_until | date: '%B %e, %Y' }}</b>.</p>{% endif %}
</div>

<div class="seal">OFFICIAL SEAL</div>
<div class="sig">
  <div class="cell">
    <div class="muted" style="font-size:10px">Certified by:</div>
    <br><br>
    <div class="name">{{ signatory.name | default: settings.punong_barangay | default: '________________' }}</div>
    <div class="lbl">{{ signatory.signatory_label | default: 'Punong Barangay' }}</div>
  </div>
</div>

<div class="foot">
  <table>
    <tr>
      {% if or_number %}<td><b>O.R. No.:</b> {{ or_number }}</td>{% endif %}
      {% if fee %}<td><b>Amount Paid:</b> ₱{{ fee }}</td>{% endif %}
      {% if or_date %}<td><b>Date Paid:</b> {{ or_date | date: '%b %e, %Y' }}</td>{% endif %}
    </tr>
    <tr><td colspan="3" class="muted">Not valid without the official dry seal. Verify at the Barangay Hall.
    {% if request_no %}Ref: {{ request_no }}{% endif %}</td></tr>
  </table>
</div>

</body>
</html>
"""

BLOTTER_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 15mm 16mm; }
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; color: #1a1a1a; margin: 0; }
  .head { text-align: center; line-height: 1.35; }
  .brgy { font-size: 15px; font-weight: 700; letter-spacing: 1px; }
  .office { font-size: 10.5px; font-style: italic; }
  .rule { border: 0; border-top: 2px solid #111; margin: 8px 0 12px; }
  .title { text-align: center; font-size: 15px; font-weight: 700; letter-spacing: 2px; margin: 6px 0 14px; }
  .kv { display: table; width: 100%; margin-bottom: 10px; }
  .kv .row { display: table-row; }
  .kv .k, .kv .v { display: table-cell; padding: 3px 6px; border-bottom: 1px dotted #ddd; }
  .kv .k { font-weight: 700; width: 150px; color: #333; }
  .sec-h { background: #f4f4f4; border-left: 4px solid #333; font-weight: 700; font-size: 10px;
           letter-spacing: 1px; padding: 4px 8px; margin: 12px 0 6px; }
  .narr { border: 1px solid #ccc; padding: 8px 10px; text-align: justify; line-height: 1.6; }
  table.grid { width: 100%; border-collapse: collapse; margin-top: 4px; }
  table.grid td, table.grid th { border: 1px solid #bbb; padding: 4px 7px; font-size: 10px; text-align: left; }
  table.grid th { background: #eee; }
  .sig { margin-top: 48px; }
  .sig .name { font-weight: 700; text-transform: uppercase; }
  .sig .lbl { font-size: 10px; border-top: 1px solid #111; width: 220px; padding-top: 2px; }
  .badge { display: inline-block; border: 1px solid #333; border-radius: 10px; padding: 1px 10px;
           font-size: 9px; font-weight: 700; text-transform: uppercase; }
</style>
</head>
<body>

<div class="head">
  <div>Republic of the Philippines</div>
  <div class="brgy">{{ blotter_no | default: 'BARANGAY' | upcase }} — BLOTTER EXTRACT</div>
  <div class="office">Barangay Incident Record (Kopya para sa Rekord)</div>
</div>
<hr class="rule">

<div class="kv">
  <div class="row"><div class="k">Blotter No.</div><div class="v"><b>{{ blotter_no }}</b></div></div>
  <div class="row"><div class="k">Date Reported</div><div class="v">{{ date_reported | date: '%B %e, %Y %I:%M %p' }}</div></div>
  <div class="row"><div class="k">Incident Date/Time</div><div class="v">{{ incident_datetime | default: '—' | date: '%B %e, %Y %I:%M %p' }}</div></div>
  <div class="row"><div class="k">Location</div><div class="v">{{ location | default: '—' }}</div></div>
  <div class="row"><div class="k">Incident Type</div><div class="v"><span class="badge">{{ incident_type | replace: '_', ' ' | upcase }}</span></div></div>
  <div class="row"><div class="k">Status</div><div class="v">{{ status | replace: '_', ' ' | upcase }}</div></div>
</div>

<div class="sec-h">NARRATIVE / SALAYSAY</div>
<div class="narr">{{ narrative | default: '—' | newline_to_br }}</div>

<div class="sec-h">PARTIES INVOLVED / MGA KINAUUKULAN</div>
<table class="grid">
  <tr><th style="width:110px">Role</th><th>Name</th><th>Contact</th><th>Statement</th></tr>
  {% for p in parties %}
  <tr>
    <td>{{ p.party_role | upcase }}</td>
    <td>{{ p.resident.first_name }} {{ p.resident.last_name }}</td>
    <td>{{ p.contact_number | default: '—' }}</td>
    <td>{{ p.statement | default: '—' }}</td>
  </tr>
  {% endfor %}
</table>
{% if other_parties %}<p style="font-size:10px"><b>Other parties:</b> {{ other_parties }}</p>{% endif %}

<div class="sec-h">ACTION TAKEN / AKSIYON</div>
<div class="narr">{{ action_taken | default: '—' | newline_to_br }}</div>
{% if referred_to %}
<div class="kv">
  <div class="row"><div class="k">Referred To</div><div class="v">{{ referred_to }}{% if referred_at %} — {{ referred_at | date: '%b %e, %Y' }}{% endif %}</div></div>
  {% if kp_case %}<div class="row"><div class="k">KP Case No.</div><div class="v">{{ kp_case.case_no }}</div></div>{% endif %}
</div>
{% endif %}

<div class="sig">
  <div>Recorded by:</div><br><br>
  <div class="name">{{ recorded_by.first_name | default: '________________' }} {{ recorded_by.last_name }}</div>
  <div class="lbl">Barangay Official on Duty</div>
</div>

</body>
</html>
"""

KP_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 16mm 18mm; }
  * { box-sizing: border-box; }
  body { font-family: 'Times New Roman', Times, serif; font-size: 13px; color: #111; margin: 0; }
  .head { text-align: center; line-height: 1.35; }
  .brgy { font-size: 16px; font-weight: 700; letter-spacing: 1px; }
  .office { font-size: 11px; font-style: italic; }
  .rule { border: 0; border-top: 2.5px solid #111; margin: 8px 0 2px; }
  .rule2 { border: 0; border-top: 1px solid #111; margin: 0 0 14px; }
  .title { text-align: center; font-size: 16px; font-weight: 700; letter-spacing: 2px; margin: 14px 0; }
  .kp { font-size: 10px; letter-spacing: 2px; text-align: center; color: #444; }
  .kv { display: table; width: 100%; margin: 10px 0; }
  .kv .row { display: table-row; }
  .kv .k, .kv .v { display: table-cell; padding: 3px 6px; border-bottom: 1px dotted #ddd; }
  .kv .k { font-weight: 700; width: 140px; }
  .body { text-align: justify; line-height: 1.7; }
  .body p { margin: 10px 0; text-indent: 40px; }
  table.grid { width: 100%; border-collapse: collapse; margin: 10px 0; }
  table.grid td, table.grid th { border: 1px solid #999; padding: 5px 8px; font-size: 11.5px; text-align: left; }
  table.grid th { background: #f0f0f0; }
  .sig { margin-top: 48px; width: 100%; }
  .sig .cell { display: inline-block; width: 49%; vertical-align: top; text-align: center; }
  .sig .name { font-weight: 700; text-transform: uppercase; }
  .sig .lbl { font-size: 11px; border-top: 1px solid #111; width: 70%; margin: 0 auto; padding-top: 2px; }
</style>
</head>
<body>

<div class="head">
  <div>Republic of the Philippines</div>
  <div class="brgy">{{ complainant.purok.name | default: 'BARANGAY' | upcase }}</div>
  <div class="office">Office of the Lupong Tagapamayapa</div>
</div>
<hr class="rule"><hr class="rule2">
<div class="kp">KATARUNGANG PAMBARANGAY</div>
<div class="title">NOTICE OF HEARING / PAUNAWA NG PAGDINIG</div>

<div class="kv">
  <div class="row"><div class="k">KP Case No.</div><div class="v"><b>{{ case_no }}</b></div></div>
  <div class="row"><div class="k">Complainant</div><div class="v">
    {% if complainant %}{{ complainant.first_name }} {{ complainant.last_name }}{% else %}{{ complainant_name }}{% endif %}</div></div>
  <div class="row"><div class="k">Respondent</div><div class="v">
    {% if respondent %}{{ respondent.first_name }} {{ respondent.last_name }}{% else %}{{ respondent_name }}{% endif %}</div></div>
  <div class="row"><div class="k">Case Type</div><div class="v">{{ case_type | replace: '_', ' ' | capitalize }}</div></div>
  <div class="row"><div class="k">Date Filed</div><div class="v">{{ date_filed | date: '%B %e, %Y' }}</div></div>
  <div class="row"><div class="k">Status</div><div class="v">{{ status | replace: '_', ' ' | upcase }}</div></div>
</div>

<div class="body">
  <p>You are hereby notified to appear before the Lupong Tagapamayapa of this barangay
  on the schedule(s) indicated below for
  <b>{{ hearings.first.hearing_type | default: status | replace: '_', ' ' }}</b> proceedings
  relative to the above-captioned case.</p>
  <p>Your failure to appear without justifiable cause may result in the dismissal of the
  complaint or the issuance of a certification that bars or permits court action, as the
  case may be, pursuant to the Katarungang Pambarangay Law (P.D. 1508 / LGC Sec. 399-422).</p>
</div>

<table class="grid">
  <tr><th>Hearing</th><th>Schedule</th><th>Venue</th><th>Outcome</th></tr>
  {% for h in hearings %}
  <tr>
    <td>{{ h.hearing_type | capitalize }}</td>
    <td>{{ h.scheduled_at | date: '%B %e, %Y %I:%M %p' }}</td>
    <td>{{ h.venue | default: 'Barangay Hall' }}</td>
    <td>{{ h.outcome | replace: '_', ' ' | capitalize }}</td>
  </tr>
  {% endfor %}
</table>

<div class="sig">
  <div class="cell">
    <div style="font-size:10px">Issued by:</div><br><br>
    <div class="name">{{ lupon_member.name | default: '________________' }}</div>
    <div class="lbl">Lupon / Pangkat Member</div>
  </div>
  <div class="cell">
    <div style="font-size:10px">Received by (Respondent):</div><br><br>
    <div class="name">________________________</div>
    <div class="lbl">Signature over printed name / Date</div>
  </div>
</div>

</body>
</html>
"""

# ============================ CHART EXEC CODES ============================

def exec_bar(title, cat_expr="r.name", val_expr="Number(r.cnt)", horizontal=False):
    if horizontal:
        axes = ("yAxis: { type: 'category', data: rows.map(function(r){ return " + cat_expr + "; }) },\n"
                "    xAxis: { type: 'value' },")
    else:
        axes = ("xAxis: { type: 'category', data: rows.map(function(r){ return " + cat_expr + "; }) },\n"
                "    yAxis: { type: 'value' },")
    return (
        "module.exports = async function(data) {\n"
        "  var rows = data.sql_1 || data.$last || [];\n"
        "  if (rows && rows.rows) rows = rows.rows;\n"
        "  return {\n"
        "    title: { text: " + json.dumps(title) + ", left: 'center' },\n"
        "    tooltip: { trigger: 'axis' },\n"
        "    grid: { left: 10, right: 20, top: 40, bottom: 10, containLabel: true },\n"
        "    " + axes + "\n"
        "    series: [{ type: 'bar', data: rows.map(function(r){ return " + val_expr + "; }),"
        "      itemStyle: { color: '#26A69A', borderRadius: [4,4,0,0] },"
        "      label: { show: true, position: " + ("'right'" if horizontal else "'top'") + " } }]\n"
        "  };\n"
        "}")


def exec_pie(title, name_expr="r.name", val_expr="Number(r.cnt)"):
    return (
        "module.exports = async function(data) {\n"
        "  var rows = data.sql_1 || data.$last || [];\n"
        "  if (rows && rows.rows) rows = rows.rows;\n"
        "  return {\n"
        "    title: { text: " + json.dumps(title) + ", left: 'center' },\n"
        "    tooltip: { trigger: 'item' },\n"
        "    legend: { bottom: 0, type: 'scroll' },\n"
        "    series: [{ type: 'pie', radius: ['40%','68%'], center: ['50%','55%'],\n"
        "      itemStyle: { borderRadius: 5, borderColor: '#fff', borderWidth: 2 },\n"
        "      label: { formatter: '{b}: {c}' },\n"
        "      data: rows.map(function(r){ return { name: " + name_expr + ", value: " + val_expr + " }; }) }]\n"
        "  };\n"
        "}")


def exec_line(title, x_expr="r.m", val_expr="Number(r.cnt)"):
    return (
        "module.exports = async function(data) {\n"
        "  var rows = data.sql_1 || data.$last || [];\n"
        "  if (rows && rows.rows) rows = rows.rows;\n"
        "  return {\n"
        "    title: { text: " + json.dumps(title) + ", left: 'center' },\n"
        "    tooltip: { trigger: 'axis' },\n"
        "    grid: { left: 10, right: 20, top: 40, bottom: 10, containLabel: true },\n"
        "    xAxis: { type: 'category', data: rows.map(function(r){ return " + x_expr + "; }), boundaryGap: false },\n"
        "    yAxis: { type: 'value', minInterval: 1 },\n"
        "    series: [{ type: 'line', smooth: true, areaStyle: { opacity: 0.15 },\n"
        "      itemStyle: { color: '#26A69A' },\n"
        "      data: rows.map(function(r){ return " + val_expr + "; }) }]\n"
        "  };\n"
        "}")


# ============================ BUILD ============================

def build():
    print("== settings M2O on bis_document_requests ==")
    ensure_field("bis_document_requests",
                 {"field": "settings", "type": "uuid",
                  "meta": {"interface": "select-dropdown-m2o", "hidden": True,
                           "readonly": True, "group": "grp_request", "width": "half",
                           "note": "Auto-stamped w/ the bis_settings singleton (letterhead)"},
                  "schema": {}})
    ensure_relation("bis_document_requests", "settings", "bis_settings")

    s, d = req("GET", "/items/bis_settings?fields=id", quiet=True)
    settings_id = (d.get("data") or {}).get("id")
    print("  settings singleton:", settings_id)

    # stamping flow: on create of document_requests -> set settings FK
    fl = find_flow("bis_stamp_settings")
    if fl:
        print("  = flow bis_stamp_settings")
    else:
        s, d = req("POST", "/flows", {
            "name": "bis_stamp_settings", "icon": "bolt", "color": "#26A69A",
            "status": "active", "trigger": "event", "accountability": "all",
            "options": {"type": "action", "scope": ["items.create"],
                        "collections": ["bis_document_requests"]}})
        fid = (d.get("data") or {}).get("id")
        if fid:
            op = ensure_op(fid, {"name": "Stamp settings", "key": "stamp", "type": "item-update",
                                 "position_x": 21, "position_y": 1,
                                 "options": {
                                     "collection": "bis_document_requests",
                                     "key": "{{$trigger.key}}",
                                     "payload": {"settings": settings_id},
                                     "emitEvents": False,
                                     "permissions": "$full"}})
            if op:
                req("PATCH", f"/flows/{fid}", {"operation": op})
                print("  + flow bis_stamp_settings")
    # backfill existing requests
    s, d = req("GET", "/items/bis_document_requests?filter%5Bsettings%5D%5B_null%5D=true&fields=id&limit=-1",
               quiet=True)
    for row in (d.get("data") or []):
        req("PATCH", f"/items/bis_document_requests/{row['id']}", {"settings": settings_id})
    if d.get("data"):
        print(f"  backfilled settings on {len(d['data'])} request(s)")

    print("== print templates ==")
    cert_id = ensure_template("bis_barangay_certificate", CERT_TEMPLATE)
    blotter_id = ensure_template("bis_blotter_extract", BLOTTER_TEMPLATE)
    kp_id = ensure_template("bis_kp_hearing_notice", KP_TEMPLATE)

    print("== print fields ==")
    if cert_id:
        ensure_print_field("bis_document_requests", "grp_release", cert_id)
    if blotter_id:
        ensure_print_field("bis_blotter", "grp_action", blotter_id)
    if kp_id:
        ensure_print_field("bis_kp_cases", "grp_case", kp_id)

    print("== chart flows ==")
    f_purok = ensure_chart_flow(
        "bis_chart_residents_per_purok",
        "SELECT p.name AS name, COUNT(r.id) AS cnt FROM bis_residents r "
        "JOIN bis_puroks p ON p.id = r.purok WHERE r.residency_status = 'active' "
        "GROUP BY p.name ORDER BY p.name",
        exec_bar("Active Residents per Purok"))
    f_doctype = ensure_chart_flow(
        "bis_chart_docs_by_type",
        "SELECT t.name AS name, COUNT(r.id) AS cnt FROM bis_document_requests r "
        "JOIN bis_document_types t ON t.id = r.document_type "
        "WHERE r.status = 'released' GROUP BY t.name ORDER BY cnt DESC",
        exec_pie("Documents Issued by Type"))
    f_blotter = ensure_chart_flow(
        "bis_chart_blotter_by_type",
        "SELECT COALESCE(incident_type, 'other') AS name, COUNT(*) AS cnt "
        "FROM bis_blotter GROUP BY 1 ORDER BY cnt DESC",
        exec_bar("Blotter by Incident Type", cat_expr="r.name", horizontal=True))
    f_sector = ensure_chart_flow(
        "bis_chart_sector_tags",
        "SELECT tag AS name, COUNT(*) AS cnt FROM ("
        "SELECT jsonb_array_elements_text(sector_tags::jsonb) AS tag FROM bis_residents "
        "WHERE residency_status = 'active' AND sector_tags IS NOT NULL AND sector_tags <> '') s "
        "GROUP BY tag ORDER BY cnt DESC",
        exec_pie("Residents by Sector"))
    f_trend = ensure_chart_flow(
        "bis_chart_issuance_trend",
        "SELECT to_char(date_trunc('month', issued_date), 'YYYY-MM') AS m, "
        "COUNT(*) AS cnt FROM bis_document_requests "
        "WHERE status = 'released' AND issued_date IS NOT NULL GROUP BY 1 ORDER BY 1",
        exec_line("Monthly Certificates Issued", x_expr="r.m"))

    print("== dashboard + panels ==")
    dash = ensure_dashboard("BIS Dashboard")
    if not dash:
        return

    metrics = [
        ("Active Residents", "bis_residents",
         {"_and": [{"residency_status": {"_eq": "active"}}]}, "#26A69A"),
        ("Households", "bis_households", None, "#8D6E63"),
        ("Certificates Issued", "bis_document_requests",
         {"_and": [{"status": {"_eq": "released"}}]}, "#42A5F5"),
        ("Open Blotter", "bis_blotter",
         {"_and": [{"status": {"_in": ["open", "endorsed_to_kp"]}}]}, "#EF5350"),
        ("Active KP Cases", "bis_kp_cases",
         {"_and": [{"status": {"_nin": ["settled", "cfa_issued", "dismissed"]}}]}, "#FFA726"),
        ("Active Permits", "bis_business_permits",
         {"_and": [{"status": {"_eq": "active"}}]}, "#66BB6A"),
    ]
    for i, (name, col, filt, color) in enumerate(metrics):
        opts = {"collection": col, "field": "id", "function": "count", "sortField": None}
        if filt:
            opts["filter"] = filt
        ensure_panel(dash, name, {"type": "metric", "options": opts, "color": color,
                                  "position_x": 1 + i * 9, "position_y": 1,
                                  "width": 8, "height": 9})

    charts = [
        ("Residents per Purok", f_purok, 1, 11),
        ("Documents by Type", f_doctype, 29, 11),
        ("Blotter by Type", f_blotter, 1, 33),
        ("Residents by Sector", f_sector, 29, 33),
        ("Issuance Trend", f_trend, 1, 55),
    ]
    for name, fid, x, y in charts:
        if not fid:
            continue
        ensure_panel(dash, name, {
            "type": "echarts-panel",
            "options": {"flow": {"key": fid, "collection": "directus_flows"}},
            "position_x": x, "position_y": y, "width": 27, "height": 22})

    print("done.")


if __name__ == "__main__":
    build()
