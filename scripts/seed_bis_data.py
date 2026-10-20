#!/usr/bin/env python3
"""Seed realistic BIS data — full sanggunian, households, residents w/ sector
spread, document requests across Aug-Oct 2026 (feeds the trend chart), blotters
w/ parties, KP cases w/ hearings, permits, announcements.

Idempotent via get_or_create on natural keys.
"""
import json, os, urllib.request, urllib.error, urllib.parse

BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ.get("DIRECTUS_TOKEN", "RBzmMVX7UP9baKtLiHV6RmmTx9s9tmFZ")
HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0"}
Q = urllib.parse.quote


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=HDRS)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        print(f"  !! {method} {path} -> {e.code}: {e.read().decode()[:250]}")
        return e.code, {}


def find(col, fq):
    s, d = req("GET", f"/items/{col}?{fq}&fields=id&limit=1")
    return d["data"][0]["id"] if s == 200 and d.get("data") else None


def goc(col, fq, item):
    return find(col, fq) or create(col, item)


def create(col, item):
    s, d = req("POST", f"/items/{col}", item)
    return (d.get("data") or {}).get("id")


def fk(col, fq):
    return find(col, fq)


# ---------- puroks ----------
PUROKS = {}
for name, risk in [("Purok 1 - Centro", "low"), ("Purok 2 - Riverside", "high"),
                   ("Purok 3 - Hillside", "moderate"), ("Purok 4 - Kamagong", "low"),
                   ("Purok 5 - Sampaguita", "low"), ("Purok 6 - Mahogany", "moderate"),
                   ("Purok 7 - Narra", "high")]:
    PUROKS[name] = goc("bis_puroks", f"filter%5Bname%5D%5B_eq%5D={Q(name)}",
                       {"name": name, "risk_level": risk})
P = lambda n: PUROKS[[k for k in PUROKS if k.startswith(n)][0]]

# ---------- settings ----------
req("PATCH", "/items/bis_settings", {
    "barangay_name": "Barangay Poblacion", "city_municipality": "San Fabian",
    "province": "Pangasinan", "region": "Ilocos Region (Region I)",
    "punong_barangay": "Ricardo M. Villanueva", "secretary_name": "Maria L. Santos",
    "treasurer_name": "Emilio G. Paredes", "contact_number": "(075) 555-1234"})

# ---------- officials ----------
OFFICIALS = [
    ("Ricardo M. Villanueva", "punong_barangay", "Executive", 1, True, "Punong Barangay"),
    ("Josefa A. Mendiola", "kagawad", "Appropriations", 2, False, None),
    ("Ramon C. dela Torre", "kagawad", "Peace & Order", 3, False, None),
    ("Liza B. Corpuz", "kagawad", "Health & Sanitation", 4, False, None),
    ("Antonio R. Fajardo", "kagawad", "Infrastructure", 5, False, None),
    ("Grace N. Salcedo", "kagawad", "Education", 6, False, None),
    ("Victor P. Manalo", "kagawad", "Environment", 7, False, None),
    ("Nena D. Rosales", "kagawad", "Social Services", 8, False, None),
    ("Karl J. Agustin", "sk_chairperson", "Youth & Sports", 9, False, None),
    ("Maria L. Santos", "secretary", None, 10, True, "Barangay Secretary"),
    ("Emilio G. Paredes", "treasurer", None, 11, True, "Barangay Treasurer"),
    ("Domingo S. Cruz", "tanod", None, 12, False, None),
    ("Alfredo T. Navarro", "lupon_member", None, 13, True, "Lupon Chairman"),
]
OFF = {}
for name, pos, comm, so, sig, lbl in OFFICIALS:
    OFF[name] = goc("bis_officials",
                    f"filter%5Bname%5D%5B_eq%5D={Q(name)}&filter%5Bposition%5D%5B_eq%5D={pos}",
                    {"name": name, "position": pos, "committee": comm, "sort_order": so,
                     "is_signatory": sig, "signatory_label": lbl, "status": "active",
                     "term_start": "2023-11-30", "term_end": "2025-12-31"})
