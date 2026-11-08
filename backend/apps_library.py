"""
AUTOProfit AI - GitHub Web Factory Tools Library
Generates 10+ turnkey interactive client-side web tools with built-in monetization slots.
"""
import sys
import html
from pathlib import Path
from typing import Dict, List, Any
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import CONFIG, APPS_DIR

TOOL_DEFINITIONS = [
    {
        "slug": "json-schema-seo-studio",
        "name": "JSON Schema & Data Formatter Pro",
        "category": "Developer & SEO Utilities",
        "price_usd": 2.99,
        "price_vnd": 70000,
        "description": "Format, validate and minify JSON data, generate Schema.org JSON-LD for SEO rich snippets instantly.",
        "icon": "⚡"
    },
    {
        "slug": "seo-opengraph-meta-generator",
        "name": "Offline SEO Snapshot Auditor",
        "category": "Marketing & Social Growth",
        "price_usd": None,
        "price_vnd": None,
        "pricing_model": "Free basic demo; customization, installation, and license require an owner-reviewed quote after scope and an actual order.",
        "description": "Inspect an owner-provided HTML snapshot locally for technical SEO, mobile metadata, headings, image alt text, and possible JavaScript-rendered content.",
        "icon": "🌐",
        "studio": {
            "app_type": "seo_snapshot",
            "version": "2.0.0",
            "readiness": "SOURCE_BACKED_CANDIDATE_NOT_PAID_VALIDATED",
            "evidence_categories": ["website_seo_technical_fixes"],
            "requirements": ["Local HTML file import", "Static title/description/viewport/H1/image-alt checks", "Heuristic JS-rendering indicator with explicit limitations", "JSON report export", "No network access or execution of imported HTML"],
            "unique_value_proof": "A public question reports difficulty crawling dynamic content with JavaScript disabled; this offline tool compares only the supplied source snapshot and labels that clue as a hypothesis.",
            "acceptance_tests": ["HTML file import", "Known missing metadata/accessibility checks", "Malicious script fixture stays inert", "JSON report download", "Mobile viewport and zero outbound requests"],
            "changelog": ["2.0.0: Replaced metadata-only input with local source snapshot audit and report export."],
            "license_ip_check": "Project-authored code, no external assets; owner review required before commercial redistribution.",
            "sample_dataset": "Synthetic HTML fixture only",
            "installation": "Open the standalone HTML file in a current browser.",
            "support": "Offline support package; no guaranteed SEO ranking or performance result.",
            "quality_score": None,
            "quality_status": "NOT_BUILT",
        }
    },
    {
        "slug": "vietqr-crypto-payment-generator",
        "name": "VietQR & Multi-Chain Payment Gateway",
        "category": "E-Commerce & Fintech",
        "price_usd": 3.49,
        "price_vnd": 85000,
        "description": "Generate zero-fee Napas247 VietQR codes and Binance USDT BEP20 deep-links with custom amounts.",
        "icon": "💳"
    },
    {
        "slug": "openai-tiktoken-cost-estimator",
        "name": "AI LLM Token & Cost Calculator",
        "category": "AI & Developer Tools",
        "price_usd": 2.49,
        "price_vnd": 60000,
        "description": "Calculate exact token count, input/output cost estimates across GPT-4o, Claude 3.5 Sonnet, and Gemini 2.0 Flash.",
        "icon": "🤖"
    },
    {
        "slug": "crypto-arbitrage-spread-scanner",
        "name": "Crypto CEX/DEX Arbitrage Spread Scanner",
        "category": "Web3 & Crypto Tools",
        "price_usd": 4.99,
        "price_vnd": 120000,
        "description": "Simulate and scan real-time crypto price spreads between Binance, Bybit, Uniswap, and PancakeSwap with gas estimation.",
        "icon": "📈"
    },
    {
        "slug": "defi-staking-yield-compounder",
        "name": "DeFi APY & Staking Yield Compounder",
        "category": "Web3 & Crypto Tools",
        "price_usd": 2.99,
        "price_vnd": 70000,
        "description": "Calculate daily/monthly/annual staking compound returns with flexible APY and inflation adjustments.",
        "icon": "🪙"
    },
    {
        "slug": "password-hash-security-auditor",
        "name": "Password Entropy & Hash Security Auditor",
        "category": "Cybersecurity & Privacy",
        "price_usd": 1.99,
        "price_vnd": 50000,
        "description": "Test password strength, bits of entropy, and crack time estimates with 100% offline client-side evaluation.",
        "icon": "🔒"
    },
    {
        "slug": "papaparse-csv-to-json-cleaner",
        "name": "Offline CSV Workbench — Map, Deduplicate & Export",
        "category": "Data & Automation",
        "price_usd": None,
        "price_vnd": None,
        "pricing_model": "Free basic demo; customization, installation, and license require an owner-reviewed quote after scope and an actual order.",
        "description": "Import a local CSV, map headers, normalize whitespace, deduplicate exact rows, and export formula-safe CSV with a change report.",
        "icon": "📊",
        "studio": {
            "app_type": "csv_workbench",
            "version": "2.0.0",
            "readiness": "SOURCE_BACKED_CANDIDATE_NOT_PAID_VALIDATED",
            "evidence_categories": ["csv_file_utilities", "excel_csv_cleanup"],
            "requirements": ["Local CSV file import", "Explicit JSON header mapping", "Exact normalized-row deduplication", "Formula-safe CSV export", "Change report and no data upload"],
            "unique_value_proof": "Public CSV questions provide problem signals. The tool combines explicit header mapping, deterministic deduplication, spreadsheet formula neutralization, and a local change report; paid demand and uniqueness remain unverified.",
            "acceptance_tests": ["CSV import", "Header mapping", "Duplicate row removal", "Formula injection protection", "Download round-trip", "Mobile viewport and zero outbound requests"],
            "changelog": ["2.0.0: Added local file import/export, mapping, deduplication, formula-safe output, and audit summary."],
            "license_ip_check": "Project-authored code, synthetic sample only, no external assets; owner review required before commercial redistribution.",
            "sample_dataset": "Synthetic CSV fixture only",
            "installation": "Open the standalone HTML file in a current browser.",
            "support": "Offline support package; customer files must remain under customer control.",
            "quality_score": None,
            "quality_status": "NOT_BUILT",
        }
    },
    {
        "slug": "css-glassmorphism-card-builder",
        "name": "Modern CSS Glassmorphism Studio",
        "category": "Frontend UI / UX",
        "price_usd": 1.99,
        "price_vnd": 50000,
        "description": "Visual drag-and-drop frosted glass CSS backdrop-filter generator with instant copy-paste HTML/CSS.",
        "icon": "🎨"
    },
    {
        "slug": "web3-airdrop-testnet-quest-tracker",
        "name": "Web3 Airdrop & Testnet Quest Tracker",
        "category": "Web3 & Crypto Tools",
        "price_usd": 3.99,
        "price_vnd": 95000,
        "description": "Track high-potential Layer-2 and testnet quests (Scroll, Berachain, Monad) with step-by-step checklist.",
        "icon": "🚀"
    },
    {
        "slug": "ai-prompt-markdown-converter",
        "name": "Markdown to HTML & Prompt Studio",
        "category": "Developer & AI Writing Tools",
        "price_usd": 2.49,
        "price_vnd": 60000,
        "description": "Convert Markdown into safe standalone HTML and format reusable prompt notes locally in your browser.",
        "icon": "✍️"
    },
    {
        "slug": "saas-roi-pomodoro-calculator",
        "name": "SaaS ROI & Pomodoro Calculator",
        "category": "Business & Productivity",
        "price_usd": 1.99,
        "price_vnd": 50000,
        "description": "Estimate SaaS acquisition payback and LTV-to-CAC from your inputs, with a configurable Pomodoro plan.",
        "icon": "⏱️"
    }
]


