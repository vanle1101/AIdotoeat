# Phase 04 — Evidence-first market research

## What counts as an opportunity

`VALIDATED_BY_SOURCE` means only that a recent, permitted source contains a
publicly observable problem signal. It does **not** mean the market is large,
the author is a buyer, or anyone will pay. Direct payment language is counted
only when it is explicit in the source text; it remains unverified until a
permitted opt-in conversation confirms it. Source popularity is not treated as
purchase intent.

Static `MarketScout` ideas stay available as `UNVALIDATED` templates. The
compatibility method `get_validated_opportunities()` returns an empty list;
the marketplace-scraping template is additionally blocked until an expressly
permitted API/export/feed is identified.

## Collection rules

- Read only the official Hacker News Firebase API and Stack Exchange API.
- Do not crawl linked pages, create leads, contact authors, or reproduce Hacker
  News story wording; only a coarse topic paraphrase is kept. Stack Exchange quotations are retained only when the API
  supplies an allowed CC BY-SA license and an attribution.
- Requests have fixed allowlisted hosts, timeouts, response-size bounds, and a
  persisted five-minute per-source interval. Provider `backoff`, HTTP 429/402,
  or payment/cost metadata stops collection; no payment request or credential
  is sent.
- Skip records older than 365 days, personal email/phone data, unknown source
  URLs/licenses, duplicates, and content matching hard-reject policy for spam,
  fake engagement/reviews, guaranteed profit, CAPTCHA bypass, or prohibited
  personal-data harvesting.
- There is no search API or paid provider in this phase. An unavailable or
  empty feed produces zero opportunities.

## Stored evidence and scoring

Each opportunity stores its source URL, capture/source timestamps, permitted
quotation and attribution, observed problem, inferred buyer persona, known
alternatives, estimated skills/resources, willingness-to-pay hypothesis, legal
limits, competition status, heuristic confidence, freshness, score components,
  and a falsifiable experiment with stop criteria. Alternatives and competition
are explicitly `NOT_RESEARCHED` when no allowed source established them.

Score is a local triage rubric, not a market measurement. Weights: evidence
quality 20%, urgency 15%, direct willingness-to-pay signal 15%, local
feasibility 14%, distribution reachability 10%, time-to-first-value 10%, owner
constraints fit 8%, competition attractiveness 4%, freshness 4%. Unobserved
payment intent receives zero. Current owner constraints and competition
ratings are marked as estimates/unresearched rather than sourced facts.

Semantic deduplication uses normalized title/tag overlap. Distinct reports from
different people can still be consolidated; the evidence table's unique source
key prevents a single URL being counted twice. Top-five output is capped at
five and may be empty.

## API and data

- Owner-only `POST /api/internet/live-scan` runs the two public feed adapters.
- `POST /api/opportunities/analyze-freelance-job` saves an owner-provided brief
  as `UNVALIDATED`; keyword fit and user-entered budgets are not presented as
  verified demand.
- Dashboard rows link directly to sources and show validation status, capture
  time, quote attribution, WTP hypothesis, evidence limitations, and experiment
  falsification/stop rules.
- Static article cards no longer present unsupported market-price or discount
  comparisons; catalog prices are labeled as configured catalog data, separate
  from market demand evidence.
- Public startup/contact cards containing scraped email addresses and canned
  cold pitches were removed. The view now directs owners to opt-in CRM records.
- Additive migration `008_market_research.sql` extends the existing evidence
  ledger and creates fetch-state rows. It preserves legacy evidence and
  opportunity records. Migration is idempotent. Test databases are temporary.

## Limitations

The feeds produce problem reports, not a representative demand sample. This
implementation does not research competitor catalogs, pricing, market size,
distribution access, or whether authors can be contacted. A source-backed row
is a candidate for owner review and a lawful opt-in experiment only. No
production deployment or outbound contact is included.