PUNONG = OFF["Ricardo M. Villanueva"]
LUPON = OFF["Alfredo T. Navarro"]

# ---------- households ----------
HOUSEHOLDS = [
    # (no, purok, addr, dwelling, risk)
    ("HH-0002", "Purok 2", "45 Lakas St.", "rented", ["flood_prone"]),
    ("HH-0003", "Purok 1", "78 Mabini St.", "owned", []),
    ("HH-0004", "Purok 3", "12 Hilltop Rd.", "owned", ["landslide_prone"]),
    ("HH-0005", "Purok 4", "9 Kamagong Ave.", "owned", []),
    ("HH-0006", "Purok 5", "22 Sampaguita St.", "owned", []),
    ("HH-0007", "Purok 2", "3 Riverside Ln.", "informal_settler",
     ["flood_prone", "evacuation_priority"]),
    ("HH-0008", "Purok 6", "31 Mahogany Dr.", "rented", []),
    ("HH-0009", "Purok 3", "18 Hilltop Rd.", "owned", ["landslide_prone"]),
    ("HH-0010", "Purok 7", "5 Narra St.", "rent_free", ["flood_prone"]),
]
HH = {"HH-0001": fk("bis_households", "filter%5Bhousehold_no%5D%5B_eq%5D=HH-0001")}
for no, pk, addr, dw, risk in HOUSEHOLDS:
    HH[no] = goc("bis_households", f"filter%5Bhousehold_no%5D%5B_eq%5D={no}",
                 {"household_no": no, "purok": P(pk), "address_line": addr,
                  "dwelling_type": dw, "risk_tags": risk})

