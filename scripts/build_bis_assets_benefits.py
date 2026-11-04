"""BIS Phase 6 — barangay asset inventory + benefit programs.

New collections (matching the "Activity / Benefits / Asset" diagram):

  bis_assets               (master_data) — barangay property inventory:
                           chairs, tents, generators, health kits...
  bis_asset_borrowings     (operations)  — borrow ledger: who borrowed what,
                           when due, returned/overdue tracking
  bis_benefit_programs     (master_data) — aid programs catalog: calamity aid,
                           free medicines, free vaccines, scholarships...
  bis_benefit_distributions(operations)  — who received what, when, how much

All carry `barangay` M2O (Phase 5 tenancy), serial flows
(BOR-<CODE>-YYYY-NNNN / BEN-<CODE>-YYYY-NNNN), scoped role permissions, and
reverse O2M aliases onto bis_residents (`asset_borrowings`,
`benefits_received`).
"""
import os, json, urllib.request

BASE = os.environ.get("DIRECTUS_URL", "https://likha-playground.zyberlab.com")
TOKEN = os.environ["DIRECTUS_TOKEN"]
UA = {"User-Agent": "curl/8.5.0", "Authorization": f"Bearer {TOKEN}",
      "Content-Type": "application/json"}

SCOPE = {"barangay": {"_eq": "$CURRENT_USER.bis_barangay"}}


def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method,
                               data=json.dumps(body).encode() if body is not None else None,
                               headers=UA)
    try:
        with urllib.request.urlopen(r) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def get_flow(name):
    s, d = req("GET", f"/flows?filter%5Bname%5D%5B_eq%5D={name}&fields=id")
    return (d.get("data") or [{}])[0].get("id")


def collection_exists(name):
    s, d = req("GET", f"/collections/{name}")
    return s == 200 and bool(d.get("data"))


def build_collection(name, icon, group, fields, display=None, note=None, sort=None):
    if collection_exists(name):
        print(f"  = {name}")
        return
    meta = {"icon": icon, "group": group, "note": note}
    if display:
        meta["display_template"] = display
    if sort:
        meta["sort_field"] = "sort_order"
    s, d = req("POST", "/collections", {
        "collection": name, "meta": meta, "schema": {}, "fields": fields})
    print(f"  + collection {name}" if s < 300 else f"  !! {name}: {d}")


def ensure_field(collection, field, spec):
    s, d = req("GET", f"/fields/{collection}?limit=-1")
    if any(f["field"] == field for f in d.get("data", [])):
        return
    s, d = req("POST", f"/fields/{collection}", spec)
    print(f"  + {collection}.{field}" if s < 300 else f"  !! {collection}.{field}: {d}")


def m2o(collection, field, related, one_field=None, display_template="{{name}}"):
    ensure_field(collection, field, {
        "field": field, "type": "uuid",
        "meta": {"interface": "select-dropdown-m2o",
                 "options": {"template": display_template}},
        "schema": {"foreign_key_table": related, "foreign_key_column": "id"}})
    s, d = req("GET", f"/relations/{collection}/{field}")
    if s == 200 and (d.get("data") or {}).get("collection"):
        return
    body = {"collection": collection, "field": field, "related_collection": related}
    if one_field:
        body["meta"] = {"one_field": one_field}
    s, d = req("POST", "/relations", body)
    print(f"  + relation {collection}.{field}->{related}" if s < 300 else f"  !! rel {collection}.{field}: {d}")


def alias(collection, field, target_collection, group=None):
    ensure_field(collection, field, {
        "field": field, "type": "alias",
        "meta": {"interface": "list-o2m", "special": ["o2m", "alias", "no-data"],
                 "group": group,
                 "options": {"enableLink": True, "enableCreate": True}}})


def barangay_m2o(collection):
    m2o(collection, "barangay", "bis_barangays")


def serial_flow(coll, field, prefix):
    name = f"bis_serial_{prefix.lower()}"
    if get_flow(name):
        print(f"  = flow {name}")
        return
    sql = (
        f"WITH r AS (SELECT barangay FROM {coll} WHERE id='{{{{$trigger.key}}}}') "
        f"SELECT '{prefix}-'||COALESCE(b.code,'XX')||'-'||to_char(now(),'YYYY')||'-'||lpad("
        f"(COALESCE(MAX(regexp_replace(x.{field},'^.*-','')::int),0)+1)::text,4,'0') AS serial "
        f"FROM r LEFT JOIN bis_barangays b ON b.id = r.barangay "
        f"LEFT JOIN {coll} x ON x.barangay = r.barangay "
        f"AND x.{field} LIKE '{prefix}-'||b.code||'-'||to_char(now(),'YYYY')||'-%' "
        f"GROUP BY b.code")
    s, d = req("POST", "/flows", {"name": name, "trigger": "event",
        "accountability": "all",
        "options": {"type": "action", "async": True,
                    "scope": ["items.create"], "collections": [coll]}})
    fid = d["data"]["id"]
    s, d = req("POST", "/operations", {"flow": fid, "name": "next serial", "key": "sql_1",
        "type": "likha_sql", "position_x": 1, "position_y": 1, "options": {"sql": sql}})
    sql_id = d["data"]["id"]
    s, d = req("POST", "/operations", {"flow": fid, "name": "stamp", "key": "stamp",
        "type": "item-update", "position_x": 19, "position_y": 1, "resolve": None,
        "options": {"collection": coll, "key": "{{$trigger.key}}",
                    "payload": {field: "{{sql_1.rows.0.serial}}"},
                    "emitEvents": False, "permissions": "$full"}})
    req("PATCH", f"/operations/{sql_id}", {"resolve": d["data"]["id"]})
    req("PATCH", f"/flows/{fid}", {"operation": sql_id})
    print(f"  + flow {name}")


