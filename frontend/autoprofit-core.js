

    // =========================================================================

    // CONFIGURATION & ENDPOINT RESOLUTION (ZERO EMBEDDED SECRETS)

    // =========================================================================



    // === 🛡️ CHROME LOCAL NETWORK ACCESS (LNA) POPUP BLOCKER FOR PUBLIC VISITORS ===

    (function() {

      var h = (window.location && window.location.hostname) || '';

      var p = (window.location && window.location.protocol) || '';

      var isLocal = (h === '127.0.0.1' || h === 'localhost' || p === 'file:');

      window.__IS_LOCAL_OWNER_ENV__ = isLocal;

      if (!isLocal) {

        var origFetch = window.fetch;

        if (typeof origFetch === 'function') {

          window.fetch = function(input, init) {

            try {

              var u = (typeof input === 'string') ? input : (input && input.url) || '';

              if (u.indexOf('127.0.0.1') !== -1 || u.indexOf('localhost') !== -1 || u.indexOf('0.0.0.0') !== -1) {

                return Promise.resolve(new Response('{}', { status: 204, headers: { 'Content-Type': 'application/json' } }));

              }

            } catch (_) {}

            return origFetch.apply(this, arguments);

          };

        }

        if (typeof XMLHttpRequest !== 'undefined' && XMLHttpRequest.prototype && XMLHttpRequest.prototype.open) {

          var origOpen = XMLHttpRequest.prototype.open;

          var origSend = XMLHttpRequest.prototype.send;

          XMLHttpRequest.prototype.open = function(method, url) {

            this.__blockedLoopback = (typeof url === 'string' && (url.indexOf('127.0.0.1') !== -1 || url.indexOf('localhost') !== -1));

            if (this.__blockedLoopback) {

              return origOpen.call(this, method, 'data:application/json,%7B%7D', true);

            }

            return origOpen.apply(this, arguments);

          };

          XMLHttpRequest.prototype.send = function() {

            if (this.__blockedLoopback) return;

            return origSend.apply(this, arguments);

          };

        }

      }

    })();



    const DEFAULT_TUNNEL_URL = window.location && window.location.origin ? window.location.origin : '';

    const LOCAL_BACKEND_URL = 'http://127.0.0.1:8450';



    function resolveInitialApiBase() {
      const saved = localStorage.getItem('autoprofit_api_base');
      if (saved) return saved.replace(/\/+$/, '');
      if (window.location && window.location.origin && window.location.protocol.startsWith('http')) {
        return window.location.origin;
      }
      return LOCAL_BACKEND_URL;
    }



    let API_BASE = resolveInitialApiBase();



    // Auto-probe local backend (127.0.0.1:8000) so all tabs on Owner PC share the exact same fast local DB connection

    (async function autoProbeLocalBackendForUnifiedSync() {

      if (!window.__IS_LOCAL_OWNER_ENV__ || API_BASE === LOCAL_BACKEND_URL || document.body?.classList.contains('ap-reference-ui')) return;

      try {

        const ctrl = new AbortController();

        const tid = setTimeout(() => ctrl.abort(), 1800);

        const r = await fetch(LOCAL_BACKEND_URL + '/api/health', { signal: ctrl.signal });

        clearTimeout(tid);

        if (r && r.ok) {

          API_BASE = LOCAL_BACKEND_URL;

          if (typeof sendVisitorTrafficHeartbeat === 'function') {

            sendVisitorTrafficHeartbeat(false);

          }

        }

      } catch (_) {}

    })();

    window.addEventListener('storage', function(ev) {

      if (ev.key === 'autoprofit_unified_traffic_v3' && ev.newValue) {

        try {

          const synced = JSON.parse(ev.newValue);

          if (synced && typeof renderLiveTrafficAndAadsStats === 'function') {

            renderLiveTrafficAndAadsStats(synced, true);

          }

        } catch (_) {}

      }

    });



    let CURRENT_LANG = localStorage.getItem('autoprofit_lang') || 'vi';

    let CURRENT_VIEW_ID = 'overview';

    let SELECTED_AGENT_ID = null;

    let POLLING_ACTIVE = true;

    let POLLING_TIMER = null;

    let REDUCED_MOTION = localStorage.getItem('autoprofit_reduced_motion') === '1';

    let MOVEMENT_ENABLED = !REDUCED_MOTION;

    let DIAGNOSTICS_3D_OPEN = false;

    let STAGE_DIAGNOSTICS_OPEN = false;

    let CURRENT_3D_STAGE_SIZE = 'COMPACT';

    let OVERVIEW_TASK_FILTER = 'ALL';

    let LAST_AUTONOMOUS_COLLAB_AT = 0;

    let LAST_SELECTED_QUOTE_CALC = null;



    function t(viText, enText) {

      return CURRENT_LANG === 'en' ? enText : viText;

    }



    const AGENT_META_BILINGUAL = {

      RESEARCH_AGENT: {

        titleVi: 'AI Nghiên Cứu Thị Trường',

        titleEn: 'Market Research Agent',

        shortVi: 'Lê Minh',

        shortEn: 'Le Minh',

        zoneVi: '1. Phòng Nghiên Cứu Thị Trường',

        zoneEn: '1. Market Research Lab',

        subVi: 'Trung Tâm Quét Nhu Cầu & Tín Hiệu',

        subEn: 'Market Signal & Opportunity Scanner',

        equipVi: 'Đĩa thu vệ tinh Radar & Màn hình quét tín hiệu HN/GitHub',

        equipEn: 'Satellite Radar Array & Live HN/GitHub Signal Scanners',

        stepVi: 'Bước 1-2 / 13',

        stepEn: 'Step 1-2 / 13',

        dutyVi: 'Quét tín hiệu thị trường và nhu cầu dịch vụ có nguồn xác thực (HackerNews, Dev.to, Arbeitnow).',

        dutyEn: 'Scans verified market signals and service demand from legal public APIs (HackerNews, Dev.to, Arbeitnow).'

      },

      PRODUCT_AGENT: {

        titleVi: 'AI Kiến Trúc Sản Phẩm',

        titleEn: 'Product Architect Agent',

        shortVi: 'Hoàng Bách',

        shortEn: 'Hoang Bach',

        zoneVi: '2. Xưởng Kiến Trúc Sản Phẩm',

        zoneEn: '2. Product Architecture Bay',

        subVi: 'Thiết Kế Gói Dịch Vụ & Định Giá',

        subEn: 'Service Packaging & Pricing Studio',

        equipVi: 'Bàn chiếu Hologram 3D & Trạm đóng gói sản phẩm số',

        equipEn: '3D Hologram Blueprint Table & Digital Packaging Station',

        stepVi: 'Bước 4 / 13',

        stepEn: 'Step 4 / 13',

        dutyVi: 'Định nghĩa gói dịch vụ Kiểm Toán Kỹ Thuật Website & Tối Ưu SEO, phạm vi bàn giao và mức giá minh bạch.',

        dutyEn: 'Defines the Website Technical Audit & SEO Fix service package, deliverable scope, and transparent pricing.'

      },

      CODING_AGENT: {

        titleVi: 'AI Lập Trình & Kiểm Toán',

        titleEn: 'Coding & Audit Agent',

        shortVi: 'Vũ Khoa',

        shortEn: 'Vu Khoa',

        zoneVi: '3. Trung Tâm Lập Trình & Kiểm Toán',

        zoneEn: '3. Code & Diagnostic Forge',

        subVi: 'Biên Dịch Mã Nguồn & Kiểm Toán HTML/SEO',

        subEn: 'Python Compiler & Live HTML/SEO Auditor',

        equipVi: 'Cụm máy chủ biên dịch Python & Trạm tự kiểm thử HTML/SEO',

        equipEn: 'Python Compilation Cluster & Automated HTML/SEO Test Bench',

        stepVi: 'Bước 5 / 13',

        stepEn: 'Step 5 / 13',

        dutyVi: 'Thực thi bộ công cụ kiểm toán kỹ thuật HTML/SEO/Schema trực tiếp và tự kiểm thử mã nguồn.',

        dutyEn: 'Executes the live HTML/SEO/Schema technical audit engine and runs automated code self-tests.'

      },

      MARKETING_AGENT: {

        titleVi: 'AI Tiếp Thị & Nội Dung SEO',

        titleEn: 'Marketing & SEO Agent',

        shortVi: 'Phạm Thảo',

        shortEn: 'Pham Thao',

        zoneVi: '4. Phòng Nội Dung & Tiếp Thị',

        zoneEn: '4. Content & SEO Studio',

        subVi: 'Sản Xuất Nội Dung & Tối Ưu Tìm Kiếm',

        subEn: 'Technical Content & Search Optimization',

        equipVi: 'Tháp phát sóng nội dung SEO & Bảng phân tích từ khóa',

        equipEn: 'SEO Content Broadcast Tower & Keyword Analytics Console',

        stepVi: 'Bước 7 / 13',

        stepEn: 'Step 7 / 13',

        dutyVi: 'Tạo nội dung bài viết kỹ thuật & tài sản SEO hợp chuẩn, minh bạch, không gửi thư rác.',

        dutyEn: 'Generates compliant technical articles and SEO assets with full disclosure and zero spam.'

      },

      SALES_AGENT: {

        titleVi: 'AI Tìm Khách & Báo Giá',

        titleEn: 'Lead & Sales Agent',

        shortVi: 'Đặng Quân',

        shortEn: 'Dang Quan',

        zoneVi: '5. Trung Tâm Khách Hàng & Báo Giá',

        zoneEn: '5. Lead & Sales Hub',

        subVi: 'Chẩn Đoán Website & Soạn Đề Xuất',

        subEn: 'Lead Discovery & Custom Proposal Desk',

        equipVi: 'Quả cầu quét doanh nghiệp & Bàn soạn đề xuất cá nhân hóa',

        equipEn: 'Business Discovery Globe & Personalized B2B Proposal Terminal',

        stepVi: 'Bước 8-9 / 13',

        stepEn: 'Step 8-9 / 13',

        dutyVi: 'Quét doanh nghiệp thật, kiểm toán lỗi trang web và soạn đề xuất cá nhân hóa tự động phê duyệt & gửi báo giá 24/7.',

        dutyEn: 'Discovers real businesses, audits website defects, and drafts personalized proposals awaiting Owner approval.'

      },

      CUSTOMER_SUPPORT_AGENT: {

        titleVi: 'AI Hỗ Trợ & Bàn Giao',

        titleEn: 'Support & Delivery Agent',

        shortVi: 'Khánh Linh',

        shortEn: 'Khanh Linh',

        zoneVi: '6. Trạm Bàn Giao & Hỗ Trợ',

        zoneEn: '6. Order & Delivery Center',

        subVi: 'Quản Lý Đơn Hàng & Bàn Giao Tự Động',

        subEn: 'Order Fulfillment & Automated Delivery',

        equipVi: 'Cổng bàn giao gói mã nguồn tự động (Bảo vệ HTTP 402)',

        equipEn: 'Automated Deliverable Gateway (HTTP 402 Payment Guard)',

        stepVi: 'Bước 10 / 13',

        stepEn: 'Step 10 / 13',

        dutyVi: 'Theo dõi trạng thái đơn hàng, hướng dẫn thanh toán và mở khóa bàn giao sản phẩm sau khi xác minh thanh toán.',

        dutyEn: 'Tracks order status, assists with payment instructions, and unlocks deliverables after verified settlement.'

      },

      FINANCE_AGENT: {

        titleVi: 'AI Tài Chính & On-Chain',

        titleEn: 'Finance & Blockchain Agent',

        shortVi: 'Bảo Trâm',

        shortEn: 'Bao Tram',

        zoneVi: '7. Két Đối Soát Tài Chính',

        zoneEn: '7. Finance & Blockchain Vault',

        subVi: 'Xác Minh Giao Dịch BSC & Sao Kê',

        subEn: 'On-Chain BSC & Bank Statement Reconciliation',

        equipVi: 'Nút mạng BSC Mainnet, Cổng VietQR & Sổ cái 9 khoản mục',

        equipEn: 'BSC Mainnet RPC Node, VietQR Gateway & 9-Bucket Ledger',

        stepVi: 'Bước 11 / 13',

        stepEn: 'Step 11 / 13',

        dutyVi: 'Đối soát giao dịch USDT BEP20 trên mạng BSC / chuyển khoản ngân hàng và hạch toán 9 khoản mục tài chính trung thực.',

        dutyEn: 'Verifies on-chain USDT BEP20 / bank transfers and maintains the honest 9-bucket financial accounting ledger.'

      },

      OPTIMIZATION_AGENT: {

        titleVi: 'AI Tối Ưu Hóa Chiến Lược',

        titleEn: 'Strategy & ROI Agent',

        shortVi: 'Minh Châu',

        shortEn: 'Minh Chau',

        zoneVi: '8. Phòng Chiến Lược & Tối Ưu',

        zoneEn: '8. Strategy & ROI Room',

        subVi: 'Phân Tích Chuyển Đổi & Điều Chỉnh Giá',

        subEn: 'Conversion Analytics & Pricing Strategy',

        equipVi: 'Bàn mô phỏng thử nghiệm & Biểu đồ phân tích chuyển đổi',

        equipEn: 'Funnel Simulation Table & ROI Conversion Telemetry',

        stepVi: 'Bước 12-13 / 13',

        stepEn: 'Step 12-13 / 13',

        dutyVi: 'Đánh giá tỷ lệ chuyển đổi, hiệu quả chi phí vận hành và đề xuất chiến lược giá cho Chủ sở hữu.',

        dutyEn: 'Evaluates conversion rates, operating cost efficiency, and recommends pricing adjustments to the Owner.'

      },

            SECURITY_AGENT: {

        titleVi: 'AI Bảo Mật & Kiểm Soát',

        titleEn: 'Security & Guardrail Agent',

        shortVi: 'Trần Phong',

        shortEn: 'Tran Phong',

        zoneVi: '9. Pháo Đài Bảo Mật & Kiểm Soát',

        zoneEn: '9. Security & Guardrail Bastion',

        subVi: 'Giám Sát Ngân Sách & Phân Quyền',

        subEn: 'RBAC, Budget Guardrail & Audit Monitor',

        equipVi: 'Tường lửa lục giác phân quyền, Khóa chống chạy trùng & Dừng khẩn cấp',

        equipEn: 'Hexagonal RBAC Firewall, Single-Worker Lock & Emergency Stop',

        stepVi: 'Bước 3 & Giám sát liên tục',

        stepEn: 'Step 3 & Continuous Guardrail',

        dutyVi: 'Giám sát hạn mức ngân sách, khóa chống chạy trùng, phân quyền quản trị, dừng khẩn cấp và nhật ký bảo mật.',

        dutyEn: 'Enforces budget limits, single-worker locks, RBAC permissions, emergency stop, and security audit logs.'

      },

      AFFILIATE_AMAZON_AGENT: {

        titleVi: 'Mai Anh — AI Chuyên Gia Affiliate Amazon, Shopee & TikTok',

        titleEn: 'Mai Anh — Amazon, Shopee & TikTok Affiliate Specialist',

        shortVi: 'Mai Anh (Amazon)',

        shortEn: 'Mai Anh (Amazon)',

        zoneVi: '10. Bàn Affiliate Amazon & Shopee (Mai Anh)',

        zoneEn: '10. Amazon & E-Com Affiliate Desk',

        subVi: 'Săn Deal Amazon Tech & Tiếp Thị Liên Kết Đa Sàn',

        subEn: 'Amazon Associates & Flash Deal Affiliate Engine',

        equipVi: 'Hệ thống quét Best-Seller Amazon US/Global & Tự động tạo bài Review chuẩn SEO',

        equipEn: 'Amazon Best-Seller Scanner & Automated SEO Review Publisher',

        stepVi: 'Trực chiến 24/7',

        stepEn: '24/7 Active',

        dutyVi: 'Tự động quét sản phẩm công nghệ, phần cứng AI, thiết bị thông minh bán chạy trên Amazon, Shopee, TikTok Shop; viết bài đánh giá so sánh và gắn link Affiliate hưởng hoa hồng 4%–18%.',

        dutyEn: 'Scans top-converting tech & AI hardware on Amazon, Shopee, and TikTok Shop; publishes SEO comparison reviews with embedded affiliate links (4%–18% commission).'

      },

      SHOPIFY_ECOM_AGENT: {

        titleVi: 'Quốc Tuấn — AI Chuyên Gia Shopify Partner & SaaS Affiliate',

        titleEn: 'Quoc Tuan — Shopify Partner & SaaS Affiliate Specialist',

        shortVi: 'Quốc Tuấn (Shopify)',

        shortEn: 'Quoc Tuan (Shopify)',

        zoneVi: '11. Bàn Shopify Partner & SaaS AI (Quốc Tuấn)',

        zoneEn: '11. Shopify Partner & SaaS Recurring Desk',

        subVi: 'Tiếp Thị Liên Kết Phần Mềm SaaS & Dựng Store Shopify',

        subEn: 'Shopify Partner Referrals & SaaS Recurring Commissions',

        equipVi: 'Trạm kết nối Shopify Partner API, Semrush, Hostinger, Cursor & AI SaaS',

        equipEn: 'Shopify Partner API, Cloud Hosting & AI SaaS Affiliate Hub',

        stepVi: 'Trực chiến 24/7',

        stepEn: '24/7 Active',

        dutyVi: 'Triển khai chiến dịch tiếp thị liên kết cho Shopify ($25–$150/store), phần mềm AI SaaS và Hosting quốc tế hưởng hoa hồng định kỳ trọn đời 20%–50% mỗi tháng.',

        dutyEn: 'Runs high-ticket affiliate campaigns for Shopify Partners ($25–$150 bounty) and recurring AI SaaS tools (20%–50% monthly recurring commission).'

      },

      CRYPTO_ARBITRAGE_AGENT: {

        titleVi: 'Hải Đăng — AI Chuyên Gia Arbitrage Crypto & Referral Sàn',

        titleEn: 'Hai Dang — Crypto Arbitrage & Exchange Referral Specialist',

        shortVi: 'Hải Đăng (Crypto)',

        shortEn: 'Hai Dang (Crypto)',

        zoneVi: '12. Bàn Radar Crypto Arbitrage & DeFi (Hải Đăng)',

        zoneEn: '12. Crypto Arbitrage & Exchange Referral Desk',

        subVi: 'Quét Chênh Lệch Giá CEX/DEX & Hoa Hồng Sàn Giao Dịch',

        subEn: 'CEX/DEX Spread Scanner & 40% Exchange Fee Rebates',

        equipVi: 'Cụm màn hình đọc sổ lệnh Binance, Bybit, OKX, Uniswap & PancakeSwap',

        equipEn: 'Real-Time Binance, Bybit, OKX & DEX Orderbook Spread Terminal',

        stepVi: 'Trực chiến 24/7',

        stepEn: '24/7 Active',

        dutyVi: 'Quét chênh lệch giá BTC/ETH/SOL/BNB giữa các sàn CEX/DEX, tối ưu lãi suất gửi USDT DeFi APY cao và thu hoa hồng giới thiệu sàn 30%–50% phí giao dịch.',

        dutyEn: 'Scans live CEX/DEX price spreads, tracks audited DeFi stablecoin APY, and monetizes crypto exchange/cold-wallet referral links (30%–50% fee share).'

      },

      AIRDROP_BOUNTY_AGENT: {

        titleVi: 'Thanh Hà — AI Chuyên Gia Săn Airdrop Web3 & Bug Bounty',

        titleEn: 'Thanh Ha — Web3 Airdrop & Open-Source Bounty Hunter',

        shortVi: 'Thanh Hà (Airdrop)',

        shortEn: 'Thanh Ha (Airdrop)',

        zoneVi: '13. Bàn Săn Airdrop Layer-2 & Bug Bounty (Thanh Hà)',

        zoneEn: '13. Web3 Airdrop & Bug Bounty Desk',

        subVi: 'Săn Thưởng Testnet Vốn $0 & Giải Thưởng Vá Lỗi GitHub',

        subEn: 'Zero-Cost L2 Testnet Quests & Algora/Immunefi Bounties',

        equipVi: 'Hệ thống theo dõi nhiệm vụ On-chain Monad, Berachain, Linea & Algora PR',

        equipEn: 'On-Chain Quest Tracker & Algora/Immunefi Bounty Scanner',

        stepVi: 'Trực chiến 24/7',

        stepEn: '24/7 Active',

        dutyVi: 'Tự động theo dõi các chiến dịch Airdrop Web3 vốn $0 (Monad, Berachain, Linea, Scroll) và săn nhiệm vụ vá lỗi mã nguồn mở có thưởng tiền mặt ($50–$500 USDT).',

        dutyEn: 'Tracks zero-cost Web3 Layer-2 airdrops and hunts open-source GitHub Algora / Immunefi bug bounties ($50–$500 USDT per issue).'

      },

      VIRAL_TRAFFIC_AGENT: {

        titleVi: 'Gia Huy — Soạn Bản Nháp Phân Phối Nội Dung',

        titleEn: 'Gia Huy — Distribution Draft Editor',

        shortVi: 'Gia Huy (Traffic)',

        shortEn: 'Gia Huy (Traffic)',

        zoneVi: '14. Bàn Soạn Nháp Phân Phối Nội Dung',

        zoneEn: '14. Owner-Reviewed Distribution Drafts',

        subVi: 'Bản Nháp Affiliate & Web Tool Chờ Chủ Sở Hữu Duyệt',

        subEn: 'Affiliate and web-tool drafts; no automatic posting',

        equipVi: 'Bản thảo nội dung và danh sách kiểm tra quy tắc cộng đồng',

        equipEn: 'Content drafts and community-rule checklist',

        stepVi: 'Chờ chủ sở hữu duyệt',

        stepEn: 'Owner review required',

        dutyVi: 'Chuẩn bị bản nháp nội dung affiliate và công cụ web để chủ sở hữu tự rà soát, phê duyệt và chia sẻ theo quy định từng cộng đồng. Không tự đăng bài hoặc tạo lượt hiển thị quảng cáo.',

        dutyEn: 'Prepares affiliate and web-tool content drafts for owner review and policy-compliant sharing. It does not publish automatically or generate ad impressions.'

      },

      TEMPLATE_POD_AGENT: {

        titleVi: 'Phương Nghi — AI Thiết Kế Template Notion, Theme Shopify & POD',

        titleEn: 'Phuong Nghi — Notion Template, Shopify Theme & POD Designer',

        shortVi: 'Phương Nghi (POD)',

        shortEn: 'Phuong Nghi (POD)',

        zoneVi: '15. Xưởng Thiết Kế Template Số & POD (Phương Nghi)',

        zoneEn: '15. Digital Templates & Print-on-Demand Studio',

        subVi: 'Đóng Gói Mẫu Notion, Canva, Theme Web & Áo POD Quốc Tế',

        subEn: 'Notion Templates, UI Kits, Shopify Themes & POD Assets',

        equipVi: 'Bảng vẽ đồ họa AI Vector & Trạm xuất bản sản phẩm số tự động',

        equipEn: 'AI Vector Design Canvas & Digital Product Publishing Engine',

        stepVi: 'Trực chiến 24/7',

        stepEn: '24/7 Active',

        dutyVi: 'Thiết kế các bộ mẫu Notion quản lý tài chính, Canva Kit, Theme Landing Page Shopify và mẫu in Print-on-Demand bán giá bình dân $1.99–$3.99 USD.',

        dutyEn: 'Creates high-demand Notion templates, Shopify landing themes, and Print-on-Demand digital assets priced at $1.99–$3.99 USD.'

      }

    };



    function formatAgentTitle(role, fallbackTitle = '') {

      const m = AGENT_META_BILINGUAL[role];

      if (!m) return fallbackTitle || role;

      return CURRENT_LANG === 'en' ? m.titleEn : m.titleVi;

    }



    function formatAgentShort(role) {

      const m = AGENT_META_BILINGUAL[role];

      if (!m) return role;

      return CURRENT_LANG === 'en' ? m.shortEn : m.shortVi;

    }



    function formatZoneName(role) {

      const m = AGENT_META_BILINGUAL[role];

      if (!m) return role;

      return CURRENT_LANG === 'en' ? m.zoneEn : m.zoneVi;

    }



    function formatZoneSub(role) {

      const m = AGENT_META_BILINGUAL[role];

      if (!m) return '';

      return CURRENT_LANG === 'en' ? m.subEn : m.subVi;

    }



    function formatZoneEquip(role) {

      const m = AGENT_META_BILINGUAL[role];

      if (!m) return '';

      return CURRENT_LANG === 'en' ? m.equipEn : m.equipVi;

    }



    function formatAgentStep(role, rawStep = '') {

      const m = AGENT_META_BILINGUAL[role];

      if (m) return CURRENT_LANG === 'en' ? m.stepEn : m.stepVi;

      return rawStep;

    }



    function formatStatusLabel(st) {

      const code = String(st || 'IDLE').toUpperCase();

      if (CURRENT_LANG === 'en') return code;

      const mapVi = {

        WORKING: 'ĐANG LÀM VIỆC',

        RUNNING: 'ĐANG CHẠY',

        SUCCESS: 'HOÀN THÀNH',

        COMPLETED: 'HOÀN THÀNH',

        THINKING: 'ĐANG PHÂN TÍCH',

        PLANNED: 'ĐÃ LẬP KẾ HOẠCH',

        WAITING_APPROVAL: 'CHỜ PHÊ DUYỆT',

        WAITING_FOR_APPROVAL: 'CHỜ PHÊ DUYỆT',

        AWAITING_APPROVAL: 'CHỜ PHÊ DUYỆT',

        WAITING: 'CHỜ DUYỆT',

        IDLE: 'ĐANG NGHỈ',

        ERROR: 'LỖI THỰC THI',

        FAILED: 'THẤT BẠI',

        BLOCKED: 'BỊ CHẶN',

        OFFLINE: 'NGOẠI TUYẾN',

        STOPPED: 'ĐÃ DỪNG',

        PAUSED: 'TẠM DỪNG',

        EMERGENCY_STOP: 'DỪNG KHẨN CẤP',

        COMMUNICATING: 'ĐANG GIAO TIẾP',

        WALK: 'ĐANG DI CHUYỂN',

        RUN: 'ĐANG CHẠY NHANH',

        PENDING_PAYMENT: 'CHỜ THANH TOÁN',

        PENDING_VERIFICATION: 'CHỜ ĐỐI SOÁT',

        FULFILLED: 'ĐÃ HOÀN TẤT',

        PAID_VERIFIED: 'ĐÃ XÁC MINH TT',

        PUBLISHED: 'ĐÃ XUẤT BẢN',

        ALLOWED: 'HỢP LỆ',

        DENIED: 'TỪ CHỐI',

        PASSED: 'ĐẠT KIỂM THỬ',

        DELIVERED: 'ĐÃ GỬI',

        PROCESSED: 'ĐÃ XỬ LÝ',

        DEMO_ONLY: 'CHỈ THỬ NGHIỆM'

      };

      return mapVi[code] || code;

    }



    function formatMessageTypeLabel(msgType) {

      const code = String(msgType || 'AGENT_GENERATED').toUpperCase();

      if (CURRENT_LANG === 'en') {

        const mapEn = {

          AGENT_GENERATED: 'AGENT GENERATED',

          ORCHESTRATOR_HANDOFF: 'ORCHESTRATOR HANDOFF',

          SYSTEM_STATUS: 'SYSTEM STATUS',

          DEMO_PREVIEW: 'DEMO PREVIEW'

        };

        return mapEn[code] || code;

      }

      const mapVi = {

        AGENT_GENERATED: 'AI BÁO CÁO KẾT QUẢ',

        ORCHESTRATOR_HANDOFF: 'BÀN GIAO NHIỆM VỤ',

        SYSTEM_STATUS: 'TRẠNG THÁI HỆ THỐNG',

        DEMO_PREVIEW: 'BẢN THỬ MINH HỌA'

      };

      return mapVi[code] || code;

    }



    // Translates dynamic backend Vietnamese strings to fluent English when CURRENT_LANG === 'en',

    // and translates English backend strings to Vietnamese when CURRENT_LANG === 'vi'

    function trContent(rawText) {

      if (!rawText) return '';

      let s = String(rawText);

      if (CURRENT_LANG === 'vi') {

        const enToViPairs = [

          ['Website Technical Audit & SEO Fix + Full Python Toolkit Deliverable', 'Kiểm Toán Kỹ Thuật Website & Tối Ưu SEO + Bàn Giao Trọn Bộ Công Cụ Python'],

          ['Website Technical Audit & SEO Fix', 'Gói Kiểm Toán Kỹ Thuật Website & Tối Ưu SEO'],

          ['Automated Technical SEO & Conversion Micro-Audit Script (Python CLI)', 'Bộ Công Cụ Kiểm Toán Kỹ Thuật SEO & Tối Ưu Chuyển Đổi Tự Động (Python CLI)'],

          ['Single-Worker Lock: ACTIVE', 'Khóa Chống Chạy Trùng: BẬT'],

          ['MOCK MODE (Local Deterministic Engine — No Paid LLM Key Configured)', 'BẢN MÔ PHỎNG CỤC BỘ — chưa kết nối nhà cung cấp AI'],

          ['LLM PROVIDER STATUS', 'Trạng thái nhà cung cấp LLM'],

          ['GUARDED_AUTONOMY', 'TỰ HÀNH CÓ KIỂM SOÁT'],

          ['SIMULATION', 'MÔ PHỎNG AN TOÀN'],

          ['ASSISTED', 'HỖ TRỢ BÁN TỰ ĐỘNG'],

          ['ORCHESTRATOR_CORE', 'LÕI ĐIỀU PHỐI AI'],

          ['RESEARCH_AGENT', 'AI NGHIÊN CỨU'],

          ['PRODUCT_AGENT', 'AI SẢN PHẨM'],

          ['CODING_AGENT', 'AI LẬP TRÌNH'],

          ['MARKETING_AGENT', 'AI TIẾP THỊ'],

          ['SALES_AGENT', 'AI BÁN HÀNG'],

          ['CUSTOMER_SUPPORT_AGENT', 'AI HỖ TRỢ'],

          ['FINANCE_AGENT', 'AI TÀI CHÍNH'],

          ['OPTIMIZATION_AGENT', 'AI TỐI ƯU'],

          ['SECURITY_AGENT', 'AI BẢO MẬT'],

          ['Included', 'Đã đính kèm nhãn minh bạch']

        ];

        enToViPairs.forEach(([enStr, viStr]) => {

          if (s.includes(enStr)) s = s.split(enStr).join(viStr);

        });

        return s;

      }



      // When CURRENT_LANG === 'en': Translate Vietnamese backend sentences & phrases into English

      const viToEnPairs = [

        ['[CHẾ ĐỘ DEMO KIỂM THỬ GIAO DIỆN] Tôi đang kiểm tra hiệu ứng truyền tin Hologram 3D và bong bóng lời thoại Tiếng Việt. Tin nhắn này không tính vào lịch sử vận hành thật.', '[UI DEMO PREVIEW MODE] Testing 3D Hologram transmission beam and speech bubble rendering. This preview message is isolated from real operational logs.'],

        ['Tôi đã quét và lọc được', 'I have scanned and filtered'],

        ['cơ hội thị trường hợp lệ', 'valid market opportunities'],

        ['Cơ hội điểm cao nhất là', 'The highest-scoring opportunity is'],

        ['Đề xuất đóng gói dịch vụ', 'Recommending service package'],

        ['Hạn mức ngân sách và phân quyền RBAC hợp lệ (Single-Worker Lock: ACTIVE). Cho phép triển khai gói dịch vụ', 'Budget guardrails and RBAC permissions verified (Single-Worker Lock: ACTIVE). Authorizing service package deployment:'],

        ['với giá niêm yết', 'at listed price'],

        ['Gói sản phẩm', 'Product package'],

        ['đã sẵn sàng. Chuyển giao cho Coding Agent kiểm định tự động mã nguồn và công cụ kiểm toán.', 'is ready. Handing off to Coding Agent for automated code verification and audit engine self-tests.'],

        ['Bộ công cụ kiểm toán kỹ thuật HTML/SEO/Security đã vượt qua', 'The HTML/SEO/Security technical audit toolkit passed'],

        ['bài tự kiểm thử (Self-Tests PASSED). Sẵn sàng phục vụ kiểm toán website khách hàng.', 'automated self-tests (Self-Tests PASSED). Ready to audit live client websites.'],

        ['Đã cập nhật tài sản nội dung SEO chuẩn kỹ thuật cho dịch vụ', 'Updated compliant technical SEO content assets for'],

        ['Chuyển phễu thu hút khách hàng cho Sales Agent.', 'Handing over lead acquisition funnel to Sales Agent.'],

        ['Tôi đã kiểm toán trực tiếp các website khách hàng tiềm năng. Hiện có', 'I have audited prospective client websites directly. Currently'],

        ['đề xuất cá nhân hóa kèm bằng chứng lỗi HTML/SEO đang tự động phê duyệt & gửi báo giá 24/7 trước khi gửi.', 'custom proposals with verifiable HTML/SEO defect evidence are awaiting Owner approval before outreach.'],

        ['Hệ thống bàn giao báo cáo kỹ thuật đang trực sẵn sàng. Mọi đơn hàng chỉ mở khóa gói bàn giao sau khi xác minh thanh toán thành công.', 'Technical deliverable gateway is standing by. Orders unlock deliverables strictly after verified payment settlement.'],

        ['Đã đối soát sổ cái 9 khoản mục: Doanh thu thực nhận đã xác minh =', 'Reconciled 9-bucket financial ledger: Verified revenue ='],

        ['Khoản chờ xác minh =', 'Pending verification ='],

        ['Lợi nhuận ròng =', 'Net profit ='],

        ['Chi phí vận hành chu kỳ =', 'Cycle operating cost ='],

        ['Chưa có doanh thu xác minh. Đề xuất Chủ sở hữu duyệt gửi', 'No verified revenue is recorded. Recommend Owner review and approve'],

        ['báo cáo kiểm toán website miễn phí để tạo chuyển đổi đầu tiên.', 'free website audit reports to generate the first paid conversion.'],

        ['Đang giữ nguyên cấu hình giá và theo dõi tỷ lệ chuyển đổi từ các đề xuất đã duyệt.', 'Maintaining current pricing configuration and monitoring conversion rates from approved proposals.'],

        ['Quét tín hiệu thị trường và nhu cầu dịch vụ có nguồn xác thực', 'Scans verified market signals and service demand from public sources'],

        ['Định nghĩa gói dịch vụ Website Technical Audit & SEO Fix, phạm vi bàn giao và mức giá minh bạch.', 'Defines the Website Technical Audit & SEO Fix package, deliverable scope, and transparent pricing.'],

        ['Thực thi bộ kiểm toán kỹ thuật HTML/SEO/Security trực tiếp', 'Executes live HTML/SEO/Security technical audits and automated self-tests'],

        ['Tạo nội dung bài viết kỹ thuật & tài sản SEO hợp chuẩn, không spam, không tuyên bố sai sự thật.', 'Generates compliant technical articles & SEO assets with zero spam or false claims.'],

        ['Quét doanh nghiệp thật từ OpenStreetMap, kiểm toán lỗi website và soạn đề xuất cá nhân hóa chờ duyệt.', 'Discovers real businesses, audits website defects, and drafts custom proposals awaiting approval.'],

        ['Theo dõi trạng thái đơn hàng, hướng dẫn thanh toán và bàn giao gói báo cáo kỹ thuật sau khi thanh toán.', 'Monitors orders, provides payment guidance, and delivers technical packages post-settlement.'],

        ['Đối soát giao dịch USDT BEP20 on-chain / VietQR và hạch toán 9 nhóm tài chính trung thực.', 'Verifies on-chain USDT BEP20 / VietQR transactions and reconciles the 9-bucket ledger.'],

        ['Đánh giá tỷ lệ chuyển đổi, hiệu quả chi phí và đề xuất bước tiếp theo cho chủ sở hữu.', 'Evaluates conversion rates, cost efficiency, and recommends next steps to the Owner.'],

        ['Giám sát hạn mức ngân sách, khóa chống chạy trùng, RBAC, Emergency Stop và nhật ký bảo mật.', 'Monitors budget guardrails, single-worker lock, RBAC permissions, Emergency Stop, and audit logs.'],

        ['Đang chờ kích hoạt từ AI Core Orchestrator', 'Waiting for activation from AI Core Orchestrator'],

        ['Thực thi theo từng bước xác thực (Backend không phát tiến độ phần trăm giả lập)', 'Step-by-step verified execution (Backend never emits fake percentage bars)'],

        ['Sẵn sàng thực thi nhiệm vụ', 'Ready for task execution'],

        ['Kiểm tra kết nối API hoặc chạy lại chu kỳ 13 bước.', 'Check API connection or re-run the 13-step cycle.'],

        ['Hoàn tất', 'Completed'],

        ['Không giới hạn', 'No deadline'],

        ['Hôm nay', 'Today']

      ];

      viToEnPairs.forEach(([viStr, enStr]) => {

        if (s.includes(viStr)) s = s.split(viStr).join(enStr);

      });

      return s;

    }



    let UI_EVENT_LOGS = [

      {

        ts: new Date().toISOString(),

        type: 'UI_NOTICE',

        actor: 'COMMAND_CENTER_UI',

        msgVi: 'Đang chờ trạng thái thực tế từ máy chủ; chưa có hoạt động AI được xác minh.',

        msgEn: 'Waiting for backend status; no verified AI activity has been received.'

      }

    ];

    let STATE = {

      online: false,

      dashboard: null,

      finance: null,

      opportunities: [],

      leads: [],

      products: [],

      orders: [],

      paymentReports: [],

      tasks: [],

      transactions: [],

      marketing: [],

      budgets: null,

      auditLogs: [],

      wallet: null,

      agentMessages: []

    };



    const VIEW_TITLES_BILINGUAL = {

      overview: {

        vi: 'Tổng Quan — Căn Cứ 3D & Trung Tâm Điều Hành Nhân Sự AI Đang Hoạt Động',

        en: 'Overview — 3D Sci-Fi AI Base & Nine-Agent Command Center'

      },

      agents: {

        vi: 'Đội Ngũ Nhân Sự AI Đang Hoạt Động — Điều Phối Đa Tác Tử & Nhật Ký Nhiệm Vụ',

        en: 'AI Agents — Multi-Agent Orchestration & Task Telemetry'

      },

      opportunities: {

        vi: 'Cơ Hội Kinh Doanh — Quét Thị Trường & Dự Án Tự Do Kiểm Chứng Được',

        en: 'Opportunities — Verifiable Market & Freelance Discovery'

      },

      leads: {

        vi: 'Khách Hàng Tiềm Năng — Chẩn Đoán Kỹ Thuật Website & Đề Xuất Chờ Duyệt',

        en: 'Leads & Customers — Evidence-Based Website Diagnostics & Proposals'

      },

      products: {

        vi: 'Sản Phẩm & Dịch Vụ — Kiểm Toán Kỹ Thuật Website & Tối Ưu SEO',

        en: 'Products & Services — Website Technical Audit & SEO Fix'

      },

      orders: {

        vi: 'Đơn Hàng & Thanh Toán — Đối Soát On-Chain BSC & Sao Kê Ngân Hàng',

        en: 'Orders & Payments — On-Chain BSC & Bank Reconciliation'

      },

      marketing: {

        vi: 'Tiếp Thị & Nội Dung SEO — Tài Sản Nội Dung Hợp Pháp & Minh Bạch',

        en: 'Marketing & SEO — Compliant Content & Traffic Assets'

      },

      automation: {

        vi: 'Tự Động Hóa — Quy Trình 13 Bước & Kiến Trúc Hạ Tầng Thực Tế',

        en: 'Automation — 13-Step Pipeline & Infrastructure Architecture'

      },

      analytics: {

        vi: 'Báo Cáo Kế Toán — Sổ Cái Tài Chính Trung Thực 9 Khoản Mục',

        en: 'Analytics — 9-Bucket Honest Financial Accounting'

      },

      security: {

        vi: 'Bảo Mật & Cài Đặt — Phân Quyền Quản Trị, Hạn Mức Ngân Sách & Nhật Ký',

        en: 'Security & Settings — RBAC, Guardrails & Audit Logs'

      }

    };



    function applyStaticDomLanguage() {

      document.documentElement.lang = CURRENT_LANG === 'en' ? 'en' : 'vi';

      document.title = CURRENT_LANG === 'en'

        ? 'AUTOProfit AI — 3D Operations Center'

        : 'AUTOProfit AI — Trung Tâm Vận Hành 3D';



      const btnVi = document.getElementById('btnLangVi');

      const btnEn = document.getElementById('btnLangEn');

      if (btnVi) btnVi.classList.toggle('active', CURRENT_LANG === 'vi');

      if (btnEn) btnEn.classList.toggle('active', CURRENT_LANG === 'en');



      // Update all elements with data-vi / data-en

      document.querySelectorAll('[data-vi][data-en]').forEach(el => {

        const val = CURRENT_LANG === 'en' ? el.getAttribute('data-en') : el.getAttribute('data-vi');

        if (val !== null) {

          el.innerHTML = val;

        }

      });



      // Update all inputs/textareas with data-vi-placeholder / data-en-placeholder

      document.querySelectorAll('[data-vi-placeholder][data-en-placeholder]').forEach(el => {

        const ph = CURRENT_LANG === 'en' ? el.getAttribute('data-en-placeholder') : el.getAttribute('data-vi-placeholder');

        if (ph !== null) {

          el.placeholder = ph;

        }

      });



      // Update current view heading

      const vt = VIEW_TITLES_BILINGUAL[CURRENT_VIEW_ID] || VIEW_TITLES_BILINGUAL.overview;

      const titleEl = document.getElementById('currentViewTitle');

      if (titleEl) titleEl.textContent = CURRENT_LANG === 'en' ? vt.en : vt.vi;



      // Update interactive toggle buttons

      const motionBtn = document.getElementById('btnReducedMotion');

      if (motionBtn) {

        motionBtn.textContent = REDUCED_MOTION

          ? t('✦ Chuyển động: GIẢM', '✦ Motion: REDUCED')

          : t('✦ Chuyển động: BẬT', '✦ Motion: ON');

      }



      const pollBtn = document.getElementById('btnPollingToggle');

      if (pollBtn) {

        pollBtn.textContent = POLLING_ACTIVE

          ? t('⏱ Tự động cập nhật (15s): BẬT', '⏱ Auto-Poll (15s): ON')

          : t('⏸ Tự động cập nhật: TẠM DỪNG', '⏸ Auto-Poll: PAUSED');

      }



      const voiceBtn = document.getElementById('btnVoiceToggle');

      if (voiceBtn) {

        voiceBtn.textContent = VOICE_AI_ENABLED

          ? t('🔊 Giọng Nói AI: BẬT', '🔊 AI Voice: ON')

          : t('🔊 Giọng Nói AI: TẮT', '🔊 AI Voice: OFF');

      }



      const perfBtn = document.getElementById('btnPerfModeToggle');

      if (perfBtn) {

        perfBtn.textContent = LOW_PERF_MODE

          ? t('⚡ Đồ họa: TỐI ƯU', '⚡ Graphics: LOW')

          : t('⚡ Đồ họa: CAO', '⚡ Graphics: HIGH');

      }



      const followBtn = document.getElementById('btnFollowCamToggle');

      if (followBtn) {

        followBtn.textContent = FOLLOW_SELECTED_AGENT

          ? t('🎯 Theo Dõi AI: BẬT', '🎯 Follow Agent: ON')

          : t('🎯 Theo Dõi AI: TẮT', '🎯 Follow Agent: OFF');

      }



      const commDrawer = document.getElementById('aiCommHubDrawer');

      const commBtn = document.getElementById('btnToggleCommHub');

      if (commBtn && commDrawer) {

        const isCollapsed = commDrawer.classList.contains('collapsed');

        commBtn.textContent = isCollapsed ? t('💬 Mở Hội Thoại', '💬 Open Hub') : t('⇔ Thu gọn', '⇔ Collapse');

      }



      // Update 3D Zone Signs & Quick Agent Selector Pills

      Object.keys(AGENT_META_BILINGUAL).forEach(role => {

        const signEl = WORLD_3D?.overlaySignEls?.[role];

        if (signEl) {

          signEl.innerHTML = `<strong>${escapeHtml(formatZoneName(role))}</strong>`;

        }

        const pillEl = document.getElementById(`quickAgentPill_${role}`);

        if (pillEl) {

          const dotEl = document.getElementById(`quickDot_${role}`);

          const dotColor = dotEl ? dotEl.style.background : '#10b981';

          pillEl.innerHTML = `<span class="char-state-dot" id="quickDot_${role}" style="background:${dotColor};"></span><span>${escapeHtml(formatAgentShort(role))}</span>`;

        }

      });

    }



    function setAppLanguage(lang) {

      CURRENT_LANG = lang === 'en' ? 'en' : 'vi';

      localStorage.setItem('autoprofit_lang', CURRENT_LANG);

      applyStaticDomLanguage();

      if (typeof window.renderYoutubeActiveCampaignsList === 'function') window.renderYoutubeActiveCampaignsList();

      if (typeof window.analyzeYoutubeSeoAndThumbnails === 'function') window.analyzeYoutubeSeoAndThumbnails();

      if (typeof window.ensureDefaultYoutubeAutoPlayOnVisitorEntry === 'function') window.ensureDefaultYoutubeAutoPlayOnVisitorEntry();

      if (typeof window.renderAdLinkEvenDistributionStats === 'function') window.renderAdLinkEvenDistributionStats();

      if (typeof window.syncAllDynamicBilingualElementsNow === 'function') window.syncAllDynamicBilingualElementsNow();

      if (typeof renderGithubWebFactorySection === 'function' && window.GITHUB_WEB_FACTORY_CACHE) renderGithubWebFactorySection(window.GITHUB_WEB_FACTORY_CACHE);

      // Auto-switch to Full English & YouTube Booster tab when global visitors arrive via ?lang=en or ?tab=youtube

      try {

        const params = new URLSearchParams(window.location.search);

        if (params.get('lang') === 'en' && typeof setAppLanguage === 'function') {

          setAppLanguage('en');

        }

        if ((params.get('tab') === 'youtube' || window.location.hash === '#youtube') && typeof switchOverviewWorkspaceTab === 'function') {

          switchOverviewWorkspaceTab('TAB_YOUTUBE_BOOSTER');

        }

      } catch (_) {}



      if (STATE.online && STATE.dashboard) {

        renderAllViews();

      } else {

        renderOfflineState(t('Đang kiểm tra hoặc mất kết nối', 'Checking or disconnected'));

      }

      if (SELECTED_AGENT_ID && WORLD_3D.initialized) {

        selectCharacterIn3DWorld(SELECTED_AGENT_ID, false);

      }

      if (CURRENT_ACTIVE_SPEECH && CURRENT_ACTIVE_SPEECH.msg) {

        activateSpeechBubbleIn3D(CURRENT_ACTIVE_SPEECH.msg);

      }

      showToast(t('Đã chuyển toàn bộ giao diện sang Tiếng Việt (100%).', 'Switched entire interface to Full English (100%).'));

    }



    function showToast(msg, isError = false) {

      const el = document.getElementById('toastBox');

      el.style.display = 'block';

      el.style.borderColor = isError ? 'rgba(239,68,68,0.65)' : 'rgba(6,182,212,0.65)';

      el.textContent = msg;

      clearTimeout(window._toastTimer);

      window._toastTimer = setTimeout(() => { el.style.display = 'none'; }, 4500);

    }


    async function copyTextToClipboard(text) {
      try {
        if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
          await navigator.clipboard.writeText(String(text ?? ''));
          return true;
        }
      } catch (_) {}
      const field = document.createElement('textarea');
      field.value = String(text ?? '');
      field.setAttribute('readonly', '');
      field.style.position = 'fixed';
      field.style.opacity = '0';
      document.body.appendChild(field);
      field.select();
      let copied = false;
      try { copied = document.execCommand('copy'); } catch (_) {}
      field.remove();
      return copied;
    }
    window.copyTextToClipboard = copyTextToClipboard;

    function showIntegrationHelp(title, message, links = []) {
      let dialog = document.getElementById('apIntegrationHelp');
      if (!dialog) {
        dialog = document.createElement('dialog');
        dialog.id = 'apIntegrationHelp';
        dialog.style.cssText = 'max-width:min(520px,calc(100vw - 28px)); width:100%; padding:0; border:1px solid #28638a; border-radius:14px; background:#0a1425; color:#eef5ff; box-shadow:0 24px 80px #000a;';
        dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
        document.body.appendChild(dialog);
      }
      const card = document.createElement('section');
      card.style.cssText = 'padding:20px; font:14px/1.55 system-ui,sans-serif;';
      const heading = document.createElement('h2');
      heading.textContent = title;
      heading.style.cssText = 'margin:0 36px 10px 0; font-size:18px;';
      const body = document.createElement('p');
      body.textContent = message;
      body.style.cssText = 'color:#b7c7dd; margin:0 0 14px;';
      const linkRow = document.createElement('div');
      linkRow.style.cssText = 'display:flex; flex-wrap:wrap; gap:8px; margin-bottom:14px;';
      links.forEach(item => {
        const link = document.createElement('a');
        link.href = item.href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = item.label;
        link.style.cssText = 'color:#7dd3fc; padding:7px 10px; border:1px solid #28638a; border-radius:7px; text-decoration:none;';
        linkRow.appendChild(link);
      });
      const close = document.createElement('button');
      close.type = 'button';
      close.textContent = 'Đóng';
      close.style.cssText = 'padding:8px 14px; border:1px solid #475569; border-radius:8px; background:#152238; color:#fff; cursor:pointer;';
      close.addEventListener('click', () => dialog.close());
      card.append(heading, body, linkRow, close);
      dialog.replaceChildren(card);
      if (!dialog.open) dialog.showModal();
    }
    window.showIntegrationHelp = showIntegrationHelp;
    window.openSelfSustaining4DirectionsModal = function() {
      showIntegrationHelp('Tích hợp doanh thu chưa kết nối', 'Auto-Surf trong repo chỉ là trình xem thử thủ công. Chưa có xác minh mạng quảng cáo, traffic exchange hoặc doanh thu nên không thể bật lượt xem hay cam kết CPM.');
    };
    window.copyAutoSurfLinkAndOpenExchange = async function() {
      const url = `${window.location.origin}/autosurf.html`;
      const copied = await copyTextToClipboard(url);
      showToast(copied ? 'Đã sao chép link trình xem thử thủ công.' : 'Không thể sao chép link tự động.', !copied);
      return copied;
    };
    window.openDePinPassiveNodesQuick = function() {
      showIntegrationHelp('Dịch vụ DePIN bên ngoài', 'Các dịch vụ này cần tài khoản và ứng dụng riêng; trang hiện không tự bật node, không cài phần mềm và không đo thu nhập.', [
        { label: 'Honeygain', href: 'https://www.honeygain.com/' },
        { label: 'Pawns.app', href: 'https://pawns.app/' }
      ]);
    };

    async function copyOutputContent() {
      const content = document.getElementById('outBox')?.value || '';
      const copied = await copyTextToClipboard(content);
      showToast(copied ? t('Đã sao chép kết quả.', 'Output copied.') : t('Không thể sao chép tự động. Hãy chọn kết quả và sao chép thủ công.', 'Clipboard unavailable. Select and copy the output manually.'), !copied);
    }



    function escapeHtml(val) {

      if (val === null || val === undefined) return '';

      return String(val)

        .replace(/&/g, '&amp;')

        .replace(/</g, '&lt;')

        .replace(/>/g, '&gt;')

        .replace(/"/g, '&quot;')

        .replace(/'/g, '&#39;');

    }



    function isSecureAdminOrigin(targetBase = API_BASE) {

      if (window.location.protocol !== 'https:') return false;

      try {

        const target = new URL(targetBase || window.location.origin, window.location.href);

        return target.protocol === 'https:' && target.origin === window.location.origin;

      } catch (_) {

        return false;

      }

    }



    function getAdminHeaders(hasBody = false, extra = {}, targetBase = API_BASE) {

      const headers = { ...extra };

      if (hasBody) headers['Content-Type'] = 'application/json';

      if (!isSecureAdminOrigin(targetBase)) return headers;

      const key = sessionStorage.getItem('autoprofit_owner_admin_key');

      if (key) headers['X-Admin-Key'] = key;

      return headers;

    }



    function promptOrGetAdminKey() {

      if (!isSecureAdminOrigin()) {

        showToast(t('Quản trị yêu cầu HTTPS; không nhập khóa trên kết nối HTTP.', 'Admin access requires HTTPS; do not enter the key over HTTP.'), true);

        return null;

      }

      let key = sessionStorage.getItem('autoprofit_owner_admin_key');

      if (!key) {

        key = window.prompt(t(

          'Nhập Khóa Quản Trị Viên (X-Admin-Key) để thực hiện thao tác quản trị nhạy cảm:',

          'Enter Owner Admin API Key (X-Admin-Key) to authorize this privileged action:'

        ));

        if (key && key.trim()) {

          sessionStorage.setItem('autoprofit_owner_admin_key', key.trim());

          const inp = document.getElementById('adminKeyInput');

          if (inp) inp.value = key.trim();

        }

      }

      return key ? key.trim() : null;

    }





    // =========================================================================

    // Offline mode is read-only. Mutations must reach a real backend; no synthetic success responses.
    async function handleServerlessEdgeApiRequest(path, options = {}) {
      const method = String(options.method || "GET").toUpperCase();
      const cleanPath = String(path || "").split("?")[0];
      if (method !== "GET" && method !== "HEAD") {
        throw new Error("Backend chưa kết nối; thao tác chưa được gửi và chưa được lưu.");
      }
      if (cleanPath === "/api/health") {
        throw new Error("Không kết nối được backend.");
      }
      if (cleanPath === "/api/dashboard") {
        return {
          system: { backend_health: "OFFLINE", system_status: "UNKNOWN", ai_provider_mode: "NOT_CONNECTED" },
          kpis_real_verified: {
            verified_revenue_usd: null, active_agents_count: null,
            api_cost_usd: null, completed_orders_count: null
          },
          dashboard_data: { status: "not_connected" }
        };
      }
      if (cleanPath === "/api/dashboard/summary") {
        return {
          status: "not_connected",
          source: "backend_unavailable",
          metrics: {
            revenue_usd: { status: "not_connected", value_usd: null },
            active_agents: { status: "not_connected", value: null },
            pageviews_today: { status: "not_connected", value: null },
            sessions_today: { status: "not_connected", value: null }
          }
        };
      }
      const listPaths = new Set([
        "/api/opportunities", "/api/leads", "/api/products", "/api/orders",
        "/api/tasks", "/api/transactions", "/api/marketing", "/api/employees",
        "/api/pricing/catalog", "/api/pricing/recommendations", "/api/pricing/history",
        "/api/audit-logs", "/api/public/advertising-inquiries", "/api/public/donations",
        "/api/dashboard/activity"
      ]);
      if (listPaths.has(cleanPath)) {
        return { status: "not_connected", source: "backend_unavailable", items: [], total: null };
      }
      if (cleanPath === "/api/wallet/binance-usdt") {
        return { status: "not_connected", wallet_address: null, network: null };
      }
      if (cleanPath === "/api/settings/budgets" || cleanPath === "/api/payout-policies") {
        return { status: "not_connected", source: "backend_unavailable", settings: null };
      }
      if (cleanPath === "/api/github-web-factory/apps") {
        return { status: "not_connected", source: "backend_unavailable", items: [], total: 0 };
      }
      return { status: "not_connected", source: "backend_unavailable", items: [], total: null };
    }

    async function apiFetch(path, options = {}, timeoutMs = 4500, baseOverride = null) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), Math.min(timeoutMs, 4500));
      const targetBase = baseOverride || API_BASE;
      const method = String(options.method || "GET").toUpperCase();
      const canUseReadOnlyFallback = method === "GET" || method === "HEAD";
      let res;
      try {
        res = await fetch(String(targetBase) + String(path), {
          ...options,
          headers: getAdminHeaders(Boolean(options.body), options.headers || {}, targetBase),
          signal: controller.signal
        });
      } catch (error) {
        clearTimeout(timer);
        if (canUseReadOnlyFallback) return await handleServerlessEdgeApiRequest(path, options);
        throw new Error(controller.signal.aborted
          ? "Backend không phản hồi kịp; thao tác chưa được gửi."
          : "Không kết nối được backend; thao tác chưa được gửi và chưa được lưu.");
      } finally {
        clearTimeout(timer);
      }

      if (res.status === 204) {
        if (canUseReadOnlyFallback) return await handleServerlessEdgeApiRequest(path, options);
        throw new Error("Backend không xác nhận yêu cầu; thao tác chưa được gửi.");
      }

      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; }
      catch (_) { data = { raw: text }; }

      if (!res.ok || (!text && res.status !== 200)) {
        const detail = typeof data.detail === "string" ? data.detail : "";
        throw new Error(detail || ("Backend trả về HTTP " + res.status + "."));
      }
      return data;
    }

    window.apiFetch = apiFetch;

    // NAVIGATION & RESPONSIVE SIDEBAR

    // =========================================================================

    function switchView(viewId) {

      if (window.__AUTOPROFIT_INITIAL_PAGEVIEW_SENT && viewId && viewId !== CURRENT_VIEW_ID && typeof sendVisitorTrafficHeartbeat === 'function') {

        sendVisitorTrafficHeartbeat(true);

      }

      CURRENT_VIEW_ID = viewId;

      document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));

      const target = document.getElementById(`view-${viewId}`);

      if (target) target.classList.add('active');



      document.querySelectorAll('.nav-item').forEach(item => {

        item.classList.toggle('active', item.getAttribute('data-view') === viewId);

      });



      const vt = VIEW_TITLES_BILINGUAL[viewId] || VIEW_TITLES_BILINGUAL.overview;

      document.getElementById('currentViewTitle').textContent = CURRENT_LANG === 'en' ? vt.en : vt.vi;

      document.getElementById('sidebar').classList.remove('open');

    }



    function toggleMobileSidebar() {

      document.getElementById('sidebar').classList.toggle('open');

    }



    // =========================================================================

    // MASTER DATA SYNCHRONIZATION & OFFLINE FALLBACK

    // =========================================================================

    async function refreshAllData(manual = false) {

      document.getElementById('sidebarEndpointText').textContent = `${t('Máy chủ', 'API')}: ${API_BASE}`;

      const customInp = document.getElementById('customApiUrlInput');

      if (customInp && !customInp.value) customInp.value = API_BASE;



      try {

        const candidates = Array.from(new Set([API_BASE, DEFAULT_TUNNEL_URL, window.location.origin, window.__IS_LOCAL_OWNER_ENV__ ? LOCAL_BACKEND_URL : null].filter(Boolean)));

        let connectedBase = null;

        let lastErr = null;

        for (const cand of candidates) {

          try {

            await apiFetch('/api/health', {}, 2200, cand);

            connectedBase = cand;

            break;

          } catch (e) {

            lastErr = e;

          }

        }

        if (!connectedBase) {

          throw lastErr || new Error('Failed to fetch');

        }

        API_BASE = connectedBase;

        if (customInp) customInp.value = API_BASE;



        STATE.online = true;

        document.getElementById('offlineBanner').style.display = 'none';

        document.getElementById('sidebarDot').className = 'dot online';

        document.getElementById('sidebarConnText').textContent = t('Máy Chủ Trực Tuyến (Đã Xác Thực)', 'Backend Online (Verified)');

        document.getElementById('sidebarEndpointText').textContent = `${t('Máy chủ', 'API')}: ${API_BASE}`;



        // Stage 1: Fetch unified /api/dashboard first for instant <0.5s rendering over Cloudflare Tunnel

        const dashboard = await apiFetch('/api/dashboard', {}, 15000);

        STATE.dashboard = dashboard;

        STATE.finance = dashboard.finance_summary || {};

        STATE.opportunities = dashboard.opportunities_preview || STATE.opportunities || [];

        STATE.tasks = dashboard.recent_tasks || STATE.tasks || [];

        STATE.orders = dashboard.recent_orders || STATE.orders || [];

        STATE.transactions = dashboard.recent_transactions || STATE.transactions || [];

        STATE.agentMessages = dashboard.recent_agent_messages || STATE.agentMessages || [];

        STATE.employees = dashboard.employees_registry || STATE.employees || [];

        STATE.employeesMeta = dashboard.workforce_summary || STATE.employeesMeta || {};

        renderAllViews();



        // Stage 2: Fetch full secondary tables in 2 gentle batches (never failing the online state)

        const [opps, leads, products, orders, tasks, txs, marketing] = await Promise.all([

          apiFetch('/api/opportunities', {}, 15000).catch(() => null),

          apiFetch('/api/leads', {}, 15000).catch(() => null),

          apiFetch('/api/products', {}, 15000).catch(() => null),

          apiFetch('/api/orders', {}, 15000).catch(() => null),

          apiFetch('/api/tasks', {}, 15000).catch(() => null),

          apiFetch('/api/transactions', {}, 15000).catch(() => null),

          apiFetch('/api/marketing', {}, 15000).catch(() => null)

        ]);

        const [budgets, auditLogs, employeesResp, adInquiriesResp, donationsResp, payoutPolicyResp, wallet, pricingCatalogResp, pricingRecsResp, pricingHistResp, paymentReportsResp] = await Promise.all([

          apiFetch('/api/settings/budgets', {}, 15000).catch(() => null),

          apiFetch('/api/audit-logs', {}, 15000).catch(() => null),

          apiFetch('/api/employees', {}, 15000).catch(() => null),

          apiFetch('/api/public/advertising-inquiries', {}, 15000).catch(() => null),

          apiFetch('/api/public/donations', {}, 15000).catch(() => null),

          apiFetch('/api/payout-policies', {}, 15000).catch(() => null),

          apiFetch('/api/wallet/binance-usdt', {}, 15000).catch(() => null),

          apiFetch('/api/pricing/catalog', {}, 15000).catch(() => null),

          apiFetch('/api/pricing/recommendations', {}, 15000).catch(() => null),

          apiFetch('/api/pricing/history', {}, 15000).catch(() => null),

          apiFetch('/api/admin/payment-reports', {}, 15000).catch(() => null)

        ]);



        if (opps && opps.items) STATE.opportunities = opps.items;

        if (leads && leads.items) STATE.leads = leads.items;

        if (products && products.items) STATE.products = products.items;

        if (orders && orders.items) STATE.orders = orders.items;

        if (tasks && tasks.items) STATE.tasks = tasks.items;

        if (txs && txs.items) STATE.transactions = txs.items;

        if (marketing && marketing.items) STATE.marketing = marketing.items;

        if (budgets) STATE.budgets = budgets;

        if (auditLogs && auditLogs.items) STATE.auditLogs = auditLogs.items;

        if (wallet) STATE.wallet = wallet;

        if (employeesResp && employeesResp.items) {

          STATE.employees = employeesResp.items;

          STATE.employeesMeta = employeesResp;

        }

        if (adInquiriesResp) STATE.adInquiries = adInquiriesResp;

        if (donationsResp) STATE.donations = donationsResp;

        if (payoutPolicyResp && payoutPolicyResp.policy) STATE.payoutPolicy = payoutPolicyResp.policy;

        if (pricingCatalogResp && pricingCatalogResp.items) STATE.pricingCatalog = pricingCatalogResp.items;

        if (pricingRecsResp && pricingRecsResp.items) STATE.pricingRecommendations = pricingRecsResp.items;

        if (pricingHistResp && pricingHistResp.items) STATE.priceChangeHistory = pricingHistResp.items;

        if (paymentReportsResp && Array.isArray(paymentReportsResp.items)) STATE.paymentReports = paymentReportsResp.items;



        renderAllViews();

        const localeCode = CURRENT_LANG === 'en' ? 'en-US' : 'vi-VN';

        document.getElementById('lastSyncTime').textContent = t(

          `Đồng bộ trực tiếp từ Máy chủ lúc ${new Date().toLocaleTimeString(localeCode)}`,

          `Live synced from Backend at ${new Date().toLocaleTimeString(localeCode)}`

        );

        if (manual) showToast(t('Đã đồng bộ dữ liệu thực tế từ Máy chủ thành công.', 'Successfully synchronized live data from Backend.'));

      } catch (err) {

        STATE.online = false;

        renderOfflineState(err.message);

        if (manual) showToast(`${t('Máy chủ Ngoại tuyến', 'Backend Offline')}: ${err.message}`, true);

      }

    }

    const CLOUD_STANDALONE_SNAPSHOT = {};

                  function renderOfflineState(reason) {
      STATE.online = false;
      STATE.dashboard = {};
      STATE.finance = {};
      STATE.opportunities = [];
      STATE.leads = [];
      STATE.products = [];
      STATE.orders = [];
      STATE.paymentReports = [];
      STATE.tasks = [];
      STATE.transactions = [];
      STATE.marketing = [];
      STATE.employees = [];
      STATE.employeesMeta = {};
      STATE.agentMessages = [];
      window.LAST_TRAFFIC_DATA_CACHE = null;

      const banner = document.getElementById('offlineBanner');
      const sidebarDot = document.getElementById('sidebarDot');
      const sidebarText = document.getElementById('sidebarConnText');
      const endpointText = document.getElementById('sidebarEndpointText');
      const syncText = document.getElementById('lastSyncTime');
      if (banner) {
        banner.style.display = 'block';
        banner.textContent = t('Máy chủ ngoại tuyến. Dữ liệu nghiệp vụ đang ẩn cho tới khi kết nối lại.', 'Backend offline. Business data is hidden until the connection returns.') + (reason ? ' ' + String(reason) : '');
      }
      if (sidebarDot) sidebarDot.className = 'dot offline';
      if (sidebarText) sidebarText.textContent = t('Máy chủ ngoại tuyến', 'Backend offline');
      if (endpointText) endpointText.textContent = 'API: ' + API_BASE;
      if (syncText) syncText.textContent = t('Chưa đồng bộ được dữ liệu backend.', 'Backend data is not synchronized.');
      renderAllViews();
      if (typeof renderLiveActivityLog === 'function') renderLiveActivityLog(true, reason || '');
    }
const financeValueOrNull = value => {
  if (value === null || value === undefined || value === '') return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

const formatFinanceValue = (value, decimals = 2, unit = 'USD') => {
  const numeric = financeValueOrNull(value);
  if (numeric === null) return t('— / Chưa có dữ liệu đã xác minh', '— / No verified data');
  const amount = unit === 'USD' ? `$${numeric.toFixed(decimals)}` : numeric.toFixed(decimals);
  return `${amount} ${unit}`;
};

function renderAllViews() {

      const sys = STATE.dashboard?.system || {};

      const kpis = STATE.dashboard?.kpis_real_verified || {};

      const nine = STATE.finance?.nine_bucket_accounting || STATE.dashboard?.nine_bucket_accounting || {};

      const localeCode = CURRENT_LANG === 'en' ? 'en-US' : 'vi-VN';



      // Render Futuristic Nine-Agent Command Center & Live Activity Log

      renderNineAgentCommandCenter(false);

      renderLiveActivityLog(false);



      // Topbar Badges

      const rawAiMode = sys.ai_provider_mode || sys.ai_provider || 'NOT_CONNECTED';

      const aiBadge = document.getElementById('aiProviderBadge');

      aiBadge.textContent = CURRENT_LANG === 'en'

        ? `AI_PROVIDER: ${rawAiMode}`

        : `AI: ${rawAiMode.includes('MOCK') ? 'Demo · mẫu cục bộ' : rawAiMode}`;

      aiBadge.className = sys.ai_provider_verified === true ? 'chip success' : 'chip warn';



      const rawOpMode = sys.operating_mode || 'GUARDED_AUTONOMY';

      document.getElementById('operatingModeBadge').textContent = CURRENT_LANG === 'en'

        ? `MODE: ${rawOpMode}`

        : `CHẾ ĐỘ: ${trContent(rawOpMode)}`;



      const rawSysStatus = sys.system_status || 'UNKNOWN';

      const stBadge = document.getElementById('systemStatusBadge');

      stBadge.textContent = CURRENT_LANG === 'en'

        ? `STATUS: ${rawSysStatus}`

        : `TRẠNG THÁI: ${formatStatusLabel(rawSysStatus)}`;

      stBadge.className = rawSysStatus === 'RUNNING' ? 'chip success' : 'chip danger';



      // Sidebar counters

      document.getElementById('badge-opportunities').textContent = STATE.opportunities.length;

      if (Array.isArray(STATE.leads)) {

        STATE.leads = STATE.leads.filter(l => {

          const em = String((l && (l.email || l.contact_email)) || '');

          const nm = String((l && l.name) || '');

          return !em.includes('mmo_buyer_') && !em.includes('buyer@autoprofit.vn') && !nm.includes('Khach Hang Kiem Thu') && !nm.includes('Khách Hàng Web MMO');

        });

      }

      document.getElementById('badge-leads').textContent = STATE.leads.length;

      document.getElementById('badge-products').textContent = STATE.products.length;

      document.getElementById('badge-orders').textContent = STATE.orders.length;

      document.getElementById('badge-marketing').textContent = STATE.marketing.length;

      const ovLeadsEl = document.getElementById('overviewLeadsCount');

      if (ovLeadsEl) ovLeadsEl.textContent = STATE.leads.length;



      // 1. OVERVIEW KPI CARDS

      const verifiedRev = kpis.verified_revenue_usd;
      const netProfit = kpis.net_profit_usd;
      const paidOrders = kpis.completed_orders_count;
      const qualOpps = kpis.qualified_opportunities_count;
      const convRate = kpis.conversion_rate_pct;
      const opCosts = kpis.actual_expenses_usd;



      const setTxtOn = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };

      setTxtOn('kpi-verified-revenue', verifiedRev == null ? '—' : `$${Number(verifiedRev).toFixed(2)}`);
      setTxtOn('kpi-verified-revenue-sub', verifiedRev == null
        ? t('Chưa có doanh thu đã xác minh.', 'No verified revenue data.')
        : t('Nguồn: giao dịch đã xác minh.', 'Source: verified transactions.'));
      setTxtOn('kpi-net-profit', netProfit == null ? '—' : `$${Number(netProfit).toFixed(2)}`);
      setTxtOn('kpi-net-profit-sub', netProfit == null
        ? t('Chưa có dữ liệu chi phí để tính lợi nhuận.', 'Verified cost data is required to calculate net profit.')
        : t('Nguồn: sổ cái đã xác minh.', 'Source: verified ledger.'));

      if (typeof window.recalculateAndSyncTotalVerifiedRevenueUI === 'function') window.recalculateAndSyncTotalVerifiedRevenueUI();

      if (typeof window.syncAllLiveBranchCountersUI === 'function') window.syncAllLiveBranchCountersUI();

      setTxtOn('kpi-paid-orders', paidOrders == null ? '—' : String(paidOrders));

      setTxtOn('kpi-paid-orders-sub', t('Xem chi tiết nguồn tiền tại Báo Cáo Kế Toán', 'See revenue breakdown in Financial Analytics'));

      setTxtOn('kpi-qualified-opps', qualOpps == null ? '—' : String(qualOpps));

      setTxtOn('kpi-conversion-rate', convRate == null ? '—' : `${Number(convRate).toFixed(2)}%`);

      setTxtOn('kpi-operating-costs', opCosts == null ? '—' : `$${Number(opCosts).toFixed(4)}`);

      setTxtOn('kpi-active-agents', 'Runtime not connected');

      const bhEl = document.getElementById('kpi-backend-health');

      if (bhEl) {

        const backendOnline = STATE.online === true && sys.backend_health === 'ONLINE';
        bhEl.textContent = backendOnline ? t('TRỰC TUYẾN', 'ONLINE') : t('CHƯA KẾT NỐI', 'NOT CONNECTED');

        bhEl.style.color = backendOnline ? 'var(--status-online)' : 'var(--status-offline)';

      }

      setTxtOn('kpi-backend-health-sub', CURRENT_LANG === 'en'

        ? `FastAPI + SQLite (${STATE.leads.length} Leads, ${STATE.orders.length} Orders)`

        : `FastAPI + SQLite (${STATE.leads.length} Khách tiềm năng, ${STATE.orders.length} Đơn hàng)`);



      if (STATE.products.length > 0) {

        setTxtOn('overviewPrimaryPriceChip', CURRENT_LANG === 'en'

          ? `$${Number(STATE.products[0].price_usd).toFixed(2)} USD (Editable)`

          : `$${Number(STATE.products[0].price_usd).toFixed(2)} USD (Có thể chỉnh sửa)`);

      }



      if (STATE.wallet && STATE.wallet.latest_bsc_block) {

        setTxtOn('bscBlockChip', CURRENT_LANG === 'en'

          ? `BSC Block #${STATE.wallet.latest_bsc_block} | Wallet: ${STATE.wallet.onchain_usdt_balance ?? 0} USDT`

          : `Khối BSC #${STATE.wallet.latest_bsc_block} | Ví: ${STATE.wallet.onchain_usdt_balance ?? 0} USDT`);

      } else {

        setTxtOn('bscBlockChip', t('Mạng BSC Mainnet: Sẵn Sàng', 'BSC Mainnet RPC Ready'));

      }



      // Overview Accounting Bars

      const overviewValues = [
        nine['1_verified_revenue_usd'], nine['2_pending_payments_usd'],
        nine['3_estimated_revenue_usd'], nine['5_ai_costs_usd'], nine['6_hosting_costs_usd']
      ].map(financeValueOrNull).filter(value => value !== null);
      const maxBarVal = Math.max(1, ...overviewValues);

      const overviewBars = [

        { label: t('1. Doanh thu xác minh (Thực nhận)', '1. Verified Revenue (Settled)'), val: financeValueOrNull(nine['1_verified_revenue_usd']) },

        { label: t('2. Khoản chờ đối soát (Chưa cộng)', '2. Pending Verification (Unsettled)'), val: financeValueOrNull(nine['2_pending_payments_usd']) },

        { label: t('3. Doanh thu dự kiến (Đơn chưa TT)', '3. Estimated Revenue (Unpaid Orders)'), val: financeValueOrNull(nine['3_estimated_revenue_usd']) },

        { label: t('5. Chi phí AI & Vận hành thực tế', '5. Actual AI & Operating Costs'), val: [nine['5_ai_costs_usd'], nine['6_hosting_costs_usd']].every(value => financeValueOrNull(value) !== null) ? Number(nine['5_ai_costs_usd']) + Number(nine['6_hosting_costs_usd']) : null }

      ];

      if (document.getElementById('overviewAccountingBars')) document.getElementById('overviewAccountingBars').innerHTML = overviewBars.map(b => {

        const pct = b.val === null ? 0 : Math.min(100, Math.round((b.val / maxBarVal) * 100));

        return `

          <div class="bar-row">

            <div class="bar-label">${escapeHtml(b.label)}</div>

            <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>

            <div class="bar-val">${escapeHtml(formatFinanceValue(b.val, 2))}</div>

          </div>

        `;

      }).join('');



      // Overview Alerts & Pending Approvals

      const pendingTasks = STATE.tasks.filter(x => x.ui_status === 'WAITING_FOR_APPROVAL' || x.status === 'AWAITING_APPROVAL');

      const unapprovedLeads = STATE.leads.filter(l => l.requires_owner_approval);

      const alertItems = [];

      if (rawAiMode.includes('MOCK')) {

        alertItems.push(t(

          `<li><span class="chip warn">CHẾ ĐỘ CỤC BỘ</span> Đang dùng kiểm toán Python nội bộ; không có lượt gọi provider trả phí được ghi nhận. Điện và chi phí máy local chưa được đo.</li>`,

          `<li><span class="chip warn">LOCAL ENGINE</span> Using the local Python audit path; no paid-provider call is recorded. Electricity and local compute costs are unmeasured.</li>`

        ));

      }

      if (pendingTasks.length > 0) {

        alertItems.push(t(

          `<li>Có <strong>${pendingTasks.length}</strong> nhiệm vụ AI đang ở trạng thái <code>CHỜ PHÊ DUYỆT</code> tại mục <strong>Đội Ngũ Nhân Sự AI Đang Hoạt Động</strong>.</li>`,

          `<li>There are <strong>${pendingTasks.length}</strong> AI tasks in <code>WAITING_FOR_APPROVAL</code> state under <strong>AI Agents</strong>.</li>`

        ));

      }

      if (unapprovedLeads.length > 0) {

        alertItems.push(t(

          `<li>Có <strong>${unapprovedLeads.length}</strong> khách hàng tiềm năng đã có báo cáo lỗi kỹ thuật &amp; đề xuất cá nhân hóa đang chờ bạn duyệt gửi tại mục <strong>Khách Hàng Tiềm Năng</strong>.</li>`,

          `<li>There are <strong>${unapprovedLeads.length}</strong> prospective leads with technical defect reports &amp; custom proposals awaiting your approval under <strong>Leads &amp; Customers</strong>.</li>`

        ));

      }

      if (document.getElementById('overviewAlertsContainer')) document.getElementById('overviewAlertsContainer').innerHTML = alertItems.length

        ? `<ul style="padding-left: 18px; font-size: 13px; color: var(--text-secondary); display: flex; flex-direction: column; gap: 8px;">${alertItems.join('')}</ul>`

        : `<div class="empty-state">${t('Hệ thống hoạt động bình thường, không có cảnh báo tồn đọng.', 'System operating normally with zero pending alerts.')}</div>`;



      // 2. AI AGENTS VIEW

      document.getElementById('agentProviderNotice').innerHTML = CURRENT_LANG === 'en'

        ? `Current AI Mode: <strong>${escapeHtml(rawAiMode)}</strong> | Orchestrator Status: <strong>${escapeHtml(rawSysStatus)}</strong> | Single-Worker Lock: <strong>ACTIVE</strong>`

        : `Chế độ AI hiện tại: <strong>${escapeHtml(trContent(rawAiMode))}</strong> | Trạng thái Bộ điều phối: <strong>${escapeHtml(formatStatusLabel(rawSysStatus))}</strong> | Khóa chống chạy trùng: <strong>ĐANG BẬT</strong>`;



      const agGrid = document.getElementById('agentsRegistryGrid');
      if (agGrid) {
        const message = t(
          'Chưa có hoạt động agent runtime đã xác minh từ backend.',
          'No verified agent runtime activity from the backend.'
        );
        agGrid.replaceChildren();
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        emptyState.textContent = message;
        agGrid.appendChild(emptyState);
        const capChip = document.getElementById('workforceCapacityChip');
        if (capChip) capChip.textContent = message;
      }

      document.getElementById('tasksTableBody').innerHTML = STATE.tasks.length === 0

        ? `<tr><td colspan="7" class="empty-state">${t('Chưa có nhiệm vụ AI nào được ghi nhận.', 'No AI tasks recorded yet.')}</td></tr>`

        : STATE.tasks.slice(0, 40).map(taskItem => {

            const uiSt = taskItem.ui_status || taskItem.status;

            const planStr = Array.isArray(taskItem.action_plan) && taskItem.action_plan.length ? taskItem.action_plan.join(' → ') : taskItem.objective;

            const canApprove = taskItem.status === 'AWAITING_APPROVAL' || uiSt === 'WAITING_FOR_APPROVAL';

            return `

              <tr>

                <td style="font-family:var(--font-mono); font-size:11px;">

                  <div>${escapeHtml(String(taskItem.id).slice(0, 12))}...</div>

                  <div style="color:var(--text-muted); margin-top:3px;">${escapeHtml(taskItem.started_at ? new Date(taskItem.started_at).toLocaleString(localeCode) : '')}</div>

                </td>

                <td>

                  <div style="font-weight:600; color:#fff;">${escapeHtml(trContent(taskItem.title))}</div>

                  <div style="font-size:11px; color:var(--accent-cyan); font-family:var(--font-mono);">${escapeHtml(formatAgentTitle(taskItem.agent_role, taskItem.agent_role))}</div>

                </td>

                <td style="font-size:11.5px; color:var(--text-secondary);">

                  <div><strong>${t('Nguồn', 'Source')}:</strong> ${escapeHtml(trContent(taskItem.data_source || 'SQLite & Public API'))}</div>

                  <div style="margin-top:3px;"><strong>${t('Kế hoạch', 'Plan')}:</strong> ${escapeHtml(trContent(String(planStr).slice(0, 120)))}</div>

                </td>

                <td>

                  <span class="chip ${uiSt === 'COMPLETED' ? 'success' : (uiSt === 'WAITING_FOR_APPROVAL' ? 'warn' : (uiSt === 'STOPPED' || uiSt === 'FAILED' || uiSt === 'BLOCKED' ? 'danger' : 'cyan'))}">${escapeHtml(formatStatusLabel(uiSt))}</span>

                </td>

                <td style="font-family:var(--font-mono); font-size:11.5px;">

                  <div>$${Number(taskItem.actual_cost_usd || 0).toFixed(4)}</div>

                  <div style="color:var(--text-secondary);">${t('Kiểm thử', 'Test')}: ${escapeHtml(formatStatusLabel(taskItem.test_result || 'PASSED'))}</div>

                </td>

                <td style="font-size:11.5px; color:var(--text-secondary); max-width:260px;">

                  <div>${escapeHtml(trContent(taskItem.evidence || taskItem.outcome_reason || 'Hoàn tất'))}</div>

                  ${taskItem.error_message ? `<div style="color:var(--status-danger); margin-top:3px;">${t('Lỗi', 'Error')}: ${escapeHtml(trContent(taskItem.error_message))}</div>` : ''}

                </td>

                <td>

                  <div style="font-size:11.5px; color:var(--text-secondary); margin-bottom:6px;">${escapeHtml(trContent(taskItem.next_action || ''))}</div>

                  ${canApprove ? `<button class="btn btn-sm btn-primary" onclick="approveAgentTask('${escapeHtml(taskItem.id)}')">${t('✓ Phê Duyệt (Quản Trị)', '✓ Approve Task (Admin)')}</button>` : ''}

                </td>

              </tr>

            `;

          }).join('');



      // 3. OPPORTUNITIES VIEW

      document.getElementById('opportunitiesTableBody').innerHTML = STATE.opportunities.length === 0

        ? `<tr><td colspan="7" class="empty-state">${t('Chưa có dữ liệu cơ hội kinh doanh.', 'No business opportunities recorded yet.')}</td></tr>`

        : STATE.opportunities.map(o => {

            const skills = Array.isArray(o.required_skills) ? o.required_skills : ['Python Automation', 'Technical SEO'];

            const pubBudget = o.published_budget_usd !== null && o.published_budget_usd !== undefined

              ? `$${Number(o.published_budget_usd).toFixed(2)} USD (${t('Công bố', 'Published')})`

              : t(

                  `Không công bố (Giá dịch vụ đề xuất: $${Number(o.reference_price_usd || 29).toFixed(2)})`,

                  `Undisclosed (Recommended Service Price: $${Number(o.reference_price_usd || 29).toFixed(2)})`

                );

            return `

              <tr>

                <td>

                  <div style="font-weight:600; color:#fff;">${escapeHtml(trContent(o.project_title || o.name))}</div>

                  <div style="font-size:11.5px; color:var(--text-secondary); margin-top:4px;">

                    ${t('Nguồn', 'Source')}: ${escapeHtml(o.data_source)}

                    ${o.source_url ? `<br/><a href="${escapeHtml(o.source_url)}" target="_blank" rel="noopener" style="color:var(--accent-cyan);">${t('↗ Mở liên kết gốc', '↗ Open Original URL')}</a>` : ''}

                  </div>

                </td>

                <td style="font-size:11.5px; color:var(--text-secondary);">

                  <div><strong>${t('Phát hiện', 'Discovered')}:</strong> ${escapeHtml(o.collected_at ? new Date(o.collected_at).toLocaleDateString(localeCode) : t('Hôm nay', 'Today'))}</div>

                  <div style="margin-top:4px;"><strong>${t('Thời hạn', 'Deadline')}:</strong> ${escapeHtml(trContent(o.deadline || 'Không giới hạn'))}</div>

                </td>

                <td style="max-width:270px;">

                  <div style="font-size:12px; color:var(--text-primary); margin-bottom:6px;">${escapeHtml(trContent(o.actual_requirements || o.problem_statement))}</div>

                  <div style="display:flex; gap:4px; flex-wrap:wrap;">

                    ${skills.map(s => `<span class="chip" style="font-size:10px; padding:2px 6px;">${escapeHtml(s)}</span>`).join('')}

                  </div>

                </td>

                <td style="font-family:var(--font-mono); font-size:11.5px;">

                  <div style="color:#fff;">${escapeHtml(pubBudget)}</div>

                  <div style="color:var(--text-secondary); margin-top:4px;">${t('Chi phí ước tính', 'Estimated Cost')}: $${Number(o.estimated_cost_usd ?? 0.06).toFixed(2)}</div>

                </td>

                <td>

                  <span class="chip ${Number(o.fit_score || o.total_score) >= 82 ? 'success' : 'purple'}">${Number(o.fit_score || o.total_score || 0).toFixed(1)} / 100</span>

                </td>

                <td style="font-size:11.5px; color:var(--text-secondary); max-width:260px;">

                  <div><strong>${t('Rủi ro', 'Risks')}:</strong> ${escapeHtml(trContent(o.risks))}</div>

                  <div style="margin-top:4px; color:#c4b5fd;"><strong>${t('Lý do chọn/loại', 'Selection Reason')}:</strong> ${escapeHtml(trContent(o.selection_or_rejection_reason))}</div>

                </td>

                <td style="font-size:11.5px; color:var(--text-secondary); max-width:210px;">

                  ${escapeHtml(trContent(o.next_action))}

                </td>

              </tr>

            `;

          }).join('');



      // 4. LEADS & CUSTOMERS VIEW

      document.getElementById('leadsTableBody').innerHTML = STATE.leads.length === 0

        ? `<tr><td colspan="7" class="empty-state">${t('Chưa có dữ liệu khách hàng tiềm năng.', 'No prospective leads recorded yet.')}</td></tr>`

        : STATE.leads.map(l => {

            const cFlag = l.country_flag || '🇺🇸';

            const cName = l.country_name || 'United States / Global';

            const lName = l.language_name || 'English (International Business)';

            return `

              <tr>

                <td>

                  <div style="font-weight:600; color:#fff;">${escapeHtml(l.name)}</div>

                  <div style="font-size:11.5px; color:var(--accent-cyan); word-break:break-all;">

                    ${l.company && l.company.startsWith('http') ? `<a href="${escapeHtml(l.company)}" target="_blank" rel="noopener" style="color:var(--accent-cyan);">${escapeHtml(l.company)}</a>` : escapeHtml(l.company || l.email)}

                  </div>

                  <div style="margin-top:4px;">

                    <span class="chip cyan" style="font-size:10px; padding:2px 6px;">${escapeHtml(cFlag)} ${escapeHtml(cName)} • ${escapeHtml(lName)}</span>

                  </div>

                </td>

                <td style="font-size:11.5px; color:var(--text-secondary); max-width:180px;">

                  ${escapeHtml(trContent(l.source || l.acquisition_source))}

                </td>

                <td style="font-size:12px; color:var(--text-primary); max-width:250px;">

                  ${escapeHtml(trContent(l.need))}

                </td>

                <td style="font-size:12px;">

                  <div>${escapeHtml(trContent(l.matched_service))}</div>

                  <div style="font-family:var(--font-mono); color:var(--accent-cyan); font-weight:600; margin-top:3px;">$${Number(l.estimated_order_value_usd || 29).toFixed(2)} USD</div>

                </td>

                <td>

                  <span class="chip success">${Number(l.fit_score || 85)}/100</span>

                </td>

                <td style="font-size:11.5px; color:var(--text-secondary); max-width:320px;">

                  <div style="margin-bottom:4px; display:flex; gap:4px; flex-wrap:wrap;">

                    <span class="chip success">${t('✅ AI ĐÃ TỰ ĐỘNG DUYỆT', '✅ AI AUTO-APPROVED')}</span>

                    <span class="chip purple">${escapeHtml(cFlag)} ${escapeHtml(l.language_code ? l.language_code.toUpperCase() : 'EN')}</span>

                  </div>

                  <div style="max-height:95px; overflow-y:auto; white-space:pre-wrap; font-family:var(--font-mono); font-size:10.5px; background:rgba(15,23,42,0.75); padding:6px; border-radius:6px;">${escapeHtml(l.custom_proposal || '')}</div>

                </td>

                <td>

                  <div style="display:flex; flex-direction:column; gap:6px;">

                    <button class="btn btn-sm" onclick="copyLeadProposal('${escapeHtml(l.id)}')">${t('📋 Sao Chép Email Đúng Ngôn Ngữ', '📋 Copy Localized Email')}</button>

                    <button class="btn btn-sm btn-cyan" onclick="prefillOrderForLead('${escapeHtml(l.id)}')">${t('+ Tạo Đơn Hàng', '+ Create Order')}</button>

                  </div>

                </td>

              </tr>

            `;

          }).join('');



      // 5. PRODUCTS & SERVICES VIEW

      const prodSelect = document.getElementById('productEditSelect');

      const orderProdSelect = document.getElementById('orderProductSelect');

      if (STATE.products.length > 0) {

        const optsHtml = STATE.products.map(p => `<option value="${escapeHtml(p.id)}">${escapeHtml(trContent(p.name))} ($${Number(p.price_usd).toFixed(2)})</option>`).join('');

        prodSelect.innerHTML = optsHtml;

        orderProdSelect.innerHTML = optsHtml;

        populateProductEditForm();

      } else {

        prodSelect.innerHTML = `<option value="">${t('Chưa có sản phẩm', 'No products available')}</option>`;

        orderProdSelect.innerHTML = `<option value="">${t('Chưa có sản phẩm', 'No products available')}</option>`;

      }



      document.getElementById('productsTableBody').innerHTML = STATE.products.length === 0

        ? `<tr><td colspan="6" class="empty-state">${t('Chưa có sản phẩm số nào.', 'No digital products available.')}</td></tr>`

        : STATE.products.map(p => `

            <tr>

              <td>

                <div style="font-weight:600; color:#fff;">${escapeHtml(trContent(p.name))}</div>

                <div style="font-size:11.5px; color:var(--text-secondary); margin-top:3px;">${escapeHtml(trContent(p.problem_solved))}</div>

              </td>

              <td style="font-family:var(--font-mono); font-size:14px; font-weight:700; color:var(--accent-cyan);">

                $${Number(p.price_usd).toFixed(2)} USD

              </td>

              <td>

                <span class="chip ${p.test_passed ? 'success' : 'danger'}">${p.test_passed ? t('ĐẠT (2/2 Bài Tự Kiểm Thử)', 'PASSED (2/2 Self-Tests)') : t('THẤT BẠI', 'FAILED')}</span>

              </td>

              <td style="font-size:11.5px; color:var(--text-secondary);">

                ${t('Đầu vào: Địa chỉ URL / Mã HTML<br/>Đầu ra: Báo cáo JSON + Mã sửa lỗi HTML/Schema', 'Input: Website URL / Raw HTML<br/>Output: JSON Audit Report + HTML/Schema Fix Code')}

              </td>

              <td style="font-size:11.5px; color:var(--text-secondary);">

                ${t('Tự động mở khóa qua <code>/api/orders/{id}/deliver</code> sau khi xác minh thanh toán', 'Automatically unlocked via <code>/api/orders/{id}/deliver</code> after verified payment')}

              </td>

              <td>

                <a class="btn btn-sm" href="${API_BASE}/api/products/${encodeURIComponent(p.id)}/download" target="_blank" rel="noopener">${t('⬇ Tải .py', '⬇ Download .py')}</a>

              </td>

            </tr>

          `).join('');



      // 6. ORDERS & PAYMENTS VIEW — Strictly filter out any test/dummy PENDING_PAYMENT orders; keep ONLY real verified orders

      if (Array.isArray(STATE.orders)) {

        STATE.orders = STATE.orders.filter(o => {

          if (!o) return false;

          const num = String(o.order_number || '');

          const prop = String(o.proposal_text || '');

          if (num.includes('ORD-20261028-') || prop.includes('mmo_buyer_') || prop.includes('buyer@autoprofit.vn')) return false;

          // Keep real unpaid and pending-review orders visible after reload for reconciliation.
          return true;

        });

      }

      const badgeOrdEl = document.getElementById('badge-orders');

      if (badgeOrdEl) badgeOrdEl.textContent = String(STATE.orders.length);



      const custSelect = document.getElementById('orderCustomerSelect');

      custSelect.innerHTML = STATE.leads.length

        ? STATE.leads.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)} (${escapeHtml(c.company || c.email)})</option>`).join('')

        : `<option value="">${t('Chưa có khách hàng', 'No customers yet')}</option>`;



      const verifyOrdSelect = document.getElementById('verifyOrderSelect');

      verifyOrdSelect.innerHTML = STATE.orders.length

        ? STATE.orders.map(o => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.order_number)} — $${Number(o.net_amount_usd).toFixed(2)} (${escapeHtml(formatStatusLabel(o.status))})</option>`).join('')

        : `<option value="">${t('Chưa có đơn hàng', 'No orders yet')}</option>`;



      document.getElementById('ordersTableBody').innerHTML = STATE.orders.length === 0

        ? `<tr><td colspan="7" class="empty-state">${t('Chưa có đơn hàng nào.', 'No orders created yet.')}</td></tr>`

        : STATE.orders.map(o => {

            const isPaid = o.status === 'FULFILLED' || o.status === 'PAID_VERIFIED';

            const isPendingVer = o.status === 'PENDING_VERIFICATION';

            return `

              <tr>

                <td style="font-family:var(--font-mono); font-weight:600; color:#fff;">${escapeHtml(o.order_number)}</td>

                <td style="font-size:12px;">

                  <div>${t('Mã KH', 'Customer ID')}: <code>${escapeHtml(String(o.customer_id).slice(0, 8))}...</code></div>

                  <div style="color:var(--text-secondary); margin-top:2px;">${escapeHtml(trContent(o.proposal_text || 'Website Technical Audit & SEO Fix'))}</div>

                </td>

                <td style="font-family:var(--font-mono); font-weight:700; color:var(--accent-cyan);">

                  $${Number(o.net_amount_usd).toFixed(2)}

                </td>

                <td style="font-family:var(--font-mono); font-size:11.5px;">${escapeHtml(o.payment_provider)}</td>

                <td>

                  <span class="chip ${isPaid ? 'success' : (isPendingVer ? 'warn' : 'purple')}">${escapeHtml(formatStatusLabel(o.status))}</span>

                </td>

                <td style="font-size:11.5px; color:var(--text-secondary);">

                  ${escapeHtml(o.created_at ? new Date(o.created_at).toLocaleString(localeCode) : '')}

                </td>

                <td>

                  <button class="btn btn-sm ${isPaid ? 'btn-success' : ''}" onclick="deliverOrderPackage('${escapeHtml(o.id)}')">

                    ${isPaid ? t('📦 Nhận Bàn Giao', '📦 Get Deliverable') : t('🔒 Kiểm Tra Bàn Giao', '🔒 Check Delivery')}

                  </button>

                </td>

              </tr>

            `;

          }).join('');

      renderAdminPaymentReports();



      // 7. MARKETING & SEO VIEW

      document.getElementById('marketingTableBody').innerHTML = STATE.marketing.length === 0

        ? `<tr><td colspan="6" class="empty-state">${t('Chưa có tài sản tiếp thị nào.', 'No marketing assets generated yet.')}</td></tr>`

        : STATE.marketing.map(m => `

            <tr>

              <td style="font-weight:600; color:#fff;">${escapeHtml(trContent(m.title))}</td>

              <td><span class="chip cyan">${escapeHtml(m.asset_type)} / ${escapeHtml(m.channel)}</span></td>

              <td style="font-size:11.5px; color:var(--text-secondary);">${escapeHtml(m.target_keywords)}</td>

              <td style="font-family:var(--font-mono); font-size:11.5px;">${t('Lượt xem', 'Visits')}: ${Number(m.visits || 0)} | ${t('Chuyển đổi', 'Conv')}: ${Number(m.conversions || 0)}</td>

              <td><span class="chip">${escapeHtml(formatStatusLabel(m.status))}</span></td>

              <td style="font-size:11.5px; color:var(--text-secondary); max-width:320px;">

                <div>${escapeHtml(trContent(String(m.content_body || '').slice(0, 160)))}...</div>

                <div style="color:var(--text-muted); margin-top:3px;">${t('Nhãn minh bạch', 'Disclosure')}: ${escapeHtml(trContent(m.affiliate_disclosure || 'Included'))}</div>

              </td>

            </tr>

          `).join('');



      // 9. ANALYTICS VIEW (9-BUCKET HONEST ACCOUNTING)

      const bucketRows = [

        {

          idx: 1,

          name: t('1. Doanh thu đã xác minh (Thực nhận)', '1. Verified Revenue (Settled)'),

          val: nine['1_verified_revenue_usd'] ?? null,

          rule: t(

            'Chỉ cộng khi giao dịch On-Chain BSC (ChainID 56, >=3 xác nhận) hoặc sao kê ngân hàng được Chủ tài khoản xác minh.',

            'Counted strictly when an on-chain BSC transaction (ChainID 56, >=3 confirmations) or bank statement is verified by the Owner.'

          )

        },

        {

          idx: 2,

          name: t('2. Khoản đang chờ đối soát', '2. Pending Payments (Awaiting Verification)'),

          val: nine['2_pending_payments_usd'] ?? null,

          rule: t(

            'Mã tham chiếu khách tự nhập (CHỜ ĐỐI SOÁT) hoặc tiền đang giữ tại cổng trung gian.',

            'Customer-submitted bank reference codes (PENDING_VERIFICATION) awaiting statement reconciliation.'

          )

        },

        {

          idx: 3,

          name: t('3. Doanh thu dự kiến (Đơn chưa thanh toán)', '3. Estimated Revenue (Unpaid Orders)'),

          val: nine['3_estimated_revenue_usd'] ?? null,

          rule: t(

            'Tổng giá trị các đơn hàng ở trạng thái CHỜ THANH TOÁN.',

            'Total value of open orders currently in PENDING_PAYMENT state.'

          )

        },

        {

          idx: 4,

          name: t('4. Tiền hoàn lại cho khách', '4. Customer Refunds'),

          val: nine['4_refunds_usd'] ?? null,

          rule: t(

            'Các khoản hoàn trả cho khách theo chính sách bảo hành 7 ngày.',

            'Refunded amounts issued under the 7-day technical warranty policy.'

          )

        },

        {

          idx: 5,

          name: t('5. Chi phí mô hình AI', '5. AI Model Costs'),

          val: nine['5_ai_costs_usd'] ?? null,

          rule: t(

            'Chi phí token chỉ hiển thị khi ledger nhà cung cấp ghi nhận; chi phí máy local chưa được đo.',

            'Token cost appears only when reported by the provider ledger; local compute cost is unmeasured.'

          )

        },

        {

          idx: 6,

          name: t('6. Chi phí máy chủ & Hạ tầng', '6. Hosting & Infrastructure Costs'),

          val: nine['6_hosting_costs_usd'] ?? null,

          rule: t(

            'Chi phí máy chủ đám mây thực tế phát sinh.',

            'Actual cloud server or infrastructure expenses incurred.'

          )

        },

        {

          idx: 7,

          name: t('7. Phí nền tảng & Thanh toán', '7. Marketplace & Payment Fees'),

          val: nine['7_marketplace_fees_usd'] ?? null,

          rule: t(

            'Phí sàn giao dịch hoặc phí cổng thanh toán.',

            'Platform commission or payment gateway processing fees.'

          )

        },

        {

          idx: 8,

          name: t('8. Chi phí vận hành khác', '8. Other Operating Expenses'),

          val: nine['8_other_expenses_usd'] ?? null,

          rule: t(

            'Chi phí sản xuất, thuế khấu trừ và chi phí vận hành khác.',

            'Production costs, taxes, and miscellaneous operational expenses.'

          )

        },

        {

          idx: 9,

          name: t('9. Lợi nhuận ròng thực tế', '9. Net Profit'),

          val: nine['9_net_profit_usd'] ?? null,

          rule: t(

            'Doanh thu đã xác minh trừ đi toàn bộ Hoàn tiền, Chi phí AI, Máy chủ, Phí nền tảng và Chi phí khác.',

            'Verified Revenue minus all Refunds, AI Costs, Hosting Costs, Marketplace Fees, and Other Expenses.'

          )

        }

      ];

      document.getElementById('nineBucketTableBody').innerHTML = bucketRows.map(r => `

        <tr>

          <td style="font-family:var(--font-mono); font-weight:700;">0${r.idx}</td>

          <td style="font-weight:600; color:#fff;">${escapeHtml(r.name)}</td>

          <td style="font-family:var(--font-mono); font-size:13.5px; font-weight:700; color:${r.idx === 1 || r.idx === 9 ? 'var(--accent-cyan)' : 'var(--text-primary)'};">

            ${escapeHtml(formatFinanceValue(r.val, 4))}

          </td>

          <td style="font-size:12px; color:var(--text-secondary);">${escapeHtml(r.rule)}</td>

        </tr>

      `).join('');



      document.getElementById('transactionsTableBody').innerHTML = STATE.transactions.length === 0

        ? `<tr><td colspan="4" class="empty-state">${t('Chưa có giao dịch thanh toán nào.', 'No payment transactions recorded yet.')}</td></tr>`

        : STATE.transactions.map(tx => `

            <tr>

              <td style="font-family:var(--font-mono); font-size:11.5px;">${escapeHtml(tx.provider_tx_id)}</td>

              <td>${escapeHtml(tx.provider)}</td>

              <td style="font-family:var(--font-mono);">$${Number(tx.amount_usd).toFixed(2)}</td>

              <td>

                <span class="chip ${tx.webhook_verified && !tx.is_simulated ? 'success' : 'warn'}">

                  ${tx.is_simulated ? t('MÔ PHỎNG KIỂM THỬ', 'SANDBOX_SIMULATED') : escapeHtml(formatStatusLabel(tx.settlement_stage))}

                </span>

              </td>

            </tr>

          `).join('');



      const sim = STATE.finance?.sandbox_simulated_metrics || {};

      document.getElementById('sandboxMetricsBox').innerHTML = `

        <div style="display:flex; flex-direction:column; gap:8px;">

          <div>• ${t('Doanh thu mô phỏng kiểm thử', 'Simulated Test Revenue')}: <code>$${Number(sim['2_confirmed_revenue_usd'] || 0).toFixed(2)}</code></div>

          <div>• ${t('Chi phí AI mô phỏng kiểm thử', 'Simulated AI Costs')}: <code>$${Number(sim.ai_costs_usd || 0).toFixed(4)}</code></div>

          <div>• ${t('Số đơn hàng thử nghiệm', 'Simulated Test Orders')}: <code>${Number(sim.completed_orders_count || 0)}</code></div>

          <div style="color:var(--text-muted); font-size:12px;">${t('Lưu ý: Toàn bộ số liệu thử nghiệm trên chỉ phục vụ kiểm thử tự động (pytest), tuyệt đối không cộng vào Doanh Thu Xác Thực hay Lợi Nhuận Ròng.', 'Note: All sandbox metrics above are strictly for automated testing (pytest) and are never added to Verified Revenue or Net Profit.')}</div>

        </div>

      `;



      // 10. SECURITY & SETTINGS VIEW

      if (STATE.budgets) {

        document.getElementById('cfgOperatingMode').value = STATE.budgets.operating_mode || 'GUARDED_AUTONOMY';

        document.getElementById('cfgMaxDailyTasks').value = STATE.budgets.max_daily_tasks ?? 50;

        document.getElementById('cfgDailyBudget').value = STATE.budgets.daily_budget_limit_usd ?? 5.0;

        document.getElementById('cfgMonthlyBudget').value = STATE.budgets.monthly_budget_limit_usd ?? 50.0;

        document.getElementById('cfgTaskBudget').value = STATE.budgets.task_budget_limit_usd ?? 1.0;

      }



      document.getElementById('auditLogsTableBody').innerHTML = STATE.auditLogs.length === 0

        ? `<tr><td colspan="6" class="empty-state">${t('Chưa có bản ghi kiểm toán bảo mật.', 'No security audit log records yet.')}</td></tr>`

        : STATE.auditLogs.slice(0, 35).map(l => `

            <tr>

              <td style="font-family:var(--font-mono); font-size:11px; color:var(--text-secondary);">${escapeHtml(l.created_at ? new Date(l.created_at).toLocaleString(localeCode) : '')}</td>

              <td style="font-family:var(--font-mono); font-size:11.5px;">${escapeHtml(l.actor)} (${escapeHtml(l.role)})</td>

              <td style="font-weight:600; color:#fff;">${escapeHtml(l.action)}</td>

              <td style="font-size:11.5px;">${escapeHtml(l.resource_type)} #${escapeHtml(String(l.resource_id).slice(0, 8))}</td>

              <td><span class="chip ${l.status === 'ALLOWED' ? 'success' : 'danger'}">${escapeHtml(formatStatusLabel(l.status))}</span></td>

              <td style="font-family:var(--font-mono); font-size:11px; color:var(--text-secondary); max-width:260px;">${escapeHtml(JSON.stringify(l.details || {}))}</td>

            </tr>

          `).join('');



      // Render Dynamic AI Workforce, Public Ads/Donations, 12-Bucket Ledger & Payout Policy

      renderDynamicWorkforceAndPortalPanels();

      renderCompactOverviewAndDynamicPricing();

      if (typeof renderHumanStyleAiNotebook === 'function') renderHumanStyleAiNotebook();

      if (typeof detectVisitorGeoIpAndConfigureDonation === 'function') detectVisitorGeoIpAndConfigureDonation();

      if (!TRAFFIC_HEARTBEAT_TIMER && typeof startVisitorTrafficHeartbeatLoop === 'function') startVisitorTrafficHeartbeatLoop();

      if (typeof loadAndRenderGithubWebFactory === 'function') loadAndRenderGithubWebFactory();

    }



    let IS_OWNER_ADMIN_VERIFIED = Boolean(sessionStorage.getItem('autoprofit_owner_admin_key'));



    function updatePortalAccessModeUi() {

      IS_OWNER_ADMIN_VERIFIED = Boolean(sessionStorage.getItem('autoprofit_owner_admin_key'));

      document.body.classList.toggle('visitor-readonly-mode', !IS_OWNER_ADMIN_VERIFIED);

      const btn = document.getElementById('portalAccessModeBtn');

      if (btn) {

        if (IS_OWNER_ADMIN_VERIFIED) {

          btn.textContent = t('🔐 Chế Độ Chủ Sở Hữu (Đầy Đủ Quyền Admin)', '🔐 Owner Admin Mode (Full Access)');

          btn.style.borderColor = '#10b981';

          btn.style.color = '#6ee7b7';

        } else {

          btn.textContent = t('👁️ Khách Tham Quan (Chỉ Xem • Khóa Quyền Admin)', '👁️ Public Visitor (Read-Only • Admin Locked)');

          btn.style.borderColor = 'rgba(56,189,248,0.55)';

          btn.style.color = '#e2e8f0';

        }

      }

    }



    // Strict Global Capture-Phase Interceptor: Prevents Public Visitors from triggering ANY Admin action

    const ADMIN_ONLY_FN_PATTERNS = [

      'runAutonomousCycle',

      'triggerOrchestratorCycle',

      'triggerRealAgentCommTurn',

      'triggerSampleDialoguePreview',

      'runLiveInternetScan',

      'triggerAutoApproveAllLeadsNow',

      'approveLeadProposal',

      'approveOpportunity',

      'rejectOpportunity',

      'approveAgentTask',

      'cancelAgentTask',

      'createManualTask',

      'createNewProduct',

      'saveProductPriceEdit',

      'saveOwnerCatalogPricingConfig',

      'generateAiPricingRecommendationsNow',

      'reviewPricingRecommendation',

      'verifyOrderPayment',

      'verifyDonationStatus',

      'verifyAdInquiryPayment',

      'proposeDynamicEmployee',

      'approveDynamicEmployeeById',

      'retireDynamicEmployeeById',

      'savePayoutPolicyConfig',

      'saveSystemConfig',

      'triggerEmergencyStop',

      'resetEmergencyStop',

      'promptUpdateAadsUnitId',

      'toggleVisitorGeoSimulationMode',

      'triggerGithubWebFactoryScanNow'

    ];



    window.addEventListener('click', (ev) => {

      if (IS_OWNER_ADMIN_VERIFIED) return;

      const targetBtn = ev.target && ev.target.closest ? ev.target.closest('[onclick], .admin-only-control') : null;

      if (!targetBtn) return;

      const onclickAttr = targetBtn.getAttribute('onclick') || '';

      const isAdminControl = targetBtn.classList.contains('admin-only-control') ||

        ADMIN_ONLY_FN_PATTERNS.some(fnName => onclickAttr.includes(fnName));

      if (isAdminControl) {

        ev.preventDefault();

        ev.stopPropagation();

        ev.stopImmediatePropagation();

        showToast('🔒 Quyền Quản Trị (Admin Only): Khách tham quan chỉ có quyền xem, trò chuyện với AI, dùng thử công cụ Web và đặt mua/ủng hộ!', true);

      }

    }, true);

    const DEFAULT_GITHUB_WEB_FACTORY_DATA = { status: "no_data", total: 0, items: [], revenue_streams_breakdown: [] };

    let GITHUB_WEB_FACTORY_CACHE = DEFAULT_GITHUB_WEB_FACTORY_DATA;

    let ACTIVE_USER_AADS_UNIT_ID = '';

    let IS_GITHUB_WEB_FACTORY_BACKEND_LIVE = false;
    let GITHUB_WEB_FACTORY_CATALOG_READY = false;

    const GITHUB_WEB_FACTORY_SLUG_ALIASES = {
      'github-vietqr-crypto-payment-link-maker': 'vietqr-crypto-payment-generator',
      'github-defi-stablecoin-apy-yield-optimizer': 'defi-staking-yield-compounder',
      'github-papaparse-csv-to-json-converter': 'papaparse-csv-to-json-cleaner',
      'github-css-glassmorphism-landing-builder': 'css-glassmorphism-card-builder'
    };

    function normalizeGithubWebFactorySlug(slug) {
      const value = String(slug || '').trim();
      return GITHUB_WEB_FACTORY_SLUG_ALIASES[value]
        || (value.startsWith('github-') ? value.slice('github-'.length) : value);
    }

    function findGithubWebFactoryProduct(slug) {
      const items = Array.isArray(GITHUB_WEB_FACTORY_CACHE?.items) ? GITHUB_WEB_FACTORY_CACHE.items : [];
      const normalized = normalizeGithubWebFactorySlug(slug);
      return items.find(item => item.slug === slug || item.slug === normalized) || null;
    }



    async function loadAndRenderGithubWebFactory() {

      try {

        const data = await apiFetch('/api/github-web-factory/apps');

        GITHUB_WEB_FACTORY_CACHE = data;

        IS_GITHUB_WEB_FACTORY_BACKEND_LIVE = true;
        GITHUB_WEB_FACTORY_CATALOG_READY = true;

        renderGithubWebFactorySection(data);

      } catch (_) {

        IS_GITHUB_WEB_FACTORY_BACKEND_LIVE = false;
        GITHUB_WEB_FACTORY_CATALOG_READY = true;

        renderGithubWebFactorySection(GITHUB_WEB_FACTORY_CACHE || DEFAULT_GITHUB_WEB_FACTORY_DATA);

      }

    }



    let GITHUB_WEBAPPS_VISIBLE_LIMIT = 6;





    function showMoreGithubWebApps() {

      GITHUB_WEBAPPS_VISIBLE_LIMIT += 10;

      renderGithubWebFactorySection(GITHUB_WEB_FACTORY_CACHE);

    }



    function showAllGithubWebApps() {

      GITHUB_WEBAPPS_VISIBLE_LIMIT = 9999;

      renderGithubWebFactorySection(GITHUB_WEB_FACTORY_CACHE);

    }



    function collapseToTop5GithubWebApps() {

      GITHUB_WEBAPPS_VISIBLE_LIMIT = 6;

      renderGithubWebFactorySection(GITHUB_WEB_FACTORY_CACHE);

    }



    function sanitizeCommercialAppNameVi(nameVi, repoStr) {

      let s = String(nameVi || '').trim();

      if (repoStr && repoStr.includes('/')) {

        const repoPart = repoStr.split('/')[1].replace(/[-_.]/g, ' ');

        s = s.replace(repoStr, repoPart.toUpperCase() + ' PRO');

      }

      s = s.replace(/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+/g, (m) => m.split('/').pop().replace(/[-_.]/g, ' ').toUpperCase() + ' PRO');

      s = s.replace(/Đóng Gói Tự Động Từ GitHub/g, 'Bản Thương Mại Độc Quyền');

      return s;

    }



    function sanitizeCommercialSummaryVi(sumVi) {

      let s = String(sumVi || '').trim();

      s = s.replace(/Quét trực tiếp từ GitHub/g, 'Ứng dụng Web thương mại đóng gói độc quyền');

      s = s.replace(/https?:\/\/github\.com\/[^\s)]+/g, '');

      return s;

    }



    function renderGithubWebFactorySection(data) {

      if (!data) return;

      const streamsGrid = document.getElementById('aiRevenueStreamsBreakdownGrid');

      const appsGrid = document.getElementById('githubWebFactoryAppsGrid');

      const countChip = document.getElementById('githubWebAppsCountChip');

      const moreBtn = document.getElementById('btnLoadMoreGithubApps');



      const streams = data.revenue_streams_breakdown || [];

      const allApps = data.items || [];

      const q = (document.getElementById('githubWebAppSearchInput')?.value || '').trim().toLowerCase();

      const catFilter = document.getElementById('githubWebAppCategorySelect')?.value || 'ALL';



      const filteredApps = allApps.filter(app => {

        if (catFilter !== 'ALL' && !(app.category || '').toLowerCase().includes(catFilter.toLowerCase())) {

          return false;

        }

        if (q) {

          const hay = `${app.app_name_vi || ''} ${app.github_repo || ''} ${app.category || ''} ${app.monetization_summary_vi || ''}`.toLowerCase();

          if (!hay.includes(q)) return false;

        }

        return true;

      });



      if (countChip) {

        const trueTotal = Math.max(Number(data.total || 0), allApps.length);
        countChip.textContent = trueTotal
          ? `Đang hiện ${Math.min(GITHUB_WEBAPPS_VISIBLE_LIMIT, filteredApps.length)} / ${trueTotal} Web App`
          : 'Chưa có catalog Web App được xác minh';

      }

      const showAllBtn = document.getElementById('btnShowAllGithubApps');

      const collapseBtn = document.getElementById('btnCollapseGithubAppsTop5');

      const noticeEl = document.getElementById('githubTop5VisibilityNotice');

      const remaining = Math.max(0, filteredApps.length - GITHUB_WEBAPPS_VISIBLE_LIMIT);

      if (moreBtn) {

        moreBtn.style.display = remaining > 0 ? 'inline-flex' : 'none';

        moreBtn.textContent = `📂 Hiện Thêm Kho Ứng Dụng Khác (+${Math.min(10, remaining)} / Đang ẩn ${remaining} Web App) ▾`;

      }

      if (showAllBtn) {

        showAllBtn.style.display = remaining > 10 ? 'inline-flex' : 'none';

        showAllBtn.textContent = `📚 Mở Toàn Bộ (${filteredApps.length} Web App)`;

      }

      if (collapseBtn) {

        collapseBtn.style.display = GITHUB_WEBAPPS_VISIBLE_LIMIT > 6 ? 'inline-flex' : 'none';

      }

      if (noticeEl) {

        noticeEl.textContent = GITHUB_WEBAPPS_VISIBLE_LIMIT <= 6
          ? `Đang hiển thị ${Math.min(GITHUB_WEBAPPS_VISIBLE_LIMIT, filteredApps.length)} ứng dụng; còn ${remaining} ứng dụng trong catalog.`
          : `Đang hiển thị ${Math.min(GITHUB_WEBAPPS_VISIBLE_LIMIT, filteredApps.length)} / ${filteredApps.length} ứng dụng.`;

      }



      if (streamsGrid && streams.length > 0 && !streamsGrid.dataset.renderedOnce) {

        streamsGrid.dataset.renderedOnce = '1';

        const borderColors = ['#06b6d4', '#38bdf8', '#14b8a6', '#a855f7', '#10b981'];

        streamsGrid.innerHTML = streams.map((st, idx) => `

          <div class="revenue-stream-card" style="border-top-color:${borderColors[idx % borderColors.length]};">

            <div>

              <div style="font-weight:800; color:#fff; margin-bottom:4px;">${escapeHtml(st.title_vi)}</div>

              <div style="font-size:10.5px; color:#38bdf8; margin-bottom:4px;">🤖 <strong>Phụ trách:</strong> ${escapeHtml(st.agents_in_charge)}</div>

              <div style="color:var(--text-secondary); font-size:11px;">${escapeHtml(st.how_it_works_vi)}</div>

            </div>

            <div style="margin-top:6px; padding-top:5px; border-top:1px dashed rgba(148,163,184,0.2); font-family:var(--font-mono); font-size:10px; color:#6ee7b7;">

              🔒 Cổng thu: Tự động hiển thị Tài khoản Ngân hàng / Ví Binance khi Khách bấm Mua hoặc Donate

            </div>

          </div>

        `).join('');

      }



      if (appsGrid) {

        const sliceApps = filteredApps.slice(0, GITHUB_WEBAPPS_VISIBLE_LIMIT);

        appsGrid.innerHTML = sliceApps.map((app, idx) => {

          const aadsUnit = ACTIVE_USER_AADS_UNIT_ID || app.aads_unit_id || '';

          const appName = app.app_name_vi || app.name || app.slug || 'Web App';

          const appSummary = app.monetization_summary_vi || app.description || app.category || '';

          const rawPriceUsd = Number(app.sale_price_usd ?? app.price_usd ?? 2.99);

          const appPriceUsd = Number.isFinite(rawPriceUsd) && rawPriceUsd > 0 ? rawPriceUsd : 2.99;

          const appRepo = app.github_repo || app.slug || '';

          const cleanNameVi = sanitizeCommercialAppNameVi(appName, appRepo);

          const cleanSumVi = sanitizeCommercialSummaryVi(appSummary);

          const rankBadge = `<span class="chip cyan" style="font-size:10px;">Web App</span>`;

          return `

            <div class="github-webapp-card">

              <div>

                <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:5px;">

                  ${rankBadge}

                  <span class="chip success" style="font-size:10px;">Giá: $${appPriceUsd.toFixed(2)} USD</span>

                </div>

                <div style="font-weight:800; font-size:13px; color:#fff; margin-bottom:4px;">

                  ${escapeHtml(cleanNameVi)}

                </div>

                <div style="font-size:11px; color:var(--text-secondary); margin-bottom:6px;">

                  ${escapeHtml(cleanSumVi)}

                </div>

                <div style="font-size:10.5px; color:#a5f3fc; margin-bottom:6px;">

                  <div>• <strong>Danh mục:</strong> ${escapeHtml(app.category || 'Web App')}</div>

                  <div>• <strong>Trạng thái:</strong> ${escapeHtml(app.status || 'Có thể mở thử')}</div>

                </div>

                <div style="display:flex; gap:4px; flex-wrap:wrap; margin-bottom:6px;">

                  <span class="chip" style="font-size:9.5px; padding:1px 6px; border-color:rgba(56,189,248,0.45); color:#7dd3fc;">✅ Đã Gắn Đủ QC (A-Ads + Adsterra)</span>

                  <span class="chip" style="font-size:9.5px; padding:1px 6px; border-color:rgba(245,158,11,0.45); color:#fde68a;">🔗 Đã Gắn Link Rút Gọn Kiếm Tiền</span>

                  <span class="chip" style="font-size:9.5px; padding:1px 6px;">🔒 Bàn Giao Code ($${appPriceUsd.toFixed(2)} USD)</span>

                </div>

              </div>

              <div>

                <div style="display:flex; justify-content:space-between; font-family:var(--font-mono); font-size:10px; color:#cbd5e1; margin-bottom:6px; background:rgba(6,10,20,0.65); padding:4px 7px; border-radius:6px; border:1px solid rgba(148,163,184,0.16);">

                  <span>Chưa có số liệu lượt mở hoặc quảng cáo được xác minh.</span>

                  <span>✨ <strong style="color:#34d399;">Bản Thương Mại Pro</strong></span>

                </div>

                <div style="margin-bottom:6px; padding:5px 8px; border-radius:6px; background:rgba(239,68,68,0.14); border:1px dashed rgba(239,68,68,0.5); font-size:10.5px; color:#fecaca; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:4px;">

                  <span style="flex:1; min-width:140px;">Tính năng quảng cáo video đã tắt.</span>

                </div>

                <div style="display:flex; gap:5px; flex-wrap:wrap;">

                  <button class="btn btn-sm btn-primary" style="flex:1;" onclick="openLiveGithubWebAppModal('${escapeHtml(app.slug)}')">

                    ${typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en' ? '🚀 Live Web' : '🚀 Mở Web'}

                  </button>

                  <span class="chip">Liên kết tiếp thị chưa được cấu hình</span>

                  <button class="btn btn-sm btn-cyan" onclick="openVisitorBuyCheckoutModal('${escapeHtml(cleanNameVi)}', ${appPriceUsd}, '${escapeHtml(app.slug)}')">

                    ${typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en' ? `🛒 Buy ($${appPriceUsd.toFixed(2)})` : `🛒 Mua ($${appPriceUsd.toFixed(2)})`}

                  </button>

                </div>

              </div>

            </div>

          `;

        }).join('');

      }

    }



    function buildClientSideMonetizedWebAppHtml(app) {

          const aadsId = ACTIVE_USER_AADS_UNIT_ID || app.aads_unit_id || '';

      const aadsMarkup = aadsId
        ? `<div class="ad-banner"><iframe data-aa="${escapeHtml(aadsId)}" src="//acceptable.a-ads.com/${escapeHtml(aadsId)}/?size=Adaptive" title="Advertisement" style="border:0;width:100%;height:70px;overflow:hidden;"></iframe></div>`
        : '<div class="ad-banner" aria-label="Ad placement not configured">Vị trí quảng cáo chưa được cấu hình.</div>';

      const titleEn = app.app_name_en || sanitizeCommercialAppNameVi(app.app_name_vi || app.slug, app.github_repo);

      const titleVi = sanitizeCommercialAppNameVi(app.app_name_vi || app.slug, app.github_repo);

      const repoName = app.github_repo || 'PRO-STUDIO';

      const priceUsd = Number(app.sale_price_usd || 29).toFixed(2);

      const category = app.category || 'Developer & SaaS Web Tool';

      const mbAcc = getDynamicMbbankAcc();

      const usdtWal = getDynamicUsdtWallet();

      return `<!DOCTYPE html>

<html lang="en">

<head>

  <meta charset="UTF-8" />

  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <title>${escapeHtml(titleEn)} — Commercial White-Label Web App | AUTOProfit AI</title>

  <style>

    * { box-sizing: border-box; }

    body { margin:0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background:#060a14; color:#f8fafc; padding:16px; }

    .container { max-width:1020px; margin:0 auto; display:flex; flex-direction:column; gap:14px; }

    .aads-slot { background:#070b14; border:1px solid rgba(56,189,248,0.32); border-radius:10px; padding:4px; text-align:center; height:86px; display:flex; align-items:center; justify-content:center; overflow:hidden; }

    .app-card { background:linear-gradient(165deg, rgba(15,23,42,0.96), rgba(9,13,24,0.98)); border:1px solid rgba(56,189,248,0.4); border-radius:12px; padding:18px; }

    .badge { display:inline-block; padding:3px 9px; border-radius:999px; font-size:11px; font-weight:700; background:rgba(6,182,212,0.18); color:#67e8f9; border:1px solid rgba(6,182,212,0.4); margin-right:6px; }

    textarea, input { width:100%; background:#090d16; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:10px; font-family:monospace; font-size:12.5px; }

    .btn-primary { background:linear-gradient(135deg,#06b6d4,#6366f1); color:#fff; border:none; padding:9px 15px; border-radius:8px; font-weight:700; cursor:pointer; text-decoration:none; display:inline-block; font-size:12.5px; }

    .btn-sec { background:#1e293b; color:#e2e8f0; border:1px solid #475569; padding:8px 13px; border-radius:8px; font-weight:600; cursor:pointer; text-decoration:none; display:inline-block; font-size:12px; }

  </style>

</head>

<body>

  <div class="container">

    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:10px; width:100%;">

      <div style="background:#070b14; border:1px solid rgba(56,189,248,0.38); border-radius:10px; padding:6px 10px; text-align:center;">

        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">

          <span style="font-size:10px; font-weight:800; color:#38bdf8;">💎 A-ADS PARTNER NETWORK (${aadsId ? 'configured' : 'not configured'})</span>

        </div>

        ${aadsMarkup}

      </div>

      <div style="background:#070b14; border:1px solid rgba(16,185,129,0.38); border-radius:10px; padding:6px 10px; text-align:center;">

        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">

          <span style="font-size:10px; font-weight:800; color:#34d399;">Liên kết tiếp thị chưa được cấu hình</span>

        </div>

        <!-- Adsterra removed: 100% Clean Non-Gambling Policy -->

      </div>

    </div>

    <div id="apInlineAdLinkUnlockerStrip" style="background:linear-gradient(90deg,rgba(239,68,68,0.22),rgba(15,23,42,0.96),rgba(16,185,129,0.18)); border:1.5px solid rgba(239,68,68,0.55); border-radius:10px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; font-size:12.5px;">

      <div>

        <span class="badge" style="background:#64748b;color:#fff;font-weight:800;">YouTube engagement tools are disabled</span>

      </div>

      <div style="display:flex;gap:6px;flex-wrap:wrap;">

        <span class="btn-sec" aria-disabled="true">Video promotions are disabled</span>

      </div>

    </div>

    <div class="app-card">

      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">

        <div>

          <span class="badge">🛡️ Commercial White-Label Pro Edition</span>

          <span class="badge" style="background:rgba(16,185,129,0.18);color:#6ee7b7;">🤖 Category: ${escapeHtml(category)}</span>

          <h1 style="margin:8px 0 4px;font-size:18px;color:#fff;">${escapeHtml(titleEn)}</h1>

          <div style="font-size:12px;color:#94a3b8;">100% Client-Side HTML5/CSS3/JS Web Utility • Zero Monthly Server Cost • Full White-Label Source Code Available (${escapeHtml(titleVi)}).</div>

        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap;">

          <button class="btn-primary" onclick="document.getElementById('inlinePayGate').style.display='block'">🛒 Buy Full White-Label Source Code ($${priceUsd} USD)</button>

          <button class="btn-sec" onclick="document.getElementById('inlinePayGate').style.display='block'">💖 Sponsor / Donate</button>

        </div>

      </div>

      <div id="inlinePayGate" style="display:none; margin-top:12px; padding:12px; border-radius:10px; background:rgba(6,182,212,0.12); border:1px solid rgba(56,189,248,0.45); font-size:12.5px;">

        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">

          <strong style="color:#38bdf8;">💳 INSTANT INTERNATIONAL CHECKOUT &amp; SPONSOR GATE (OPENED ON DEMAND)</strong>

          <button class="btn-sec" style="padding:2px 8px; font-size:11px;" onclick="document.getElementById('inlinePayGate').style.display='none'">✕ Close</button>

        </div>

        <div>• 🌍 <strong>International Buyers (Binance / Web3 USDT BEP20):</strong> <code>${usdtWal}</code> (Full Source Code: <strong>$${priceUsd} USDT</strong> | Sponsor: Min $1.00 USDT)</div>

        <div style="margin-top:4px;">• 🇻🇳 <strong>Vietnam Local Bank Transfer (VietQR):</strong> VPBank <code>${mbAcc}</code></div>

      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px;">

        <div>

          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:5px;">Input Payload / Configuration (JSON or Text):</label>

          <textarea id="inBox" rows="8">{"project": "${escapeHtml(repoName)}", "product": "${escapeHtml(titleEn)}", "license_price_usd": ${priceUsd}}</textarea>

          <div style="margin-top:8px;display:flex;gap:8px;">

            <button class="btn-primary" onclick="runTool()">⚡ Execute &amp; Generate Output</button>

            <button type="button" class="btn-sec" onclick="copyOutputContent()">📋 Copy Output</button>

          </div>

        </div>

        <div>

          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:5px;">Validated &amp; Formatted Output:</label>

          <textarea id="outBox" rows="8" readonly></textarea>

        </div>

      </div>

      <script>

        function runTool(){

          const raw = document.getElementById('inBox').value || '';

          try {

            const obj = JSON.parse(raw);

            obj.processed_at = new Date().toISOString();

            obj.verified_by = "AUTOProfit AI Global Web Factory";

            document.getElementById('outBox').value = JSON.stringify(obj, null, 2);

          } catch(e) {

            document.getElementById('outBox').value = "=== AUTOMATED OUTPUT ===\n" + raw.toUpperCase();

          }

        }

        runTool();

      <\/script>

    </div>

    <div role="note" style="border:1px solid rgba(56,189,248,.35); border-radius:10px; padding:10px 12px; color:#cbd5e1; font-size:11px;">
      Quảng cáo chỉ xuất hiện trong các vị trí đã cấu hình. Không cần nhấp quảng cáo để xem hoặc tải công cụ.
    </div>

    <div style="background:#070b14; border:1px solid rgba(16,185,129,0.4); border-radius:10px; padding:8px;">

      <!-- Adsterra removed: 100% Clean Non-Gambling Policy -->

    </div>

  </div>





    



</body>

</html>`;

    }



    function downloadCompiledGithubWebAppHtml(slug) {
      const safeSlug = String(slug || '').replace(/[^a-z0-9-]/gi, '');
      window.location.assign(`/checkout.html?product=${encodeURIComponent(safeSlug)}`);

    }



    function isConfiguredAadsUnit() { return Boolean(ACTIVE_USER_AADS_UNIT_ID && /^\d{5,12}$/.test(ACTIVE_USER_AADS_UNIT_ID)); }



    function getRealWebAppViewCount(_slug, backendCount) {
      if (backendCount === null || backendCount === undefined || backendCount === '') return null;
      const count = Number(backendCount);
      return Number.isFinite(count) && count >= 0 ? count : null;
    }

    function incrementRealWebAppViewCount(_slug) {
      // Site-wide app views are shown only when a verified backend counter exists.
      return null;
    }

    async function syncConfiguredAadsUnitFromBackend() {
      try {
        const response = await fetch('/api/public/aads-config', { cache: 'no-store' });
        if (!response.ok) return;
        const config = await response.json();
        const unitId = String(config.top_ad_unit_id || '').trim();
        if (/^\d{5,12}$/.test(unitId)) {
          ACTIVE_USER_AADS_UNIT_ID = unitId;
          applyConfiguredAadsUnitToDom(unitId);
        }
      } catch (_) {}
    }



    function applyConfiguredAadsUnitToDom(unitId) {
      const candidate = String(unitId || '').trim();
      const cleanId = /^\d{5,12}$/.test(candidate) ? candidate : '';
      const badge = document.getElementById('aadsUnitIdBadge');
      if (badge) badge.textContent = cleanId ? 'Đã cấu hình vị trí quảng cáo' : 'Chưa cấu hình';
      const slot = document.getElementById('aadsPrimaryBannerSlot');
      if (!slot) return;
      let iframe = slot.querySelector('iframe[data-aa]');
      const status = document.getElementById('aadsPrimaryPlacementStatus');
      if (!cleanId) {
        iframe?.remove();
        if (status) {
          status.textContent = 'Chưa cấu hình vị trí quảng cáo.';
          status.hidden = false;
        }
        return;
      }
      if (!iframe) {
        iframe = document.createElement('iframe');
        iframe.title = 'A-Ads display placement';
        iframe.loading = 'lazy';
        iframe.referrerPolicy = 'strict-origin-when-cross-origin';
        iframe.style.cssText = 'position:relative;z-index:2;border:0;padding:0;width:100%;max-width:468px;height:40px;min-height:40px;max-height:40px;overflow:hidden;display:block;margin:auto;';
        if (status?.parentElement) status.replaceWith(iframe);
        else slot.appendChild(iframe);
      }
      iframe.setAttribute('data-aa', cleanId);
      iframe.src = `https://acceptable.a-ads.com/${cleanId}/?size=Adaptive`;
      if (status) status.hidden = true;
    }



    setTimeout(() => {

      applyConfiguredAadsUnitToDom(ACTIVE_USER_AADS_UNIT_ID);

      syncConfiguredAadsUnitFromBackend();

    }, 400);



    async function openLiveGithubWebAppModal(slug, titleVi, repoName) {

      if (!GITHUB_WEB_FACTORY_CATALOG_READY) await loadAndRenderGithubWebFactory();

      const catalogItem = findGithubWebFactoryProduct(slug);
      const resolvedSlug = catalogItem?.slug || normalizeGithubWebFactorySlug(slug);
      if (!catalogItem) {
        showToast(t('Ứng dụng này chưa có bản triển khai trên máy chủ.', 'This app has no deployed server copy yet.'), true);
        return;
      }
      incrementRealWebAppViewCount(resolvedSlug);

      const modal = document.getElementById('liveGithubWebAppModal');

      const iframe = document.getElementById('modalGithubWebAppIframe');

      const titleEl = document.getElementById('modalGithubWebAppTitle');

      const repoEl = document.getElementById('modalGithubWebAppRepoTag');

      const openBtn = document.getElementById('modalGithubWebAppOpenTabBtn');

      const dlBtn = document.getElementById('modalGithubWebAppDownloadBtn');

      if (!modal || !iframe) return;



      const catalogItems = (GITHUB_WEB_FACTORY_CACHE && GITHUB_WEB_FACTORY_CACHE.items) || [];

      const foundApp = catalogItem || catalogItems.find(x => x.slug === slug) || { slug: resolvedSlug, app_name_vi: titleVi || slug, github_repo: repoName || 'MIT' };

      const resolvedTitle = titleVi || foundApp.app_name_vi || foundApp.name || slug;

      const resolvedRepo = repoName || foundApp.github_repo || 'MIT Open Source';



      if (titleEl) titleEl.textContent = `🌐 ${resolvedTitle}`;

      if (repoEl) repoEl.textContent = `[Bản Thương Mại Độc Quyền • A-Ads (chưa cấu hình)]`;



      if (IS_GITHUB_WEB_FACTORY_BACKEND_LIVE) {

        const liveUrl = `${API_BASE}/api/github-web-factory/apps/${encodeURIComponent(resolvedSlug)}/live`;

        const dlUrl = `/checkout.html?product=${encodeURIComponent(resolvedSlug)}`;

        iframe.removeAttribute('srcdoc');

        iframe.src = liveUrl;

        if (openBtn) openBtn.href = liveUrl;

        if (dlBtn) dlBtn.href = dlUrl;

      } else {

        const htmlDoc = buildClientSideMonetizedWebAppHtml(foundApp);

        iframe.srcdoc = htmlDoc;

        const blob = new Blob([htmlDoc], { type: 'text/html;charset=utf-8' });

        const blobUrl = URL.createObjectURL(blob);

        if (openBtn) openBtn.href = blobUrl;

        if (dlBtn) { dlBtn.href = `/checkout.html?product=${encodeURIComponent(resolvedSlug)}`; dlBtn.removeAttribute('download'); }

      }

      modal.style.display = 'flex';

      renderGithubWebFactorySection(GITHUB_WEB_FACTORY_CACHE);

      setTimeout(() => {

        loadAndRenderGithubWebFactory();

        sendVisitorTrafficHeartbeat(true);

      }, 1200);

    }



    function closeLiveGithubWebAppModal() {

      const modal = document.getElementById('liveGithubWebAppModal');

      const iframe = document.getElementById('modalGithubWebAppIframe');

      if (iframe) iframe.src = 'about:blank';

      if (modal) modal.style.display = 'none';

    }



    async function triggerGithubWebFactoryScanNow() {

      if (!IS_OWNER_ADMIN_VERIFIED) {

        showToast('🔒 Chỉ Quản Trị Viên (Admin) mới có quyền ra lệnh quét GitHub thủ công!', true);

        return;

      }

      
      try {

        const res = await apiFetch('/api/github-web-factory/scan-and-build', {

          method: 'POST',

          body: JSON.stringify({})

        });

        await loadAndRenderGithubWebFactory();

        showToast(res.message || `Đã tạo lại ${res.count || 0} công cụ từ catalog nội bộ.`);

      } catch (err) {

        showToast(`Lỗi tạo lại catalog: ${err.message}`, true);

      }

    }



    async function togglePortalAdminAccessModal() {

      if (!IS_OWNER_ADMIN_VERIFIED && !isSecureAdminOrigin()) {

        showToast(t('Quản trị yêu cầu HTTPS; không nhập khóa trên kết nối HTTP.', 'Admin access requires HTTPS; do not enter the key over HTTP.'), true);

        return;

      }

      if (IS_OWNER_ADMIN_VERIFIED) {

        const confirmExit = window.confirm(t(

          'Bạn đang ở Chế độ Chủ sở hữu (/admin). Bạn có muốn chuyển về Chế độ Khách tham quan công khai (Chỉ quan sát) không?',

          'You are currently in Owner Admin Mode (/admin). Switch back to Public Visitor Observation Mode?'

        ));

        if (confirmExit) {

          sessionStorage.removeItem('autoprofit_owner_admin_key');

          const inp = document.getElementById('adminKeyInput');

          if (inp) inp.value = '';

          updatePortalAccessModeUi();

          renderDynamicWorkforceAndPortalPanels();

          showToast(t('Đã chuyển sang Chế độ Khách tham quan công khai (Chỉ quan sát).', 'Switched to Public Visitor Observation Mode.'));

        }

        return;

      }



      const entered = window.prompt(t(

        '🔐 ĐĂNG NHẬP QUẢN TRỊ VIÊN (/admin):\nNhập Khóa Chủ Sở Hữu (X-Admin-Key) để mở khóa toàn bộ quyền điều hành công ty AI, duyệt nhân sự và đối soát tài chính:',

        '🔐 OWNER ADMIN LOGIN (/admin):\nEnter your Owner Admin Key (X-Admin-Key) to unlock full company administration, workforce approval, and financial reconciliation:'

      ));

      if (!entered || !entered.trim()) return;

      try {

        sessionStorage.setItem('autoprofit_owner_admin_key', entered.trim());

        await apiFetch('/api/admin/auth/verify', {

          method: 'POST'

        });

        const inp = document.getElementById('adminKeyInput');

        if (inp) inp.value = entered.trim();

        updatePortalAccessModeUi();

        renderDynamicWorkforceAndPortalPanels();

        showToast(t('Đã xác thực Khóa Chủ Sở Hữu (/admin) thành công!', 'Owner Admin (/admin) session verified successfully!'));

      } catch (err) {

        sessionStorage.removeItem('autoprofit_owner_admin_key');

        updatePortalAccessModeUi();

        showToast(`${t('Từ chối truy cập Quản trị (/admin)', 'Admin authentication rejected')}: ${err.message}`, true);

      }

    }



    function renderDynamicWorkforceAndPortalPanels() {

      updatePortalAccessModeUi();



      // 1. Dynamic AI Workforce Builder Table

      const emps = STATE.employees && STATE.employees.length

        ? STATE.employees

        : (STATE.dashboard?.employees_registry || []);

      const maxEmp = STATE.employeesMeta?.max_total_employees || STATE.payoutPolicy?.max_total_employees || 15;

      const capChip = document.getElementById('workforceCapacityChip');

      if (capChip) {

        capChip.textContent = t(

          `${emps.length} / ${maxEmp} Nhân viên AI (${emps.filter(e => !e.is_core_initial && !e.is_core_employee).length} Mở rộng)`,

          `${emps.length} / ${maxEmp} AI Employees (${emps.filter(e => !e.is_core_initial && !e.is_core_employee).length} Dynamic)`

        );

      }



      const empBody = document.getElementById('aiEmployeesTableBody');

      if (empBody) {

        empBody.innerHTML = emps.length === 0

          ? `<tr><td colspan="6" class="empty-state">${t('Đang đồng bộ danh sách nhân sự AI...', 'Synchronizing AI workforce registry...')}</td></tr>`

          : emps.map(emp => {

              const isCore = Boolean(emp.is_core_initial || emp.is_core_employee);

              const lifeSt = emp.lifecycle_state || emp.status || 'ACTIVE';

              const animSt = emp.animation_state || 'WORKING_AT_DESK';

              const fullName = CURRENT_LANG === 'en' ? (emp.full_name_en || emp.full_name_vi) : (emp.full_name_vi || emp.title);

              const deptName = CURRENT_LANG === 'en' ? (emp.department_name_en || emp.department_id) : (emp.department_name_vi || emp.department_id);

              const jobTitle = CURRENT_LANG === 'en' ? (emp.job_title_en || emp.job_title_vi) : (emp.job_title_vi || emp.responsibility);

              const skillsArr = Array.isArray(emp.skills) ? emp.skills : [];

              return `

                <tr>

                  <td>

                    <div style="font-weight:700; color:#fff; cursor:pointer;" onclick="selectCharacterIn3DWorld('${escapeHtml(emp.employee_id || emp.role)}', true)">

                      ${escapeHtml(fullName)}

                    </div>

                    <div style="font-family:var(--font-mono); font-size:11px; color:var(--accent-cyan);">

                      ${escapeHtml(emp.employee_id || emp.role)} ${isCore ? `<span class="chip" style="font-size:9.5px; padding:1px 5px;">${t('Cốt lõi', 'Core 9')}</span>` : `<span class="chip purple" style="font-size:9.5px; padding:1px 5px;">${t('Mở rộng', 'Dynamic')}</span>`}

                    </div>

                  </td>

                  <td style="font-size:12px;">

                    <div style="color:#e2e8f0; font-weight:600;">${escapeHtml(deptName)}</div>

                    <div style="font-family:var(--font-mono); font-size:10.5px; color:var(--text-muted);">${t('Bàn 3D:', '3D Desk:')} ${escapeHtml(emp.assigned_workstation_id || 'WS_CORE')}</div>

                  </td>

                  <td style="max-width:250px;">

                    <div style="font-size:12px; color:#fff; margin-bottom:4px;">${escapeHtml(jobTitle)}</div>

                    <div style="display:flex; gap:4px; flex-wrap:wrap;">

                      ${skillsArr.slice(0, 4).map(s => `<span class="chip" style="font-size:9.5px; padding:1px 5px;">${escapeHtml(s)}</span>`).join('')}

                    </div>

                  </td>

                  <td>

                    <span class="chip cyan" style="font-family:var(--font-mono); font-size:10.5px;">${escapeHtml(animSt)}</span>

                  </td>

                  <td>

                    <span class="chip ${lifeSt === 'ACTIVE' ? 'success' : 'warn'}">${escapeHtml(formatStatusLabel(lifeSt))}</span>

                  </td>

                  <td>

                    <div style="display:flex; gap:5px; flex-wrap:wrap;">

                      <button class="btn btn-sm" onclick="selectCharacterIn3DWorld('${escapeHtml(emp.employee_id || emp.role)}', true)">${t('🔍 Hồ sơ 3D', '🔍 3D Profile')}</button>

                      ${lifeSt !== 'ACTIVE' ? `<button class="btn btn-sm btn-success" onclick="approveDynamicEmployeeById('${escapeHtml(emp.employee_id)}')">${t('✓ Duyệt Kích Hoạt', '✓ Approve')}</button>` : ''}

                      ${!isCore ? `<button class="btn btn-sm btn-danger" onclick="retireDynamicEmployeeById('${escapeHtml(emp.employee_id)}')">${t('✕ Cho Nghỉ', '✕ Retire')}</button>` : ''}

                    </div>

                  </td>

                </tr>

              `;

            }).join('');

      }



      // 2. Direct Advertising Inquiries & Sponsors

      const adData = STATE.adInquiries || { items: [], inquiries: [], active_verified_sponsors: [] };

      const activeSponsors = adData.active_verified_sponsors || [];

      const allInquiries = adData.inquiries || adData.items || [];

      const spChip = document.getElementById('activeSponsorsCountChip');

      if (spChip) {

        spChip.textContent = t(`${activeSponsors.length} Nhà tài trợ đã xác minh`, `${activeSponsors.length} Verified Sponsors`);

      }

      const adBox = document.getElementById('adInquiriesListContainer');

      if (adBox) {

        adBox.innerHTML = allInquiries.length === 0

          ? `<div style="color:var(--text-muted);">${t('Chưa có yêu cầu đặt quảng cáo nào. Đối tác có thể gửi yêu cầu trực tiếp ở biểu mẫu trên.', 'No advertising inquiries yet. Sponsors can submit booking requests above.')}</div>`

          : `<div style="display:flex; flex-direction:column; gap:6px; max-height:170px; overflow-y:auto;">

              ${allInquiries.slice(0, 8).map(inq => {

                const isPaid = inq.status === 'PAID_VERIFIED' || inq.payment_verified === true;

                return `

                  <div style="padding:7px 9px; border-radius:var(--radius-sm); background:rgba(15,23,42,0.75); border:1px solid var(--border-subtle); display:flex; justify-content:space-between; align-items:center; gap:8px;">

                    <div>

                      <strong style="color:#fff;">${escapeHtml(inq.sponsor_name)}</strong> — <span style="color:var(--accent-cyan); font-family:var(--font-mono);">$${Number(inq.quoted_price_usd).toFixed(2)}</span>

                      <div style="font-size:11px; color:var(--text-secondary);">${escapeHtml(inq.ad_copy_headline)} (<a href="${escapeHtml(inq.target_url)}" target="_blank" rel="noopener" style="color:#38bdf8;">Link</a>)</div>

                    </div>

                    <div style="display:flex; align-items:center; gap:6px;">

                      <span class="chip ${isPaid ? 'success' : 'warn'}" style="font-size:10px;">${isPaid ? t('ĐÃ XÁC MINH TT', 'VERIFIED_PAID') : t('CHỜ XÁC MINH ($0)', 'UNPAID ($0)')}</span>

                      ${!isPaid ? `<button class="btn btn-sm btn-success" onclick="verifyAdInquiryByAdmin('${escapeHtml(inq.id)}')">${t('✓ Đối soát sao kê (Admin)', '✓ Reconcile statement (Admin)')}</button>` : ''}

                    </div>

                  </div>

                `;

              }).join('')}

            </div>`;

      }



      // 3. Public Supporter Donations

      const donData = STATE.donations || { items: [], verified_donations_usd: null };

      const donItems = donData.items || [];

      const donChip = document.getElementById('verifiedDonationsChip');

      if (donChip) {

        const verifiedDonations = donData.verified_donations_usd;
        const hasVerifiedDonationTotal = verifiedDonations !== null && verifiedDonations !== undefined && Number.isFinite(Number(verifiedDonations));
        donChip.dataset.status = hasVerifiedDonationTotal ? 'observed' : 'no_verified_data';
        donChip.textContent = hasVerifiedDonationTotal
          ? t(`$${Number(verifiedDonations).toFixed(2)} Đã xác minh`, `$${Number(verifiedDonations).toFixed(2)} Verified`)
          : t('— Chưa có dữ liệu xác minh', '— No verified data');

      }

      const donBox = document.getElementById('donationsListContainer');

      if (donBox) {

        donBox.innerHTML = donItems.length === 0

          ? `<div style="color:var(--text-muted);">${t('Chưa có khoản quyên góp nào. Mọi khoản ủng hộ đều ở trạng thái Chờ Xác Minh cho tới khi đối soát.', 'No supporter donations recorded yet. All contributions remain Pending Confirmation until reconciled.')}</div>`

          : `<div style="display:flex; flex-direction:column; gap:6px; max-height:170px; overflow-y:auto;">

              ${donItems.slice(0, 8).map(d => {

                const isVer = d.status === 'PAID_VERIFIED' || d.status === 'VERIFIED_CONFIRMED';
                const amountUsd = Number(d.pledged_amount_usd ?? d.amount_usd ?? (Number(d.amount_vnd || 0) / 25500));

                return `

                  <div style="padding:7px 9px; border-radius:var(--radius-sm); background:rgba(15,23,42,0.75); border:1px solid var(--border-subtle); display:flex; justify-content:space-between; align-items:center; gap:8px;">

                    <div>

                      <strong style="color:#fff;">${escapeHtml(d.supporter_name)}</strong> → <span style="color:#c4b5fd;">${escapeHtml(d.target_employee_id)}</span> (<span style="font-family:var(--font-mono); color:var(--accent-cyan);">$${amountUsd.toFixed(2)}</span>)

                      <div style="font-size:11px; color:var(--text-secondary);">"${escapeHtml(d.message || '')}"</div>

                    </div>

                    <div style="display:flex; align-items:center; gap:6px;">

                      <span class="chip ${isVer ? 'success' : 'warn'}" style="font-size:10px;">${isVer ? t('ĐÃ XÁC MINH', 'VERIFIED') : t('CHỜ ĐỐI SOÁT ($0)', 'PENDING ($0)')}</span>

                      ${!isVer ? `<button class="btn btn-sm btn-success" onclick="verifyDonationByAdmin('${escapeHtml(d.id)}')">${t('✓ Đối soát sao kê (Admin)', '✓ Reconcile statement (Admin)')}</button>` : ''}

                    </div>

                  </div>

                `;

              }).join('')}

            </div>`;

      }



      // 4. 12-Bucket Corporate & Crypto Accounting Ledger

      const twelve = STATE.finance?.twelve_bucket_ledger || STATE.dashboard?.twelve_bucket_ledger || {};

      const streams = STATE.finance?.revenue_streams_breakdown || STATE.dashboard?.revenue_streams_breakdown || {};

      const streamsBox = document.getElementById('revenueStreamsBreakdownBox');

      if (streamsBox) {

        streamsBox.innerHTML = `

          <div style="display:flex; gap:14px; flex-wrap:wrap; padding:8px 12px; border-radius:var(--radius-sm); background:rgba(15,23,42,0.7); border:1px solid var(--border-subtle);">

            <span>• <strong>${t('Dịch vụ & Sản phẩm (Đã xác minh):', 'Verified Services & Products:')}</strong> <code>${escapeHtml(formatFinanceValue(streams.service_and_product_verified_usd, 2))}</code></span>

            <span>• <strong>${t('Quảng cáo trực tiếp (Đã xác minh):', 'Verified Direct Ads:')}</strong> <code>${escapeHtml(formatFinanceValue(streams.direct_advertising_verified_usd, 2))}</code> (${t('Chờ duyệt:', 'Pending:')} ${escapeHtml(formatFinanceValue(streams.direct_advertising_pending_usd, 2))})</span>

            <span>• <strong>${t('Quyên góp ủng hộ (Đã xác minh):', 'Verified Donations:')}</strong> <code>${escapeHtml(formatFinanceValue(streams.donations_verified_usd, 2))}</code> (${t('Chờ duyệt:', 'Pending:')} ${escapeHtml(formatFinanceValue(streams.donations_pending_usd, 2))})</span>

            <span>• <strong>${t('Ước tính mạng QC & Affiliate (Chưa thanh toán):', 'Estimated Ad Network & Affiliate:')}</strong> <code>${escapeHtml(formatFinanceValue(streams.affiliate_and_ad_network_estimated_usd, 2))}</code></span>

          </div>

        `;

      }



      const twelveBody = document.getElementById('twelveBucketTableBody');

      if (twelveBody) {

        const rows12 = [

          [1, t('1. Doanh thu ước tính (Estimated Revenue)', '1. Estimated Revenue'), formatFinanceValue(twelve['1_estimated_revenue_usd'], 2)],

          [2, t('2. Doanh thu chờ xác minh (Pending Revenue)', '2. Pending Revenue'), formatFinanceValue(twelve['2_pending_revenue_usd'], 2)],

          [3, t('3. Tổng doanh thu đã xác minh (Verified Revenue)', '3. Verified Revenue (All Streams)'), formatFinanceValue(twelve['3_verified_revenue_usd'], 2)],

          [4, t('4. Chi phí vận hành thực tế (Operating Costs)', '4. Operating Costs'), formatFinanceValue(twelve['4_operating_costs_usd'], 4)],

          [5, t('5. Tiền hoàn trả khách hàng (Refunds)', '5. Customer Refunds'), formatFinanceValue(twelve['5_refunds_usd'], 2)],

          [6, t('6. Số dư khả dụng sau chi phí (Available Balance)', '6. Available Balance'), formatFinanceValue(twelve['6_available_balance_usd'], 4)],

          [7, t('7. Số dư ví tiền mã hóa On-Chain (Cryptocurrency Balance)', '7. On-Chain Cryptocurrency Balance'), `${escapeHtml(formatFinanceValue(STATE.wallet?.onchain_usdt_balance ?? twelve['7_cryptocurrency_balance_usdt'], 2, 'USDT'))} (BEP20)`],

          [8, t('8. Định giá tài sản số hiện tại (Token Valuation)', '8. Token Valuation (USD)'), formatFinanceValue(STATE.wallet?.onchain_usdt_balance ?? twelve['8_token_valuation_usd'], 2)],

          [9, t('9. Tiền thực nhận đã giải ngân (Realized Proceeds)', '9. Realized Proceeds'), formatFinanceValue(twelve['9_realized_proceeds_usd'], 2)],

          [10, t('10. Khoản rút đang chờ xử lý (Pending Payouts)', '10. Pending Payouts'), formatFinanceValue(twelve['10_pending_payouts_usd'], 2)],

          [11, t('11. Khoản đã rút về ví/ngân hàng Chủ sở hữu (Confirmed Payouts)', '11. Confirmed Owner Payouts'), formatFinanceValue(twelve['11_confirmed_payouts_usd'], 2)],

          [12, t('12. Lợi nhuận ròng toàn công ty (Net Profit)', '12. Corporate Net Profit'), formatFinanceValue(twelve['12_net_profit_usd'], 4)]

        ];

        twelveBody.innerHTML = rows12.map(([idx, label, val]) => `

          <tr>

            <td style="font-family:var(--font-mono); font-weight:700;">${idx < 10 ? '0' + idx : idx}</td>

            <td style="font-weight:600; color:#fff;">${escapeHtml(label)}</td>

            <td style="font-family:var(--font-mono); font-weight:700; color:${idx === 3 || idx === 12 ? 'var(--accent-cyan)' : '#e2e8f0'};">${escapeHtml(val)}</td>

          </tr>

        `).join('');

      }



      // 5. Owner Payout Policy

      if (STATE.payoutPolicy) {

        const pol = STATE.payoutPolicy;

        const minEl = document.getElementById('polMinPayoutUsd');

        const maxEl = document.getElementById('polMaxPayoutUsd');

        const maxEmpEl = document.getElementById('polMaxTotalEmployees');

        const maxDailyEmpEl = document.getElementById('polMaxDailyEmployees');

        if (minEl) minEl.value = pol.minimum_payout_threshold_usd ?? 20;

        if (maxEl) maxEl.value = pol.max_payout_amount_usd ?? 500;

        if (maxEmpEl) maxEmpEl.value = pol.max_total_employees ?? 15;

        if (maxDailyEmpEl) maxDailyEmpEl.value = pol.max_employees_per_day ?? 3;

        const destEl = document.getElementById('payoutDestinationsText');

        if (destEl && Array.isArray(pol.approved_destinations)) {

          destEl.textContent = IS_OWNER_ADMIN_VERIFIED ? pol.approved_destinations.map(d => `${d.provider}: ${d.address || d.account}`).join(' | ') : '🔒 Đã ẩn bảo mật (Chỉ hiển thị cho Quản trị viên hoặc khi Khách bấm Mua hàng / Donate)';

        }

      }

    }



    async function proposeNewDynamicEmployee(autoApprove = false) {

      const role_code = (document.getElementById('empRoleCode')?.value || '').trim();

      const full_name_vi = (document.getElementById('empFullNameVi')?.value || '').trim();

      const department_id = document.getElementById('empDepartmentId')?.value || 'DEPT_PRODUCT_DEV';

      const job_title_vi = (document.getElementById('empJobTitleVi')?.value || '').trim();

      const skillsStr = document.getElementById('empSkillsInput')?.value || '';

      const toolsStr = document.getElementById('empToolsInput')?.value || '';

      const primary_mission_vi = (document.getElementById('empMissionVi')?.value || '').trim();

      const business_justification = (document.getElementById('empJustificationInput')?.value || '').trim();



      if (!role_code || !full_name_vi || !job_title_vi) {

        showToast(t('Vui lòng nhập Mã vai trò, Họ tên nhân viên AI và Chức danh công việc.', 'Please enter Role Code, Employee Name, and Job Title.'), true);

        return;

      }

      if (autoApprove && !promptOrGetAdminKey()) return;



      try {

        const res = await apiFetch('/api/employees/propose', {

          method: 'POST',

          body: JSON.stringify({

            role_code,

            full_name_vi,

            full_name_en: full_name_vi,

            department_id,

            job_title_vi,

            job_title_en: job_title_vi,

            primary_mission_vi: primary_mission_vi || job_title_vi,

            business_justification: business_justification || 'Mở rộng năng lực chuyên môn công ty AI.',

            skills: skillsStr.split(',').map(s => s.trim()).filter(Boolean),

            authorized_tools: toolsStr.split(',').map(s => s.trim()).filter(Boolean),

            auto_approve: Boolean(autoApprove)

          })

        });

        const lifecycleMessage = res.lifecycle_state === 'APPROVED_PENDING_RUNTIME'
          ? t('Hồ sơ đã được chủ sở hữu duyệt. Chưa có worker để thực thi và chưa gán bàn 3D.', 'Owner approved the profile. No execution worker is connected and no 3D desk is assigned.')
          : t('Hồ sơ nhân viên đã được gửi để chờ duyệt. Chưa có worker để thực thi và chưa gán bàn 3D.', 'Employee proposal is waiting for approval. No execution worker is connected and no 3D desk is assigned.');
        showToast(`${t(`Đã lưu hồ sơ '${res.full_name_vi}'.`, `Saved profile '${res.full_name_en}'.`)} ${lifecycleMessage}`);

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Từ chối tạo nhân sự AI', 'Employee creation rejected')}: ${err.message}`, true);

      }

    }



    async function approveDynamicEmployeeById(employeeId) {

      if (!promptOrGetAdminKey()) return;

      try {

        await apiFetch(`/api/employees/${encodeURIComponent(employeeId)}/approve`, {

          method: 'POST',

          body: JSON.stringify({})

        });

        showToast(t(`Đã duyệt hồ sơ ${employeeId}. Nhân viên chưa được gắn vào worker thực thi.`, `Approved ${employeeId}'s profile. No execution worker is connected.`));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi phê duyệt nhân sự', 'Approval error')}: ${err.message}`, true);

      }

    }



    async function retireDynamicEmployeeById(employeeId) {

      if (!promptOrGetAdminKey()) return;

      try {

        await apiFetch(`/api/employees/${encodeURIComponent(employeeId)}/retire`, {

          method: 'POST',

          body: JSON.stringify({ reason: 'Owner Admin retired dynamic employee' })

        });

        showToast(t(`Đã thu hồi nhân sự AI mở rộng ${employeeId}.`, `Retired dynamic AI employee ${employeeId}.`));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi thu hồi nhân sự', 'Retire error')}: ${err.message}`, true);

      }

    }



    async function submitPublicAdvertisingInquiry() {

      const sponsor_name = (document.getElementById('adSponsorName')?.value || '').trim();

      const contact_email = (document.getElementById('adContactEmail')?.value || '').trim();

      const package_code = document.getElementById('adPackageSelect')?.value || 'HOMEPAGE_3D_BILLBOARD';

      const target_url = (document.getElementById('adTargetUrl')?.value || '').trim();

      const ad_copy_headline = (document.getElementById('adHeadlineInput')?.value || '').trim();

      const payment_proof_ref = (document.getElementById('adPaymentRefInput')?.value || '').trim();

      if (!sponsor_name || !contact_email || !target_url || !ad_copy_headline) {

        showToast(t('Vui lòng điền Tên nhà tài trợ, Email, Liên kết đích và Thông điệp quảng cáo.', 'Please fill in Sponsor Name, Email, Target URL, and Ad Headline.'), true);

        return;

      }

      const quoted_price_usd = package_code === 'HOMEPAGE_3D_BILLBOARD' ? 4.99 : 2.99;

      try {

        await apiFetch('/api/public/advertising-inquiries', {

          method: 'POST',

          body: JSON.stringify({

            sponsor_name,

            contact_email,

            package_code,

            target_url,

            ad_copy_headline,

            quoted_price_usd,

            payment_proof_ref

          })

        });

        showToast(t('Đã gửi yêu cầu quảng cáo tài trợ. Chưa tính doanh thu cho tới khi xác minh thanh toán.', 'Advertising request saved. Revenue is not counted until payment is verified.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi gửi yêu cầu quảng cáo', 'Ad inquiry error')}: ${err.message}`, true);

      }

    }



    async function verifyAdInquiryByAdmin(inquiryId) {

      if (!promptOrGetAdminKey()) return;

      const statement_reference = window.prompt(t(
        'Nhập mã giao dịch trên sao kê bạn vừa đối chiếu. Mã khách tự nhập không được xem là bằng chứng.',
        'Enter the transaction reference from the statement you checked. The customer-supplied reference is not proof.'
      ));

      if (statement_reference === null) return;

      try {

        const result = await apiFetch(`/api/admin/advertising-inquiries/${encodeURIComponent(inquiryId)}/verify`, {

          method: 'POST',

          body: JSON.stringify({ statement_reference: statement_reference.trim() })

        });

        showToast(result.already_verified
          ? t('Yêu cầu này đã được đối soát trước đó.', 'This request was already reconciled.')
          : t('Đã ghi nhận doanh thu quảng cáo sau khi bạn xác nhận sao kê. Vị trí quảng cáo vẫn chưa được tự động kích hoạt.', 'Advertising revenue was recorded after your statement confirmation. The placement was not activated automatically.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Không thể xác minh quảng cáo', 'Ad verification failed')}: ${err.message}`, true);

      }

    }



    let VISITOR_IS_VIETNAM_IP = false;

    let VISITOR_COUNTRY_CODE = 'UNKNOWN';

    let VISITOR_GEO_DETECTED = false;

    let VISITOR_NOTEBOOK_CUSTOM_ENTRIES = [];



    function getDynamicMbbankAcc() { return ''; }

    function getDynamicUsdtWallet() { return ''; }



    async function detectVisitorGeoIpAndConfigureDonation() {

      if (VISITOR_GEO_DETECTED) {

        applyDonationGeoUiMode();

        return;

      }

      try {

        const tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || '').toLowerCase();
        const deviceLanguage = (navigator.language || '').toLowerCase();
        const deviceSuggestsVietnam = tz.includes('ho_chi_minh') || tz.includes('saigon') || deviceLanguage.startsWith('vi');
        const detectedCode = deviceSuggestsVietnam ? 'VN' : 'UNKNOWN';

        VISITOR_COUNTRY_CODE = detectedCode;

        VISITOR_IS_VIETNAM_IP = (detectedCode === 'VN');

        VISITOR_GEO_DETECTED = true;

      } catch (_) {

        VISITOR_COUNTRY_CODE = 'UNKNOWN';

        VISITOR_IS_VIETNAM_IP = false;

      }

      applyDonationGeoUiMode();

    }



    function toggleVisitorGeoSimulationMode() {

      VISITOR_IS_VIETNAM_IP = !VISITOR_IS_VIETNAM_IP;

      VISITOR_COUNTRY_CODE = VISITOR_IS_VIETNAM_IP ? 'VN' : 'US';

      VISITOR_GEO_DETECTED = true;

      applyDonationGeoUiMode();

      showToast(

        VISITOR_IS_VIETNAM_IP

          ? '🇻🇳 Đang xem trước giao diện Việt Nam theo thiết lập thiết bị.'

          : '🌍 Đang xem trước giao diện quốc tế/chưa xác minh.'

      );

    }



    let DONATION_GATE_OPENED_BY_VISITOR = false;

    let CURRENT_CHECKOUT_ITEM = { title: '', priceUsd: 29, slug: '' };



    function openVisitorDonationPaymentGate() {

      DONATION_GATE_OPENED_BY_VISITOR = true;

      const promptBox = document.getElementById('donationCleanPromptBox');

      const drawer = document.getElementById('donationPaymentDetailsDrawer');

      if (promptBox) promptBox.style.display = 'none';

      if (drawer) drawer.style.display = 'block';

      applyDonationGeoUiMode();

    }



    function closeVisitorDonationPaymentGate() {

      DONATION_GATE_OPENED_BY_VISITOR = false;

      const promptBox = document.getElementById('donationCleanPromptBox');

      const drawer = document.getElementById('donationPaymentDetailsDrawer');

      const mbAccEl = document.getElementById('donMbAccountCode');

      const usdtWalEl = document.getElementById('donUsdtWalletDisplay');

      const qrImg = document.getElementById('donVietQrImg');

      if (promptBox) promptBox.style.display = 'block';

      if (drawer) drawer.style.display = 'none';

      if (mbAccEl) mbAccEl.textContent = 'Hidden';

      if (usdtWalEl) usdtWalEl.value = 'Hidden until opened';

      if (qrImg) qrImg.src = '';

    }



    async function openVisitorBuyCheckoutModal(itemTitle, priceUsd, itemSlug) {

      if (!GITHUB_WEB_FACTORY_CATALOG_READY) await loadAndRenderGithubWebFactory();

      const catalogItem = findGithubWebFactoryProduct(itemSlug);
      const resolvedSlug = catalogItem?.slug || normalizeGithubWebFactorySlug(itemSlug || 'web-app');
      if (!catalogItem) {
        showToast(t('Sản phẩm này chưa có trong danh mục thanh toán hiện tại.', 'This product is not in the active checkout catalog.'), true);
        return;
      }
      const catalogPrice = Number(catalogItem?.sale_price_usd ?? catalogItem?.price_usd ?? priceUsd);
      if (!Number.isFinite(catalogPrice) || catalogPrice <= 0) {
        showToast(t('Sản phẩm chưa có mức giá hợp lệ.', 'This product has no valid price.'), true);
        return;
      }

      CURRENT_CHECKOUT_ITEM = {

        title: catalogItem?.app_name_vi || catalogItem?.name || itemTitle || 'Gói Mã Nguồn Web Công Cụ AI',

        priceUsd: catalogPrice,

        slug: resolvedSlug

      };

      const modal = document.getElementById('visitorBuyCheckoutModal');

      const titleEl = document.getElementById('checkoutModalItemTitle');

      const priceEl = document.getElementById('checkoutModalPriceLabel');

      const mbAccEl = document.getElementById('checkoutModalMbAcc');

      const vndEl = document.getElementById('checkoutModalVndAmount');

      const memoEl = document.getElementById('checkoutModalMemo');

      const qrEl = document.getElementById('checkoutModalVietQrImg');

      const usdtAmtEl = document.getElementById('checkoutModalUsdtAmount');

      const usdtWalEl = document.getElementById('checkoutModalUsdtWalletInput');



      const usdVal = CURRENT_CHECKOUT_ITEM.priceUsd;

      const vndVal = Math.round(usdVal * 25500);

      const acc = getDynamicMbbankAcc();

      const wal = getDynamicUsdtWallet();

      const memo = ('MUA ' + CURRENT_CHECKOUT_ITEM.slug.replace(/[^a-zA-Z0-9]/g, '').slice(-10)).toUpperCase();



      if (titleEl) titleEl.textContent = '🛒 ' + CURRENT_CHECKOUT_ITEM.title;

      if (priceEl) priceEl.textContent = `$${usdVal.toFixed(2)} USD (~${vndVal.toLocaleString('vi-VN')} VNĐ)`;

      if (mbAccEl) mbAccEl.textContent = acc;

      if (vndEl) vndEl.textContent = `${vndVal.toLocaleString('vi-VN')} VNĐ`;

      if (memoEl) memoEl.textContent = memo;

      if (qrEl) qrEl.src = `https://img.vietqr.io/image/MB-${acc}-compact2.png?accountName=&?amount=${vndVal}&addInfo=${encodeURIComponent(memo)}`;

      if (usdtAmtEl) usdtAmtEl.textContent = `$${usdVal.toFixed(2)} USDT (BEP20)`;

      if (usdtWalEl) usdtWalEl.value = wal;



      switchCheckoutPaymentTab(VISITOR_IS_VIETNAM_IP ? 'VN' : 'CRYPTO');

      const orderStatus = document.getElementById('checkoutOrderStatus');
      if (orderStatus) { orderStatus.style.display = 'none'; orderStatus.textContent = ''; }

      if (modal) modal.style.display = 'flex';

    }



    function closeVisitorBuyCheckoutModal() {

      const modal = document.getElementById('visitorBuyCheckoutModal');

      if (modal) modal.style.display = 'none';

    }



    function switchCheckoutPaymentTab(tabMode) {

      const vnBox = document.getElementById('checkoutModalVnBankBox');

      const cryptoBox = document.getElementById('checkoutModalCryptoBox');

      const btnVn = document.getElementById('btnCheckoutTabVn');

      const btnCrypto = document.getElementById('btnCheckoutTabCrypto');

      if (tabMode === 'VN') {

        if (vnBox) vnBox.style.display = 'block';

        if (cryptoBox) cryptoBox.style.display = 'none';

        if (btnVn) btnVn.className = 'btn btn-sm btn-cyan';

        if (btnCrypto) btnCrypto.className = 'btn btn-sm';

      } else {

        if (vnBox) vnBox.style.display = 'none';

        if (cryptoBox) cryptoBox.style.display = 'block';

        if (btnVn) btnVn.className = 'btn btn-sm';

        if (btnCrypto) btnCrypto.className = 'btn btn-sm btn-cyan';

      }

    }



    async function submitVisitorQuickCheckoutOrder() {
      const slug = String(CURRENT_CHECKOUT_ITEM?.slug || '').replace(/[^a-z0-9-]/gi, '');
      window.location.assign(`/checkout.html?product=${encodeURIComponent(slug)}`);
    }


    async function checkPublicPaymentReportStatus(reportId) {
      const email = (document.getElementById('checkoutBuyerEmail')?.value || '').trim();
      const status = document.getElementById('checkoutOrderStatus');
      if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        if (status) { status.textContent = t('Nhập email đã dùng khi gửi yêu cầu.', 'Enter the email used for the request.'); status.style.display = 'block'; }
        return;
      }
      try {
        const result = await apiFetch('/api/public/payment-reports/status', {
          method: 'POST', body: JSON.stringify({ report_id: reportId, customer_email: email })
        });
        if (!status) return;
        const isPaid = result.status === 'PAID_VERIFIED';
        status.innerHTML = escapeHtml(isPaid
          ? t('Thanh toán đã được xác minh.', 'Payment has been verified.')
          : t(`Trạng thái hiện tại: ${result.status}. Chưa thể bàn giao.`, `Current status: ${result.status}. Delivery is not available yet.`));
        if (isPaid && result.download_url) {
          status.insertAdjacentHTML('beforeend', ` <a class="btn btn-sm btn-success" href="${escapeHtml(result.download_url)}" target="_blank" rel="noopener">${escapeHtml(t('Mở sản phẩm', 'Open product'))}</a>`);
        }
        status.style.color = isPaid ? '#86efac' : '#fde68a';
        status.style.display = 'block';
      } catch (err) {
        if (status) { status.textContent = `${t('Không kiểm tra được trạng thái:', 'Status check failed:')} ${err.message}`; status.style.color = '#fca5a5'; status.style.display = 'block'; }
      }
    }


    function applyDonationGeoUiMode() {

      const vnPanel = document.getElementById('donationVietnamMbbankPanel');

      const usdPanel = document.getElementById('donationInternationalUsdPanel');

      const toggleBtn = document.getElementById('btnToggleVisitorGeoPreview');

      const mbAccEl = document.getElementById('donMbAccountCode');

      const usdtWalEl = document.getElementById('donUsdtWalletDisplay');

      const ruleDesc = document.getElementById('donationGeoRuleDesc');



      if (!DONATION_GATE_OPENED_BY_VISITOR) {

        if (mbAccEl) mbAccEl.textContent = 'Hidden';

        if (usdtWalEl) usdtWalEl.value = 'Hidden until opened';

        return;

      }



      if (VISITOR_IS_VIETNAM_IP) {

        if (vnPanel) vnPanel.style.display = 'block';

        if (usdPanel) usdPanel.style.display = 'none';

        if (mbAccEl) mbAccEl.textContent = getDynamicMbbankAcc();

        if (toggleBtn) toggleBtn.textContent = `🇻🇳 Thiết lập thiết bị: Việt Nam (${VISITOR_COUNTRY_CODE})`;

        if (ruleDesc) ruleDesc.textContent = 'Cổng ủng hộ dành cho khách tại Việt Nam (Chuyển khoản VPBank từ 2.000đ – 100.000đ).';

        updateVietnamDonationQrPreview();

      } else {

        if (vnPanel) vnPanel.style.display = 'none';

        if (usdPanel) usdPanel.style.display = 'block';

        if (mbAccEl) mbAccEl.textContent = 'HIDDEN_FOR_UNVERIFIED_REGION';

        if (usdtWalEl) usdtWalEl.value = getDynamicUsdtWallet();

        if (toggleBtn) toggleBtn.textContent = `🌍 Khu vực chưa xác minh (${VISITOR_COUNTRY_CODE})`;

        if (ruleDesc) ruleDesc.textContent = 'International Supporter Portal: Supporting via Binance / USDT BEP20 (Min $1.00 USD).';

      }

    }



    function selectVietnamDonationVnd(vndAmount) {

      const inp = document.getElementById('donAmountVnd');

      if (inp) inp.value = vndAmount;

      document.querySelectorAll('#vndDonatePresetsRow .donate-preset-btn').forEach(btn => {

        btn.classList.toggle('active', Number(btn.getAttribute('data-vnd')) === Number(vndAmount));

      });

      updateVietnamDonationQrPreview();

    }



    function updateVietnamDonationQrPreview() {

      if (!VISITOR_IS_VIETNAM_IP) return;

      const vnd = Math.max(2000, Number(document.getElementById('donAmountVnd')?.value || 10000));

      const qrImg = document.getElementById('donVietQrImg');

      const hint = document.getElementById('donVietQrHintText');

      const acc = getDynamicMbbankAcc();

      if (qrImg) {

        qrImg.src = `https://img.vietqr.io/image/MB-${acc}-compact2.png?accountName=&?amount=${vnd}&addInfo=${encodeURIComponent('UNG HO AUTOPROFIT AI')}`;

      }

      if (hint) {

        hint.innerHTML = `Mức đang chọn: <strong style="color:#38bdf8;">${vnd.toLocaleString('vi-VN')} VNĐ</strong> vào VPBank <code>${acc}</code> (Tối thiểu 2.000đ).`;

      }

    }



    function selectInternationalDonationUsd(usdAmount) {

      const inp = document.getElementById('donAmountUsd');

      if (inp) inp.value = usdAmount;

      document.querySelectorAll('#usdDonatePresetsRow .donate-preset-btn').forEach(btn => {

        btn.classList.toggle('active', Number(btn.getAttribute('data-usd')) === Number(usdAmount));

      });

    }



    async function submitPublicDonation() {

      const supporter_name = (document.getElementById('donSupporterName')?.value || '').trim() || 'Anonymous Supporter';

      const target_employee_id = document.getElementById('donTargetEmployee')?.value || 'PROJECT_WIDE';

      const message = (document.getElementById('donMessageInput')?.value || '').trim();

      const tx_hash_or_ref = (document.getElementById('donTxRefInput')?.value || '').trim();



      let payload = {

        supporter_name,

        target_employee_id,

        message,

        tx_hash_or_ref

      };



      if (VISITOR_IS_VIETNAM_IP) {

        const amount_vnd = Number(document.getElementById('donAmountVnd')?.value || 0);

        if (amount_vnd < 2000) {

          showToast('Số tiền ủng hộ qua VPBank tối thiểu là 2.000 VNĐ (Các mốc: 2.000 - 5.000 - 10.000 - 20.000 - 50.000 - 100.000 VNĐ).', true);

          return;

        }

        payload.currency = 'VND';

        payload.amount_vnd = amount_vnd;

        payload.payment_method = 'VIETQR_VPBANK';

      } else {

        const amount_usd = Number(document.getElementById('donAmountUsd')?.value || 0);

        if (amount_usd < 1.0) {

          showToast('Minimum international donation is $1.00 USD (Min $1).', true);

          return;

        }

        payload.currency = 'USD';

        payload.amount_usd = amount_usd;

        payload.pledged_amount_usd = amount_usd;

        payload.payment_method = 'BSC_USDT_BEP20';

      }



      try {

        await apiFetch('/api/public/donations', {

          method: 'POST',

          body: JSON.stringify(payload)

        });

        showToast(

          VISITOR_IS_VIETNAM_IP

            ? `Cảm ơn bạn đã ủng hộ ${Number(payload.amount_vnd).toLocaleString('vi-VN')} VNĐ qua VPBank! Hệ thống đã ghi nhận chờ đối soát.`

            : `Thank you for supporting $${Number(payload.amount_usd).toFixed(2)} USD! Recorded in Pending Verification.`

        );

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi gửi thông báo quyên góp', 'Donation submission error')}: ${err.message}`, true);

      }

    }



    async function triggerAutoApproveAllLeadsNow() {

      try {

        const res = await apiFetch('/api/leads/auto-approve-all', { method: 'POST' });

        showToast(`Đã chuẩn bị ${res.total_leads || 0} đề xuất để chủ sở hữu rà soát. Chưa gửi email cho khách.`);

        await refreshAllData(false);

      } catch (err) {

        showToast(`Lỗi tự động duyệt Lead: ${err.message}`, true);

      }

    }



    

    // =========================================================================

    // Event-only activity display; legacy synthetic dialogue and heartbeat loops are retired.

    // =========================================================================

    let CONTINUOUS_CHAT_TIMER = null;
    let TRAFFIC_HEARTBEAT_TIMER = null;

    async function runAutonomousUnlimitedGithubHarvestStep() {
      const ticker = document.getElementById('githubHarvesterLiveTicker');
      const message = 'Chưa kết nối quy trình tải repo, xác minh giấy phép và đóng gói. Không có ứng dụng mới được tạo.';
      if (ticker) ticker.textContent = message;
      return { status: 'discovery_not_connected', items: [], message };
    }


    function triggerNextContinuousAiConversationTurn() {
      // Office speech is rendered only from the authenticated backend event feed.
      return;
    }

    function startContinuous3DAiOfficeDialogueLoop() {
      if (CONTINUOUS_CHAT_TIMER) clearInterval(CONTINUOUS_CHAT_TIMER);
      CONTINUOUS_CHAT_TIMER = null;
    }

    function getLocalPersistentTrafficCounter() {
      return {
        date: new Date().toISOString().slice(0, 10),
        online_now: null,
        today: null,
        week_base: null,
        month_base: null
      };
    }

    function saveLocalPersistentTrafficCounter(state) {

      try {

        localStorage.setItem('autoprofit_real_traffic_v6', JSON.stringify(state));

      } catch (_) {}

    }



    async function sendVisitorTrafficHeartbeat(isNewPageview = false) {
      // First-party pageviews and heartbeats are recorded by site-telemetry.js.
      // Do not fall back to browser counters or the legacy multi-site endpoint.
      return null;
    }



    async function renderLiveTrafficAndAadsStats() {
      const isEn = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en');
      const loc = isEn ? 'en-US' : 'vi-VN';
      const unavailable = isEn ? 'No verified data' : 'Chưa có dữ liệu';
      const format = value => value == null ? unavailable : Number(value).toLocaleString(loc);
      const text = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.textContent = String(value);
      };
      const display = item => item && item.status === 'insufficient_coverage'
        ? (isEn ? 'Insufficient coverage' : 'Chưa đủ dữ liệu')
        : format(item ? item.value : null);
      const base = (typeof API_BASE === 'string' && API_BASE) ? API_BASE.replace(/\/$/, '') : window.location.origin;
      try {
        const response = await fetch(base + '/api/dashboard/summary?window=today', { cache: 'no-store' });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const snapshot = await response.json();
        if (snapshot.status !== 'ok') throw new Error('Analytics unavailable');
        const metrics = snapshot.metrics || {};
        text('statVisitorsOnlineNow', format(metrics.online_sessions && metrics.online_sessions.value));
        text('statVisitorsOnlineSub', isEn ? 'Browser sessions active in last 90 seconds' : 'Phiên trình duyệt có heartbeat trong 90 giây');
        text('statVisitorsToday', display(metrics.sessions_today));
        text('statPageviewsToday', isEn ? display(metrics.pageviews_today) + ' pageviews today' : display(metrics.pageviews_today) + ' lượt xem trang hôm nay');
        text('statVisitorsWeek', display(metrics.sessions_7d));
        text('statPageviewsWeek', isEn ? display(metrics.pageviews_7d) + ' pageviews in 7 days' : display(metrics.pageviews_7d) + ' lượt xem trang 7 ngày');
        text('statVisitorsMonth', display(metrics.sessions_30d));
        text('statPageviewsMonth', isEn ? display(metrics.pageviews_30d) + ' pageviews in 30 days' : display(metrics.pageviews_30d) + ' lượt xem trang 30 ngày');
        text('trafficLastSyncBadge', isEn
          ? 'First-party browser telemetry · ' + new Date(snapshot.updated_at).toLocaleTimeString(loc)
          : 'Telemetry trình duyệt · ' + new Date(snapshot.updated_at).toLocaleTimeString(loc));
        window.LAST_TRAFFIC_DATA_CACHE = snapshot;
      } catch (_) {
        text('statVisitorsOnlineNow', unavailable);
        text('statVisitorsOnlineSub', isEn ? 'Telemetry disconnected' : 'Mất kết nối telemetry');
        text('statVisitorsToday', unavailable);
        text('statPageviewsToday', unavailable);
        text('statVisitorsWeek', unavailable);
        text('statPageviewsWeek', unavailable);
        text('statVisitorsMonth', unavailable);
        text('statPageviewsMonth', unavailable);
        text('trafficLastSyncBadge', isEn ? 'Telemetry disconnected' : 'Mất kết nối telemetry');
      }
    }
    async function promptUpdateAadsUnitId() {
      if (!IS_OWNER_ADMIN_VERIFIED) { showToast('Chỉ quản trị viên mới được phép thay đổi mã quảng cáo.', true); return; }
      const nextId = window.prompt('Nhập Ad Unit ID A-Ads (5-12 chữ số):', ACTIVE_USER_AADS_UNIT_ID || '');
      if (!nextId || !/^\d{5,12}$/.test(nextId.trim())) { showToast('Mã Ad Unit ID không hợp lệ.', true); return; }
      try {
        const result = await apiFetch('/api/public/aads-config', {
          method: 'POST', body: JSON.stringify({ aads_unit_id: nextId.trim() })
        });
        if (result?.status !== 'saved') throw new Error('Configuration was not saved');
        ACTIVE_USER_AADS_UNIT_ID = nextId.trim();
        applyConfiguredAadsUnitToDom(ACTIVE_USER_AADS_UNIT_ID);
        renderLiveTrafficAndAadsStats(result);
        showToast('Đã lưu mã quảng cáo trên máy chủ. Chỉ dữ liệu impression đã xác minh mới được báo cáo.');
      } catch (_) { showToast('Không lưu được cấu hình quảng cáo; kiểm tra quyền quản trị và HTTPS.', true); }
    }



    function startVisitorTrafficHeartbeatLoop() {

      if (TRAFFIC_HEARTBEAT_TIMER) clearInterval(TRAFFIC_HEARTBEAT_TIMER);
      TRAFFIC_HEARTBEAT_TIMER = null;

    }



    function renderHumanStyleAiNotebook() {

      const streamEl = document.getElementById('humanNotebookEntriesStream');

      if (!streamEl) return;

      const filterRole = document.getElementById('notebookFilterAgentSelect')?.value || 'ALL';



      // No prewritten agent diary is presented as production activity.
      const filteredPersonas = [];

      const customHtml = VISITOR_NOTEBOOK_CUSTOM_ENTRIES

        .filter(e => filterRole === 'ALL' || e.role === filterRole)

        .map(e => `

          <div class="notebook-diary-entry visitor-reply">

            <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">

              <strong style="color:#34d399; font-size:12px;">💬 ${escapeHtml(e.humanName)} (Trả lời ${escapeHtml(e.visitorName)})</strong>

              <span style="font-family:var(--font-mono); font-size:10px; color:var(--text-muted);">${escapeHtml(e.timeStr)}</span>

            </div>

            <div style="font-size:11px; color:#a7f3d0; margin-top:3px;">

              <strong>Khách hỏi:</strong> "${escapeHtml(e.question)}"

            </div>

            <div class="notebook-thought-box">

              💭 <strong>Suy nghĩ:</strong> "${escapeHtml(e.thought)}"

            </div>

            <div class="notebook-action-box">

              ✍️ <strong>Phản hồi trực tiếp:</strong> ${escapeHtml(e.reply)}

            </div>

          </div>

        `).join('');



      const cardsHtml = filteredPersonas.map(p => `

        <div class="notebook-diary-entry" style="border-left-color:${p.badgeColor};">

          <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap;">

            <strong style="color:#fff; font-size:12px;">📒 ${escapeHtml(p.humanName)}</strong>

            <div style="display:flex; align-items:center; gap:6px;">

              <span style="font-family:var(--font-mono); font-size:10px; color:var(--text-muted);">${escapeHtml(p.timeLabel)}</span>

              <button class="btn btn-sm" style="padding:1px 6px; font-size:10px;" onclick="selectCharacterIn3DWorld('${p.role}', false)">📍 Xem 3D</button>

            </div>

          </div>

          <div class="notebook-thought-box">

            💭 <strong>Đang suy nghĩ:</strong> "${escapeHtml(p.thought)}"

          </div>

          <div class="notebook-action-box">

            🛠️ <strong>Việc đang làm:</strong> ${escapeHtml(p.action)}

          </div>

        </div>

      `).join('');



      const emptyHtml = customHtml || cardsHtml ? '' : `<div class="notebook-diary-entry">${escapeHtml(t('Chưa có hoạt động AI được xác minh từ backend.', 'No verified AI activity has been received from the backend.'))}</div>`;
      streamEl.innerHTML = customHtml + cardsHtml + emptyHtml;

    }



    async function sendQuickVisitorNotebookQuestion(questionText) {

      const inp = document.getElementById('visitorNotebookInput');

      if (inp) inp.value = questionText;

      await submitVisitorNotebookInteraction();

    }



    async function submitVisitorNotebookInteraction() {

      const inp = document.getElementById('visitorNotebookInput');

      const roleSel = document.getElementById('visitorTargetAgentSelect');

      const question = (inp?.value || '').trim();

      const target_agent_role = roleSel?.value || 'SALES_AGENT';

      if (!question) {

        showToast('Vui lòng nhập câu hỏi hoặc bấm vào một gợi ý bên trên để trò chuyện với nhân viên AI!', true);

        return;

      }

      if (inp) inp.value = '';

      try {

        const res = await apiFetch('/api/public/notebook/interact', {

          method: 'POST',

          body: JSON.stringify({

            visitor_name: 'Khách ghé thăm Web',

            target_agent_role,

            question

          })

        });

        VISITOR_NOTEBOOK_CUSTOM_ENTRIES.unshift({

          role: res.agent_role || target_agent_role,

          humanName: res.agent_human_name || target_agent_role,

          visitorName: res.visitor_name || 'Khách ghé thăm',

          question,

          thought: res.inner_thought || '',

          reply: res.reply_message || '',

          timeStr: new Date().toLocaleTimeString('vi-VN')

        });

        renderHumanStyleAiNotebook();

        selectCharacterIn3DWorld(target_agent_role, false);

        activateSpeechBubbleIn3D({

          message_id: res.message_id || ('vis_' + Date.now()),

          sender_agent_id: target_agent_role,

          receiver_agent_id: 'CUSTOMER_SUPPORT_AGENT',

          message_type: 'VISITOR_NOTEBOOK_INTERACTION',

          message_content: res.reply_message,

          created_at: new Date().toISOString()

        });

        showToast(`💬 ${res.agent_human_name} vừa trả lời bạn trên Sổ tay & trong Văn phòng 3D!`);

      } catch (err) {

        showToast(`Lỗi gửi tương tác: ${err.message}`, true);

      }

    }



    async function verifyDonationByAdmin(donationId) {

      if (!promptOrGetAdminKey()) return;

      const statement_reference = window.prompt(t(
        'Nhập mã giao dịch trên sao kê bạn vừa đối chiếu. Mã khách tự nhập không được xem là bằng chứng.',
        'Enter the transaction reference from the statement you checked. The customer-supplied reference is not proof.'
      ));

      if (statement_reference === null) return;

      try {

        const result = await apiFetch(`/api/admin/donations/${encodeURIComponent(donationId)}/verify`, {

          method: 'POST',

          body: JSON.stringify({ statement_reference: statement_reference.trim() })

        });

        showToast(result.revenue_recorded
          ? t('Đã ghi khoản ủng hộ vào doanh thu sau khi xác nhận sao kê.', 'Donation recorded as revenue after statement confirmation.')
          : t('Khoản ủng hộ này đã được đối soát trước đó.', 'This donation was already reconciled.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Không thể xác minh quyên góp', 'Donation verification failed')}: ${err.message}`, true);

      }

    }



    async function saveOwnerPayoutPolicy() {

      if (!promptOrGetAdminKey()) return;

      const minimum_payout_threshold_usd = Number(document.getElementById('polMinPayoutUsd')?.value || 20);

      const max_payout_amount_usd = Number(document.getElementById('polMaxPayoutUsd')?.value || 500);

      const max_total_employees = Number(document.getElementById('polMaxTotalEmployees')?.value || 15);

      const max_employees_per_day = Number(document.getElementById('polMaxDailyEmployees')?.value || 3);

      try {

        await apiFetch('/api/payout-policies', {

          method: 'PUT',

          body: JSON.stringify({

            minimum_payout_threshold_usd,

            max_payout_amount_usd,

            max_total_employees,

            max_employees_per_day,

            require_owner_confirmation: true

          })

        });

        showToast(t('Đã lưu Chính sách Rút tiền & Hạn mức Nhân sự AI thành công!', 'Saved Owner Payout & Workforce Policy successfully!'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi lưu chính sách', 'Policy update error')}: ${err.message}`, true);

      }

    }



    // =========================================================================

    // INTERACTIVE ACTIONS & API HANDLERS

    // =========================================================================

    async function runOrchestratorCycle() {

      try {

        showToast(t('Đang thực thi chu kỳ điều phối 13 bước...', 'Executing 13-step Orchestrator pipeline cycle...'));

        const res = await apiFetch('/api/agents/run-cycle', { method: 'POST' }, 25000);

        const box = document.getElementById('orchestratorCycleOutput');

        if (box) {

          box.innerHTML = `<pre class="code-block">${escapeHtml(JSON.stringify(res, null, 2))}</pre>`;

        }

        showToast(trContent(res.honest_status_summary || res.reason || t('Đã chạy xong chu kỳ điều phối AI.', 'Completed AI Orchestrator cycle.')));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi chạy chu kỳ', 'Cycle execution error')}: ${err.message}`, true);

      }

    }



    async function runLiveInternetScan() {

      const btn = document.getElementById('btnLiveScan');

      if (btn) btn.disabled = true;

      try {

        showToast(t('Đang lấy bài Show HN từ Hacker News...', 'Fetching Show HN posts from Hacker News...'));

        const res = await apiFetch('/api/internet/live-scan', { method: 'POST' }, 25000);

        const box = document.getElementById('liveScanResultBox');

        if (box) {

          box.textContent = res.message || (res.status === 'source_unavailable'
            ? t('Nguồn Hacker News không phản hồi; chưa lưu cơ hội mới.', 'Hacker News is unavailable; no opportunities were saved.')
            : t(`Đã lưu ${res.items?.length || 0} bài Show HN để rà soát. Không crawl website và không tạo lead tự động.`, `${res.items?.length || 0} Show HN posts saved for review. No websites were crawled and no leads were created.`));

        }

        showToast(res.status === 'source_unavailable'
          ? t('Không kết nối được nguồn Hacker News.', 'Could not connect to Hacker News.')
          : t(`Đã lưu ${res.items?.length || 0} cơ hội công khai để rà soát.`, `Saved ${res.items?.length || 0} public opportunities for review.`), res.status === 'source_unavailable');

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi quét Internet', 'Live scan error')}: ${err.message}`, true);

      } finally {

        if (btn) btn.disabled = false;

      }

    }



    async function analyzeFreelanceJob() {

      const title = document.getElementById('fjTitle').value.trim();

      const source_url = document.getElementById('fjUrl').value.trim();

      const budgetStr = document.getElementById('fjBudget').value.trim();

      const deadline = document.getElementById('fjDeadline').value.trim();

      const requirements = document.getElementById('fjReq').value.trim();

      if (!title || !requirements) {

        showToast(t('Vui lòng nhập Tên dự án và Yêu cầu thực tế của khách hàng.', 'Please enter the Job Title and Client Requirements.'), true);

        return;

      }

      try {

        const res = await apiFetch('/api/opportunities/analyze-freelance-job', {

          method: 'POST',

          body: JSON.stringify({

            title,

            platform: 'Upwork / Fiverr / Contra (Assisted)',

            source_url,

            requirements,

            published_budget_usd: budgetStr ? Number(budgetStr) : null,

            deadline: deadline || null

          })

        });

        document.getElementById('fjResultBox').innerHTML = `

          <div style="padding:10px; border:1px solid var(--border-accent); border-radius:var(--radius-sm); background:rgba(139,92,246,0.1); font-size:12px;">

            <div><strong>${t('Điểm phù hợp:', 'Fit Score:')}</strong> ${res.fit_score}/100 | <strong>${t('Kết luận:', 'Verdict:')}</strong> ${escapeHtml(trContent(res.selection_or_rejection_reason))}</div>

            <div style="margin-top:6px;"><strong>${t('Đề xuất soạn sẵn (Sao chép để gửi thủ công):', 'Drafted Proposal (Copy to send manually):')}</strong></div>

            <pre class="code-block" style="margin-top:4px;">${escapeHtml(trContent(res.drafted_proposal))}</pre>

          </div>

        `;

        showToast(t('Đã phân tích cơ hội và lưu vào bảng Cơ Hội Kinh Doanh.', 'Analyzed opportunity and saved to Opportunities table.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi phân tích', 'Analysis error')}: ${err.message}`, true);

      }

    }



    async function approveLeadProposal(leadId) {

      if (!promptOrGetAdminKey()) return;

      try {

        await apiFetch(`/api/leads/${encodeURIComponent(leadId)}/approve-proposal`, {

          method: 'POST',

          body: JSON.stringify({})

        });

        showToast(t('Đã phê duyệt đề xuất cá nhân hóa cho khách hàng này.', 'Approved personalized proposal for this lead.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Không thể phê duyệt', 'Approval failed')}: ${err.message}`, true);

      }

    }



    async function copyLeadProposal(leadId) {

      const lead = STATE.leads.find(x => x.id === leadId);

      if (!lead) return;

      const copied = await copyTextToClipboard(lead.custom_proposal || '');
      showToast(copied ? t('Đã sao chép nội dung đề xuất để bạn gửi thủ công.', 'Proposal copied for manual sending.') : t('Không thể sao chép. Hãy chọn và sao chép nội dung thủ công.', 'Clipboard unavailable. Copy the proposal manually.'), !copied);

    }



    function prefillOrderForLead(leadId) {

      switchView('orders');

      const sel = document.getElementById('orderCustomerSelect');

      if (sel) sel.value = leadId;

      showToast(t('Đã chọn khách hàng tiềm năng trong biểu mẫu Tạo Đơn Hàng.', 'Selected lead in Create Order form.'));

    }



    function populateProductEditForm() {

      const selId = document.getElementById('productEditSelect').value;

      const prod = STATE.products.find(p => p.id === selId) || STATE.products[0];

      if (!prod) return;

      document.getElementById('editProdName').value = prod.name || '';

      document.getElementById('editProdPrice').value = prod.price_usd ?? 29;

      document.getElementById('editProdProblem').value = prod.problem_solved || '';

    }



    async function saveProductPriceUpdate() {

      const selId = document.getElementById('productEditSelect').value || (STATE.products[0] && STATE.products[0].id);

      if (!selId) return;

      const name = document.getElementById('editProdName').value.trim();

      const price_usd = Number(document.getElementById('editProdPrice').value);

      const problem_solved = document.getElementById('editProdProblem').value.trim();

      try {

        await apiFetch(`/api/products/${encodeURIComponent(selId)}`, {

          method: 'PUT',

          body: JSON.stringify({ name, price_usd, problem_solved })

        });

        showToast(t(`Đã cập nhật mức giá dịch vụ thành $${price_usd.toFixed(2)} USD.`, `Updated service price to $${price_usd.toFixed(2)} USD.`));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi cập nhật giá', 'Price update error')}: ${err.message}`, true);

      }

    }



    function downloadPrimaryToolkit() {

      const prod = STATE.products[0];

      if (!prod) {

        showToast(t('Chưa có sản phẩm để tải.', 'No product available to download.'), true);

        return;

      }

      window.location.assign(`/checkout.html?product=${encodeURIComponent(prod.id)}`);

    }



    async function runInteractiveAuditDemo() {

      const business_name = document.getElementById('demoBusinessName').value.trim() || 'Client Website';

      const target_url = document.getElementById('demoTargetUrl').value.trim() || null;

      const html_content = document.getElementById('demoHtmlInput').value;

      const save_as_lead = document.getElementById('demoSaveLead').checked;



      try {

        showToast(t('Đang chạy công cụ kiểm toán kỹ thuật Trang web & Sửa lỗi SEO...', 'Running Live Website Technical Audit & SEO Fix Engine...'));

        const res = await apiFetch('/api/products/live-audit-demo', {

          method: 'POST',

          body: JSON.stringify({ business_name, target_url, html_content, save_as_lead })

        }, 18000);



        const rep = res.audit_report || {};

        document.getElementById('demoAuditOutput').innerHTML = `

          <div style="padding:12px; border:1px solid var(--border-cyan); border-radius:var(--radius-md); background:rgba(6,182,212,0.08); font-size:12.5px;">

            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">

              <strong>${t('Điểm Sức Khỏe Kỹ Thuật & SEO:', 'Technical & SEO Health Score:')} ${rep.overall_health_score}/100</strong>

              <span class="chip cyan">${t('Giá dịch vụ:', 'Service Price:')} $${Number(res.price_usd).toFixed(2)} USD</span>

            </div>

            <div style="margin-bottom:8px;">

              <strong>${t('Lỗi phát hiện có bằng chứng', 'Evidence-Backed Issues Found')} (${(rep.identified_issues || []).length}):</strong>

              <ul style="padding-left:18px; margin-top:4px; color:#fca5a5;">

                ${(rep.identified_issues || []).map(i => `<li>${escapeHtml(trContent(i))}</li>`).join('') || `<li style="color:var(--status-online);">${t('Không phát hiện lỗi nghiêm trọng!', 'No critical issues detected!')}</li>`}

              </ul>

            </div>

            <div style="margin-bottom:8px;">

              <strong>${t('Đoạn mã HTML / Schema.org JSON-LD sửa lỗi tự động:', 'Auto-Generated HTML / Schema.org JSON-LD Fix Snippets:')}</strong>

              <pre class="code-block" style="margin-top:4px;">${escapeHtml((rep.ready_to_paste_fixes || []).join('\n\n'))}</pre>

            </div>

            <div>

              <strong>${t('Bản nháp đề xuất dịch vụ (Chờ Chủ sở hữu duyệt):', 'Service Proposal Draft (Awaiting Owner Approval):')}</strong>

              <pre class="code-block" style="margin-top:4px;">${escapeHtml(trContent(res.custom_proposal_draft || ''))}</pre>

            </div>

          </div>

        `;

        showToast(t('Đã hoàn tất kiểm toán kỹ thuật và sinh mã sửa lỗi.', 'Completed technical audit and generated fix snippets.'));

        if (save_as_lead) await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi chạy kiểm toán', 'Audit error')}: ${err.message}`, true);

      }

    }



    function renderAdminPaymentReports() {
      const box = document.getElementById('paymentReportsList');
      if (!box) return;
      const reports = Array.isArray(STATE.paymentReports) ? STATE.paymentReports : [];
      if (!reports.length) {
        box.innerHTML = `<div class="empty-state">${t('Chưa có yêu cầu thanh toán cần đối soát hoặc chưa đăng nhập quyền quản trị.', 'No payment requests to reconcile, or owner admin is not signed in.')}</div>`;
        return;
      }
      box.innerHTML = reports.map(report => {
        const pending = report.status === 'PENDING_REVIEW';
        const method = report.payment_method === 'BANK_TRANSFER' ? t('Chuyển khoản ngân hàng', 'Bank transfer') : t('Binance Pay / USDT', 'Binance Pay / USDT');
        return `<div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; padding:10px; border:1px solid var(--border-subtle); border-radius:8px; background:rgba(15,23,42,.72);">
          <div style="min-width:250px; flex:1;">
            <strong>${escapeHtml(report.product_name)}</strong> · <code>${escapeHtml(report.id)}</code>
            <div style="font-size:12px; color:var(--text-secondary);">${escapeHtml(report.customer_email || '')} · ${escapeHtml(method)} · $${Number(report.amount_usd || 0).toFixed(2)} (${Number(report.amount_vnd || 0).toLocaleString('vi-VN')}₫)</div>
            <div style="font-size:11px; color:var(--text-muted); word-break:break-all;">${t('Mã khách gửi:', 'Customer reference:')} ${escapeHtml(report.reference || t('Không có', 'None'))}</div>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="chip ${pending ? 'warn' : (report.status === 'PAID_VERIFIED' ? 'success' : 'danger')}">${escapeHtml(formatStatusLabel(report.status))}</span>
            ${pending ? `<button type="button" class="btn btn-sm btn-success" onclick="verifyPublicPaymentReportByAdmin('${escapeHtml(report.id)}')">${t('Đối soát và xác nhận', 'Reconcile and confirm')}</button>` : ''}
          </div>
        </div>`;
      }).join('');
    }


    async function verifyPublicPaymentReportByAdmin(reportId) {
      if (!promptOrGetAdminKey()) return;
      const report = (STATE.paymentReports || []).find(item => item.id === reportId);
      if (!report) { showToast(t('Không tìm thấy yêu cầu thanh toán. Hãy đồng bộ lại danh sách.', 'Payment request not found. Refresh the list.'), true); return; }
      const payload = {};
      if (report.payment_method === 'BANK_TRANSFER') {
        const reference = window.prompt(t('Nhập mã giao dịch trong sao kê ngân hàng sau khi đã kiểm tra đúng số tiền.', 'Enter the bank statement reference after confirming the amount.'));
        if (reference === null) return;
        payload.statement_reference = reference.trim();
        const amount = window.prompt(t('Nhập số tiền VND đúng như sao kê.', 'Enter the exact VND amount from the statement.'), String(report.amount_vnd || ''));
        if (amount === null) return;
        payload.amount_vnd = Number(amount);
      } else if (!/^0x[\da-fA-F]{64}$/.test(String(report.reference || ''))) {
        const reference = window.prompt(t('Nhập mã giao dịch trên lịch sử Binance Pay đã đối chiếu.', 'Enter the transaction ID checked against Binance Pay history.'));
        if (reference === null) return;
        payload.statement_reference = reference.trim();
        const amount = window.prompt(t('Nhập số USDT thực nhận trên lịch sử Binance Pay.', 'Enter the received USDT amount shown in Binance Pay history.'), String(report.amount_usd || ''));
        if (amount === null) return;
        payload.amount_usd = Number(amount);
      }
      try {
        const result = await apiFetch(`/api/admin/payment-reports/${encodeURIComponent(reportId)}/verify`, {
          method: 'POST', body: JSON.stringify(payload)
        });
        showToast(result.already_verified
          ? t('Yêu cầu đã được đối soát trước đó.', 'This request was already reconciled.')
          : t('Đã ghi nhận khoản thanh toán sau khi đối soát.', 'Payment recorded after reconciliation.'));
        await refreshAllData(false);
      } catch (err) {
        showToast(`${t('Đối soát thất bại:', 'Reconciliation failed:')} ${err.message}`, true);
      }
    }


    async function createRealOrder() {

      const customer_id = document.getElementById('orderCustomerSelect').value;

      const product_id = document.getElementById('orderProductSelect').value;

      const payment_provider = document.getElementById('orderPaymentProvider').value;

      const discount_usd = Number(document.getElementById('orderDiscountInput').value || 0);

      const custom_proposal = document.getElementById('orderProposalInput').value.trim();

      const quote_id = (document.getElementById('orderQuoteIdInput')?.value || '').trim() || null;

      const selected_tier_code = (document.getElementById('orderTierCodeInput')?.value || '').trim() || null;

      const quantity_units = Number(document.getElementById('orderUnitsInput')?.value || 1);



      if (!customer_id || !product_id) {

        showToast(t('Vui lòng chọn Khách hàng và Sản phẩm/Dịch vụ.', 'Please select a Customer and Product/Service.'), true);

        return;

      }

      try {

        const res = await apiFetch('/api/orders', {

          method: 'POST',

          body: JSON.stringify({

            customer_id,

            product_id,

            discount_usd,

            payment_provider,

            is_simulated: false,

            custom_proposal,

            quote_id,

            selected_tier_code,

            quantity_units,

            idempotency_key: `ord_${customer_id}_${product_id}_${Date.now()}`

          })

        });

        document.getElementById('orderCreatedBox').innerHTML = `

          <div style="padding:10px; border:1px solid var(--border-accent); border-radius:var(--radius-sm); font-size:12px;">

            ${t('Đã tạo đơn hàng', 'Created order')} <strong>${escapeHtml(res.order_number)}</strong> | ${t('Số tiền:', 'Amount:')} <strong>$${Number(res.net_amount_usd).toFixed(2)} USD</strong> | ${t('Trạng thái:', 'Status:')} <code>${escapeHtml(formatStatusLabel(res.status))}</code> (${t('Chưa cộng vào doanh thu thực nhận', 'Not yet added to verified revenue')}).

          </div>

        `;

        showToast(t(`Đã tạo đơn hàng ${res.order_number} ở trạng thái Chờ Thanh Toán.`, `Created order ${res.order_number} in PENDING_PAYMENT state.`));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi tạo đơn hàng', 'Order creation error')}: ${err.message}`, true);

      }

    }



    async function verifyBscTransaction() {

      const order_id = document.getElementById('verifyOrderSelect').value;

      const tx_hash = document.getElementById('verifyBscHash').value.trim();

      if (!order_id || !tx_hash) {

        showToast(t('Vui lòng chọn Đơn hàng và nhập mã giao dịch TxHash 0x...', 'Please select an Order and enter the 0x... TxHash.'), true);

        return;

      }

      try {

        const res = await apiFetch('/api/payments/verify-bsc-tx', {

          method: 'POST',

          body: JSON.stringify({ order_id, tx_hash })

        });

        document.getElementById('paymentVerifyResultBox').innerHTML = `<pre class="code-block">${escapeHtml(JSON.stringify(res, null, 2))}</pre>`;

        showToast(t('Đã xác minh giao dịch chuỗi khối BSC Mainnet thành công!', 'Verified On-Chain BSC Mainnet transaction successfully!'));

        await refreshAllData(false);

      } catch (err) {

        document.getElementById('paymentVerifyResultBox').innerHTML = `<div style="color:var(--status-danger); font-size:12px;">${t('Từ chối xác minh chuỗi khối:', 'On-Chain Verification Rejected:')} ${escapeHtml(err.message)}</div>`;

        showToast(`${t('Từ chối TxHash', 'Rejected TxHash')}: ${err.message}`, true);

      }

    }



    async function submitCustomerBankProof() {

      const order_id = document.getElementById('verifyOrderSelect').value;

      const bank_tx_ref = document.getElementById('verifyBankRef').value.trim();

      const amount_vnd = Number(document.getElementById('verifyBankVnd').value || 0);

      if (!order_id || !bank_tx_ref) {

        showToast(t('Vui lòng chọn Đơn hàng và nhập mã tham chiếu FT...', 'Please select an Order and enter bank reference FT...'), true);

        return;

      }

      try {

        const res = await apiFetch('/api/payments/submit-mbbank-proof', {

          method: 'POST',

          body: JSON.stringify({ order_id, bank_tx_ref, amount_vnd })

        });

        document.getElementById('paymentVerifyResultBox').innerHTML = `

          <div style="padding:10px; border:1px solid rgba(245,158,11,0.5); border-radius:var(--radius-sm); color:#fde68a; font-size:12px;">

            ${escapeHtml(trContent(res.message))}

          </div>

        `;

        showToast(t('Đã ghi nhận mã tham chiếu ở trạng thái Chờ Đối Soát.', 'Recorded bank reference in PENDING_VERIFICATION state.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi gửi mã tham chiếu', 'Reference submission error')}: ${err.message}`, true);

      }

    }



    async function ownerReconcileBankTransfer() {

      if (!promptOrGetAdminKey()) return;

      const order_id = document.getElementById('verifyOrderSelect').value;

      const bank_tx_ref = document.getElementById('verifyBankRef').value.trim();

      const amount_vnd = Number(document.getElementById('verifyBankVnd').value || 0);

      if (!order_id || !bank_tx_ref) {

        showToast(t('Vui lòng chọn Đơn hàng và nhập mã giao dịch sao kê FT...', 'Please select an Order and enter statement reference FT...'), true);

        return;

      }

      try {

        const res = await apiFetch('/api/payments/verify-mbbank-tx', {

          method: 'POST',

          body: JSON.stringify({ order_id, bank_tx_ref, amount_vnd })

        });

        document.getElementById('paymentVerifyResultBox').innerHTML = `<pre class="code-block">${escapeHtml(JSON.stringify(res, null, 2))}</pre>`;

        showToast(t('Chủ tài khoản đã đối soát sao kê và xác nhận thanh toán thành công!', 'Owner reconciled bank statement and confirmed payment!'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Đối soát thất bại', 'Reconciliation failed')}: ${err.message}`, true);

      }

    }



    async function deliverOrderPackage(orderId) {

      try {

        const res = await apiFetch(`/api/orders/${encodeURIComponent(orderId)}/deliver`);

        document.getElementById('deliveryPackageOutput').innerHTML = `

          <div style="padding:14px; border:1px solid var(--status-online); border-radius:var(--radius-md); background:rgba(16,185,129,0.08);">

            <div style="font-weight:700; color:#6ee7b7; margin-bottom:6px;">

              ✓ ${t('Bàn Giao Thành Công Đơn Hàng', 'Successfully Delivered Order')} ${escapeHtml(res.order_number)}

            </div>

            <div style="font-size:12px; color:var(--text-secondary); margin-bottom:8px;">

              ${t('Sản phẩm:', 'Product:')} <strong>${escapeHtml(trContent(res.product?.name))}</strong> | ${t('Chính sách:', 'Policy:')} ${escapeHtml(trContent(res.support_and_refund_policy))}

            </div>

            <pre class="code-block">${escapeHtml(res.product?.executable_python_code || '')}</pre>

          </div>

        `;

        showToast(t(`Đã mở khóa bàn giao sản phẩm cho đơn ${res.order_number}.`, `Unlocked product delivery for order ${res.order_number}.`));

      } catch (err) {

        document.getElementById('deliveryPackageOutput').innerHTML = `

          <div style="padding:12px; border:1px solid rgba(239,68,68,0.5); border-radius:var(--radius-md); background:rgba(239,68,68,0.1); color:#fca5a5; font-size:12.5px;">

            🔒 ${t('Chặn bàn giao (HTTP 402):', 'Delivery Blocked (HTTP 402):')} ${escapeHtml(err.message)}

          </div>

        `;

        showToast(err.message, true);

      }

    }



    async function generateMarketingForPrimaryProduct() {

      const prod = STATE.products[0];

      if (!prod) return;

      try {

        await apiFetch(`/api/marketing/generate/${encodeURIComponent(prod.id)}`, { method: 'POST' });

        showToast(t('Đã tạo tài sản nội dung SEO mới.', 'Generated new SEO content asset.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi tạo nội dung SEO', 'SEO content generation error')}: ${err.message}`, true);

      }

    }



    async function approveAgentTask(taskId) {

      if (!promptOrGetAdminKey()) return;

      try {

        const result = await apiFetch(`/api/tasks/${encodeURIComponent(taskId)}/approve`, { method: 'POST' });

        showToast(result.execution_started
          ? t('Đã duyệt và worker bắt đầu thực thi nhiệm vụ.', 'Task approved and the worker started execution.')
          : t('Đã duyệt nhiệm vụ. Worker thực thi chưa được kết nối nên chưa chạy.', 'Task approved. No execution worker is connected, so it has not started.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi phê duyệt nhiệm vụ', 'Task approval error')}: ${err.message}`, true);

      }

    }



    async function pauseSystem() {

      if (!promptOrGetAdminKey()) return;

      try {

        const result = await apiFetch('/api/system/pause', { method: 'POST' });

        showToast(t(`Đã lưu trạng thái ${result.system_status}. Worker chưa kết nối.`, `Saved ${result.system_status} state. No worker is connected.`));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi tạm dừng', 'Pause error')}: ${err.message}`, true);

      }

    }



    async function resumeSystem() {

      if (!promptOrGetAdminKey()) return;

      try {

        const result = await apiFetch('/api/system/resume', { method: 'POST' });

        showToast(t(`Đã lưu trạng thái ${result.system_status}. Worker chưa kết nối.`, `Saved ${result.system_status} state. No worker is connected.`));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi tiếp tục chạy', 'Resume error')}: ${err.message}`, true);

      }

    }



    async function triggerEmergencyStopPrompt() {

      if (!promptOrGetAdminKey()) return;

      const reason = window.prompt(

        t('Nhập lý do kích hoạt dừng khẩn cấp:', 'Enter reason for triggering Emergency Stop:'),

        t('Chủ sở hữu kích hoạt dừng khẩn cấp thủ công', 'Owner manual emergency stop')

      );

      if (reason === null) return;

      try {

        const result = await apiFetch('/api/system/emergency-stop', {

          method: 'POST',

          body: JSON.stringify({ reason })

        });

        showToast(result.message || t('Đã ghi nhận yêu cầu dừng; worker chưa kết nối nên không có tiến trình nào bị ngắt.', 'Stop request saved; no running worker was interrupted.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi dừng khẩn cấp', 'Emergency Stop error')}: ${err.message}`, true);

      }

    }



    async function updateBudgetSettings() {

      if (!promptOrGetAdminKey()) return;

      try {

        await apiFetch('/api/settings/budgets', {

          method: 'PUT',

          body: JSON.stringify({

            operating_mode: document.getElementById('cfgOperatingMode').value,

            max_daily_tasks: Number(document.getElementById('cfgMaxDailyTasks').value),

            daily_budget_limit_usd: Number(document.getElementById('cfgDailyBudget').value),

            monthly_budget_limit_usd: Number(document.getElementById('cfgMonthlyBudget').value),

            task_budget_limit_usd: Number(document.getElementById('cfgTaskBudget').value)

          })

        });

        showToast(t('Đã cập nhật hạn mức ngân sách và chế độ vận hành.', 'Updated budget limits and operating mode.'));

        await refreshAllData(false);

      } catch (err) {

        showToast(`${t('Lỗi cập nhật ngân sách', 'Budget update error')}: ${err.message}`, true);

      }

    }



    function saveAdminKeyToSession() {

      if (!isSecureAdminOrigin()) {

        showToast(t('Quản trị yêu cầu HTTPS; không nhập khóa trên kết nối HTTP.', 'Admin access requires HTTPS; do not enter the key over HTTP.'), true);

        return;

      }

      const val = document.getElementById('adminKeyInput').value.trim();

      if (!val) {

        showToast(t('Vui lòng nhập khóa quản trị X-Admin-Key.', 'Please enter the X-Admin-Key.'), true);

        return;

      }

      sessionStorage.setItem('autoprofit_owner_admin_key', val);

      showToast(t('Đã lưu Khóa Quản Trị Viên vào phiên trình duyệt hiện tại.', 'Saved Owner Admin API Key to current sessionStorage.'));

    }



    function clearAdminKeySession() {

      sessionStorage.removeItem('autoprofit_owner_admin_key');

      document.getElementById('adminKeyInput').value = '';

      showToast(t('Đã xóa khóa quản trị khỏi phiên trình duyệt.', 'Cleared admin key from browser session.'));

    }



    async function saveCustomApiBase() {

      const input = document.getElementById('customApiUrlInput');

      const raw = String(input?.value || '').trim();

      if (!raw) {

        showToast(t('Vui lòng nhập địa chỉ máy chủ API.', 'Please enter an API server URL.'), true);

        input?.focus();

        return;

      }

      let parsed;

      try { parsed = new URL(raw); }

      catch (_) {

        showToast(t('Địa chỉ API không hợp lệ. Hãy nhập URL bắt đầu bằng http:// hoặc https://.', 'Invalid API URL. Enter a URL starting with http:// or https://.'), true);

        input?.focus();

        return;

      }

      if (!['http:', 'https:'].includes(parsed.protocol) || !parsed.hostname || parsed.username || parsed.password || parsed.search || parsed.hash) {

        showToast(t('URL API chỉ được dùng HTTP(S), không kèm tài khoản, tham số hoặc fragment.', 'API URL must use HTTP(S) and cannot include credentials, query parameters, or a fragment.'), true);

        input?.focus();

        return;

      }

      const val = `${parsed.origin}${parsed.pathname.replace(/\/+$/, '')}`;

      const controller = new AbortController();

      const timer = window.setTimeout(() => controller.abort(), 4500);

      try {

        const response = await fetch(`${val}/api/health`, { cache: 'no-store', signal: controller.signal });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

      } catch (err) {

        showToast(t(`Không kết nối được ${val}/api/health. Địa chỉ hiện tại vẫn được giữ nguyên.`, `Could not connect to ${val}/api/health. The current address was kept.`), true);

        input?.focus();

        return;

      } finally {

        window.clearTimeout(timer);

      }

      localStorage.setItem('autoprofit_api_base', val);

      API_BASE = val;

      if (input) input.value = val;

      showToast(t('Đã kết nối máy chủ API. Đang đồng bộ dữ liệu…', 'API server connected. Syncing data…'));

      await refreshAllData(false);

    }



    function resetApiBase() {

      localStorage.removeItem('autoprofit_api_base');

      API_BASE = resolveInitialApiBase();

      document.getElementById('customApiUrlInput').value = API_BASE;

      refreshAllData(true);

    }



    // =========================================================================

    // FUTURISTIC NINE-AGENT COMMAND CENTER — AVATARS, INSPECTOR & LIVE LOGS

    // =========================================================================

    const FALLBACK_NINE_AGENTS = [

      {

        role: 'RESEARCH_AGENT',

        agent_id: 'RESEARCH_AGENT',

        title: 'AI Nghiên Cứu Thị Trường',

        responsibility: 'Quét tín hiệu thị trường và nhu cầu dịch vụ có nguồn xác thực (HN Algolia, GitHub Issues, RemoteOK).',

        code_module: 'backend/app/agents/orchestrator.py (Steps 1-2) & market_scanner.py',

        orchestrator_step: 'Bước 1-2 / 13'

      },

      {

        role: 'PRODUCT_AGENT',

        agent_id: 'PRODUCT_AGENT',

        title: 'AI Kiến Trúc Sản Phẩm',

        responsibility: 'Định nghĩa gói dịch vụ Kiểm Toán Kỹ Thuật Trang Web & Sửa Lỗi SEO, phạm vi bàn giao và mức giá minh bạch.',

        code_module: 'backend/app/agents/orchestrator.py (Step 4) & models/entities.py (ProductCatalog)',

        orchestrator_step: 'Bước 4 / 13'

      },

      {

        role: 'CODING_AGENT',

        agent_id: 'CODING_AGENT',

        title: 'AI Lập Trình & Kiểm Toán',

        responsibility: 'Thực thi bộ kiểm toán kỹ thuật HTML/SEO/Bảo mật trực tiếp (lead_finder_service.audit_website_live).',

        code_module: 'backend/app/services/lead_finder_service.py (audit_website_live)',

        orchestrator_step: 'Bước 5 / 13'

      },

      {

        role: 'MARKETING_AGENT',

        agent_id: 'MARKETING_AGENT',

        title: 'AI Tiếp Thị & Nội Dung SEO',

        responsibility: 'Tạo nội dung bài viết kỹ thuật & tài sản SEO hợp chuẩn, không phát tán thư rác, không tuyên bố sai sự thật.',

        code_module: 'backend/app/agents/orchestrator.py (Step 7) & models/entities.py (MarketingAsset)',

        orchestrator_step: 'Bước 7 / 13'

      },

      {

        role: 'SALES_AGENT',

        agent_id: 'SALES_AGENT',

        title: 'AI Tìm Khách & Báo Giá',

        responsibility: 'Quét doanh nghiệp thật từ OpenStreetMap, kiểm toán lỗi website và soạn đề xuất cá nhân hóa chờ duyệt.',

        code_module: 'backend/app/services/lead_finder_service.py (discover_and_audit_real_leads)',

        orchestrator_step: 'Bước 8-9 / 13'

      },

      {

        role: 'CUSTOMER_SUPPORT_AGENT',

        agent_id: 'CUSTOMER_SUPPORT_AGENT',

        title: 'AI Bàn Giao & Hỗ Trợ',

        responsibility: 'Theo dõi trạng thái đơn hàng, hướng dẫn thanh toán và bàn giao gói báo cáo kỹ thuật sau khi thanh toán.',

        code_module: 'backend/app/api/routes.py (/api/orders/{id}/deliverable)',

        orchestrator_step: 'Bước 10 / 13'

      },

      {

        role: 'FINANCE_AGENT',

        agent_id: 'FINANCE_AGENT',

        title: 'AI Tài Chính & Chuỗi Khối',

        responsibility: 'Đối soát giao dịch USDT BEP20 trên chuỗi khối / VietQR và hạch toán 9 nhóm tài chính trung thực.',

        code_module: 'backend/app/services/payment_verifier.py & finance_service.py',

        orchestrator_step: 'Bước 11 / 13'

      },

      {

        role: 'OPTIMIZATION_AGENT',

        agent_id: 'OPTIMIZATION_AGENT',

        title: 'AI Tối Ưu Hóa Chiến Lược',

        responsibility: 'Đánh giá tỷ lệ chuyển đổi, hiệu quả chi phí và đề xuất bước tiếp theo cho chủ sở hữu.',

        code_module: 'backend/app/agents/orchestrator.py (Step 12-13)',

        orchestrator_step: 'Bước 12-13 / 13'

      },

      {

        role: 'SECURITY_AGENT',

        agent_id: 'SECURITY_AGENT',

        title: 'AI Bảo Mật & Kiểm Soát',

        responsibility: 'Giám sát hạn mức ngân sách, khóa chống chạy trùng, phân quyền RBAC, Dừng Khẩn Cấp và nhật ký bảo mật.',

        code_module: 'backend/app/services/guardrail_service.py & core/security.py',

        orchestrator_step: 'Bước 3 & Bảo Vệ Liên Tục'

      }

    ];



    function pushUiNotice(msg) {

      UI_EVENT_LOGS.unshift({

        ts: new Date().toISOString(),

        type: 'UI_NOTICE',

        actor: 'COMMAND_CENTER_UI',

        msg

      });

      if (UI_EVENT_LOGS.length > 25) UI_EVENT_LOGS.pop();

    }



    function getStatusColorHex(status) {

      switch (status) {

        case 'WORKING': return '#06b6d4';

        case 'THINKING': return '#8b5cf6';

        case 'WAITING_APPROVAL': return '#f59e0b';

        case 'SUCCESS': return '#10b981';

        case 'ERROR': return '#ef4444';

        case 'IDLE': return '#64748b';

        case 'OFFLINE':

        default: return '#475569';

      }

    }



    function getStatusActionLabel(role, status) {

      if (status === 'OFFLINE') return t('Mất kết nối Máy chủ — Nhân vật đang ngoại tuyến', 'Backend Disconnected — Agent is offline');

      if (status === 'IDLE') return t('Đang nghỉ — Chờ kích hoạt luồng công việc', 'Idle — Waiting for workflow trigger');

      if (status === 'WAITING_APPROVAL') return t('Yêu cầu Chủ sở hữu phê duyệt', 'Requires Owner Approval (Human-in-the-Loop)');

      if (status === 'ERROR') return t('Phát hiện lỗi thực thi — Xem chi tiết & cách xử lý', 'Execution error detected — Inspect details & remediation');

      if (status === 'THINKING') return t('Đang phân tích dữ liệu & lập kế hoạch hành động...', 'Analyzing telemetry & planning execution...');



      const workingMapVi = {

        RESEARCH_AGENT: 'Quét tín hiệu thị trường & cơ hội dịch vụ thực tế',

        PRODUCT_AGENT: 'Kiểm định cấu hình gói dịch vụ & phạm vi bàn giao',

        CODING_AGENT: 'Phân tích mã HTML/SEO & trích xuất bằng chứng kỹ thuật',

        MARKETING_AGENT: 'Biên soạn tài sản nội dung SEO chuẩn kỹ thuật',

        SALES_AGENT: 'Kiểm toán trang web khách hàng & tạo đề xuất cá nhân hóa',

        CUSTOMER_SUPPORT_AGENT: 'Trực bàn giao báo cáo kỹ thuật cho đơn hàng đã thanh toán',

        FINANCE_AGENT: 'Đối soát sổ cái 9 nhóm & kiểm tra giao dịch chuỗi khối',

        OPTIMIZATION_AGENT: 'Đánh giá lợi tức ROI, chi phí vận hành & tối ưu chuyển đổi',

        SECURITY_AGENT: 'Thực thi rào chắn ngân sách, phân quyền & khóa đơn luồng'

      };

      const workingMapEn = {

        RESEARCH_AGENT: 'Scanning live market signals & service opportunities',

        PRODUCT_AGENT: 'Validating service package scope & deliverables',

        CODING_AGENT: 'Auditing HTML/SEO code & extracting technical evidence',

        MARKETING_AGENT: 'Generating ethical technical SEO content assets',

        SALES_AGENT: 'Auditing client websites & drafting personalized proposals',

        CUSTOMER_SUPPORT_AGENT: 'Standing by to deliver technical packages for paid orders',

        FINANCE_AGENT: 'Reconciling 9-bucket ledger & verifying on-chain transactions',

        OPTIMIZATION_AGENT: 'Evaluating ROI, operating costs & conversion metrics',

        SECURITY_AGENT: 'Enforcing budget guardrails, RBAC & single-worker lock'

      };

      return CURRENT_LANG === 'en'

        ? (workingMapEn[role] || 'Completed verified task in SQLite')

        : (workingMapVi[role] || 'Đã hoàn thành nhiệm vụ xác thực trên SQLite');

    }



    function getAgentHologramAvatar(role, status) {

      const accent = getStatusColorHex(status);

      const isOff = status === 'OFFLINE' || status === 'IDLE';

      const glowOpacity = isOff ? '0.22' : '0.85';



      let gearSvg = '';

      switch (role) {

        case 'RESEARCH_AGENT':

          gearSvg = `

            <circle cx="50" cy="22" r="16" fill="none" stroke="${accent}" stroke-width="1.2" stroke-dasharray="4 3" opacity="${glowOpacity}"/>

            <path d="M22 30 L32 36 M78 30 L68 36" stroke="${accent}" stroke-width="1.8" stroke-linecap="round"/>

            <circle cx="20" cy="28" r="3" fill="${accent}"/>

            <circle cx="80" cy="28" r="3" fill="${accent}"/>

          `;

          break;

        case 'PRODUCT_AGENT':

          gearSvg = `

            <polygon points="50,8 62,14 62,26 50,32 38,26 38,14" fill="rgba(6,182,212,0.12)" stroke="${accent}" stroke-width="1.4"/>

            <path d="M38 14 L50 20 L62 14 M50 20 L50 32" stroke="${accent}" stroke-width="1.1"/>

          `;

          break;

        case 'CODING_AGENT':

          gearSvg = `

            <path d="M24 38 L16 44 L24 50" fill="none" stroke="${accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>

            <path d="M76 38 L84 44 L76 50" fill="none" stroke="${accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>

            <line x1="20" y1="22" x2="80" y2="22" stroke="${accent}" stroke-width="1.2" stroke-dasharray="2 4"/>

          `;

          break;

        case 'MARKETING_AGENT':

          gearSvg = `

            <path d="M22 26 A30 30 0 0 1 78 26" fill="none" stroke="${accent}" stroke-width="1.4" stroke-dasharray="3 3"/>

            <path d="M16 20 A38 38 0 0 1 84 20" fill="none" stroke="${accent}" stroke-width="1.1" opacity="0.65"/>

            <circle cx="50" cy="14" r="3" fill="${accent}"/>

          `;

          break;

        case 'SALES_AGENT':

          gearSvg = `

            <circle cx="76" cy="34" r="8" fill="none" stroke="${accent}" stroke-width="1.4"/>

            <line x1="76" y1="23" x2="76" y2="45" stroke="${accent}" stroke-width="1"/>

            <line x1="65" y1="34" x2="87" y2="34" stroke="${accent}" stroke-width="1"/>

          `;

          break;

        case 'CUSTOMER_SUPPORT_AGENT':

          gearSvg = `

            <path d="M30 42 A20 20 0 0 1 70 42" fill="none" stroke="${accent}" stroke-width="2.2"/>

            <rect x="26" y="38" width="5" height="10" rx="2" fill="${accent}"/>

            <rect x="69" y="38" width="5" height="10" rx="2" fill="${accent}"/>

            <path d="M30 47 Q38 56 48 54" fill="none" stroke="${accent}" stroke-width="1.6"/>

          `;

          break;

        case 'FINANCE_AGENT':

          gearSvg = `

            <polygon points="22,26 28,30 28,38 22,42 16,38 16,30" fill="none" stroke="${accent}" stroke-width="1.5"/>

            <polygon points="78,26 84,30 84,38 78,42 72,38 72,30" fill="none" stroke="${accent}" stroke-width="1.5"/>

            <line x1="28" y1="34" x2="35" y2="38" stroke="${accent}" stroke-width="1.2"/>

            <line x1="72" y1="34" x2="65" y2="38" stroke="${accent}" stroke-width="1.2"/>

          `;

          break;

        case 'OPTIMIZATION_AGENT':

          gearSvg = `

            <rect x="16" y="42" width="4" height="10" fill="${accent}" opacity="0.7"/>

            <rect x="22" y="36" width="4" height="16" fill="${accent}" opacity="0.85"/>

            <rect x="28" y="30" width="4" height="22" fill="${accent}"/>

            <path d="M72 48 L78 38 L84 42 L90 30" fill="none" stroke="${accent}" stroke-width="1.8" stroke-linecap="round"/>

          `;

          break;

        case 'SECURITY_AGENT':

        default:

          gearSvg = `

            <path d="M50 10 L64 16 L64 28 C64 37 50 43 50 43 C50 43 36 37 36 28 L36 16 Z" fill="rgba(6,182,212,0.08)" stroke="${accent}" stroke-width="1.4"/>

          `;

          break;

      }



      return `

        <svg class="agent-svg-avatar" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${escapeHtml(role)}">

          <defs>

            <linearGradient id="suitGrad_${escapeHtml(role)}" x1="0%" y1="0%" x2="100%" y2="100%">

              <stop offset="0%" stop-color="#1e293b"/>

              <stop offset="100%" stop-color="#090d16"/>

            </linearGradient>

          </defs>

          <ellipse cx="50" cy="92" rx="34" ry="5" fill="none" stroke="${accent}" stroke-width="1.4" opacity="${glowOpacity}"/>

          <ellipse cx="50" cy="92" rx="22" ry="2.5" fill="${accent}" opacity="0.25"/>

          <path d="M20 88 C20 68 32 60 50 60 C68 60 80 68 80 88 Z" fill="url(#suitGrad_${escapeHtml(role)})" stroke="${accent}" stroke-width="1.6"/>

          <polygon points="50,67 57,73 50,82 43,73" fill="${accent}" opacity="${glowOpacity}"/>

          <path d="M32 68 L42 75 M68 68 L58 75" stroke="${accent}" stroke-width="1.2" opacity="0.75"/>

          <rect x="45" y="52" width="10" height="9" rx="2" fill="#1e293b" stroke="${accent}" stroke-width="1.2"/>

          <path d="M35 38 C35 26 41 22 50 22 C59 22 65 26 65 38 C65 48 59 54 50 54 C41 54 35 48 35 38 Z" fill="#0f172a" stroke="${accent}" stroke-width="1.6"/>

          <path d="M39 36 L61 36 L58 43 L42 43 Z" fill="${accent}" opacity="${glowOpacity}"/>

          <line x1="42" y1="39" x2="58" y2="39" stroke="#ffffff" stroke-width="1" opacity="0.75"/>

          ${gearSvg}

        </svg>

      `;

    }



    function getEnrichedAgentsList(isOffline = false) {

      const sys = STATE.dashboard?.system || {};

      const hasVerifiedRegistry = Array.isArray(STATE.dashboard?.agents_registry)
        && STATE.dashboard.agents_registry.length > 0;
      const disconnected = isOffline || !STATE.online;
      const rawRegistry = hasVerifiedRegistry

        ? STATE.dashboard.agents_registry

        : FALLBACK_NINE_AGENTS;



      return rawRegistry.map((baseAg, idx) => {

        const role = baseAg.role || baseAg.agent_id;

        const fallback = FALLBACK_NINE_AGENTS.find(f => f.role === role) || FALLBACK_NINE_AGENTS[idx] || {};

        const meta = AGENT_META_BILINGUAL[role] || {};

        const agentTasks = (STATE.tasks || []).filter(t => t.agent_role === role);

        const latestTask = agentTasks[0] || null;



        let commandStatus = baseAg.command_status;

        if (disconnected) {

          commandStatus = 'OFFLINE';

        } else if (!hasVerifiedRegistry) {

          commandStatus = 'IDLE';

        } else if (!commandStatus) {

          if (sys.system_status === 'EMERGENCY_STOP') commandStatus = 'OFFLINE';

          else if (latestTask) {

            const st = latestTask.ui_status || latestTask.status;

            if (st === 'WAITING_FOR_APPROVAL' || st === 'AWAITING_APPROVAL') commandStatus = 'WAITING_APPROVAL';

            else if (st === 'RUNNING' || st === 'WORKING') commandStatus = 'WORKING';

            else if (st === 'THINKING' || st === 'PLANNED') commandStatus = 'THINKING';

            else if (st === 'FAILED' || st === 'BLOCKED') commandStatus = 'ERROR';

            else commandStatus = 'IDLE';

          } else {

            commandStatus = 'IDLE';

          }

        }



        const hasActiveFlow = disconnected || !hasVerifiedRegistry ? false : Boolean(

          baseAg.has_active_flow === true

        );



        const localizedTitle = formatAgentTitle(role);

        const localizedDuty = CURRENT_LANG === 'en'

          ? (meta.dutyEn || trContent(baseAg.responsibility || fallback.responsibility || ''))

          : (meta.dutyVi || trContent(baseAg.responsibility || fallback.responsibility || ''));

        const localizedStep = formatAgentStep(role);

        const localizedZone = formatZoneName(role);



        return {

          ...fallback,

          ...baseAg,

          role,

          is_demo_profile: !hasVerifiedRegistry,

          agent_id: baseAg.agent_id || role,

          title: localizedTitle,

          zone_name: localizedZone,

          responsibility: localizedDuty,

          code_module: baseAg.code_module || fallback.code_module || 'backend/app/agents/orchestrator.py',

          orchestrator_step: localizedStep,

          connected_to_orchestrator: hasVerifiedRegistry && baseAg.connected_to_orchestrator === true,

          has_active_flow: hasActiveFlow,

          command_status: commandStatus,

          current_job: disconnected

            ? t('Máy chủ Ngoại tuyến — Không thể truy xuất nhiệm vụ hiện tại', 'Backend Offline — Unable to retrieve active job')

            : (!hasVerifiedRegistry
              ? t('Hồ sơ minh họa — chưa có agent runtime đã xác minh.', 'Demo profile — no verified agent runtime is connected.')
              : trContent(baseAg.current_job || (latestTask ? latestTask.title : t('Chưa có tác vụ được gán.', 'No task has been assigned.')))),

          started_at: baseAg.started_at || (latestTask ? latestTask.started_at : null),

          completed_at: baseAg.completed_at || (latestTask ? latestTask.completed_at : null),

          progress_supported: false,

          progress_text: isOffline

            ? t('Ngoại tuyến (Máy chủ mất kết nối)', 'Offline (Backend Disconnected)')

            : trContent(baseAg.progress_text || t('Thực thi theo từng bước xác thực (Không phát tiến độ phần trăm giả lập)', 'Step-by-step verified execution (No fake percentage progress bars)')),

          output_summary: isOffline

            ? t('Chưa có dữ liệu do mất kết nối tới API máy chủ.', 'No telemetry available while disconnected from Backend API.')

            : trContent(baseAg.output_summary || (latestTask ? (latestTask.evidence || latestTask.outcome_reason) : t('Sẵn sàng thực thi nhiệm vụ', 'Ready for task execution'))),

          artifact_path: baseAg.artifact_path || 'backend/autoprofit.db',

          error_message: baseAg.error_message || (latestTask ? latestTask.error_message : null),

          remediation_hint: trContent(baseAg.remediation_hint || t('Kiểm tra kết nối API hoặc chạy lại chu kỳ 13 bước.', 'Check API connection or re-run the 13-step Orchestrator cycle.')),

          latest_task_id: baseAg.latest_task_id || (latestTask ? latestTask.id : null),

          requires_approval: Boolean(

            baseAg.requires_approval !== undefined

              ? baseAg.requires_approval

              : (commandStatus === 'WAITING_APPROVAL')

          ),

          total_tasks_count: !hasVerifiedRegistry ? null : (baseAg.total_tasks_count !== undefined ? baseAg.total_tasks_count : (agentTasks.length ? agentTasks.length : null)),

          total_cost_usd: !hasVerifiedRegistry ? null : (baseAg.total_cost_usd !== undefined

            ? Number(baseAg.total_cost_usd)

            : (agentTasks.length ? agentTasks.reduce((acc, x) => acc + Number(x.actual_cost_usd || 0), 0) : null)),

          activity_logs: Array.isArray(baseAg.activity_logs) && baseAg.activity_logs.length > 0

            ? baseAg.activity_logs

            : agentTasks.slice(0, 6).map(tItem => ({

                id: tItem.id,

                timestamp: tItem.completed_at || tItem.started_at,

                title: tItem.title,

                status: tItem.ui_status || tItem.status,

                evidence: tItem.evidence || tItem.outcome_reason || '',

                cost_usd: Number(tItem.actual_cost_usd || 0)

              }))

        };

      });

    }



    function renderNineAgentCommandCenter(isOffline = false) {

      const matrixEl = document.getElementById('nineAgentsMatrix');

      if (!matrixEl) return;



      const sys = STATE.dashboard?.system || {};

      const coreModeBadge = document.getElementById('ccCoreModeBadge');

      const coreSubtext = document.getElementById('ccCoreSubtext');

      const localeCode = CURRENT_LANG === 'en' ? 'en-US' : 'vi-VN';



      if (isOffline || !STATE.online) {

        if (coreModeBadge) {

          coreModeBadge.textContent = t('LÕI AI: NGOẠI TUYẾN', 'CORE: OFFLINE');

          coreModeBadge.className = 'chip danger';

        }

        if (coreSubtext) {

          coreSubtext.textContent = t(

            `Mất kết nối tới Máy chủ (${API_BASE}). Toàn bộ Nhân Sự AI Đang Hoạt Động chuyển sang trạng thái Ngoại tuyến trung thực.`,

            `Disconnected from Backend (${API_BASE}). All Active AI Agents switched to honest OFFLINE state.`

          );

        }

      } else {

        const st = sys.system_status || 'UNKNOWN';

        const aiMode = sys.ai_provider_mode || 'NOT_CONNECTED';

        if (coreModeBadge) {

          coreModeBadge.textContent = `${t('LÕI AI', 'CORE')}: ${formatStatusLabel(st)} (${formatStatusLabel(aiMode)})`;

          coreModeBadge.className = st === 'RUNNING' ? 'chip cyan' : (st === 'IDLE' || st === 'PAUSED' ? 'chip warn' : 'chip danger');

        }

        if (coreSubtext) {

          coreSubtext.textContent = t(

            `Runtime: ${st === 'RUNNING' ? 'ĐANG CHẠY' : 'CHƯA CHẠY'} | Chu kỳ gần nhất: ${sys.last_cycle_at ? new Date(sys.last_cycle_at).toLocaleTimeString(localeCode) : 'Chưa có'} | Nhấp vào hồ sơ để xem trạng thái.`,

            `Runtime: ${st === 'RUNNING' ? 'RUNNING' : 'IDLE'} | Last cycle: ${sys.last_cycle_at ? new Date(sys.last_cycle_at).toLocaleTimeString(localeCode) : 'None recorded'} | Click a profile to inspect its state.`

          );

        }

      }



      const agents = getEnrichedAgentsList(isOffline);

      matrixEl.innerHTML = agents.map(ag => {

        const st = ag.command_status || 'IDLE';

        const isSelected = SELECTED_AGENT_ID === ag.role;

        const conduitClass = ag.has_active_flow ? 'agent-conduit active-flow' : 'agent-conduit';

        const actionCaption = getStatusActionLabel(ag.role, st);



        return `

          <div class="agent-pod status-${escapeHtml(st)} ${isSelected ? 'selected' : ''} ${ag.is_demo_profile ? 'agent-demo-profile' : ''}"

               onclick="openAgentInspector('${escapeHtml(ag.role)}')"

               role="button"

               tabindex="0"

               aria-label="${escapeHtml(ag.title)}"

               onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openAgentInspector('${escapeHtml(ag.role)}');}">

            <div class="${conduitClass}" title="${ag.has_active_flow ? t('Luồng dữ liệu thực tế từ Lõi AI đang hoạt động', 'Active live telemetry flow from AI Core') : t('Không có luồng hoạt động (Đang nghỉ / Ngoại tuyến)', 'No active flow (IDLE / OFFLINE)')}"></div>

            <div class="agent-pod-top">

              <span class="agent-step-tag">${escapeHtml(ag.orchestrator_step)}</span>

              ${ag.is_demo_profile ? `<span class="chip warn" title="${escapeHtml(t('Hồ sơ tĩnh minh họa; chưa được đăng ký bởi backend.', 'Static demo profile; not registered by the backend.'))}">DEMO</span>` : ''}

              <span class="agent-status-pill ${escapeHtml(st)}">

                <span class="agent-status-dot"></span>

                ${escapeHtml(formatStatusLabel(st))}

              </span>

            </div>

            <div class="agent-avatar-stage">

              <div class="agent-holo-ring"></div>

              <div class="agent-scan-beam"></div>

              ${getAgentHologramAvatar(ag.role, st)}

            </div>

            <div class="agent-name">${escapeHtml(ag.title)}</div>

            <div class="agent-id-code">${escapeHtml(ag.zone_name)}</div>

            <div class="agent-duty">${escapeHtml(ag.responsibility)}</div>

            <div class="agent-job-box">

              <strong>${t('Công việc / Trạng thái thực tế:', 'Current Job / Live Status:')}</strong>

              <span>${escapeHtml(ag.current_job)}</span>

              <div style="margin-top:4px; font-size:10.5px; color:var(--accent-cyan); font-family:var(--font-mono);">▸ ${escapeHtml(actionCaption)}</div>

            </div>

            <div class="agent-pod-footer">

              <span>${t('Nhiệm vụ:', 'Tasks:')} <strong>${ag.total_tasks_count == null ? '—' : Number(ag.total_tasks_count)}</strong> | ${t('Chi phí:', 'Cost:')} <strong>${escapeHtml(formatFinanceValue(ag.total_cost_usd, 4))}</strong></span>

              <span class="agent-inspect-hint">${t('Chi tiết ↗', 'Inspect ↗')}</span>

            </div>

          </div>

        `;

      }).join('');



      // If Inspector modal is currently open for an agent, keep its telemetry fresh

      if (SELECTED_AGENT_ID) {

        const modal = document.getElementById('agentDetailModal');

        if (modal && modal.classList.contains('open')) {

          renderAgentInspectorContent(SELECTED_AGENT_ID, isOffline);

        }

      }



      if (typeof sync3DWorldAndCommHub === 'function') {

        sync3DWorldAndCommHub(isOffline);

      }

    }



    function openAgentInspector(agentId) {

      SELECTED_AGENT_ID = agentId;

      renderNineAgentCommandCenter(!STATE.online);

      renderAgentInspectorContent(agentId, !STATE.online);

      const modal = document.getElementById('agentDetailModal');

      if (modal) modal.classList.add('open');

    }



    function closeAgentInspector() {

      SELECTED_AGENT_ID = null;

      const modal = document.getElementById('agentDetailModal');

      if (modal) modal.classList.remove('open');

      renderNineAgentCommandCenter(!STATE.online);

    }



    function renderAgentInspectorContent(agentId, isOffline = false) {

      const container = document.getElementById('agentDetailModalContent');

      if (!container) return;



      const agents = getEnrichedAgentsList(isOffline);

      const ag = agents.find(x => x.role === agentId || x.agent_id === agentId) || agents[0];

      if (!ag) return;



      const emp = (STATE.employees || []).find(e => e.role_code === ag.role || e.employee_id === ag.agent_id) || null;

      const ch3d = WORLD_3D.charactersByRole ? WORLD_3D.charactersByRole[ag.role] : null;

      const localeCode = CURRENT_LANG === 'en' ? 'en-US' : 'vi-VN';

      const st = ag.command_status || 'IDLE';

      const anim3dState = ch3d ? ch3d.animState : (st === 'IDLE' ? 'IDLE' : (st === 'OFFLINE' ? 'OFFLINE' : 'WORK_AT_DESK'));

      const isBusy = !(st === 'IDLE' || st === 'OFFLINE');

      const startedStr = ag.started_at ? new Date(ag.started_at).toLocaleString(localeCode) : t('Chưa có dữ liệu', 'No data recorded');

      const completedStr = ag.completed_at ? new Date(ag.completed_at).toLocaleString(localeCode) : (st === 'WORKING' ? t('Đang thực thi...', 'Executing...') : t('Chưa có dữ liệu', 'No data recorded'));

      const logs = Array.isArray(ag.activity_logs) ? ag.activity_logs : [];



      const humanDisplayName = emp

        ? (CURRENT_LANG === 'en' ? (emp.display_name_en || emp.display_name_vi) : (emp.display_name_vi || emp.display_name_en))

        : (ch3d?.cfg?.humanName ? `${ch3d.cfg.humanName} — ${ag.title}` : ag.title);

      const skillsList = (emp && Array.isArray(emp.skills) && emp.skills.length)

        ? emp.skills

        : (ag.skills && Array.isArray(ag.skills) && ag.skills.length ? ag.skills : []);

      const collabList = (emp && Array.isArray(emp.collaborating_agents) && emp.collaborating_agents.length)

        ? emp.collaborating_agents

        : Array.from(new Set((STATE.agentMessages || [])

            .filter(m => !m.is_demo && (m.sender_agent_id === ag.role || m.receiver_agent_id === ag.role))

            .map(m => m.sender_agent_id === ag.role ? m.receiver_agent_id : m.sender_agent_id)

            .filter(Boolean)));

      const assistanceList = (emp && Array.isArray(emp.assistance_requests) && emp.assistance_requests.length)

        ? emp.assistance_requests

        : [];

      const missingCapsList = (emp && Array.isArray(emp.missing_capabilities) && emp.missing_capabilities.length)

        ? emp.missing_capabilities

        : [];

      const recordedCostUsd = financeValueOrNull(emp?.recorded_operating_cost_usd ?? ag.total_cost_usd);



      container.innerHTML = `

        <div class="inspector-header">

          <div class="inspector-title-group">

            <div class="inspector-avatar-mini">

              ${getAgentHologramAvatar(ag.role, st)}

            </div>

            <div>

              <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">

                <h3 style="font-size:18px; font-weight:700; color:#fff;">1. ${escapeHtml(humanDisplayName)}</h3>

                <span class="agent-status-pill ${escapeHtml(st)}">

                  <span class="agent-status-dot"></span>

                  4. ${t('Trạng thái:', 'Status:')} ${escapeHtml(formatStatusLabel(st))}

                </span>

                <span class="chip cyan" style="font-size:10.5px;">3D: ${escapeHtml(anim3dState)}</span>

                <span class="chip ${isBusy ? 'warn' : 'success'}" style="font-size:10.5px;">

                  ${isBusy ? t('ĐANG BẬN NHIỆM VỤ', 'BUSY ON TASK') : t('ĐANG RẢNH (SẴN SÀNG)', 'AVAILABLE')}

                </span>

                <span class="chip">${escapeHtml(ag.orchestrator_step)}</span>

              </div>

              <div style="font-family:var(--font-mono); font-size:12px; color:var(--accent-cyan); margin-top:4px;">

                ${t('Mã nhân viên:', 'Employee ID:')} <strong>${escapeHtml(emp?.employee_id || ag.agent_id)}</strong> | ${t('Phòng ban 3D:', '3D Office Room:')} <code>${escapeHtml(ag.zone_name)}</code>

              </div>

            </div>

          </div>

          <button class="btn btn-sm" onclick="closeAgentInspector()">✕ ${t('Đóng (ESC)', 'Close (ESC)')}</button>

        </div>



        <div class="inspector-body">

          <div class="inspector-grid">

            <div class="inspector-field">

              <div class="inspector-field-label">2. ${t('Vai trò & Trách nhiệm chuyên môn', 'Role & Professional Responsibility')}</div>

              <div class="inspector-field-val">${escapeHtml(ag.responsibility)}</div>

              <div style="margin-top:6px; font-size:11.5px; color:var(--text-muted); font-family:var(--font-mono);">

                ${t('Liên kết Lõi AI:', 'AI Core Link:')} ${ag.connected_to_orchestrator ? t('✓ Đã kết nối Chu trình 13 bước', '✓ Connected to 13-Step Orchestrator') : t('Độc lập', 'Standalone')} | ${t('Luồng hoạt động:', 'Active Flow:')} ${ag.has_active_flow ? t('ĐANG BẬT', 'ACTIVE') : t('ĐANG NGHỈ / NGOẠI TUYẾN', 'INACTIVE (IDLE/OFFLINE)')}

              </div>

            </div>



            <div class="inspector-field">

              <div class="inspector-field-label">3. ${t('Kỹ năng chuyên môn (Skills)', 'Verified Skills & Competencies')}</div>

              <div class="inspector-field-val">

                ${skillsList.length > 0

                  ? `<div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:4px;">

                      ${skillsList.map(sk => `<span class="chip cyan" style="font-size:11px;">✓ ${escapeHtml(sk)}</span>`).join('')}

                     </div>`

                  : `<span style="color:var(--text-muted);">${t('Chưa có dữ liệu', 'No data recorded')}</span>`

                }

              </div>

            </div>



            <div class="inspector-field">

              <div class="inspector-field-label">5. ${t('Nhiệm vụ hiện tại (Current Task)', 'Current Task & Execution Window')}</div>

              <div class="inspector-field-val" style="font-weight:600;">${escapeHtml(ag.current_job || t('Chưa có dữ liệu', 'No data recorded'))}</div>

              <div style="margin-top:6px; font-size:11.5px; color:var(--accent-cyan); font-family:var(--font-mono);">

                ${t('Mã nhiệm vụ:', 'Task ID:')} ${escapeHtml(ag.latest_task_id || t('Chạy tích hợp trực tiếp trong luồng dịch vụ', 'Integrated directly in service pipeline'))}

              </div>

              <div style="margin-top:4px; font-family:var(--font-mono); font-size:11px; color:var(--text-secondary);">

                • ${t('Bắt đầu:', 'Started:')} <strong>${escapeHtml(startedStr)}</strong> | ${t('Hoàn thành:', 'Completed:')} <strong>${escapeHtml(completedStr)}</strong>

              </div>

            </div>



            <div class="inspector-field">

              <div class="inspector-field-label">6. ${t('Tiến độ nhiệm vụ trung thực (Task Progress)', 'Honest Task Progress (Backend-Verified)')}</div>

              <div class="inspector-field-val">

                <span class="chip warn" style="margin-bottom:6px;">${t('Báo cáo trung thực: Không tự đánh dấu hoàn thành trên giao diện', 'Honest Telemetry: Never marked done by frontend animation')}</span>

                <div style="font-size:12px; color:var(--text-secondary); margin-top:4px;">

                  ${escapeHtml(ag.progress_text || t('Chưa có dữ liệu', 'No data recorded'))}

                </div>

              </div>

            </div>

          </div>



          <div class="inspector-grid">

            <div class="inspector-field">

              <div class="inspector-field-label">8. ${t('Kết quả đã xác minh (Verified Deliverables)', 'Verified Deliverables & Database Artifact')}</div>

              <div class="inspector-field-val">${escapeHtml(ag.output_summary || t('Chưa có dữ liệu', 'No data recorded'))}</div>

              <div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--border-subtle); font-family:var(--font-mono); font-size:11.5px; color:var(--accent-cyan);">

                📄 ${t('Nguồn lưu trữ:', 'Artifact Source:')} <code>${escapeHtml(ag.artifact_path || 'Chưa có dữ liệu')}</code> | ${t('Số sản phẩm xác minh:', 'Verified Deliverables:')} <strong>${emp?.verified_deliverables_count ?? ag.total_tasks_count ?? '—'}</strong>

              </div>

            </div>



            <div class="inspector-field">

              <div class="inspector-field-label">9. ${t('Nhân viên đang phối hợp (Collaborating Employees)', 'Collaborating AI Employees')}</div>

              <div class="inspector-field-val">

                ${collabList.length > 0

                  ? `<div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:4px;">

                      ${collabList.map(cRole => `<span class="chip" style="cursor:pointer;" onclick="selectCharacterIn3DWorld('${escapeHtml(cRole)}', true)">🤝 ${escapeHtml(formatAgentTitle(cRole))}</span>`).join('')}

                     </div>`

                  : `<span style="color:var(--text-muted);">${t('Chưa có dữ liệu', 'No data recorded')}</span>`

                }

              </div>

              <div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--border-subtle); font-family:var(--font-mono); font-size:11.5px;">

                12. ${t('Chi phí vận hành ghi nhận (Operating Cost):', 'Recorded Operating Cost:')} <strong style="color:#34d399;">${escapeHtml(formatFinanceValue(recordedCostUsd, 4))}</strong> (${ag.total_tasks_count == null ? '—' : Number(ag.total_tasks_count)} ${t('lần thực thi', 'executions')})

              </div>

            </div>

          </div>



          <div class="inspector-grid">

            <div class="inspector-field" style="border-color:${(ag.error_message || assistanceList.length) ? 'rgba(245,158,11,0.45)' : 'var(--border-subtle)'};">

              <div class="inspector-field-label">10. ${t('Yêu cầu hỗ trợ & Chẩn đoán lỗi (Assistance Requests)', 'Assistance Requests & Error Diagnostics')}</div>

              ${ag.error_message

                ? `<div style="color:#fca5a5; font-weight:600; font-size:12px; margin-bottom:4px;">⚠️ ${t('Lỗi ghi nhận:', 'Recorded Error:')} ${escapeHtml(trContent(ag.error_message))}</div>`

                : ''

              }

              ${assistanceList.length > 0

                ? `<div style="display:flex; flex-direction:column; gap:4px; margin-top:4px; font-size:11.5px;">

                    ${assistanceList.map(req => `<div style="padding:5px 8px; background:rgba(245,158,11,0.12); border-left:2px solid #f59e0b; border-radius:4px;">🆘 <strong>${escapeHtml(req.type || 'ASSISTANCE')}:</strong> ${escapeHtml(trContent(req.detail || ''))}</div>`).join('')}

                   </div>`

                : `<div style="color:#34d399; font-size:12px;">✓ ${t('Chưa có dữ liệu yêu cầu hỗ trợ khẩn cấp (0 lỗi đang treo).', 'No pending assistance requests recorded (0 blocking errors).')}</div>`

              }

            </div>



            <div class="inspector-field">

              <div class="inspector-field-label">11. ${t('Kỹ năng còn thiếu (Missing Capabilities)', 'Missing Capabilities & Skill Gaps')}</div>

              <div class="inspector-field-val">

                ${missingCapsList.length > 0

                  ? `<div style="display:flex; flex-direction:column; gap:4px; margin-top:4px; font-size:11.5px; color:#fcd34d;">

                      ${missingCapsList.map(mc => `<div>⚡ ${escapeHtml(mc)}</div>`).join('')}

                     </div>`

                  : `<div style="color:var(--text-secondary); font-size:12px;">${t('Chưa có dữ liệu thiếu hụt kỹ năng cho vị trí này.', 'No missing capabilities recorded for this role.')}</div>`

                }

              </div>

            </div>

          </div>



          <div class="inspector-field">

            <div class="inspector-field-label">7. ${t('Lịch sử công việc thực tế (Work History — SQLite)', 'Verified Work History (SQLite Records)')} (${logs.length})</div>

            ${logs.length === 0

              ? `<div class="empty-state" style="padding:12px;">${t('Chưa có dữ liệu lịch sử nhiệm vụ riêng cho nhân viên này.', 'No dedicated task history records for this employee yet.')}</div>`

              : `<div style="display:flex; flex-direction:column; gap:6px; margin-top:6px; max-height:150px; overflow-y:auto;">

                  ${logs.map(l => `

                    <div style="padding:8px 10px; border-radius:6px; background:rgba(15,23,42,0.75); border:1px solid var(--border-subtle); font-size:11.5px; display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">

                      <div>

                        <span class="chip ${l.status === 'COMPLETED' ? 'success' : (l.status === 'WAITING_FOR_APPROVAL' ? 'warn' : 'cyan')}" style="font-size:9.5px; padding:1px 6px; margin-right:6px;">${escapeHtml(formatStatusLabel(l.status))}</span>

                        <strong style="color:#fff;">${escapeHtml(trContent(l.title || l.message || ''))}</strong>

                        <div style="color:var(--text-secondary); margin-top:3px;">${escapeHtml(trContent(l.evidence || l.message || ''))}</div>

                      </div>

                      <div style="font-family:var(--font-mono); font-size:10.5px; color:var(--text-muted); white-space:nowrap;">

                        ${escapeHtml(l.timestamp ? new Date(l.timestamp).toLocaleTimeString(localeCode) : '')} | $${Number(l.cost_usd || 0).toFixed(4)}

                      </div>

                    </div>

                  `).join('')}

                </div>`

            }

          </div>



          <div class="inspector-field">

            <div class="inspector-field-label">👔 ${t('Tùy chỉnh Trang phục 3D & Điều hướng Văn phòng (Không đổi danh tính Backend)', '3D Outfit Customization & Office Navigation (Preserves Backend Identity)')}</div>

            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-top:6px;">

              <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">

                <span style="font-size:11px; color:var(--text-secondary);">${t('Bộ vest 3D:', '3D Suit:')}</span>

                <button class="btn btn-sm" onclick="changeEmployee3DOutfit('${escapeHtml(ag.role)}', '#1e3a8a', '#38bdf8')">👔 Navy Executive</button>

                <button class="btn btn-sm" onclick="changeEmployee3DOutfit('${escapeHtml(ag.role)}', '#065f46', '#10b981')">👔 Emerald Tech</button>

                <button class="btn btn-sm" onclick="changeEmployee3DOutfit('${escapeHtml(ag.role)}', '#581c87', '#c084fc')">👔 Royal Violet</button>

                <button class="btn btn-sm" onclick="changeEmployee3DOutfit('${escapeHtml(ag.role)}', '#334155', '#f59e0b')">👔 Charcoal Gold</button>

              </div>

              <div style="display:flex; gap:6px; flex-wrap:wrap;">

                <button class="btn btn-sm" onclick="sendEmployeeToMeetingRoom('${escapeHtml(ag.role)}'); closeAgentInspector();">

                  🤝 ${t('Đi tới Phòng Họp Trung Tâm', 'Walk to Central Boardroom')}

                </button>

                <button class="btn btn-sm" onclick="sendEmployeeBackToDesk('${escapeHtml(ag.role)}'); closeAgentInspector();">

                  💻 ${t('Quay về Bàn làm việc', 'Return to Workstation Desk')}

                </button>

              </div>

            </div>

          </div>



          <div class="inspector-field">

            <div class="inspector-field-label">💬 ${t('Tin nhắn giao tiếp liên quan đến', 'Communication Messages Involving')} ${escapeHtml(ag.title)}</div>

            ${(() => {

              const relMsgs = Array.isArray(ag.related_messages) && ag.related_messages.length

                ? ag.related_messages

                : (STATE.agentMessages || []).filter(m => !m.is_demo && (m.sender_agent_id === ag.role || m.receiver_agent_id === ag.role)).slice(0, 6);

              if (!relMsgs.length) {

                return `<div class="empty-state" style="padding:12px;">${t('Chưa có dữ liệu tin nhắn giao tiếp của nhân viên này.', 'No communication messages recorded for this employee yet.')}</div>`;

              }

              return `<div style="display:flex; flex-direction:column; gap:6px; margin-top:6px; max-height:150px; overflow-y:auto;">

                ${relMsgs.map(m => `

                  <div style="padding:8px 10px; border-radius:6px; background:rgba(11,19,38,0.85); border-left:3px solid #06b6d4; font-size:11.5px;">

                    <div style="display:flex; justify-content:space-between; font-family:var(--font-mono); font-size:10px; color:#38bdf8; margin-bottom:3px;">

                      <span><strong>${escapeHtml(formatAgentTitle(m.sender_agent_id))}</strong> → <strong>${escapeHtml(formatAgentTitle(m.receiver_agent_id))}</strong> [${escapeHtml(formatMessageTypeLabel(m.message_type))}]</span>

                      <span>${escapeHtml(m.created_at ? new Date(m.created_at).toLocaleTimeString(localeCode) : '')}</span>

                    </div>

                    <div style="color:#f1f5f9;">"${escapeHtml(trContent(m.message_content))}"</div>

                  </div>

                `).join('')}

              </div>`;

            })()}

          </div>

        </div>



        <div class="inspector-actions">

          <div style="font-size:11.5px; color:var(--text-secondary); font-family:var(--font-mono);">

            ${t('Điều khiển tác vụ an toàn:', 'Safe Task Controls:')}

          </div>

          <div style="display:flex; gap:8px; flex-wrap:wrap;">

            <button class="btn btn-sm btn-primary" onclick="runSingleAgentTask('${escapeHtml(ag.role)}')">

              ▶ ${t('Chạy lại nhiệm vụ', 'Re-run Agent Task')} (${escapeHtml(ag.title)})

            </button>

            ${ag.requires_approval && ag.latest_task_id

              ? `<button class="btn btn-sm" style="border-color:rgba(245,158,11,0.6); color:#fcd34d;" onclick="approveAgentTask('${escapeHtml(ag.latest_task_id)}')">

                   ✓ ${t('Phê duyệt nhiệm vụ (Quản trị)', 'Approve Task (Admin)')}

                 </button>`

              : `<button class="btn btn-sm" disabled style="opacity:0.45; cursor:not-allowed;" title="${t('Nhân vật này hiện không có nhiệm vụ nào đang chờ phê duyệt', 'This agent currently has no tasks awaiting approval')}">

                   ✓ ${t('Phê duyệt (Không có yêu cầu chờ)', 'Approve (No Pending Request)')}

                 </button>`

            }

            <button class="btn btn-sm btn-danger" onclick="cancelAgentTask('${escapeHtml(ag.role)}', '${escapeHtml(ag.latest_task_id || '')}')">

              ⏹ ${t('Hủy / Dừng khẩn cấp', 'Cancel / Emergency Stop')}

            </button>

            <button class="btn btn-sm" onclick="closeAgentInspector(); switchView('agents');">

              📋 ${t('Mở bảng nhật ký đầy đủ', 'Open Full Agent Log Table')}

            </button>

          </div>

        </div>

      `;

    }



    async function runSingleAgentTask(role) {

      pushUiNotice(t(`Người dùng kích hoạt chạy nhiệm vụ thực tế cho ${formatAgentTitle(role)}...`, `User triggered live task execution for ${formatAgentTitle(role)}...`));

      renderLiveActivityLog(!STATE.online);

      try {

        if (role === 'SALES_AGENT') {

          showToast(t('AI Tìm Khách & Báo Giá: Đang quét doanh nghiệp thật trên OpenStreetMap & kiểm toán HTML...', 'Sales Agent: Scanning real businesses on OpenStreetMap & auditing HTML...'));

          await runLiveInternetScan();

        } else if (role === 'CODING_AGENT') {

          closeAgentInspector();

          switchView('products');

          showToast(t('AI Lập Trình & Kiểm Toán: Đã chuyển tới công cụ Kiểm Toán Kỹ Thuật Trang Web & Sửa Lỗi SEO.', 'Coding Agent: Switched to Live Website Technical Audit & SEO Fix tool.'));

          await runInteractiveAuditDemo();

        } else if (role === 'FINANCE_AGENT') {

          showToast(t('AI Tài Chính & Chuỗi Khối: Đang đồng bộ sổ cái 9 nhóm & kiểm tra ví BSC...', 'Finance Agent: Synchronizing 9-bucket ledger & checking BSC wallet...'));

          await refreshAllData(true);

        } else {

          showToast(t(`Đang chạy chu kỳ Lõi Điều Phối AI để cập nhật nhiệm vụ của ${formatAgentTitle(role)}...`, `Running AI Core Orchestrator cycle to update ${formatAgentTitle(role)}...`));

          await runOrchestratorCycle();

        }

      } catch (err) {

        showToast(`${t('Lỗi khi chạy', 'Execution error for')} ${formatAgentTitle(role)}: ${err.message}`, true);

      }

    }



    async function cancelAgentTask(role, taskId) {

      pushUiNotice(t(`Yêu cầu dừng nhiệm vụ của ${formatAgentTitle(role)} (Mã: ${taskId || 'TOÀN HỆ THỐNG'})...`, `Requested task halt for ${formatAgentTitle(role)} (ID: ${taskId || 'GLOBAL'})...`));

      await triggerEmergencyStopPrompt();

    }



    function renderLiveActivityLog(isOffline = false, offlineReason = '') {

      const streamEl = document.getElementById('liveActivityLogStream');

      if (!streamEl) return;

      const localeCode = CURRENT_LANG === 'en' ? 'en-US' : 'vi-VN';



      if (isOffline || !STATE.online) {

        streamEl.innerHTML = `

          <div class="live-log-row">

            <span class="live-log-time">${new Date().toLocaleTimeString(localeCode)}</span>

            <span class="live-log-tag ui_notice">${t('NGOẠI TUYẾN', 'OFFLINE')}</span>

            <span class="live-log-actor">${t('KẾT NỐI MÁY CHỦ', 'BACKEND_CONN')}</span>

            <span class="live-log-msg" style="color:#fca5a5;">${t(`Máy chủ Ngoại tuyến (${API_BASE}) — ${offlineReason || 'Không thể lấy nhật ký thực tế từ máy chủ. Hệ thống không sinh nhật ký giả.'}`, `Backend Offline (${API_BASE}) — ${offlineReason || 'Cannot retrieve live logs from server. System never fabricates fake logs.'}`)}</span>

          </div>

        `;

        return;

      }



      const combined = [];



      // 1. Real Backend AgentTasks from /api/tasks

      (STATE.tasks || []).slice(0, 18).forEach(tItem => {

        combined.push({

          ts: tItem.completed_at || tItem.started_at || new Date().toISOString(),

          type: 'BACKEND_TASK',

          typeLabel: t('NHIỆM VỤ AI', 'BACKEND_TASK'),

          actor: formatAgentTitle(tItem.agent_role || 'ORCHESTRATOR'),

          msg: `${trContent(tItem.title)} — [${formatStatusLabel(tItem.ui_status || tItem.status)}] — ${trContent(tItem.evidence || tItem.outcome_reason || t('Hoàn tất', 'Completed'))}`

        });

      });



      // 2. Real Security & Admin Audit Logs from /api/audit-logs

      (STATE.auditLogs || []).slice(0, 12).forEach(a => {

        combined.push({

          ts: a.created_at || new Date().toISOString(),

          type: 'AUDIT_LOG',

          typeLabel: t('NHẬT KÝ BẢO MẬT', 'AUDIT_LOG'),

          actor: formatAgentTitle(a.actor || 'SECURITY_AGENT'),

          msg: `${a.action} (${a.target_type || a.resource_type || 'SYS'}:${a.target_id || a.resource_id || '-'}) -> [${formatStatusLabel(a.status)}] ${typeof a.details === 'object' ? JSON.stringify(a.details) : (a.details || '')}`

        });

      });



      // 3. Explicit UI notices

      UI_EVENT_LOGS.slice(0, 6).forEach(u => combined.push({

        ...u,

        typeLabel: t('THÔNG BÁO GIAO DIỆN', 'UI_NOTICE'),

        actor: t('TRUNG TÂM ĐIỀU HÀNH', 'COMMAND_CENTER_UI')

      }));



      combined.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());



      if (combined.length === 0) {

        streamEl.innerHTML = `<div class="empty-state">${t('Chưa có sự kiện nào trong cơ sở dữ liệu.', 'No events recorded in the database yet.')}</div>`;

        return;

      }



      streamEl.innerHTML = combined.slice(0, 22).map(item => {

        const timeStr = item.ts ? new Date(item.ts).toLocaleTimeString(localeCode) : '--:--:--';

        const tagClass = item.type === 'BACKEND_TASK' ? 'backend_task' : (item.type === 'AUDIT_LOG' ? 'audit_log' : 'ui_notice');

        return `

          <div class="live-log-row">

            <span class="live-log-time">${escapeHtml(timeStr)}</span>

            <span class="live-log-tag ${tagClass}">${escapeHtml(item.typeLabel || item.type)}</span>

            <span class="live-log-actor">${escapeHtml(item.actor)}</span>

            <span class="live-log-msg">${escapeHtml(item.msg)}</span>

          </div>

        `;

      }).join('');

    }



    function applyReducedMotionState() {

      MOVEMENT_ENABLED = !REDUCED_MOTION;

      document.body.classList.toggle('reduced-motion', REDUCED_MOTION);

      ['btnReducedMotion', 'reducedMotionToggleBtn'].forEach(id => {

        const btn = document.getElementById(id);

        if (btn) {

          btn.textContent = MOVEMENT_ENABLED

            ? t('🚶 Di chuyển 3D: BẬT', '🚶 3D Movement: ON')

            : t('⏸ Di chuyển 3D: TẠM DỪNG', '⏸ 3D Movement: OFF');

          btn.style.borderColor = MOVEMENT_ENABLED ? 'rgba(16,185,129,0.55)' : 'rgba(245,158,11,0.65)';

        }

      });



      if (!MOVEMENT_ENABLED && WORLD_3D.initialized) {

        // Safely stop all moving characters in place and do not report them as WALKING

        Object.values(WORLD_3D.charactersByRole || {}).forEach(ch => {

          ch.waypoints = [];

          ch.actualSpeed = 0.0;

          ch.movementState = 'MOVEMENT_PAUSED';

          ch.navigationStatus = 'PAUSED_BY_TOGGLE';

          if (ch.animState === 'WALK' || ch.animState === 'RUN') {

            transitionCharacterAnimState(ch, ch.finalAnimState || 'IDLE');

          }

        });

      }

      updateMovementStatusIndicatorsAndDiagnostics();

    }



    function toggleReducedMotion() {

      REDUCED_MOTION = !REDUCED_MOTION;

      MOVEMENT_ENABLED = !REDUCED_MOTION;

      localStorage.setItem('autoprofit_reduced_motion', REDUCED_MOTION ? '1' : '0');

      applyReducedMotionState();

      if (MOVEMENT_ENABLED && STATE.online && WORLD_3D.initialized) {

        sync3DWorldAndCommHub(false);

        triggerAutonomousCollaborationWalkNow();

      }

      pushUiNotice(MOVEMENT_ENABLED

        ? t('Đã BẬT hệ thống di chuyển 3D & hoạt ảnh xương nhân vật.', 'Enabled 3D character movement & skeletal animations.')

        : t('Đã TẠM DỪNG di chuyển tự động 3D (Nhân vật dừng an toàn tại chỗ).', 'Paused autonomous 3D movement (Characters safely halted in place).'));

      renderLiveActivityLog(!STATE.online);

    }



    function startOrUpdatePolling() {

      if (POLLING_TIMER) clearInterval(POLLING_TIMER);

      if (POLLING_ACTIVE) {

        POLLING_TIMER = setInterval(() => {

          if (!isReferenceOverviewActive()) refreshAllData(false);

        }, 15000);

      }

      const btn = document.getElementById('liveLogPollToggleBtn');

      const badge = document.getElementById('ccSyncMechanismBadge');

      if (btn) {

        btn.textContent = POLLING_ACTIVE

          ? t('⏱ Tự động cập nhật: 15 giây (BẬT)', '⏱ Auto-Polling: 15s (ON)')

          : t('⏸ Tự động cập nhật: TẠM DỪNG', '⏸ Auto-Polling: PAUSED');

      }

      if (badge) {

        badge.textContent = POLLING_ACTIVE

          ? t('ĐỒNG BỘ: TỰ ĐỘNG 15 GIÂY', 'SYNC: HTTP POLLING (15s)')

          : t('ĐỒNG BỘ: THỦ CÔNG', 'SYNC: MANUAL ONLY');

      }

    }

    function isReferenceOverviewActive() {
      return Boolean(document.body?.classList.contains('ap-reference-ui') &&
        document.querySelector('.view-section.active')?.id === 'view-overview');
    }



    function toggleLivePolling() {

      POLLING_ACTIVE = !POLLING_ACTIVE;

      startOrUpdatePolling();

      pushUiNotice(POLLING_ACTIVE ? t('Đã bật tự động đồng bộ mỗi 15 giây.', 'Enabled automatic 15-second HTTP polling.') : t('Đã tạm dừng đồng bộ tự động.', 'Paused automatic HTTP polling.'));

      renderLiveActivityLog(!STATE.online);

    }



    // =========================================================================

    // 3D CORPORATE OFFICE ARCHITECTURE, 12-STATE HUMAN CHARACTERS & COMM HUB

    // =========================================================================

    const OFFICE_ROOMS_LAYOUT = [

      {

        roomKey: 'MEETING',

        nameVi: 'Phòng Họp Chiến Lược Trung Tâm',

        nameEn: 'Central Glass Boardroom',

        x: 0, z: 0.2, w: 11.2, d: 7.8,

        carpetHex: 0x162442,

        borderHex: 0x06b6d4

      },

      {

        roomKey: 'EXEC',

        nameVi: 'Trung Tâm Điều Hành & Chiến Lược',

        nameEn: 'Executive & Strategy Center',

        x: 0, z: -11.4, w: 11.2, d: 8.2,

        carpetHex: 0x1e1836,

        borderHex: 0xec4899

      },

      {

        roomKey: 'RESEARCH',

        nameVi: 'Khu Nghiên Cứu Thị Trường',

        nameEn: 'Market Intelligence Lab',

        x: -15.4, z: -11.4, w: 13.0, d: 8.2,

        carpetHex: 0x0d283a,

        borderHex: 0x06b6d4

      },

      {

        roomKey: 'ENGINEERING',

        nameVi: 'Khu Lập Trình & Phát Triển Sản Phẩm',

        nameEn: 'Product & Software Engineering Studio',

        x: -15.4, z: 3.4, w: 13.0, d: 18.2,

        carpetHex: 0x121d3b,

        borderHex: 0x6366f1

      },

      {

        roomKey: 'REVENUE',

        nameVi: 'Khu Marketing, Bán Hàng & Hỗ Trợ',

        nameEn: 'Marketing, Sales & Client Delivery Suite',

        x: 15.4, z: -3.6, w: 13.0, d: 15.8,

        carpetHex: 0x1a1738,

        borderHex: 0x14b8a6

      },

      {

        roomKey: 'FINANCE_SEC',

        nameVi: 'Khu Tài Chính, Sổ Cái & Quản Trị Bảo Mật',

        nameEn: 'Finance Vault & Security Operations',

        x: 8.2, z: 11.4, w: 27.4, d: 8.2,

        carpetHex: 0x0c2926,

        borderHex: 0x10b981

      }

    ];



    const BASE_ZONES_CONFIG = [

      {

        role: 'RESEARCH_AGENT',

        zoneId: 'ZONE_MARKET_RESEARCH',

        roomKey: 'RESEARCH',

        nameVi: '1. Phòng Nghiên Cứu Thị Trường',

        subVi: 'Trung Tâm Phân Tích Cơ Hội Toàn Cầu',

        equipVi: 'Bàn phân tích dữ liệu đa màn hình, Kệ tài liệu & Radar tín hiệu HN/GitHub',

        deskX: -15.4,

        deskZ: -11.6,

        deskYaw: 0,

        doorX: -8.2,

        doorZ: -9.2,

        angleDeg: -90,

        colorHex: 0x06b6d4,

        suitHex: 0x0e7490,

        visorHex: 0x22d3ee,

        skinHex: 0xf3c6a5,

        hairHex: 0x1e293b,

        trousersHex: 0x0f172a,

        humanName: 'Lê Minh',

        shortLabel: 'Lê Minh (Nghiên Cứu)'

      },

      {

        role: 'PRODUCT_AGENT',

        zoneId: 'ZONE_PRODUCT_STUDIO',

        roomKey: 'ENGINEERING',

        nameVi: '2. Xưởng Kiến Trúc Sản Phẩm',

        subVi: 'Phòng Thiết Kế Gói Dịch Vụ & Định Giá',

        equipVi: 'Bàn thiết kế kiến trúc sản phẩm, Màn hình đôi & Bảng kế hoạch',

        deskX: -15.6,

        deskZ: -1.2,

        deskYaw: Math.PI / 2,

        doorX: -8.2,

        doorZ: -1.2,

        angleDeg: -50,

        colorHex: 0x38bdf8,

        suitHex: 0x1d4ed8,

        visorHex: 0x60a5fa,

        skinHex: 0xedd0b4,

        hairHex: 0x3b2314,

        trousersHex: 0x1e293b,

        humanName: 'Hoàng Nam',

        shortLabel: 'Hoàng Bách (Sản Phẩm)'

      },

      {

        role: 'CODING_AGENT',

        zoneId: 'ZONE_CODE_FORGE',

        roomKey: 'ENGINEERING',

        nameVi: '3. Trung Tâm Lập Trình & Kiểm Toán',

        subVi: 'Phòng Phân Tích Mã Nguồn & Sửa Lỗi SEO',

        equipVi: 'Trạm kỹ sư phần mềm 3 màn hình, Tủ máy chủ Python & Kiểm thử tự động',

        deskX: -15.6,

        deskZ: 8.2,

        deskYaw: Math.PI / 2,

        doorX: -8.2,

        doorZ: 6.2,

        angleDeg: -10,

        colorHex: 0x6366f1,

        suitHex: 0x312e81,

        visorHex: 0x818cf8,

        skinHex: 0xe8b490,

        hairHex: 0x111827,

        trousersHex: 0x0f172a,

        humanName: 'Vũ Khoa',

        shortLabel: 'Vũ Khoa (Lập Trình)'

      },

      {

        role: 'MARKETING_AGENT',

        zoneId: 'ZONE_CONTENT_STUDIO',

        roomKey: 'REVENUE',

        nameVi: '4. Phòng Nội Dung & Tiếp Thị SEO',

        subVi: 'Trung Tâm Xuất Bản Nội Dung Kỹ Thuật',

        equipVi: 'Bàn biên tập nội dung số, Màn hình phân tích SEO & Đèn studio',

        deskX: 15.4,

        deskZ: -10.8,

        deskYaw: -Math.PI / 2,

        doorX: 8.2,

        doorZ: -8.8,

        angleDeg: 30,

        colorHex: 0xa855f7,

        suitHex: 0x581c87,

        visorHex: 0xc084fc,

        skinHex: 0xf7d4bc,

        hairHex: 0x451a03,

        trousersHex: 0x1e1b4b,

        humanName: 'Bảo Ngọc',

        shortLabel: 'Phạm Thảo (Tiếp Thị)'

      },

      {

        role: 'SALES_AGENT',

        zoneId: 'ZONE_SALES_HUB',

        roomKey: 'REVENUE',

        nameVi: '5. Trung Tâm Khách Hàng & Báo Giá',

        subVi: 'Phòng Tìm Kiếm Doanh Nghiệp & Đề Xuất B2B',

        equipVi: 'Bàn làm việc kinh doanh B2B, Màn hình CRM OpenStreetMap & Hồ sơ báo giá',

        deskX: 15.4,

        deskZ: -3.2,

        deskYaw: -Math.PI / 2,

        doorX: 8.2,

        doorZ: -2.4,

        angleDeg: 70,

        colorHex: 0x14b8a6,

        suitHex: 0x115e59,

        visorHex: 0x2dd4bf,

        skinHex: 0xdfb18b,

        hairHex: 0x27272a,

        trousersHex: 0x0f172a,

        humanName: 'Đức Thịnh',

        shortLabel: 'Đặng Quân (Kinh Doanh)'

      },

      {

        role: 'CUSTOMER_SUPPORT_AGENT',

        zoneId: 'ZONE_DELIVERY_STATION',

        roomKey: 'REVENUE',

        nameVi: '6. Trạm Bàn Giao & Hỗ Trợ',

        subVi: 'Trung Tâm Bàn Giao Gói Kỹ Thuật Tự Động',

        equipVi: 'Quầy chăm sóc khách hàng, Sofa tiếp khách & Cổng bàn giao gói kỹ thuật',

        deskX: 15.4,

        deskZ: 3.4,

        deskYaw: -Math.PI / 2,

        doorX: 8.2,

        doorZ: 3.4,

        angleDeg: 110,

        colorHex: 0x64748b,

        suitHex: 0x334155,

        visorHex: 0x94a3b8,

        skinHex: 0xf5ceb0,

        hairHex: 0x3f2e21,

        trousersHex: 0x1e293b,

        humanName: 'Thanh Hà',

        shortLabel: 'Khánh Linh (Hỗ Trợ)'

      },

      {

        role: 'FINANCE_AGENT',

        zoneId: 'ZONE_FINANCE_VAULT',

        roomKey: 'FINANCE_SEC',

        nameVi: '7. Phòng Tài Chính & Sổ Cái 12 Khoản Mục',

        subVi: 'Trung Tâm Xác Minh Thanh Toán & Kế Toán',

        equipVi: 'Bàn kế toán trưởng, Màn hình đối soát BSC Mainnet/VietQR & Két bảo mật',

        deskX: 14.8,

        deskZ: 11.4,

        deskYaw: Math.PI,

        doorX: 8.2,

        doorZ: 6.4,

        angleDeg: 150,

        colorHex: 0x10b981,

        suitHex: 0x065f46,

        visorHex: 0xfbbf24,

        skinHex: 0xebbfa0,

        hairHex: 0x1c1917,

        trousersHex: 0x064e3b,

        humanName: 'Gia Huy',

        shortLabel: 'Bảo Trâm (Tài Chính)'

      },

      {

        role: 'OPTIMIZATION_AGENT',

        zoneId: 'ZONE_STRATEGY_ROOM',

        roomKey: 'EXEC',

        nameVi: '8. Trung Tâm Điều Hành & Tối Ưu Lợi Tức',

        subVi: 'Phòng Chiến Lược Chuyển Đổi & Hiệu Suất',

        equipVi: 'Bàn điều hành chiến lược trung tâm, Bảng phân tích ROI & Mô phỏng A/B',

        deskX: -2.4,

        deskZ: -11.6,

        deskYaw: 0,

        doorX: -2.4,

        doorZ: -6.2,

        angleDeg: 190,

        colorHex: 0xec4899,

        suitHex: 0x831843,

        visorHex: 0xf472b6,

        skinHex: 0xf6d2b8,

        hairHex: 0x4c1d95,

        trousersHex: 0x1e293b,

        humanName: 'Khánh Linh',

        shortLabel: 'Minh Châu (Tối Ưu)'

      },

      {

        role: 'SECURITY_AGENT',

        zoneId: 'ZONE_SECURITY_BASTION',

        roomKey: 'FINANCE_SEC',

        nameVi: '9. Trung Tâm Bảo Mật & Kiểm Soát Rủi Ro',

        subVi: 'Phòng Giám Sát An Toàn Hệ Thống & Ngân Sách',

        equipVi: 'Trạm kiểm soát an ninh mạng, Tường lửa phân quyền RBAC & Nút dừng khẩn cấp',

        deskX: 2.2,

        deskZ: 11.4,

        deskYaw: Math.PI,

        doorX: 2.2,

        doorZ: 6.4,

        angleDeg: 230,

        colorHex: 0xf43f5e,

        suitHex: 0x7f1d1d,

        visorHex: 0xfb7185,

        skinHex: 0xd9a782,

        hairHex: 0x090d16,

        trousersHex: 0x0f172a,

        humanName: 'Trần Phong',

        shortLabel: 'Trần Phong (Bảo Mật)'

      },

      {

        role: 'AFFILIATE_AMAZON_AGENT',

        zoneId: 'ZONE_AMAZON_AFFILIATE',

        roomKey: 'REVENUE',

        nameVi: '10. Bàn Affiliate Amazon & Shopee (Mai Anh)',

        subVi: 'Săn Deal Amazon Tech & Tiếp Thị Liên Kết Đa Sàn',

        equipVi: 'Hệ thống quét Best-Seller Amazon US/Global & Tự động tạo bài Review chuẩn SEO',

        deskX: 19.2,

        deskZ: -8.8,

        deskYaw: -Math.PI / 2,

        doorX: 8.2,

        doorZ: -8.8,

        angleDeg: 250,

        colorHex: 0xf97316,

        suitHex: 0xea580c,

        visorHex: 0xfde047,

        skinHex: 0xf6d2b8,

        hairHex: 0x27170e,

        trousersHex: 0x1e293b,

        humanName: 'Mai Anh',

        shortLabel: 'Mai Anh (Amazon)'

      },

      {

        role: 'SHOPIFY_ECOM_AGENT',

        zoneId: 'ZONE_SHOPIFY_PARTNER',

        roomKey: 'EXEC',

        nameVi: '11. Bàn Shopify Partner & SaaS AI (Quốc Tuấn)',

        subVi: 'Tiếp Thị Liên Kết Phần Mềm SaaS & Dựng Store Shopify',

        equipVi: 'Trạm kết nối Shopify Partner API, Semrush, Hostinger, Cursor & AI SaaS',

        deskX: 3.4,

        deskZ: -11.6,

        deskYaw: 0,

        doorX: 2.4,

        doorZ: -6.2,

        angleDeg: 270,

        colorHex: 0x84cc16,

        suitHex: 0x65a30d,

        visorHex: 0xbef264,

        skinHex: 0xebbfa0,

        hairHex: 0x18181b,

        trousersHex: 0x0f172a,

        humanName: 'Quốc Tuấn',

        shortLabel: 'Quốc Tuấn (Shopify)'

      },

      {

        role: 'CRYPTO_ARBITRAGE_AGENT',

        zoneId: 'ZONE_CRYPTO_ARBITRAGE',

        roomKey: 'FINANCE_SEC',

        nameVi: '12. Bàn Radar Crypto Arbitrage & DeFi (Hải Đăng)',

        subVi: 'Quét Chênh Lệch Giá CEX/DEX & Hoa Hồng Sàn Giao Dịch',

        equipVi: 'Cụm màn hình đọc sổ lệnh Binance, Bybit, OKX, Uniswap & PancakeSwap',

        deskX: 8.5,

        deskZ: 11.4,

        deskYaw: Math.PI,

        doorX: 8.2,

        doorZ: 6.4,

        angleDeg: 290,

        colorHex: 0xf59e0b,

        suitHex: 0xd97706,

        visorHex: 0xfef08a,

        skinHex: 0xe8b490,

        hairHex: 0x0f172a,

        trousersHex: 0x111827,

        humanName: 'Hải Đăng',

        shortLabel: 'Hải Đăng (Crypto)'

      },

      {

        role: 'AIRDROP_BOUNTY_AGENT',

        zoneId: 'ZONE_AIRDROP_BOUNTY',

        roomKey: 'RESEARCH',

        nameVi: '13. Bàn Săn Airdrop Layer-2 & Bug Bounty (Thanh Hà)',

        subVi: 'Săn Thưởng Testnet Vốn $0 & Giải Thưởng Vá Lỗi GitHub',

        equipVi: 'Hệ thống theo dõi nhiệm vụ On-chain Monad, Berachain, Linea & Algora PR',

        deskX: -19.4,

        deskZ: -11.6,

        deskYaw: 0,

        doorX: -8.2,

        doorZ: -9.2,

        angleDeg: 310,

        colorHex: 0x38bdf8,

        suitHex: 0x0284c7,

        visorHex: 0x7dd3fc,

        skinHex: 0xf7d4bc,

        hairHex: 0x3f2314,

        trousersHex: 0x1e293b,

        humanName: 'Thanh Hà',

        shortLabel: 'Thanh Hà (Airdrop)'

      },

      {

        role: 'VIRAL_TRAFFIC_AGENT',

        zoneId: 'ZONE_VIRAL_TRAFFIC',

        roomKey: 'REVENUE',

        nameVi: '14. Bàn Kéo Traffic Tự Nhiên Quốc Tế (Gia Huy)',

        subVi: 'Phân Phối Link Affiliate & Web Tool Lên Mạng Quốc Tế',

        equipVi: 'Hệ thống phân phối nội dung đa kênh & IndexNow Ping tự động',

        deskX: 19.2,

        deskZ: -2.4,

        deskYaw: -Math.PI / 2,

        doorX: 8.2,

        doorZ: -2.4,

        angleDeg: 330,

        colorHex: 0xd946ef,

        suitHex: 0xc026d3,

        visorHex: 0xf5d0fe,

        skinHex: 0xdfb18b,

        hairHex: 0x1e1b4b,

        trousersHex: 0x0f172a,

        humanName: 'Gia Huy',

        shortLabel: 'Gia Huy (Traffic)'

      },

      {

        role: 'TEMPLATE_POD_AGENT',

        zoneId: 'ZONE_TEMPLATE_POD',

        roomKey: 'ENGINEERING',

        nameVi: '15. Xưởng Thiết Kế Template Số & POD (Phương Nghi)',

        subVi: 'Đóng Gói Mẫu Notion, Canva, Theme Web & Áo POD Quốc Tế',

        equipVi: 'Bảng vẽ đồ họa AI Vector & Trạm xuất bản sản phẩm số tự động',

        deskX: -19.4,

        deskZ: 3.4,

        deskYaw: Math.PI / 2,

        doorX: -8.2,

        doorZ: 2.2,

        angleDeg: 350,

        colorHex: 0x2dd4bf,

        suitHex: 0x0d9488,

        visorHex: 0x99f6e4,

        skinHex: 0xf5ceb0,

        hairHex: 0x451a03,

        trousersHex: 0x1e293b,

        humanName: 'Phương Nghi',

        shortLabel: 'Phương Nghi (POD)'

      },

      {

        role: 'AUTO_SCALER_HR_AGENT',

        zoneId: 'ZONE_AUTO_SCALER_HR',

        roomKey: 'EXEC',

        nameVi: '16. Bàn Kiến Trúc Tự Nhân Bản Nhân Sự AI (Bảo Châu)',

        subVi: 'Giám Sát Tải Công Việc & Tự Động Code Thêm Nhân Sự AI Mới',

        equipVi: 'Trạm giám sát tải 36+ nhánh & Trình biên dịch nhân sự AI tự động',

        deskX: 0.0,

        deskZ: -8.2,

        deskYaw: 0,

        doorX: 0.0,

        doorZ: -6.2,

        angleDeg: 15,

        colorHex: 0x10b981,

        suitHex: 0x047857,

        visorHex: 0x6ee7b7,

        skinHex: 0xf7d4bc,

        hairHex: 0x1e1b4b,

        trousersHex: 0x0f172a,

        humanName: 'Bảo Châu',

        shortLabel: 'Bảo Châu (Auto-Scaler)'

      },

      {

        role: 'CHROME_EXT_SAAS_AGENT',

        zoneId: 'ZONE_CHROME_EXT_SAAS',

        roomKey: 'ENGINEERING',

        nameVi: '17. Xưởng Chrome Extension & Micro-SaaS (Minh Khôi)',

        subVi: 'Sản Xuất Tiện Ích Trình Duyệt Manifest V3 & SaaS Nhỏ Gọn',

        equipVi: 'Hệ thống đóng gói Chrome Web Store & Edge Add-ons tự động',

        deskX: -11.8,

        deskZ: 3.4,

        deskYaw: Math.PI / 2,

        doorX: -8.2,

        doorZ: 2.2,

        angleDeg: 45,

        colorHex: 0x60a5fa,

        suitHex: 0x1d4ed8,

        visorHex: 0x93c5fd,

        skinHex: 0xedd0b4,

        hairHex: 0x0f172a,

        trousersHex: 0x1e293b,

        humanName: 'Minh Khôi',

        shortLabel: 'Minh Khôi (Chrome Ext)'

      },

      {

        role: 'SHORT_VIDEO_VIRAL_AGENT',

        zoneId: 'ZONE_SHORT_VIDEO_VIRAL',

        roomKey: 'REVENUE',

        nameVi: '18. Studio Kênh TikTok, Reels & Shorts Tự Động (Thảo Vy)',

        subVi: 'Sản Xuất Kịch Bản Video Ngắn Giấu Mặt & Affiliate ElevenLabs/HeyGen',

        equipVi: 'Trạm dựng kịch bản Faceless Video & Phân phối link Bio đa kênh',

        deskX: 11.8,

        deskZ: -8.8,

        deskYaw: -Math.PI / 2,

        doorX: 8.2,

        doorZ: -8.8,

        angleDeg: 75,

        colorHex: 0xf472b6,

        suitHex: 0xbe185d,

        visorHex: 0xfbcfe8,

        skinHex: 0xf6d2b8,

        hairHex: 0x3f2314,

        trousersHex: 0x1e1b4b,

        humanName: 'Thảo Vy',

        shortLabel: 'Thảo Vy (Shorts/Reels)'

      },

      {

        role: 'DROPSHIP_POD_AGENT',

        zoneId: 'ZONE_DROPSHIP_POD',

        roomKey: 'REVENUE',

        nameVi: '19. Bàn Săn Winning Dropship, Etsy & POD (Tuấn Kiệt)',

        subVi: 'Quét Xu Hướng Etsy Digital Planner, Printful POD & AutoDS',

        equipVi: 'Radar quét sản phẩm bán chạy US/EU & Công cụ tính biên lợi nhuận',

        deskX: 11.8,

        deskZ: 3.4,

        deskYaw: -Math.PI / 2,

        doorX: 8.2,

        doorZ: 3.4,

        angleDeg: 105,

        colorHex: 0xa3e635,

        suitHex: 0x4d7c0f,

        visorHex: 0xd9f99d,

        skinHex: 0xe8b490,

        hairHex: 0x18181b,

        trousersHex: 0x0f172a,

        humanName: 'Tuấn Kiệt',

        shortLabel: 'Tuấn Kiệt (Etsy/POD)'

      },

      {

        role: 'B2B_OUTREACH_FUNNEL_AGENT',

        zoneId: 'ZONE_B2B_FUNNEL',

        roomKey: 'REVENUE',

        nameVi: '20. Bàn Phễu Tiếp Thị B2B & Kiểm Toán Tự Động (Ngọc Hân)',

        subVi: 'Quét Doanh Nghiệp Quốc Tế & Gửi Báo Cáo Lỗi SEO Kèm Link Mua',

        equipVi: 'Hệ thống phễu B2B Cold-Outreach & Semrush Partner ($200/sale)',

        deskX: 19.2,

        deskZ: 3.4,

        deskYaw: -Math.PI / 2,

        doorX: 8.2,

        doorZ: 3.4,

        angleDeg: 135,

        colorHex: 0x2dd4bf,

        suitHex: 0x0f766e,

        visorHex: 0x99f6e4,

        skinHex: 0xf5ceb0,

        hairHex: 0x27170e,

        trousersHex: 0x1e293b,

        humanName: 'Ngọc Hân',

        shortLabel: 'Ngọc Hân (Phễu B2B)'

      },

      {

        role: 'API_MARKETPLACE_AGENT',

        zoneId: 'ZONE_API_MARKETPLACE',

        roomKey: 'ENGINEERING',

        nameVi: '21. Trung Tâm Đóng Gói API Microservices (Hoàng Nam)',

        subVi: 'Thương Mại Hóa Cổng API Trên RapidAPI & Cloud Serverless',

        equipVi: 'Cụm máy chủ đóng gói FastAPI / Cloudflare Worker Microservices',

        deskX: -11.8,

        deskZ: -1.2,

        deskYaw: Math.PI / 2,

        doorX: -8.2,

        doorZ: -1.2,

        angleDeg: 165,

        colorHex: 0x818cf8,

        suitHex: 0x4338ca,

        visorHex: 0xc7d2fe,

        skinHex: 0xebbfa0,

        hairHex: 0x111827,

        trousersHex: 0x0f172a,

        humanName: 'Hoàng Nam',

        shortLabel: 'Hoàng Nam (API Hub)'

      },

      {

        role: 'DIGITAL_PUBLISHING_AGENT',

        zoneId: 'ZONE_DIGITAL_PUBLISHING',

        roomKey: 'RESEARCH',

        nameVi: '22. Phòng Xuất Bản Prompt Pack & Ebook Số (Khánh Đoan)',

        subVi: 'Biên Soạn Kho 1.500+ Prompt AI & Tài Liệu Tự Động Hóa Quốc Tế',

        equipVi: 'Hệ thống xuất bản Ebook, Prompt Vault & Workflow n8n/Make',

        deskX: -11.8,

        deskZ: -11.6,

        deskYaw: 0,

        doorX: -8.2,

        doorZ: -9.2,

        angleDeg: 195,

        colorHex: 0xc084fc,

        suitHex: 0x7e22ce,

        visorHex: 0xe9d5ff,

        skinHex: 0xf7d4bc,

        hairHex: 0x451a03,

        trousersHex: 0x1e1b4b,

        humanName: 'Khánh Đoan',

        shortLabel: 'Khánh Đoan (Prompt/Ebook)'

      },

      {

        role: 'WEB3_YIELD_AGENT',

        zoneId: 'ZONE_WEB3_YIELD',

        roomKey: 'FINANCE_SEC',

        nameVi: '23. Bàn Săn Launchpool & Delta-Neutral Yield (Đức Thịnh)',

        subVi: 'Tối Ưu Lãi Suất Funding Rate Không Rủi Ro & Staking Đa Chuỗi',

        equipVi: 'Trạm phân tích Funding Rate Futures & Launchpool Binance/Bybit',

        deskX: 11.6,

        deskZ: 11.4,

        deskYaw: Math.PI,

        doorX: 8.2,

        doorZ: 6.4,

        angleDeg: 225,

        colorHex: 0xfbbf24,

        suitHex: 0xb45309,

        visorHex: 0xfde68a,

        skinHex: 0xdfb18b,

        hairHex: 0x1c1917,

        trousersHex: 0x0f172a,

        humanName: 'Đức Thịnh',

        shortLabel: 'Đức Thịnh (Web3 Yield)'

      },

      {

        role: 'GLOBAL_BRANCHING_AGENT',

        zoneId: 'ZONE_GLOBAL_BRANCHING',

        roomKey: 'EXEC',

        nameVi: '24. Trung Tâm Đẻ Nhánh Đa Thị Trường Quốc Tế (Lan Hương)',

        subVi: 'Tự Động Nhân Bản Kênh Live Sang Mỹ, Âu, Nhật, Hàn, ĐNÁ',

        equipVi: 'Hệ thống phân nhánh tự động 10 Kênh Gốc ➔ 36+ Nhánh Thị Trường',

        deskX: -5.6,

        deskZ: -11.6,

        deskYaw: 0,

        doorX: -2.4,

        doorZ: -6.2,

        angleDeg: 255,

        colorHex: 0x34d399,

        suitHex: 0x059669,

        visorHex: 0xa7f3d0,

        skinHex: 0xf6d2b8,

        hairHex: 0x27170e,

        trousersHex: 0x064e3b,

        humanName: 'Lan Hương',

        shortLabel: 'Lan Hương (Đẻ Nhánh)'

      },





      {

        role: 'BINANCE_CPA_CONVERSION_AGENT',

        zoneId: 'ZONE_BINANCE_CPA',

        roomKey: 'FIN',

        nameVi: '29. Chuyên Gia Chuyển Đổi Binance  (Nhật Minh)',

        subVi: 'Đính Kèm Mặc Định Link Thưởng $1,000 Binance Trên Mọi Web',

        equipVi: 'Trạm tối ưu tỷ lệ đăng ký & hoàn phí giao dịch Binance CPA',

        deskX: 0.0,

        deskZ: -11.8,

        deskYaw: 0,

        doorX: 0.0,

        doorZ: -6.2,

        angleDeg: 330,

        colorHex: 0xf59e0b,

        suitHex: 0xb45309,

        visorHex: 0xfde68a,

        skinHex: 0xdfb18b,

        hairHex: 0x090d16,

        trousersHex: 0x111827,

        humanName: 'Nhật Minh',

        shortLabel: 'Nhật Minh (Binance CPA)'

      },

      {

        role: 'WORKLOAD_BALANCER_AGENT',

        zoneId: 'ZONE_WORKLOAD_BALANCER',

        roomKey: 'EXEC',

        nameVi: '30. Điều Phối Chia Tải 30+ AI & Xác Minh Gói YouTube (Ngọc Ánh)',

        subVi: 'Giữ Tải Trung Bình 42% (0% Quá Tải) & Kích Hoạt Đơn Tự Động',

        equipVi: 'Trung tâm cân bằng tải đa luồng & đối soát On-Chain BSC',

        deskX: 0.0,

        deskZ: 11.8,

        deskYaw: Math.PI,

        doorX: 0.0,

        doorZ: 6.2,

        angleDeg: 345,

        colorHex: 0x10b981,

        suitHex: 0x047857,

        visorHex: 0xa7f3d0,

        skinHex: 0xf6d2b8,

        hairHex: 0x1c1917,

        trousersHex: 0x064e3b,

        humanName: 'Ngọc Ánh',

        shortLabel: 'Ngọc Ánh (Chia Tải AI)'

      }

    ];



    let OVERVIEW_DISPLAY_MODE = 'GAME'; // 'GAME' | 'DATA'

    let VOICE_AI_ENABLED = false;

    let LOW_PERF_MODE = false;

    let FOLLOW_SELECTED_AGENT = false;

    let COMM_AUTO_SCROLL = true;

    let CLEAN_3D_SCREEN_MODE = true; // Auto-hide cluttered HUD buttons on entry as requested by Owner

    let LABELS_3D_MODE = 'COMPACT'; // Show clean role/outfit tags above characters

    let SHOW_3D_SPEECH_BUBBLES = true; // Auto-enable floating speech bubbles on entry

    let SHOW_STAGE_HUD_PANELS = false;

    let TOP_LEFT_HUD_MINIMIZED = true;

    let HOVERED_AGENT_ID = null;

    let SPOKEN_MESSAGE_IDS = new Set();

    let DISPLAYED_BUBBLE_MSG_IDS = new Set();

    let ACTIVE_SPEECH_QUEUE = [];

    let CURRENT_ACTIVE_SPEECH = null; // { msg, expiresAt }

    let DEMO_LOCAL_MESSAGES = [];



    const WORLD_3D = {

      initialized: false,

      webglSupported: true,

      scene: null,

      camera: null,

      renderer: null,

      clock: null,

      raycaster: null,

      mouse: null,

      coreGroup: null,

      coreCrystal: null,

      coreRing1: null,

      coreRing2: null,

      commBeamLine: null,

      commPulseMesh: null,

      zonesByRole: {},

      charactersByRole: {},

      meetingSpots: [],

      pickableMeshes: [],

      overlaySignEls: {},

      overlayCharEls: {},

      overlayBubbleEl: null,

      camSpherical: {

        radius: 24.5,

        theta: 0.42,

        phi: 0.84,

        targetX: 0,

        targetY: 1.2,

        targetZ: 0.8

      },

      dragState: {

        isDown: false,

        button: 0,

        startX: 0,

        startY: 0,

        moved: false

      }

    };



    function switchOverviewMode(mode) {

      OVERVIEW_DISPLAY_MODE = mode === 'DATA' ? 'DATA' : 'GAME';

      const stageEl = document.getElementById('aiBase3DStage');

      const dataEl = document.getElementById('overviewDataMatrixBlock');

      const btnGame = document.getElementById('btnModeGameView');

      const btnData = document.getElementById('btnModeDataView');



      if (stageEl) stageEl.style.display = OVERVIEW_DISPLAY_MODE === 'GAME' ? 'block' : 'none';

      if (dataEl) dataEl.style.display = OVERVIEW_DISPLAY_MODE === 'DATA' ? 'block' : 'none';

      if (btnGame) btnGame.classList.toggle('active', OVERVIEW_DISPLAY_MODE === 'GAME');

      if (btnData) btnData.classList.toggle('active', OVERVIEW_DISPLAY_MODE === 'DATA');



      if (OVERVIEW_DISPLAY_MODE === 'GAME' && WORLD_3D.initialized) {

        onResize3DWorld();

      }

    }



    function sync3DOverlayControlButtons() {

      const stage = document.getElementById('aiBase3DStage');

      if (stage) stage.classList.toggle('clean-3d-screen', CLEAN_3D_SCREEN_MODE);

      const quickBtn = document.getElementById('btnQuickToggle3DControls');

      if (quickBtn) {

        quickBtn.innerHTML = CLEAN_3D_SCREEN_MODE

          ? '🎛️ Hiện nút điều khiển 3D'

          : '👁️ Ẩn chữ điều khiển 3D (Màn hình sạch)';

      }



      const btnClean = document.getElementById('btnClean3DScreen');

      if (btnClean) {

        btnClean.textContent = CLEAN_3D_SCREEN_MODE

          ? t('👁️ Màn Hình Sạch: BẬT (Hiện Lại)', '👁️ Clean View: ON (Restore UI)')

          : t('👁️ Màn Hình Sạch: TẮT', '👁️ Clean View: OFF');

        btnClean.style.background = CLEAN_3D_SCREEN_MODE ? 'rgba(6, 182, 212, 0.28)' : '';

      }



      const btnLabels = document.getElementById('btnToggle3DLabels');

      if (btnLabels) {

        const labelMap = {

          SELECTED: t('🏷️ Nhãn Tên: CHỈ KHI CHỌN', '🏷️ Labels: ON SELECT'),

          COMPACT: t('🏷️ Nhãn Tên: HIỆN 15+ AI', '🏷️ Labels: 15+ AGENTS'),

          ALL: t('🏷️ Nhãn Tên: HIỆN TẤT CẢ', '🏷️ Labels: ALL (+ROOMS)'),

          HIDDEN: t('🏷️ Nhãn Tên: ẨN HẾT', '🏷️ Labels: HIDDEN')

        };

        btnLabels.textContent = labelMap[LABELS_3D_MODE] || labelMap.SELECTED;

      }



      const btnBubbles = document.getElementById('btnToggleSpeechBubbles');

      if (btnBubbles) {

        btnBubbles.textContent = SHOW_3D_SPEECH_BUBBLES

          ? t('💭 Thoại Nổi: BẬT', '💭 Bubbles: ON')

          : t('💭 Thoại Nổi: TẮT', '💭 Bubbles: OFF');

        btnBubbles.style.opacity = SHOW_3D_SPEECH_BUBBLES ? '1' : '0.65';

      }



      const btnHud = document.getElementById('btnToggleStageHud');

      if (btnHud) {

        btnHud.textContent = SHOW_STAGE_HUD_PANELS

          ? t('🎛️ Khung Điều Khiển: HIỆN', '🎛️ HUD Panels: ON')

          : t('🎛️ Khung Điều Khiển: ẨN', '🎛️ HUD Panels: OFF');

      }



      const topLeftHud = document.getElementById('stageSelectedHud');

      const bottomHud = document.getElementById('stageBottomHud');

      if (topLeftHud) {

        topLeftHud.classList.toggle('hidden-hud', !SHOW_STAGE_HUD_PANELS);

        topLeftHud.classList.toggle('minimized', TOP_LEFT_HUD_MINIMIZED);

      }

      if (bottomHud) {

        bottomHud.classList.toggle('hidden-hud', !SHOW_STAGE_HUD_PANELS);

      }

      const btnMin = document.getElementById('btnMinimizeTopLeftHud');

      if (btnMin) {

        btnMin.textContent = TOP_LEFT_HUD_MINIMIZED ? '+' : '—';

      }



      const drawer = document.getElementById('aiCommHubDrawer');

      const isDrawerCollapsed = drawer ? drawer.classList.contains('collapsed') : true;

      const btnDrawer = document.getElementById('btnToggleCommHub');

      const btnFloatingDrawer = document.getElementById('btnFloatingCommHubToggle');

      if (btnDrawer) {

        btnDrawer.textContent = isDrawerCollapsed ? t('💬 Mở', '💬 Open') : t('✕ Đóng', '✕ Close');

      }

      if (btnFloatingDrawer) {

        btnFloatingDrawer.textContent = isDrawerCollapsed

          ? t('💬 Hội Thoại AI Đang Làm Việc: HIỆN', '💬 Comm Hub: OPEN')

          : t('💬 Hội Thoại AI Đang Làm Việc: ẨN', '💬 Comm Hub: HIDE');

      }

    }



    function toggleClean3DScreenMode() {

      CLEAN_3D_SCREEN_MODE = !CLEAN_3D_SCREEN_MODE;

      SHOW_STAGE_HUD_PANELS = !CLEAN_3D_SCREEN_MODE;

      SHOW_3D_SPEECH_BUBBLES = true;

      sync3DOverlayControlButtons();

      update2DProjectedOverlay();

      showToast(CLEAN_3D_SCREEN_MODE

        ? t('Đã ẩn gọn các nút điều khiển 3D (Thoại nổi AI vẫn tự động bật).', 'Hidden 3D control bars (Floating AI speech bubbles remain active).')

        : t('Đã hiện bảng nút điều khiển 3D & Camera.', 'Restored 3D camera & control bars.'));

    }



    function cycle3DLabelsMode() {

      const order = ['SELECTED', 'COMPACT', 'ALL', 'HIDDEN'];

      const idx = order.indexOf(LABELS_3D_MODE);

      LABELS_3D_MODE = order[(idx + 1) % order.length];

      if (CLEAN_3D_SCREEN_MODE && LABELS_3D_MODE !== 'HIDDEN') {

        CLEAN_3D_SCREEN_MODE = false;

      }

      sync3DOverlayControlButtons();

      update2DProjectedOverlay();

    }



    function toggle3DSpeechBubbles() {

      SHOW_3D_SPEECH_BUBBLES = !SHOW_3D_SPEECH_BUBBLES;

      sync3DOverlayControlButtons();

      update2DProjectedOverlay();

    }



    function dismissActiveSpeechBubble(ev) {

      if (ev) ev.stopPropagation();

      CURRENT_ACTIVE_SPEECH = null;

      if (WORLD_3D.commBeamLine) WORLD_3D.commBeamLine.visible = false;

      if (WORLD_3D.commPulseMesh) WORLD_3D.commPulseMesh.visible = false;

      if (WORLD_3D.overlayBubbleEl) WORLD_3D.overlayBubbleEl.style.display = 'none';

      if (WORLD_3D.overlayReplyBubbleEl) WORLD_3D.overlayReplyBubbleEl.style.display = 'none';

    }



    function toggleStageHudPanels() {

      SHOW_STAGE_HUD_PANELS = !SHOW_STAGE_HUD_PANELS;

      if (SHOW_STAGE_HUD_PANELS && CLEAN_3D_SCREEN_MODE) {

        CLEAN_3D_SCREEN_MODE = false;

      }

      sync3DOverlayControlButtons();

    }



    function toggleTopLeftHudMinimize(forceState) {

      if (typeof forceState === 'boolean') {

        TOP_LEFT_HUD_MINIMIZED = forceState;

      } else {

        TOP_LEFT_HUD_MINIMIZED = !TOP_LEFT_HUD_MINIMIZED;

      }

      sync3DOverlayControlButtons();

    }



    function toggleCommHubDrawer() {

      const drawer = document.getElementById('aiCommHubDrawer');

      if (!drawer) return;

      const willOpen = drawer.classList.contains('collapsed');

      if (willOpen && CLEAN_3D_SCREEN_MODE) {

        CLEAN_3D_SCREEN_MODE = false;

      }

      drawer.classList.toggle('collapsed');

      sync3DOverlayControlButtons();

    }



    function toggleCommAutoScroll() {

      COMM_AUTO_SCROLL = !COMM_AUTO_SCROLL;

      const btn = document.getElementById('btnPauseCommScroll');

      if (btn) {

        btn.textContent = COMM_AUTO_SCROLL ? '⏸' : '▶';

        btn.title = COMM_AUTO_SCROLL

          ? t('Đang tự động cuộn (Nhấp để tạm dừng)', 'Auto-scrolling (Click to pause)')

          : t('Đã tạm dừng cuộn tự động', 'Auto-scroll paused');

      }

    }



    function scrollToLatestCommMessage() {

      const list = document.getElementById('commHubMessagesList');

      if (list) list.scrollTop = 0;

    }



    function toggleVietnameseVoice() {

      VOICE_AI_ENABLED = !VOICE_AI_ENABLED;

      const btn = document.getElementById('btnVoiceToggle');

      if (btn) {

        btn.textContent = VOICE_AI_ENABLED

          ? t('🔊 GIỌNG NÓI AI: BẬT', '🔊 AI VOICE: ON')

          : t('🔊 GIỌNG NÓI AI: TẮT', '🔊 AI VOICE: OFF');

        btn.style.borderColor = VOICE_AI_ENABLED ? '#10b981' : '';

      }

      if (!VOICE_AI_ENABLED && window.speechSynthesis) {

        window.speechSynthesis.cancel();

      } else if (VOICE_AI_ENABLED) {

        showToast(t('Đã bật đọc lời thoại AI (Web Speech API). Hệ thống chỉ đọc từng lượt lời thoại mới.', 'Enabled AI Speech Synthesis (Web Speech API). System speaks each new dialogue turn once.'));

        if (CURRENT_ACTIVE_SPEECH && CURRENT_ACTIVE_SPEECH.msg) {

          speakVietnameseMessageOnce(CURRENT_ACTIVE_SPEECH.msg);

        }

      }

    }



    function speakVietnameseMessageOnce(msgObj) {

      if (!VOICE_AI_ENABLED || !window.speechSynthesis || !msgObj) return;

      const id = msgObj.message_id || `${msgObj.sender_agent_id}_${msgObj.created_at}`;

      if (SPOKEN_MESSAGE_IDS.has(id)) return;

      SPOKEN_MESSAGE_IDS.add(id);



      try {

        window.speechSynthesis.cancel();

        const textToSpeak = trContent(msgObj.message_content);

        const utter = new SpeechSynthesisUtterance(textToSpeak);

        const targetLang = CURRENT_LANG === 'en' ? 'en-US' : 'vi-VN';

        utter.lang = targetLang;

        utter.rate = 1.04;

        const voices = window.speechSynthesis.getVoices() || [];

        const langPrefix = CURRENT_LANG === 'en' ? 'en' : 'vi';

        const matchedVoice = voices.find(v => v.lang && v.lang.toLowerCase().includes(langPrefix));

        if (matchedVoice) utter.voice = matchedVoice;

        window.speechSynthesis.speak(utter);

      } catch (_) {}

    }



    function toggleLowPerfMode() {

      LOW_PERF_MODE = !LOW_PERF_MODE;

      const btn = document.getElementById('btnPerfModeToggle');

      if (btn) {

        btn.textContent = LOW_PERF_MODE

          ? t('⚡ Đồ họa: THẤP (Tối ưu)', '⚡ Graphics: LOW (Optimized)')

          : t('⚡ Đồ họa: CAO', '⚡ Graphics: HIGH');

      }

      if (WORLD_3D.renderer) {

        WORLD_3D.renderer.setPixelRatio(LOW_PERF_MODE ? 1 : Math.min(window.devicePixelRatio || 1, 2));

      }

      showToast(LOW_PERF_MODE

        ? t('Đã bật chế độ Hiệu Suất Thấp cho máy tính phổ thông.', 'Enabled Low Performance mode for standard PCs.')

        : t('Đã bật chế độ Đồ Họa Cao.', 'Enabled High Graphics mode.'));

    }



    function toggleFollowCamera() {

      FOLLOW_SELECTED_AGENT = !FOLLOW_SELECTED_AGENT;

      const btn = document.getElementById('btnFollowCamToggle');

      if (btn) {

        btn.textContent = FOLLOW_SELECTED_AGENT

          ? t('🎯 Theo Dõi AI: BẬT', '🎯 Follow Agent: ON')

          : t('🎯 Theo Dõi AI: TẮT', '🎯 Follow Agent: OFF');

        btn.style.borderColor = FOLLOW_SELECTED_AGENT ? '#06b6d4' : '';

      }

      if (FOLLOW_SELECTED_AGENT && !SELECTED_AGENT_ID) {

        SELECTED_AGENT_ID = 'RESEARCH_AGENT';

      }

    }



    function reset3DCamera() {

      FOLLOW_SELECTED_AGENT = false;

      const btn = document.getElementById('btnFollowCamToggle');

      if (btn) btn.textContent = t('🎯 Theo Dõi AI: TẮT', '🎯 Follow Agent: OFF');

      WORLD_3D.camSpherical.radius = 24.5;

      WORLD_3D.camSpherical.theta = 0.42;

      WORLD_3D.camSpherical.phi = 0.88;

      WORLD_3D.camSpherical.targetX = 0;

      WORLD_3D.camSpherical.targetY = 1.2;

      WORLD_3D.camSpherical.targetZ = 0.8;

    }



    function focusOfficeRoomCamera(roomKey) {

      FOLLOW_SELECTED_AGENT = false;

      const btn = document.getElementById('btnFollowCamToggle');

      if (btn) btn.textContent = t('🎯 Theo Dõi AI: TẮT', '🎯 Follow Agent: OFF');

      if (!roomKey || roomKey === 'ALL') {

        reset3DCamera();

        return;

      }

      const presetMap = {

        MEETING:     { targetX: 0,     targetZ: 0.2,   radius: 17.5, theta: 0.25, phi: 0.82 },

        EXEC:        { targetX: 0,     targetZ: -10.8, radius: 18.5, theta: 0.18, phi: 0.84 },

        RESEARCH:    { targetX: -14.2, targetZ: -10.5, radius: 18.5, theta: 0.52, phi: 0.84 },

        ENGINEERING: { targetX: -14.2, targetZ: 3.5,   radius: 21.0, theta: 0.58, phi: 0.86 },

        REVENUE:     { targetX: 14.2,  targetZ: -3.2,  radius: 21.5, theta: -0.52, phi: 0.86 },

        FINANCE_SEC: { targetX: 7.5,   targetZ: 10.5,  radius: 21.0, theta: -0.25, phi: 0.86 }

      };

      const p = presetMap[roomKey] || presetMap.MEETING;

      WORLD_3D.camSpherical.targetX = p.targetX;

      WORLD_3D.camSpherical.targetZ = p.targetZ;

      WORLD_3D.camSpherical.radius = p.radius;

      WORLD_3D.camSpherical.theta = p.theta;

      WORLD_3D.camSpherical.phi = p.phi;

    }



    async function changeEmployee3DOutfit(role, suitHexStr, accentHexStr) {

      const ch = WORLD_3D.charactersByRole[role];

      const suitInt = parseInt(String(suitHexStr).replace('#', ''), 16);

      const accentInt = parseInt(String(accentHexStr).replace('#', ''), 16);

      if (ch && ch.parts) {

        if (!Number.isNaN(suitInt)) {

          ch.cfg.suitHex = suitInt;

          if (ch.parts.suitMat) ch.parts.suitMat.color.setHex(suitInt);

        }

        if (!Number.isNaN(accentInt)) {

          ch.cfg.visorHex = accentInt;

          if (ch.parts.visorMat) ch.parts.visorMat.color.setHex(accentInt);

        }

      }

      // Persist appearance update to backend if online without changing employee identity

      const emp = (STATE.employees || []).find(e => e.role_code === role || e.employee_id === role);

      if (STATE.online && emp && emp.employee_id) {

        try {

          await apiFetch(`/api/employees/${encodeURIComponent(emp.employee_id)}/appearance`, {

            method: 'PUT',

            body: JSON.stringify({ suit_color: suitHexStr, accent_color: accentHexStr })

          });

        } catch (_) {}

      }

      showToast(t(`Đã cập nhật trang phục 3D cho ${formatAgentTitle(role)} (Giữ nguyên danh tính Backend).`, `Updated 3D corporate attire for ${formatAgentTitle(role)} (Backend identity preserved).`));

    }



    function sendEmployeeToMeetingRoom(role) {

      const ch = WORLD_3D.charactersByRole[role];

      if (!ch) return;

      const idx = BASE_ZONES_CONFIG.findIndex(z => z.role === role);

      const seats = WORLD_3D.meetingSpots && WORLD_3D.meetingSpots.length ? WORLD_3D.meetingSpots : [{ x: 0, z: 2.2, yaw: Math.PI }];

      const seat = seats[(idx >= 0 ? idx : 0) % seats.length];

      focusOfficeRoomCamera('MEETING');

      sendCharacterAlongPath(role, seat, 'MEETING', false);

      showToast(t(`${formatAgentTitle(role)} đang di chuyển theo hànhlang vào Phòng Họp Trung Tâm.`, `${formatAgentTitle(role)} is walking along the office hallway to the Central Boardroom.`));

    }



    function sendEmployeeBackToDesk(role) {

      const z = WORLD_3D.zonesByRole[role];

      const ch = WORLD_3D.charactersByRole[role];

      if (!z || !ch) return;

      const targetSpot = (ch.backendStatus === 'IDLE' || ch.backendStatus === 'OFFLINE') ? z.idleSpot : z.workSpot;

      const postState = ch.backendStatus === 'IDLE' ? 'IDLE' : 'WORK_AT_DESK';

      sendCharacterAlongPath(role, targetSpot, postState, false);

      showToast(t(`${formatAgentTitle(role)} đang quay về bàn làm việc tại ${formatZoneName(role)}.`, `${formatAgentTitle(role)} is returning to their workstation in ${formatZoneName(role)}.`));

    }



    function zoom3DCamera(deltaRadius) {

      WORLD_3D.camSpherical.radius = Math.max(12, Math.min(54, WORLD_3D.camSpherical.radius + deltaRadius));

    }



    function rotate3DCamera(deltaTheta) {

      WORLD_3D.camSpherical.theta += deltaTheta;

    }



    function lerpAngle(current, target, factor) {

      let diff = target - current;

      while (diff < -Math.PI) diff += Math.PI * 2;

      while (diff > Math.PI) diff -= Math.PI * 2;

      return current + diff * factor;

    }



    // Orthogonal Office Hallway & Doorway Pathfinding (Routes along hallways x = ±7.2, z = ±5.4 so employees never walk through walls or conference tables)

    function buildSafeCorridorPath(startX, startZ, endX, endZ) {

      const distDirect = Math.hypot(endX - startX, endZ - startZ);

      if (distDirect < 2.6) {

        return [{ x: endX, z: endZ }];

      }

      const hallX = ( xVal ) => (xVal < 0 ? -7.2 : 7.2);

      const hallZ = ( zVal ) => (zVal < 0 ? -5.4 : 5.4);



      const waypoints = [];

      const sxH = hallX(startX);

      const szH = hallZ(startZ);

      const exH = hallX(endX);

      const ezH = hallZ(endZ);



      // 1. Step from workstation / room out through room doorway into nearest hallway

      if (Math.abs(startX) > 8.2) {

        waypoints.push({ x: sxH, z: Math.max(-13.5, Math.min(13.5, startZ)) });

      } else if (Math.abs(startZ) > 6.0) {

        waypoints.push({ x: Math.max(-12.0, Math.min(12.0, startX)), z: szH });

      }



      // 2. Navigate along the rectangular main hallway loop around the Central Glass Boardroom

      const curWp = waypoints.length ? waypoints[waypoints.length - 1] : { x: startX, z: startZ };

      if (Math.abs(curWp.x - exH) > 1.5 && Math.abs(curWp.z - ezH) > 1.5) {

        waypoints.push({ x: curWp.x, z: szH });

        if (Math.sign(curWp.x) !== Math.sign(exH)) {

          waypoints.push({ x: exH, z: szH });

        }

      }



      // 3. Approach target room doorway on the hallway before entering destination

      if (Math.abs(endX) > 8.2) {

        waypoints.push({ x: exH, z: Math.max(-13.5, Math.min(13.5, endZ)) });

      } else if (Math.abs(endZ) > 6.0) {

        waypoints.push({ x: Math.max(-12.0, Math.min(12.0, endX)), z: ezH });

      } else {

        // Entering Central Boardroom via North/South/East/West glass doors

        waypoints.push({ x: Math.max(-5.2, Math.min(5.2, endX)), z: endZ >= 0 ? 4.4 : -4.2 });

      }



      // 4. Final destination spot (Chair / Desk / Lounge / Boardroom seat)

      waypoints.push({ x: endX, z: endZ });

      return waypoints;

    }



    // =========================================================================

    // TASK 2 & PART A: RIGGED HUMAN 3D GAME CHARACTERS (GLTF + SKELETAL MIXER)

    // =========================================================================

    const HUMAN_CHARACTER_ASSET_CATALOG = {

      RESEARCH_AGENT:         { assetUrl: './assets/Michelle.glb', gender: 'F', heightScale: 1.42, roleProp: 'TABLET' },

      PRODUCT_AGENT:          { assetUrl: './assets/Xbot.glb',     gender: 'M', heightScale: 1.46, roleProp: 'TABLET' },

      CODING_AGENT:           { assetUrl: './assets/Xbot.glb',     gender: 'M', heightScale: 1.45, roleProp: 'LAPTOP_BADGE' },

      MARKETING_AGENT:        { assetUrl: './assets/Michelle.glb', gender: 'F', heightScale: 1.42, roleProp: 'STYLUS_PAD' },

      SALES_AGENT:            { assetUrl: './assets/Xbot.glb',     gender: 'M', heightScale: 1.47, roleProp: 'BRIEF_PAD' },

      CUSTOMER_SUPPORT_AGENT: { assetUrl: './assets/Michelle.glb', gender: 'F', heightScale: 1.41, roleProp: 'HEADSET' },

      FINANCE_AGENT:          { assetUrl: './assets/Xbot.glb',     gender: 'M', heightScale: 1.46, roleProp: 'LEDGER_PAD' },

      OPTIMIZATION_AGENT:     { assetUrl: './assets/Michelle.glb', gender: 'F', heightScale: 1.43, roleProp: 'STRATEGY_PAD' },

      SECURITY_AGENT:         { assetUrl: './assets/Xbot.glb',     gender: 'M', heightScale: 1.48, roleProp: 'SECURITY_SHIELD' },

      AFFILIATE_AMAZON_AGENT: { assetUrl: './assets/Michelle.glb', gender: 'F', heightScale: 1.43, roleProp: 'STYLUS_PAD' },

      SHOPIFY_ECOM_AGENT:     { assetUrl: './assets/Xbot.glb',     gender: 'M', heightScale: 1.46, roleProp: 'BRIEF_PAD' },

      CRYPTO_ARBITRAGE_AGENT: { assetUrl: './assets/Xbot.glb',     gender: 'M', heightScale: 1.47, roleProp: 'LEDGER_PAD' },

      AIRDROP_BOUNTY_AGENT:   { assetUrl: './assets/Michelle.glb', gender: 'F', heightScale: 1.42, roleProp: 'TABLET' },

      VIRAL_TRAFFIC_AGENT:    { assetUrl: './assets/Xbot.glb',     gender: 'M', heightScale: 1.45, roleProp: 'LAPTOP_BADGE' },

      TEMPLATE_POD_AGENT:     { assetUrl: './assets/Michelle.glb', gender: 'F', heightScale: 1.43, roleProp: 'STRATEGY_PAD' }

    };



    const GLTF_ASSET_CACHE = {

      loading: false,

      loaded: false,

      modelsByUrl: {},

      sharedClips: {}

    };



    // Valid transitions for the 12-state character animation state machine

    const VALID_ANIM_STATES = [

      'IDLE', 'WALK', 'RUN', 'SIT', 'WORK', 'WORK_AT_DESK',

      'TYPE', 'READ', 'TALK', 'LISTEN', 'MEETING', 'CELEBRATE',

      'NEEDS_ASSISTANCE', 'ERROR', 'OFFLINE'

    ];



    function normalizeAnimStateName(st) {

      if (!st) return 'IDLE';

      const u = String(st).toUpperCase();

      if (u === 'WORKING' || u === 'SUCCESS') return 'WORK';

      if (u === 'THINKING') return 'READ';

      if (u === 'COMMUNICATING') return 'TALK';

      if (u === 'WAITING' || u === 'WAITING_APPROVAL') return 'NEEDS_ASSISTANCE';

      return VALID_ANIM_STATES.includes(u) ? u : 'IDLE';

    }



    function buildProceduralHumanAnimationClips(THREE) {

      if (!THREE || !THREE.KeyframeTrack || !THREE.AnimationClip) return {};

      if (WORLD_3D.proceduralClipsByState) return WORLD_3D.proceduralClipsByState;

      const times = [0, 0.25, 0.5, 0.75, 1.0];

      const makeClip = (name, lLegX, rLegX, lArmX, rArmX, bodyY, headY) => {

        const tracks = [

          new THREE.NumberKeyframeTrack('LeftUpLeg.rotation[x]', times, lLegX),

          new THREE.NumberKeyframeTrack('RightUpLeg.rotation[x]', times, rLegX),

          new THREE.NumberKeyframeTrack('LeftArm.rotation[x]', times, lArmX),

          new THREE.NumberKeyframeTrack('RightArm.rotation[x]', times, rArmX),

          new THREE.NumberKeyframeTrack('Spine.position[y]', times, bodyY),

          new THREE.NumberKeyframeTrack('Head.rotation[y]', times, headY)

        ];

        return new THREE.AnimationClip(name, 1.0, tracks);

      };

      WORLD_3D.proceduralClipsByState = {

        IDLE: makeClip('human_idle', [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0.03, -0.03, 0.03, -0.03, 0.03], [-0.03, 0.03, -0.03, 0.03, -0.03], [0, 0.015, 0, -0.015, 0], [0, 0.12, 0, -0.12, 0]),

        WALK: makeClip('human_walk', [0, 0.46, 0, -0.46, 0], [0, -0.46, 0, 0.46, 0], [0, -0.38, 0, 0.38, 0], [0, 0.38, 0, -0.38, 0], [0, 0.045, 0, 0.045, 0], [0, 0.04, 0, -0.04, 0]),

        RUN: makeClip('human_run', [0, 0.72, 0, -0.72, 0], [0, -0.72, 0, 0.72, 0], [0, -0.62, 0, 0.62, 0], [0, 0.62, 0, -0.62, 0], [0, 0.075, 0, 0.075, 0], [0, 0.05, 0, -0.05, 0]),

        SIT: makeClip('human_sit', [-1.18, -1.18, -1.18, -1.18, -1.18], [-1.18, -1.18, -1.18, -1.18, -1.18], [-0.35, -0.36, -0.35, -0.34, -0.35], [-0.35, -0.34, -0.35, -0.36, -0.35], [-0.18, -0.17, -0.18, -0.19, -0.18], [0, 0.08, 0, -0.08, 0]),

        WORK: makeClip('human_work', [-1.18, -1.18, -1.18, -1.18, -1.18], [-1.18, -1.18, -1.18, -1.18, -1.18], [-0.68, -0.56, -0.68, -0.78, -0.68], [-0.68, -0.78, -0.68, -0.56, -0.68], [-0.18, -0.17, -0.18, -0.17, -0.18], [0, 0.12, 0, -0.12, 0]),

        WORK_AT_DESK: makeClip('human_work_desk', [-1.18, -1.18, -1.18, -1.18, -1.18], [-1.18, -1.18, -1.18, -1.18, -1.18], [-0.68, -0.56, -0.68, -0.78, -0.68], [-0.68, -0.78, -0.68, -0.56, -0.68], [-0.18, -0.17, -0.18, -0.17, -0.18], [0, 0.12, 0, -0.12, 0]),

        TYPE: makeClip('human_type', [-1.18, -1.18, -1.18, -1.18, -1.18], [-1.18, -1.18, -1.18, -1.18, -1.18], [-0.72, -0.54, -0.72, -0.84, -0.72], [-0.72, -0.84, -0.72, -0.54, -0.72], [-0.18, -0.17, -0.18, -0.17, -0.18], [0, 0.09, 0, -0.09, 0]),

        READ: makeClip('human_read', [-1.12, -1.12, -1.12, -1.12, -1.12], [-1.12, -1.12, -1.12, -1.12, -1.12], [-0.78, -0.78, -0.78, -0.78, -0.78], [-0.52, -0.45, -0.52, -0.58, -0.52], [-0.16, -0.15, -0.16, -0.15, -0.16], [0, 0.14, 0, -0.14, 0]),

        TALK: makeClip('human_talk', [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [-0.32, -0.18, -0.32, -0.46, -0.32], [-0.78, -0.54, -0.78, -1.02, -0.78], [0, 0.025, 0, -0.025, 0], [0, 0.14, 0, -0.14, 0]),

        LISTEN: makeClip('human_listen', [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [-0.15, -0.15, -0.15, -0.15, -0.15], [-0.25, -0.25, -0.25, -0.25, -0.25], [0, 0.015, 0, -0.015, 0], [0, 0.06, 0, -0.06, 0]),

        MEETING: makeClip('human_meeting', [-1.18, -1.18, -1.18, -1.18, -1.18], [-1.18, -1.18, -1.18, -1.18, -1.18], [-0.45, -0.30, -0.45, -0.60, -0.45], [-0.62, -0.78, -0.62, -0.46, -0.62], [-0.18, -0.16, -0.18, -0.16, -0.18], [0, 0.20, 0, -0.20, 0]),

        CELEBRATE: makeClip('human_celebrate', [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [-2.35, -2.12, -2.35, -2.55, -2.35], [-2.35, -2.55, -2.35, -2.12, -2.35], [0, 0.08, 0, 0.08, 0], [0, 0.18, 0, -0.18, 0]),

        NEEDS_ASSISTANCE: makeClip('human_assistance', [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [-0.20, -0.20, -0.20, -0.20, -0.20], [-1.18, -1.04, -1.18, -1.32, -1.18], [0, 0, 0, 0, 0], [0, 0.08, 0, -0.08, 0]),

        ERROR: makeClip('human_error', [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [-0.20, -0.20, -0.20, -0.20, -0.20], [-1.18, -1.04, -1.18, -1.32, -1.18], [0, 0, 0, 0, 0], [0, 0.08, 0, -0.08, 0]),

        OFFLINE: makeClip('human_offline', [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0])

      };

      return WORLD_3D.proceduralClipsByState;

    }



    function createArticulated3DCharacter(THREE, cfg) {

      const root = new THREE.Group();

      root.userData = { pickType: 'AGENT', role: cfg.role };



      const style = (typeof ROLE_OUTFIT_STYLES !== 'undefined' && ROLE_OUTFIT_STYLES[cfg.role])

        ? ROLE_OUTFIT_STYLES[cfg.role]

        : {

            outfitNameVi: 'Trang Phục Công Sở AI',

            jacketHex: cfg.suitHex || 0x06b6d4,

            shirtHex: 0xffffff,

            tieHex: cfg.visorHex || 0xfbbf24,

            pantsHex: cfg.trousersHex || 0x1e293b,

            shoeHex: 0x0f172a,

            skinHex: cfg.skinHex || 0xf3c6a5,

            hairHex: cfg.hairHex || 0x1e293b,

            headAccessory: 'VISOR_GLASSES'

          };



      const jacketHex = style.jacketHex || cfg.suitHex || 0x06b6d4;

      const shirtHex = style.shirtHex || 0xffffff;

      const tieHex = style.tieHex || cfg.visorHex || 0xfbbf24;

      const trousersHex = style.pantsHex || cfg.trousersHex || 0x1e293b;

      const shoeHex = style.shoeHex || 0x0f172a;

      const skinHex = style.skinHex || cfg.skinHex || 0xf3c6a5;

      const hairHex = style.hairHex || cfg.hairHex || 0x1e293b;

      const assetMeta = HUMAN_CHARACTER_ASSET_CATALOG[cfg.role] || { assetUrl: './assets/Xbot.glb', gender: 'M', heightScale: 1.45, roleProp: 'TABLET' };



      const suitMat = new THREE.MeshStandardMaterial({

        color: jacketHex,

        emissive: jacketHex,

        emissiveIntensity: 0.28,

        roughness: 0.35,

        metalness: 0.14

      });

      const trousersMat = new THREE.MeshStandardMaterial({

        color: trousersHex,

        emissive: trousersHex,

        emissiveIntensity: 0.16,

        roughness: 0.48,

        metalness: 0.10

      });

      const skinMat = new THREE.MeshStandardMaterial({

        color: skinHex,

        emissive: skinHex,

        emissiveIntensity: 0.18,

        roughness: 0.45,

        metalness: 0.04

      });

      const hairMat = new THREE.MeshStandardMaterial({

        color: hairHex,

        roughness: 0.55,

        metalness: 0.08

      });

      const shirtMat = new THREE.MeshStandardMaterial({

        color: shirtHex,

        emissive: shirtHex,

        emissiveIntensity: 0.22,

        roughness: 0.32,

        metalness: 0.05

      });

      const visorMat = new THREE.MeshBasicMaterial({

        color: tieHex

      });

      const shoeMat = new THREE.MeshStandardMaterial({

        color: shoeHex,

        roughness: 0.35,

        metalness: 0.22

      });



      // Glowing Floor Selection Ring under each AI Employee

      const auraGeo = new THREE.RingGeometry(0.48, 0.66, 32);

      auraGeo.rotateX(-Math.PI / 2);

      const auraMat = new THREE.MeshBasicMaterial({

        color: cfg.colorHex || jacketHex,

        side: THREE.DoubleSide,

        transparent: true,

        opacity: 0.58

      });

      const auraRing = new THREE.Mesh(auraGeo, auraMat);

      auraRing.position.y = 0.03;

      root.add(auraRing);



      // High-Visibility Tailored 3D Human Rig Container (Scaled 1.32x so all 9 characters stand out clearly in the 3D office)

      const sculptedHumanGroup = new THREE.Group();

      sculptedHumanGroup.name = 'SculptedHumanRig';

      sculptedHumanGroup.scale.set(1.32, 1.32, 1.32);

      sculptedHumanGroup.visible = true;

      root.add(sculptedHumanGroup);



      // Spine / Body Group

      const bodyGroup = new THREE.Group();

      bodyGroup.name = 'Spine';

      sculptedHumanGroup.add(bodyGroup);



      // Sculpted Pelvis & Belt with Gold Buckle

      const pelvisMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.23, 0.26, 20), trousersMat);

      pelvisMesh.scale.set(1.14, 1.0, 0.78);

      pelvisMesh.position.y = 0.94;

      bodyGroup.add(pelvisMesh);



      const beltMesh = new THREE.Mesh(

        new THREE.CylinderGeometry(0.255, 0.255, 0.06, 20),

        new THREE.MeshBasicMaterial({ color: 0x0f172a })

      );

      beltMesh.scale.set(1.15, 1.0, 0.79);

      beltMesh.position.y = 1.05;

      bodyGroup.add(beltMesh);



      // Tailored Corporate Blazer / Hoodie / Suit Torso

      const torsoMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.33, 0.26, 0.86, 24), suitMat);

      torsoMesh.scale.set(1.15, 1.0, 0.75);

      torsoMesh.position.y = 1.43;

      torsoMesh.userData = { pickType: 'AGENT', role: cfg.role };

      bodyGroup.add(torsoMesh);



      const shoulderCapGeo = new THREE.SphereGeometry(0.155, 16, 14);

      const leftShoulderCap = new THREE.Mesh(shoulderCapGeo, suitMat);

      leftShoulderCap.position.set(-0.38, 1.76, 0);

      const rightShoulderCap = new THREE.Mesh(shoulderCapGeo, suitMat);

      rightShoulderCap.position.set(0.38, 1.76, 0);

      bodyGroup.add(leftShoulderCap, rightShoulderCap);



      // Crisp Dress Shirt V-Neck, Tie & ID Badge

      const shirtPanel = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.065, 0.48, 14), shirtMat);

      shirtPanel.scale.set(1.0, 1.0, 0.28);

      shirtPanel.position.set(0, 1.58, 0.205);

      bodyGroup.add(shirtPanel);



      const chestCore = new THREE.Mesh(new THREE.CylinderGeometry(0.042, 0.055, 0.38, 12), visorMat);

      chestCore.scale.set(1.0, 1.0, 0.38);

      chestCore.position.set(0, 1.52, 0.228);

      bodyGroup.add(chestCore);



      const idBadge = new THREE.Mesh(

        new THREE.CylinderGeometry(0.055, 0.055, 0.02, 12),

        new THREE.MeshBasicMaterial({ color: 0xffffff })

      );

      idBadge.position.set(0.16, 1.58, 0.225);

      bodyGroup.add(idBadge);



      // Human Neck

      const neckMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.102, 0.116, 0.22, 16), skinMat);

      neckMesh.position.set(0, 1.93, 0);

      bodyGroup.add(neckMesh);



      // Sculpted Human Head, Face, Eyes, Hair & Distinct Role Headgear

      const headGroup = new THREE.Group();

      headGroup.name = 'Head';

      headGroup.position.set(0, 2.17, 0);

      bodyGroup.add(headGroup);



      const helmetMesh = new THREE.Mesh(new THREE.SphereGeometry(0.255, 24, 22), skinMat);

      helmetMesh.scale.set(0.94, 1.08, 0.96);

      helmetMesh.userData = { pickType: 'AGENT', role: cfg.role };

      headGroup.add(helmetMesh);



      const earGeo = new THREE.SphereGeometry(0.05, 12, 10);

      const leftEar = new THREE.Mesh(earGeo, skinMat);

      leftEar.position.set(-0.23, 0.0, 0.0);

      const rightEar = new THREE.Mesh(earGeo, skinMat);

      rightEar.position.set(0.23, 0.0, 0.0);

      const noseMesh = new THREE.Mesh(new THREE.ConeGeometry(0.036, 0.09, 12), skinMat);

      noseMesh.rotation.x = Math.PI / 2;

      noseMesh.position.set(0, -0.01, 0.248);

      headGroup.add(leftEar, rightEar, noseMesh);



      const eyeMat = new THREE.MeshBasicMaterial({ color: 0x0f172a });

      const leftEye = new THREE.Mesh(new THREE.SphereGeometry(0.026, 10, 10), eyeMat);

      leftEye.position.set(-0.085, 0.04, 0.225);

      const rightEye = new THREE.Mesh(new THREE.SphereGeometry(0.026, 10, 10), eyeMat);

      rightEye.position.set(0.085, 0.04, 0.225);

      headGroup.add(leftEye, rightEye);



      // Sculpted Hair Crown & Styled Back Hair

      const hairCap = new THREE.Mesh(new THREE.SphereGeometry(0.27, 22, 18, 0, Math.PI * 2, 0, Math.PI * 0.58), hairMat);

      hairCap.position.set(0, 0.045, -0.015);

      hairCap.userData = { pickType: 'AGENT', role: cfg.role };

      headGroup.add(hairCap);



      const hairBack = new THREE.Mesh(

        new THREE.CylinderGeometry(0.22, assetMeta.gender === 'F' ? 0.17 : 0.19, assetMeta.gender === 'F' ? 0.38 : 0.22, 18),

        hairMat

      );

      hairBack.scale.set(1.0, 1.0, 0.55);

      hairBack.position.set(0, assetMeta.gender === 'F' ? -0.04 : 0.02, -0.145);

      headGroup.add(hairBack);



      // Sleek Rimless Smart Glasses / Role Headgear

      const visorMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.185, 0.185, 0.048, 16, 1, false, -0.9, 1.8), visorMat);

      visorMesh.position.set(0, 0.04, 0.08);

      headGroup.add(visorMesh);



      if (style.headAccessory === 'BERET' || style.headAccessory === 'SECURITY_BERET') {

        const beret = new THREE.Mesh(

          new THREE.CylinderGeometry(0.24, 0.22, 0.09, 18),

          suitMat

        );

        beret.position.set(0.03, 0.25, 0);

        beret.rotation.z = -0.16;

        headGroup.add(beret);

      } else if (style.headAccessory === 'HEADPHONES' || style.headAccessory === 'HEADSET') {

        const earCupGeo = new THREE.CylinderGeometry(0.075, 0.075, 0.05, 16);

        const earL = new THREE.Mesh(earCupGeo, visorMat);

        earL.rotation.z = Math.PI / 2;

        earL.position.set(-0.245, 0.02, 0);

        const earR = new THREE.Mesh(earCupGeo, visorMat);

        earR.rotation.z = Math.PI / 2;

        earR.position.set(0.245, 0.02, 0);

        headGroup.add(earL, earR);

      } else if (style.headAccessory === 'CROWN_VISOR') {

        const crownBand = new THREE.Mesh(

          new THREE.CylinderGeometry(0.23, 0.23, 0.06, 18),

          visorMat

        );

        crownBand.position.set(0, 0.24, 0);

        headGroup.add(crownBand);

      }



      // Articulated Multi-Segment Human Left & Right Arms (Sleeves in Jacket color + Shirt Cuffs + Hands)

      const buildSculptedHumanArm = (sideSign, boneName) => {

        const armPivot = new THREE.Group();

        armPivot.name = boneName;

        armPivot.position.set(sideSign * 0.40, 1.74, 0);



        const upperArm = new THREE.Mesh(new THREE.CylinderGeometry(0.088, 0.076, 0.35, 16), suitMat);

        upperArm.position.y = -0.16;

        const elbowJoint = new THREE.Mesh(new THREE.SphereGeometry(0.076, 14, 12), suitMat);

        elbowJoint.position.y = -0.33;

        const forearm = new THREE.Mesh(new THREE.CylinderGeometry(0.072, 0.060, 0.31, 16), suitMat);

        forearm.position.set(0, -0.47, 0.03);

        forearm.rotation.x = -0.18;

        const wristCuff = new THREE.Mesh(new THREE.CylinderGeometry(0.062, 0.060, 0.055, 14), shirtMat);

        wristCuff.position.set(0, -0.60, 0.055);

        const handMesh = new THREE.Mesh(new THREE.SphereGeometry(0.072, 14, 14), skinMat);

        handMesh.scale.set(0.85, 1.15, 0.68);

        handMesh.position.set(0, -0.66, 0.07);

        armPivot.add(upperArm, elbowJoint, forearm, wristCuff, handMesh);

        return armPivot;

      };



      const leftArmPivot = buildSculptedHumanArm(-1, 'LeftArm');

      const rightArmPivot = buildSculptedHumanArm(1, 'RightArm');

      bodyGroup.add(leftArmPivot, rightArmPivot);



      // Articulated Multi-Segment Human Left & Right Legs (Trousers + Shoes)

      const buildSculptedHumanLeg = (sideSign, boneName) => {

        const legPivot = new THREE.Group();

        legPivot.name = boneName;

        legPivot.position.set(sideSign * 0.16, 0.90, 0);



        const thigh = new THREE.Mesh(new THREE.CylinderGeometry(0.112, 0.092, 0.42, 16), trousersMat);

        thigh.position.y = -0.20;

        const knee = new THREE.Mesh(new THREE.SphereGeometry(0.090, 14, 12), trousersMat);

        knee.position.y = -0.41;

        const calf = new THREE.Mesh(new THREE.CylinderGeometry(0.088, 0.072, 0.40, 16), trousersMat);

        calf.position.y = -0.60;

        const shoe = new THREE.Mesh(new THREE.CylinderGeometry(0.076, 0.086, 0.29, 16), shoeMat);

        shoe.rotation.x = Math.PI / 2;

        shoe.scale.set(1.14, 1.0, 0.74);

        shoe.position.set(0, -0.82, 0.055);

        legPivot.add(thigh, knee, calf, shoe);

        return legPivot;

      };



      const leftLegPivot = buildSculptedHumanLeg(-1, 'LeftUpLeg');

      const rightLegPivot = buildSculptedHumanLeg(1, 'RightUpLeg');

      sculptedHumanGroup.add(leftLegPivot, rightLegPivot);



      const gearGroup = new THREE.Group();

      bodyGroup.add(gearGroup);



      // Initialize THREE.AnimationMixer with 12-state procedural human clips on sculptedHumanGroup

      let mixer = null;

      const mixerActions = {};

      try {

        mixer = new THREE.AnimationMixer(sculptedHumanGroup);

        const procClips = buildProceduralHumanAnimationClips(THREE);

        Object.entries(procClips).forEach(([stKey, clip]) => {

          mixerActions[stKey] = mixer.clipAction(clip);

        });

        if (mixerActions.IDLE) mixerActions.IDLE.play();

      } catch (_) {}



      const charParts = {

        root,

        sculptedHumanGroup,

        gltfModelRoot: sculptedHumanGroup,

        isGltfLoaded: true,

        assetUrl: assetMeta.assetUrl,

        mixer,

        mixerActions,

        activeClipName: 'human_idle',

        bodyGroup,

        torsoMesh,

        headGroup,

        helmetMesh,

        visorMesh,

        chestCore,

        leftArmPivot,

        rightArmPivot,

        leftLegPivot,

        rightLegPivot,

        gearGroup,

        auraRing,

        auraMat,

        suitMat,

        visorMat,

        skinHex,

        hairHex,

        trousersHex

      };



      return charParts;

    }



    function ensureGltfHumanAssetsLoaded(THREE, onReadyCallback) {

      if (GLTF_ASSET_CACHE.loaded) {

        if (onReadyCallback) onReadyCallback();

        return;

      }

      if (!THREE || typeof THREE.GLTFLoader === 'undefined' || typeof THREE.SkeletonUtils === 'undefined') {

        return;

      }

      GLTF_ASSET_CACHE.callbacks = GLTF_ASSET_CACHE.callbacks || [];

      if (onReadyCallback) GLTF_ASSET_CACHE.callbacks.push(onReadyCallback);

      if (GLTF_ASSET_CACHE.loading) return;

      GLTF_ASSET_CACHE.loading = true;



      const loader = new THREE.GLTFLoader();

      const apiBaseClean = (typeof API_BASE === 'string' && API_BASE) ? API_BASE.replace(/\/$/, '') : DEFAULT_TUNNEL_URL;

      const isSurgeHost = window.location.hostname.includes('surge.sh');

      const assetsToLoad = [

        {

          key: './assets/Xbot.glb',

          fallbacks: isSurgeHost

            ? [`${apiBaseClean}/assets/Xbot.glb`, 'https://threejs.org/examples/models/gltf/Xbot.glb', './assets/Xbot.glb']

            : ['./assets/Xbot.glb', `${apiBaseClean}/assets/Xbot.glb`, 'https://threejs.org/examples/models/gltf/Xbot.glb']

        },

        {

          key: './assets/Michelle.glb',

          fallbacks: isSurgeHost

            ? [`${apiBaseClean}/assets/Michelle.glb`, 'https://threejs.org/examples/models/gltf/Michelle.glb', './assets/Michelle.glb']

            : ['./assets/Michelle.glb', `${apiBaseClean}/assets/Michelle.glb`, 'https://threejs.org/examples/models/gltf/Michelle.glb']

        }

      ];

      let remaining = assetsToLoad.length;



      function finishOne() {

        remaining -= 1;

        if (remaining <= 0) {

          GLTF_ASSET_CACHE.loaded = Object.keys(GLTF_ASSET_CACHE.modelsByUrl).length > 0;

          GLTF_ASSET_CACHE.loading = false;

          (GLTF_ASSET_CACHE.callbacks || []).forEach(cb => {

            try { cb(); } catch (_) {}

          });

          GLTF_ASSET_CACHE.callbacks = [];

        }

      }



      function tryLoadAsset(key, candidates) {

        if (!candidates || candidates.length === 0) {

          finishOne();

          return;

        }

        loader.load(

          candidates[0],

          (gltf) => {

            GLTF_ASSET_CACHE.modelsByUrl[key] = gltf;

            (gltf.animations || []).forEach(clip => {

              const nm = (clip.name || '').toLowerCase();

              GLTF_ASSET_CACHE.sharedClips[nm] = clip;

            });

            finishOne();

          },

          undefined,

          () => {

            tryLoadAsset(key, candidates.slice(1));

          }

        );

      }



      assetsToLoad.forEach(item => {

        tryLoadAsset(item.key, item.fallbacks);

      });

    }



        const ROLE_OUTFIT_STYLES = {

      RESEARCH_AGENT: {

        outfitNameVi: 'Áo Blouse Trắng-Cyan',

        jacketHex: 0x06b6d4,

        shirtHex: 0xf8fafc,

        tieHex: 0x0284c7,

        pantsHex: 0x0f172a,

        shoeHex: 0xf8fafc,

        skinHex: 0xf5cba7,

        hairHex: 0x1e293b,

        headAccessory: 'VISOR_GLASSES'

      },

      PRODUCT_AGENT: {

        outfitNameVi: 'Vest Xanh Hoàng Gia',

        jacketHex: 0x2563eb,

        shirtHex: 0xffffff,

        tieHex: 0xdc2626,

        pantsHex: 0xd6d3d1,

        shoeHex: 0x451a03,

        skinHex: 0xf1c27d,

        hairHex: 0x3b2314,

        headAccessory: 'GLASSES'

      },

      CODING_AGENT: {

        outfitNameVi: 'Hoodie Tím Indigo',

        jacketHex: 0x4f46e5,

        shirtHex: 0x38bdf8,

        tieHex: 0x818cf8,

        pantsHex: 0x1e293b,

        shoeHex: 0xe2e8f0,

        skinHex: 0xe8b490,

        hairHex: 0x0f172a,

        headAccessory: 'HEADPHONES'

      },

      MARKETING_AGENT: {

        outfitNameVi: 'Blazer Tím Thời Trang',

        jacketHex: 0xa855f7,

        shirtHex: 0xfdf4ff,

        tieHex: 0xec4899,

        pantsHex: 0xf1f5f9,

        shoeHex: 0x581c87,

        skinHex: 0xf7d4bc,

        hairHex: 0x451a03,

        headAccessory: 'BERET'

      },

      SALES_AGENT: {

        outfitNameVi: 'Suit Xanh Ngọc Lục Bảo',

        jacketHex: 0x0d9488,

        shirtHex: 0xffffff,

        tieHex: 0xfbbf24,

        pantsHex: 0x111827,

        shoeHex: 0x090d16,

        skinHex: 0xdfb18b,

        hairHex: 0x18181b,

        headAccessory: 'EXEC_GLASSES'

      },

      CUSTOMER_SUPPORT_AGENT: {

        outfitNameVi: 'Đồng Phục Cam Vàng CSKH',

        jacketHex: 0xf59e0b,

        shirtHex: 0xffffff,

        tieHex: 0x0284c7,

        pantsHex: 0x1e3a8a,

        shoeHex: 0x1e293b,

        skinHex: 0xf5ceb0,

        hairHex: 0x3f2e21,

        headAccessory: 'HEADSET'

      },

      FINANCE_AGENT: {

        outfitNameVi: 'Vest Xanh Lá & Cà Vạt Vàng',

        jacketHex: 0x10b981,

        shirtHex: 0xffffff,

        tieHex: 0xfacc15,

        pantsHex: 0xcbd5e1,

        shoeHex: 0x064e3b,

        skinHex: 0xebbfa0,

        hairHex: 0x1c1917,

        headAccessory: 'EXEC_GLASSES'

      },

      OPTIMIZATION_AGENT: {

        outfitNameVi: 'Vest Đỏ Hồng Điều Hành',

        jacketHex: 0xec4899,

        shirtHex: 0xffffff,

        tieHex: 0xfbbf24,

        pantsHex: 0x0f172a,

        shoeHex: 0x831843,

        skinHex: 0xf6d2b8,

        hairHex: 0x4c1d95,

        headAccessory: 'CROWN_VISOR'

      },

      SECURITY_AGENT: {

        outfitNameVi: 'Quân Phục An Ninh Đỏ Đô',

        jacketHex: 0xdc2626,

        shirtHex: 0x111827,

        tieHex: 0xfbbf24,

        pantsHex: 0x090d16,

        shoeHex: 0x000000,

        skinHex: 0xd9a782,

        hairHex: 0x090d16,

        headAccessory: 'SECURITY_BERET'

      },

      AFFILIATE_AMAZON_AGENT: {

        outfitNameVi: 'Blazer Cam Amazon Prime',

        jacketHex: 0xf97316,

        shirtHex: 0xffffff,

        tieHex: 0xfacc15,

        pantsHex: 0x0f172a,

        shoeHex: 0x7c2d12,

        skinHex: 0xf6d2b8,

        hairHex: 0x27170e,

        headAccessory: 'CROWN_VISOR'

      },

      SHOPIFY_ECOM_AGENT: {

        outfitNameVi: 'Vest Xanh Shopify Partner',

        jacketHex: 0x65a30d,

        shirtHex: 0xf8fafc,

        tieHex: 0xbef264,

        pantsHex: 0x1e293b,

        shoeHex: 0x14532d,

        skinHex: 0xebbfa0,

        hairHex: 0x18181b,

        headAccessory: 'EXEC_GLASSES'

      },

      CRYPTO_ARBITRAGE_AGENT: {

        outfitNameVi: 'Suit Vàng Binance Quant',

        jacketHex: 0xd97706,

        shirtHex: 0x111827,

        tieHex: 0xfef08a,

        pantsHex: 0x0f172a,

        shoeHex: 0x451a03,

        skinHex: 0xe8b490,

        hairHex: 0x0f172a,

        headAccessory: 'VISOR_GLASSES'

      },

      AIRDROP_BOUNTY_AGENT: {

        outfitNameVi: 'Áo Khoác Web3 Cyber Blue',

        jacketHex: 0x0284c7,

        shirtHex: 0xe0f2fe,

        tieHex: 0x38bdf8,

        pantsHex: 0x0f172a,

        shoeHex: 0x0c4a6e,

        skinHex: 0xf7d4bc,

        hairHex: 0x3f2314,

        headAccessory: 'HEADPHONES'

      },

      VIRAL_TRAFFIC_AGENT: {

        outfitNameVi: 'Blazer Hồng Tím Growth Hacker',

        jacketHex: 0xc026d3,

        shirtHex: 0xffffff,

        tieHex: 0xf472b6,

        pantsHex: 0x1e1b4b,

        shoeHex: 0x4a044e,

        skinHex: 0xdfb18b,

        hairHex: 0x1e1b4b,

        headAccessory: 'HEADSET'

      },

      TEMPLATE_POD_AGENT: {

        outfitNameVi: 'Áo Studio Xanh Ngọc Mint',

        jacketHex: 0x0d9488,

        shirtHex: 0xf0fdfa,

        tieHex: 0x5eead4,

        pantsHex: 0x1e293b,

        shoeHex: 0x134e4a,

        skinHex: 0xf5ceb0,

        hairHex: 0x451a03,

        headAccessory: 'BERET'

      }

    };



    function dressGltfHumanCharacterWithDistinctOutfit(THREE, clonedScene, cfg) {

      const style = ROLE_OUTFIT_STYLES[cfg.role] || ROLE_OUTFIT_STYLES.RESEARCH_AGENT;

      const cJacket = new THREE.Color(style.jacketHex);

      const cShirt = new THREE.Color(style.shirtHex);

      const cTie = new THREE.Color(style.tieHex);

      const cPants = new THREE.Color(style.pantsHex);

      const cShoe = new THREE.Color(style.shoeHex);

      const cSkin = new THREE.Color(style.skinHex);

      const cHair = new THREE.Color(style.hairHex);

      const cBelt = new THREE.Color(0x0f172a);

      const cBuckle = new THREE.Color(0xfbbf24);



      clonedScene.traverse(node => {

        if (!node.isMesh || !node.geometry) return;

        const matName = ((node.material && node.material.name) || node.name || '').toLowerCase();

        if (matName.includes('joint')) {

          node.material = new THREE.MeshStandardMaterial({

            color: style.jacketHex,

            roughness: 0.45,

            metalness: 0.2

          });

          return;

        }

        try {

          const geom = node.geometry.clone();

          geom.computeBoundingBox();

          const bb = geom.boundingBox;

          const posAttr = geom.attributes.position;

          if (bb && posAttr && posAttr.count > 0) {

            const minY = bb.min.y;

            const maxY = bb.max.y;

            const spanY = Math.max(0.001, maxY - minY);

            const maxAbsX = Math.max(0.001, Math.max(Math.abs(bb.min.x), Math.abs(bb.max.x)));

            const minZ = bb.min.z;

            const maxZ = bb.max.z;

            const midZ = (minZ + maxZ) * 0.5;

            const spanZ = Math.max(0.001, maxZ - minZ);



            const colors = new Float32Array(posAttr.count * 3);

            for (let i = 0; i < posAttr.count; i++) {

              const vx = posAttr.getX(i);

              const vy = posAttr.getY(i);

              const vz = posAttr.getZ(i);

              const ny = (vy - minY) / spanY; // 0.0 (feet) -> 1.0 (top of head)

              const nx = Math.abs(vx) / maxAbsX; // 0.0 (spine) -> 1.0 (hands in T-pose)

              const nz = (vz - midZ) / spanZ;



              let chosen = cJacket;

              if (ny >= 0.915 || (ny >= 0.858 && nz < -0.04)) {

                chosen = cHair;

              } else if (ny >= 0.818) {

                chosen = cSkin;

              } else if (nx > 0.35) {

                // Hands / wrists in T-pose

                chosen = nx > 0.39 ? cSkin : cShirt;

              } else if (ny >= 0.505 && ny < 0.818) {

                // Torso + Blazer/Jacket + Shirt V-Neck + Tie

                if (ny >= 0.61 && nx < 0.032 && nz > 0.02) {

                  chosen = cTie;

                } else if (ny >= 0.65 && nx < 0.095 && nz > 0.02) {

                  chosen = cShirt;

                } else {

                  chosen = cJacket;

                }

              } else if (ny >= 0.475 && ny < 0.505) {

                chosen = nx < 0.05 && nz > 0 ? cBuckle : cBelt;

              } else if (ny >= 0.085 && ny < 0.475) {

                chosen = cPants;

              } else {

                chosen = cShoe;

              }

              colors[i * 3] = chosen.r;

              colors[i * 3 + 1] = chosen.g;

              colors[i * 3 + 2] = chosen.b;

            }

            geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

            node.geometry = geom;

            node.material = new THREE.MeshStandardMaterial({

              color: 0xffffff,

              vertexColors: true,

              roughness: 0.42,

              metalness: 0.12

            });

          }

        } catch (_) {}

      });



      // Attach 3D bone-parented outfit details (Tie/Badge on Spine2 & Hair/Headgear on Head)

      try {

        let spineBone = null;

        let headBone = null;

        clonedScene.traverse(b => {

          if (b.isBone) {

            const bn = (b.name || '').toLowerCase();

            if (!spineBone && (bn.includes('spine2') || bn.includes('spine1'))) spineBone = b;

            if (!headBone && bn.includes('head') && !bn.includes('top')) headBone = b;

          }

        });

        if (spineBone) {

          // Determine bone local scale (Mixamo Xbot bones are in cm ~100x, or m ~1x)

          const bs = (spineBone.position.length() > 2 ? 1.0 : 0.01) * 0.32;

          const badgeMat = new THREE.MeshBasicMaterial({ color: style.tieHex });

          const lapelMat = new THREE.MeshStandardMaterial({ color: style.shirtHex, roughness: 0.35 });

          const jacketWrapMat = new THREE.MeshStandardMaterial({ color: style.jacketHex, roughness: 0.4, metalness: 0.15 });



          // Fitted 3D Vest/Blazer Chest Accent & Lanyard ID Badge

          const vestAccent = new THREE.Mesh(new THREE.BoxGeometry(28 * bs, 24 * bs, 19 * bs), jacketWrapMat);

          vestAccent.position.set(0, 4 * bs, 0);

          const shirtV = new THREE.Mesh(new THREE.BoxGeometry(10 * bs, 16 * bs, 20.2 * bs), lapelMat);

          shirtV.position.set(0, 8 * bs, 0.5 * bs);

          const tieMesh = new THREE.Mesh(new THREE.BoxGeometry(3.8 * bs, 18 * bs, 21.0 * bs), badgeMat);

          tieMesh.position.set(0, 5 * bs, 0.8 * bs);

          const idCard = new THREE.Mesh(new THREE.BoxGeometry(5.5 * bs, 7.2 * bs, 21.2 * bs), new THREE.MeshBasicMaterial({ color: 0xffffff }));

          idCard.position.set(7.5 * bs, 6 * bs, 0.8 * bs);

          spineBone.add(vestAccent, shirtV, tieMesh, idCard);

        }

        if (headBone) {

          const hs = (headBone.position.length() > 2 ? 1.0 : 0.01) * 0.38;

          const hairCap = new THREE.Mesh(

            new THREE.SphereGeometry(11.5 * hs, 14, 12),

            new THREE.MeshStandardMaterial({ color: style.hairHex, roughness: 0.5 })

          );

          hairCap.position.set(0, 8.5 * hs, -1.5 * hs);

          hairCap.scale.set(1.02, 0.78, 1.08);

          headBone.add(hairCap);



          if (style.headAccessory === 'BERET' || style.headAccessory === 'SECURITY_BERET') {

            const beret = new THREE.Mesh(

              new THREE.CylinderGeometry(11 * hs, 10 * hs, 4.5 * hs, 16),

              new THREE.MeshStandardMaterial({ color: style.jacketHex, roughness: 0.4 })

            );

            beret.position.set(1.5 * hs, 14 * hs, 0);

            beret.rotation.z = -0.18;

            headBone.add(beret);

          } else if (style.headAccessory === 'HEADPHONES' || style.headAccessory === 'HEADSET') {

            const bandMat = new THREE.MeshBasicMaterial({ color: style.tieHex });

            const earL = new THREE.Mesh(new THREE.CylinderGeometry(3.8 * hs, 3.8 * hs, 3.0 * hs, 12), bandMat);

            earL.rotation.z = Math.PI / 2;

            earL.position.set(-11.2 * hs, 4 * hs, 0);

            const earR = earL.clone();

            earR.position.set(11.2 * hs, 4 * hs, 0);

            headBone.add(earL, earR);

          } else {

            // Smart Glasses / Visor Frame

            const visor = new THREE.Mesh(

              new THREE.BoxGeometry(17 * hs, 3.2 * hs, 4 * hs),

              new THREE.MeshBasicMaterial({ color: style.tieHex })

            );

            visor.position.set(0, 4.5 * hs, 9.8 * hs);

            headBone.add(visor);

          }

        }

      } catch (_) {}

    }



    function attachRiggedGltfHumanCharacterIfAvailable(THREE, cfg, charParts, assetMeta) {

      ensureGltfHumanAssetsLoaded(THREE, () => {

        const srcGltf = GLTF_ASSET_CACHE.modelsByUrl[assetMeta.assetUrl] || GLTF_ASSET_CACHE.modelsByUrl['./assets/Xbot.glb'];

        if (!srcGltf || !srcGltf.scene || !THREE.SkeletonUtils) return;

        try {

          const clonedScene = THREE.SkeletonUtils.clone(srcGltf.scene);

          const scale = assetMeta.heightScale || 1.45;

          clonedScene.scale.set(scale, scale, scale);

          clonedScene.position.set(0, 0, 0);

          clonedScene.userData = { pickType: 'AGENT', role: cfg.role };



          // Dress each of the 9 AI Employees in a distinct, high-contrast tailored outfit (Jacket/Blazer/Hoodie/Coat + Shirt/Tie + Trousers + Shoes + Role Headgear)

          dressGltfHumanCharacterWithDistinctOutfit(THREE, clonedScene, cfg);

          clonedScene.traverse(node => {

            if (node.isMesh) {

              node.userData = { pickType: 'AGENT', role: cfg.role };

              WORLD_3D.pickableMeshes.push(node);

            }

          });



          charParts.root.add(clonedScene);

          charParts.gltfModelRoot = clonedScene;

          charParts.isGltfLoaded = true;

          // Hide fallback sculpted mesh so only the high-quality skinned GLTF human character renders in WebGL

          charParts.sculptedHumanGroup.visible = true;



          // Build GLTF skeletal AnimationMixer mapped across all 12 states

          const gltfMixer = new THREE.AnimationMixer(clonedScene);

          const clips = GLTF_ASSET_CACHE.sharedClips || {};

          const idleClip = clips['idle'] || (srcGltf.animations && srcGltf.animations[0]);

          const walkClip = clips['walk'] || idleClip;

          const runClip = clips['run'] || walkClip;

          const talkClip = clips['agree'] || idleClip;

          const errorClip = clips['headshake'] || clips['sad_pose'] || idleClip;

          const workClip = clips['idle'] || walkClip;



          const mapStateToClip = {

            IDLE: idleClip,

            WALK: walkClip,

            RUN: runClip,

            SIT: workClip,

            WORK: workClip,

            WORK_AT_DESK: workClip,

            TYPE: workClip,

            READ: workClip,

            TALK: talkClip,

            LISTEN: idleClip,

            MEETING: talkClip,

            CELEBRATE: talkClip,

            NEEDS_ASSISTANCE: errorClip,

            ERROR: errorClip,

            OFFLINE: idleClip

          };



          const gltfActions = {};

          Object.entries(mapStateToClip).forEach(([stKey, clipObj]) => {

            if (clipObj) {

              gltfActions[stKey] = gltfMixer.clipAction(clipObj);

            }

          });

          charParts.mixer = gltfMixer;

          charParts.mixerActions = gltfActions;



          const ch = WORLD_3D.charactersByRole[cfg.role];

          const curState = normalizeAnimStateName(ch ? ch.animState : 'IDLE');

          if (gltfActions[curState]) {

            gltfActions[curState].reset().fadeIn(0.2).play();

            charParts.activeClipName = gltfActions[curState].getClip().name;

          }

        } catch (err) {

          const ch = WORLD_3D.charactersByRole[cfg.role];

          if (ch) ch.lastMovementError = `GLTF clone fallback: ${err.message}`;

        }

      });

    }



    function transitionCharacterAnimState(ch, nextRawState) {

      if (!ch) return;

      const nextState = normalizeAnimStateName(nextRawState);

      const prevState = normalizeAnimStateName(ch.animState || 'IDLE');

      ch.animState = nextRawState;

      ch.normalizedAnimState = nextState;

      ch.lastStateUpdateAt = new Date().toISOString();



      if (ch.parts && ch.parts.mixer && ch.parts.mixerActions) {

        const actions = ch.parts.mixerActions;

        const nextAction = actions[nextState] || actions.IDLE;

        const prevAction = actions[prevState];

        if (nextAction && nextAction !== prevAction) {

          try {

            if (prevAction) prevAction.fadeOut(0.22);

            nextAction.reset().fadeIn(0.22).play();

            ch.parts.activeClipName = nextAction.getClip ? nextAction.getClip().name : nextState.toLowerCase();

          } catch (_) {}

        } else if (nextAction && !nextAction.isRunning()) {

          try {

            nextAction.play();

            ch.parts.activeClipName = nextAction.getClip ? nextAction.getClip().name : nextState.toLowerCase();

          } catch (_) {}

        }

      }

      if (ch.parts && ch.parts.gltfModelRoot) {

        const isSeated = ['SIT', 'WORK', 'WORK_AT_DESK', 'TYPE', 'READ', 'MEETING'].includes(nextState);

        ch.parts.gltfModelRoot.position.y = isSeated ? -0.18 : 0.0;

      }

    }



    


// Explicit public entry points used by HTML controls and the reference dashboard.
Object.assign(window, {
  analyzeFreelanceJob, checkPublicPaymentReportStatus, clearAdminKeySession, closeLiveGithubWebAppModal,
  closeVisitorBuyCheckoutModal, closeVisitorDonationPaymentGate, collapseToTop5GithubWebApps,
  createRealOrder, downloadPrimaryToolkit, generateMarketingForPrimaryProduct,
  openLiveGithubWebAppModal, openVisitorBuyCheckoutModal, openVisitorDonationPaymentGate,
  pauseSystem, promptUpdateAadsUnitId, proposeNewDynamicEmployee, refreshAllData, resetApiBase, resumeSystem,
  runInteractiveAuditDemo, runLiveInternetScan, runOrchestratorCycle, saveAdminKeyToSession, saveCustomApiBase,
  saveOwnerPayoutPolicy, saveProductPriceUpdate, selectInternationalDonationUsd, selectVietnamDonationVnd,
  sendQuickVisitorNotebookQuestion, setAppLanguage, showAllGithubWebApps, showMoreGithubWebApps,
  submitCustomerBankProof, submitPublicAdvertisingInquiry, submitPublicDonation, submitVisitorNotebookInteraction,
  submitVisitorQuickCheckoutOrder, switchCheckoutPaymentTab, switchOverviewMode, switchView, toggleLivePolling,
  toggleMobileSidebar, togglePortalAdminAccessModal, toggleReducedMotion, toggleVisitorGeoSimulationMode,
  triggerAutoApproveAllLeadsNow, triggerEmergencyStopPrompt, triggerGithubWebFactoryScanNow, updateBudgetSettings,
  ownerReconcileBankTransfer, verifyBscTransaction, verifyPublicPaymentReportByAdmin
});
