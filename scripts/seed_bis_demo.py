#!/usr/bin/env python3
"""BIS demo-data generator — procedural, deterministic (random.seed(7)).

Adds volume on top of the hand-seeded data so dashboards look real:
  ~45 households / ~250 residents (rule-based sector tags, voter flags)
  ~80 document requests across Nov 2025-Oct 2026 (growing trend)
  ~20 blotters w/ parties, ~8 KP cases w/ hearings, ~12 permits.

Idempotent: skips bulk gens once count thresholds are reached; named items use
get_or_create on natural keys.
"""
import json, os, random, urllib.request, urllib.error, urllib.parse
from datetime import date, timedelta

BASE = "https://likha-playground.zyberlab.com"
TOKEN = os.environ.get("DIRECTUS_TOKEN", "RBzmMVX7UP9baKtLiHV6RmmTx9s9tmFZ")
HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0"}
Q = urllib.parse.quote
random.seed(7)


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=HDRS)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        print(f"  !! {method} {path} -> {e.code}: {e.read().decode()[:220]}")
        return e.code, {}


def find(col, fq):
    s, d = req("GET", f"/items/{col}?{fq}&fields=id&limit=1")
    return d["data"][0]["id"] if s == 200 and d.get("data") else None


def create(col, item):
    s, d = req("POST", f"/items/{col}", item)
    return (d.get("data") or {}).get("id")


def goc(col, fq, item):
    return find(col, fq) or create(col, item)


def count(col):
    s, d = req("GET", f"/items/{col}?limit=1&meta=total_count")
    return (d.get("meta") or {}).get("total_count", 0)


def bday(min_age, max_age):
    today = date(2026, 10, 21)
    span = (today - date(today.year - max_age, today.month, today.day)).days
    return (today - timedelta(days=random.randint(min_age * 365, span))).isoformat()


# ---------- lookups ----------
s, d = req("GET", "/items/bis_puroks?fields=id,name&limit=-1")
PUROKS = {r["name"]: r["id"] for r in d.get("data", [])}
PORDER = [PUROKS[n] for n in sorted(PUROKS)]                    # purok 1..7
P_W = [3, 7, 5, 4, 3, 4, 6]                                    # pop weights
DT = {}
for r in (req("GET", "/items/bis_document_types?fields=id,code&limit=-1")[1].get("data") or []):
    DT[r["code"]] = r["id"]
s, d = req("GET", "/items/bis_officials?filter%5Bposition%5D%5B_eq%5D=punong_barangay"
           "&filter%5Bstatus%5D%5B_eq%5D=active&fields=id&limit=1")
PUNONG = (d.get("data") or [{}])[0].get("id")
s, d = req("GET", "/items/bis_officials?filter%5Bposition%5D%5B_eq%5D=lupon_member"
           "&filter%5Bstatus%5D%5B_eq%5D=active&fields=id&limit=1")
LUPON = (d.get("data") or [{}])[0].get("id")
s, d = req("GET", "/users/me?fields=id")
ME = (d.get("data") or {}).get("id")

SURNAMES = ("Aguilar Alvarez Bautista Cabrera Castillo Castro Concepcion David Diaz "
            "Domingo Dominguez Espino Estrada Fernandez Flores Fuentes Galang Gutierrez "
            "Hernandez Ilagan Jimenez Lorenzo Magsaysay Mercado Molina Navarro Ocampo "
            "Padilla Pascual Quintana Rivera Robles Salvador Sandoval Santiago Tolentino "
            "Trinidad Valdez Velasco Ventura Villanueva Zamora").split()
MALES = ("Adrian Alvin Angelo Anthony Ariel Benjie Bryan Carlo Cedric Christian Daniel "
         "Darwin Dennis Edgar Eduardo Elijah Eric Felix Francis Gabriel Gerald Gilbert "
         "Ian Jerome Jonathan Jordan Joseph Joshua Kenneth Kevin Leonardo Luis Manuel "
         "Marvin Nathaniel Noel Oliver Patrick Reynaldo Rommel Samuel Vincent Xavier").split()
