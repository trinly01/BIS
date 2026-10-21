"""BIS Phase 4 — resident portal backend.

Public webhook flows (accountability: all, no auth) modeled on easypc's
tracker pattern: client POSTs/GETs hit /flows/trigger/{id}; an exec
"validate" op sanitizes+escapes input, likha_sql does the DB work, and a
final exec "respond" op returns a sanitized payload only. Direct
collection access stays denied to public.

Flows:
  bis_portal_options  GET  — doc types + fees/sla for the request form
  bis_portal_request  POST — find-or-create resident, stamp DOC- serial,
                             due_date (sla_days), fee, settings -> create
                             request row via raw INSERT (bypasses the
                             event-driven serial/SLA flows -> no
                             double-stamp)
  bis_portal_track    POST — status lookup by request_no + mobile (shared
                             secret, same idea as easypc WO + mobile)
  bis_verify_doc      GET  — ?serial= -> validity check for QR codes on
                             printed certificates (released docs only,
                             masked holder name)

Also adds bis_document_requests.portal_mobile (Request tab) — the
submitter's mobile, used as the tracking shared-secret even when the
linked resident's contact_number differs.
"""
import os, json, urllib.request

BASE = os.environ.get("DIRECTUS_URL", "https://likha-playground.zyberlab.com")
TOKEN = os.environ["DIRECTUS_TOKEN"]
UA = {"User-Agent": "curl/8.5.0", "Authorization": f"Bearer {TOKEN}",
      "Content-Type": "application/json"}


def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method,
                               data=json.dumps(body).encode() if body is not None else None,
                               headers=UA)
    try:
        with urllib.request.urlopen(r) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def ensure_field(collection, field, spec):
    s, d = req("GET", f"/fields/{collection}?limit=-1")
    if any(f["field"] == field for f in d.get("data", [])):
        print(f"  = field {collection}.{field}")
        return
    s, d = req("POST", f"/fields/{collection}", spec)
    print(f"  + field {collection}.{field}" if s < 300 else f"  !! field {collection}.{field}: {d}")


def get_flow(name):
    s, d = req("GET", f"/flows?filter%5Bname%5D%5B_eq%5D={name}&fields=id")
    return (d.get("data") or [{}])[0].get("id")


def build_flow(name, trigger_opts, ops):
    """ops: list of dicts {key,name,type,options,reject?} in chain order."""
    fid = get_flow(name)
    if fid:
        s, d = req("DELETE", f"/flows/{fid}")
        print(f"  - rebuilt flow {name}")
    s, d = req("POST", "/flows", {
        "name": name, "icon": "public", "color": None,
        "trigger": "webhook", "accountability": "all",
        "options": trigger_opts})
    fid = d["data"]["id"]
    ids = []
    for spec in reversed(ops):
        body = {"flow": fid, "name": spec["name"], "key": spec["key"],
                "type": spec["type"], "position_x": 19, "position_y": 1,
                "options": spec["options"]}
        if ids:
            body["resolve"] = ids[0]
        if spec.get("reject_to"):
            body["reject"] = spec["reject_to"]
        s, d = req("POST", "/operations", body)
        ids.insert(0, d["data"]["id"])
    req("PATCH", f"/flows/{fid}", {"operation": ids[0]})
    print(f"  + flow {name} ({fid})")
    return fid


def ex(code):
    return {"type": "exec", "options": {"code": code}}


# ---------- op snippets ----------

VALIDATE_REQUEST = """module.exports = async function(data){
  const b = (data.$trigger && data.$trigger.body) || {};
  const req = ['first_name','last_name','mobile','document_type','purpose'];
  for (const k of req) if (!b[k] || !String(b[k]).trim()) throw new Error('Missing: ' + k);
  let mob = String(b.mobile).replace(/\\D/g,'');
  if (mob.startsWith('63')) mob = '0' + mob.slice(2);
  if (!/^0\\d{10}$/.test(mob)) throw new Error('Invalid mobile number (use 09xxxxxxxxx)');
  if (!/^[0-9a-fA-F-]{36}$/.test(String(b.document_type))) throw new Error('Invalid document type');
  if (String(b.purpose).length > 500) throw new Error('Purpose too long');
  const q = s => String(s || '').trim().replace(/'/g, "''").slice(0,120);
  return { fn: q(b.first_name), ln: q(b.last_name), mn: q(b.middle_name),
    mobile: mob, doc: String(b.document_type).trim(), purpose: q(b.purpose) };
}"""

