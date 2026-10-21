# Directus API — likha-playground (EasyPC + BIS)

Project skill for working with the shared likha-playground Directus instance. Read before any Directus API work.

## Instance

- URL: `https://likha-playground.zyberlab.com` — Directus **11.17.4**, project "LikhaERP"
- **Shared playground**: 100+ collections belonging to other projects. NEVER touch anything not prefixed `easypc_`. Every artifact we create (collections, junctions, flows, roles, policies) is prefixed `easypc_`.
- Token: admin bearer token provided by user (kept in env var `DIRECTUS_TOKEN`, never committed).

## Hard-won rules (each one came from a real failure)

1. **Cloudflare blocks non-curl user agents.** Default `Python-urllib/*` and spoofed browser UAs get `403 error code: 1010` on writes. Always send `User-Agent: curl/8.5.0` (urllib/requests) or use `curl` directly. GETs are unaffected.
2. **NEVER PATCH `/relations` — it crashes this server.** Any `PATCH /relations/{collection}/{field}` (even correct, verified) enters `RelationsService.alterType` → `schema.collections[...].fields` → TypeError → process crash; nodemon does NOT auto-restart (needs `rs`). POST /relations is safe. To change relation behavior post-creation, use SQL directly (see below) or recreate the relation.
3. **Missing-field GETs return 403, not 404.** `GET /fields/{col}/{missing}` → 403 FORBIDDEN, so don't treat non-200 as "doesn't exist". For existence checks list `/fields/{col}` and search, or just POST and tolerate 400.
4. **M2M junction deletes**: `one_deselect_action` can't be PATCHed (rule 2). Options: (a) delete junction rows before the parent, or (b) DB-level cascade + meta fix via SQL:
   ```sql
   ALTER TABLE easypc_work_orders_services DROP CONSTRAINT easypc_work_orders_services_easypc_work_orders_id_foreign,
     ADD CONSTRAINT easypc_work_orders_services_easypc_work_orders_id_foreign FOREIGN KEY (easypc_work_orders_id) REFERENCES easypc_work_orders(id) ON DELETE CASCADE;
   ALTER TABLE easypc_work_orders_files DROP CONSTRAINT easypc_work_orders_files_easypc_work_orders_id_foreign,
     ADD CONSTRAINT easypc_work_orders_files_easypc_work_orders_id_foreign FOREIGN KEY (easypc_work_orders_id) REFERENCES easypc_work_orders(id) ON DELETE CASCADE;
   UPDATE directus_relations SET one_deselect_action='delete'
     WHERE many_collection IN ('easypc_work_orders_services','easypc_work_orders_files') AND many_field='easypc_work_orders_id';
   ```
