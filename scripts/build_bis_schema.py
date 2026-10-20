#!/usr/bin/env python3
"""Build the BIS (Barangay Information System) schema on likha-playground Directus.

Idempotent: safe to re-run. Never PATCHes /relations (crashes this server).
Writes require User-Agent: curl/* (Cloudflare blocks python/spoofed UAs).
"""
import json, os, sys, urllib.request, urllib.error, urllib.parse

BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ.get("DIRECTUS_TOKEN", "RBzmMVX7UP9baKtLiHV6RmmTx9s9tmFZ")
HDRS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "curl/8.5.0",
}
DRY = "--dry-run" in sys.argv


def req(method, path, body=None, quiet=False):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers=HDRS)
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


def collection_exists(name):
    s, _ = req("GET", f"/collections/{urllib.parse.quote(name)}", quiet=True)
    return s == 200


def list_fields(col):
    s, d = req("GET", f"/fields/{urllib.parse.quote(col)}?limit=-1", quiet=True)
    return {f["field"]: f for f in d.get("data", [])} if s == 200 else {}


def list_relations(col):
    s, d = req("GET", f"/relations/{urllib.parse.quote(col)}", quiet=True)
    return {(r["collection"], r["field"]): r for r in d.get("data", [])} if s == 200 else {}


ID_FIELD = {"field": "id", "type": "uuid",
            "meta": {"special": ["uuid"], "interface": "input", "readonly": True, "hidden": True},
            "schema": {"is_primary_key": True, "is_nullable": False}}


def ensure_collection(name, meta):
    if collection_exists(name):
        req("PATCH", f"/collections/{name}", {"meta": meta})
        print(f"  = {name} (patched meta)")
    else:
        s, _ = req("POST", "/collections",
                   {"collection": name, "meta": meta, "schema": {}, "fields": [ID_FIELD]})
        print(f"  + {name}" if s in (200, 201) else f"  ? {name} status {s}")


def ensure_folder(name, meta):
    """Group folder = collection row with schema NULL."""
    if collection_exists(name):
        req("PATCH", f"/collections/{name}", {"meta": meta})
        print(f"  = {name} folder (patched)")
    else:
        s, _ = req("POST", "/collections", {"collection": name, "meta": meta, "schema": None})
        print(f"  + {name} folder" if s in (200, 201) else f"  ? {name} status {s}")


def ensure_field(col, spec):
    existing = list_fields(col)
    f = spec["field"]
    if f in existing:
        req("PATCH", f"/fields/{col}/{f}", {"meta": spec.get("meta", {})})
        return "patched"
    s, _ = req("POST", f"/fields/{col}", spec)
    if s in (200, 201):
        return "created"
    print(f"  !! field {col}.{f} failed")
    return "failed"


def ensure_relation(col, field, related, one_field=None, schema_fk=True):
    rels = list_relations(col)
    if (col, field) in rels:
        print(f"  = rel {col}.{field} -> {related}")
        return
    body = {"collection": col, "field": field, "related_collection": related}
    meta = {}
    if one_field:
        meta["one_field"] = one_field
    if meta:
        body["meta"] = meta
    s, _ = req("POST", "/relations", body)
    print(f"  + rel {col}.{field} -> {related}" if s in (200, 201) else f"  !! rel {col}.{field} status {s}")


def patch_field_meta(col, field, meta):
    s, _ = req("PATCH", f"/fields/{col}/{field}", {"meta": meta})
    if s not in (200, 204):
        print(f"  !! patch {col}.{field} -> {s}")


# ---------- helpers ----------

def dd(choices, **kw):  # dropdown field
    return {"type": "string", "meta": {"interface": "select-dropdown",
            "options": {"choices": [{"text": t, "value": v} for t, v in choices]}, **kw.pop("meta", {})},
            **kw}


def checks(choices, **kw):  # multi-checkbox csv
    return {"type": "csv", "meta": {"interface": "select-multiple-checkbox",
            "options": {"choices": [{"text": t, "value": v} for t, v in choices]}, **kw.pop("meta", {})},
            "schema": {}, **kw}


