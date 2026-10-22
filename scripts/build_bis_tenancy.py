"""BIS Phase 5 — multi-barangay tenancy.

Design (confirmed):
- New `bis_barangays` = tenant root (letterhead fields live here too via a
  per-barangay `bis_settings` row — see below).
- `barangay` M2O -> bis_barangays on 9 entity collections + bis_settings.
- `bis_settings` converted singleton -> collection: ONE ROW PER BARANGAY
  (`barangay` M2O). Print templates keep `settings.*` — the stamp flow now
  resolves the settings row matching the record's barangay. Zero template
  churn.
- `directus_users.bis_barangay` M2O; role permission filters
  {barangay: {_eq: $CURRENT_USER.bis_barangay}} + create presets — same
  pattern as easypc multi-branch (easypc_store). Junction collections
  (blotter_parties/attachments, kp_hearings) filter via their parent M2O.
- New `bis_admin` role = municipal tier: unfiltered full access.
- Serials embed the barangay code: DOC-POB-2026-0001, per-barangay counter.
- Portal: options flow returns barangay list; request flow takes barangay id.
"""
import os, json, urllib.request

BASE = os.environ.get("DIRECTUS_URL", "https://likha-playground.zyberlab.com")
TOKEN = os.environ["DIRECTUS_TOKEN"]
UA = {"User-Agent": "curl/8.5.0", "Authorization": f"Bearer {TOKEN}",
      "Content-Type": "application/json"}

ENTITIES = ["bis_residents", "bis_households", "bis_document_requests",
            "bis_blotter", "bis_kp_cases", "bis_business_permits",
            "bis_puroks", "bis_officials", "bis_announcements"]

# junction collection -> parent M2O field (for nested permission filters)
JUNCTIONS = {"bis_blotter_parties": "blotter",
             "bis_blotter_attachments": "blotter",
             "bis_kp_hearings": "kp_case"}

ROLES = {"bis_staff": None, "bis_secretary": None, "bis_captain": None}


def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method,
                               data=json.dumps(body).encode() if body is not None else None,
                               headers=UA)
    try:
        with urllib.request.urlopen(r) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def sqlflow(sql):
    """Run raw SQL via a throwaway webhook flow + likha_sql op."""
    s, d = req("POST", "/flows", {"name": "tmp_sql_runner", "trigger": "webhook",
                                  "accountability": "all", "options": {"async": False}})
    fid = d["data"]["id"]
    s, d = req("POST", "/operations", {"flow": fid, "name": "q", "key": "sql_1",
                                       "type": "likha_sql", "position_x": 1, "position_y": 1,
                                       "options": {"sql": sql}})
    req("PATCH", f"/flows/{fid}", {"operation": d["data"]["id"]})
    s, out = req("GET", f"/flows/trigger/{fid}")
    req("DELETE", f"/flows/{fid}")
    return out


def get_flow(name):
    s, d = req("GET", f"/flows?filter%5Bname%5D%5B_eq%5D={name}&fields=id")
    return (d.get("data") or [{}])[0].get("id")


def build_flow(name, trigger_opts, ops, trigger="webhook", scope=None):
    fid = get_flow(name)
    if fid:
        req("DELETE", f"/flows/{fid}")
        print(f"  - rebuilt flow {name}")
    body = {"name": name, "icon": "bolt", "trigger": trigger,
            "accountability": "all", "options": trigger_opts}
    if scope:
        body["options"]["scope"] = scope
        body["options"]["type"] = "action"
    s, d = req("POST", "/flows", body)
    fid = d["data"]["id"]
    ids = []
    for spec in reversed(ops):
        body = {"flow": fid, "name": spec["name"], "key": spec["key"],
                "type": spec["type"], "position_x": 19, "position_y": 1,
                "options": spec["options"]}
        if ids:
            body["resolve"] = ids[0]
        s, d = req("POST", "/operations", body)
        ids.insert(0, d["data"]["id"])
    req("PATCH", f"/flows/{fid}", {"operation": ids[0]})
    print(f"  + flow {name}")
    return fid


def ensure_field(collection, field, spec):
    s, d = req("GET", f"/fields/{collection}?limit=-1")
    if any(f["field"] == field for f in d.get("data", [])):
        return False
    s, d = req("POST", f"/fields/{collection}", spec)
    if s >= 300:
        print(f"  !! field {collection}.{field}: {d}")
        return False
    return True