# ---------- residents ----------
# (last, first, middle, sex, bday, civil, household, role, purok, sectors, voter, occup, emp, edu, res_start)
RESIDENTS = [
    ("Reyes", "Mario", "Dizon", "male", "1955-03-12", "married", "HH-0002", "head",
     "Purok 2", ["senior_citizen", "pwd"], True, "Retired Driver", "retired", "elementary", "1998-06-01"),
    ("Reyes", "Luningning", "Cruz", "female", "1958-07-25", "married", "HH-0002", "spouse",
     "Purok 2", ["senior_citizen"], True, None, "retired", "elementary", "1998-06-01"),
    ("Reyes", "Paolo", "Santos", "male", "2004-11-02", "single", "HH-0002", "child",
     "Purok 2", ["youth"], True, "Delivery Rider", "employed", "high_school", "1998-06-01"),
    ("Santos", "Roberto", "Lim", "male", "1975-01-30", "married", "HH-0003", "head",
     "Purok 1", [], True, "Tricycle Driver", "self_employed", "high_school", "2000-02-14"),
    ("Santos", "Corazon", "Vega", "female", "1978-09-17", "married", "HH-0003", "spouse",
     "Purok 1", [], True, "Vendor", "self_employed", "high_school", "2000-02-14"),
    ("Santos", "Miguel", "Vega", "male", "2003-05-08", "single", "HH-0003", "child",
     "Purok 1", ["youth"], True, "Student", "student", "high_school", "2000-02-14"),
    ("Aquino", "Elena", "Ramos", "female", "1985-12-03", "widowed", "HH-0004", "head",
     "Purok 3", ["solo_parent", "four_ps"], True, "Laundress", "self_employed", "high_school", "2008-04-20"),
    ("Aquino", "Katrina", "Ramos", "female", "2007-02-14", "single", "HH-0004", "child",
     "Purok 3", ["youth", "four_ps"], False, "Student", "student", "high_school", "2008-04-20"),
    ("Aquino", "Joshua", "Ramos", "male", "2010-08-30", "single", "HH-0004", "child",
     "Purok 3", ["four_ps"], False, "Student", "student", "elementary", "2008-04-20"),
    ("Garcia", "Fernando", "Ong", "male", "1970-06-18", "married", "HH-0005", "head",
     "Purok 4", [], True, "Construction Foreman", "employed", "vocational", "1995-01-10"),
    ("Garcia", "Rosalinda", "Tan", "female", "1973-10-05", "married", "HH-0005", "spouse",
     "Purok 4", ["four_ps"], True, "Housewife", "unemployed", "high_school", "1995-01-10"),
    ("Garcia", "Mark", "Tan", "male", "2001-04-22", "single", "HH-0005", "child",
     "Purok 4", ["youth"], True, "BPO Agent", "employed", "college", "1995-01-10"),
    ("Garcia", "Angel", "Tan", "female", "2006-12-11", "single", "HH-0005", "child",
     "Purok 4", ["youth"], False, "Student", "student", "high_school", "1995-01-10"),
    ("Mendoza", "Teresita", "Go", "female", "1949-02-28", "widowed", "HH-0006", "head",
     "Purok 5", ["senior_citizen", "evacuation_priority"], True, None, "retired", "elementary", "1980-05-15"),
    ("Bautista", "Danilo", "Sia", "male", "1982-03-19", "married", "HH-0007", "head",
     "Purok 2", ["informal_settler"], True, "Jeepney Barker", "self_employed", "elementary", "2015-07-01"),
    ("Bautista", "Marites", "Yu", "female", "1986-11-27", "married", "HH-0007", "spouse",
     "Purok 2", ["informal_settler", "pregnant_lactating"], True, "Housewife", "unemployed", "high_school", "2015-07-01"),
    ("Bautista", "Jenny", "Yu", "female", "2011-01-09", "single", "HH-0007", "child",
     "Purok 2", ["informal_settler", "four_ps"], False, "Student", "student", "elementary", "2015-07-01"),
    ("Bautista", "Marco", "Yu", "male", "2014-06-25", "single", "HH-0007", "child",
     "Purok 2", ["informal_settler", "four_ps"], False, "Student", "student", "elementary", "2015-07-01"),
    ("Ramos", "Gregorio", "Chua", "male", "1968-09-14", "married", "HH-0008", "head",
     "Purok 6", ["pwd"], True, "Watch Repairman", "self_employed", "vocational", "2003-11-11"),
    ("Ramos", "Angelina", "Dee", "female", "1971-04-02", "married", "HH-0008", "spouse",
     "Purok 6", [], True, "Sari-Sari Store Owner", "self_employed", "high_school", "2003-11-11"),
    ("Torres", "Christopher", "Uy", "male", "1980-08-07", "married", "HH-0009", "head",
     "Purok 3", [], True, "Seafarer", "ofw", "college", "2005-03-30"),
    ("Torres", "Jocelyn", "Sy", "female", "1983-10-21", "married", "HH-0009", "spouse",
     "Purok 3", ["solo_parent"], True, "Online Seller", "self_employed", "college", "2005-03-30"),
    ("Torres", "Ivan", "Sy", "male", "2009-07-16", "single", "HH-0009", "child",
     "Purok 3", ["youth"], False, "Student", "student", "high_school", "2005-03-30"),
    ("Lim", "Benjamin", "Ko", "male", "1965-05-29", "married", "HH-0010", "head",
     "Purok 7", [], True, "Hardware Store Owner", "self_employed", "college", "1992-08-08"),
    ("Lim", "Sharon", "Ty", "female", "1968-12-01", "married", "HH-0010", "spouse",
     "Purok 7", [], True, "Dentist", "employed", "postgraduate", "1992-08-08"),
    ("Lim", "Andrea", "Ty", "female", "2002-03-03", "single", "HH-0010", "child",
     "Purok 7", ["youth"], True, "Nurse", "employed", "college", "1992-08-08"),
]
R = {"Dela Cruz,Jose": fk("bis_residents",
        "filter%5Blast_name%5D%5B_eq%5D=Dela%20Cruz&filter%5Bfirst_name%5D%5B_eq%5D=Jose"),
     "Dela Cruz,Ana": fk("bis_residents",
        "filter%5Blast_name%5D%5B_eq%5D=Dela%20Cruz&filter%5Bfirst_name%5D%5B_eq%5D=Ana")}