# One CTE: find-or-create resident, compute next DOC serial, fetch doc
# type fee/sla, settings id, then INSERT the request row. Raw SQL insert
# emits no items.create event, so bis_serial_doc / bis_stamp_sla do not
# double-stamp.
SQL_MKREQ = """WITH res AS (
  SELECT id FROM bis_residents
  WHERE contact_number = '{{validate.mobile}}'
     OR (lower(first_name) = lower('{{validate.fn}}') AND lower(last_name) = lower('{{validate.ln}}'))
  LIMIT 1
), newres AS (
  INSERT INTO bis_residents (id, first_name, last_name, middle_name, contact_number, residency_status)
  SELECT gen_random_uuid(), '{{validate.fn}}', '{{validate.ln}}', NULLIF('{{validate.mn}}',''),
         '{{validate.mobile}}', 'active'
  WHERE NOT EXISTS (SELECT 1 FROM res) RETURNING id
), r AS (SELECT id FROM res UNION ALL SELECT id FROM newres LIMIT 1),
d AS (SELECT id, fee, COALESCE(sla_days,3) sla FROM bis_document_types WHERE id = '{{validate.doc}}'::uuid),
s AS (SELECT (COALESCE(MAX(regexp_replace(request_no,'^.*-','')::int),0)+1) n
      FROM bis_document_requests WHERE request_no LIKE 'DOC-'||to_char(now(),'YYYY')||'-%'),
st AS (SELECT id FROM bis_settings LIMIT 1),
ins AS (
  INSERT INTO bis_document_requests
    (id, resident, document_type, purpose, status, portal_mobile, request_no, due_date, fee, settings, date_requested)
  SELECT gen_random_uuid(), r.id, d.id, '{{validate.purpose}}', 'received', '{{validate.mobile}}',
         'DOC-'||to_char(now(),'YYYY')||'-'||lpad(s.n::text,4,'0'),
         CURRENT_DATE + d.sla, d.fee, st.id, now()
  FROM r, d, s, st RETURNING request_no, due_date
)
SELECT i.request_no, to_char(i.due_date,'YYYY-MM-DD') AS due_date,
       d.id AS doc_id, (SELECT name FROM bis_document_types WHERE id = d.id) AS doc_name,
       d.fee FROM ins i, d"""

RESPOND_REQUEST = """module.exports = async function(data){
  const rows = (data.mkreq && data.mkreq.rows) || [];
  if (!rows.length) throw new Error('Unknown document type');
  const r = rows[0];
  return { ok: true, request_no: r.request_no, status: 'received',
    document_type: r.doc_name, fee: r.fee, eta: r.due_date,
    track_hint: 'Track anytime with your request number and mobile number.' };
}"""

VALIDATE_TRACK = """module.exports = async function(data){
  const b = (data.$trigger && data.$trigger.body) || {};
  if (!b.ref || !String(b.ref).trim()) throw new Error('Missing: ref');
  if (!b.key || !String(b.key).trim()) throw new Error('Missing: key');
  let mob = String(b.key).replace(/\\D/g,'');
  if (mob.startsWith('63')) mob = '0' + mob.slice(2);
  const q = s => String(s || '').trim().replace(/'/g, "''").slice(0,60);
  return { ref: q(b.ref).toUpperCase(), mobile: q(mob) };
}"""

SQL_TRACK = """SELECT r.request_no, r.status, r.serial_no, r.or_number,
  to_char(r.date_requested,'YYYY-MM-DD') AS requested,
  to_char(r.due_date,'YYYY-MM-DD') AS due_date,
  to_char(r.issued_date,'YYYY-MM-DD') AS issued,
  to_char(r.valid_until,'YYYY-MM-DD') AS valid_until,
  r.fee, r.amount_paid, r.released_to,
  t.name AS doc_name
FROM bis_document_requests r
LEFT JOIN bis_document_types t ON t.id = r.document_type
LEFT JOIN bis_residents res ON res.id = r.resident
WHERE (upper(r.request_no) = '{{validate.ref}}' OR upper(r.serial_no) = '{{validate.ref}}'
       OR upper(r.or_number) = '{{validate.ref}}')
  AND (r.portal_mobile = '{{validate.mobile}}' OR res.contact_number = '{{validate.mobile}}')
LIMIT 1"""

RESPOND_TRACK = """module.exports = async function(data){
  const rows = (data.lookup && data.lookup.rows) || [];
  if (!rows.length) throw new Error('No matching request. Check the request number and mobile.');
  const r = rows[0];
  return { found: true, request: {
    request_no: r.request_no, status: r.status, document_type: r.doc_name,
    requested: r.requested, due_date: r.due_date, issued: r.issued,
    valid_until: r.valid_until, serial_no: r.serial_no, or_number: r.or_number,
    fee: r.fee, amount_paid: r.amount_paid, released_to: r.released_to } };
}"""