def barangay_m2o(collection, group=None):
    """Add `barangay` M2O + relation + display meta."""
    if ensure_field(collection, "barangay", {
            "field": "barangay", "type": "uuid",
            "meta": {"interface": "select-dropdown-m2o",
                     "display": "related-values",
                     "group": group,
                     "options": {"template": "{{name}}"},
                     "display_options": {"template": "{{name}}"}},
            "schema": {"foreign_key_table": "bis_barangays",
                       "foreign_key_column": "id"}}):
        print(f"  + {collection}.barangay")
    s, d = req("GET", f"/relations/{collection}/barangay")
    if s == 403 or s == 404 or not (d.get("data") or {}).get("collection"):
        s, d = req("POST", "/relations", {
            "collection": collection, "field": "barangay",
            "related_collection": "bis_barangays"})
        if s < 300:
            print(f"  + relation {collection}.barangay")


# ============================== build ==============================

def step_barangays():
    print("== bis_barangays collection")
    s, d = req("GET", "/collections/bis_barangays")
    if s == 403 or s == 404:
        s, d = req("POST", "/collections", {
            "collection": "bis_barangays", "meta": {"icon": "holiday_village",
            "group": "bis_master_data", "sort": 1,
            "display_template": "{{name}}, {{municipality}}"},
            "schema": {}, "fields": [
                {"field": "id", "type": "uuid", "meta": {"hidden": True, "special": ["uuid"], "interface": "input", "readonly": True},
                 "schema": {"is_primary_key": True, "has_auto_increment": False}},
                {"field": "name", "type": "string", "meta": {"interface": "input", "required": True}},
                {"field": "code", "type": "string", "meta": {"interface": "input", "required": True,
                     "note": "Serial prefix, e.g. POB -> DOC-POB-2026-0001"}},
                {"field": "municipality", "type": "string", "meta": {"interface": "input"}},
                {"field": "province", "type": "string", "meta": {"interface": "input"}},
                {"field": "region", "type": "string", "meta": {"interface": "input"}},
                {"field": "punong_barangay", "type": "string", "meta": {"interface": "input"}},
                {"field": "contact_number", "type": "string", "meta": {"interface": "input"}},
                {"field": "email", "type": "string", "meta": {"interface": "input"}},
                {"field": "location", "type": "json", "meta": {"interface": "map", "special": ["cast-geojson"], "options": {"defaultView": {"center": {"lng": 120.41, "lat": 16.13}, "zoom": 14}}}},
            ]})
        print("  + collection bis_barangays" if s < 300 else f"  !! {d}")

    # seed Poblacion (letterhead copied from singleton settings)
    s, d = req("GET", "/items/bis_barangays?filter%5Bcode%5D%5B_eq%5D=POB&fields=id")
    rows = d.get("data") or []
    if rows:
        pob = rows[0]["id"]
        print("  = Poblacion exists")
    else:
        s, st = req("GET", "/items/bis_settings?limit=1")
        st = (st.get("data") or [{}])
        st = st[0] if isinstance(st, list) and st else st
        s, d = req("POST", "/items/bis_barangays", {
            "name": st.get("barangay_name", "Barangay Poblacion"),
            "code": "POB",
            "municipality": st.get("city_municipality", "San Fabian"),
            "province": st.get("province", "Pangasinan"),
            "region": st.get("region", "Ilocos Region (Region I)"),
            "punong_barangay": st.get("punong_barangay"),
            "location": {"type": "Point", "coordinates": [120.41, 16.13]}})
        pob = d["data"]["id"]
        print(f"  + Poblacion barangay {pob}")
    return pob


def step_fields(pob):
    print("== barangay M2O on entities + settings + users")
    for c in ENTITIES:
        barangay_m2o(c)
    barangay_m2o("bis_settings")
    ensure_field("directus_users", "bis_barangay", {
        "field": "bis_barangay", "type": "uuid",
        "meta": {"interface": "select-dropdown-m2o", "special": None,
                 "options": {"template": "{{name}}"}},
        "schema": {"foreign_key_table": "bis_barangays", "foreign_key_column": "id"}})
    s, d = req("GET", "/relations/directus_users/bis_barangay")
    if s == 403 or s == 404:
        s, d = req("POST", "/relations", {
            "collection": "directus_users", "field": "bis_barangay",
            "related_collection": "bis_barangays"})
        print("  + directus_users.bis_barangay" if s < 300 else f"  !! users.barangay {d}")

    print("== backfill Poblacion")
    for c in ENTITIES + ["bis_settings"]:
        out = sqlflow(f"UPDATE {c} SET barangay='{pob}' WHERE barangay IS NULL")
        print(f"  backfilled {c}")