for last, first, mid, sex, bday, civil, hh, role, pk, sec, voter, occ, emp, edu, rs in RESIDENTS:
    key = f"{last},{first}"
    R[key] = goc("bis_residents",
                 f"filter%5Blast_name%5D%5B_eq%5D={Q(last)}&filter%5Bfirst_name%5D%5B_eq%5D={Q(first)}",
                 {"last_name": last, "first_name": first, "middle_name": mid, "sex": sex,
                  "birthdate": bday, "civil_status": civil, "citizenship": "Filipino",
                  "household": HH[hh], "household_role": role, "purok": P(pk),
                  "sector_tags": sec, "registered_voter": voter, "occupation": occ,
                  "employment_status": emp, "highest_education": edu,
                  "residency_start": rs, "residency_status": "active",
                  "privacy_consent": True})
print("residents:", sum(1 for v in R.values() if v))

# set household heads
HEADS = {"HH-0001": R["Dela Cruz,Jose"], "HH-0002": R["Reyes,Mario"],
         "HH-0003": R["Santos,Roberto"], "HH-0004": R["Aquino,Elena"],
         "HH-0005": R["Garcia,Fernando"], "HH-0006": R["Mendoza,Teresita"],
         "HH-0007": R["Bautista,Danilo"], "HH-0008": R["Ramos,Gregorio"],
         "HH-0009": R["Torres,Christopher"], "HH-0010": R["Lim,Benjamin"]}
for hh, rid in HEADS.items():
    if hh in HH and rid:
        req("PATCH", f"/items/bis_households/{HH[hh]}", {"head_resident": rid})

# ---------- document types lookup ----------
DT = {}
for code in ["barangay_clearance", "residency", "indigency", "business_clearance",
             "good_moral", "first_time_jobseeker"]:
    DT[code] = fk("bis_document_types", f"filter%5Bcode%5D%5B_eq%5D={code}")