VALIDATE_VERIFY = """module.exports = async function(data){
  const q = ((data.$trigger && data.$trigger.query) || {});
  const s = String(q.serial || q.ref || '').trim().replace(/'/g, "''").slice(0,60);
  if (!s) throw new Error('Missing serial');
  return { s: s.toUpperCase() };
}"""

# UNION: doc requests (released) + business permits (not revoked) — QR
# codes on both printed documents resolve here.
SQL_VERIFY = """SELECT r.request_no, r.serial_no, r.status,
  to_char(r.issued_date,'YYYY-MM-DD') AS issued,
  to_char(r.valid_until,'YYYY-MM-DD') AS valid_until,
  t.name AS doc_name,
  res.first_name || ' ' || left(res.last_name,1) || '.' AS holder
FROM bis_document_requests r
LEFT JOIN bis_document_types t ON t.id = r.document_type
LEFT JOIN bis_residents res ON res.id = r.resident
WHERE (upper(r.serial_no) = '{{validate.s}}' OR upper(r.request_no) = '{{validate.s}}')
  AND r.status = 'released'
UNION ALL
SELECT p.permit_no, p.permit_no, p.status,
  to_char(p.date_issued,'YYYY-MM-DD'), to_char(p.valid_until,'YYYY-MM-DD'),
  'Barangay Business Clearance', p.business_name
FROM bis_business_permits p
WHERE upper(p.permit_no) = '{{validate.s}}' AND p.status <> 'revoked'
LIMIT 1"""

RESPOND_VERIFY = """module.exports = async function(data){
  const rows = (data.lookup && data.lookup.rows) || [];
  if (!rows.length) return { valid: false };
  const r = rows[0];
  const today = new Date().toISOString().slice(0,10);
  const expired = (r.valid_until && r.valid_until < today) || r.status === 'expired';
  return { valid: !expired, expired: !!expired,
    document_type: r.doc_name, serial_no: r.serial_no || r.request_no,
    request_no: r.request_no, issued: r.issued, valid_until: r.valid_until,
    holder: r.holder };
}"""

SQL_OPTIONS = """SELECT id, name, fee, sla_days, validity_days
FROM bis_document_types WHERE status = 'active' ORDER BY name"""

RESPOND_OPTIONS = """module.exports = async function(data){
  const rows = (data.sql_1 && data.sql_1.rows) || [];
  return { types: rows.map(r => ({ id: r.id, name: r.name, fee: r.fee,
    sla_days: r.sla_days, validity_days: r.validity_days })) };
}"""


def main():
    print("== portal_mobile field")
    ensure_field("bis_document_requests", "portal_mobile", {
        "field": "portal_mobile", "type": "string",
        "meta": {"interface": "input", "group": "grp_request",
                 "note": "Mobile number submitted via resident portal — tracking key"}})

    print("== portal flows")
    ids = {}
    ids["options"] = build_flow("bis_portal_options", {"method": "GET", "async": False}, [
        {"key": "sql_1", "name": "doc types", "type": "likha_sql",
         "options": {"sql": SQL_OPTIONS}},
        {"key": "respond", "name": "respond", "type": "exec",
         "options": {"code": RESPOND_OPTIONS}},
    ])
    ids["request"] = build_flow("bis_portal_request", {"method": "POST", "async": False}, [
        {"key": "validate", "name": "validate", "type": "exec",
         "options": {"code": VALIDATE_REQUEST}},
        {"key": "mkreq", "name": "mkreq", "type": "likha_sql",
         "options": {"sql": SQL_MKREQ}},
        {"key": "respond", "name": "respond", "type": "exec",
         "options": {"code": RESPOND_REQUEST}},
    ])
    ids["track"] = build_flow("bis_portal_track", {"method": "POST", "async": False}, [
        {"key": "validate", "name": "validate", "type": "exec",
         "options": {"code": VALIDATE_TRACK}},
        {"key": "lookup", "name": "lookup", "type": "likha_sql",
         "options": {"sql": SQL_TRACK}},
        {"key": "respond", "name": "respond", "type": "exec",
         "options": {"code": RESPOND_TRACK}},
    ])
    ids["verify"] = build_flow("bis_verify_doc", {"method": "GET", "async": False}, [
        {"key": "validate", "name": "validate", "type": "exec",
         "options": {"code": VALIDATE_VERIFY}},
        {"key": "lookup", "name": "lookup", "type": "likha_sql",
         "options": {"sql": SQL_VERIFY}},
        {"key": "respond", "name": "respond", "type": "exec",
         "options": {"code": RESPOND_VERIFY}},
    ])
    print("\nFLOW_IDS = " + json.dumps(ids, indent=2))


if __name__ == "__main__":
    main()