def step_settings():
    print("== bis_settings -> per-barangay collection")
    s, d = req("PATCH", "/collections/bis_settings", {
        "meta": {"singleton": False, "group": "bis_master_data",
                 "display_template": "{{barangay_name}} ({{barangay.name}})"}})
    print("  un-singletoned" if s < 300 else f"  !! {d}")
    # repoint stamp flow: dynamic collection via $trigger.collection
    print("== rebuild bis_stamp_settings")
    build_flow("bis_stamp_settings",
               {"type": "action", "async": True,
                "scope": ["items.create"]},
               [{"key": "stamp", "name": "stamp per-barangay settings",
                 "type": "likha_sql",
                 "options": {"sql": (
                     "UPDATE {{$trigger.collection}} t SET settings = "
                     "(SELECT s.id FROM bis_settings s WHERE s.barangay = t.barangay LIMIT 1) "
                     "WHERE t.id = '{{$trigger.key}}' AND t.barangay IS NOT NULL")}}],
               trigger="event",
               scope=["bis_document_requests", "bis_business_permits",
                      "bis_residents", "bis_kp_cases", "bis_blotter",
                      "bis_puroks", "bis_announcements"])


def step_serials():
    print("== rebuild serial flows (barangay-code embedded)")
    specs = [("bis_document_requests", "request_no", "DOC"),
             ("bis_blotter", "blotter_no", "BLT"),
             ("bis_kp_cases", "case_no", "KP"),
             ("bis_business_permits", "permit_no", "BP")]
    for coll, field, prefix in specs:
        sql = (
            f"WITH r AS (SELECT barangay FROM {coll} WHERE id='{{{{$trigger.key}}}}') "
            f"SELECT '{prefix}-'||COALESCE(b.code,'XX')||'-'||to_char(now(),'YYYY')||'-'||lpad("
            f"(COALESCE(MAX(regexp_replace(x.{field},'^.*-','')::int),0)+1)::text,4,'0') AS serial "
            f"FROM r LEFT JOIN bis_barangays b ON b.id = r.barangay "
            f"LEFT JOIN {coll} x ON x.barangay = r.barangay "
            f"AND x.{field} LIKE '{prefix}-'||b.code||'-'||to_char(now(),'YYYY')||'-%' "
            f"GROUP BY b.code")
        build_flow(f"bis_serial_{prefix.lower()}",
                   {"type": "action", "async": True, "scope": ["items.create"]},
                   [{"key": "sql_1", "name": "next serial", "type": "likha_sql",
                     "options": {"sql": sql}},
                    {"key": "stamp", "name": "stamp", "type": "item-update",
                     "options": {"collection": coll, "key": "{{$trigger.key}}",
                                 "payload": {field: "{{sql_1.rows.0.serial}}"},
                                 "emitEvents": False, "permissions": "$full"}}],
                   trigger="event", scope=[coll])


def step_roles():
    print("== scope role permissions to barangay")
    scope_filter = {"barangay": {"_eq": "$CURRENT_USER.bis_barangay"}}
    for role in ROLES:
        s, d = req("GET", f"/roles?filter%5Bname%5D%5B_eq%5D={role}&fields=id")
        rid = (d.get("data") or [{}])[0].get("id")
        if not rid:
            print(f"  !! role {role} missing"); continue
        s, d = req("GET", f"/policies?filter%5Bname%5D%5B_eq%5D={role}_policy&fields=id")
        pid = (d.get("data") or [{}])[0].get("id")
        s, d = req("GET", f"/permissions?filter%5Bpolicy%5D%5B_eq%5D={pid}&limit=-1&fields=id,collection,action,permissions,presets")
        n = 0
        for p in d.get("data", []):
            coll, act = p["collection"], p["action"]
            if coll in JUNCTIONS:
                f = {JUNCTIONS[coll]: scope_filter}
            elif coll in ENTITIES or coll == "bis_settings":
                f = scope_filter
            else:
                continue
            patch = {"permissions": f}
            if act == "create" and coll in ENTITIES:
                presets = dict(p.get("presets") or {})
                presets["barangay"] = "$CURRENT_USER.bis_barangay"
                patch["presets"] = presets
            req("PATCH", f"/permissions/{p['id']}", patch)
            n += 1
        print(f"  {role}: {n} perms scoped")

    print("== bis_admin (municipal tier)")
    s, d = req("GET", "/roles?filter%5Bname%5D%5B_eq%5D=bis_admin&fields=id")
    rid = (d.get("data") or [{}])[0].get("id")
    if not rid:
        s, d = req("POST", "/roles", {"name": "bis_admin", "icon": "location_city",
                                     "description": "Municipal admin — all barangays"})
        rid = d["data"]["id"]
    s, d = req("GET", "/policies?filter%5Bname%5D%5B_eq%5D=bis_admin_policy&fields=id")
    pid = (d.get("data") or [{}])[0].get("id")
    if not pid:
        s, d = req("POST", "/policies", {"name": "bis_admin_policy", "icon": "location_city",
                                         "admin_access": False, "app_access": True})
        pid = d["data"]["id"]
        req("POST", "/access", {"role": rid, "policy": pid})
    s, d = req("GET", f"/permissions?filter%5Bpolicy%5D%5B_eq%5D={pid}&fields=collection,action&limit=-1")
    have = {(p["collection"], p["action"]) for p in d.get("data", [])}
    all_colls = ENTITIES + list(JUNCTIONS) + ["bis_barangays", "bis_settings",
                                              "bis_document_types"]
    n = 0
    for coll in all_colls:
        for act in ["create", "read", "update", "delete"]:
            if (coll, act) not in have:
                req("POST", "/permissions", {
                    "policy": pid, "collection": coll, "action": act,
                    "fields": ["*"]})
                n += 1
    print(f"  bis_admin: +{n} perms")


