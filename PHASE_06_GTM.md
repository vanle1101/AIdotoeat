# Phase 06 — one evidence-led GTM experiment

## Selection and offer

The Phase 04 collector was run against its allowlisted official Stack Exchange
and Hacker News feeds, using a disposable SQLite database. The current top-five
list contained five source-backed problems. The highest local rubric score was
**website technical SEO/crawlability: 54.1**, followed by CSV workflow at
**53.9**. The selected opportunity is a Stack Overflow question about dynamic
page content when JavaScript is disabled:

- Source: [How can search engines crawl dynamic page content when JavaScript is
  disabled?](https://stackoverflow.com/questions/80013003/how-can-search-engines-crawl-dynamic-page-content-when-javascript-is-disabled)
- CC BY-SA 4.0, attributed to Ankita Khokhar on Stack Overflow.
- Captured 2026-11-08. Its score is a heuristic rubric, not market size,
  popularity proof, buyer authority or payment evidence. Direct willingness to
  pay was absent.

Exactly one offer and experiment is staged: a fixed-scope audit of one
owner-authorized HTML snapshot for static title, description, viewport, H1,
image-alt and possible JavaScript-rendering observations. The free local demo
does not upload the input. The paid-service price hypothesis is **$29–$49 per
page** and remains unverified. No ranking, traffic, performance or revenue
outcome is promised.

The portfolio demo runs the existing Offline SEO Snapshot Auditor against a
synthetic HTML fixture. It includes a real Chromium preview screenshot, a
reproducible JSON report and a case-study walkthrough explicitly labelled as a
synthetic fixture, not client work. Screenshot generation strips active
content, disables JavaScript and aborts every network request.

## Experiment design

- Window: 14 days, with zero cash budget and no paid media, mailing lists,
  commissioned services or automatic acquisition.
- One candidate channel: one owner-approved, manually written Indie Hackers
  feedback submission, only after checking the current destination rules and
  obtaining owner approval. The official Terms were reviewed on 2026-11-08;
  they prohibit spam, automated posting and scraping. A separate current
  community-specific posting guide was not established, so submission stays
  blocked until it is rechecked.
- Hacker News has a separate saved draft for preview only. Its official
  [Guidelines](https://news.ycombinator.com/newsguidelines.html) say not to use
  the site primarily for promotion, not to submit generated text and not to
  automate posting. The queue requires an owner-attested substantial rewrite;
  there is no posting adapter.
- Week 1: owner reviews the offer, privacy language and current community rules.
  If approved, manually submit only one human-authored channel post. Observe
  consented landing views, demo starts, opt-in contact submissions and
  qualified inquiries.
- Week 2: reply only to explicit inbound requests. Create personalized
  one-to-one proposal drafts, approve them as owner before contact, and record
  manually sent proposals, customer replies, accepted quotes and payments only
  when supported by the verified payment ledger.
- Continue only with at least 2 distinct qualified opt-in inquiries and one
  explicit request for a quote in 14 days. Stop after 14 days or 5 opt-in
  problem checks, whichever comes first, if the problem cannot be reproduced
  or there are zero qualified inquiries. These are experiment thresholds, not
  proof of repeatable demand.

## Landing and SEO staging

The generated package contains one semantic landing page, one tutorial, one
synthetic portfolio case study, a local demo, canonical and Open Graph metadata,
valid Schema.org `WebPage`/`Service` JSON-LD, a one-URL sitemap and a robots file.
The landing page includes benefits, audience, scope, price hypothesis, working
demo, actual fixture results, FAQ, privacy choices, consented contact form and
quote CTA. It has no fake testimonials, customer logos, ratings, keyword
stuffing, articles-at-scale or ranking claims.

The package is **noindex** and `robots.txt` disallows crawling. It uses
`https://example.invalid` until a public base URL is configured and an owner
authorizes publication. It is a private preview, not an indexed public page.
No content was copied into `frontend/` or served as a public landing route.

## CRM and data rules

Migration `009_gtm_crm_analytics.sql` is additive and preserves the existing
`leads` table. Legacy contacts start with consent `UNKNOWN` and cannot be
contacted by this campaign. Inbound contact requires a checked, purpose-limited
permission; opt-out suppresses a matching address, revokes permission and
clears approval. The response does not reveal whether the email was present.
No contact list is bought or harvested; contact replies are never auto-sent.

Owners can qualify an inbound lead, save a personalized proposal draft, approve
the exact current draft and record a **manually sent** one-to-one proposal.
Approval is hash-bound to the draft. Suppressed contacts cannot be contacted;
the cap is two owner-attested contacts with at least 14 days between them. There
is no email sender. A proposal-sent event is recorded only after owner
attestation that it was manually sent.

Landing and demo events require optional analytics consent. Contact submissions
are stored as requested CRM work; session and UTM context for a contact event
are retained only when analytics consent was separately enabled. Event storage
keeps a path, limited UTM fields, random session ID if opted in, event time and
source; it does not keep IP, full query strings, user-agent, prompts or contact
form bodies. Known bots, Playwright/WebDriver and explicit internal-test traffic
are excluded. Event/session conversion rates are labelled estimates; UTM is
visitor-supplied and unverified. Channel ROI and revenue remain `null` until a
verified transaction and defensible channel attribution both exist.

## Review and endpoints

- `GET /api/gtm/experiment` — experiment, evidence and thresholds.
- `GET /api/gtm/policies` — reviewed channel rules and source URLs.
- `GET /api/gtm/artifact` — owner-authenticated staging ZIP and SHA-256.
- `GET /api/gtm/admin/drafts` — owner-only community draft previews.
- `POST /api/gtm/admin/publication-queue` — queue an existing draft for review.
- `POST /api/gtm/admin/publication-queue/{id}/review` — require human rewrite,
  a fresh channel check and owner approval for manual posting only.
- `POST /api/gtm/admin/publication-queue/{id}/publish` — always blocked because
  posting credentials/adapters are not configured.
- `POST /api/gtm/leads`, `POST /api/gtm/opt-out`, `POST /api/gtm/events` —
  consented inbound and privacy-limited first-party events.
- `/api/gtm/admin/leads/*` and `/api/gtm/admin/kpis` — owner-only CRM and
  verified funnel observations.

Public lead submission is rate-limited to 3 per hour per source; analytics to
30 events per minute. Owner mutations use HTTPS, admin auth, same-origin
middleware and 30 per minute. No actual post, outreach, payment or production
deployment was performed.

## Verification

The staging build runs Chromium at 375×812 and 1440×900 with reduced motion. It
checks semantic language/headings, explicit form labels, keyboard skip link,
contact and analytics consent, real demo navigation, opt-out submission, no
third-party requests, internal links, structured data, preview robots/sitemap,
and one-experiment/no-fake-proof copy. Every check must pass before a QA score
is assigned. The bundle uses normalized ZIP timestamps and per-file SHA-256;
identical inputs are tested for byte-identical package hashes.

Phase 06 acceptance coverage is in `tests/test_phase06_gtm.py`. The full
repository suite passed: **124 tests in 25.251 seconds**. The test run emitted
two Python `ResourceWarning` messages for already-closed socket objects; they
did not fail tests. The suite also regenerated the existing app catalog into a
temporary directory. `git diff --check` passed (Git reported only its usual
LF-to-CRLF working-copy notices).

The final deterministic staging build passed **18/18** browser/build checks
(quality score **100.0**, computed only from those checks). Artifact:
`outputs/staging/gtm-website-snapshot-audit-2026w46-v1.0.0.zip`

SHA-256: `7ab1d259a76d09f0fdba1f870d1e9bca5137782f327df6e192243ea9625a04aa`

The ZIP and adjacent `.sha256` file are the private staging deliverable. The
manifest records `STAGING_QA_PASS_NO_PUBLICATION`; the artifact has noindex
metadata, disallows crawling, and the publication gate remains closed. No
production deployment, public post, or owner outreach was performed.