FEMALES = ("Agnes Aileen Althea Amalia Angela Anita Annabelle Aurora Beatriz Bernadette "
           "Camille Carla Carmen Cecilia Charisse Cheryl Christine Clarissa Daphne Diana "
           "Dolores Edna Eleanor Elizabeth Emmalyn Evelyn Fe Felicia Florencia Genevieve "
           "Gloria Hazel Imelda Irene Jasmine Josephine Kathleen Leonora Lorna Lucia "
           "Maricel Marites Melissa Michelle Nelia Olivia Patricia Pearl").split()

used_names = set()
def new_name(sex):
    for _ in range(60):
        nm = (random.choice(MALES if sex == "male" else FEMALES), random.choice(SURNAMES))
        if nm not in used_names:
            used_names.add(nm)
            return nm
    return (f"{random.choice(MALES if sex=='male' else FEMALES)}{random.randint(2,99)}",
            random.choice(SURNAMES))


def sectors(age, sex, poor, hh_risk):
    tags = []
    if age >= 60: tags.append("senior_citizen")
    if 15 <= age <= 30: tags.append("youth")
    if random.random() < 0.045: tags.append("pwd")
    if poor and random.random() < 0.30: tags.append("four_ps")
    if sex == "female" and 18 <= age <= 40 and random.random() < 0.05:
        tags.append("pregnant_lactating")
    if "informal_settler" in hh_risk: tags.append("informal_settler")
    if "evacuation_priority" in hh_risk and random.random() < 0.6:
        tags.append("evacuation_priority")
    return tags


# ---------- bulk households + residents ----------
TARGET_HH, TARGET_RES = 55, 250
if count("bis_households") >= TARGET_HH and count("bis_residents") >= TARGET_RES:
    print("households+residents already at target — skipping bulk gen")
    R_ALL = [r["id"] for r in req("GET", "/items/bis_residents?fields=id&limit=-1")[1].get("data", [])]
else:
    RES_IDS = []
    hh_i = 11
    while len(RES_IDS) < TARGET_RES - 28:
        no = f"HH-{hh_i:04d}"
        hh_i += 1
        pk = random.choices(range(7), weights=P_W)[0]
        pk_id = PORDER[pk]
        pname = sorted(PUROKS)[pk]
        dwelling = random.choices(
            ["owned", "rented", "rent_free", "informal_settler"],
            weights=[55, 25, 8, 12])[0]
        risk = []
        if "Riverside" in pname or "Narra" in pname:
            risk.append("flood_prone")
            if random.random() < 0.5: risk.append("evacuation_priority")
        if "Hillside" in pname:
            risk.append("landslide_prone")
        if dwelling == "informal_settler":
            risk.append("informal_settler")
        streets = ["Rose", "Lily", "Ilang-Ilang", "Champaca", "Dama de Noche",
                   "Orchids", "Dahlia", "Jasmin", "Kamia", "Rosal"]
        hid = create("bis_households", {
            "household_no": no, "purok": pk_id,
            "address_line": f"{random.randint(1,200)} {random.choice(streets)} St.",
            "dwelling_type": dwelling, "risk_tags": risk})
        if not hid:
            continue
        poor = dwelling in ("informal_settler", "rented")
        # family composition
        head_sex = random.choice(["male", "male", "male", "female"])
        hf, hl = new_name(head_sex)
        head_age = random.randint(30, 62)
        solo = head_sex == "female" and random.random() < 0.3
        head_tags = sectors(head_age, head_sex, poor, risk)
        if solo: head_tags.append("solo_parent")
        def add_res(first, last, sex, b_, civil, role, tags, voter, occ, emp, edu):
            rid = create("bis_residents", {
                "last_name": last, "first_name": first, "sex": sex, "birthdate": b_,
                "civil_status": civil, "citizenship": "Filipino", "household": hid,
                "household_role": role, "purok": pk_id, "sector_tags": tags,
                "registered_voter": voter,
                "precinct_no": f"{random.randint(2300,2399)}-A" if voter else None,
                "occupation": occ, "employment_status": emp,
                "highest_education": edu, "residency_status": "active",
                "residency_start": f"{random.randint(1990,2020)}-{random.randint(1,12):02d}-15",
                "privacy_consent": True})
            if rid: RES_IDS.append(rid)
            return rid
        head_id = add_res(hf, hl, head_sex, bday(head_age, head_age), "widowed" if solo else "married",
                          "head", head_tags, True, "Vendor", "self_employed",
                          random.choice(["elementary", "high_school", "high_school"]))
        if head_id:
            req("PATCH", f"/items/bis_households/{hid}", {"head_resident": head_id})
        if not solo and random.random() < 0.85:  # spouse
            sf, _ = new_name("female" if head_sex == "male" else "male")
            add_res(sf, hl, "female" if head_sex == "male" else "male",
                    bday(head_age - 5, head_age + 3), "married", "spouse",
                    sectors(head_age, "female" if head_sex == "male" else "male", poor, risk),
                    random.random() < 0.8, "Housewife", "unemployed", "high_school")
        for _ in range(random.randint(1, 3)):  # children
            sex = random.choice(["male", "female"])
            cf, _ = new_name(sex)
            c_age = random.randint(4, 24)
            add_res(cf, hl, sex, bday(c_age, c_age + 1), "single", "child",
                    sectors(c_age, sex, poor, risk), c_age >= 18,
                    "Student" if c_age < 20 else None,
                    "student" if c_age < 20 else random.choice(["employed", "unemployed"]),
                    "elementary" if c_age < 13 else "high_school")
        if random.random() < 0.18:  # senior relative
            pf_, pl_ = (hl, hl)
            mf = new_name(random.choice(["male", "female"]))[0]
            s_age = random.randint(62, 82)
            add_res(mf, hl, random.choice(["male", "female"]), bday(s_age, s_age), "widowed",
                    "parent", ["senior_citizen"] + (["evacuation_priority"] if "evacuation_priority" in risk else []),
                    True, None, "retired", "elementary")
    R_ALL = [r["id"] for r in req("GET", "/items/bis_residents?fields=id&limit=-1")[1].get("data", [])]