def step_portal():
    print("== portal flows: barangay-aware")
    # options: add barangays
    fid = get_flow("bis_portal_options")
    s, d = req("GET", f"/operations?filter%5Bflow%5D%5B_eq%5D={fid}&fields=id,key")
    op = {o["key"]: o["id"] for o in d["data"]}
    req("PATCH", f"/operations/{op['sql_1']}", {"options": {"sql": (
        "SELECT id, name, fee, sla_days, validity_days, 'type' AS kind "
        "FROM bis_document_types WHERE status='active'") }})
    req("PATCH", f"/operations/{op['respond']}", {"options": {"code": (
        "module.exports = async function(data){"
        "  const types = (data.sql_1 && data.sql_1.rows) || [];"
        "  const brgys = (data.brgys && data.brgys.rows) || [];"
        "  return { types: types.map(r => ({ id: r.id, name: r.name, fee: r.fee,"
        "    sla_days: r.sla_days, validity_days: r.validity_days })),"
        "    barangays: brgys };"
        "}")}})
    # add a brgys op chained before respond
    s, d = req("GET", f"/operations/{op['sql_1']}?fields=resolve")
    # insert likha_sql 'brgys' between sql_1 and respond: sql_1.resolve -> brgys.id, brgys.resolve -> respond.id
    s, d = req("POST", "/operations", {"flow": fid, "name": "brgys", "key": "brgys",
        "type": "likha_sql", "position_x": 19, "position_y": 1,
        "resolve": op["respond"],
        "options": {"sql": "SELECT id, name, code, municipality FROM bis_barangays ORDER BY name"}})
    brgys_id = d["data"]["id"]
    req("PATCH", f"/operations/{op['sql_1']}", {"resolve": brgys_id})
    print("  options flow returns barangays")

    # request: accept barangay id
    fid = get_flow("bis_portal_request")
    s, d = req("GET", f"/operations?filter%5Bflow%5D%5B_eq%5D={fid}&fields=id,key")
    op = {o["key"]: o["id"] for o in d["data"]}
    req("PATCH", f"/operations/{op['validate']}", {"options": {"code": (
        "module.exports = async function(data){\n"
        "  const b = (data.$trigger && data.$trigger.body) || {};\n"
        "  const req = ['first_name','last_name','mobile','document_type','purpose','barangay'];\n"
        "  for (const k of req) if (!b[k] || !String(b[k]).trim()) throw new Error('Missing: ' + k);\n"
        "  let mob = String(b.mobile).replace(/\\D/g,'');\n"
        "  if (mob.startsWith('63')) mob = '0' + mob.slice(2);\n"
        "  if (!/^0\\d{10}$/.test(mob)) throw new Error('Invalid mobile number (use 09xxxxxxxxx)');\n"
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
    print("  request flow: barangay + DOC-<CODE> serials")


def main():
    pob = step_barangays()
    step_fields(pob)
    step_settings()
    step_serials()
    step_roles()
    step_portal()
    req("POST", "/utils/cache/clear", {"cache": "system"})
    print("\nDone. Poblacion barangay:", pob)


if __name__ == "__main__":
    main()