# ---------- document requests ----------
# (no, resident, code, purpose, req_date, status, issued, or_no, serial)
DOCS = [
    ("REQ-2026-0003", "Reyes,Paolo", "barangay_clearance", "Employment requirement",
     "2026-08-04", "released", "2026-08-04", "OR-1010", "BC-2026-0002"),
    ("REQ-2026-0004", "Santos,Miguel", "indigency", "Scholarship application",
     "2026-08-12", "released", "2026-08-12", "OR-1011", "CI-2026-0001"),
    ("REQ-2026-0005", "Aquino,Elena", "indigency", "Medical assistance (PCSO)",
     "2026-08-19", "released", "2026-08-19", "OR-1012", "CI-2026-0002"),
    ("REQ-2026-0006", "Garcia,Mark", "first_time_jobseeker", "RA 11261 jobseeker cert",
     "2026-08-26", "released", "2026-08-26", "OR-1013", "FTJ-2026-0001"),
    ("REQ-2026-0007", "Ramos,Angelina", "business_clearance", "Sari-sari store renewal",
     "2026-09-02", "released", "2026-09-03", "OR-1020", "BCL-2026-0001"),
    ("REQ-2026-0008", "Lim,Andrea", "barangay_clearance", "Hospital employment",
     "2026-09-05", "released", "2026-09-05", "OR-1021", "BC-2026-0003"),
    ("REQ-2026-0009", "Mendoza,Teresita", "residency", "Senior citizen ID renewal",
     "2026-09-09", "released", "2026-09-09", "OR-1022", "CR-2026-0001"),
    ("REQ-2026-0010", "Torres,Jocelyn", "good_moral", "Visa application",
     "2026-09-15", "released", "2026-09-15", "OR-1023", "GM-2026-0001"),
    ("REQ-2026-0011", "Bautista,Danilo", "residency", "DSWD requirements",
     "2026-09-22", "released", "2026-09-22", "OR-1024", "CR-2026-0002"),
    ("REQ-2026-0012", "Garcia,Fernando", "barangay_clearance", "Project site deployment",
     "2026-10-02", "released", "2026-10-02", "OR-1030", "BC-2026-0004"),
    ("REQ-2026-0013", "Reyes,Luningning", "indigency", "Burial assistance",
     "2026-10-06", "released", "2026-10-06", "OR-1031", "CI-2026-0003"),
    ("REQ-2026-0014", "Lim,Benjamin", "business_clearance", "Hardware store renewal",
     "2026-10-08", "released", "2026-10-09", "OR-1032", "BCL-2026-0002"),
    ("REQ-2026-0015", "Santos,Corazon", "barangay_clearance", "Vendor's permit",
     "2026-10-12", "released", "2026-10-12", "OR-1033", "BC-2026-0005"),
    ("REQ-2026-0016", "Aquino,Katrina", "indigency", "School requirement",
     "2026-10-14", "for_signature", None, "OR-1034", None),
    ("REQ-2026-0017", "Torres,Christopher", "residency", "Passport renewal",
     "2026-10-19", "for_payment", None, None, None),
    ("REQ-2026-0018", "Dela Cruz,Ana", "barangay_clearance", "Bank requirement",
     "2026-10-20", "received", None, None, None),
    ("REQ-2026-0019", "Ramos,Gregorio", "residency", "PWD ID application",
     "2026-10-21", "requirements_check", None, None, None),
]
FEES = {"barangay_clearance": 50, "residency": 50, "indigency": 0,
        "business_clearance": 500, "good_moral": 50, "first_time_jobseeker": 0}
for no, rkey, code, purpose, rd, status, issued, orn, serial in DOCS:
    item = {"request_no": no, "resident": R[rkey], "document_type": DT[code],
            "purpose": purpose, "date_requested": rd + "T09:30:00", "status": status,
            "fee": FEES[code], "signatory": PUNONG}
    if orn:
        item["or_number"] = orn
        item["or_date"] = rd
        item["amount_paid"] = FEES[code]
    if issued:
        from datetime import date, timedelta
        item["issued_date"] = issued
        item["serial_no"] = serial
        d0 = date.fromisoformat(issued)
        item["valid_until"] = (d0 + timedelta(days=365 if code == "first_time_jobseeker"
                                              else 90)).isoformat()
    goc("bis_document_requests", f"filter%5Brequest_no%5D%5B_eq%5D={no}", item)
print("doc requests seeded")

# ---------- me (recorded_by) ----------
s, d = req("GET", "/users/me?fields=id")
ME = (d.get("data") or {}).get("id")