def product_studio_catalog() -> Dict[str, Any]:
    """Return all existing catalog rows without implying untested quality."""
    items = []
    for tool in TOOL_DEFINITIONS:
        studio = tool.get("studio")
        if not studio:
            studio = {
                "version": "1.0.0", "readiness": "UNVALIDATED_TEMPLATE",
                "quality_score": None, "quality_status": "NOT_BUILT",
                "note": "Legacy utility template; not approved for publication by the product studio.",
            }
        items.append({
            "slug": tool["slug"], "name": tool["name"], "category": tool["category"],
            "description": tool["description"],
            "price_usd": None if tool.get("studio") else tool["price_usd"],
            "pricing_model": (
                "Free basic demo; customization, installation or licensing requires an owner-reviewed scope and quote after an actual order."
                if tool.get("studio") else "configured_catalog_price"
            ),
            "studio": studio,
        })
    return {
        "items": items, "total": len(items), "source": "existing_product_catalog",
        "tracks": [
            {"id": "A", "name": "B2B website snapshot audit", "requires": "Current website technical-SEO opportunity plus owner-authorized HTML snapshot.", "network": "No crawl or outbound request; screenshot uses sanitized local HTML."},
            {"id": "B", "name": "CSV/Excel data workflow pack", "requires": "Current CSV/Excel source-backed opportunity.", "network": "Local file processing only; no upload or scraping."},
            {"id": "C", "name": "Offline microtool / white-label pack", "requires": "Current website and CSV source-backed opportunities.", "network": "Two existing catalog apps; no clone pages or app telemetry."},
        ],
    }


def requires_owner_quote(product: Dict[str, Any] | None) -> bool:
    """Studio demos are free; paid work needs a separately approved quote."""
    return bool(product and product.get("studio"))


