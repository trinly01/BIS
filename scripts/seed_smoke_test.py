#!/usr/bin/env python3
"""Seed a small end-to-end smoke-test chain for BIS and verify relational reads."""
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
        return e.code, json.loads(e.read().decode() or "{}")


def create(col, item):
    s, d = req("POST", f"/items/{col}", item)
    if s in (200, 201):
        return d["data"]["id"]
    print(f"!! create {col}: {s} {json.dumps(d)[:300]}")
    return None


def find(col, filter_q):
    s, d = req("GET", f"/items/{col}?{filter_q}")
    return d["data"][0] if s == 200 and d.get("data") else None


def get_or_create(col, filter_q, item):
    row = find(col, filter_q)
    return row["id"] if row else create(col, item)


PUROK = "f4b82a8c-7791-4286-8f49-a97499365e98"
PUNONG = "18e7fb72-3e35-40ca-a77c-bb464dca5f7a"
DT = find("bis_document_types", "filter%5Bcode%5D%5B_eq%5D=barangay_clearance&fields=id")["id"]

H1 = get_or_create("bis_households", "filter%5Bhousehold_no%5D%5B_eq%5D=HH-0001&fields=id",
                   {"household_no": "HH-0001", "purok": PUROK,
                    "address_line": "123 Mabini St.", "dwelling_type": "owned",
                    "risk_tags": ["flood_prone"]})
R1 = get_or_create("bis_residents",
                   "filter%5Blast_name%5D%5B_eq%5D=Dela%20Cruz&filter%5Bfirst_name%5D%5B_eq%5D=Jose&fields=id",
                   {"last_name": "Dela Cruz", "first_name": "Jose",
                    "middle_name": "Rizal", "sex": "male", "birthdate": "1990-05-15",
                    "civil_status": "married", "citizenship": "Filipino", "purok": PUROK,
                    "household": H1, "household_role": "head", "residency_start": "2010-01-01",
                    "residency_status": "active", "registered_voter": True,
                    "sector_tags": ["youth"], "occupation": "Driver",
                    "employment_status": "employed"})
R2 = get_or_create("bis_residents",
                   "filter%5Blast_name%5D%5B_eq%5D=Dela%20Cruz&filter%5Bfirst_name%5D%5B_eq%5D=Ana&fields=id",
                   {"last_name": "Dela Cruz", "first_name": "Ana",
                    "sex": "female", "birthdate": "1992-08-20", "civil_status": "married",
                    "purok": PUROK, "household": H1, "household_role": "spouse",
                    "residency_status": "active", "sector_tags": ["four_ps"]})
print("household:", H1, "| residents:", R1, R2)

# point household.head_resident at R1
req("PATCH", f"/items/bis_households/{H1}", {"head_resident": R1})

DR = get_or_create("bis_document_requests",
                   "filter%5Brequest_no%5D%5B_eq%5D=REQ-2026-0001&fields=id", {
    "request_no": "REQ-2026-0001", "resident": R1, "document_type": DT,
    "purpose": "Employment requirement", "date_requested": "2026-10-21T09:00:00",
    "status": "released", "fee": 50, "or_number": "OR-1001",
    "or_date": "2026-10-21", "amount_paid": 50, "serial_no": "BC-2026-0001",
    "issued_date": "2026-10-21", "signatory": PUNONG})
print("docreq:", DR)

B1 = get_or_create("bis_blotter",
                   "filter%5Bblotter_no%5D%5B_eq%5D=BLT-2026-0001&fields=id", {
    "blotter_no": "BLT-2026-0001", "date_reported": "2026-10-20T14:30:00",
    "incident_datetime": "2026-10-20T13:00:00", "location": "Purok 1 - Centro",
    "incident_type": "noise",
    "narrative": "Noise complaint re: videoke past 10PM",
    "status": "endorsed_to_kp"})
if not find("bis_blotter_parties",
            f"filter%5Bblotter%5D%5B_eq%5D={B1}&fields=id"):
    create("bis_blotter_parties", {"blotter": B1, "resident": R1, "party_role": "complainant"})
    create("bis_blotter_parties", {"blotter": B1, "resident": R2, "party_role": "respondent"})
print("blotter:", B1)

KP = get_or_create("bis_kp_cases", "filter%5Bcase_no%5D%5B_eq%5D=KP-2026-0001&fields=id", {
    "case_no": "KP-2026-0001", "blotter": B1, "complainant": R1, "respondent": R2,
    "case_type": "neighborhood", "date_filed": "2026-10-21", "status": "mediation",
    "lupon_member": PUNONG})
if not find("bis_kp_hearings", f"filter%5Bkp_case%5D%5B_eq%5D={KP}&fields=id"):
    create("bis_kp_hearings", {"kp_case": KP, "hearing_type": "mediation",
           "scheduled_at": "2026-10-28T09:00:00", "venue": "Barangay Hall",
           "outcome": "pending"})
print("kp:", KP)

get_or_create("bis_business_permits", "filter%5Bpermit_no%5D%5B_eq%5D=BP-2026-001&fields=id", {
    "business_name": "Jose's Sari-Sari Store", "owner_resident": R1,
    "business_type": "sari_sari", "address": "123 Mabini St.", "purok": PUROK,
    "permit_no": "BP-2026-001", "date_issued": "2026-10-01",
    "valid_until": "2026-12-31", "fee": 500, "or_number": "OR-1002",
    "status": "active"})
get_or_create("bis_announcements", "filter%5Btitle%5D%5B_eq%5D=Barangay%20Assembly%20-%20Oct%2026&fields=id", {
    "title": "Barangay Assembly - Oct 26", "category": "event",
    "status": "published", "pinned": True, "publish_at": "2026-10-21T08:00:00",
    "body": "<p>Semi-annual barangay assembly at the covered court, 8AM.</p>"})

# singleton settings: PATCH (no POST for singletons)
s, d = req("PATCH", "/items/bis_settings", {
    "barangay_name": "Barangay Sample", "city_municipality": "Quezon City",
    "province": "Metro Manila", "region": "NCR", "punong_barangay": "Juan D. Cruz"})
print("settings patch:", s)

print("\n--- relational verification ---")
s, d = req("GET", f"/items/bis_residents/{R1}"
           "?fields=last_name,first_name,household.household_no,purok.name,"
           "document_requests.request_no,blotter_involvements.party_role,"
           "kp_cases_as_complainant.case_no,business_permits.business_name,"
           "user_created.first_name,date_created")
print(json.dumps(d, indent=1)[:1500])

s, d = req("GET", f"/items/bis_blotter/{B1}"
           "?fields=blotter_no,status,parties.party_role,parties.resident.first_name,"
           "kp_cases.case_no")
print(json.dumps(d, indent=1)[:1000])

s, d = req("GET", f"/items/bis_kp_cases/{KP}"
           "?fields=case_no,status,hearings.scheduled_at,hearings.outcome,"
           "complainant.first_name,respondent.first_name")
print(json.dumps(d, indent=1)[:1000])
