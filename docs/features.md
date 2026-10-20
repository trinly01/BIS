# Barangay Information System — Market Research & Feature Ranking

Sources reviewed (Oct 2026): DILG LGUSS-BIMS (official, free), OneBarangay, BMIS (barangay.info),
Dynite IBIS, Odoo BMIS module, ERPat functional spec, various capstone/open-source BMS projects.

## What providers ship

| Provider | Notable modules |
|---|---|
| DILG BIMS | Resident profiling, issuance mgmt, Katarungang Pambarangay (KP), property mgmt, disaster preparedness, GAD plan & budget, NGA reports, custom website |
| OneBarangay | Resident records, docs with **QR verification**, KP case tracking w/ hearing schedules, blotter, **official receipts + daily cashier balancing**, online requests 24/7, PAGASA flood alerts, self-serve doc templates |
| BMIS | Resident registry + beneficiary status, certificate workflow (review/approve/print/release), announcements, messaging, officials, per-barangay isolation, roles |
| Dynite IBIS | 15 certificate/clearance types, judicial (blotter, invitation, summon, agreement), household profile w/ **Resident ID + QR**, dwelling/health/water-sanitation/agri/BDRRM data, offline+online |
| Odoo BMIS | Resident mgmt, permits & clearances w/ payment integration, case mgmt w/ hearings, project mgmt, import/export |
| ERPat spec | RBI registry (purok risk tags, sector tags, residency engine, duplicate detection, DILG-aligned export), configurable doc types w/ per-type fee/SLA/validity (ARTA RA 11032), SHA-256 + QR doc verification, First-Time Jobseeker (RA 11261) rules, business clearance (LGC 152c) |

## Features ranked by value

### Tier 1 — core daily transactions (must have)
1. **Resident registry / profiling (RBI)** — foundation for every other module; demographics, sector tags (senior/PWD/solo parent/4Ps/voter), residency history, duplicate detection.
2. **Households + purok/sitio master list** — residents roll up to households → puroks; required for RBI reports and disaster planning.
3. **Certificate & clearance issuance** — the #1 counter transaction: barangay clearance, certificate of residency, indigency, business clearance, good moral, first-time jobseeker. Needs request → fee/OR → sign → release workflow, serial numbers, per-type fee/validity config.
4. **Blotter / incident log** — legal-grade incident recording (complainant/respondent/witness, narrative, action taken, referrals); feeds KP.
5. **Barangay officials directory** — positions, terms, signatories used on every issued document.

### Tier 2 — high value, standard in paid products
6. **KP case management** — mediation → conciliation → arbitration stages, hearing schedules, Certificate to File Action; legally mandated process, big time-saver.
7. **Fees & collections** — fee per doc type, OR numbers, amount paid; daily collection report / cashier balancing.
8. **Document templates + print + QR verification** — reusable templates, serial + QR so agencies can verify authenticity (OneBarangay's headline feature).
9. **Business permits / clearances registry** — renewal tracking, expiry.

### Tier 3 — differentiating
10. **Announcements / advisories** — publish community notices, emergencies, ordinances.
11. **Reports & statistics** — population by purok/sector/age, issuance counts, blotter stats, DILG/NGA report exports.
12. **Disaster preparedness (BDRRM)** — risk-tagged puroks/households, evacuation priority lists.
13. **Online resident request portal** — requests 24/7 without a trip to the hall (needs a frontend on top of Directus).

### Tier 4 — advanced / later phases
14. Property/asset management, GAD plan & budget, project tracking, SMS/PAGASA integrations, custom public website.

## What we implement on Directus (phases)

- **Phase 1 (this build):** Tiers 1–2 minus print templates — registry (puroks, households, residents w/ tabs & sector tags), officials, document types, document requests w/ OR fields, blotter w/ parties + attachments, KP cases + hearings, business permits, announcements, settings singleton.
- **Phase 2:** roles/policies (secretary/staff/captain), flows (auto serial numbers, SLA due-date stamping, status milestones), print templates (`print` interface + `print_template` rows), dashboards.
- **Phase 3:** resident-facing request portal, QR verification endpoint, SMS alerts.