5. **URL-encode filter params.** `?filter[key][_eq]=x` with raw brackets intermittently fails through the proxy; always encode (`filter%5Bkey%5D%5B_eq%5D`).
6. **Reverse O2M aliases are created by `meta.one_field`** on the relation POST — then PATCH `/fields/{col}/{alias}` to set `interface: list-o2m`, options template, and `group` for tab placement. M2M needs `junction_field` on the junction→parent relation + patch the alias to `interface: list-m2m` / `files`.
7. **group-tabs is native** (≥11.17.1). Group fields are `type: alias`, `special: ["alias","group","no-data"]`; children point at parent via `meta.group`. Set `meta.translations` for tab labels.
8. **Multi-branch is implemented.** `directus_users.easypc_store` (M2O → `easypc_stores`) assigns each staff user a branch; `easypc_front_desk`/`easypc_technician` permissions filter `easypc_work_orders` to `$CURRENT_USER.easypc_store` (children via `work_order.store`, junctions via `easypc_work_orders_id.store`); front-desk creates preset `store` to their branch. `easypc_manager` is unfiltered — sees all branches.
9. **Audit fields+relations are NOT auto-created.** Setting `meta.accountability:"all"` (on collection POST or PATCH) does NOT create `user_created`/`date_created`/`user_updated`/`date_updated` — confirmed 2026-10-21 building BIS: meta said `all`, zero fields existed. Create them explicitly as fields (uuid/timestamp, specials `user-created`/`date-created`/`user-updated`/`date-updated`, readonly+hidden), then POST the two M2O relations to `directus_users` — otherwise the field stores a UUID it can't resolve ("relationship not configured").
10. **Junction FK fields must not be `hidden`** — hiding `easypc_work_orders_id`/`easypc_services_id`/`directus_files_id` breaks the `list-m2m`/`files` interface ("relationship not configured" error).
11. **`$CURRENT_USER` is NOT a valid `schema.default_value`** (500 invalid uuid). Default-to-logged-in-user goes in permission **presets**: `presets: {"created_by": "$CURRENT_USER"}` on each role's create permission. Done for created_by/recorded_by/done_by/tested_by/received_by (+ `store` on WOs). `$CURRENT_USER.easypc_store` works in presets/filters too.
12. **`easypc_work_order_updates` is append-only** for front_desk/technician (update+delete perms removed; manager keeps all). `created_by` is readonly+preset; `notification_sent_at` readonly (flow-stamped after send, blank = pending).
13. **`condition` flow op silently fails here — gate inside `exec` instead.** An op that `throw`s routes to `reject` (null) and stops the chain cleanly; verified working. Also: operation `resolve`/`reject` are **unique** — two ops can't resolve to the same target; clear the existing link first. `$trigger` shape for items.update = `{payload: {changedFields}, keys: [ids], collection, event}` — `payload` is NOT double-nested.
14. **Collection folders**: `EasyPC` is a group folder (collection with `schema: null`); membership = `PATCH /collections/{name} meta.group="EasyPC"`. All 13 `easypc_*` collections are inside it.
15. **Working flows** (`scripts/build_flows.py`): `easypc_generate_wo_number` (verified: auto WO-YYYY-NNNN on create), `easypc_status_milestone` (verified), `easypc_warranty_stamp` (verified: +30d on released), `easypc_notify_on_update` (mail op needs `EMAIL_*` env on server — untested), `easypc_unclaimed_reminder` (disabled placeholder).
17. **Bash `$` expansion corrupts flow options.** `python -c "... $last ..."` inside double quotes silently strips `$trigger`/`$last`/`$full` → stored as `data. || {}`, `{{.key}}`, `permissions:""` → flow silently dies. ALWAYS write/patch ops containing `$` tokens via a script file (see `scripts/fix_warranty_flow.py`), never inline `python -c "..."`. Verify stored options after patching.
18. **`item-update` op `key` field**: use literal or `{{$last.key}}`/`{{$trigger.keys[0]}}` — both resolve here. Always set `emitEvents: false` on ops that write back to the trigger collection (every working op on this instance does; prevents self-trigger loops).
19. **Print field interface is `print`, not `likha-print-template`** — `procurement_plan.print` uses the legacy name; the UI picker registers `print`. Options shape: `{templateSelection: {collection: "print_template", key: "<template-row-uuid>"}, fields: ["*.*.*"]}`. Templates (`print_template` rows) are LiquidJS HTML; `scripts/easypc_work_order_form.liquid` = local source of `easypc_work_order_form` (id 3f63e917-44de-4dbe-ae08-cd58617ba9da). Terminal output can clip UUIDs — always re-fetch real ids by name before writing them into options.
20. **`likha_sql` custom op exists** — runs raw SQL server-side (`options.sql`, multi-statement OK). The sanctioned way to change things the crashing `/relations` PATCH can't (junction_field, deselect actions, FK cascades). Fire it via a **webhook-triggered** flow + `POST /flows/trigger/{id}` — `manual` trigger 403s via API. Used to fix M2M `junction_field` on both junction relations (both sides must point at each other's field — missing second side = "relationship not configured" in app) + `ON DELETE CASCADE`. `POST /utils/cache/clear {"cache":"system"}` refreshes schema after direct-DB changes.

