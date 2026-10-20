#!/usr/bin/env python3
"""BIS print expansion — every printable gets a template + `print` field.

Adds `settings` M2O -> bis_settings (letterhead) to all printable collections,
extends `bis_stamp_settings` flow scope, backfills, then creates templates:

  bis_business_permit        -> bis_business_permits.print   (Permit to Operate)
  bis_barangay_id            -> bis_residents.print          (barangay ID card)
  bis_purok_roster           -> bis_puroks.print             (RBI resident roster)
  bis_posting                -> bis_announcements.print      (public posting copy)
  bis_kp_amicable_settlement -> bis_kp_cases.print_settlement (KP Form 16-style)
  bis_kp_cert_to_file_action -> bis_kp_cases.print_cfa        (KP Form 18-style)

Also updates bis_blotter_extract / bis_kp_hearing_notice to render the letterhead
from `settings` (now available on those collections).

Idempotent. Never edits inline — $ tokens live in this file only (skill rule 17).
"""
import json, os, urllib.request, urllib.error, urllib.parse

BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ.get("DIRECTUS_TOKEN", "RBzmMVX7UP9baKtLiHV6RmmTx9s9tmFZ")
HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0"}
Q = urllib.parse.quote

PRINTABLES = ["bis_document_requests", "bis_business_permits", "bis_residents",
              "bis_kp_cases", "bis_blotter", "bis_puroks", "bis_announcements"]


def req(method, path, body=None, quiet=False):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=HDRS)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        if not quiet:
            print(f"  !! {method} {path} -> {e.code}: {txt[:300]}")
        return e.code, {}


def ensure_field(col, spec):
    s, d = req("GET", f"/fields/{col}?limit=-1", quiet=True)
    names = {f["field"] for f in d.get("data", [])} if s == 200 else set()
    if spec["field"] in names:
        req("PATCH", f"/fields/{col}/{spec['field']}", {"meta": spec.get("meta", {})})
    else:
        req("POST", f"/fields/{col}", spec)


def ensure_relation(col, field, related):
    s, d = req("GET", f"/relations/{col}", quiet=True)
    if s == 200 and any(r["field"] == field for r in d.get("data", [])):
        return
    s, _ = req("POST", "/relations",
               {"collection": col, "field": field, "related_collection": related})
    if s not in (200, 201):
        print(f"  !! rel {col}.{field}")


def ensure_template(name, code):
    s, d = req("GET", f"/items/print_template?filter%5Bname%5D%5B_eq%5D={Q(name)}&fields=id",
               quiet=True)
    rows = d.get("data") or []
    if rows:
        req("PATCH", f"/items/print_template/{rows[0]['id']}", {"code": code})
        print(f"  = template {name}")
        return rows[0]["id"]
    s, d = req("POST", "/items/print_template",
               {"name": name, "code": code, "status": "published"})
    tid = (d.get("data") or {}).get("id")
    print(f"  + template {name}" if tid else f"  !! template {name}")
    return tid


def print_field(col, fname, group, tpl_id):
    ensure_field(col, {"field": fname, "type": "alias", "meta": {
        "special": ["alias", "no-data"], "interface": "print", "width": "half",
        "group": group,
        "options": {"templateSelection": {"collection": "print_template", "key": tpl_id},
                    "fields": ["*.*.*"]}}})
    print(f"  = {col}.{fname}")


# ============================ TEMPLATES ============================

