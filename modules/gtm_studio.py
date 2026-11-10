"""Staging-only, evidence-led go-to-market assets for one Phase 06 experiment."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs, urlsplit
import zipfile

from core.config import OUTPUTS_DIR
from modules.product_builder import SAMPLE_HTML, audit_html_snapshot, _render_safe_preview


CAMPAIGN_ID = "gtm-website-snapshot-audit-2026w46"
OFFER_ID = "website-snapshot-audit"
CONSENT_VERSION = "gtm-contact-v1"
PACKAGE_VERSION = "1.0.0"
PUBLIC_PREVIEW_HOST = "https://example.invalid"
STAGING_DIR = OUTPUTS_DIR / "staging"
STAGING_PACKAGE = "gtm-website-snapshot-audit-2026w46-v1.0.0.zip"

EXPERIMENT: dict[str, Any] = {
    "experiment_id": CAMPAIGN_ID,
    "status": "STAGING_ONLY_OWNER_APPROVAL_REQUIRED",
    "selected_niche": "website_seo_technical_fixes",
    "selection_basis": "Live Phase 04 weighted-rubric rank 1 of 5 current source-backed opportunities; score is heuristic triage, not market size or buyer proof.",
    "selection_score": 54.1,
    "runner_up_score": 53.9,
    "source": {
        "url": "https://stackoverflow.com/questions/80013003/how-can-search-engines-crawl-dynamic-page-content-when-javascript-is-disabled",
        "source_type": "stackexchange_public_question",
        "captured_date": "2026-11-08",
        "license": "CC BY-SA 4.0",
        "attribution": "Ankita Khokhar on stackoverflow.com",
        "problem_signal": "A public question describes uncertainty about dynamic page content when JavaScript is disabled.",
        "willingness_to_pay": "HYPOTHESIS_ONLY; no direct willingness-to-pay signal was found.",
    },
    "offer_id": OFFER_ID,
    "offer_name": "Small-business HTML snapshot audit",
    "audience": "An independent web developer or small-business site owner who can supply an authorized HTML snapshot and wants reproducible static SEO/accessibility findings.",
    "offer_scope": "One owner-authorized HTML snapshot; static title, description, viewport, H1, image-alt and source-renderability checks; a sanitized screenshot, JSON/HTML report and repair suggestions.",
    "not_in_scope": ["No crawl or live-site request", "No Core Web Vitals measurement", "No ranking or traffic promise", "No website modification or PR without separate repository permission"],
    "pricing_hypothesis": "$29-$49 for a one-page snapshot audit, subject to owner review and an opt-in buyer conversation; not a configured checkout price.",
    "primary_distribution_channel": "One owner-approved Indie Hackers feedback submission after a fresh manual check of the current channel rules; no automated post or direct message.",
    "experiment_window_days": 14,
    "cash_budget_usd": 0,
    "weekly_plan": [
        {"week": 1, "actions": ["Owner reviews the offer, privacy text and community rules.", "If approved, publish one human-reviewed Indie Hackers feedback post; otherwise keep it staged.", "Collect only consented inbound requests and observe the local demo."], "kpis": ["consented landing views (count; not unique people)", "demo starts", "opt-in contact submissions", "qualified inquiries"]},
        {"week": 2, "actions": ["Respond only to people who explicitly requested contact.", "Send at most one owner-approved, personalized proposal per qualified opt-in lead.", "Record replies, accepted quotes and verified payments from their true source."], "kpis": ["qualified inquiry rate (estimated from consented sessions)", "proposal sent (owner-attested)", "customer replies", "accepted quotes", "verified payments"]},
    ],
    "success_threshold": "Within 14 days, at least 2 distinct qualified opt-in inquiries and at least 1 explicit request for a quote; this is a continuation signal, not proof of a repeatable market.",
    "failure_threshold": "Stop after 14 days or 5 opt-in problem checks, whichever comes first, if nobody can reproduce the problem or there are zero qualified opt-in inquiries. Do not increase channels or buy traffic to rescue a failed test.",
    "attribution_limit": "UTM values are visitor-supplied and unverified. Event totals are counts, not unique people; session-based rates are estimates and require optional analytics consent.",
}

COMMUNITY_POLICIES: dict[str, dict[str, Any]] = {
    "hacker_news_show_hn": {
        "label": "Hacker News / Show HN",
        "source_url": "https://news.ycombinator.com/newsguidelines.html",
        "checked_date": "2026-11-08",
        "checked_scope": "Official Hacker News Guidelines page read directly.",
        "rules_summary": [
            "Do not use the site primarily for promotion; a submission must be useful to the community.",
            "HN asks posters not to put generated text in posts and not to automate posting.",
            "Use a genuine working demo and describe limitations without asking for engagement manipulation.",
        ],
        "publication_gate": "BLOCKED_NEEDS_HUMAN_REWRITE_AND_OWNER_REVIEW",
        "human_rewrite_required": True,
    },
    "indie_hackers": {
        "label": "Indie Hackers",
        "source_url": "https://www.indiehackers.com/terms",
        "checked_date": "2026-11-08",
        "checked_scope": "Official Terms of Service page read directly; a separate community-posting guide was not established.",
        "rules_summary": [
            "Terms prohibit spam, automated posting, and crawling/scraping Indie Hackers content.",
            "Do not copy member content or imply revenue, customer results, or endorsement that has not happened.",
            "Check current community-specific rules and moderator guidance immediately before posting.",
        ],
        "publication_gate": "BLOCKED_RECHECK_CURRENT_COMMUNITY_RULES_AND_OWNER_REVIEW",
        "human_rewrite_required": True,
    },
}


@dataclass(frozen=True)
class GTMCheck:
    check_id: str
    passed: bool
    evidence: str


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_utm(value: str | Mapping[str, Any] | None) -> dict[str, str]:
    """Return only known, bounded UTM values; never retain arbitrary query data."""
    if value is None:
        params: Mapping[str, Any] = {}
    elif isinstance(value, str):
        params = {key: rows[-1] for key, rows in parse_qs(urlsplit(value).query, keep_blank_values=False).items() if rows}
    elif isinstance(value, Mapping):
        params = value
    else:
        return {}
    result: dict[str, str] = {}
    for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"):
        raw = params.get(key)
        if isinstance(raw, (list, tuple)):
            raw = raw[-1] if raw else ""
        if not isinstance(raw, str):
            continue
        cleaned = re.sub(r"[^A-Za-z0-9._~-]", "", raw.strip())[:80]
        if cleaned:
            result[key] = cleaned
    return result


def _safe_base_url(value: str | None) -> tuple[str, bool]:
    raw = (value or "").strip().rstrip("/")
    parts = urlsplit(raw)
    configured = bool(
        parts.scheme == "https" and parts.hostname and not parts.username and not parts.password
        and not parts.query and not parts.fragment and not parts.hostname.endswith(".invalid")
        and not parts.hostname.endswith(".example")
    )
    if not configured:
        return PUBLIC_PREVIEW_HOST, False
    return raw, True


def _landing_html(*, base_url: str | None = None, preview: bool = True) -> str:
    base, configured = _safe_base_url(base_url or os.getenv("AUTOPROFIT_PUBLIC_BASE_URL"))
    canonical = base + "/offers/website-snapshot-audit/"
    robots = "noindex,nofollow" if preview or not configured else "index,follow"
    data = {
        "@context": "https://schema.org", "@type": "WebPage",
        "name": "Kiểm tra HTML snapshot cho website nhỏ",
        "description": "Báo cáo kiểm tra tĩnh, có ảnh chụp đã khử nội dung hoạt động, từ HTML do chủ website cung cấp.",
        "url": canonical,
        "mainEntity": {"@type": "Service", "name": "Small-business HTML snapshot audit",
                       "serviceType": "Static HTML accessibility and technical SEO review",
                       "description": "Chỉ kiểm tra snapshot được chủ sở hữu cho phép; không crawl và không đo hiệu năng mạng."},
    }
    return f'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kiểm tra HTML snapshot cho website nhỏ | AUTOProfit AI</title>
<meta name="description" content="Báo cáo tĩnh có ảnh chụp và đề xuất sửa HTML do chủ website cung cấp. Không crawl, không tải dữ liệu lên, không cam kết thứ hạng.">
<meta name="robots" content="{robots}"><link rel="canonical" href="{html.escape(canonical, quote=True)}">
<meta property="og:type" content="website"><meta property="og:title" content="Kiểm tra HTML snapshot cho website nhỏ">
<meta property="og:description" content="Kiểm tra tĩnh HTML do bạn cho phép, với báo cáo có thể lặp lại.">
<script type="application/ld+json">{json.dumps(data, ensure_ascii=False, separators=(',', ':'))}</script>
<style>
:root{{--ink:#020617;--navy:#0f172a;--blue:#0369a1;--on-blue:#fff;--muted:#475569;--line:#dbe3ec;--paper:#f8fafc;--card:#fff;--focus:#7c2d12;--space:clamp(1rem,3vw,2rem)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}}
a{{color:#075985;text-underline-offset:.18em}}a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{{outline:3px solid var(--focus);outline-offset:3px}}
.skip{{position:absolute;left:-9999px;top:0;background:#fff;padding:1rem;z-index:5}}.skip:focus{{left:1rem}}
header{{background:var(--navy);color:#fff}}nav,.wrap{{max-width:1120px;margin:auto;padding:0 var(--space)}}nav{{display:flex;align-items:center;justify-content:space-between;min-height:68px;gap:1rem}}nav a{{color:#fff}}
.hero{{max-width:1120px;margin:auto;padding:clamp(3rem,8vw,7rem) var(--space);display:grid;grid-template-columns:minmax(0,1.1fr) minmax(250px,.9fr);gap:2rem;align-items:center}}
h1,h2,h3{{line-height:1.2;letter-spacing:-.02em}}h1{{font-size:clamp(2.1rem,5vw,3.8rem);max-width:15ch;margin:.45rem 0 1rem}}h2{{font-size:clamp(1.55rem,3vw,2.25rem)}}p{{max-width:70ch}}.eyebrow{{font-weight:750;letter-spacing:.08em;text-transform:uppercase;color:#bae6fd;font-size:.8rem}}
.lead{{font-size:1.17rem;color:#e2e8f0}}.actions{{display:flex;flex-wrap:wrap;gap:.75rem;margin:1.5rem 0}}.button{{min-height:48px;padding:.7rem 1rem;border-radius:.6rem;border:2px solid var(--blue);background:var(--blue);color:var(--on-blue);font-weight:700;text-decoration:none;display:inline-flex;align-items:center;justify-content:center}}
.button.secondary{{background:transparent;color:#fff;border-color:#cbd5e1}}.button.light{{color:var(--navy);border-color:var(--line);background:#fff}}.note{{font-size:.94rem;color:#cbd5e1}}
.hero-card,.card,.form-card{{background:var(--card);border:1px solid var(--line);border-radius:1rem;padding:clamp(1rem,3vw,1.5rem);box-shadow:0 8px 24px #0f172a0d}}
img{{max-width:100%;height:auto;border:1px solid var(--line);border-radius:.6rem}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}}section{{padding:clamp(2.5rem,6vw,5rem) 0}}.section-head{{max-width:760px;margin-bottom:1.5rem}}.tag{{font-size:.83rem;border-radius:999px;padding:.2rem .65rem;background:#e0f2fe;color:#0c4a6e;font-weight:700;display:inline-block}}
.report{{overflow:auto;background:#f1f5f9;padding:1rem;border-radius:.7rem;font:14px/1.5 ui-monospace,monospace;white-space:pre-wrap}}.price{{font-size:1.1rem;font-weight:750}}.muted{{color:var(--muted)}}form{{display:grid;gap:1rem}}label{{display:block;font-weight:650;margin-bottom:.3rem}}input,textarea{{width:100%;font:inherit;padding:.7rem;border:1px solid #64748b;border-radius:.5rem;background:#fff;color:var(--ink)}}textarea{{min-height:7rem}}.checkline{{display:flex;align-items:flex-start;gap:.7rem}}.checkline input{{width:1.2rem;height:1.2rem;flex:none;margin-top:.2rem}}.checkline label{{font-weight:500;margin:0}}
.honeypot{{position:absolute!important;left:-10000px!important;width:1px!important;height:1px!important;overflow:hidden!important}}.privacy-box{{background:#eff6ff;border-left:4px solid var(--blue);padding:1rem}}footer{{border-top:1px solid var(--line);padding:2rem 0;color:var(--muted)}}.status{{min-height:1.5rem}}.sr-only{{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}}
@media(max-width:760px){{.hero{{grid-template-columns:1fr;padding-top:3rem}}.grid{{grid-template-columns:1fr}}nav{{align-items:flex-start;padding-top:1rem;padding-bottom:1rem;flex-direction:column}}}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}*,*::before,*::after{{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}}}
</style></head><body>
<a class="skip" href="#main">Bỏ qua điều hướng</a><header><nav aria-label="Điều hướng chính"><a href="#top" aria-label="AUTOProfit AI, đầu trang">AUTOProfit AI</a><div><a href="#demo">Xem demo</a> · <a href="#scope">Phạm vi</a> · <a href="#contact">Liên hệ</a></div></nav>
<div class="hero" id="top"><div><span class="eyebrow">Dịch vụ kiểm tra HTML snapshot · bản demo miễn phí</span><h1>Biết chính xác snapshot HTML đang thiếu gì</h1>
<p class="lead">Gửi một bản HTML bạn có quyền chia sẻ để nhận báo cáo tĩnh về title, meta description, viewport, cấu trúc H1, alt ảnh và dấu hiệu cần kiểm tra JavaScript rendering.</p>
<div class="actions"><a class="button" href="#contact">Yêu cầu xem phạm vi</a><a class="button secondary" href="demo/seo-opengraph-meta-generator.html">Mở demo miễn phí</a></div>
<p class="note">Không tải nội dung lên qua demo, không crawl website, không hứa tăng hạng Google. Báo giá thử nghiệm: <strong>{html.escape(EXPERIMENT['pricing_hypothesis'])}</strong></p></div>
<div class="hero-card"><span class="tag">Ví dụ portfolio · fixture tổng hợp</span><h2>Ảnh preview đã khử active content</h2>
<img src="assets/sample-page-preview.png" width="960" height="540" alt="Ảnh chụp Chromium cục bộ của trang HTML mẫu tổng hợp được dùng làm đầu vào audit">
<p class="muted">Đây là đầu vào mẫu, không phải website khách hàng. <a href="case-study.html">Xem cách tạo báo cáo mẫu</a>.</p></div></div></header>
<main id="main" class="wrap">
<section aria-labelledby="problem-title"><div class="section-head"><span class="tag">Tín hiệu vấn đề, chưa phải bằng chứng mua</span><h2 id="problem-title">Vì sao có audit snapshot?</h2>
<p>Trong câu hỏi công khai, một người dùng nêu vấn đề nội dung trang động khi JavaScript bị tắt. Đây là một ví dụ vấn đề, không phải khách hàng hay lời chứng thực. <a href="{html.escape(EXPERIMENT['source']['url'], quote=True)}" target="_blank" rel="noopener noreferrer">Mở nguồn gốc Stack Overflow</a> · {html.escape(EXPERIMENT['source']['attribution'])} · {html.escape(EXPERIMENT['source']['license'])}.</p></div>
<div class="grid"><article class="card"><h3>Kiểm tra lặp lại</h3><p>Cùng một snapshot sẽ cho cùng các quan sát tĩnh; báo cáo lưu hash nguồn để đối chiếu.</p></article><article class="card"><h3>Giữ dữ liệu tại chỗ</h3><p>Demo xử lý file trong trình duyệt. Gói dịch vụ dùng snapshot được chủ website gửi có chủ đích.</p></article><article class="card"><h3>Nêu rõ giới hạn</h3><p>Không đo Core Web Vitals, trạng thái HTTP, robots, canonical hoặc kết quả Google thực tế.</p></article></div></section>
<section id="demo" aria-labelledby="demo-title"><div class="section-head"><span class="tag">Kết quả mẫu thực chạy</span><h2 id="demo-title">Portfolio demo với fixture tổng hợp</h2>
<p>HTML mẫu thiếu title, meta description, viewport và alt ảnh. Bộ audit sinh JSON/HTML report cùng ảnh Chromium đã khử script, event handler và liên kết ngoài.</p></div>
<div class="grid"><div class="card"><h3>Quan sát có thể tái tạo</h3><ul><li>Thiếu title và meta description.</li><li>Thiếu viewport và alt ảnh.</li><li>JavaScript rendering được ghi là heuristic cần kiểm tra.</li></ul><a href="case-study.html">Đọc quy trình và report mẫu</a></div>
<div class="card"><h3>Thử demo ngay</h3><p>Chọn file HTML cục bộ hoặc dùng trang mẫu. Nội dung không rời thiết bị.</p><a class="button light" id="demoStart" href="demo/seo-opengraph-meta-generator.html">Bắt đầu demo</a></div>
<div class="card"><h3>Đề xuất sửa</h3><p>Báo cáo đưa ra gợi ý theo từng check ID. Việc sửa file hoặc mở PR chỉ làm khi được chủ website cho phép.</p><a href="portfolio-report.json">Mở report mẫu JSON</a></div></div></section>
<section id="scope" aria-labelledby="scope-title"><div class="section-head"><span class="tag">Phạm vi báo giá thử nghiệm</span><h2 id="scope-title">Một trang, một snapshot, kết quả rõ ràng</h2>
<p class="price">Giả thuyết giá: $29-$49 / một trang</p><p class="muted">Đây là giả thuyết cần kiểm tra với người quan tâm thật; chưa phải giá đã được khách hàng chấp nhận. Chỉ có báo giá sau khi chủ sở hữu và người mua cùng chốt phạm vi.</p></div>
<div class="grid"><article class="card"><h3>Nhận được</h3><ul><li>Report HTML và JSON có mã kiểm tra.</li><li>Ảnh preview cục bộ đã khử thông tin liên hệ phổ biến.</li><li>Gợi ý sửa và checklist xác minh lại.</li><li>Hướng dẫn giữ bản gốc và rollback.</li></ul></article><article class="card"><h3>Cần từ bạn</h3><ul><li>File snapshot bạn có quyền chia sẻ.</li><li>Mục tiêu cụ thể để đánh giá.</li><li>Không gửi mật khẩu, cookie hay dữ liệu người dùng.</li></ul></article><article class="card"><h3>Không bao gồm</h3><ul><li>Crawl, pentest hoặc tải website trực tiếp.</li><li>Đo tốc độ mạng hay thứ hạng tìm kiếm.</li><li>Cam kết traffic, leads hoặc doanh thu.</li></ul></article></div></section>
<section aria-labelledby="faq-title"><div class="section-head"><h2 id="faq-title">Câu hỏi thường gặp</h2></div><details><summary>File HTML có bị tải lên không?</summary><p>Demo miễn phí chạy cục bộ trong trình duyệt. Dịch vụ chỉ xử lý snapshot khi bạn tự nguyện gửi qua form và xác nhận quyền chia sẻ; file không được gửi trong form liên hệ.</p></details>
<details><summary>Báo cáo có chứng minh Google không đọc được trang?</summary><p>Không. Báo cáo quan sát source snapshot và gắn cờ heuristic. Muốn kết luận về crawler hoặc performance cần một phép đo được cấp quyền riêng.</p></details>
<details><summary>Giá đã được xác nhận chưa?</summary><p>Chưa. Khoảng $29-$49 là giả thuyết thử nghiệm; không có thanh toán tự động trên trang này.</p></details></section>
<section id="contact" aria-labelledby="contact-title"><div class="section-head"><span class="tag">Opt-in inbound</span><h2 id="contact-title">Yêu cầu trao đổi về phạm vi</h2><p>Chỉ gửi thông tin liên hệ nếu bạn muốn nhận phản hồi cho yêu cầu này. Không có gửi email tự động hay danh sách tiếp thị.</p></div>
<div class="form-card"><form id="leadForm" action="/api/gtm/leads" method="post" novalidate>
<div><label for="name">Tên gọi</label><input id="name" name="name" autocomplete="name" maxlength="100" required></div>
<div><label for="email">Email để trả lời yêu cầu này</label><input id="email" name="email" type="email" autocomplete="email" maxlength="254" required></div>
<div><label for="company">Tên doanh nghiệp (không bắt buộc)</label><input id="company" name="company" autocomplete="organization" maxlength="160"></div>
<div><label for="need">Bạn muốn kiểm tra điều gì?</label><textarea id="need" name="need" maxlength="1200" required></textarea></div>
<div class="honeypot" aria-hidden="true"><label for="website">Website</label><input id="website" name="website" tabindex="-1" autocomplete="off"></div>
<div class="checkline"><input id="contactConsent" name="contact_consent" type="checkbox" value="yes" required><label for="contactConsent">Tôi đồng ý để AUTOProfit AI dùng thông tin này chỉ nhằm phản hồi yêu cầu kiểm tra snapshot của tôi. Có thể rút lại quyền liên hệ bất cứ lúc nào.</label></div>
<button class="button" type="submit">Gửi yêu cầu có opt-in</button><p id="formStatus" class="status" role="status" aria-live="polite"></p>
</form></div></section>
<section id="privacy" aria-labelledby="privacy-title"><div class="section-head"><h2 id="privacy-title">Quyền riêng tư và lựa chọn đo lường</h2><div class="privacy-box"><p><strong>Form liên hệ:</strong> chỉ lưu khi bạn gửi và chọn đồng ý. Báo cáo HTML/CSV không được gửi qua form. Contact list không được dùng cho newsletter.</p>
<p><strong>Analytics tùy chọn:</strong> landing view và demo start chỉ được ghi sau khi bạn chọn “Cho phép đo lường ẩn danh”; session ID ngẫu nhiên được lưu trong sessionStorage. UTM do trình duyệt cung cấp và chưa xác minh; không lưu toàn bộ URL/query, IP hay user-agent.</p>
<button id="allowAnalytics" class="button light" type="button">Cho phép đo lường ẩn danh</button> <button id="rejectAnalytics" class="button light" type="button">Tiếp tục không đo lường</button> <button id="revokeAnalytics" class="button light" type="button">Rút lại đồng ý analytics</button>
<p id="analyticsStatus" role="status" aria-live="polite"></p></div>
<form id="optOutForm" action="/api/gtm/opt-out" method="post"><div><label for="optOutEmail">Email cần rút quyền liên hệ</label><input id="optOutEmail" name="email" type="email" autocomplete="email" maxlength="254" required></div><button class="button light" type="submit">Rút lại quyền liên hệ</button><p id="optOutStatus" class="status" role="status" aria-live="polite"></p></form>
<p class="muted">Yêu cầu rút quyền luôn trả cùng một thông báo, dù email có trong CRM hay không.</p></div></section>
<footer><p>© 2026 AUTOProfit AI · Bản staging chưa được lập chỉ mục. <a href="{html.escape(EXPERIMENT['source']['url'], quote=True)}" target="_blank" rel="noopener noreferrer">Nguồn vấn đề công khai</a>.</p></footer>
</main><script>
(()=>{{'use strict';const campaign='{CAMPAIGN_ID}',consentKey='autoprofit.gtm.analytics.v1',sessionKey='autoprofit.gtm.session.v1',utmKeys=['utm_source','utm_medium','utm_campaign','utm_content','utm_term'];
const status=(id,text)=>{{const e=document.getElementById(id);if(e)e.textContent=text}};
const utm=()=>{{const p=new URLSearchParams(location.search),o={{}};for(const k of utmKeys){{const v=(p.get(k)||'').replace(/[^A-Za-z0-9._~-]/g,'').slice(0,80);if(v)o[k]=v}}return o}};
const id=()=>crypto.randomUUID?crypto.randomUUID():'';
const analyticsAllowed=()=>{{try{{return sessionStorage.getItem(consentKey)==='yes'}}catch(_){{return false}}}};
async function track(name){{if(!analyticsAllowed()||navigator.webdriver||new URLSearchParams(location.search).get('internal_test')==='1')return;let sid='';try{{sid=sessionStorage.getItem(sessionKey)||id();if(sid)sessionStorage.setItem(sessionKey,sid)}}catch(_){{return}}if(!sid)return;try{{await fetch('/api/gtm/events',{{method:'POST',credentials:'same-origin',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{event_name:name,event_id:id(),campaign_id:campaign,page_path:location.pathname,session_id:sid,analytics_consent:true,utm:utm(),internal_test:false}})}})}}catch(_){{}}}}
const analyticsChoice=sessionStorage.getItem(consentKey);if(analyticsChoice==='yes')track('landing_view');
document.getElementById('allowAnalytics').addEventListener('click',()=>{{sessionStorage.setItem(consentKey,'yes');status('analyticsStatus','Đã bật analytics ẩn danh trong tab này.');track('landing_view')}});
document.getElementById('rejectAnalytics').addEventListener('click',()=>{{sessionStorage.setItem(consentKey,'no');sessionStorage.removeItem(sessionKey);status('analyticsStatus','Không ghi analytics trong tab này.')}});
document.getElementById('revokeAnalytics').addEventListener('click',()=>{{sessionStorage.setItem(consentKey,'no');sessionStorage.removeItem(sessionKey);status('analyticsStatus','Đã rút lại consent; không gửi thêm analytics trong tab này.')}});
document.getElementById('demoStart').addEventListener('click',async e=>{{e.preventDefault();const target=e.currentTarget.href;await track('demo_start');location.href=target}});
async function submitForm(form,statusId,kind){{const out=document.getElementById(statusId);if(location.protocol==='file:'){{out.textContent='Bản preview offline: form chưa nối API. Mở staging preview trong ứng dụng để kiểm tra luồng.';return}}if(!form.reportValidity())return;const data=new FormData(form),analytics=analyticsAllowed();const payload={{name:data.get('name')||'',email:data.get('email')||'',company:data.get('company')||'',need:data.get('need')||'',website:data.get('website')||'',contact_consent:data.get('contact_consent')==='yes',campaign_id:campaign,page_path:location.pathname,analytics_consent:analytics,utm:analytics?utm():{{}},session_id:analytics?sessionStorage.getItem(sessionKey):null}};try{{const response=await fetch(form.action,{{method:'POST',credentials:'same-origin',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});const result=await response.json();if(response.ok){{form.reset();out.textContent=kind==='lead'?'Đã nhận yêu cầu. Chủ sở hữu sẽ xem xét; chưa có email nào được gửi.':'Nếu yêu cầu khớp, quyền liên hệ đã được rút lại.'}}else out.textContent=result.detail||'Không gửi được. Hãy thử lại sau.'}}catch(_){{out.textContent='Không kết nối được. Không có thông tin nào được gửi; thử lại sau.'}}}}
document.getElementById('leadForm').addEventListener('submit',e=>{{e.preventDefault();submitForm(e.currentTarget,'formStatus','lead')}});
document.getElementById('optOutForm').addEventListener('submit',e=>{{e.preventDefault();submitForm(e.currentTarget,'optOutStatus','optout')}});
}})();
</script></body></html>'''


def _tutorial_html() -> str:
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>How to review an HTML snapshot without uploading it</title></head><body><main><p>STAGING DRAFT — not published</p><h1>How to review an HTML snapshot without uploading it</h1><p>This practical tutorial uses a synthetic fixture and the offline SEO Snapshot Auditor. It does not claim to reproduce a search engine crawler.</p><ol><li>Save an HTML copy you own or have permission to review.</li><li>Open the offline demo and select the saved file.</li><li>Review title, description, viewport, H1 and image-alt observations.</li><li>Treat JavaScript-rendering findings as a clue; compare a browser-rendered view before acting.</li><li>Keep the original file and apply changes only with the site owner’s approval.</li></ol><p>The sample report and screenshot are fixture outputs. Network performance, Core Web Vitals, HTTP headers, robots and canonical behavior are not measured.</p><p><a href="demo/seo-opengraph-meta-generator.html">Open the local demo</a> · <a href="landing.html#contact">Request an opt-in scope review</a></p></main></body></html>'''


def _case_study_html(report: Mapping[str, Any]) -> str:
    observations = "".join(f"<li><code>{html.escape(str(row['check_id']))}</code> — {html.escape(str(row['observation']))}</li>" for row in report["issues"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Portfolio walkthrough — synthetic HTML fixture</title></head><body><main><p>PORTFOLIO WALKTHROUGH · SYNTHETIC FIXTURE · NOT A CUSTOMER CASE</p><h1>Reproducible static audit example</h1><p>Input: bundled synthetic HTML fixture. Source SHA-256: <code>{html.escape(report['snapshot_sha256'])}</code>. No website was crawled and no customer was interviewed.</p><h2>Observed checks</h2><ul>{observations}</ul><p>Performance timing: NOT MEASURED. The screenshot is produced by local Chromium after active scripts, handlers and external resources are removed.</p><p>These observations demonstrate tool behavior only. They are not proof of market demand or a promised search result.</p><p><a href="assets/sample-page-preview.png">Open screenshot</a> · <a href="portfolio-report.json">Open JSON report</a> · <a href="demo/seo-opengraph-meta-generator.html">Try the demo</a> · <a href="landing.html#contact">Request a scope review</a></p></main></body></html>'''


def build_content_assets(report: Mapping[str, Any]) -> dict[str, bytes]:
    """Create one owned tutorial plus source-specific community draft variants."""
    drafts = {
        "hacker_news_show_hn": {
            "title": "Show HN: Offline HTML snapshot auditor with local file processing",
            "body": "I built a small browser demo that reads a user-selected HTML snapshot locally and reports a few reproducible static checks. It does not crawl sites, measure Core Web Vitals, or claim to predict Google rankings. The attached screenshot comes from a synthetic fixture, not a customer site. I am looking for feedback on whether the report makes its limits clear.",
            "generated_by_template": True,
            "human_rewrite_required": True,
            "publication_gate": COMMUNITY_POLICIES["hacker_news_show_hn"]["publication_gate"],
            "policy_url": COMMUNITY_POLICIES["hacker_news_show_hn"]["source_url"],
        },
        "indie_hackers": {
            "title": "I built an offline HTML audit demo; what would make this report useful?",
            "body": "I made a small local HTML snapshot auditor for title, description, viewport, H1 and image-alt checks. The portfolio example is a synthetic fixture, not client work, and I have no customer or revenue results to report. It does not upload files, crawl a site, measure live performance or predict rankings. If you maintain a small-business website, what would you need to see before trusting this kind of report?",
            "generated_by_template": True,
            "human_rewrite_required": True,
            "publication_gate": COMMUNITY_POLICIES["indie_hackers"]["publication_gate"],
            "policy_url": COMMUNITY_POLICIES["indie_hackers"]["source_url"],
        },
    }
    rules = {
        "checked_date": "2026-11-08",
        "checked_by": "read-only review of the official public policy pages",
        "channels": COMMUNITY_POLICIES,
        "posting_policy": "Drafts are previews only. Recheck the live rules immediately before posting, rewrite in the owner's own words, and post manually from the owner's real account only if the community allows it.",
    }
    content = {
        "tutorial.html": _tutorial_html().encode("utf-8"),
        "case-study.html": _case_study_html(report).encode("utf-8"),
        "drafts/community-drafts.json": _json_bytes(drafts),
        "COMMUNITY_RULES.json": _json_bytes(rules),
        "COMMUNITY_RULES.md": _community_rules_markdown().encode("utf-8"),
    }
    return content


def _community_rules_markdown() -> str:
    rows = []
    for key, policy in COMMUNITY_POLICIES.items():
        rows.append(f"## {policy['label']}\n\n- Checked: {policy['checked_date']} ({policy['checked_scope']})\n- Official source: {policy['source_url']}\n" + "".join(f"- {rule}\n" for rule in policy["rules_summary"]) + f"- Gate: `{policy['publication_gate']}`\n")
    return "# Community submission policy review\n\n" + "\n".join(rows) + "\nRules can change. Recheck the official page and the destination community before each post. No draft is automatically posted.\n"


def run_accessibility_and_mobile_checks(landing: str, demo: str, *, preview_png: bytes | None = None,
                                       browser_engine: Any = None) -> tuple[GTMCheck, ...]:
    """Run a local-browser preview against accessible semantics and responsive flow."""
    from playwright.sync_api import sync_playwright
    from urllib.parse import unquote

    external_requests: list[str] = []
    analytics_payloads: list[dict[str, Any]] = []
    contact_payloads: list[dict[str, Any]] = []
    optout_payloads: list[dict[str, Any]] = []
    demo_html = demo
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 375, "height": 812}, reduced_motion="reduce")
            page = context.new_page()
            page.set_default_timeout(5000)
            # Simulate a normal visitor only inside the locally intercepted
            # fixture; the public app correctly suppresses Playwright traffic.
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")

            def route_request(route):
                url = route.request.url
                if url.startswith("http://localhost/"):
                    path = unquote(urlsplit(url).path)
                    if path in {"/", "/landing.html"}:
                        route.fulfill(status=200, content_type="text/html; charset=utf-8", body=landing)
                    elif path == "/demo/seo-opengraph-meta-generator.html":
                        route.fulfill(status=200, content_type="text/html; charset=utf-8", body=demo_html)
                    elif path == "/assets/sample-page-preview.png" and preview_png:
                        route.fulfill(status=200, content_type="image/png", body=preview_png)
                    elif path == "/api/gtm/events":
                        try:
                            analytics_payloads.append(json.loads(route.request.post_data or "{}"))
                        except ValueError:
                            pass
                        route.fulfill(status=202, content_type="application/json", body='{"accepted":true}')
                    elif path == "/api/gtm/leads":
                        try:
                            contact_payloads.append(json.loads(route.request.post_data or "{}"))
                        except ValueError:
                            pass
                        route.fulfill(status=202, content_type="application/json", body='{"accepted":true}')
                    elif path == "/api/gtm/opt-out":
                        try:
                            optout_payloads.append(json.loads(route.request.post_data or "{}"))
                        except ValueError:
                            pass
                        route.fulfill(status=202, content_type="application/json", body='{"accepted":true}')
                    else:
                        route.fulfill(status=404, body="not found")
                else:
                    external_requests.append(url)
                    route.abort()

            page.route("**/*", route_request)
            page.goto("http://localhost/landing.html", wait_until="domcontentloaded")
            mobile_ok = page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            h1_count = page.locator("h1").count()
            labels_ok = page.locator("label[for='name']").count() == 1 and page.locator("label[for='email']").count() == 1 and page.locator("label[for='need']").count() == 1
            alt_ok = page.locator("img[alt]").count() == page.locator("img").count() and page.locator("img[alt]").count() >= 1
            keyboard_ok = page.keyboard.press("Tab") is None and page.evaluate("document.activeElement.textContent.includes('Bỏ qua')")
            noindex = page.locator("meta[name='robots']").get_attribute("content") == "noindex,nofollow"
            consent_ok = page.evaluate("document.querySelector('#contactConsent').checked === false")
            page.set_viewport_size({"width": 1440, "height": 900})
            desktop_ok = page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            performance_entry = page.evaluate("performance.getEntriesByType('navigation')[0]?.domContentLoadedEventEnd || 0")
            cta_height = page.locator(".button").first.evaluate("el => el.getBoundingClientRect().height")
            checks = (
                GTMCheck("semantic_h1_and_language", h1_count == 1 and page.locator("html").get_attribute("lang") == "vi", f"h1_count={h1_count}; lang=vi"),
                GTMCheck("contact_fields_have_labels", labels_ok, "Name, email and need fields have explicit label associations."),
                GTMCheck("meaningful_image_alternative", alt_ok, "Portfolio preview images have non-empty alt text."),
                GTMCheck("keyboard_skip_link", keyboard_ok, "First keyboard tab reaches the visible skip link."),
                GTMCheck("mobile_375px_no_horizontal_overflow", bool(mobile_ok), "Checked at 375×812 with reduced motion."),
                GTMCheck("desktop_1440px_no_horizontal_overflow", bool(desktop_ok), "Checked at 1440×900."),
                GTMCheck("local_landing_dom_ready_under_5_seconds", 0 < performance_entry < 5000,
                         "Observed local DOMContentLoaded under the 5,000 ms budget with remote assets blocked; exact wall time is omitted from the reproducible manifest."),
                GTMCheck("primary_cta_meets_touch_target", cta_height >= 44,
                         f"primary CTA rendered height={round(cta_height,1)} CSS pixels."),
                GTMCheck("contact_consent_defaults_unchecked", bool(consent_ok), "Contact permission is an explicit separate opt-in."),
                GTMCheck("staging_preview_noindex", bool(noindex), "Preview stays noindex until publication is separately approved."),
                GTMCheck("no_third_party_network_requests", not external_requests, f"blocked_external_requests={len(external_requests)}"),
            )
            page.click("#demoStart")
            page.wait_for_url("**/demo/seo-opengraph-meta-generator.html")
            no_analytics_without_consent = not analytics_payloads
            page.go_back(wait_until="domcontentloaded")
            page.click("#allowAnalytics")
            page.wait_for_function("document.querySelector('#analyticsStatus').textContent.includes('Đã bật')")
            page.click("#demoStart")
            page.wait_for_url("**/demo/seo-opengraph-meta-generator.html")
            consented_demo_event = any(row.get("event_name") == "demo_start" and row.get("analytics_consent") is True for row in analytics_payloads)
            page.go_back(wait_until="domcontentloaded")
            page.fill("#name", "Synthetic Visitor")
            page.fill("#email", "visitor@example.test")
            page.fill("#need", "Please review the synthetic HTML example.")
            page.locator("#contactConsent").check()
            page.click("#leadForm button[type=submit]")
            page.wait_for_function("document.querySelector('#formStatus').textContent.includes('Đã nhận')")
            contact_sent = bool(contact_payloads and contact_payloads[-1].get("contact_consent") is True
                                and contact_payloads[-1].get("analytics_consent") is True)
            page.fill("#optOutEmail", "visitor@example.test")
            page.click("#optOutForm button[type=submit]")
            page.wait_for_function("document.querySelector('#optOutStatus').textContent.includes('Nếu yêu cầu')")
            optout_sent = bool(optout_payloads and optout_payloads[-1].get("email") == "visitor@example.test")
            checks += (
                GTMCheck("analytics_requires_separate_opt_in", no_analytics_without_consent and consented_demo_event,
                         f"events_without_consent={int(not no_analytics_without_consent)}; consented_demo_event={consented_demo_event}; events={[row.get('event_name') for row in analytics_payloads]}"),
                GTMCheck("contact_submission_requires_explicit_consent", contact_sent,
                         "The contact checkbox is required and submitted to the inbound form endpoint."),
                GTMCheck("contact_opt_out_form_submits", optout_sent,
                         "The opt-out form submits a neutral email-only suppression request."),
            )
        finally:
            browser.close()
    if any(not check.passed for check in checks):
        failed = ", ".join(f"{check.check_id}: {check.evidence}" for check in checks if not check.passed)
        raise ValueError(f"GTM landing QA failed: {failed}")
    return checks


def build_staging_bundle(*, staging_dir: Path | str | None = None,
                         public_base_url: str | None = None) -> dict[str, Any]:
    """Build a noindex GTM preview bundle only after checks pass."""
    from modules.product_builder import _studio_apps

    root = Path(staging_dir) if staging_dir else STAGING_DIR
    root.mkdir(parents=True, exist_ok=True)
    base, base_configured = _safe_base_url(public_base_url or os.getenv("AUTOPROFIT_PUBLIC_BASE_URL"))
    landing = _landing_html(base_url=base if base_configured else None, preview=True)
    report = audit_html_snapshot(SAMPLE_HTML)
    screenshot = _render_safe_preview(SAMPLE_HTML)
    app = _studio_apps().get("seo-opengraph-meta-generator")
    if not app:
        raise ValueError("Offline SEO demo is missing from the existing catalog.")
    import sys
    backend_dir = str(Path(__file__).resolve().parents[1] / "backend")
    inserted = backend_dir not in sys.path
    if inserted:
        sys.path.insert(0, backend_dir)
    try:
        import apps_library
        demo = apps_library.generate_tool_html(app).encode("utf-8")
    finally:
        if inserted:
            try:
                sys.path.remove(backend_dir)
            except ValueError:
                pass

    content = {
        "landing.html": landing.encode("utf-8"),
        "assets/sample-page-preview.png": screenshot,
        "portfolio-report.json": _json_bytes(report),
        "case-study.html": _case_study_html(report).encode("utf-8"),
        "tutorial.html": _tutorial_html().encode("utf-8"),
        "demo/seo-opengraph-meta-generator.html": demo,
        "demo/sample-input.html": SAMPLE_HTML.encode("utf-8"),
        "robots.txt": b"User-agent: *\nDisallow: /\n# Staging preview; do not crawl before owner-approved publication.\n",
        "sitemap.xml": (f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                        f"<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"><url><loc>{html.escape(base, quote=False)}/offers/website-snapshot-audit/</loc></url></urlset>\n").encode("utf-8"),
    }
    content.update(build_content_assets(report))
    link_refs = re.findall(r"(?:href|src)=\"([^\"]+)\"", landing)
    internal = [ref for ref in link_refs if not ref.startswith(("https://", "http://", "mailto:", "#"))]
    missing = [ref for ref in internal if ref.split("#", 1)[0] not in content]
    try:
        embedded = re.search(r"<script type=\"application/ld\+json\">(.*?)</script>", landing, flags=re.S)
        structured = json.loads(embedded.group(1)) if embedded else None
    except (ValueError, AttributeError):
        structured = None
    checks = list(run_accessibility_and_mobile_checks(landing, demo.decode("utf-8"), preview_png=screenshot))
    checks.extend((
        GTMCheck("internal_links_resolve", not missing, f"unresolved={missing}"),
        GTMCheck("structured_data_is_valid_json", isinstance(structured, dict) and structured.get("@type") == "WebPage", "Schema.org WebPage JSON-LD parses; no rating or price claim is included."),
        GTMCheck("sitemap_robots_are_staging_safe", b"Disallow: /" in content["robots.txt"] and b"/offers/website-snapshot-audit/" in content["sitemap.xml"], "Preview sitemap has one canonical candidate; robots disallows crawling until owner approval."),
        GTMCheck("single_experiment_and_no_fake_social_proof", len([EXPERIMENT]) == 1 and "customer testimonial" not in landing.lower() and "guaranteed" not in landing.lower(), "Exactly one experiment; no testimonial, ranking promise or fabricated outcome."),
    ))
    if any(not check.passed for check in checks):
        failed = ", ".join(check.check_id for check in checks if not check.passed)
        raise ValueError(f"GTM landing QA failed ({failed}); publication artifact was not staged.")

    manifest = {
        "schema_version": 1, "status": "STAGING_QA_PASS_NO_PUBLICATION", "campaign_id": CAMPAIGN_ID,
        "offer_id": OFFER_ID, "version": PACKAGE_VERSION, "experiment": EXPERIMENT,
        "community_policies": COMMUNITY_POLICIES,
        "publication_gate": {"public_base_url_configured": bool(base_configured), "owner_approval": False,
                              "external_posting_adapter": "NOT_CONFIGURED", "public_publish_performed": False},
        "quality_score": round(100 * sum(check.passed for check in checks) / len(checks), 1),
        "quality_score_method": "passed build-time acceptance checks / total build-time acceptance checks * 100",
        "checks": [asdict(check) for check in checks],
        "reproducible_build": {"network_used_for_build": False, "zip_timestamps_normalized": True,
                               "third_party_runtime_assets": False},
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(content.items())},
        "preview_canonical": base + "/offers/website-snapshot-audit/",
        "preview_noindex": True,
    }
    content["BUILD_MANIFEST.json"] = _json_bytes(manifest)
    archive_path = root / STAGING_PACKAGE
    with tempfile.TemporaryDirectory(prefix=".gtm-build-", dir=root) as temp_dir:
        temp_archive = Path(temp_dir) / "package.zip"
        with zipfile.ZipFile(temp_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(content.items()):
                posix = PurePosixPath(name)
                if posix.is_absolute() or ".." in posix.parts:
                    raise ValueError("Unsafe path in GTM staging artifact.")
                info = zipfile.ZipInfo(posix.as_posix(), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        digest = hashlib.sha256(temp_archive.read_bytes()).hexdigest()
        os.replace(temp_archive, archive_path)
        archive_path.with_suffix(archive_path.suffix + ".sha256").write_text(
            f"{digest}  {archive_path.name}\n", encoding="ascii")
    return {"artifact_id": archive_path.stem, "path": archive_path, "sha256": digest,
            "manifest": manifest, "preview_files": content}


def can_approve_community_draft(draft: Mapping[str, Any], *, now: date | None = None) -> tuple[bool, str]:
    channel = str(draft.get("channel") or "")
    policy = COMMUNITY_POLICIES.get(channel)
    if not policy:
        return False, "channel_policy_missing"
    today = now or date.today()
    try:
        checked = date.fromisoformat(str(policy["checked_date"]))
    except ValueError:
        return False, "channel_policy_invalid"
    if (today - checked).days < 0 or (today - checked).days > 30:
        return False, "channel_policy_stale"
    if draft.get("human_rewrite_required") and not draft.get("human_rewritten"):
        return False, "human_rewrite_required"
    if channel == "indie_hackers" and not draft.get("community_rules_rechecked"):
        return False, "community_rules_recheck_required"
    return True, "manual_owner_review_required"