def m2o(**kw):
    return {"type": "uuid", "meta": {"interface": "select-dropdown-m2o", **kw.pop("meta", {})},
            "schema": {}, **kw}


def file_f(**kw):
    return {"type": "uuid", "meta": {"interface": "file", **kw.pop("meta", {})}, "schema": {}, **kw}


def txt(t="string", iface="input", **kw):
    return {"type": t, "meta": {"interface": iface, **kw.pop("meta", {})}, "schema": {}, **kw}


def toggle(**kw):
    return {"type": "boolean", "meta": {"interface": "toggle", **kw.pop("meta", {})},
            "schema": {}, **kw}


def F(field, spec, group=None, width="full", required=False, note=None):
    spec = dict(spec)
    spec["field"] = field
    m = spec.setdefault("meta", {})
    if group: m["group"] = group
    if width: m["width"] = width
    if required: m["required"] = True
    if note: m["note"] = note
    return spec


def tabs(col, tab_list, start_sort=900):
    """tab_list: [(field_name, label)]. Returns set of group names."""
    ensure_field(col, F("grp_tabs", {"type": "alias", "meta": {
        "special": ["alias", "group", "no-data"], "interface": "group-tabs",
        "width": "full"}}, width="full"))
    for i, (name, label) in enumerate(tab_list):
        ensure_field(col, F(name, {"type": "alias", "meta": {
            "special": ["alias", "group", "no-data"], "interface": "group-raw",
            "group": "grp_tabs", "width": "full",
            "translations": [{"language": "en-US", "translation": label}]}}))
    return {n for n, _ in tab_list}


def add_audit_fields_and_relations(col):
    """accountability='all' sets meta but does NOT create the fields on this
    instance — create them explicitly (specials make Directus auto-fill them),
    then wire the M2O relations to directus_users (skill rule 9)."""
    for spec in [
        F("user_created", m2o(meta={"special": ["user-created"], "readonly": True,
                                "hidden": True, "width": "half"})),
        F("date_created", {"type": "timestamp", "meta": {"interface": "datetime",
                           "special": ["date-created"], "readonly": True,
                           "hidden": True, "width": "half"}, "schema": {}}),
        F("user_updated", m2o(meta={"special": ["user-updated"], "readonly": True,
                                "hidden": True, "width": "half"})),
        F("date_updated", {"type": "timestamp", "meta": {"interface": "datetime",
                           "special": ["date-updated"], "readonly": True,
                           "hidden": True, "width": "half"}, "schema": {}}),
    ]:
        ensure_field(col, spec)
    for f in ("user_created", "user_updated"):
        ensure_relation(col, f, "directus_users")


