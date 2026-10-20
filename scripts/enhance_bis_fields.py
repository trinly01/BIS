#!/usr/bin/env python3
"""BIS field-config polish pass.

- list-o2m aliases: `fields` column list (table-like rows), sortField, enableLink/Create/Select
- M2O pickers: display `options.template`
- junction-ish collections: display_template + hidden from nav
Idempotent — safe to re-run.
"""
import json, os, urllib.request, urllib.error

BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ.get("DIRECTUS_TOKEN", "RBzmMVX7UP9baKtLiHV6RmmTx9s9tmFZ")
HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0"}


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=HDRS)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        print(f"  !! {method} {path} -> {e.code}: {e.read().decode()[:250]}")
        return e.code, {}


def pf(col, field, meta):
    s, _ = req("PATCH", f"/fields/{col}/{field}", {"meta": meta})
    print(("  = " if s in (200, 204) else "  !! ") + f"{col}.{field}")


def pc(col, meta):
    s, _ = req("PATCH", f"/collections/{col}", {"meta": meta})
    print(("  = " if s in (200, 204) else "  !! ") + f"collection {col}")


def o2m(col, field, group, template, fields=None, sort=None):
    opts = {"template": template, "enableCreate": True, "enableSelect": True,
            "enableLink": True, "enableSearchFilter": True}
    if fields:
        opts["fields"] = fields
    if sort:
        opts["sortField"] = sort
    meta = {"interface": "list-o2m", "special": ["o2m"], "width": "full", "options": opts}
    if group:
        meta["group"] = group
    pf(col, field, meta)


def m2o_tpl(col, field, template, group=None, extra_opts=None):
    opts = {"template": template}
    if extra_opts:
        opts.update(extra_opts)
    meta = {"interface": "select-dropdown-m2o", "options": opts}
    if group:
        meta["group"] = group
    pf(col, field, meta)


# ---------- O2M aliases: table-style field lists ----------
O2M = [
    # residents "Records" tab
    ("bis_residents", "document_requests", "grp_records",
     "{{request_no}} — {{status}}",
     ["request_no", "document_type", "status", "date_requested"], "-date_requested"),
    ("bis_residents", "blotter_involvements", "grp_records",
     "{{blotter.blotter_no}} — {{party_role}}", ["blotter", "party_role"], None),
    ("bis_residents", "kp_cases_as_complainant", "grp_records",
     "{{case_no}} — {{status}}", ["case_no", "case_type", "status", "date_filed"], "-date_filed"),
    ("bis_residents", "kp_cases_as_respondent", "grp_records",
     "{{case_no}} — {{status}}", ["case_no", "case_type", "status", "date_filed"], "-date_filed"),
    ("bis_residents", "business_permits", "grp_records",
     "{{business_name}} — {{status}}",
     ["business_name", "permit_no", "status", "valid_until"], "-date_issued"),
    ("bis_residents", "official_posts", "grp_records",
     "{{position}} ({{term_start}})", ["position", "term_start", "term_end", "status"], "sort_order"),
    # households
    ("bis_households", "members", "grp_members",
     "{{last_name}}, {{first_name}} ({{household_role}})",
     ["first_name", "last_name", "household_role", "sex", "birthdate", "sector_tags"], None),
    # puroks
    ("bis_puroks", "residents", None, "{{last_name}}, {{first_name}}",
     ["first_name", "last_name", "sex", "household_role", "sector_tags"], "last_name"),
    ("bis_puroks", "households", None, "{{household_no}} — {{address_line}}",
     ["household_no", "address_line", "dwelling_type", "risk_tags"], "household_no"),
    ("bis_puroks", "business_permits", None, "{{business_name}}",
     ["business_name", "owner_name", "status", "valid_until"], None),
    # master data reverse lists
    ("bis_document_types", "requests", None, "{{request_no}} — {{status}}",
     ["request_no", "resident", "status", "date_requested"], "-date_requested"),
    ("bis_officials", "signed_documents", None, "{{serial_no}}",
     ["serial_no", "document_type", "status", "issued_date"], "-issued_date"),
    ("bis_officials", "kp_cases_handled", None, "{{case_no}} — {{status}}",
     ["case_no", "status", "date_filed"], "-date_filed"),
    # operations parents
    ("bis_blotter", "parties", "grp_parties",
     "{{resident.last_name}}, {{resident.first_name}} ({{party_role}})",
     ["party_role", "resident", "contact_number", "statement"], "party_role"),
    ("bis_blotter", "attachments", "grp_action", "{{title}}", ["file", "title"], None),
    ("bis_blotter", "kp_cases", "grp_action", "{{case_no}} — {{status}}",
     ["case_no", "status", "date_filed"], "-date_filed"),
    ("bis_kp_cases", "hearings", "grp_hearings",
     "{{scheduled_at}} — {{hearing_type}} — {{outcome}}",
     ["hearing_type", "scheduled_at", "venue", "outcome"], "scheduled_at"),
    ("bis_kp_cases", "blotters", "grp_case", "{{blotter_no}}",
     ["blotter_no", "incident_type", "date_reported", "status"], "-date_reported"),
]

