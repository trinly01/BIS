# BIS Data Model — Directus Implementation Plan

Instance: `https://likha-playground.zyberlab.com` (Directus 11.17.4, shared playground).
Every artifact prefixed `bis_`. Mirrors the `easypc_` layout: top group folder → sub-folders → collections.

## Navigation structure

```
BIS                       (group folder)
├── bis_master_data       (group folder)
│   ├── bis_settings      (singleton)
│   ├── bis_puroks
│   ├── bis_officials
│   └── bis_document_types
├── bis_registry          (group folder)
│   ├── bis_households
│   └── bis_residents
└── bis_operations        (group folder)
    ├── bis_document_requests
    ├── bis_blotter
    ├── bis_blotter_parties
    ├── bis_blotter_attachments
    ├── bis_kp_cases
    ├── bis_kp_hearings
    ├── bis_business_permits
    └── bis_announcements
```

All entity collections: `accountability: all` (user_created/user_updated/date_created/date_updated)
+ manual M2O relations to `directus_users` (skill rule 9 — audit relations are NOT auto-created).

## Collections

### bis_settings (singleton)
`barangay_name, city_municipality, province, region, punong_barangay, secretary_name,
treasurer_name, logo→directus_files, doc_header (richtext), doc_footer, contact_number, email`

### bis_puroks
`name*, description, risk_level (low/moderate/high), notes`,
geo: `location` (Point centroid, map), `boundary` (MultiPolygon, map)
O2M out: households, residents, business_permits. Print: `bis_purok_roster`.

### bis_officials
`resident→bis_residents (optional link), name*, position (punong_barangay/kagawad/sk_chairperson/
secretary/treasurer/tanod/lupon_member/other), committee, term_start, term_end, sort_order,
is_signatory, signatory_label, status (active/inactive), photo→directus_files, contact_number`

### bis_document_types
Configurable issuance catalog (one row per certificate/clearance):
`name*, code* (barangay_clearance/residency/indigency/business_clearance/good_moral/
first_time_jobseeker/custom), fee, validity_days, sla_days (ARTA), requirements (text),
status (active/inactive), template (richtext body), notes`

### bis_households
Tabs — **Details**: `household_no*, purok→bis_puroks, address_line, dwelling_type
(owned/rented/rent_free/informal_settler), risk_tags (csv checkboxes: flood_prone/
landslide_prone/storm_surge/evacuation_priority), head_resident→bis_residents,
location (Point, map)`
**Members**: `members` O2M → bis_residents (household FK) · **Notes**: `notes`

### bis_residents — flagship, 5 tabs
- **Identity**: `last_name*, first_name*, middle_name, suffix, sex*, birthdate*, place_of_birth,
  civil_status*, citizenship (default Filipino), photo→directus_files`
- **Contact & Household**: `contact_number, email, address_line, purok→bis_puroks,
  household→bis_households, household_role (head/spouse/child/parent/sibling/relative/other),
  emergency_contact_name, emergency_contact_phone`
- **Residency**: `residency_start, residency_status (active/moved_out/deceased),
  registered_voter, precinct_no, philsys_id, field_point (Point, map — field-verified)`
- **Sectors & Livelihood**: `occupation, employment_status (employed/self_employed/unemployed/
  student/retired/ofw), highest_education, sector_tags (csv checkboxes: senior_citizen/pwd/
  solo_parent/youth/pregnant_lactating/four_ps/indigenous/informal_settler/evacuation_priority)`
- **Records**: `document_requests`, `blotter_involvements`, `kp_cases_as_complainant`,
  `kp_cases_as_respondent`, `business_permits`, `official_posts` (O2M aliases),
  `privacy_consent, consent_date, notes`, `print` (barangay ID)

### bis_document_requests — 4 tabs
- **Request**: `request_no, resident→bis_residents*, document_type→bis_document_types*,
  purpose, date_requested, settings→bis_settings (hidden, flow-stamped), status
  (received/requirements_check/for_payment/for_signature/released/rejected/cancelled)`
- **Payment**: `fee, or_number, or_date, amount_paid, processed_by→directus_users`
- **Release**: `serial_no, issued_date, valid_until, signatory→bis_officials, released_to,
  released_by→directus_users`
- **Notes**: `remarks`

### bis_blotter — 3 tabs
- **Incident**: `blotter_no, date_reported*, incident_datetime, location, incident_type
  (theft/physical_injury/threats/property_damage/noise/domestic/lost_item/traffic/other),
  incident_point (Point, map), narrative, status (open/endorsed_to_kp/referred/settled/closed)`
- **Parties**: `parties` O2M → bis_blotter_parties (junction w/ payload), `other_parties`
- **Action Taken**: `action_taken, referred_to, referred_at, kp_case→bis_kp_cases,
  recorded_by→directus_users`, `attachments` O2M → bis_blotter_attachments

### bis_blotter_parties (O2M junction, hidden in nav optional)
`blotter→bis_blotter*, resident→bis_residents*, party_role (complainant/respondent/witness),
statement, contact_number`

### bis_blotter_attachments
`blotter→bis_blotter*, file→directus_files, title`

### bis_kp_cases — 3 tabs (Katarungang Pambarangay)
- **Case**: `case_no, blotter→bis_blotter, complainant→bis_residents + complainant_name
  (text for non-residents), respondent→bis_residents + respondent_name, case_type
  (debt_collection/property_dispute/family_dispute/neighborhood/physical_injury/other),
  date_filed, status (filed/summons_issued/mediation/conciliation/arbitration/settled/
  cfa_issued/dismissed)`