def build():
    print("== folders ==")
    ensure_folder("BIS", {"icon": "home_work", "collapse": "open", "sort": 2})
    for name, icon, srt in (("bis_master_data", "database", 1),
                            ("bis_registry", "folder_shared", 2),
                            ("bis_operations", "assignment", 3)):
        ensure_folder(name, {"icon": icon, "group": "BIS", "collapse": "open", "sort": srt})

    print("== collections ==")
    cols = [
        ("bis_settings", "bis_master_data", "settings", 1,
         {"singleton": True, "note": "Barangay profile and document defaults"}),
        ("bis_puroks", "bis_master_data", "location_on", 2,
         {"note": "Purok / sitio master list", "display_template": "{{name}}"}),
        ("bis_officials", "bis_master_data", "badge", 3,
         {"note": "Barangay officials, terms and signatories",
          "display_template": "{{name}} — {{position}}", "sort_field": "sort_order"}),
        ("bis_document_types", "bis_master_data", "description", 4,
         {"note": "Configurable certificate/clearance types (fee, SLA, validity)",
          "display_template": "{{name}}"}),
        ("bis_households", "bis_registry", "home", 1,
         {"note": "Household records", "display_template": "{{household_no}}"}),
        ("bis_residents", "bis_registry", "people", 2,
         {"note": "Resident registry (RBI)",
          "display_template": "{{last_name}}, {{first_name}}"}),
        ("bis_document_requests", "bis_operations", "article", 1,
         {"note": "Certificate & clearance issuance",
          "display_template": "{{request_no}}"}),
        ("bis_blotter", "bis_operations", "gavel", 2,
         {"note": "Incident blotter", "display_template": "{{blotter_no}}"}),
        ("bis_blotter_parties", "bis_operations", "group", 3,
         {"note": "Blotter parties (complainant/respondent/witness)"}),
        ("bis_blotter_attachments", "bis_operations", "attach_file", 4, {}),
        ("bis_kp_cases", "bis_operations", "balance", 5,
         {"note": "Katarungang Pambarangay cases", "display_template": "{{case_no}}"}),
        ("bis_kp_hearings", "bis_operations", "event", 6,
         {"note": "KP hearing schedules"}),
        ("bis_business_permits", "bis_operations", "storefront", 7,
         {"note": "Business permits & clearances",
          "display_template": "{{business_name}}"}),
        ("bis_announcements", "bis_operations", "campaign", 8,
         {"note": "Barangay announcements & advisories",
          "display_template": "{{title}}", "sort_field": "publish_at"}),
    ]
    for name, grp, icon, srt, extra in cols:
        meta = {"group": grp, "icon": icon, "sort": srt,
                "accountability": "all", "collapse": "open"}
        meta.update(extra)
        ensure_collection(name, meta)

    # ---------- fields ----------
    print("== fields: bis_settings ==")
    for spec in [
        F("barangay_name", txt(), required=True, width="half"),
        F("city_municipality", txt(), width="half"),
        F("province", txt(), width="half"),
        F("region", txt(), width="half"),
        F("punong_barangay", txt(), width="half"),
        F("secretary_name", txt(), width="half"),
        F("treasurer_name", txt(), width="half"),
        F("contact_number", txt(), width="half"),
        F("email", txt(), width="half"),
        F("logo", file_f(), width="half"),
        F("doc_header", txt("text", "input-rich-text-html"), width="full"),
        F("doc_footer", txt("text", "input-rich-text-md"), width="full"),
    ]:
        ensure_field("bis_settings", spec)

    print("== fields: bis_puroks ==")
    for spec in [
        F("name", txt(), required=True, width="half"),
        F("risk_level", dd([("Low", "low"), ("Moderate", "moderate"), ("High", "high")]), width="half"),
        F("description", txt("text", "input-multiline"), width="full"),
        F("notes", txt("text", "input-multiline"), width="full"),
    ]:
        ensure_field("bis_puroks", spec)

    print("== fields: bis_officials ==")
    for spec in [
        F("name", txt(), required=True, width="half"),
        F("position", dd([("Punong Barangay", "punong_barangay"), ("Kagawad", "kagawad"),
                          ("SK Chairperson", "sk_chairperson"), ("Secretary", "secretary"),
                          ("Treasurer", "treasurer"), ("Tanod", "tanod"),
                          ("Lupon Member", "lupon_member"), ("Other", "other")]),
          required=True, width="half"),
        F("resident", m2o(), width="half", note="Link to resident record if registered"),
        F("committee", txt(), width="half"),
        F("term_start", txt("date", "datetime"), width="half"),
        F("term_end", txt("date", "datetime"), width="half"),
        F("is_signatory", toggle(), width="half"),
        F("signatory_label", txt(), width="half", note="e.g. 'Punong Barangay' printed on certificates"),
        F("sort_order", txt("integer"), width="half"),
        F("status", dd([("Active", "active"), ("Inactive", "inactive")]), width="half"),
        F("photo", file_f(), width="half"),
        F("contact_number", txt(), width="half"),
    ]:
        ensure_field("bis_officials", spec)

    print("== fields: bis_document_types ==")
    for spec in [
        F("name", txt(), required=True, width="half"),
        F("code", dd([("Barangay Clearance", "barangay_clearance"),
                      ("Certificate of Residency", "residency"),
                      ("Certificate of Indigency", "indigency"),
                      ("Business Clearance", "business_clearance"),
                      ("Certificate of Good Moral", "good_moral"),
                      ("First-Time Jobseeker", "first_time_jobseeker"),
                      ("Custom", "custom")]), required=True, width="half"),
        F("fee", txt("decimal"), width="half"),
        F("validity_days", txt("integer"), width="half"),
        F("sla_days", txt("integer"), width="half",
          note="ARTA: simple=3, complex=7, highly technical=20 working days"),
        F("requirements", txt("text", "input-multiline"), width="full",
          note="One requirement per line"),
        F("template", txt("text", "input-rich-text-md"), width="full"),
        F("status", dd([("Active", "active"), ("Inactive", "inactive")]), width="half"),
        F("notes", txt("text", "input-multiline"), width="full"),
    ]:
        ensure_field("bis_document_types", spec)

    print("== fields: bis_households ==")
    tabs("bis_households", [("grp_details", "Details"), ("grp_members", "Members"),
                            ("grp_notes", "Notes")])
    for spec in [
        F("household_no", txt(), required=True, width="half", group="grp_details"),
        F("purok", m2o(), width="half", group="grp_details"),
        F("address_line", txt(), width="full", group="grp_details"),
        F("dwelling_type", dd([("Owned", "owned"), ("Rented", "rented"),
                               ("Rent-free", "rent_free"), ("Informal Settler", "informal_settler")]),
          width="half", group="grp_details"),
        F("risk_tags", checks([("Flood Prone", "flood_prone"), ("Landslide Prone", "landslide_prone"),
                               ("Storm Surge", "storm_surge"), ("Evacuation Priority", "evacuation_priority")]),
          width="full", group="grp_details"),
        F("head_resident", m2o(), width="half", group="grp_details"),
        F("notes", txt("text", "input-multiline"), width="full", group="grp_notes"),
    ]:
        ensure_field("bis_households", spec)

    print("== fields: bis_residents ==")
    tabs("bis_residents", [("grp_identity", "Identity"), ("grp_contact", "Contact & Household"),
                           ("grp_residency", "Residency"), ("grp_sectors", "Sectors & Livelihood"),
                           ("grp_records", "Records")])
    for spec in [
        F("last_name", txt(), required=True, width="half", group="grp_identity"),
        F("first_name", txt(), required=True, width="half", group="grp_identity"),
        F("middle_name", txt(), width="half", group="grp_identity"),
        F("suffix", txt(), width="half", group="grp_identity"),
        F("sex", dd([("Male", "male"), ("Female", "female")]), required=True, width="half",
          group="grp_identity"),
        F("birthdate", txt("date", "datetime"), required=True, width="half", group="grp_identity"),
        F("place_of_birth", txt(), width="half", group="grp_identity"),
        F("civil_status", dd([("Single", "single"), ("Married", "married"), ("Widowed", "widowed"),
                              ("Separated", "separated"), ("Live-in", "live_in")]),
          required=True, width="half", group="grp_identity"),
        F("citizenship", txt(meta={"options": {"placeholder": "Filipino"}}), width="half",
          group="grp_identity"),
        F("photo", file_f(), width="half", group="grp_identity"),

        F("contact_number", txt(), width="half", group="grp_contact"),
        F("email", txt(), width="half", group="grp_contact"),
        F("address_line", txt(), width="full", group="grp_contact"),
        F("purok", m2o(), width="half", group="grp_contact"),
        F("household", m2o(), width="half", group="grp_contact"),
        F("household_role", dd([("Head", "head"), ("Spouse", "spouse"), ("Child", "child"),
                                ("Parent", "parent"), ("Sibling", "sibling"),
                                ("Relative", "relative"), ("Other", "other")]),
          width="half", group="grp_contact"),
        F("emergency_contact_name", txt(), width="half", group="grp_contact"),
        F("emergency_contact_phone", txt(), width="half", group="grp_contact"),

        F("residency_start", txt("date", "datetime"), width="half", group="grp_residency"),
        F("residency_status", dd([("Active", "active"), ("Moved Out", "moved_out"),
                                  ("Deceased", "deceased")]), width="half", group="grp_residency"),
        F("registered_voter", toggle(), width="half", group="grp_residency"),
        F("precinct_no", txt(), width="half", group="grp_residency"),
        F("philsys_id", txt(), width="half", group="grp_residency",
          note="PhilSys PCN (optional)"),

        F("occupation", txt(), width="half", group="grp_sectors"),
        F("employment_status", dd([("Employed", "employed"), ("Self-Employed", "self_employed"),
                                   ("Unemployed", "unemployed"), ("Student", "student"),
                                   ("Retired", "retired"), ("OFW", "ofw")]),
          width="half", group="grp_sectors"),
        F("highest_education", dd([("Elementary", "elementary"), ("High School", "high_school"),
                                   ("Vocational", "vocational"), ("College", "college"),
                                   ("Postgraduate", "postgraduate"), ("None", "none")]),
          width="half", group="grp_sectors"),
        F("sector_tags", checks([("Senior Citizen", "senior_citizen"), ("PWD", "pwd"),
                                 ("Solo Parent", "solo_parent"), ("Youth (15-30)", "youth"),
                                 ("Pregnant/Lactating", "pregnant_lactating"),
                                 ("4Ps Beneficiary", "four_ps"), ("Indigenous", "indigenous"),
                                 ("Informal Settler", "informal_settler"),
                                 ("Evacuation Priority", "evacuation_priority")]),
          width="full", group="grp_sectors"),

        F("privacy_consent", toggle(), width="half", group="grp_records"),
        F("consent_date", txt("date", "datetime"), width="half", group="grp_records"),
        F("notes", txt("text", "input-multiline"), width="full", group="grp_records"),
    ]:
        ensure_field("bis_residents", spec)

    print("== fields: bis_document_requests ==")
    tabs("bis_document_requests", [("grp_request", "Request"), ("grp_payment", "Payment"),
                                   ("grp_release", "Release"), ("grp_notes", "Notes")])
    for spec in [
        F("request_no", txt(), width="half", group="grp_request"),
        F("resident", m2o(), required=True, width="half", group="grp_request"),
        F("document_type", m2o(), required=True, width="half", group="grp_request"),
        F("purpose", txt("text", "input-multiline"), width="full", group="grp_request"),
        F("date_requested", txt("timestamp", "datetime"), width="half", group="grp_request"),
        F("status", dd([("Received", "received"), ("Requirements Check", "requirements_check"),
                        ("For Payment", "for_payment"), ("For Signature", "for_signature"),
                        ("Released", "released"), ("Rejected", "rejected"),
                        ("Cancelled", "cancelled")]), width="half", group="grp_request"),

        F("fee", txt("decimal"), width="half", group="grp_payment"),
        F("amount_paid", txt("decimal"), width="half", group="grp_payment"),
        F("or_number", txt(), width="half", group="grp_payment"),
        F("or_date", txt("date", "datetime"), width="half", group="grp_payment"),
        F("processed_by", m2o(), width="half", group="grp_payment"),

        F("serial_no", txt(), width="half", group="grp_release"),
        F("issued_date", txt("date", "datetime"), width="half", group="grp_release"),
        F("valid_until", txt("date", "datetime"), width="half", group="grp_release"),
        F("signatory", m2o(), width="half", group="grp_release"),
        F("released_to", txt(), width="half", group="grp_release"),
        F("released_by", m2o(), width="half", group="grp_release"),

        F("remarks", txt("text", "input-multiline"), width="full", group="grp_notes"),
    ]:
        ensure_field("bis_document_requests", spec)

    print("== fields: bis_blotter ==")
    tabs("bis_blotter", [("grp_incident", "Incident"), ("grp_parties", "Parties"),
                         ("grp_action", "Action Taken")])
    for spec in [
        F("blotter_no", txt(), width="half", group="grp_incident"),
        F("date_reported", txt("timestamp", "datetime"), required=True, width="half",
          group="grp_incident"),
        F("incident_datetime", txt("timestamp", "datetime"), width="half", group="grp_incident"),
        F("location", txt(), width="half", group="grp_incident"),
        F("incident_type", dd([("Theft", "theft"), ("Physical Injury", "physical_injury"),
                               ("Threats", "threats"), ("Property Damage", "property_damage"),
                               ("Noise/Nuisance", "noise"), ("Domestic", "domestic"),
                               ("Lost Item", "lost_item"), ("Traffic", "traffic"),
                               ("Other", "other")]), width="half", group="grp_incident"),
        F("status", dd([("Open", "open"), ("Endorsed to KP", "endorsed_to_kp"),
                        ("Referred", "referred"), ("Settled", "settled"),
                        ("Closed", "closed")]), width="half", group="grp_incident"),
        F("narrative", txt("text", "input-multiline"), width="full", group="grp_incident"),

        F("other_parties", txt("text", "input-multiline"), width="full", group="grp_parties",
          note="Non-resident parties (free text)"),

        F("action_taken", txt("text", "input-multiline"), width="full", group="grp_action"),
        F("kp_case", m2o(), width="half", group="grp_action"),
        F("referred_to", txt(), width="half", group="grp_action"),
        F("referred_at", txt("date", "datetime"), width="half", group="grp_action"),
        F("recorded_by", m2o(), width="half", group="grp_action"),
    ]:
        ensure_field("bis_blotter", spec)

    print("== fields: bis_blotter_parties ==")
    for spec in [
        F("blotter", m2o(), required=True, width="half"),
        F("resident", m2o(), required=True, width="half"),
        F("party_role", dd([("Complainant", "complainant"), ("Respondent", "respondent"),
                            ("Witness", "witness")]), required=True, width="half"),
        F("contact_number", txt(), width="half"),
        F("statement", txt("text", "input-multiline"), width="full"),
    ]:
        ensure_field("bis_blotter_parties", spec)

    print("== fields: bis_blotter_attachments ==")
    for spec in [
        F("blotter", m2o(), required=True, width="half"),
        F("file", file_f(), required=True, width="half"),
        F("title", txt(), width="half"),
    ]:
        ensure_field("bis_blotter_attachments", spec)

    print("== fields: bis_kp_cases ==")
    tabs("bis_kp_cases", [("grp_case", "Case"), ("grp_hearings", "Hearings"),
                          ("grp_resolution", "Resolution")])
    for spec in [
        F("case_no", txt(), width="half", group="grp_case"),
        F("blotter", m2o(), width="half", group="grp_case",
          note="Source blotter entry, if any"),
        F("complainant", m2o(), width="half", group="grp_case"),
        F("complainant_name", txt(), width="half", group="grp_case",
          note="Free text if not a registered resident"),
        F("respondent", m2o(), width="half", group="grp_case"),
        F("respondent_name", txt(), width="half", group="grp_case"),
        F("case_type", dd([("Debt Collection", "debt_collection"),
                           ("Property Dispute", "property_dispute"),
                           ("Family Dispute", "family_dispute"),
                           ("Neighborhood", "neighborhood"),
                           ("Physical Injury", "physical_injury"), ("Other", "other")]),
          width="half", group="grp_case"),
        F("date_filed", txt("date", "datetime"), width="half", group="grp_case"),
        F("status", dd([("Filed", "filed"), ("Summons Issued", "summons_issued"),
                        ("Mediation", "mediation"), ("Conciliation", "conciliation"),
                        ("Arbitration", "arbitration"), ("Settled", "settled"),
                        ("CFA Issued", "cfa_issued"), ("Dismissed", "dismissed")]),
          width="half", group="grp_case"),

        F("settlement_details", txt("text", "input-multiline"), width="full",
          group="grp_resolution"),
        F("settled_at", txt("date", "datetime"), width="half", group="grp_resolution"),
        F("cfa_issued_at", txt("date", "datetime"), width="half", group="grp_resolution",
          note="Certificate to File Action date"),
        F("cfa_reason", txt("text", "input-multiline"), width="full", group="grp_resolution"),
        F("lupon_member", m2o(), width="half", group="grp_resolution"),
        F("remarks", txt("text", "input-multiline"), width="full", group="grp_resolution"),
    ]:
        ensure_field("bis_kp_cases", spec)

    print("== fields: bis_kp_hearings ==")
    for spec in [
        F("kp_case", m2o(), required=True, width="half"),
        F("hearing_type", dd([("Mediation", "mediation"), ("Conciliation", "conciliation"),
                              ("Arbitration", "arbitration")]), required=True, width="half"),
        F("scheduled_at", txt("timestamp", "datetime"), required=True, width="half"),
        F("venue", txt(), width="half"),
        F("outcome", dd([("Pending", "pending"), ("Settled", "settled"),
                         ("Rescheduled", "rescheduled"), ("No Appearance", "no_appearance"),
                         ("Escalated", "escalated")]), width="half"),
        F("notes", txt("text", "input-multiline"), width="full"),
    ]:
        ensure_field("bis_kp_hearings", spec)

    print("== fields: bis_business_permits ==")
    for spec in [
        F("business_name", txt(), required=True, width="half"),
        F("owner_resident", m2o(), width="half"),
        F("owner_name", txt(), width="half"),
        F("business_type", dd([("Sari-Sari Store", "sari_sari"), ("Eatery/Carinderia", "eatery"),
                               ("Services", "services"), ("Retail", "retail"),
                               ("Other", "other")]), width="half"),
        F("address", txt(), width="half"),
        F("purok", m2o(), width="half"),
        F("permit_no", txt(), width="half"),
        F("date_issued", txt("date", "datetime"), width="half"),
        F("valid_until", txt("date", "datetime"), width="half"),
        F("fee", txt("decimal"), width="half"),
        F("or_number", txt(), width="half"),
        F("status", dd([("Active", "active"), ("Expired", "expired"),
                        ("Revoked", "revoked")]), width="half"),
        F("remarks", txt("text", "input-multiline"), width="full"),
    ]:
        ensure_field("bis_business_permits", spec)

    print("== fields: bis_announcements ==")
    for spec in [
        F("title", txt(), required=True, width="half"),
        F("category", dd([("Advisory", "advisory"), ("Event", "event"),
                          ("Emergency", "emergency"), ("Ordinance", "ordinance"),
                          ("Livelihood", "livelihood"), ("Other", "other")]), width="half"),
        F("status", dd([("Draft", "draft"), ("Published", "published"),
                        ("Archived", "archived")]), width="half"),
        F("pinned", toggle(), width="half"),
        F("publish_at", txt("timestamp", "datetime"), width="half"),
        F("expires_at", txt("timestamp", "datetime"), width="half"),
        F("posted_by", m2o(), width="half"),
        F("body", txt("text", "input-rich-text-html"), width="full"),
    ]:
        ensure_field("bis_announcements", spec)

    # ---------- relations ----------
    print("== relations ==")
    RELS = [
        # (collection, field, related, one_field)
        ("bis_settings", "logo", "directus_files", None),
        ("bis_officials", "resident", "bis_residents", "official_posts"),
        ("bis_officials", "photo", "directus_files", None),
        ("bis_households", "purok", "bis_puroks", "households"),
        ("bis_households", "head_resident", "bis_residents", None),
        ("bis_residents", "purok", "bis_puroks", "residents"),
        ("bis_residents", "household", "bis_households", "members"),
        ("bis_residents", "photo", "directus_files", None),
        ("bis_document_requests", "resident", "bis_residents", "document_requests"),
        ("bis_document_requests", "document_type", "bis_document_types", "requests"),
        ("bis_document_requests", "signatory", "bis_officials", "signed_documents"),
        ("bis_document_requests", "processed_by", "directus_users", None),
        ("bis_document_requests", "released_by", "directus_users", None),
        ("bis_blotter_parties", "blotter", "bis_blotter", "parties"),
        ("bis_blotter_parties", "resident", "bis_residents", "blotter_involvements"),
        ("bis_blotter_attachments", "blotter", "bis_blotter", "attachments"),
        ("bis_blotter_attachments", "file", "directus_files", None),
        ("bis_blotter", "kp_case", "bis_kp_cases", "blotters"),
        ("bis_blotter", "recorded_by", "directus_users", None),
        ("bis_kp_cases", "blotter", "bis_blotter", "kp_cases"),
        ("bis_kp_cases", "complainant", "bis_residents", "kp_cases_as_complainant"),
        ("bis_kp_cases", "respondent", "bis_residents", "kp_cases_as_respondent"),
        ("bis_kp_cases", "lupon_member", "bis_officials", "kp_cases_handled"),
        ("bis_kp_hearings", "kp_case", "bis_kp_cases", "hearings"),
        ("bis_business_permits", "owner_resident", "bis_residents", "business_permits"),
        ("bis_business_permits", "purok", "bis_puroks", "business_permits"),
        ("bis_announcements", "posted_by", "directus_users", None),
    ]
    for col, field, rel, one in RELS:
        ensure_relation(col, field, rel, one)

    print("== audit fields + relations (directus_users) ==")
    for name, *_ in cols:
        add_audit_fields_and_relations(name)

    # ---------- alias interfaces + tab placement ----------
    print("== alias interface patches ==")
    ALIAS = [
        ("bis_puroks", "households", "list-o2m", None, "{{household_no}} — {{dwelling_type}}"),
        ("bis_puroks", "residents", "list-o2m", None, "{{last_name}}, {{first_name}}"),
        ("bis_puroks", "business_permits", "list-o2m", None, "{{business_name}}"),
        ("bis_residents", "official_posts", "list-o2m", "grp_records", "{{position}} ({{term_start}})"),
        ("bis_residents", "document_requests", "list-o2m", "grp_records",
         "{{document_type.name}} — {{status}}"),
        ("bis_residents", "blotter_involvements", "list-o2m", "grp_records",
         "{{blotter.blotter_no}} — {{party_role}}"),
        ("bis_residents", "kp_cases_as_complainant", "list-o2m", "grp_records", "{{case_no}}"),
        ("bis_residents", "kp_cases_as_respondent", "list-o2m", "grp_records", "{{case_no}}"),
        ("bis_residents", "business_permits", "list-o2m", "grp_records", "{{business_name}}"),
        ("bis_households", "members", "list-o2m", "grp_members",
         "{{last_name}}, {{first_name}} ({{household_role}})"),
        ("bis_document_types", "requests", "list-o2m", None, "{{request_no}} — {{status}}"),
        ("bis_officials", "signed_documents", "list-o2m", None, "{{serial_no}}"),
        ("bis_officials", "kp_cases_handled", "list-o2m", None, "{{case_no}}"),
        ("bis_blotter", "parties", "list-o2m", "grp_parties",
         "{{resident.last_name}}, {{resident.first_name}} ({{party_role}})"),
        ("bis_blotter", "attachments", "list-o2m", "grp_action", "{{title}}"),
        ("bis_kp_cases", "hearings", "list-o2m", "grp_hearings",
         "{{scheduled_at}} — {{hearing_type}} — {{outcome}}"),
        ("bis_kp_cases", "blotters", "list-o2m", "grp_case", "{{blotter_no}}"),
        ("bis_blotter", "kp_cases", "list-o2m", "grp_action", "{{case_no}}"),
    ]
    for col, field, iface, grp, tmpl in ALIAS:
        meta = {"interface": iface, "options": {"template": tmpl, "enableCreate": True},
                "special": ["o2m"], "width": "full"}
        if grp:
            meta["group"] = grp
        patch_field_meta(col, field, meta)

    print("done.")


if __name__ == "__main__":
    build()
