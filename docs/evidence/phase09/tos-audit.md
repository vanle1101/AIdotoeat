# Phase 09 source terms and license check

Reviewed 2026-11-08 UTC for the two live-research adapters in `core/market_research.py`.

| Source | Official source checked | Result | Code controls |
|---|---|---|---|
| Stack Exchange API | [API Terms of Use](https://stackexchange.com/legal/api-terms-of-use) (HTTP 200; page title `API Terms of Use - Stack Overflow`) and [Public Network Terms](https://stackoverflow.com/legal/terms-of-service/public) (HTTP 200) | The API terms require visible Stack Exchange attribution. The normalizer accepts only content carrying a supported CC BY-SA license and records author, source URL, license, and capture time. API-specific documentation at `api.stackexchange.com/docs/terms-of-use` returned HTTP 404 from this audit, so endpoint quota details were not independently confirmed here. | Official HTTPS endpoint allowlist, bounded page size, persisted fetch backoff, `content_license` validation, no personal contact data, source URL and author attribution retained. |
| Hacker News | [Official Firebase API reference](https://github.com/HackerNews/API) returned HTTP 504 from this audit; the official public item endpoint was reachable. | Read-only Ask HN metadata fetch; formal API terms and a guaranteed request quota were not verified in this environment. Treat terms/quota as unresolved before increasing live fetch volume. | Official `hacker-news.firebaseio.com` allowlist, a bounded 10-item maximum per fetch, per-source backoff, no automated posting, voting, clicks, or impressions. |

## Release decision

The source policy is conservative and both integrations are read-only. Stack Exchange attribution and license metadata are retained. This is a technical audit, not legal advice. Formal Hacker News API terms and Stack Exchange request quota documentation remain unverified; live research must keep the existing low request caps and backoff until those documents can be checked. There is no crawling, login, CAPTCHA bypass, proxy rotation, user contact harvesting, or automated community posting in the pipeline.

## Reproducible checks

- The source normalization and refusal cases are covered by [test_phase04_market_research.py](../../tests/test_phase04_market_research.py) and the licensed source fixture [phase09_public_stackexchange_question.json](../../tests/fixtures/phase09_public_stackexchange_question.json).
- The staged product manifest records source attribution and share-alike license metadata; the Phase 09 E2E evidence records that the fixture retained only the question title and attribution, without the body.