- **Hearings**: `hearings` O2M → bis_kp_hearings
- **Resolution**: `settlement_details, settled_at, cfa_issued_at, cfa_reason,
  lupon_member→bis_officials, remarks`, `print_settlement`, `print_cfa` (alias fields)

### bis_kp_hearings
`kp_case→bis_kp_cases*, hearing_type (mediation/conciliation/arbitration), scheduled_at*,
venue, outcome (pending/settled/rescheduled/no_appearance/escalated), notes`

### bis_business_permits
`business_name*, owner_resident→bis_residents, owner_name, business_type
(sari_sari/eatery/services/retail/other), address, purok→bis_puroks, permit_no,
date_issued, valid_until, fee, or_number, status (active/expired/revoked), remarks,
location (Point, map)`. Print: `bis_business_permit`.

### bis_announcements
`title*, body (richtext), category (advisory/event/emergency/ordinance/livelihood/other),
publish_at, expires_at, pinned, status (draft/published/archived), posted_by→directus_users`

## Key relationships

| From | Field | To | Reverse alias (one_field) |
|---|---|---|---|
| bis_residents | household | bis_households | `members` |
| bis_residents | purok | bis_puroks | `residents` |
| bis_households | purok | bis_puroks | `households` |
| bis_households | head_resident | bis_residents | — (null) |
| bis_residents/officials | photo | directus_files | — |
| bis_officials | resident | bis_residents | `official_posts` |
| bis_document_requests | resident | bis_residents | `document_requests` |
| bis_document_requests | document_type | bis_document_types | `requests` |
| bis_document_requests | signatory | bis_officials | `signed_documents` |
| bis_document_requests | processed_by/released_by | directus_users | — |
| bis_blotter_parties | blotter | bis_blotter | `parties` |
| bis_blotter_parties | resident | bis_residents | `blotter_involvements` |
| bis_blotter_attachments | blotter | bis_blotter | `attachments` |
| bis_blotter_attachments | file | directus_files | — |
| bis_blotter | kp_case | bis_kp_cases | `blotters` |
| bis_blotter | recorded_by | directus_users | — |
| bis_kp_cases | blotter | bis_blotter | `kp_cases` |
| bis_kp_cases | complainant/respondent | bis_residents | `kp_cases_as_complainant` / `_respondent` |
| bis_kp_cases | lupon_member | bis_officials | `kp_cases_handled` |
| bis_kp_hearings | kp_case | bis_kp_cases | `hearings` |
| bis_business_permits | owner_resident | bis_residents | `business_permits` |
| bis_business_permits | purok | bis_puroks | `business_permits` |
| bis_announcements | posted_by | directus_users | — |
| bis_settings | logo | directus_files | — |
| *every collection* | user_created/user_updated | directus_users | — |

Tab pattern (native, verified on easypc): `grp_tabs` alias w/ `interface: group-tabs`;
`grp_*` aliases w/ `interface: group-raw`, `meta.group=grp_tabs`, `meta.translations` labels;
children carry `meta.group=grp_*`.

## As-built additions (Phase 2, 2026-10-21)

**`settings` M2O → `bis_settings` on all 7 printable collections**
(bis_document_requests, bis_business_permits, bis_residents, bis_kp_cases, bis_blotter,
bis_puroks, bis_announcements) — hidden, readonly, stamped by event flow
`bis_stamp_settings` (items.create → item-update `settings=<singleton id>`,
`emitEvents:false`). Powers template letterheads.

**Print** — `print_template` rows (LiquidJS) + `print`-interface alias fields:
`bis_barangay_certificate`, `bis_blotter_extract`, `bis_kp_hearing_notice`,
`bis_business_permit`, `bis_barangay_id`, `bis_purok_roster`, `bis_posting`,
`bis_kp_amicable_settlement` (KF-16), `bis_kp_cert_to_file_action` (KF-18). See
README print-coverage table for field placement.

**Insights "BIS Dashboard"** — 6 metric panels + 5 `echarts-panel`s, each backed by a
webhook flow `bis_chart_*` (`likha_sql` → `exec` returning the option object):
residents/purok, docs-by-type, blotter-by-type, residents-by-sector, issuance trend.
Plus 3 `likhaHeatmap-panel` (type `likhaHeatmap-panel`) map panels — collection-driven
(`options.collection` + `geoField` + `filter` + `popupFields`, no flow): blotter
incident points, household locations, resident field-points; San Fabian center
`[120.4156, 16.1324]`, clustering + popups enabled.

**Field config** — O2M aliases use `options.fields` column lists + `sortField`
(+enableLink/Create/Select); M2O pickers have `options.template` display labels;
`bis_blotter_parties` + `bis_blotter_attachments` hidden from nav (`meta.hidden`).

**Geo** — `geometry.Point`: `bis_puroks.location`, `bis_households.location`,
`bis_blotter.incident_point`, `bis_business_permits.location`,
`bis_residents.field_point` (vulnerable residents only); `geometry.MultiPolygon`:
`bis_puroks.boundary`. All `map` interface, OSM basemap.

**Junction collections** (nav-hidden, edited via parent tabs): `bis_blotter_parties`,
`bis_blotter_attachments`.

## Phase 3 (remaining)
Roles/policies (bis_secretary, bis_staff, bis_captain) w/ permission presets;
serial-number flows (DOC-/BLT-/KP-YYYY-NNNN); SLA due-date stamping; resident-facing
request portal + QR verification endpoint; SMS alerts; dashboard map panel
(echarts geo scatter via `ST_AsGeoJSON`).