PERMIT = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  @page { size: A4; margin: 18mm 20mm; }
  body { font-family: 'Times New Roman', Times, serif; font-size: 13px; color: #111; margin: 0;
         border: 4px double #111; padding: 14mm 14mm; }
  .head { text-align: center; line-height: 1.35; }
  .brgy { font-size: 17px; font-weight: 700; letter-spacing: 1px; }
  .office { font-size: 11px; font-style: italic; }
  .title { text-align: center; font-size: 21px; font-weight: 700; letter-spacing: 2px; margin: 22px 0 4px; }
  .sub { text-align: center; font-size: 11px; letter-spacing: 4px; margin-bottom: 18px; }
  .pno { text-align: right; font-size: 12px; margin-bottom: 6px; }
  .biz { text-align: center; margin: 16px 0; }
  .biz .nm { font-size: 20px; font-weight: 700; text-transform: uppercase; }
  .biz .own { font-size: 13px; margin-top: 6px; }
  .body { text-align: justify; line-height: 1.7; }
  .body p { margin: 10px 0; text-indent: 40px; }
  .foot { display: table; width: 100%; margin-top: 30px; font-size: 11.5px; }
  .foot .c { display: table-cell; width: 33%; vertical-align: bottom; }
  .sig { text-align: center; margin-top: 60px; }
  .sig .name { font-weight: 700; text-transform: uppercase; font-size: 15px; }
  .sig .lbl { font-size: 11px; border-top: 1px solid #111; width: 55%; margin: 0 auto; padding-top: 3px; }
</style></head><body>

<div class="head">
  <div>Republic of the Philippines</div>
  <div>Province of {{ settings.province | default: '__________' }}</div>
  <div>{{ settings.city_municipality | default: '__________' }}</div>
  <div class="brgy">{{ settings.barangay_name | default: 'BARANGAY ______' | upcase }}</div>
  <div class="office">Office of the Punong Barangay</div>
</div>

<div class="title">BARANGAY BUSINESS CLEARANCE</div>
<div class="sub">PERMIT TO OPERATE</div>
<div class="pno">Permit No.: <b>{{ permit_no }}</b></div>

<div class="biz">
  <div class="nm">{{ business_name }}</div>
  <div class="own">
    {% if owner_resident %}Operated by <b>{{ owner_resident.first_name }} {{ owner_resident.last_name }}</b>
    {% elsif owner_name %}Operated by <b>{{ owner_name }}</b>{% endif %}
    <br>{{ address | default: '' }}{% if purok.name %}, {{ purok.name }}{% endif %},
    {{ settings.barangay_name }}, {{ settings.city_municipality }}
  </div>
</div>

<div class="body">
  <p>This is to certify that the above-named business establishment has been granted
  <b>Barangay Business Clearance</b> pursuant to Sec. 152(c) of the Local Government
  Code of 1991, after due inspection and payment of the required clearance fee.</p>
  <p>This clearance is a prerequisite to the issuance of the corresponding Mayor's/
  Business Permit and is valid until <b>{{ valid_until | date: '%B %e, %Y' }}</b>,
  unless sooner revoked for violation of barangay ordinances.</p>
  <p>Issued this <b>{{ date_issued | date: '%e day of %B, %Y' }}</b> at
  {{ settings.barangay_name }}, {{ settings.city_municipality }}.</p>
</div>

<div class="foot">
  <div class="c"><b>O.R. No.:</b> {{ or_number | default: '—' }}<br>
    <b>Amount Paid:</b> ₱{{ fee | default: '—' }}</div>
  <div class="c"><b>Date Issued:</b> {{ date_issued | date: '%b %e, %Y' }}<br>
    <b>Valid Until:</b> {{ valid_until | date: '%b %e, %Y' }}</div>
</div>

<div class="sig">
  <div class="name">{{ settings.punong_barangay | default: '________________' }}</div>
  <div class="lbl">Punong Barangay</div>
</div>

</body></html>
"""

BARANGAY_ID = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  @page { size: 85.6mm 54mm; margin: 0; }
  body { font-family: Arial, Helvetica, sans-serif; margin: 0; width: 85.6mm; height: 54mm;
         color: #111; }
  .card { width: 100%; height: 100%; border: 1px solid #2e7d32; border-radius: 3mm;
          overflow: hidden; }
  .top { background: #2e7d32; color: #fff; text-align: center; padding: 2mm 0 1.5mm; }
  .top .r { font-size: 5.5pt; letter-spacing: 1px; }
  .top .b { font-size: 8.5pt; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; }
  .mid { display: table; width: 100%; padding: 2.5mm 3mm; }
  .photo { display: table-cell; width: 19mm; height: 24mm; border: 1px solid #999;
           vertical-align: middle; text-align: center; font-size: 6pt; color: #999;
           background: #f4f4f4; }
  .info { display: table-cell; vertical-align: top; padding-left: 3mm; }
  .info .nm { font-size: 9pt; font-weight: 800; text-transform: uppercase; line-height: 1.15; }
  .info .row { font-size: 6pt; margin-top: 1mm; color: #333; }
  .info .tags { margin-top: 1.2mm; }
  .tag { display: inline-block; background: #e8f5e9; border: 0.5px solid #2e7d32; color: #1b5e20;
         border-radius: 2mm; font-size: 5pt; font-weight: 700; padding: 0.4mm 1.6mm;
         margin: 0 0.8mm 0.6mm 0; text-transform: uppercase; }
  .bot { border-top: 1px solid #2e7d32; padding: 1.4mm 3mm; display: table; width: 100%;
         font-size: 5.5pt; }
  .bot .l { display: table-cell; }
  .bot .r { display: table-cell; text-align: right; }
  .sigline { display: inline-block; border-top: 0.5px solid #111; width: 26mm;
             font-size: 5pt; text-align: center; padding-top: 0.5mm; margin-top: 1mm; }
</style></head><body>
<div class="card">
  <div class="top">
    <div class="r">Republic of the Philippines &bull; {{ settings.city_municipality | default: '' }}</div>
    <div class="b">{{ settings.barangay_name | default: 'BARANGAY ID' | upcase }}</div>
  </div>
  <div class="mid">
    <div class="photo">1&times;1<br>PHOTO</div>
    <div class="info">
      <div class="nm">{{ last_name }}, {{ first_name }}{% if middle_name %} {{ middle_name | slice: 0 }}.{% endif %}{% if suffix %} {{ suffix }}{% endif %}</div>
      <div class="row"><b>Address:</b> {{ address_line | default: household.address_line }}{% if purok.name %}, {{ purok.name }}{% endif %}</div>
      <div class="row"><b>Birthdate:</b> {{ birthdate | date: '%m/%d/%Y' }} &nbsp;
        <b>Sex:</b> {{ sex | capitalize }} &nbsp; <b>Resident since:</b> {{ residency_start | date: '%Y' }}</div>
      <div class="row"><b>ID No.:</b> {{ id }} &nbsp; {% if registered_voter %}<b>VOTER</b>{% endif %}</div>
      <div class="tags">
        {% assign tags = sector_tags | split: ',' %}
        {% for t in tags %}<span class="tag">{{ t | replace: '[', '' | replace: ']', '' | replace: '"', '' | replace: '_', ' ' }}</span>{% endfor %}
      </div>
    </div>
  </div>
  <div class="bot">
    <div class="l">Emergency: {{ emergency_contact_name | default: '—' }}
      {{ emergency_contact_phone }}</div>
    <div class="r"><span class="sigline">&nbsp;<br>Signature</span></div>
  </div>
</div>
</body></html>
"""

ROSTER = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  @page { size: A4 landscape; margin: 14mm 15mm; }
  body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10.5px; color: #111; margin: 0; }
  .head { text-align: center; line-height: 1.3; }
  .brgy { font-size: 15px; font-weight: 700; }
  .title { text-align: center; font-size: 14px; font-weight: 700; letter-spacing: 2px; margin: 12px 0 10px; }
  table.grid { width: 100%; border-collapse: collapse; }
  table.grid td, table.grid th { border: 1px solid #999; padding: 3px 6px; font-size: 9.5px;
    text-align: left; vertical-align: top; }
  table.grid th { background: #eceff1; text-transform: uppercase; font-size: 8.5px; letter-spacing: .4px; }
  .foot { margin-top: 14px; font-size: 10px; }
  .sig { margin-top: 40px; width: 220px; text-align: center; }
  .sig .name { font-weight: 700; text-transform: uppercase; }
  .sig .lbl { font-size: 9px; border-top: 1px solid #111; padding-top: 2px; }
</style></head><body>

<div class="head">
  <div>Republic of the Philippines</div>
  <div>{{ settings.city_municipality | default: '__________' }}</div>
  <div class="brgy">{{ settings.barangay_name | default: 'BARANGAY ______' | upcase }}</div>
</div>
<div class="title">CERTIFIED LIST OF RESIDENTS — {{ name | upcase }}</div>

<table class="grid">
  <tr><th style="width:26px">#</th><th>Name</th><th style="width:40px">Sex</th>
      <th style="width:80px">Birthdate</th><th style="width:150px">Household</th>
      <th style="width:90px">Role</th><th>Sectors</th></tr>
  {% for r in residents %}
  <tr>
    <td>{{ forloop.index }}</td>
    <td><b>{{ r.last_name }}</b>, {{ r.first_name }} {{ r.middle_name }}</td>
    <td>{{ r.sex | capitalize }}</td>
    <td>{{ r.birthdate | date: '%m/%d/%Y' }}</td>
    <td>{{ r.household.household_no | default: '—' }}</td>
    <td>{{ r.household_role | capitalize }}</td>
    <td>{{ r.sector_tags | replace: '[', '' | replace: ']', '' | replace: '"', '' | replace: '_', ' ' }}</td>
  </tr>
  {% endfor %}
</table>

<div class="foot"><b>Total residents:</b> {{ residents.size }}
  &nbsp;&nbsp; <b>Purok risk level:</b> {{ risk_level | upcase }}</div>

<div class="sig">
  <div style="font-size:9px">Certified correct:</div><br><br>
  <div class="name">{{ settings.secretary_name | default: '________________' }}</div>
  <div class="lbl">Barangay Secretary</div>
</div>

</body></html>
"""

POSTING = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  @page { size: A4; margin: 20mm; }
  body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; color: #111; margin: 0; }
  .head { text-align: center; border-bottom: 3px double #111; padding-bottom: 10px; }
  .brgy { font-size: 17px; font-weight: 700; letter-spacing: 1px; }
  .office { font-size: 11px; font-style: italic; }
  .cat { display: inline-block; margin-top: 8px; border: 1.5px solid #111; border-radius: 12px;
         padding: 2px 14px; font-size: 10px; font-weight: 700; letter-spacing: 2px;
         text-transform: uppercase; }
  .title { text-align: center; font-size: 24px; font-weight: 800; margin: 22px 0 6px; }
  .dates { text-align: center; font-size: 10.5px; color: #444; margin-bottom: 20px; }
  .body { font-size: 13.5px; line-height: 1.75; }
  .foot { margin-top: 34px; font-size: 10px; color: #444; border-top: 1px solid #999;
          padding-top: 6px; }
</style></head><body>

<div class="head">
  <div>Republic of the Philippines</div>
  <div class="brgy">{{ settings.barangay_name | default: 'BARANGAY ______' | upcase }}</div>
  <div class="office">Office of the Punong Barangay &bull; {{ settings.contact_number }}</div>
  <div class="cat">{{ category | default: 'ANNOUNCEMENT' }}</div>
</div>

<div class="title">{{ title }}</div>
<div class="dates">Posted {{ publish_at | date: '%B %e, %Y' }}
  {% if expires_at %} &bull; Effective until {{ expires_at | date: '%B %e, %Y' }}{% endif %}</div>

<div class="body">{{ body }}</div>

<div class="foot">For inquiries, visit the Barangay Hall during office hours (8AM–5PM, Mon–Fri)
  or call {{ settings.contact_number | default: 'the barangay hotline' }}.</div>

</body></html>
"""

KP_SETTLEMENT = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  @page { size: A4; margin: 16mm 18mm; }
  body { font-family: 'Times New Roman', Times, serif; font-size: 13px; margin: 0; }
  .head { text-align: center; line-height: 1.35; }
  .brgy { font-size: 16px; font-weight: 700; letter-spacing: 1px; }
  .office { font-size: 11px; font-style: italic; }
  .rule { border: 0; border-top: 2.5px solid #111; margin: 8px 0 2px; }
  .rule2 { border: 0; border-top: 1px solid #111; margin: 0 0 14px; }
  .kp { font-size: 10px; letter-spacing: 2px; text-align: center; color: #444; }
  .form { text-align: right; font-size: 9.5px; color: #555; }
  .title { text-align: center; font-size: 16px; font-weight: 700; letter-spacing: 1.5px; margin: 14px 0; }
  .vs { width: 100%; margin: 8px 0 14px; font-size: 13px; }
  .vs td { padding: 2px 4px; }
  .body { text-align: justify; line-height: 1.7; }
  .body p { margin: 10px 0; text-indent: 40px; }
  .terms { border: 1px solid #999; padding: 10px 14px; margin: 12px 0; line-height: 1.6; }
  .sig { margin-top: 46px; width: 100%; }
  .sig .cell { display: inline-block; width: 49%; text-align: center; vertical-align: top; }
  .sig .name { font-weight: 700; text-transform: uppercase; }
  .sig .lbl { font-size: 10.5px; border-top: 1px solid #111; width: 70%; margin: 0 auto; padding-top: 2px; }
</style></head><body>
<div class="form">KP Form No. 16</div>
<div class="head">
  <div>Republic of the Philippines</div>
  <div>{{ settings.city_municipality | default: '__________' }}</div>
  <div class="brgy">{{ settings.barangay_name | default: 'BARANGAY ______' | upcase }}</div>
  <div class="office">Office of the Lupong Tagapamayapa</div>
</div>
<hr class="rule"><hr class="rule2">
<div class="kp">KATARUNGANG PAMBARANGAY</div>
<div class="title">AMICABLE SETTLEMENT / KASUNDUAN NG PAG-AAYOS</div>

<table class="vs">
  <tr><td><b>Complainant:</b> {% if complainant %}{{ complainant.first_name }} {{ complainant.last_name }}{% else %}{{ complainant_name }}{% endif %}</td>
      <td rowspan="2" style="width:40px;text-align:center">— vs —</td></tr>
  <tr><td><b>Respondent:</b> {% if respondent %}{{ respondent.first_name }} {{ respondent.last_name }}{% else %}{{ respondent_name }}{% endif %}</td></tr>
</table>
<p style="font-size:12px">KP Case No. <b>{{ case_no }}</b> &bull; Nature: {{ case_type | replace: '_', ' ' | capitalize }} &bull; Filed {{ date_filed | date: '%B %e, %Y' }}</p>

<div class="body">
  <p>After hearing the testimonies and evidence presented by both parties, the parties
  have freely and voluntarily agreed to settle their dispute on the following terms:</p>
</div>
<div class="terms">{{ settlement_details | default: '—' | newline_to_br }}</div>
<div class="body">
  <p>Both parties undertake to comply in good faith with the above terms. This settlement
  shall have the force and effect of a final judgment after the lapse of ten (10) days
  from this date unless repudiated in accordance with law.</p>
  <p>Entered into this <b>{{ settled_at | date: '%e day of %B, %Y' }}</b> at
  {{ settings.barangay_name }}, {{ settings.city_municipality }}.</p>
</div>

<div class="sig">
  <div class="cell"><br><br>
    <div class="name">{% if complainant %}{{ complainant.first_name }} {{ complainant.last_name }}{% else %}{{ complainant_name | default: '________' }}{% endif %}</div>
    <div class="lbl">Complainant</div></div>
  <div class="cell"><br><br>
    <div class="name">{% if respondent %}{{ respondent.first_name }} {{ respondent.last_name }}{% else %}{{ respondent_name | default: '________' }}{% endif %}</div>
    <div class="lbl">Respondent</div></div>
</div>
<div class="sig" style="margin-top:34px">
  <div class="cell"><div style="font-size:10px">Attested by:</div><br><br>
    <div class="name">{{ lupon_member.name | default: '________________' }}</div>
    <div class="lbl">Pangkat Chairman / Lupon Member</div></div>
  <div class="cell"><div style="font-size:10px">Approved by:</div><br><br>
    <div class="name">{{ settings.punong_barangay | default: '________________' }}</div>
    <div class="lbl">Punong Barangay / Lupon Chairman</div></div>
</div>
</body></html>
"""

KP_CFA = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  @page { size: A4; margin: 16mm 18mm; }
  body { font-family: 'Times New Roman', Times, serif; font-size: 13px; margin: 0; }
  .head { text-align: center; line-height: 1.35; }
  .brgy { font-size: 16px; font-weight: 700; letter-spacing: 1px; }
  .office { font-size: 11px; font-style: italic; }
  .rule { border: 0; border-top: 2.5px solid #111; margin: 8px 0 2px; }
  .rule2 { border: 0; border-top: 1px solid #111; margin: 0 0 14px; }
  .kp { font-size: 10px; letter-spacing: 2px; text-align: center; color: #444; }
  .form { text-align: right; font-size: 9.5px; color: #555; }
  .title { text-align: center; font-size: 16px; font-weight: 700; letter-spacing: 1.5px; margin: 14px 0; }
  .body { text-align: justify; line-height: 1.7; }
  .body p { margin: 10px 0; text-indent: 40px; }
  .sig { margin-top: 60px; }
  .sig .name { font-weight: 700; text-transform: uppercase; }
  .sig .lbl { font-size: 10.5px; border-top: 1px solid #111; width: 250px; padding-top: 2px; }
</style></head><body>
<div class="form">KP Form No. 18</div>
<div class="head">
  <div>Republic of the Philippines</div>
  <div>{{ settings.city_municipality | default: '__________' }}</div>
  <div class="brgy">{{ settings.barangay_name | default: 'BARANGAY ______' | upcase }}</div>
  <div class="office">Office of the Lupong Tagapamayapa</div>
</div>
<hr class="rule"><hr class="rule2">
<div class="kp">KATARUNGANG PAMBARANGAY</div>
<div class="title">CERTIFICATION TO FILE ACTION</div>

<div class="body">
  <p>This is to certify that:</p>
  <p style="text-indent:0">1. There was a personal confrontation between the
  complainant, <b>{% if complainant %}{{ complainant.first_name }} {{ complainant.last_name }}{% else %}{{ complainant_name }}{% endif %}</b>,
  and the respondent, <b>{% if respondent %}{{ respondent.first_name }} {{ respondent.last_name }}{% else %}{{ respondent_name }}{% endif %}</b>,
  in the presence of the Punong Barangay / Pangkat ng Tagapagkasundo;</p>
  <p style="text-indent:0">2. Despite earnest efforts at mediation and conciliation
  under KP Case No. <b>{{ case_no }}</b> ({{ case_type | replace: '_', ' ' | capitalize }},
  filed {{ date_filed | date: '%B %e, %Y' }}), no amicable settlement was reached;</p>
  <p style="text-indent:0">3. {% if cfa_reason %}{{ cfa_reason }}{% else %}The respondent
  failed to appear despite due notice, or the parties could not agree on a settlement.{% endif %}</p>
  <p>WHEREFORE, the complainant is hereby permitted to file the corresponding action
  in the appropriate court or office.</p>
  <p>Issued this <b>{{ cfa_issued_at | default: date_updated | date: '%e day of %B, %Y' }}</b>
  at {{ settings.barangay_name }}, {{ settings.city_municipality }}.</p>
</div>

<div class="sig"><br><br>
  <div class="name">{{ lupon_member.name | default: settings.punong_barangay | default: '________________' }}</div>
  <div class="lbl">Lupon/Pangkat Chairman</div>
</div>
</body></html>
"""


# ============================ BUILD ============================

def build():
    print("== settings M2O on all printables ==")
    s, d = req("GET", "/items/bis_settings?fields=id", quiet=True)
    settings_id = (d.get("data") or {}).get("id")
    for col in PRINTABLES:
        ensure_field(col, {"field": "settings", "type": "uuid", "schema": {},
                           "meta": {"interface": "select-dropdown-m2o", "hidden": True,
                                    "readonly": True, "width": "half",
                                    "note": "Auto-stamped w/ the bis_settings singleton (letterhead)"}})
        ensure_relation(col, "settings", "bis_settings")
        s, d = req("GET",
                   f"/items/{col}?filter%5Bsettings%5D%5B_null%5D=true&fields=id&limit=-1",
                   quiet=True)
        n = 0
        for row in (d.get("data") or []):
            req("PATCH", f"/items/{col}/{row['id']}", {"settings": settings_id})
            n += 1
        print(f"  {col}: settings field+rel ok, backfilled {n}")

    print("== extend bis_stamp_settings scope ==")
    s, d = req("GET", "/flows?filter%5Bname%5D%5B_eq%5D=bis_stamp_settings&limit=1", quiet=True)
    fl = (d.get("data") or [None])[0]
    if fl:
        opts = dict(fl.get("options") or {})
        opts["collections"] = PRINTABLES
        req("PATCH", f"/flows/{fl['id']}", {"options": opts})
        print("  = flow scope ->", PRINTABLES)

    print("== templates ==")
    t_permit = ensure_template("bis_business_permit", PERMIT)
    t_id = ensure_template("bis_barangay_id", BARANGAY_ID)
    t_roster = ensure_template("bis_purok_roster", ROSTER)
    t_post = ensure_template("bis_posting", POSTING)
    t_settle = ensure_template("bis_kp_amicable_settlement", KP_SETTLEMENT)
    t_cfa = ensure_template("bis_kp_cert_to_file_action", KP_CFA)

    print("== refresh existing templates (settings letterhead) ==")
    s, d = req("GET", "/items/print_template?filter%5Bname%5D%5B_eq%5D=bis_blotter_extract&fields=id,code",
               quiet=True)
    if d.get("data"):
        code = d["data"][0]["code"].replace(
            '{{ blotter_no | default: \'BARANGAY\' | upcase }} — BLOTTER EXTRACT',
            '{{ settings.barangay_name | default: "BARANGAY" | upcase }} — BLOTTER EXTRACT')
        req("PATCH", f"/items/print_template/{d['data'][0]['id']}", {"code": code})
        print("  = blotter_extract letterhead")
    s, d = req("GET", "/items/print_template?filter%5Bname%5D%5B_eq%5D=bis_kp_hearing_notice&fields=id,code",
               quiet=True)
    if d.get("data"):
        code = d["data"][0]["code"].replace(
            '{{ complainant.purok.name | default: \'BARANGAY\' | upcase }}',
            '{{ settings.barangay_name | default: "BARANGAY" | upcase }}')
        req("PATCH", f"/items/print_template/{d['data'][0]['id']}", {"code": code})
        print("  = kp_hearing_notice letterhead")

    print("== print fields ==")
    if t_permit:
        print_field("bis_business_permits", "print", None, t_permit)
    if t_id:
        print_field("bis_residents", "print", "grp_records", t_id)
    if t_roster:
        print_field("bis_puroks", "print", None, t_roster)
    if t_post:
        print_field("bis_announcements", "print", None, t_post)
    if t_settle:
        print_field("bis_kp_cases", "print_settlement", "grp_resolution", t_settle)
    if t_cfa:
        print_field("bis_kp_cases", "print_cfa", "grp_resolution", t_cfa)

    print("done.")


if __name__ == "__main__":
    build()