def policy_id(name):
    s, d = req("GET", f"/policies?filter%5Bname%5D%5B_eq%5D={name}&fields=id")
    return (d.get("data") or [{}])[0].get("id")


def add_perms(pid, coll, actions, scoped=True, preset=False):
    s, d = req("GET", f"/permissions?filter%5Bpolicy%5D%5B_eq%5D={pid}&filter%5Bcollection%5D%5B_eq%5D={coll}&fields=id,action&limit=-1")
    have = {p["action"] for p in d.get("data", [])}
    for act in actions:
        if act in have:
            continue
        body = {"policy": pid, "collection": coll, "action": act, "fields": ["*"]}
        if scoped:
            body["permissions"] = SCOPE
        if act == "create" and preset:
            body["presets"] = {"barangay": "$CURRENT_USER.bis_barangay"}
        s, d = req("POST", "/permissions", body)
    print(f"    perms {coll}")


def ddl(label, values):
    return {"choices": [{"text": v.replace("_", " ").title(), "value": v} for v in values]}


def main():
    # ---------- collections ----------
    print("== collections")
    build_collection("bis_assets", "inventory_2", "bis_master_data", [
        {"field": "id", "type": "uuid", "meta": {"hidden": True, "special": ["uuid"], "interface": "input", "readonly": True},
         "schema": {"is_primary_key": True, "has_auto_increment": False}},
        {"field": "asset_code", "type": "string", "meta": {"interface": "input"}},
        {"field": "name", "type": "string", "meta": {"interface": "input", "required": True}},
        {"field": "category", "type": "string", "meta": {"interface": "select-dropdown",
            "options": ddl("category", ["equipment","furniture","vehicle","facility","medical_supplies","sports","other"])}},
        {"field": "description", "type": "text", "meta": {"interface": "input-multiline"}},
        {"field": "quantity", "type": "integer", "schema": {"default_value": 1},
         "meta": {"interface": "input"}},
        {"field": "condition", "type": "string", "schema": {"default_value": "good"},
         "meta": {"interface": "select-dropdown", "options": ddl("condition", ["good","fair","for_repair","retired"])}},
        {"field": "purchase_date", "type": "date", "meta": {"interface": "datetime"}},
        {"field": "purchase_cost", "type": "decimal", "meta": {"interface": "input"}},
        {"field": "location", "type": "string", "meta": {"interface": "input"}},
        {"field": "status", "type": "string", "schema": {"default_value": "available"},
         "meta": {"interface": "select-dropdown", "options": ddl("status", ["available","fully_borrowed","for_repair","retired"])}},
        {"field": "notes", "type": "text", "meta": {"interface": "input-multiline"}},
    ], display="{{asset_code}} {{name}}")

    build_collection("bis_benefit_programs", "volunteer_activism", "bis_master_data", [
        {"field": "id", "type": "uuid", "meta": {"hidden": True, "special": ["uuid"], "interface": "input", "readonly": True},
         "schema": {"is_primary_key": True, "has_auto_increment": False}},
        {"field": "name", "type": "string", "meta": {"interface": "input", "required": True}},
        {"field": "code", "type": "string", "meta": {"interface": "input"}},
        {"field": "benefit_type", "type": "string", "meta": {"interface": "select-dropdown",
            "options": ddl("benefit_type", ["calamity_aid","free_medicines","free_vaccines","financial_assistance","food_packs","scholarship","other"])}},
        {"field": "description", "type": "text", "meta": {"interface": "input-multiline"}},
        {"field": "funding_source", "type": "string", "meta": {"interface": "input"}},
        {"field": "budget", "type": "decimal", "meta": {"interface": "input"}},
        {"field": "start_date", "type": "date", "meta": {"interface": "datetime"}},
        {"field": "end_date", "type": "date", "meta": {"interface": "datetime"}},
        {"field": "status", "type": "string", "schema": {"default_value": "active"},
         "meta": {"interface": "select-dropdown", "options": ddl("status", ["upcoming","active","closed"])}},
        {"field": "notes", "type": "text", "meta": {"interface": "input-multiline"}},
    ], display="{{name}}")

    build_collection("bis_asset_borrowings", "handyman", "bis_operations", [
        {"field": "id", "type": "uuid", "meta": {"hidden": True, "special": ["uuid"], "interface": "input", "readonly": True},
         "schema": {"is_primary_key": True, "has_auto_increment": False}},
        {"field": "borrow_no", "type": "string", "meta": {"interface": "input", "readonly": True}},
        {"field": "borrower_name", "type": "string", "meta": {"interface": "input", "note": "For non-registered borrowers"}},
        {"field": "purpose", "type": "text", "meta": {"interface": "input-multiline"}},
        {"field": "quantity", "type": "integer", "schema": {"default_value": 1}, "meta": {"interface": "input"}},
        {"field": "date_borrowed", "type": "timestamp", "meta": {"interface": "datetime", "required": True}},
        {"field": "expected_return", "type": "date", "meta": {"interface": "datetime"}},
        {"field": "date_returned", "type": "timestamp", "meta": {"interface": "datetime"}},
        {"field": "status", "type": "string", "schema": {"default_value": "borrowed"},
         "meta": {"interface": "select-dropdown", "options": ddl("status", ["borrowed","returned","overdue","lost"])}},
        {"field": "remarks", "type": "text", "meta": {"interface": "input-multiline"}},
    ], display="{{borrow_no}} {{borrower_name}}")

    build_collection("bis_benefit_distributions", "redeem", "bis_operations", [
        {"field": "id", "type": "uuid", "meta": {"hidden": True, "special": ["uuid"], "interface": "input", "readonly": True},
         "schema": {"is_primary_key": True, "has_auto_increment": False}},
        {"field": "distribution_no", "type": "string", "meta": {"interface": "input", "readonly": True}},
        {"field": "recipient_name", "type": "string", "meta": {"interface": "input"}},
        {"field": "date_received", "type": "date", "meta": {"interface": "datetime", "required": True}},
        {"field": "amount", "type": "decimal", "meta": {"interface": "input"}},
        {"field": "quantity", "type": "integer", "schema": {"default_value": 1}, "meta": {"interface": "input"}},
        {"field": "item_details", "type": "text", "meta": {"interface": "input-multiline"}},
        {"field": "remarks", "type": "text", "meta": {"interface": "input-multiline"}},
    ], display="{{distribution_no}} {{recipient_name}}")

    # ---------- relations ----------
    print("== relations + aliases")
    barangay_m2o("bis_assets"); barangay_m2o("bis_benefit_programs")
    barangay_m2o("bis_asset_borrowings"); barangay_m2o("bis_benefit_distributions")
    m2o("bis_asset_borrowings", "asset", "bis_assets", one_field="borrowings",
        display_template="{{name}}")
    m2o("bis_asset_borrowings", "resident", "bis_residents", one_field="asset_borrowings",
        display_template="{{last_name}}, {{first_name}}")
    m2o("bis_benefit_distributions", "program", "bis_benefit_programs", one_field="distributions",
        display_template="{{name}}")
    m2o("bis_benefit_distributions", "resident", "bis_residents", one_field="benefits_received",
        display_template="{{last_name}}, {{first_name}}")
    m2o("bis_benefit_distributions", "household", "bis_households", one_field="benefit_distributions",
        display_template="{{household_no}}")

    # reverse alias interfaces
    for coll, field in [("bis_assets", "borrowings"), ("bis_benefit_programs", "distributions"),
                        ("bis_residents", "asset_borrowings"), ("bis_residents", "benefits_received"),
                        ("bis_households", "benefit_distributions")]:
        alias(coll, field, None)
    # residents aliases into the Records tab
    for f in ["asset_borrowings", "benefits_received"]:
        req("PATCH", f"/fields/bis_residents/{f}", {"meta": {"group": "grp_records"}})

    # ---------- serials ----------
    print("== serial flows")
    serial_flow("bis_asset_borrowings", "borrow_no", "BOR")
    serial_flow("bis_benefit_distributions", "distribution_no", "BEN")

    # ---------- permissions ----------
    print("== permissions")
    staff = policy_id("bis_staff_policy")
    sec = policy_id("bis_secretary_policy")
    cap = policy_id("bis_captain_policy")
    adm = policy_id("bis_admin_policy")
    new_colls = ["bis_assets", "bis_asset_borrowings",
                 "bis_benefit_programs", "bis_benefit_distributions"]
    for c in new_colls:
        if staff: add_perms(staff, c, ["create", "read", "update"], scoped=True, preset=True)
        if sec:   add_perms(sec, c, ["create", "read", "update", "delete"], scoped=True, preset=True)
        if cap:   add_perms(cap, c, ["read"] + (["update"] if "borrowings" in c or "distributions" in c else []), scoped=True)
        if adm:   add_perms(adm, c, ["create", "read", "update", "delete"], scoped=False)

    req("POST", "/utils/cache/clear", {"cache": "system"})
    print("done")


if __name__ == "__main__":
    main()