# ---------- blotter ----------
BLOTTERS = [
    # (no, type, loc, status, narrative, parties [(reskey, role)], other, date)
    ("BLT-2026-0002", "noise", "Purok 4 - Kamagong Ave.", "settled",
     "Complaint re: loud barking dogs at night and videoke until 1AM. "
     "Both parties appeared before the tanod and agreed to a 10PM noise curfew.",
     [("Garcia,Fernando", "complainant"), ("Santos,Roberto", "respondent")], None,
     "2026-09-28"),
    ("BLT-2026-0003", "property_damage", "Purok 3 - Hilltop Rd.", "endorsed_to_kp",
     "Respondent's tricycle allegedly backed into complainant's gate, bending the post. "
     "Estimated damage ₱3,500. Parties failed to settle at the desk — endorsed to KP.",
     [("Aquino,Elena", "complainant"), ("Bautista,Danilo", "respondent")], None,
     "2026-10-03"),
    ("BLT-2026-0004", "theft", "Purok 2 - Riverside Ln.", "referred",
     "Complainant reports a stolen bicycle parked outside their dwelling overnight. "
     "Referred to QCPD Station 14 for proper investigation.",
     [("Bautista,Marites", "complainant")], "Suspect unidentified", "2026-10-05"),
    ("BLT-2026-0005", "domestic", "Purok 7 - Narra St.", "closed",
     "Verbal altercation between spouses overheard by neighbors. VAWC desk officer "
     "assessed; parties counseled and case closed at their request.",
     [("Lim,Sharon", "complainant")], None, "2026-10-08"),
    ("BLT-2026-0006", "lost_item", "Purok 1 - Centro", "open",
     "Resident reports losing a wallet containing PhilSys ID and ATM card near the "
     "public market. Entry recorded for reference.",
     [("Santos,Corazon", "complainant")], None, "2026-10-15"),
    ("BLT-2026-0007", "traffic", "Purok 6 - Mahogany Dr.", "open",
     "Minor tricycle-vs-motorcycle sideswipe. No injuries. Parties requested the "
     "incident be recorded pending insurance documentation.",
     [("Ramos,Gregorio", "complainant")], "Motorcycle driver: non-resident, name on file",
     "2026-10-18"),
    ("BLT-2026-0008", "threats", "Purok 5 - Sampaguita St.", "endorsed_to_kp",
     "Complainant alleges respondent threatened her over a disputed property line. "
     "Blotter recorded; KP mediation requested.",
     [("Mendoza,Teresita", "complainant"), ("Lim,Benjamin", "respondent")], None,
     "2026-10-19"),
]
for no, itype, loc, status, narr, parties, other, dt in BLOTTERS:
    bid = goc("bis_blotter", f"filter%5Bblotter_no%5D%5B_eq%5D={no}",
              {"blotter_no": no, "date_reported": dt + "T15:00:00",
               "incident_datetime": dt + "T12:00:00", "location": loc,
               "incident_type": itype, "narrative": narr, "status": status,
               "other_parties": other, "recorded_by": ME,
               "action_taken": "Recorded and acknowledged."})
    if bid and not find("bis_blotter_parties", f"filter%5Bblotter%5D%5B_eq%5D={bid}"):
        for rkey, role in parties:
            create("bis_blotter_parties",
                   {"blotter": bid, "resident": R[rkey], "party_role": role})
print("blotter seeded")

# ---------- KP cases ----------
KPS = [
    ("KP-2026-0002", "BLT-2026-0003", "Aquino,Elena", "Bautista,Danilo",
     "property_dispute", "2026-10-06", "conciliation",
     [("mediation", "2026-10-13T09:00:00", "Barangay Hall", "rescheduled"),
      ("conciliation", "2026-10-27T09:00:00", "Barangay Hall", "pending")]),
    ("KP-2026-0003", "BLT-2026-0008", "Mendoza,Teresita", "Lim,Benjamin",
     "property_dispute", "2026-10-20", "mediation",
     [("mediation", "2026-10-30T10:00:00", "Barangay Hall", "pending")]),
    ("KP-2026-0004", None, "Garcia,Rosalinda", "Santos,Corazon",
     "debt_collection", "2026-09-10", "settled",
     [("mediation", "2026-09-17T09:00:00", "Barangay Hall", "settled")]),
]
for no, blt, comp, resp, ctype, filed, status, hearings in KPS:
    item = {"case_no": no, "complainant": R[comp], "respondent": R[resp],
            "case_type": ctype, "date_filed": filed, "status": status,
            "lupon_member": LUPON}
    if blt:
        item["blotter"] = find("bis_blotter",
                               f"filter%5Bblotter_no%5D%5B_eq%5D={blt}")
    if status == "settled":
        item["settlement_details"] = ("Amicable settlement: respondent to pay ₱2,000 "
                                      "in two installments; parties shook hands.")
        item["settled_at"] = "2026-09-17"
    kid = goc("bis_kp_cases", f"filter%5Bcase_no%5D%5B_eq%5D={no}", item)
    if kid and not find("bis_kp_hearings", f"filter%5Bkp_case%5D%5B_eq%5D={kid}"):
        for ht, sched, venue, out in hearings:
            create("bis_kp_hearings", {"kp_case": kid, "hearing_type": ht,
                                       "scheduled_at": sched, "venue": venue,
                                       "outcome": out})