## What exists (built 2026-10-17, script: `scripts/build_schema.py`)

13 collections: `easypc_stores`, `easypc_services`, `easypc_parts_catalog`, `easypc_customers`, `easypc_work_orders` (+ `grp_tabs` 7-tab layout), `easypc_work_order_parts`, `easypc_work_order_parts_used`, `easypc_job_processes`, `easypc_diagnostics`, `easypc_approvals`, `easypc_work_order_updates`, junctions `easypc_work_orders_services` (with `charged_price` snapshot) and `easypc_work_orders_files`.

Roles/policies: `easypc_front_desk`, `easypc_technician`, `easypc_manager` (+ `*_policy`).

Design spec: `docs/data-model.md`, `docs/workflow.md`, `docs/README.md`.

## BIS (Barangay Information System) — built 2026-10-21

Second app on this instance; prefix `bis_` (same isolation rule — never touch non-`bis_`/`easypc_` collections).
Scripts live in the **BIS repo** (not the easypc one): `scripts/build_bis_schema.py` (idempotent
schema builder) and `scripts/seed_smoke_test.py` (reference data + relational smoke test).

Nav: `BIS` folder → `bis_master_data` / `bis_registry` / `bis_operations` sub-folders.
14 collections: `bis_settings` (singleton), `bis_puroks`, `bis_officials`, `bis_document_types`,
`bis_households`, `bis_residents` (5-tab layout), `bis_document_requests` (4 tabs),
`bis_blotter` (3 tabs), `bis_blotter_parties` (O2M junction w/ `party_role` payload — avoids
M2M `junction_field` issues entirely), `bis_blotter_attachments`, `bis_kp_cases` (3 tabs),
`bis_kp_hearings`, `bis_business_permits`, `bis_announcements`. All UUID PKs +
audit fields wired to `directus_users`.

BIS-specific lessons:
- **Prefer O2M junction-with-payload over M2M** when you need per-link data (party_role,
  statement) — `list-o2m` gives inline editing and never needs `junction_field` fixes (rule 20).
- **Singletons**: POST `/items/{singleton}` → ROUTE_NOT_FOUND; use PATCH instead.
- **Seed UUID vars need JSON quotes** — `"household": $H1` (unquoted) 400s with cryptic
  "Expected ',' or '}'" errors; write seeders as script files, not inline shell JSON.
- Verified end-to-end: nested reads across households/residents/doc_requests/blotter parties/
  KP hearings all resolve; `user_created` resolves to real users.
- Phase 2 built 2026-10-21 (`scripts/build_bis_phase2.py`): 3 `print_template` rows +
  `print` fields on doc_requests/blotter/kp_cases; "BIS Dashboard" w/ 6 metric panels +
  5 echarts panels; `bis_stamp_settings` flow auto-stamps `settings` M2O → `bis_settings`
  singleton on create (letterhead in templates) + backfilled.
- Phase 3 built 2026-10-21 (`scripts/build_bis_phase3.py`): roles `bis_staff`/
  `bis_secretary`/`bis_captain` → `{role}_policy` via `directus_access` +
  `directus_permissions` rows; serial flows `bis_serial_doc|blt|kp|bp` (event
  items.create → likha_sql next `PREFIX-YYYY-NNNN` → item-update `{{sql_1.rows.0.serial}}`);
  `bis_stamp_sla` flow stamps `due_date` = create + `document_types.sla_days`.
  Remaining: portal + QR verify, SMS, choropleth panel, real purok names.
- Design spec: `docs/data-model.md`, `docs/features.md` (provider research + value-ranked
  features), `docs/README.md` in the BIS repo.

## Dashboards, echarts & printing (added 2026-10-21)