print("residents:", count("bis_residents"), "| households:", count("bis_households"))

# ---------- document requests: 12-month growing volume ----------
FEES = {"barangay_clearance": 50, "residency": 50, "indigency": 0,
        "business_clearance": 500, "good_moral": 50, "first_time_jobseeker": 0}
DT_W = [("barangay_clearance", 38), ("residency", 20), ("indigency", 16),
        ("good_moral", 12), ("business_clearance", 8), ("first_time_jobseeker", 6)]
PURPOSE = {"barangay_clearance": ["Employment requirement", "Bank requirement",
                                  "Loan application", "Police clearance prerequisite",
                                  "School enrollment", "ID application"],
           "residency": ["Proof of residency", "DSWD requirement", "Passport application",
                         "Voter registration", "PhilHealth requirement"],
           "indigency": ["Medical assistance", "Burial assistance", "Scholarship",
                         "Financial assistance", "Free legal aid"],
           "good_moral": ["Employment", "Visa application", "Travel abroad", "Promotion"],
           "business_clearance": ["Business permit application", "Permit renewal"],
           "first_time_jobseeker": ["RA 11261 first-time jobseeker"]}
PREFIX = {"barangay_clearance": "BC", "residency": "CR", "indigency": "CI",
          "business_clearance": "BCL", "good_moral": "GM", "first_time_jobseeker": "FTJ"}

if count("bis_document_requests") >= 95:
    print("doc requests already at target — skipping")
