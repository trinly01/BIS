# BIS — Barangay Information System (Directus)

A barangay (Philippine village-level LGU) information system built as a Directus
schema on `https://likha-playground.zyberlab.com` (project "LikhaERP", Directus 11.17.4).

## Docs

- `docs/features.md` — market research (DILG BIMS, OneBarangay, BMIS, Dynite IBIS, Odoo, ERPat)
  and features ranked by value (tiers 1–4).
- `docs/data-model.md` — full schema plan: collections, tab layouts, relations, nav grouping.

## What was built (2026-10-21)

Nav: `BIS` group folder → `bis_master_data` / `bis_registry` / `bis_operations` sub-folders.

| Collection | Purpose | Tabs |
|---|---|---|
| `bis_settings` | Singleton: barangay profile, signatories, doc header/footer | — |
| `bis_puroks` | Purok/sitio master list w/ risk level | — |
| `bis_officials` | Officials, terms, signatories | — |
| `bis_document_types` | Configurable certificate types (fee, SLA, validity, template) | — |
| `bis_households` | Households w/ head, dwelling, risk tags | Details / Members / Notes |
| `bis_residents` | Resident registry (RBI): demographics, sectors, voter, PhilSys | Identity / Contact & Household / Residency / Sectors / Records |
| `bis_document_requests` | Certificate issuance workflow w/ OR + signatory | Request / Payment / Release / Notes |
| `bis_blotter` | Incident blotter | Incident / Parties / Action Taken |
| `bis_blotter_parties` | Junction w/ role payload (complainant/respondent/witness) | — |
| `bis_blotter_attachments` | File attachments | — |
| `bis_kp_cases` | Katarungang Pambarangay cases (mediation→arbitration, CFA) | Case / Hearings / Resolution |
| `bis_kp_hearings` | KP hearing schedules + outcomes | — |
| `bis_business_permits` | Business permit registry w/ expiry | — |
| `bis_announcements` | Advisories/events/emergencies | — |

All collections: UUID PK, `accountability: all`, audit fields wired to `directus_users`.

## Scripts (all idempotent, re-run safe)

| Script | Purpose |
|---|---|
| `build_bis_schema.py` | Schema builder: folders, 14 collections, fields, tab groups, relations, alias interfaces, audit fields+relations |
| `build_bis_phase2.py` | `settings` M2O + stamp flow, 3 base print templates + print fields, BIS Dashboard (6 metrics + 5 echarts flows/panels) |
| `build_bis_prints.py` | 6 more print templates + fields, `settings` M2O on all 7 printables, stamp-flow scope extension |
| `enhance_bis_fields.py` | list-o2m `fields` table views + sort, M2O picker templates, junction nav hiding |
| `build_bis_geo.py` | geometry fields + synthesized coordinates (puroks, households, blotters, permits, vulnerable residents) |
| `build_bis_heatmap.py` | 3 `likhaHeatmap-panel`s on the dashboard: incident, household/risk density, vulnerable-resident maps |
| `seed_smoke_test.py` | reference data + relational smoke test |
| `seed_bis_data.py` | hand-crafted realistic data (officials roster, named households/residents) |
| `seed_bis_demo.py` | procedural demo volume (~250 residents, 95 requests, count-guarded) |

Auth: admin bearer token via env `DIRECTUS_TOKEN` (never commit). All writes need
`User-Agent: curl/8.5.0` — see `.devin/skills/directus-api/SKILL.md`.

## Phase 2 — built 2026-10-21 (`scripts/build_bis_phase2.py`)

**Print templates** (`print_template` rows, LiquidJS HTML):
- `bis_barangay_certificate` — generic official certificate; `{% case document_type.code %}`
  renders tailored wording for indigency/residency/business clearance/good moral/
  first-time jobseeker (RA 11261)/generic clearance. Letterhead comes from
  `settings` M2O → `bis_settings` singleton.
- `bis_blotter_extract` — incident record w/ parties table (role/contact/statement).
- `bis_kp_hearing_notice` — KP summons w/ hearing schedule table + receipt signature.

`print` alias fields added: `bis_document_requests.print` (Release tab),
`bis_blotter.print` (Action tab), `bis_kp_cases.print` (Case tab).

### Print coverage (`scripts/build_bis_prints.py`)

