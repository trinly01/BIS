#!/usr/bin/env python3
"""BIS Phase 3 — roles/policies, serial-number flows, SLA due-date stamping.

Directus 11 model: roles -> access(role,policy) -> policies -> permissions
(policy,collection,action,permissions(filter),validation,presets,fields).

Serial flows: event/items.create (non-blocking) -> likha_sql next serial ->
item-update {{$trigger.key}}. Result lands at {{sql_1.0.serial}}.
SLA flow: item-read doc type -> exec date math -> item-update due_date.
"""
import json, os, urllib.request, urllib.error, urllib.parse

BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ["DIRECTUS_TOKEN"]
HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0"}
Q = urllib.parse.quote

BIS = ["bis_settings", "bis_puroks", "bis_officials", "bis_document_types",
       "bis_households", "bis_residents", "bis_document_requests", "bis_blotter",
       "bis_blotter_parties", "bis_blotter_attachments", "bis_kp_cases",
       "bis_kp_hearings", "bis_business_permits", "bis_announcements"]
MASTER = {"bis_settings", "bis_puroks", "bis_officials", "bis_document_types"}
OPS = [c for c in BIS if c not in MASTER]
SUPPORT_READS = ["print_template", "directus_files", "directus_users",
                 "directus_dashboards", "directus_panels"]

ROLES = {
    "bis_staff": ("Front desk / records staff — registry + operations CRUD, master read-only",
                  "staff_policy"),
    "bis_secretary": ("Barangay secretary — full access incl. master data & config",
                      "secretary_policy"),
    "bis_captain": ("Punong barangay — read all, approve/release on docs, KP, blotter, permits",
                    "captain_policy"),
}


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=HDRS)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        print(f"  !! {method} {path} -> {e.code}: {e.read().decode()[:220]}")
        return e.code, {}


def find(ep, name):
    s, d = req("GET", f"/{ep}?filter%5Bname%5D%5B_eq%5D={Q(name)}&limit=1")
    return (d.get("data") or [None])[0]


def ensure_perm(policy_id, collection, action, perms=None, presets=None):
    s, d = req("GET",
        f"/permissions?filter%5Bpolicy%5D%5B_eq%5D={policy_id}"
        f"&filter%5Bcollection%5D%5B_eq%5D={collection}"
        f"&filter%5Baction%5D%5B_eq%5D={action}&limit=1")
    if d.get("data"):
        return
    req("POST", "/permissions", {
        "policy": policy_id, "collection": collection, "action": action,
        "permissions": perms or {}, "validation": None,
        "presets": presets or {}, "fields": ["*"]})


def ensure_field(coll, field, ftype, meta):
    s, d = req("GET", f"/fields/{coll}/{field}")
    if d.get("data"):
        return
    req("POST", f"/fields/{coll}", {"field": field, "type": ftype, "meta": meta})
    print(f"  + field {coll}.{field}")


def ensure_flow(name, icon, collections):
    fl = find("flows", name)
    if fl:
        return fl["id"]
    s, d = req("POST", "/flows", {
        "name": name, "icon": icon, "color": "#42A5F5", "status": "active",
        "trigger": "event",
        "options": {"type": "action", "scope": ["items.create"],
                    "collections": collections}})
    fid = (d.get("data") or {}).get("id")
    print(f"  + flow {name}" if fid else f"  !! flow {name}")
    return fid


def make_op(fid, spec, resolve_from=None):
    s, d = req("POST", "/operations", dict(spec, flow=fid))
    oid = (d.get("data") or {}).get("id")
    if oid and resolve_from:
        req("PATCH", f"/operations/{resolve_from}", {"resolve": oid})
    return oid


def serial_flow(coll, field, prefix):
    name = f"bis_serial_{prefix.lower()}"
    fid = ensure_flow(name, "pin", [coll])
    if not fid:
        return
    sql = (f"SELECT '{prefix}-' || to_char(now(),'YYYY') || '-' || lpad("
           f"(COALESCE(MAX(regexp_replace({field},'^.*-','')::int),0)+1)::text,4,'0') AS serial "
           f"FROM {coll} WHERE {field} ~ '^{prefix}-[0-9]{{4}}-[0-9]{{4}}$' "
           f"AND {field} LIKE '{prefix}-' || to_char(now(),'YYYY') || '-%'")
    op1 = make_op(fid, {"name": "Next serial", "key": "sql_1", "type": "likha_sql",
                        "position_x": 21, "position_y": 1,
                        "options": {"sql": sql, "binding": []}})
    op2 = make_op(fid, {"name": "Stamp", "key": "stamp", "type": "item-update",
                        "position_x": 39, "position_y": 1,
                        "options": {"collection": coll, "key": "{{$trigger.key}}",
                                    # likha_sql returns {sql,binding,rows:[...]}
                                    # — rows live under .rows, not at top level
                                    "payload": {field: "{{sql_1.rows.0.serial}}"},
                                    "emitEvents": False, "permissions": "$full"}},
                  resolve_from=op1)
    if op1 and op2:
        req("PATCH", f"/flows/{fid}", {"operation": op1})
        print(f"    wired {name} ({coll}.{field} <- {prefix}-YYYY-NNNN)")