else:
    MONTHLY = [3, 4, 4, 5, 6, 5, 7, 8, 6, 9, 10, 9]  # Nov'25 .. Oct'26
    seq, or_seq, sr_seq = 100, 2000, 100
    for m_off, n_docs in enumerate(MONTHLY):       # m_off 0 = Nov 2025
        yr = 2025 if m_off < 2 else 2026
        mo = 11 + m_off if m_off < 2 else m_off - 1
        for _ in range(n_docs):
            seq += 1
            day = random.randint(1, 28)
            rd = date(yr, mo, day)
            code = random.choices([c for c, _ in DT_W], weights=[w for _, w in DT_W])[0]
            age_days = (date(2026, 10, 21) - rd).days
            status = (random.choices(["released", "rejected", "cancelled"],
                                     weights=[92, 5, 3])[0] if age_days > 10
                      else random.choice(["received", "requirements_check",
                                          "for_payment", "for_signature", "released"]))
            issued = None
            if status == "released":
                issued = rd + timedelta(days=random.randint(0, 2))
            item = {"request_no": f"REQ-{yr}-{seq:04d}", "resident": random.choice(R_ALL),
                    "document_type": DT[code],
                    "purpose": random.choice(PURPOSE[code]),
                    "date_requested": rd.isoformat() + f"T{random.randint(8,16):02d}:{random.randint(0,59):02d}:00",
                    "status": status, "fee": FEES[code], "signatory": PUNONG}
            if status in ("released", "for_signature"):
                or_seq += 1
                item.update(or_number=f"OR-{or_seq}", or_date=rd.isoformat(),
                            amount_paid=FEES[code])
            if issued:
                sr_seq += 1
                item.update(serial_no=f"{PREFIX[code]}-{yr}-{sr_seq:04d}",
                            issued_date=issued.isoformat(),
                            valid_until=(issued + timedelta(days=365 if code == "first_time_jobseeker" else 90)).isoformat(),
                            released_to="Owner", )
            goc("bis_document_requests",
                f"filter%5Brequest_no%5D%5B_eq%5D=REQ-{yr}-{seq:04d}", item)
print("doc requests:", count("bis_document_requests"))

# ---------- blotter ----------
BTYPES = [("noise", 22), ("property_damage", 14), ("domestic", 14), ("theft", 12),
          ("traffic", 10), ("threats", 10), ("lost_item", 8), ("physical_injury", 6),
          ("other", 4)]
NARR = {
 "noise": "Complaint regarding excessive noise from {x} beyond 10PM curfew.",
 "property_damage": "Damage to property reported — {x}. Estimated cost under dispute.",
 "domestic": "Domestic dispute reported by neighbors; VAWC desk officer assessed on-site.",
 "theft": "Theft incident reported — {x}. Referred for barangay tanod patrol review.",
 "traffic": "Minor vehicular incident along {x}; parties requested blotter for insurance.",
 "threats": "Complainant alleges verbal threats during an argument about {x}.",
 "lost_item": "Resident reports lost {x}; entry recorded for reference and recovery.",
 "physical_injury": "Altercation resulted in minor injuries; parties brought to the hall for blotter.",
 "other": "Incident recorded for documentation purposes — see narrative details on file."}
XFILL = ["karaoke session", "videoke machine", "rowdy gathering",
         "boundary fence", "parked tricycle", "garden wall",
         "mobile phone", "bicycle", "cash proceeds",
         "Main Road corner Sampaguita", "Purok plaza", "public market stall",
         "borrowed tools", "shared water meter", "right-of-way path"]

if count("bis_blotter") >= 26:
    print("blotter already at target — skipping")
else:
    for i in range(18):
        mo = random.randint(6, 10)
        d0 = date(2026, mo, random.randint(1, 28))
        itype = random.choices([t for t, _ in BTYPES], weights=[w for _, w in BTYPES])[0]
        status = random.choices(
            ["open", "endorsed_to_kp", "referred", "settled", "closed"],
            weights=[15, 20, 10, 35, 20])[0]
        bno = f"BLT-2026-{20+i:04d}"
        comp = random.choice(R_ALL)
        resp = random.choice([r for r in R_ALL if r != comp])
        bid = goc("bis_blotter", f"filter%5Bblotter_no%5D%5B_eq%5D={bno}", {
            "blotter_no": bno, "date_reported": d0.isoformat() + "T14:00:00",
            "incident_datetime": d0.isoformat() + "T10:30:00",
            "location": sorted(PUROKS)[random.choices(range(7), weights=P_W)[0]],
            "incident_type": itype,
            "narrative": NARR[itype].format(x=random.choice(XFILL)),
            "status": status, "recorded_by": ME,
            "action_taken": "Recorded, parties summoned." if status != "referred"
                            else "Referred to proper authorities."})
        if bid and not find("bis_blotter_parties", f"filter%5Bblotter%5D%5B_eq%5D={bid}"):
            create("bis_blotter_parties", {"blotter": bid, "resident": comp, "party_role": "complainant"})
            if itype != "lost_item":
                create("bis_blotter_parties", {"blotter": bid, "resident": resp, "party_role": "respondent"})
            if random.random() < 0.35:
                wit = random.choice([r for r in R_ALL if r not in (comp, resp)])
                create("bis_blotter_parties", {"blotter": bid, "resident": wit, "party_role": "witness"})
