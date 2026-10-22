import os, json, urllib.request
BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ["DIRECTUS_TOKEN"]
UA = {"User-Agent": "curl/8.5.0", "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
def req(m, p, b=None):
    r = urllib.request.Request(BASE + p, method=m, data=json.dumps(b).encode() if b else None, headers=UA)
    try:
        with urllib.request.urlopen(r) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

def get_flow(n):
    s, d = req("GET", f"/flows?filter%5Bname%5D%5B_eq%5D={n}&fields=id")
    return (d.get("data") or [{}])[0].get("id")

fid = get_flow("bis_portal_options")
s, d = req("GET", f"/operations?filter%5Bflow%5D%5B_eq%5D={fid}&fields=id,key,resolve")
ops = d["data"]
op = {o["key"]: o["id"] for o in ops}
print("ops:", [(o["key"], o["resolve"]) for o in ops])
# check if brgys already exists
if "brgys" not in op:
    # unlink sql_1 -> respond first (resolve must be unique)
    req("PATCH", f"/operations/{op['sql_1']}", {"resolve": None})
    s, d = req("POST", "/operations", {"flow": fid, "name": "brgys", "key": "brgys",
        "type": "likha_sql", "position_x": 19, "position_y": 1,
        "resolve": op["respond"],
        "options": {"sql": "SELECT id, name, code, municipality FROM bis_barangays ORDER BY name"}})
    brgys = d["data"]["id"]
    req("PATCH", f"/operations/{op['sql_1']}", {"resolve": brgys})
    print("inserted brgys op")

# ensure sql_1 + respond options are the barangay-aware versions
req("PATCH", f"/operations/{op['sql_1']}", {"options": {"sql":
    "SELECT id, name, fee, sla_days, validity_days FROM bis_document_types WHERE status='active' ORDER BY name"}})
req("PATCH", f"/operations/{op['respond']}", {"options": {"code":
    "module.exports = async function(data){"
    "  const types = (data.sql_1 && data.sql_1.rows) || [];"
    "  const brgys = (data.brgys && data.brgys.rows) || [];"
    "  return { types: types.map(r => ({ id: r.id, name: r.name, fee: r.fee,"
    "    sla_days: r.sla_days, validity_days: r.validity_days })),"
    "    barangays: brgys };"
    "}"}})

fid = get_flow("bis_portal_request")
s, d = req("GET", f"/operations?filter%5Bflow%5D%5B_eq%5D={fid}&fields=id,key")
op = {o["key"]: o["id"] for o in d["data"]}
req("PATCH", f"/operations/{op['validate']}", {"options": {"code": (
    "module.exports = async function(data){\n"
    "  const b = (data.$trigger && data.$trigger.body) || {};\n"
    "  const req = ['first_name','last_name','mobile','document_type','purpose','barangay'];\n"
    "  for (const k of req) if (!b[k] || !String(b[k]).trim()) throw new Error('Missing: ' + k);\n"
    "  let mob = String(b.mobile).replace(/\D/g,'');\n"
    "  if (mob.startsWith('63')) mob = '0' + mob.slice(2);\n"
    "  if (!/^0\d{10}$/.test(mob)) throw new Error('Invalid mobile number (use 09xxxxxxxxx)');\n"
    "  if (!/^[0-9a-fA-F-]{36}$/.test(String(b.document_type))) throw new Error('Invalid document type');\n"
    "  if (!/^[0-9a-fA-F-]{36}$/.test(String(b.barangay))) throw new Error('Invalid barangay');\n"
    "  if (String(b.purpose).length > 500) throw new Error('Purpose too long');\n"
    "  const q = s => String(s || '').trim().replace(/'/g, \"''\").slice(0,120);\n"
    "  return { fn: q(b.first_name), ln: q(b.last_name), mn: q(b.middle_name),\n"
    "    mobile: mob, doc: String(b.document_type).trim(), brgy: String(b.barangay).trim(),\n"
    "    purpose: q(b.purpose) };\n"
    "}")}})
req("PATCH", f"/operations/{op['mkreq']}", {"options": {"sql": (
    "WITH res AS (\n"
    "  SELECT id FROM bis_residents\n"
    "  WHERE contact_number = '{{validate.mobile}}'\n"
    "     OR (lower(first_name) = lower('{{validate.fn}}') AND lower(last_name) = lower('{{validate.ln}}'))\n"
    "  LIMIT 1\n"
    "), newres AS (\n"
    "  INSERT INTO bis_residents (id, first_name, last_name, middle_name, contact_number, residency_status, barangay)\n"
    "  SELECT gen_random_uuid(), '{{validate.fn}}', '{{validate.ln}}', NULLIF('{{validate.mn}}',''),\n"
    "         '{{validate.mobile}}', 'active', '{{validate.brgy}}'::uuid\n"
    "  WHERE NOT EXISTS (SELECT 1 FROM res) RETURNING id\n"
    "), r AS (SELECT id FROM res UNION ALL SELECT id FROM newres LIMIT 1),\n"
    "b AS (SELECT id, code FROM bis_barangays WHERE id = '{{validate.brgy}}'::uuid),\n"
    "d AS (SELECT id, fee, COALESCE(sla_days,3) sla FROM bis_document_types WHERE id = '{{validate.doc}}'::uuid),\n"
    "s AS (SELECT (COALESCE(MAX(regexp_replace(request_no,'^.*-','')::int),0)+1) n\n"
    "      FROM bis_document_requests WHERE barangay = '{{validate.brgy}}'::uuid\n"
    "      AND request_no LIKE 'DOC-'||(SELECT code FROM b)||'-'||to_char(now(),'YYYY')||'-%'),\n"
    "st AS (SELECT id FROM bis_settings WHERE barangay = '{{validate.brgy}}'::uuid LIMIT 1),\n"
    "ins AS (\n"
    "  INSERT INTO bis_document_requests\n"
    "    (id, resident, document_type, purpose, status, portal_mobile, request_no, due_date, fee, settings, barangay, date_requested)\n"
    "  SELECT gen_random_uuid(), r.id, d.id, '{{validate.purpose}}', 'received', '{{validate.mobile}}',\n"
    "         'DOC-'||b.code||'-'||to_char(now(),'YYYY')||'-'||lpad(s.n::text,4,'0'),\n"
    "         CURRENT_DATE + d.sla, d.fee, st.id, b.id, now()\n"
    "  FROM r, d, s, st, b RETURNING request_no, due_date\n"
    ")\n"
    "SELECT i.request_no, to_char(i.due_date,'YYYY-MM-DD') AS due_date,\n"
    "       (SELECT name FROM bis_document_types WHERE id = d.id) AS doc_name,\n"
    "       d.fee FROM ins i, d")}})
print("portal flows updated")
req("POST", "/utils/cache/clear", {"cache": "system"})