print("kp seeded")

# ---------- business permits ----------
PERMITS = [
    ("Ramos General Merchandise", "Ramos,Angelina", "sari_sari", "31 Mahogany Dr.",
     "Purok 6", "BP-2026-002", "2026-01-15", "2026-12-31", "active"),
    ("Lim's Hardware & Supply", "Lim,Benjamin", "retail", "5 Narra St.",
     "Purok 7", "BP-2026-003", "2026-01-20", "2026-12-31", "active"),
    ("Santos Eatery", "Santos,Corazon", "eatery", "78 Mabini St.",
     "Purok 1", "BP-2026-004", "2026-02-01", "2026-12-31", "active"),
    ("Jocelyn's Online Shop", "Torres,Jocelyn", "retail", "18 Hilltop Rd.",
     "Purok 3", "BP-2025-011", "2025-01-10", "2025-12-31", "expired"),
    ("Kamagong Internet Cafe", "Garcia,Mark", "services", "9 Kamagong Ave.",
     "Purok 4", "BP-2026-005", "2026-03-01", "2026-12-31", "active"),
]
for name, rkey, btype, addr, pk, pno, issued, until, status in PERMITS:
    goc("bis_business_permits", f"filter%5Bpermit_no%5D%5B_eq%5D={pno}",
        {"business_name": name, "owner_resident": R[rkey], "business_type": btype,
         "address": addr, "purok": P(pk), "permit_no": pno, "date_issued": issued,
         "valid_until": until, "fee": 500, "or_number": "OR-" + pno[-3:],
         "status": status})
print("permits seeded")

# ---------- announcements ----------
ANNS = [
    ("Free Flu Vaccination - Nov 5", "event", "published",
     "2026-10-20T08:00:00", "2026-11-06T00:00:00",
     "<p>Free flu vaccination for senior citizens and PWDs at the Barangay Health "
     "Station, 8AM-12NN. Bring your senior/PWD ID.</p>"),
    ("Road Closure: Mahogany Dr. Nov 8", "advisory", "published",
     "2026-10-21T08:00:00", "2026-11-09T00:00:00",
     "<p>Mahogany Dr. will be closed 6AM-6PM for drainage repairs. "
     "Please use Kamagong Ave. as alternate route.</p>"),
    ("Barangay Ordinance 2026-03: Curfew", "ordinance", "published",
     "2026-10-01T08:00:00", None,
     "<p>Minors are required to be indoors by 10PM unless accompanied by a "
     "guardian. Effective immediately.</p>"),
    ("TUPAD Orientation - Payout Schedule", "livelihood", "published",
     "2026-10-18T08:00:00", "2026-11-30T00:00:00",
     "<p>TUPAD beneficiaries: orientation Nov 3 at the covered court, 1PM. "
     "Bring one valid ID.</p>"),
    ("Typhoon Preparedness Drill", "emergency", "draft",
     "2026-10-25T08:00:00", None,
     "<p>BDRRM evacuation drill tentatively Nov 15. Purok 2 and 7 households "
     "tagged for priority evacuation — checklist to follow.</p>"),
]
for title, cat, status, pub, exp, body in ANNS:
    goc("bis_announcements", f"filter%5Btitle%5D%5B_eq%5D={Q(title)}",
        {"title": title, "category": cat, "status": status, "publish_at": pub,
         "expires_at": exp, "posted_by": ME, "body": body})
print("announcements seeded")
print("done.")