- **Installed app extensions are enumerable**: `GET /extensions?limit=-1` returns every
  enabled panel/interface/layout/module (`schema.type` + `schema.name`) — use it to discover
  custom panel types instead of guessing from existing rows (`/panels` only shows
  instantiated types). `directus_extensions` items are 403 — the `/extensions` endpoint works.
- **Panel type ids are NOT inferable from folder names**: `likha-echarts-panel` → type
  `echarts-panel`, but `likhaHeatmap-panel` → type `likhaHeatmap-panel` (prefix kept!).
  Read `src/index.ts` `definePanel({id:...})` — extension sources for this instance live in
  the sibling repo `../LikhaCMS-2/backend/extensions/<folder>/src/` (not served over HTTP).
- **Custom panels on this instance**: `echarts-panel`, `likhaHeatmap-panel` (Heatmap),
  `@directus-labs/choropleth-map-panel` (colors a geometry/boundary column by a value —
  good for `bis_puroks.boundary`), `@directus-labs/table-view-panel`,
  `@samfurlong/directus-panel-calendar`, `likhaButtonLink-panel`, `flow-triggers-panel`.
- **`echarts-panel` custom panel type exists.** Options: `{flow: {key: <flow-uuid>, collection: "directus_flows"}}`.
  On render the panel hits `GET /flows/trigger/{id}` and draws whatever the flow's last op returns —
  that return value must be a plain ECharts option object.
- **Chart flow recipe**: `trigger:"webhook"`, `accountability:"all"`, `options.error_on_reject:true`;
  ops chain `likha_sql` (key `sql_1`, `options.sql` + `binding:[]`) → `exec` (`module.exports =
  async function(data){ ... return option }`; SQL rows arrive at `data.sql_1` — array of row objects).
  Wire `op1.resolve = op2.id` and `flow.operation = op1.id`. Verify: `GET /flows/trigger/{id}`.
- **Webhook triggers are GET, not POST** — `POST /flows/trigger/{id}` → 403 FORBIDDEN; plain GET works
  and returns the last op's result as the response body.
- **`likha_sql` op returns `{sql, binding, rows:[...]}`** — in downstream `item-update`
  payloads template rows via `{{sql_1.rows.0.col}}`; in `exec` ops `data.sql_1` may be
  that object, so unwrap `rows = data.sql_1.rows || data.sql_1`. Writing `{{sql_1.0.x}}`
  stores literal "undefined". UPDATE statements return `rows:[]` (no RETURNING).
- **`csv` fields store a JSON-array string** (e.g. `["youth","four_ps"]`), not comma-separated text —
  expand in SQL with `jsonb_array_elements_text(sector_tags::jsonb)`; `string_to_array(col,',')`
  yields broken `["a"]`-style rows.
- **Native panel option shapes**: metric `{collection, field:"id", function:"count", filter:{...}, sortField:null}`;
  bar-chart `{collection, column, legend, xAxis}`; pie-chart `{collection, column}`; variable `{type:"variable"}`
  for dashboard filters. Grid units: dashboard ~56 wide; metrics ~8×9, echarts ~27×22; `show_header:true` shows `name`.
- **`print_template` + `print` field**: field = `type:"alias"`, `special:["alias","no-data"]`,
  `interface:"print"`, `options:{templateSelection:{collection:"print_template",key:"<row-uuid>"},fields:["*.*.*"]}`.
  LiquidJS context = the item resolved to `fields` depth: M2O → nested object, O2M → array of junction
  rows (`{% for p in parties %}{{ p.resident.first_name }}{% endfor %}`); filters `default`, `date`, `upcase`,
  `replace`, `capitalize`, `newline_to_br`, `{% case %}` all work.
- **Singleton letterhead in templates**: give the printable collection a `settings` M2O → singleton and stamp
  it via an `event`/`items.create` flow `item-update` op (`key:"{{$trigger.key}}"`, `emitEvents:false`,
  `permissions:"$full"`); backfill existing rows once. Template reads `{{ settings.barangay_name }}`.
