# Phase 05 — Evidence-gated Product Studio

## What it builds

The product studio accepts only current VALIDATED_BY_SOURCE opportunities
with an HTTPS source URL on the Phase 04 allowlist. That status means a permitted
public source contains a problem report. It does not mean the author is a buyer,
that the problem is common, or that anyone will pay. Willingness to pay remains
a hypothesis until an opt-in buyer confirms it.

Three tracks are implemented:

- **A — B2B website snapshot audit.** Accepts an owner-authorized HTML snapshot,
  produces a sanitized real Chromium screenshot, a SHA-256-linked static
  accessibility/technical-SEO report, reviewable repair fragments, and an
  unsent owner-reviewed offer draft. No crawl, live performance score, source
  modification, PR, or outbound contact is performed.
- **B — Local CSV workflow.** A Python standard-library CLI maps headers,
  trims values, removes exact normalized duplicate rows, neutralizes formula
  values in both data and mapped headers, and writes a change report. It reads
  the source without overwriting it and makes no network requests.
- **C — Offline microtool pack.** Improves two existing catalog tools only:
  CSV Workbench and SEO Snapshot Auditor. They import local files, keep
  untrusted HTML inert, export CSV/JSON, run without external assets or
  telemetry, and have responsive mobile controls.

The 12-entry app catalog is retained. Only the two improved Studio tools have
no fixed purchase price: the demo is free and customization, installation, or
licensing requires an owner-reviewed scope and quote after an actual order.
The public payment-report route rejects these Studio products at the legacy
fixed-price checkout. Existing non-Studio catalog entries are unchanged.

## Product package contract

Each staged ZIP contains a requirements spec, passing QA results, versioned
changelog, licensing/IP review notes, installation and rollback steps, support
notes, synthetic sample data, and an honest landing page. The manifest stores
source evidence and per-file SHA-256 hashes. A .zip.sha256 sidecar verifies
the complete archive. ZIP timestamps are normalized for repeatable builds.

quality_score is computed as passed required acceptance checks divided by
the total required checks. A failed check prevents creation or replacement of
the artifact. The score measures package QA only; it is not evidence of sales,
legal approval, or paid demand. Any quoted Stack Exchange excerpt is included
only with a CC BY-SA license, a source link, and author attribution. The
packages contain no third-party runtime code or assets.

## Source evidence used for staging

The current product databases contained no validated opportunity records.
For this build, the official Stack Exchange public API was queried through the
Phase 04 allowlisted collector using a temporary database. No source rows were
written to either project database. The selected records are recent, licensed
public questions:

- Website/SEO problem signal:
  [How can search engines crawl dynamic page content when JavaScript is disabled?](https://stackoverflow.com/questions/80013003/how-can-search-engines-crawl-dynamic-page-content-when-javascript-is-disabled)
  — source date 2026-10-28; captured 2026-11-08T01:56:09Z.
- CSV import problem signal:
  [NiceGui Upload CSV Error](https://stackoverflow.com/questions/80003017/nicegui-upload-csv-error-uploadeventarguments-object-has-no-attribute-content)
  — source date 2026-09-14; captured 2026-11-08T01:56:08Z.
- CSV export/header problem signal:
  [Why does export-data ignore -dt true for a tree-model CSV header?](https://stackoverflow.com/questions/79998615/why-does-export-data-ignore-dt-true-for-a-tree-model-csv-header)
  — source date 2026-08-27; captured 2026-11-08T01:56:08Z.

The collection returned 35 eligible source signals and five current source
opportunities. This is a small, biased problem sample, not market validation.
The offers and landing pages explicitly make that distinction. The Track A
preview in the package is the synthetic fixture, not a customer website.

## Staged artifacts

All packages passed their build-time E2E checks and were written locally:

- Track A — service-site-audit-21e19e55cdea-v1.0.0.zip, SHA-256
  9818ec5c7c6fc4759a6d7c1a0be623fdbc3fd827ab8b04cc72e568267d68e93a; 6/6
  checks passed.
- Track B — csv-workflow-pack-1fb92ca9c702-v1.0.0.zip, SHA-256
  78b271ca7134ba45e059577b620dfe38804a1f5b7022c5fe7b991c27c7e21ca3; 6/6
  checks passed.
- Track C — offline-microtool-pack-167c88780872-v1.0.0.zip, SHA-256
  cf5357b7dcc6cad5afa6ca2a8f5c67b6be9e15fafbb625cb00e188b29b62132c; 7/7
  checks passed.

Each staged manifest reports a test-derived quality score of 100.0. The score
does not certify market demand or legal readiness.

## QA and access

The product builder runs the Python CSV CLI with synthetic fixtures, opens both
browser tools in Chromium at a mobile viewport, verifies file import/export,
formula safety, inert hostile HTML, no outbound browser requests, and package
hashes. The service pack verifies screenshot provenance and contact redaction.
The owner-only API exposes build, list, and download endpoints under
/api/product-studio; the catalog is public but does not award quality scores
until a verified staged ZIP includes passing QA evidence.

Staging is local under outputs/staging. Production is not modified and no
outreach is sent.