# ---------- M2O pickers: display templates ----------
M2O = [
    ("bis_households", "purok", "{{name}}", "grp_details"),
    ("bis_households", "head_resident", "{{last_name}}, {{first_name}}", "grp_details"),
    ("bis_residents", "purok", "{{name}}", "grp_contact"),
    ("bis_residents", "household", "{{household_no}} — {{address_line}}", "grp_contact"),
    ("bis_officials", "resident", "{{last_name}}, {{first_name}}", None),
    ("bis_document_requests", "resident", "{{last_name}}, {{first_name}}", "grp_request"),
    ("bis_document_requests", "document_type", "{{name}} (₱{{fee}})", "grp_request"),
    ("bis_document_requests", "signatory", "{{name}} — {{signatory_label}}", "grp_release"),
    ("bis_blotter", "kp_case", "{{case_no}} — {{status}}", "grp_action"),
    ("bis_blotter_parties", "blotter", "{{blotter_no}}", None),
    ("bis_blotter_parties", "resident", "{{last_name}}, {{first_name}}", None),
    ("bis_blotter_attachments", "blotter", "{{blotter_no}}", None),
    ("bis_kp_cases", "blotter", "{{blotter_no}} — {{incident_type}}", "grp_case"),
    ("bis_kp_cases", "complainant", "{{last_name}}, {{first_name}}", "grp_case"),
    ("bis_kp_cases", "respondent", "{{last_name}}, {{first_name}}", "grp_case"),
    ("bis_kp_cases", "lupon_member", "{{name}} — {{position}}", "grp_resolution"),
    ("bis_kp_hearings", "kp_case", "{{case_no}} — {{status}}", None),
    ("bis_business_permits", "owner_resident", "{{last_name}}, {{first_name}}", None),
    ("bis_business_permits", "purok", "{{name}}", None),
]

# ---------- collections: display templates / nav visibility ----------
COL_META = [
    ("bis_blotter_parties", {"display_template": "{{party_role}} — {{resident.last_name}}",
                             "hidden": True}),
    ("bis_blotter_attachments", {"display_template": "{{title}}", "hidden": True}),
    ("bis_kp_hearings", {"display_template": "{{hearing_type}} — {{scheduled_at}}"}),
]

if __name__ == "__main__":
    print("== o2m aliases (table fields) ==")
    for col, fld, grp, tpl, fields, sort in O2M:
        o2m(col, fld, grp, tpl, fields, sort)
    print("== m2o picker templates ==")
    for col, fld, tpl, grp in M2O:
        m2o_tpl(col, fld, tpl, grp)
    print("== collection meta ==")
    for col, meta in COL_META:
        pc(col, meta)
    print("done.")