def _tool_processor_js(slug: str) -> str:
    """Return the offline processor used by each generated tool page."""
    return r'''const TOOL_SLUG = __TOOL_SLUG__;

    function setActionStatus(message, isError = false, targetId = 'actionStatus') {
      const status = document.getElementById(targetId);
      if (!status) return;
      status.textContent = message;
      status.style.color = isError ? '#fca5a5' : '#86efac';
      status.style.display = 'block';
    }

    function parseObject(text, label = 'JSON') {
      let value;
      try { value = JSON.parse(text); }
      catch (error) { throw new Error(`${label} không hợp lệ: ${error.message}`); }
      if (!value || typeof value !== 'object' || Array.isArray(value)) {
        throw new Error('Dữ liệu phải là một object JSON.');
      }
      return value;
    }

    function parseCsv(text) {
      const rows = [];
      let row = [], cell = '', quoted = false;
      for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (quoted && ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
        else if (ch === '"') quoted = !quoted;
        else if (ch === ',' && !quoted) { row.push(cell); cell = ''; }
        else if ((ch === '\n' || ch === '\r') && !quoted) {
          if (ch === '\r' && text[i + 1] === '\n') i++;
          row.push(cell); cell = '';
          if (row.some(value => value.trim() !== '')) rows.push(row);
          row = [];
        } else cell += ch;
      }
      row.push(cell);
      if (row.some(value => value.trim() !== '')) rows.push(row);
      if (quoted) throw new Error('CSV có dấu ngoặc kép chưa đóng.');
      if (rows.length < 2) throw new Error('CSV cần có hàng tiêu đề và ít nhất một hàng dữ liệu.');
      const headers = rows.shift().map((value, index) => value.trim() || `column_${index + 1}`);
      const uniqueHeaders = headers.map((name, index) => {
        const occurrences = headers.slice(0, index).filter(item => item === name).length;
        return occurrences ? `${name}_${occurrences + 1}` : name;
      });
      return rows.map(values => Object.fromEntries(uniqueHeaders.map((name, index) => [name, values[index] ?? ''])));
    }

    function parseKeyValueInput(text) {
      if (text.trim().startsWith('{')) return parseObject(text);
      return Object.fromEntries(text.split(/\r?\n/).map(line => {
        const i = line.search(/[:=]/);
        return i < 0 ? [line.trim(), ''] : [line.slice(0, i).trim(), line.slice(i + 1).trim()];
      }).filter(([key]) => key));
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
    }

    async function runToolProcessor(slug, raw) {
      if (slug === 'json-schema-seo-studio') {
        let data;
        try { data = JSON.parse(raw); }
        catch (error) { throw new Error(`JSON không hợp lệ: ${error.message}`); }
        return `JSON hợp lệ\n\nĐịnh dạng dễ đọc:\n${JSON.stringify(data, null, 2)}\n\nBản minify:\n${JSON.stringify(data)}`;
      }
      if (slug === 'seo-opengraph-meta-generator') {
        const data = parseKeyValueInput(raw);
        const title = data.title || 'Tiêu đề trang';
        const description = data.description || 'Mô tả ngắn cho trang web';
        const url = data.url || '';
        const image = data.image || '';
        return `<!-- Open Graph -->\n<meta property="og:title" content="${escapeHtml(title)}">\n<meta property="og:description" content="${escapeHtml(description)}">\n<meta property="og:url" content="${escapeHtml(url)}">\n<meta property="og:image" content="${escapeHtml(image)}">\n<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="${escapeHtml(title)}">\n<meta name="twitter:description" content="${escapeHtml(description)}">`;
      }
      if (slug === 'vietqr-crypto-payment-generator') {
        const data = parseKeyValueInput(raw);
        const bank = String(data.bank || data.bank_id || '').trim();
        const account = String(data.account || data.account_number || '').replace(/\s+/g, '');
        const amount = Math.floor(Number(data.amount));
        if (!/^[A-Za-z0-9]{2,12}$/.test(bank) || !/^\d{6,20}$/.test(account) || !Number.isFinite(amount) || amount <= 0) {
          throw new Error('Nhập bank, account và amount hợp lệ. Ví dụ: {"bank":"MB","account":"123456","amount":50000,"name":"NGUYEN VAN A","memo":"ORDER-01"}.');
        }
        const name = String(data.name || '').trim();
        const memo = String(data.memo || '').trim();
        const qr = new URL(`https://img.vietqr.io/image/${bank}-${account}-compact2.png`);
        qr.searchParams.set('amount', String(amount));
        if (name) qr.searchParams.set('accountName', name);
        if (memo) qr.searchParams.set('addInfo', memo);
        return `VietQR URL:\n${qr.toString()}\n\nSố tiền: ${amount.toLocaleString('vi-VN')} VND\nNội dung: ${memo || '(chưa đặt)'}`;
      }
      if (slug === 'openai-tiktoken-cost-estimator') {
        const data = raw.trim().startsWith('{') ? parseObject(raw) : { text: raw };
        const model = String(data.model || 'gpt-4o').toLowerCase();
        const rates = {
          'gpt-4o': [2.5, 10],
          'claude-3.5-sonnet': [3, 15],
          'gemini-2.0-flash': [0.1, 0.4]
        };
        const rate = rates[model] || rates['gpt-4o'];
        const inputTokens = Math.max(0, Number(data.input_tokens ?? Math.ceil(String(data.text || '').length / 4)) || 0);
        const outputTokens = Math.max(0, Number(data.output_tokens || 0) || 0);
        const cost = inputTokens * rate[0] / 1_000_000 + outputTokens * rate[1] / 1_000_000;
        return `ƯỚC TÍNH CHI PHÍ (tham khảo; cần đối chiếu bảng giá nhà cung cấp)\nModel: ${model}\nInput: ${inputTokens.toLocaleString('vi-VN')} tokens × $${rate[0]}/1M\nOutput: ${outputTokens.toLocaleString('vi-VN')} tokens × $${rate[1]}/1M\nTổng: $${cost.toFixed(6)} USD\n\nToken từ văn bản được ước lượng xấp xỉ 4 ký tự/token.`;
      }
      if (slug === 'crypto-arbitrage-spread-scanner') {
        const data = parseObject(raw);
        const buy = Number(data.buy_price), sell = Number(data.sell_price);
        const quantity = Math.max(0, Number(data.quantity || 1));
        const buyFee = Math.max(0, Number(data.buy_fee_pct || 0)) / 100;
        const sellFee = Math.max(0, Number(data.sell_fee_pct || 0)) / 100;
        const networkFee = Math.max(0, Number(data.network_fee_usd || 0));
        if (![buy, sell, quantity, buyFee, sellFee, networkFee].every(Number.isFinite) || buy <= 0 || sell <= 0 || quantity <= 0) {
          throw new Error('Cần buy_price, sell_price dương và quantity dương; phí là tùy chọn.');
        }
        const gross = (sell - buy) * quantity;
        const costs = buy * quantity * buyFee + sell * quantity * sellFee + networkFee;
        const net = gross - costs;
        const roi = (net / (buy * quantity + buy * quantity * buyFee + networkFee)) * 100;
        return `So sánh giá do bạn nhập (không phải dữ liệu sàn trực tiếp)\nGiá mua: $${buy}\nGiá bán: $${sell}\nKhối lượng: ${quantity}\nChênh lệch gộp: $${gross.toFixed(4)}\nPhí ước tính: $${costs.toFixed(4)}\nLãi/lỗ sau phí: $${net.toFixed(4)} (${roi.toFixed(3)}%)`;
      }
      if (slug === 'defi-staking-yield-compounder') {
        const data = parseObject(raw);
        const principal = Number(data.principal), apy = Number(data.apy_percent), days = Number(data.days);
        const compounds = Math.max(1, Number(data.compounds_per_year || 365));
        if (![principal, apy, days, compounds].every(Number.isFinite) || principal < 0 || apy < 0 || days < 0) throw new Error('Cần principal, apy_percent và days là số không âm.');
        const earned = principal * Math.pow(1 + apy / 100 / compounds, compounds * days / 365) - principal;
        return `Ước tính lãi kép\nGốc: ${principal.toFixed(2)}\nAPY: ${apy}%\nThời hạn: ${days} ngày\nLãi ước tính: ${earned.toFixed(2)}\nTổng cuối kỳ: ${(principal + earned).toFixed(2)}\n\nKhông bao gồm phí, biến động giá hoặc rủi ro giao thức.`;
      }
      if (slug === 'password-hash-security-auditor') {
        if (!raw) throw new Error('Nhập mật khẩu để phân tích. Dữ liệu được xử lý trong trình duyệt và không gửi lên máy chủ.');
        let pool = 0;
        if (/[a-z]/.test(raw)) pool += 26;
        if (/[A-Z]/.test(raw)) pool += 26;
        if (/\d/.test(raw)) pool += 10;
        if (/[^A-Za-z0-9]/.test(raw)) pool += 33;
        const entropy = raw.length * Math.log2(Math.max(pool, 1));
        let digest = 'SHA-256 unavailable in this browser';
        if (globalThis.crypto?.subtle && globalThis.TextEncoder) {
          const bytes = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw));
          digest = Array.from(new Uint8Array(bytes), value => value.toString(16).padStart(2, '0')).join('');
        }
        return `Phân tích cục bộ — không hiển thị lại mật khẩu\nĐộ dài: ${raw.length} ký tự\nEntropy ước tính: ${entropy.toFixed(1)} bit\nSHA-256: ${digest}\n\nĐây là ước lượng lý thuyết; không dùng hash SHA-256 thuần để lưu mật khẩu người dùng.`;
      }
      if (slug === 'papaparse-csv-to-json-cleaner') {
        return JSON.stringify(parseCsv(raw), null, 2);
      }
      if (slug === 'css-glassmorphism-card-builder') {
        const data = raw.trim() ? parseObject(raw) : {};
        const blur = Math.min(50, Math.max(0, Number(data.blur_px ?? 16)));
        const opacity = Math.min(1, Math.max(0, Number(data.opacity ?? 0.18)));
        const color = /^#[\da-f]{3}(?:[\da-f]{3})?$/i.test(String(data.color || '#ffffff')) ? String(data.color || '#ffffff') : '#ffffff';
        const css = `.glass-card {\n  background: ${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')};\n  backdrop-filter: blur(${blur}px);\n  -webkit-backdrop-filter: blur(${blur}px);\n  border: 1px solid rgba(255, 255, 255, 0.24);\n  border-radius: 16px;\n  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);\n}`;
        return `${css}\n\nPreview HTML:\n<div class="glass-card">Nội dung thẻ</div>`;
      }
      if (slug === 'web3-airdrop-testnet-quest-tracker') {
        const tasks = raw.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
        if (!tasks.length) throw new Error('Nhập mỗi nhiệm vụ trên một dòng.');
        return JSON.stringify(tasks.map((title, index) => ({ id: index + 1, title, completed: false })), null, 2);
      }
      if (slug === 'ai-prompt-markdown-converter') {
        const source = raw.trim();
        if (!source) throw new Error('Nhập nội dung Markdown hoặc prompt trước.');
        const inline = value => escapeHtml(value)
          .replace(/`([^`]+)`/g, '<code>$1</code>')
          .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
          .replace(/\*([^*]+)\*/g, '<em>$1</em>');
        const html = source.split(/\r?\n/).map(line => {
          const heading = line.match(/^(#{1,6})\s+(.+)$/);
          if (heading) return `<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`;
          if (/^\s*[-*]\s+/.test(line)) return `<li>${inline(line.replace(/^\s*[-*]\s+/, ''))}</li>`;
          return line.trim() ? `<p>${inline(line)}</p>` : '';
        }).join('\n').replace(/(?:<li>[\s\S]*?<\/li>\n?)+/g, match => `<ul>\n${match}</ul>`);
        return `<!doctype html>\n<html lang="vi">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>Markdown Preview</title>\n<body>\n${html}\n</body>\n</html>`;
      }
      if (slug === 'saas-roi-pomodoro-calculator') {
        const data = parseKeyValueInput(raw);
        const number = (key, fallback) => {
          const value = Number(data[key] ?? fallback);
          if (!Number.isFinite(value) || value < 0) throw new Error(`${key} phải là số không âm.`);
          return value;
        };
        const mrr = number('mrr_usd', 0);
        const cac = number('cac_usd', 0);
        const churn = Math.min(99, number('monthly_churn_pct', 0)) / 100;
        const customers = number('customers', 0);
        const ltv = churn > 0 ? mrr * (1 - churn) / churn : null;
        const payback = mrr > 0 ? cac / mrr : null;
        const ltvCac = ltv !== null && cac > 0 ? ltv / cac : null;
        const work = Math.round(Math.max(5, Math.min(180, number('pomodoro_minutes', 25))));
        const rest = Math.round(Math.max(1, Math.min(60, number('break_minutes', 5))));
        return [
          'SaaS ROI estimate (based on supplied values)',
          `MRR: $${mrr.toFixed(2)} · Customers: ${customers}`,
          `CAC: $${cac.toFixed(2)} · Monthly churn: ${(churn * 100).toFixed(1)}%`,
          `Estimated CAC payback: ${payback === null ? 'enter a positive mrr_usd value' : `${payback.toFixed(1)} months`}`,
          `Estimated LTV: ${ltv === null ? 'not available (monthly_churn_pct is 0)' : `$${ltv.toFixed(2)}`}`,
          `Estimated LTV / CAC: ${ltvCac === null ? 'not available' : `${ltvCac.toFixed(2)}x`}`,
          '',
          `Pomodoro plan: ${work} minutes focus, ${rest} minutes break.`,
          'Input format: mrr_usd=49, cac_usd=120, monthly_churn_pct=5, customers=12, pomodoro_minutes=25, break_minutes=5'
        ].join('\n');
      }
      return JSON.stringify(JSON.parse(raw), null, 2);
    }

    async function processTask() {
      const input = document.getElementById('inputData');
      const out = document.getElementById('outputResult');
      const value = input.value.trim();
      if (!value && TOOL_SLUG !== 'css-glassmorphism-card-builder') {
        out.textContent = '// Vui lòng nhập dữ liệu đầu vào.';
        out.dataset.ready = 'false';
        setActionStatus('Chưa có dữ liệu đầu vào.', true);
        return;
      }
      try {
        out.textContent = await runToolProcessor(TOOL_SLUG, value);
        out.dataset.ready = 'true';
        setActionStatus('Xử lý xong.');
      } catch (error) {
        out.textContent = `Lỗi: ${error.message}`;
        out.dataset.ready = 'false';
        setActionStatus(error.message, true);
      }
    }

    async function copyText(value, statusId = 'actionStatus') {
      try {
        if (navigator.clipboard?.writeText && window.isSecureContext) {
          await navigator.clipboard.writeText(value);
          setActionStatus('Đã sao chép vào clipboard.', false, statusId);
          return true;
        }
      } catch (_) {}
      const field = document.createElement('textarea');
      field.value = value;
      field.setAttribute('readonly', '');
      field.style.position = 'fixed';
      field.style.opacity = '0';
      document.body.appendChild(field);
      field.select();
      let copied = false;
      try { copied = document.execCommand('copy'); } catch (_) {}
      field.remove();
      setActionStatus(copied ? 'Đã sao chép vào clipboard.' : 'Không thể sao chép tự động; hãy chọn và sao chép nội dung.', !copied, statusId);
      return copied;
    }

    async function copyResult() {
      const out = document.getElementById('outputResult');
      if (out.dataset.ready !== 'true') {
        setActionStatus('Chưa có kết quả để sao chép. Hãy chạy xử lý trước.', true);
        return;
      }
      await copyText(out.textContent);
    }

    function clearData() {
      document.getElementById('inputData').value = '';
      const out = document.getElementById('outputResult');
      out.textContent = '// Đã xóa dữ liệu.';
      out.dataset.ready = 'false';
      setActionStatus('Đã xóa dữ liệu.');
    }

    async function copyPaymentReference() {
      await copyText(`MUA CODE __SLUG__`, 'paymentStatus');
    }

    async function reportPaymentStatus() {
      const button = document.getElementById('reportPaymentButton');
      const paymentMethod = document.getElementById('paymentMethod').value;
      const reference = document.getElementById('paymentReference').value.trim();
      button.disabled = true;
      button.textContent = 'Đang gửi báo cáo…';
      try {
        const response = await fetch('/api/public/payment-reports', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_slug: TOOL_SLUG, payment_method: paymentMethod, reference })
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok || !result.accepted) throw new Error(result.detail || 'Không thể gửi báo cáo lúc này.');
        setActionStatus(`Đã gửi báo cáo ${result.report_id}. Trạng thái: chờ chủ cửa hàng đối soát; chưa xác nhận thanh toán và chưa cấp mã nguồn.`, false, 'paymentStatus');
      } catch (error) {
        setActionStatus(`${error.message || 'Không thể kết nối máy chủ.'} Báo cáo chưa được lưu; hãy thử lại hoặc liên hệ chủ cửa hàng.`, true, 'paymentStatus');
      } finally {
        button.disabled = false;
        button.textContent = 'Tôi đã chuyển khoản';
      }
    }

    function openCheckout() {
      const modal = document.getElementById('checkoutModal');
      modal.style.display = 'flex';
      modal.setAttribute('aria-hidden', 'false');
      setActionStatus('', false, 'paymentStatus');
    }

    function closeCheckout() {
      const modal = document.getElementById('checkoutModal');
      modal.style.display = 'none';
      modal.setAttribute('aria-hidden', 'true');
    }
    document.getElementById('checkoutModal').addEventListener('click', event => {
      if (event.target.id === 'checkoutModal') closeCheckout();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') closeCheckout();
    });
    '''.replace('__TOOL_SLUG__', json.dumps(slug)).replace('__SLUG__', slug)