def build_roles():
    for rname, (desc, psuffix) in ROLES.items():
        role = find("roles", rname)
        if not role:
            s, d = req("POST", "/roles", {"name": rname, "description": desc})
            role = d.get("data") or {}
            print(f"  + role {rname}")
        role_id = role.get("id")
        pname = f"{rname}_{psuffix.split('_')[0] if False else 'policy'}"
        pname = f"{rname}_policy"
        pol = find("policies", pname)
        if not pol:
            s, d = req("POST", "/policies", {
                "name": pname, "icon": "policy", "description": desc,
                "admin_access": False, "app_access": True})
            pol = d.get("data") or {}
            print(f"  + policy {pname}")
        pol_id = pol.get("id")
        if role_id and pol_id:
            s, d = req("GET",
                f"/access?filter%5Brole%5D%5B_eq%5D={role_id}"
                f"&filter%5Bpolicy%5D%5B_eq%5D={pol_id}&limit=1")
            if not d.get("data"):
                req("POST", "/access", {"role": role_id, "policy": pol_id, "sort": 1})
        yield rname, pol_id


def build_permissions(policies):
    for rname, pid in policies.items():
        if not pid:
            continue
        # everyone reads all bis_ collections + support collections
        for coll in BIS + SUPPORT_READS:
            ensure_perm(pid, coll, "read")
        if rname == "bis_secretary":
            for coll in BIS:
                for a in ("create", "update", "delete"):
                    ensure_perm(pid, coll, a)
        elif rname == "bis_staff":
            for coll in OPS:
                presets = {"recorded_by": "$CURRENT_USER"} if coll == "bis_blotter" else None
                ensure_perm(pid, coll, "create", presets=presets)
                ensure_perm(pid, coll, "update")
        elif rname == "bis_captain":
            for coll in ["bis_document_requests", "bis_blotter",
                         "bis_kp_cases", "bis_business_permits"]:
                ensure_perm(pid, coll, "update")
        print(f"  perms -> {rname}")


def build_serials():
    serial_flow("bis_document_requests", "request_no", "DOC")
    serial_flow("bis_blotter", "blotter_no", "BLT")
    serial_flow("bis_kp_cases", "case_no", "KP")
    serial_flow("bis_business_permits", "permit_no", "BP")


def build_sla():
    ensure_field("bis_document_requests", "due_date", "date", {
        "interface": "datetime", "width": "half", "group": "grp_request",
        "note": "Auto-stamped: created date + document_type.sla_days"})
    fid = ensure_flow("bis_stamp_sla", "schedule", ["bis_document_requests"])
    if not fid:
        return
    op1 = make_op(fid, {"name": "Read doc type", "key": "read_type",
                        "type": "item-read", "position_x": 21, "position_y": 1,
                        "options": {"collection": "bis_document_types",
                                    "key": "{{$trigger.payload.document_type}}",
                                    "query": {"fields": ["sla_days"]}}})
    op2 = make_op(fid, {"name": "Compute due", "key": "compute", "type": "exec",
                        "position_x": 39, "position_y": 1,
                        "options": {"code":
            "module.exports = async function(data) {\n"
            "  var days = (data.read_type && data.read_type.sla_days) || 0;\n"
            "  var d = new Date(); d.setDate(d.getDate() + days);\n"
            "  return { due_date: d.toISOString().slice(0,10) };\n"
            "}"}}, resolve_from=op1)
    op3 = make_op(fid, {"name": "Stamp due_date", "key": "stamp",
                        "type": "item-update", "position_x": 57, "position_y": 1,
                        "options": {"collection": "bis_document_requests",
                                    "key": "{{$trigger.key}}",
                                    "payload": {"due_date": "{{compute.due_date}}"},
                                    "emitEvents": False, "permissions": "$full"}},
                  resolve_from=op2)
    if op3:
        req("PATCH", f"/flows/{fid}", {"operation": op1})
        print("    wired bis_stamp_sla (due_date = create + sla_days)")


def build():
    print("== roles/policies")
    policies = dict(build_roles())
    print("== permissions")
    build_permissions(policies)
    print("== serial flows")
    build_serials()
    print("== SLA")
    build_sla()
    print("done.")


if __name__ == "__main__":
    build()