| Collection | Field | Template | Output |
|---|---|---|---|
| `bis_document_requests` | `print` | `bis_barangay_certificate` | Official certificate (per doc-type wording) |
| `bis_business_permits` | `print` | `bis_business_permit` | Permit to Operate (LGC 152c) |
| `bis_blotter` | `print` | `bis_blotter_extract` | Incident record extract |
| `bis_kp_cases` | `print` | `bis_kp_hearing_notice` | Summons / notice of hearing |
| `bis_kp_cases` | `print_settlement` | `bis_kp_amicable_settlement` | KP Form 16-style settlement |
| `bis_kp_cases` | `print_cfa` | `bis_kp_cert_to_file_action` | Certification to File Action |
| `bis_residents` | `print` | `bis_barangay_id` | CR80-size barangay ID card |
| `bis_puroks` | `print` | `bis_purok_roster` | Certified resident roster (RBI) |
| `bis_announcements` | `print` | `bis_posting` | Public posting copy |

All printable collections carry a hidden `settings` M2O → `bis_settings` singleton
(letterhead); `bis_stamp_settings` stamps it on create for all seven.

**Settings stamping:** `bis_stamp_settings` event flow (items.create on
`bis_document_requests`) auto-sets `settings` → singleton so certificates always
render the letterhead. Existing rows backfilled.

**Insights — "BIS Dashboard"**: 6 metric panels (active residents, households,
certificates issued, open blotter, active KP, active permits) + 5 echarts panels
powered by webhook flows (`likha_sql` → `exec` returning an ECharts option):
residents per purok (bar), docs issued by type (donut), blotter by incident type
(horizontal bar), residents by sector (donut), monthly issuance trend (line).
Verify any chart: `GET /flows/trigger/<flow-id>` returns the option JSON.

+ 3 `likhaHeatmap-panel` map panels (`scripts/build_bis_heatmap.py`) — collection-driven,
no flows: **Incident Heatmap** (`bis_blotter.incident_point`, coolwarm), **Household &
Risk Density** (`bis_households.location`, viridis), **Vulnerable Residents**
(`bis_residents.field_point`, plasma). All centered on San Fabian w/ clustering +
click popups (nested popup fields like `purok.name`). Note: the panel's options drawer
crashes in the UI — configure via `PATCH /panels/{id}` (script does this).

**Field polish** (`scripts/enhance_bis_fields.py`): all O2M aliases use table-style
`options.fields` column lists + `sortField` + `enableLink/Create/Select`; all M2O pickers
have display `options.template` (e.g. residents render "Last, First"); junction-ish
collections (`bis_blotter_parties`, `bis_blotter_attachments`) hidden from nav — edit them
through the parent's tab.

**Seeds**: `scripts/seed_bis_data.py` (hand-crafted reference data) +
`scripts/seed_bis_demo.py` (procedural demo volume, `random.seed(7)`, count-guarded):
**Barangay Poblacion, San Fabian, Pangasinan** — 7 puroks, full sanggunian + lupon, 68 households,
**251 residents** w/ rule-based sector tags (65 youth, 35 evacuation-priority,
27 seniors, 24 4Ps, 22 informal settlers, 11 PWD…), **95 document requests across
Nov 2025–Oct 2026** w/ growth trend (92% released, OR + serial + validity filled),
26 blotters w/ parties, 12 KP cases w/ hearings, 18 permits, 6 announcements.

**Geo-tagging** (`scripts/build_bis_geo.py`): `bis_puroks.location` (Point centroid)
+ `boundary` (MultiPolygon), `bis_households.location`, `bis_blotter.incident_point`,
`bis_business_permits.location` — all `map` interface (OpenStreetMap basemap, default
view centered on San Fabian town proper ~16.13N 120.41E). Demo coordinates synthesized;
replace with surveyed pins. Blotter `incident_point` is derived from the `location`
text → purok.

Person-level geo is two-tier by design: the **household pin is canonical** (residents
resolve `household.location` — one pin per dwelling), while `bis_residents.field_point`
(Residency tab) is an optional field-verified point for vulnerable residents —
seeded for 64 seniors/PWD/evacuation-priority/pregnant residents, jittered ~40m from
their household pin. That's the set BDRRM needs at response time.

## Phase 3 (next)

Roles/policies (`bis_secretary`, `bis_staff`, `bis_captain`) with permission presets;
serial-number flows (DOC-/BLT-/KP-YYYY-NNNN); SLA due-date stamping per doc type;
resident-facing request portal + QR verification endpoint; SMS alerts.