def _generate_studio_tool_html(tool: Dict[str, Any]) -> str:
    """Generate a self-contained, offline-first page for audited studio tools."""
    studio = tool["studio"]
    title = html.escape(str(tool["name"]), quote=True)
    description = html.escape(str(tool["description"]), quote=True)
    app_type = str(studio.get("app_type", ""))
    common_style = """
      :root{color-scheme:dark;--bg:#0b1020;--panel:#111a2d;--line:#2a3853;--text:#e6eefb;--muted:#a6b5cb;--accent:#67d5c1}
      *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,sans-serif;padding:16px}
      main{max-width:980px;margin:0 auto}header,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:clamp(16px,4vw,28px);margin:0 0 16px}
      h1{font-size:clamp(1.35rem,4vw,2rem);line-height:1.2;margin:.3rem 0 .6rem}p{color:var(--muted)}label{display:block;margin:.8rem 0 .3rem;font-weight:650}
      textarea,input{font:inherit;width:100%;color:var(--text);background:#080d19;border:1px solid var(--line);border-radius:8px;padding:10px}
      textarea{min-height:130px;font:13px/1.45 ui-monospace,monospace}input[type=file]{max-width:100%}button{font:inherit;font-weight:650;color:#06211f;background:var(--accent);border:0;border-radius:8px;padding:10px 14px;min-height:44px;cursor:pointer}
      button.secondary{color:var(--text);background:#263651;border:1px solid var(--line)}button:disabled{opacity:.55;cursor:not-allowed}.actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
      pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#080d19;border:1px solid var(--line);border-radius:8px;padding:12px;min-height:90px;max-height:45vh;overflow:auto}
      #status{min-height:1.5em;color:var(--accent)}.badge{display:inline-block;padding:3px 9px;border:1px solid #28766b;border-radius:999px;color:var(--accent);font-size:.8rem;font-weight:700}
      .foot{font-size:.9rem;border-top:1px solid var(--line);padding-top:12px}@media(max-width:520px){body{padding:10px}.actions button{flex:1 1 100%}}
    """
    if app_type == "csv_workbench":
        controls = """
      <label for="csvFile">Choose a CSV file (max 5 MB)</label><input id="csvFile" type="file" accept=".csv,text/csv">
      <label for="inputData">Or paste CSV data locally</label><textarea id="inputData" autocomplete="off" spellcheck="false" placeholder="id,name,note&#10;1,Ada,example"></textarea>
      <label for="columnMapping">Optional header mapping (JSON object)</label><textarea id="columnMapping" rows="2" autocomplete="off" spellcheck="false" placeholder='{"old_header":"new_header"}'></textarea>
      <div class="actions"><button id="processCsv" type="button">Process locally</button><button id="downloadCsv" class="secondary" type="button" disabled>Download cleaned CSV</button><button id="downloadReport" class="secondary" type="button" disabled>Download report JSON</button><button id="clearData" class="secondary" type="button">Clear</button></div>
      <p id="status" role="status" aria-live="polite"></p><h2>Result</h2><pre id="outputResult" aria-live="polite">Your file stays in this browser.</pre>
    """
        processor = r'''(() => {
  const file = document.querySelector('#csvFile'), input = document.querySelector('#inputData'), mappingField = document.querySelector('#columnMapping');
  const output = document.querySelector('#outputResult'), status = document.querySelector('#status');
  const downloadCsv = document.querySelector('#downloadCsv'), downloadReport = document.querySelector('#downloadReport');
  let cleanedCsv = '', reportData = null;
  function parseCsv(text) {
    text = String(text).replace(/^\uFEFF/, ''); const rows=[]; let row=[], cell='', quoted=false;
    for(let i=0;i<text.length;i++){const ch=text[i];
      if(quoted&&ch==='"'&&text[i+1]==='"'){cell+='"';i++;}
      else if(ch==='"'){if(quoted)quoted=false;else if(cell==='')quoted=true;else throw new Error('Unexpected quote in CSV cell.');}
      else if(ch===','&&!quoted){row.push(cell);cell='';}
      else if((ch==='\n'||ch==='\r')&&!quoted){if(ch==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(v=>v.trim()))rows.push(row);row=[];cell='';}
      else cell+=ch;
    }
    if(quoted)throw new Error('CSV has an unclosed quoted cell.');row.push(cell);if(row.some(v=>v.trim()))rows.push(row);
    if(rows.length<2)throw new Error('CSV needs a header and at least one data row.');
    const width=rows[0].length;if(!width||width>500||rows.length>50001||rows.some(r=>r.length>width))throw new Error('CSV size or column limit exceeded.');
    let headers=rows.shift().map((v,i)=>v.trim()||`column_${i+1}`);const counts=new Map();headers=headers.map(h=>{const n=(counts.get(h)||0)+1;counts.set(h,n);return n===1?h:`${h}_${n}`;});
    return {headers,rows};
  }
  const safeCell=value=>{const text=String(value??'');return /^[\x00-\x20\u00a0\u2000-\u200b\u2028\u2029\ufeff]*[=+\-@]/.test(text)?"'"+text:text;};
  const quoteCell=value=>'"'+String(value??'').replaceAll('"','""')+'"';
  function transform(text,mapping){const parsed=parseCsv(text);const headers=parsed.headers.map(h=>String(mapping[h]??h).trim());
    if(headers.some(h=>!h)||new Set(headers).size!==headers.length)throw new Error('Mapped headers must be non-empty and unique.');
    const seen=new Set(),result=[];let duplicates=0,escaped=0,blank=0;
    for(const raw of parsed.rows){const values=parsed.headers.map((_,i)=>(raw[i]??'').trim());if(!values.some(Boolean)){blank++;continue;}
      const key=JSON.stringify(values.map(v=>v.toLocaleLowerCase()));if(seen.has(key)){duplicates++;continue;}seen.add(key);
      const safe=values.map(safeCell);escaped+=safe.filter((v,i)=>v!==values[i]).length;result.push(safe);}
    const safeHeaders=headers.map(safeCell);escaped+=safeHeaders.filter((v,i)=>v!==headers[i]).length;
    const csv=[safeHeaders,...result].map(row=>row.map(quoteCell).join(',')).join('\r\n')+'\r\n';
    return {csv,report:{input_rows:parsed.rows.length,output_rows:result.length,duplicate_rows_removed:duplicates,blank_rows_skipped:blank,formula_cells_escaped:escaped,network_requests:0,input_persisted:false}};
  }
  function save(name,text,type){const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  file.addEventListener('change',async()=>{const selected=file.files&&file.files[0];if(!selected)return;if(selected.size>5000000){status.textContent='File exceeds 5 MB.';file.value='';return;}input.value=await selected.text();status.textContent='File loaded locally; nothing uploaded.';});
  document.querySelector('#processCsv').addEventListener('click',()=>{try{const text=input.value||(file.files&&file.files[0]?input.value:'');if(!text)throw new Error('Choose a CSV or paste local CSV data.');if(new TextEncoder().encode(text).length>5000000)throw new Error('CSV exceeds 5 MB.');
    const mappingText=mappingField.value.trim();const mapping=mappingText?JSON.parse(mappingText):{};if(!mapping||Array.isArray(mapping)||typeof mapping!=='object'||Object.values(mapping).some(v=>typeof v!=='string'))throw new Error('Mapping must be a JSON object of string headers.');
    const result=transform(text,mapping);cleanedCsv=result.csv;reportData=result.report;output.textContent=JSON.stringify({...result.report,preview_csv:cleanedCsv.split('\r\n').slice(0,6).join('\n')},null,2);downloadCsv.disabled=false;downloadReport.disabled=false;status.textContent=`Processed ${result.report.input_rows} input rows; ${result.report.duplicate_rows_removed} duplicate row(s) removed.`;
  }catch(error){cleanedCsv='';reportData=null;downloadCsv.disabled=true;downloadReport.disabled=true;output.textContent='';status.textContent=error.message;}});
  downloadCsv.addEventListener('click',()=>{if(cleanedCsv)save('cleaned.csv','\uFEFF'+cleanedCsv,'text/csv;charset=utf-8');});
  downloadReport.addEventListener('click',()=>{if(reportData)save('cleaning-report.json',JSON.stringify(reportData,null,2),'application/json');});
  document.querySelector('#clearData').addEventListener('click',()=>{input.value='';file.value='';mappingField.value='';output.textContent='';status.textContent='Cleared from this page.';cleanedCsv='';reportData=null;downloadCsv.disabled=true;downloadReport.disabled=true;});
  globalThis.productStudioExports={parseCsv,transform};
})();'''
    elif app_type == "seo_snapshot":
        controls = """
      <label for="htmlFile">Choose an HTML snapshot (max 750 KB)</label><input id="htmlFile" type="file" accept=".html,.htm,text/html">
      <label for="inputData">Or paste saved HTML locally</label><textarea id="inputData" autocomplete="off" spellcheck="false" placeholder="Paste an owner-authorized HTML snapshot; scripts are parsed as data only."></textarea>
      <div class="actions"><button id="auditHtml" type="button">Audit snapshot locally</button><button id="downloadReport" class="secondary" type="button" disabled>Download report JSON</button><button id="clearData" class="secondary" type="button">Clear</button></div>
      <p id="status" role="status" aria-live="polite"></p><h2>Report</h2><pre id="outputResult" aria-live="polite">No page source has been sent or uploaded.</pre>
    """
        processor = r'''(() => {
  const file=document.querySelector('#htmlFile'),input=document.querySelector('#inputData'),output=document.querySelector('#outputResult'),status=document.querySelector('#status'),download=document.querySelector('#downloadReport');let report=null;
  file.addEventListener('change',async()=>{const selected=file.files&&file.files[0];if(!selected)return;if(selected.size>750000){status.textContent='Snapshot exceeds 750 KB.';file.value='';return;}input.value=await selected.text();status.textContent='Snapshot loaded locally; nothing uploaded.';});
  function analyze(source){if(new TextEncoder().encode(source).length>750000)throw new Error('Snapshot exceeds 750 KB.');const doc=new DOMParser().parseFromString(source,'text/html'),issues=[];const add=(check_id,severity,observation,suggestion)=>issues.push({check_id,severity,observation,suggestion});
    if(!doc.title.trim())add('seo.title.missing','high','No non-empty title element.','Add a unique descriptive title in the source HTML.');
    if(!doc.querySelector('meta[name="description"]')?.getAttribute('content')?.trim())add('seo.description.missing','medium','No meta description.','Add a concise description to the source HTML.');
    if(!doc.querySelector('meta[name="viewport"]'))add('accessibility.mobile.viewport_missing','medium','No responsive viewport declaration.','Add a viewport meta declaration and test at mobile widths.');
    const h1=doc.querySelectorAll('h1').length;if(h1!==1)add('accessibility.heading.h1_count','medium',`Found ${h1} H1 elements; expected one.`,'Use one page-level heading and preserve heading order.');
    const missingAlt=[...doc.images].filter(image=>!image.hasAttribute('alt')).length;if(missingAlt)add('accessibility.images.alt_missing','high',`${missingAlt} image(s) have no alt attribute.`,'Add meaningful alt text or alt="" for decorative images.');
    const text=(doc.body?.textContent||'').trim(),scripts=doc.scripts.length;if(scripts&&text.length<80)add('seo.rendering.js_dependency_possible','review','Source has scripts and little static text; client-rendered content may be absent when JavaScript is disabled.','Compare with a browser-rendered page; this is a hypothesis, not proof of crawler failure.');
    const external=[...doc.querySelectorAll('img[src],script[src],iframe[src],link[rel~="stylesheet"][href]')].filter(el=>/^https?:|^\/\//i.test(el.getAttribute('src')||el.getAttribute('href')||'')).length;
    return {source_bytes:new TextEncoder().encode(source).length,measurements:{title_present:!!doc.title.trim(),meta_description_present:!!doc.querySelector('meta[name="description"]')?.getAttribute('content')?.trim(),viewport_present:!!doc.querySelector('meta[name="viewport"]'),h1_count:h1,images_missing_alt:missingAlt,script_count:scripts,external_resource_references:external,performance_timing:'NOT_MEASURED; no network load or Lighthouse run'},issues,limitations:['Owner-provided HTML snapshot only; no crawl or network requests.','Script-rendering warning is heuristic and requires browser-rendered comparison.','Core Web Vitals, HTTP status, robots.txt, canonical and server headers are not measured.']};}
  function save(name,text){const url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  document.querySelector('#auditHtml').addEventListener('click',()=>{try{if(!input.value.trim())throw new Error('Choose or paste an HTML snapshot.');report=analyze(input.value);output.textContent=JSON.stringify(report,null,2);download.disabled=false;status.textContent='Audit complete. Static findings only; performance was not measured.';}catch(error){report=null;output.textContent='';download.disabled=true;status.textContent=error.message;}});
  download.addEventListener('click',()=>{if(report)save('seo-snapshot-report.json',JSON.stringify(report,null,2));});
  document.querySelector('#clearData').addEventListener('click',()=>{input.value='';file.value='';output.textContent='';status.textContent='Cleared from this page.';report=null;download.disabled=true;});
  globalThis.productStudioExports={analyze};
})();'''
    else:
        raise ValueError("Unknown studio app type.")
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="__DESCRIPTION__"><title>__TITLE__</title><style>__STYLE__</style></head><body><main>
    <header><span class="badge">FREE BASIC DEMO · OFFLINE</span><h1>__TITLE__</h1><p>__DESCRIPTION__</p></header>
    <section class="panel"><h2>Local workspace</h2><p>Choose a local file or paste data. Processing stays in this browser. No telemetry, account, ad, external asset, or upload.</p>__CONTROLS__</section>
    <section class="panel foot"><strong>Offer:</strong> Free basic demo. Customization, installation or a redistribution license is available only under a separate owner-reviewed scope and quote; no price or performance guarantee is implied. Keep a copy of original files. Code is project-authored; review license terms before redistribution.</section>
    </main><script>__PROCESSOR__</script></body></html>""".replace("__TITLE__", title).replace("__DESCRIPTION__", description).replace("__STYLE__", common_style).replace("__CONTROLS__", controls).replace("__PROCESSOR__", processor)


def generate_tool_html(tool: Dict[str, Any]) -> str:
    """Generate a catalog app; studio entries use an isolated offline template."""
    if tool.get("studio"):
        return _generate_studio_tool_html(tool)
    slug = tool["slug"]
    name = tool["name"]
    category = tool["category"]
    price_usd = tool["price_usd"]
    price_vnd = tool["price_vnd"]
    desc = tool["description"]
    processor_js = _tool_processor_js(slug)
    # Generated apps are public static pages. Never embed the owner's payout
    # destinations in generated HTML; users of the standalone VietQR tool
    # enter their own destination in the tool itself.
    bank_markup = '<p style="color:#fbbf24;">Thanh toán chưa được cấu hình cho trang công cụ này.</p>'
    payment_select = '<option value="" selected>Chưa cấu hình thanh toán</option>'
    payment_disabled = " disabled"
    top_ad_markup = (
        f"<div class='ad-banner'><iframe data-aa='{html.escape(CONFIG.AADS_UNIT_ID_TOP, quote=True)}' "
        f"src='//acceptable.a-ads.com/{html.escape(CONFIG.AADS_UNIT_ID_TOP, quote=True)}/?size=Adaptive' "
        "style='border:0;padding:0;width:100%;height:70px;overflow:hidden;'></iframe></div>"
        if CONFIG.AADS_UNIT_ID_TOP else "<div class='ad-banner' aria-label='Ad placement not configured'></div>"
    )
    bottom_ad_markup = (
        f"<div class='ad-banner'><iframe data-aa='{html.escape(CONFIG.AADS_UNIT_ID_BOTTOM, quote=True)}' "
        f"src='//acceptable.a-ads.com/{html.escape(CONFIG.AADS_UNIT_ID_BOTTOM, quote=True)}/?size=Adaptive' "
        "style='border:0;padding:0;width:100%;height:70px;overflow:hidden;'></iframe></div>"
        if CONFIG.AADS_UNIT_ID_BOTTOM else "<div class='ad-banner' aria-label='Ad placement not configured'></div>"
    )

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} — AUTOProfit AI Web Factory</title>
  <meta name="description" content="{desc}">
  <script defer src="/site-telemetry.js?v=1"></script>
  <style>
    :root {{
      --bg: #090d16;
      --card: #111827;
      --border: #1f293d;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --text: #f8fafc;
      --text-muted: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 16px;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
      width: 100%;
      flex: 1;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 18px;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      margin-bottom: 16px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      color: var(--accent);
    }}
    .tag {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }}
    .ad-banner {{
      background: #0f172a;
      border: 1px dashed #334155;
      border-radius: 8px;
      padding: 8px;
      text-align: center;
      margin-bottom: 16px;
      overflow: hidden;
      min-height: 70px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .app-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 24px;
      margin-bottom: 20px;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
    }}
    h1 {{ font-size: 22px; margin-bottom: 8px; color: #fff; }}
    p.desc {{ color: var(--text-muted); font-size: 14px; margin-bottom: 20px; }}
    .workspace {{
      display: grid;
      gap: 16px;
      margin-bottom: 20px;
    }}
    textarea, input {{
      width: 100%;
      background: #0b1120;
      border: 1px solid #243048;
      border-radius: 8px;
      color: #fff;
      padding: 12px;
      font-family: 'Courier New', Courier, monospace;
      font-size: 13px;
      resize: vertical;
    }}
    textarea:focus, input:focus {{
      outline: none;
      border-color: var(--accent);
    }}
    .btn-row {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    button, .btn {{
      padding: 10px 18px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 14px;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .btn-primary {{
      background: var(--accent);
      color: #0f172a;
    }}
    .btn-primary:hover {{ background: var(--accent-hover); color: #fff; }}
    .btn-outline {{
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text-muted);
    }}
    .btn-outline:hover {{
      border-color: var(--accent);
      color: #fff;
    }}
    .btn-buy {{
      background: #10b981;
      color: #fff;
    }}
    .btn-buy:hover {{ background: #059669; }}
    .result-box {{
      background: #080d1a;
      border: 1px solid #1e293b;
      border-radius: 8px;
      padding: 14px;
      color: #38bdf8;
      font-family: monospace;
      font-size: 13px;
      white-space: pre-wrap;
      word-break: break-all;
      min-height: 80px;
    }}
    .monetization-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.2);
      border-radius: 10px;
      padding: 14px 18px;
      margin-top: 20px;
    }}
    .modal {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.8);
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }}
    .modal-content {{
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 16px;
      padding: 24px;
      max-width: 420px;
      width: 90%;
      text-align: center;
    }}
    .checkout-field {{
      display: block;
      width: 100%;
      margin: 8px 0;
      padding: 9px 10px;
      border: 1px solid #334155;
      border-radius: 8px;
      background: #0b1120;
      color: #f8fafc;
      font: inherit;
      text-align: left;
    }}
    footer {{
      text-align: center;
      color: #64748b;
      font-size: 12px;
      margin-top: 30px;
      padding: 14px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <span>⚡ AUTOProfit AI Web Factory</span>
      </div>
      <div class="tag">{category}</div>
    </header>

    <!-- Top ad placement appears only when an ad unit is configured. -->
    {top_ad_markup}

    <main class="app-card">
      <h1>{name}</h1>
      <p class="desc">{desc}</p>

      <div class="workspace">
        <label style="font-size: 12px; color: #94a3b8; font-weight:600;">DỮ LIỆU ĐẦU VÀO:</label>
        <textarea id="inputData" rows="6" placeholder="Dán văn bản, đoạn mã hoặc tham số cần xử lý tại đây..."></textarea>
        
        <div class="btn-row">
          <button type="button" class="btn btn-primary" onclick="processTask()">🚀 Thực Thi Xử Lý</button>
          <button type="button" class="btn btn-outline" onclick="copyResult()">📋 Copy Kết Quả</button>
          <button type="button" class="btn btn-outline" onclick="clearData()">✕ Xóa</button>
        </div>
        <div id="actionStatus" role="status" aria-live="polite" style="display:none; font-size:12px; margin-top:8px;"></div>

        <label style="font-size: 12px; color: #94a3b8; font-weight:600; margin-top: 10px;">KẾT QUẢ TỨC THÌ:</label>
        <div id="outputResult" class="result-box">// Kết quả đã xử lý sẽ xuất hiện tại đây...</div>
      </div>

      <div class="monetization-bar">
        <div>
          <div style="font-weight: 700; color: #10b981; font-size: 14px;">Tải Mã Nguồn Độc Lập (.html)</div>
          <div style="font-size: 12px; color: #94a3b8;">Sở hữu toàn bộ mã nguồn sạch không quảng cáo: ${price_usd} USD (~{price_vnd:,}đ)</div>
        </div>
        <button type="button" class="btn btn-buy" onclick="openCheckout()">🛒 Mua Mã Nguồn</button>
      </div>
    </main>

    <!-- Bottom ad placement appears only when an ad unit is configured. -->
    {bottom_ad_markup}

    <footer>
      Hệ thống Web App thương mại tự động hóa bởi AUTOProfit AI Enterprise &copy; 2026.
    </footer>
  </div>

  <!-- Checkout Modal -->
  <div id="checkoutModal" class="modal" role="presentation" aria-hidden="true">
    <div class="modal-content" role="dialog" aria-modal="true" aria-labelledby="checkoutTitle">
      <h3 id="checkoutTitle" style="margin-bottom: 8px;">Thanh Toán Bản Quyền Mã Nguồn</h3>
      <p style="font-size: 13px; color: #94a3b8; margin-bottom: 16px;">Sản phẩm: {name}</p>
      
      <div style="background: #1e293b; padding: 14px; border-radius: 10px; margin-bottom: 14px;">
        {bank_markup}
        <div style="font-size: 13px; color: #38bdf8; font-weight:700; margin-top: 6px;">Số tiền: {price_vnd:,} VND</div>
      </div>

      <p style="font-size:12px; color:#fbbf24; margin-bottom:8px;">Báo cáo sẽ được lưu để đối soát thủ công. Hệ thống không tự xác minh giao dịch hoặc cấp mã nguồn.</p>
      <label for="paymentMethod" style="display:block; text-align:left; font-size:12px; color:#cbd5e1;">Phương thức thanh toán</label>
      <select id="paymentMethod" class="checkout-field">
        {payment_select}
      </select>
      <label for="paymentReference" style="display:block; text-align:left; font-size:12px; color:#cbd5e1;">Mã giao dịch hoặc ghi chú (không bắt buộc)</label>
      <input id="paymentReference" class="checkout-field" type="text" maxlength="120" autocomplete="off" placeholder="Nhập mã giao dịch để chủ cửa hàng đối soát nhanh hơn">

      <div style="display: flex; gap: 8px; justify-content: center;">
        <button type="button" class="btn btn-outline" onclick="copyPaymentReference()">📋 Sao chép nội dung chuyển khoản</button>
        <button type="button" id="reportPaymentButton" class="btn btn-primary" onclick="reportPaymentStatus()"{payment_disabled}>Tôi đã chuyển khoản</button>
        <button type="button" class="btn btn-outline" onclick="closeCheckout()">Đóng</button>
      </div>
      <div id="paymentStatus" role="status" aria-live="polite" style="display:none; font-size:12px; margin-top:12px;"></div>
    </div>
  </div>

  <script>
    {processor_js}
  </script>
</body>
</html>
"""

def build_all_tools():
    """Generates all tool HTML files into frontend/apps directory."""
    APPS_DIR.mkdir(parents=True, exist_ok=True)
    for tool in TOOL_DEFINITIONS:
        content = generate_tool_html(tool)
        file_path = APPS_DIR / f"{tool['slug']}.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"Generated {len(TOOL_DEFINITIONS)} web apps successfully in {APPS_DIR}.")

if __name__ == "__main__":
    build_all_tools()