- **`csv` fields reach print templates as JSON STRINGS** (`'["a","b"]'`, not arrays) — iterate with
  `{% assign t = field | split: ',' %}` then per item `| replace:'[','' | replace:']','' | replace:'"',''`.
  Same caveat for SQL (jsonb_array_elements_text) — string in API, JSON-array text in DB.
- **Multiple `print` alias fields per collection are fine** (e.g. `print`, `print_settlement`, `print_cfa`
  on `bis_kp_cases`) — each is a separate alias field with its own `templateSelection`.
- **Geometry fields are namespace-prefixed**: `type:"point"` → INVALID_PAYLOAD (error lists valid enum);
  use `geometry.Point` / `geometry.MultiPolygon` / plain `geometry`. Payloads accept AND return GeoJSON
  objects `{"type":"Point","coordinates":[lng,lat]}` — remember lng first. Map interface options:
  `{basemap:"OpenStreetMap", defaultView:{center:{lat,lng},zoom}}` (OSM needs no token).
- **`likhaHeatmap-panel` data contract (verified from source)**: NO flow reference — the
  panel queries a collection itself (limit 1000). Options:
  `{collection, geoField, field?, filter?, popupFields?, showHeader, autoFitBounds,
  defaultCenter(GeoJSON Point), defaultZoom, defaultBearing, colorScheme
  (coolwarm|viridis|plasma|grayscale|spectral), heatmapRadius, heatmapIntensity,
  showCircleLayer, heatmapMaxZoom, circleMinZoom, transitionRange, enableClustering,
  clusterRadius, clusterAggregation(count|sum|avg|min|max), clusterCategories}`.
  `geoField` accepts GeoJSON Point natively (also "lat,lng" strings, {lat,lng}, arrays);
  `field` = numeric metric → `Number(field)` fallback 1, so OMIT it when the collection has
  no numeric metric; `popupFields` supports dot-notation nested paths (`purok.name`).
  ⚠️ The panel's OPTIONS UI is buggy — clicks throw `Cannot read properties of undefined
  (reading 'query')` and nothing saves; configure panels via `PATCH /panels/{id}` instead
  (see `scripts/build_bis_heatmap.py` for the working options JSON).
- **`field` (metric) must be a real numeric field** — undefined `field` → `split` crash;
  nonexistent name → intensity falls back to 1 but legend/popup look wrong. BIS added
  `severity`(blotter 1–5), `risk_score`(households), `vulnerability_score`(residents).
- **Extension update pipeline (LikhaCMS-2)**: edit `backend/extensions/<name>/src/*` →
  `npm run build` in that dir (or `npm run backend:build:all:extensions` at repo root) →
  push → on server `git pull` + `docker compose build backend && up -d backend`
  (backend.Dockerfile bakes extensions INTO the image — restart alone won't pick them up;
  volume-mounts only cover uploads). Served bundle is `GET /extensions/sources/index.js`
  (all ext concat) — grep it to verify a deploy landed; users must hard-refresh after.
- **likhaHeatmap bugs fixed 2026-10-21** (commit 9b7fcaf on likhaCMS/LikhaERP): TDZ crash
  (`let resizeObserver` declared after use — move decls before first reference) and
  cluster clicks showing "0" (cluster features lack `value`/`popupFields` — guard
  `properties.cluster` and `getClusterExpansionZoom`+easeTo instead of record popup).
- **list-o2m table view**: `options.fields:["a","b"]` renders rows as columns (not just the template string);
  add `options.sortField`, `enableLink/Create/Select/SearchFilter`. Hide pure junction collections from nav
  via collection `meta.hidden:true` — still editable through the parent's O2M tab. M2O pickers need
  `options.template` or the dropdown shows raw UUIDs.