print("blotter:", count("bis_blotter"))

# ---------- KP cases ----------
if count("bis_kp_cases") >= 12:
    print("kp already at target — skipping")
else:
    endorsed = [r["id"] for r in req(
        "GET", "/items/bis_blotter?filter%5Bstatus%5D%5B_eq%5D=endorsed_to_kp&fields=id&limit=-1")[1].get("data", [])]
    ctypes = ["property_dispute", "neighborhood", "debt_collection", "family_dispute", "other"]
    kstatuses = ["mediation", "conciliation", "settled", "cfa_issued", "arbitration", "dismissed"]
    for i in range(8):
        cno = f"KP-2026-{10+i:04d}"
        kst = kstatuses[i % len(kstatuses)]
        filed = date(2026, random.randint(8, 10), random.randint(1, 28))
        item = {"case_no": cno, "complainant": random.choice(R_ALL),
                "respondent": random.choice(R_ALL),
                "case_type": random.choice(ctypes), "date_filed": filed.isoformat(),
                "status": kst, "lupon_member": LUPON}
        if i < len(endorsed):
            item["blotter"] = endorsed[i]
        if kst == "settled":
            item["settlement_details"] = "Parties reached an amicable settlement before the Pangkat."
            item["settled_at"] = (filed + timedelta(days=21)).isoformat()
        if kst == "cfa_issued":
            item["cfa_issued_at"] = (filed + timedelta(days=30)).isoformat()
            item["cfa_reason"] = "Respondent failed to appear in two scheduled hearings."
        kid = goc("bis_kp_cases", f"filter%5Bcase_no%5D%5B_eq%5D={cno}", item)
        if kid and not find("bis_kp_hearings", f"filter%5Bkp_case%5D%5B_eq%5D={kid}"):
            h1 = filed + timedelta(days=14)
            create("bis_kp_hearings", {"kp_case": kid, "hearing_type": "mediation",
                   "scheduled_at": h1.isoformat() + "T09:00:00", "venue": "Barangay Hall",
                   "outcome": "settled" if kst == "settled" else
                              "no_appearance" if kst == "cfa_issued" else "rescheduled"})
            if kst in ("conciliation", "arbitration", "cfa_issued"):
                create("bis_kp_hearings", {"kp_case": kid,
                       "hearing_type": "conciliation",
                       "scheduled_at": (h1 + timedelta(days=14)).isoformat() + "T09:00:00",
                       "venue": "Barangay Hall",
                       "outcome": "no_appearance" if kst == "cfa_issued" else "pending"})
print("kp:", count("bis_kp_cases"))

# ---------- permits ----------
BIZ = ["Aling Nena's Sari-Sari", "RJ Computer Shop", "Kape Purok", "Lola's Carinderia",
       "Triple J Auto Repair", "Mang Domeng Barbershop", "Sto. Niño Bakery",
       "Kumare's Salon", "Bert's Water Refilling", "Pinoy Pawnshop Outlet",
       "Kambal Pandesal", "Emer Laundry Services"]
if count("bis_business_permits") >= 18:
    print("permits already at target — skipping")
else:
    for i, name in enumerate(BIZ):
        pno = f"BP-2026-{10+i:03d}"
        issued = date(2026, random.randint(1, 9), random.randint(1, 28))
        goc("bis_business_permits", f"filter%5Bpermit_no%5D%5B_eq%5D={pno}", {
            "business_name": name, "owner_resident": random.choice(R_ALL),
            "business_type": random.choice(["sari_sari", "eatery", "services", "retail", "other"]),
            "address": f"{random.randint(1,200)} {random.choice(['Rose','Mahogany','Narra'])} St.",
            "purok": PORDER[random.choices(range(7), weights=P_W)[0]],
            "permit_no": pno, "date_issued": issued.isoformat(),
            "valid_until": "2026-12-31", "fee": 500,
            "or_number": f"OR-{3000+i}", "status": "active"})
print("permits:", count("bis_business_permits"))
print("done.")
