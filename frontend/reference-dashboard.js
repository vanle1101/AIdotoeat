/* AUTOProfit reference dashboard: live data only, no presentation fixtures. */
(function () {
  'use strict';

  const icons = {
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    user: '<circle cx="12" cy="7" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    megaphone: '<path d="m3 11 15-6v14L3 13zM18 8a4 4 0 0 1 0 8M6 14l2 6h4l-2-5"/>',
    box: '<path d="m12 2 9 5v10l-9 5-9-5V7zM3 7l9 5 9-5M12 12v10"/>',
    cart: '<circle cx="9" cy="20" r="1"/><circle cx="19" cy="20" r="1"/><path d="M2 3h2l3 13h13l2-9H5"/>',
    chart: '<path d="M3 21h18M6 18v-6M11 18V8M16 18V5M21 18v-9"/><path d="m4 10 6-4 5 2 6-5"/>',
    file: '<path d="M6 2h8l5 5v14H6zM14 2v5h5M9 12h7M9 16h7"/>',
    database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    coins: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    globe: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M5 5c4 3 10 3 14 0M5 19c4-3 10-3 14 0"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 2v6M17 2v6M3 10h18"/>',
    bot: '<rect x="4" y="7" width="16" height="13" rx="4"/><path d="M12 3v4M9 3h6M1 13h3M20 13h3"/><circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/><path d="M9 17h6"/>',
    send: '<path d="m22 2-7 20-4-9-9-4Z M22 2 11 13"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M19 13.5 21 12l-2-1.5-.5-2 1-2-2-2-2 1-2-.5L12 2l-1.5 2-2 .5-2-1-2 2 1 2-.5 2L2 12l2 1.5.5 2-1 2 2 2 2-1 2 .5L12 22l1.5-2 2-.5 2 1 2-2-1-2z"/>',
    expand: '<path d="M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    activity: '<path d="M2 12h4l3-7 5 14 3-7h5"/>',
    headset: '<path d="M3 14v-2a9 9 0 0 1 18 0v2M3 14v5h4v-7H3M21 14v5h-4v-7h4M17 21h-4"/>',
    paperclip: '<path d="m21 11-9 9a6 6 0 0 1-8-8l9-9a4 4 0 0 1 6 6l-9 9a2 2 0 0 1-3-3l8-8"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    close: '<path d="m18 6-12 12M6 6l12 12"/>'
  };
  const svg = (name, className = '') => `<svg class="ap-icon ${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.activity}</svg>`;

  if (document.body) document.body.classList.add('ap-reference-ui');

  const nav = [
    ['overview', 'home', 'Tổng Quan', 'Bảng điều hành chính'],
    ['agents', 'users', 'Nhân Sự AI', 'AI Agent & Tự động hóa'],
    ['opportunities', 'megaphone', 'Cơ Hội', 'Thị trường & Dự án'],
    ['leads', 'users', 'Khách Hàng', 'Tiềm năng & Đề xuất'],
    ['products', 'box', 'Sản Phẩm', 'Web App & Landing Page'],
    ['orders', 'cart', 'Đơn Hàng', 'Khách hàng & Thanh toán'],
    ['marketing', 'chart', 'Mạng QC & SEO', 'Nội dung & Tăng trưởng'],
    ['analytics', 'file', 'Báo Cáo', 'Thống kê & Phân tích']
  ];
  const viewCopy = {
    overview: ['Tổng quan', 'Trung tâm điều hành AI', 'Số liệu lấy từ nguồn đã kết nối; mục chưa có nguồn được đánh dấu rõ.'],
    agents: ['Nhân sự AI', 'Điều phối & giám sát', 'Danh mục vai trò và nhiệm vụ được ghi nhận từ backend'],
    opportunities: ['Cơ hội kinh doanh', 'Quét thị trường', 'Nguồn cơ hội chưa kết nối'],
    leads: ['Khách hàng', 'Tiềm năng & đề xuất', 'Dữ liệu khách hàng chỉ hiển thị sau xác thực quản trị'],
    products: ['Sản phẩm', 'Web App & dịch vụ', 'Danh mục ứng dụng đang có trong hệ thống'],
    orders: ['Đơn hàng', 'Thanh toán & đối soát', 'Giao dịch đã ghi nhận trong cơ sở dữ liệu'],
    marketing: ['Mạng QC & SEO', 'Tăng trưởng nội dung', 'Nguồn chiến dịch chưa kết nối'],
    automation: ['Tự động hóa', 'Quy trình vận hành', 'Chỉ hiển thị tác vụ thực tế được backend ghi lại'],
    analytics: ['Báo cáo', 'Phân tích dữ liệu', 'Traffic được đo từ trình duyệt; nguồn tài chính chưa kết nối'],
    security: ['Cài đặt', 'Bảo mật & hệ thống', 'Quản lý quyền truy cập và thiết lập hệ thống']
  };
  const metricDefs = [
    { key: 'revenue_usd', icon: 'database', label: 'TỔNG DOANH THU', color: 'cyan', kind: 'currency', note: 'Giao dịch đã xác nhận' },
    { key: 'ad_revenue_usd', icon: 'megaphone', label: 'DOANH THU QUẢNG CÁO', color: 'violet', kind: 'currency', note: 'Nguồn mạng quảng cáo' },
    { key: 'ai_token_cost_usd', icon: 'coins', label: 'CHI PHÍ TOKEN AI', color: 'pink', kind: 'currency', note: 'Usage từ nhà cung cấp' },
    { key: 'active_agents', icon: 'user', label: 'AGENT ĐANG THỰC THI', color: 'blue', kind: 'count', note: 'Vai trò có task RUNNING' },
    { key: 'monetized_views', icon: 'eye', label: 'LƯỢT XEM KIẾM TIỀN', color: 'gold', kind: 'count', note: 'Không đồng nhất với pageview' },
    { key: 'international_pageviews', icon: 'globe', label: 'TRUY CẬP QUỐC TẾ', color: 'cyan', kind: 'count', note: 'Cần nguồn địa lý hợp lệ' }
  ];

  let summary = null;
  let feedEvents = [];
  let commandCenter = null;
  let activityAbortController = null;
  let activityReconnectTimer = 0;
  let commandStartObserver = null;
  let commandStartQueued = false;
  let commandStartPromise = null;
  let threeRuntimePromise = null;
  let feedState = 'connecting';
  let activitySourceStatus = 'unknown';
  let zonePanelOpen = false;
  let selectedObjectInfo = null;
  let chartPoints = [];
  let chartIndex = -1;
  let activityBeforeId = null;

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  }

  function formatNumber(value) {
    return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(value);
  }

  function ownerAdminKey() {
    if (window.location.protocol !== 'https:') return '';
    try { return sessionStorage.getItem('autoprofit_owner_admin_key') || ''; } catch (_) { return ''; }
  }

  function ownerHeaders() {
    const key = ownerAdminKey();
    return key ? { 'X-Admin-Key': key } : {};
  }

  function formatMetric(metric) {
    const item = summary?.metrics?.[metric.key];
    if (!item) return { value: 'Chưa có dữ liệu', note: metric.note, status: 'unknown' };
    const status = item.status || 'unknown';
    if (status === 'not_connected') return { value: 'Chưa kết nối', note: metric.note, status };
    if (status === 'owner_auth_required') return { value: 'Cần xác thực chủ sở hữu', note: metric.note, status };
    if (status === 'degraded_demo') return { value: 'Demo', note: metric.note, status };
    if (status === 'pending_review') return { value: 'Chờ duyệt', note: metric.note, status };
    if (status === 'insufficient_coverage') return { value: 'Chưa đủ dữ liệu', note: metric.note, status };
    if (status === 'error') return { value: 'Lỗi nguồn dữ liệu', note: metric.note, status };
    if (status === 'no_verified_records' || status === 'no_data' || status === 'no_verified_amounts') return { value: 'Chưa có dữ liệu', note: metric.note, status };
    const raw = metric.kind === 'currency' ? item.value_usd : item.value;
    if (raw === null || raw === undefined || !Number.isFinite(Number(raw))) return { value: 'Chưa có dữ liệu', note: metric.note, status };
    const value = metric.kind === 'currency'
      ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(raw))
      : formatNumber(Number(raw));
    let note = metric.note;
    if (status === 'partial_coverage' && item.coverage_start) note = `Ghi nhận từ ${formatDate(item.coverage_start)}`;
    return { value, note, status };
  }

  function metricMarkup(metric, index) {
    const display = formatMetric(metric);
    return `<article class="ap-metric ap-${metric.color}" data-metric="${metric.key}"><div class="ap-metric-top"><span class="ap-metric-icon">${svg(metric.icon)}</span><div class="ap-metric-text"><div class="ap-metric-label">${metric.label}</div><div class="ap-metric-line"><strong id="apMetric${index}" data-status="${display.status}">${escapeHtml(display.value)}</strong></div><small>${escapeHtml(display.note)}</small></div></div><div class="ap-metric-source">${escapeHtml(sourceLabel(summary?.metrics?.[metric.key]?.source, display.status))}</div></article>`;
  }

  function sourceLabel(source, status) {
    if (status === 'not_connected') return 'Nguồn chưa kết nối';
    if (status === 'owner_auth_required') return 'Cần xác thực chủ sở hữu';
    if (status === 'degraded_demo') return 'Demo · degraded mode';
    if (status === 'pending_review') return 'Pending review';
    if (status === 'error') return 'Nguồn đang lỗi';
    if (status === 'no_verified_records') return 'Chưa có bản ghi xác thực';
    if (source === 'transactions') return 'SQLite · giao dịch xác nhận';
    if (source === 'core.tasks') return 'SQLite · task runtime';
    if (source === 'telemetry_pageviews') return 'First-party telemetry';
    if (source === 'telemetry_sessions') return 'Heartbeat trình duyệt';
    return 'Đang chờ nguồn dữ liệu';
  }

  function init() {
    const sidebar = document.getElementById('sidebar');
    const topbar = document.querySelector('.topbar');
    const overview = document.getElementById('view-overview');
    if (!sidebar || !topbar || !overview) return;

    sidebar.insertAdjacentHTML('beforeend', `<div class="ap-sidebar-shell"><div class="ap-brand"><button type="button" class="ap-brand-mark" aria-label="AUTOProfit AI"><img src="/logo.svg" alt=""/></button><div class="ap-brand-copy"><div><span>AUTO</span><span>Profit</span><br/>AI</div><small>CÔNG TY AI TỰ ĐỘNG<br/>KIẾM TIỀN ONLINE</small></div></div><nav class="ap-side-nav" aria-label="Điều hướng chính">${nav.map(([view, icon, title, sub]) => `<button type="button" class="ap-side-link${view === 'overview' ? ' active' : ''}" data-ap-view="${view}"><span class="ap-side-icon">${svg(icon)}</span><span><strong>${title}</strong><small>${sub}</small></span></button>`).join('')}</nav><div class="ap-sidebar-orb"><img src="/assets/sidebar-globe.webp" alt="" aria-hidden="true"/><span>AI AUTOMATION<br/>GLOBAL BUSINESS</span></div><div class="ap-sidebar-status ap-api-state"><strong><i></i><span id="apSidebarStatus">ĐANG KẾT NỐI API</span></strong><small>Phiên bản: backend API</small><small>Cập nhật: <span id="apSidebarDate">—</span></small><button type="button" aria-label="Cài đặt" data-ap-view="security">${svg('gear')}</button></div></div>`);
    sidebar.querySelector('.ap-side-nav')?.insertAdjacentHTML('afterend', `<div class="ap-side-extras"><button type="button" data-ap-view="automation">${svg('activity')} Tự động hóa</button><button type="button" data-ap-view="security">${svg('gear')} Cài đặt</button></div>`);

    const titleBox = document.getElementById('currentViewTitle')?.parentElement;
    if (titleBox) titleBox.insertAdjacentHTML('beforeend', `<div class="ap-overview-heading">Tổng quan <span>— Trung tâm điều hành AI</span></div><div class="ap-overview-tagline">Số liệu lấy từ nguồn đã kết nối; mục chưa có nguồn được đánh dấu rõ.</div>`);
    topbar.insertAdjacentHTML('beforeend', `<div class="ap-top-actions"><button type="button" class="ap-top-pill" data-ap-action="language">VN ${svg('chevron')}</button><button type="button" class="ap-top-pill ap-language-name" data-ap-action="language">Tiếng Việt ${svg('chevron')}</button><button type="button" class="ap-top-pill" data-ap-action="mobile">${svg('box')} Giao diện Mobile</button><button type="button" class="ap-icon-button" data-ap-view="security" aria-label="Cài đặt giao diện">${svg('sun')}</button><span class="ap-system-pill" id="apSystemPill"><i></i><span id="apSystemStatus">ĐANG KẾT NỐI</span></span><span class="ap-stream-state" id="apStreamState">Feed đang kết nối</span><span class="ap-clock"><strong id="apClockTime"></strong><small id="apClockDate"></small></span><button type="button" class="ap-icon-button ap-refresh-button" data-ap-action="refresh" aria-label="Đồng bộ dữ liệu" title="Đồng bộ dữ liệu">${svg('activity')}</button></div>`);

    const metricsHtml = metricDefs.map(metricMarkup).join('');
    overview.insertAdjacentHTML('afterbegin', `<div class="ap-dashboard" id="apReferenceDashboard">
      <div class="ap-metrics-row" id="apMetricsRow">${metricsHtml}</div>
      <div class="ap-traffic-row">
        <section class="ap-online-panel" aria-labelledby="apOnlineHeading"><div class="ap-online-icon">${svg('users')}</div><div class="ap-online-copy"><strong id="apOnlineHeading">PHIÊN TRÌNH DUYỆT ĐANG HOẠT ĐỘNG</strong><div><b id="apOnlineCount">—</b><span class="ap-online-status" id="apOnlineState">Đang lấy dữ liệu</span></div><small>Heartbeat trong 90 giây · không phải người dùng duy nhất</small></div><div class="ap-wave-wrap"><div class="ap-chart-top"><span>PAGEVIEW THEO THỜI GIAN</span><span id="apChartUpdated">—</span></div><svg id="apTrafficChart" viewBox="0 0 600 140" role="img" aria-label="Biểu đồ lượt xem trang theo thời gian" tabindex="0"><defs><linearGradient id="apWaveFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1edfff" stop-opacity=".28"/><stop offset="1" stop-color="#1edfff" stop-opacity="0"/></linearGradient><linearGradient id="apWaveStroke"><stop offset="0" stop-color="#2ef4ff"/><stop offset=".55" stop-color="#48a9ff"/><stop offset="1" stop-color="#b56aff"/></linearGradient></defs><path class="ap-chart-grid" d="M0 28H600M0 64H600M0 100H600M0 126H600"/><path id="apWaveArea" class="ap-wave-area" d=""/><path id="apWavePath" class="ap-wave-path" d=""/><path id="apWaveGlow" class="ap-wave-glow" d=""/><circle id="apChartPoint" class="ap-chart-point" cx="0" cy="0" r="4" hidden/></svg><div id="apChartTooltip" class="ap-chart-tooltip" role="status" hidden></div><div class="ap-chart-foot"><span id="apChartSource">Nguồn: first-party browser telemetry</span><label>Khoảng thời gian <select id="apChartWindow" aria-label="Khoảng thời gian biểu đồ"><option value="realtime">60 phút</option><option value="today" selected>Hôm nay</option><option value="7d">7 ngày</option><option value="30d">30 ngày</option></select></label></div></div></section>
        <section class="ap-traffic-period"><span>${svg('calendar')} HÔM NAY</span><b id="apTodayValue">—</b><small>Pageview đã ghi nhận</small></section>
        <section class="ap-traffic-period"><span>${svg('calendar')} 7 NGÀY</span><b id="apWeekValue">—</b><small id="apWeekNote">Pageview đã ghi nhận</small></section>
        <section class="ap-traffic-period"><span>${svg('calendar')} 30 NGÀY</span><b id="apMonthValue">—</b><small id="apMonthNote">Pageview đã ghi nhận</small></section>
        <section class="ap-world-panel" aria-label="Thống kê quốc tế"><img class="ap-world-map" src="/assets/world-traffic.webp" alt="" aria-hidden="true"><div class="ap-world-copy"><strong>THỐNG KÊ QUỐC TẾ</strong><b id="apCountryValue">Chưa kết nối</b><small>Chưa có nguồn địa lý tổng hợp đáng tin cậy</small></div></section>
      </div>
      <div class="ap-toolbar"><div class="ap-scene-tabs" id="apSceneTabs" role="tablist" aria-label="Chế độ camera">${[['3d','users','Chế độ 3D'],['panorama','box','Toàn cảnh'],['agents','user','Nhân sự AI'],['ads','megaphone','Mạng QC'],['products','box','Sản phẩm'],['live','chart','Dữ liệu Live'],['revenue','coins','Doanh thu'],['global','globe','Quốc tế']].map(([key, icon, label], i) => `<button type="button" class="${i === 0 ? 'active' : ''}" data-ap-tab="${key}" role="tab" aria-selected="${i === 0}" tabindex="${i === 0 ? '0' : '-1'}">${svg(icon)} ${label}</button>`).join('')}</div><button type="button" class="ap-reset-view" data-ap-action="reset-scene">${svg('expand')} Reset View</button></div>
      <div class="ap-workspace"><div class="ap-left-workspace"><section class="ap-command-center" id="apCommandCenter" data-view="3d" aria-label="Mô hình WebGL 3D có thể xoay và chọn công trình"><canvas id="apSceneCanvas" tabindex="0" aria-label="Mô hình căn cứ AI 3D. Kéo để orbit, cuộn để zoom, kéo phải để pan, bấm công trình để focus."></canvas><div class="ap-scene-tooltip" id="apSceneTooltip" role="tooltip" hidden></div><div class="ap-scene-heading"><span class="ap-scene-kicker">AUTOProfit AI · 3D COMMAND CENTER</span><span class="ap-scene-data-state" id="apSceneDataState">ĐANG KHỞI TẠO WEBGL</span></div><div class="ap-scene-help">Kéo xoay · Cuộn zoom · Kéo phải pan · Bấm công trình để chọn</div></section>
        <div class="ap-quick-row"><span>${svg('activity')} ĐI TỚI MODULE</span><button type="button" data-ap-view="marketing" title="Mở công cụ nội dung và SEO">Nội dung &amp; SEO</button><button type="button" data-ap-view="products" title="Mở danh mục sản phẩm">Sản phẩm</button><button type="button" data-ap-view="marketing" title="Mở trang quản lý tiếp thị">Tiếp thị</button><button type="button" data-ap-view="opportunities" title="Mở cơ hội thị trường">Cơ hội thị trường</button><button type="button" data-ap-view="analytics" title="Mở phân tích dữ liệu">Phân tích</button><button type="button" data-ap-action="export-report" title="Tải báo cáo số liệu hiện có">Xuất báo cáo</button></div>
        <div class="ap-composer"><span class="ap-composer-bot">${svg('bot')}</span><div class="ap-composer-status" role="status">Chat AI chưa kết nối workflow. Nhật ký backend khả dụng khi có sự kiện thật.</div><button type="button" class="ap-bottom-tool" data-ap-view="agents">${svg('users')} Nhật ký task</button><button type="button" class="ap-bottom-tool" data-ap-view="security">${svg('gear')} Cài đặt</button><button type="button" class="ap-icon-button ap-expand" data-ap-action="expand" aria-label="Mở rộng scene" aria-pressed="false">${svg('expand')}</button></div></div>
        <aside class="ap-activity-panel" aria-labelledby="apActivityTitle"><div class="ap-activity-heading"><strong id="apActivityTitle"><i></i> NHẬT KÝ HOẠT ĐỘNG AI</strong><span id="apFeedBadge" data-state="connecting"><i></i><span>Đang kết nối</span></span></div><div class="ap-activity-filters"><label>Trạng thái <select id="apActivityFilter"><option value="all">Tất cả</option><option value="RUNNING">Đang chạy</option><option value="PENDING">Đang xếp hàng</option><option value="WAITING_OWNER">Chờ duyệt</option><option value="DONE">Hoàn tất</option><option value="FAILED">Thất bại</option></select></label><label>Agent <select id="apAgentFilter"><option value="all">Tất cả agent</option></select></label><span id="apActivityCount">Chưa có sự kiện</span></div><aside class="ap-zone-panel" id="apZonePanel" aria-live="polite"><button type="button" class="ap-zone-close" data-ap-action="close-zone" aria-label="Đóng thông tin khu vực">${svg('close')}</button><small>VÙNG ĐƯỢC CHỌN</small><strong id="apZoneTitle">AI Command Center</strong><p id="apZoneDescription">Camera 3D và trạng thái vận hành được đồng bộ với vùng đã chọn.</p><div id="apZoneDataState">Chờ trạng thái backend</div></aside><div class="ap-activity-list" id="apActivityList" aria-live="polite"><div class="ap-empty-state"><span>${svg('activity')}</span><strong>Chưa có hoạt động được ghi nhận</strong><p>Nhật ký chỉ xuất hiện khi backend ghi một sự kiện task thực tế.</p></div></div><button type="button" class="ap-more-activity" id="apMoreActivity" disabled>Xem thêm hoạt động ${svg('arrow')}</button></aside></div>
      <div class="ap-detail-scrim" id="apDetailScrim" hidden><section class="ap-detail-drawer" role="dialog" aria-modal="true" aria-labelledby="apDetailTitle"><button type="button" class="ap-detail-close" data-ap-action="close-detail" aria-label="Đóng">${svg('close')}</button><small>CHI TIẾT SỰ KIỆN BACKEND</small><h2 id="apDetailTitle">Task</h2><div id="apDetailBody"></div></section></div>
    </div>`);

    document.addEventListener('click', handleClick);
    document.getElementById('apSceneTabs')?.addEventListener('keydown', event => {
      const current = event.target.closest('[data-ap-tab]');
      if (!current) return;
      const tabs = [...document.querySelectorAll('#apSceneTabs [data-ap-tab]')];
      const currentIndex = tabs.indexOf(current);
      let nextIndex = currentIndex;
      if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      else if (event.key === 'Home') nextIndex = 0;
      else if (event.key === 'End') nextIndex = tabs.length - 1;
      else return;
      event.preventDefault();
      tabs[nextIndex]?.focus();
      tabs[nextIndex]?.click();
    });
    document.getElementById('apChartWindow')?.addEventListener('change', event => refreshSummary(event.target.value));
    document.getElementById('apActivityFilter')?.addEventListener('change', renderActivity);
    document.getElementById('apAgentFilter')?.addEventListener('change', renderActivity);
    document.getElementById('apMoreActivity')?.addEventListener('click', loadOlderActivity);
    document.getElementById('apTrafficChart')?.addEventListener('keydown', handleChartKeydown);
    document.getElementById('apDetailScrim')?.addEventListener('click', event => { if (event.target.id === 'apDetailScrim') closeDetail(); });
    window.addEventListener('ap-owner-auth-change', () => {
      activityAbortController?.abort();
      activityAbortController = null;
      window.clearTimeout(activityReconnectTimer);
      activityReconnectTimer = 0;
      if (ownerAdminKey()) {
        feedState = 'connecting';
        connectActivityStream();
      } else {
        feedEvents = [];
        activityBeforeId = null;
        activitySourceStatus = 'owner_auth_required';
        feedState = 'owner_auth_required';
        renderActivity();
      }
    });
    document.addEventListener('fullscreenchange', () => {
      const expand = document.querySelector('.ap-expand');
      expand?.setAttribute('aria-pressed', String(document.fullscreenElement === document.getElementById('apCommandCenter')));
    });
    document.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      closeDetail();
      const scene = document.getElementById('apCommandCenter');
      if (scene?.classList.contains('ap-scene-expanded')) {
        scene.classList.remove('ap-scene-expanded');
        document.querySelector('.ap-expand')?.setAttribute('aria-pressed', 'false');
      }
    });
    const observer = new MutationObserver(syncShellState);
    document.querySelectorAll('.view-section').forEach(section => observer.observe(section, { attributes: true, attributeFilter: ['class'] }));
    document.body.classList.add('ap-reference-ui');
    syncShellState();
    updateClock();
    window.setInterval(updateClock, 1000);
    refreshSummary('today');
    connectActivityStream();
    window.setInterval(() => refreshSummary(document.getElementById('apChartWindow')?.value || 'today'), 15000);
    startCommandCenter();
  }

  function loadThreeRuntime() {
    if (window.THREE?.WebGLRenderer) return Promise.resolve(true);
    if (threeRuntimePromise) return threeRuntimePromise;
    threeRuntimePromise = new Promise(resolve => {
      const script = document.createElement('script');
      script.src = '/three.min.js?v=phase08-lazy-scene';
      script.async = true;
      script.onload = () => resolve(Boolean(window.THREE?.WebGLRenderer));
      script.onerror = () => resolve(false);
      document.head.appendChild(script);
    }).then(loaded => {
      if (!loaded) threeRuntimePromise = null;
      return loaded;
    });
    return threeRuntimePromise;
  }

  function startCommandCenter(attempt = 0) {
    if (commandCenter || commandStartQueued || commandStartPromise) return;
    const host = document.getElementById('apCommandCenter');
    if (attempt === 0 && host && 'IntersectionObserver' in window) {
      commandStartQueued = true;
      commandStartObserver = new IntersectionObserver(entries => {
        if (!entries.some(entry => entry.isIntersecting)) return;
        commandStartObserver?.disconnect();
        commandStartObserver = null;
        commandStartQueued = false;
        startCommandCenter(1);
      });
      commandStartObserver.observe(host);
      return;
    }
    commandStartPromise = (async () => {
      const loaded = await loadThreeRuntime();
      if (!loaded) {
        renderZoneStatus('unavailable');
        showSceneFallback('Bộ dựng Three.js chưa tải được.');
        return;
      }
      const factory = window.AutoProfitCommandCenter;
      if (typeof factory?.create === 'function') {
        try {
          commandCenter = factory.create({
            canvas: document.getElementById('apSceneCanvas'),
            onZoneSelect: selectZone,
            onHover: renderSceneHover,
            onStatus: renderZoneStatus
          });
          window.__AUTOProfitCommandCenter = commandCenter;
          if (!commandCenter && !document.querySelector('.ap-scene-fallback')) {
            renderZoneStatus('error');
            showSceneFallback('Không khởi tạo được WebGL. Kiểm tra tăng tốc phần cứng của trình duyệt.');
          }
        } catch (error) {
          console.error('AUTOProfit 3D command center failed to initialize.', error);
          renderZoneStatus('error');
          showSceneFallback('Không khởi tạo được WebGL. Mô hình 3D chưa thể chạy trên thiết bị này.');
        }
        return;
      }
      if (attempt < 20) {
        commandStartPromise = null;
        window.setTimeout(() => startCommandCenter(attempt + 1), 100);
        return;
      }
      renderZoneStatus('unavailable');
      showSceneFallback('Bộ dựng Three.js chưa tải được.');
    })();
  }

  function showSceneFallback(message) {
    const host = document.getElementById('apCommandCenter');
    if (!host || host.querySelector('.ap-scene-fallback')) return;
    const fallback = document.createElement('div');
    fallback.className = 'ap-scene-fallback';
    fallback.textContent = message;
    host.appendChild(fallback);
  }

  function renderSceneHover(zone, x, y, item) {
    const tooltip = document.getElementById('apSceneTooltip');
    const host = document.getElementById('apCommandCenter');
    if (!tooltip || !host) return;
    if (!zone) { tooltip.hidden = true; return; }
    const names = {
      command: 'AI Command Center', agents: 'AI Agents', ads: 'Ad Network',
      products: 'Web Apps', live: 'Data Hub', revenue: 'Affiliate & Revenue', global: 'Global Traffic'
    };
    tooltip.textContent = item?.objectType === 'workstation' || item?.objectType === 'landmark' ? item.name : names[zone] || 'Khu vực vận hành';
    tooltip.style.left = `${Math.max(10, Math.min(host.clientWidth - 190, x - 204))}px`;
    tooltip.style.top = `${Math.max(38, Math.min(host.clientHeight - 42, y - 44))}px`;
    tooltip.hidden = false;
  }

  function renderZoneStatus(state) {
    const element = document.getElementById('apSceneDataState');
    if (!element) return;
    const labels = {
      ready: 'WEBGL 3D · ĐANG HOẠT ĐỘNG',
      'webgl-unavailable': 'WEBGL KHÔNG KHẢ DỤNG',
      unavailable: 'THREE.JS CHƯA TẢI',
      error: 'LỖI KHỞI TẠO WEBGL'
    };
    element.textContent = labels[state] || 'ĐANG KHỞI TẠO WEBGL';
    if (state === 'error') showSceneFallback('Scene WebGL không vẽ được hình học 3D. Hãy kiểm tra tăng tốc phần cứng của trình duyệt.');
  }

  function syncShellState() {
    const activeView = document.querySelector('.view-section.active')?.id?.replace('view-', '') || 'overview';
    document.body.classList.toggle('ap-overview-mode', activeView === 'overview');
    document.querySelectorAll('.ap-side-link, .ap-side-extras button').forEach(button => button.classList.toggle('active', button.dataset.apView === activeView));
    const copy = viewCopy[activeView] || viewCopy.overview;
    const heading = document.querySelector('.ap-overview-heading');
    const tagline = document.querySelector('.ap-overview-tagline');
    if (heading) heading.innerHTML = `${escapeHtml(copy[0])} <span>— ${escapeHtml(copy[1])}</span>`;
    if (tagline) tagline.textContent = copy[2];
    const en = localStorage.getItem('autoprofit_lang') === 'en';
    const langName = document.querySelector('.ap-language-name');
    if (langName) langName.innerHTML = `${en ? 'English' : 'Tiếng Việt'} ${svg('chevron')}`;
  }

  function updateClock() {
    const now = new Date();
    const time = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(now);
    const date = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' }).format(now);
    const timeEl = document.getElementById('apClockTime');
    const dateEl = document.getElementById('apClockDate');
    const sideEl = document.getElementById('apSidebarDate');
    if (timeEl) timeEl.textContent = time;
    if (dateEl) dateEl.textContent = date;
    if (sideEl) sideEl.textContent = `${date.split(',').pop().trim()} ${time.slice(0, 5)}`;
  }

  function formatDate(value) {
    if (!value) return '—';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'short', timeStyle: 'short' }).format(date);
  }

  async function refreshSummary(windowName = 'today') {
    try {
      const response = await fetch(`/api/dashboard/summary?window=${encodeURIComponent(windowName)}`, { cache: 'no-store', credentials: 'same-origin' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      summary = await response.json();
      renderSummary();
      setApiState(true, summary.updated_at);
    } catch (_) {
      setApiState(false);
      const count = document.getElementById('apOnlineCount');
      if (count) count.textContent = '—';
      const state = document.getElementById('apOnlineState');
      if (state) state.textContent = 'Mất kết nối API';
      const row = document.getElementById('apMetricsRow');
      if (row) row.querySelectorAll('.ap-metric-line strong').forEach(element => { element.textContent = 'Không khả dụng'; element.dataset.status = 'error'; });
      ['apTodayValue', 'apWeekValue', 'apMonthValue'].forEach(id => {
        const period = document.getElementById(id);
        if (period) { period.textContent = 'Mất kết nối'; period.dataset.status = 'error'; }
      });
      drawChart([]);
    }
  }

  function setApiState(online, timestamp) {
    const pill = document.getElementById('apSystemPill');
    const label = document.getElementById('apSystemStatus');
    const sidebar = document.getElementById('apSidebarStatus');
    const shell = document.querySelector('.ap-sidebar-shell');
    pill?.classList.toggle('ap-offline', !online);
    shell?.classList.toggle('ap-status-offline', !online);
    if (label) label.textContent = online ? 'API ĐANG KẾT NỐI' : 'MẤT KẾT NỐI API';
    if (sidebar) sidebar.textContent = online ? 'API ĐANG KẾT NỐI' : 'MẤT KẾT NỐI API';
    if (timestamp) {
      const date = document.getElementById('apSidebarDate');
      if (date) date.textContent = formatDate(timestamp);
    }
  }

  function renderSummary() {
    if (!summary || summary.status !== 'ok') return;
    const row = document.getElementById('apMetricsRow');
    if (row) row.innerHTML = metricDefs.map(metricMarkup).join('');
    const metrics = summary.metrics || {};
    const online = metrics.online_sessions;
    const onlineEl = document.getElementById('apOnlineCount');
    const onlineState = document.getElementById('apOnlineState');
    if (onlineEl) {
      onlineEl.dataset.status = online?.status || 'unknown';
      onlineEl.textContent = online && online.value != null ? formatNumber(online.value) : 'Chưa có dữ liệu';
    }
    if (onlineState) {
      onlineState.textContent = online?.status === 'observed' ? 'Telemetry đang kết nối' : 'Chưa kết nối';
      onlineState.dataset.live = String(online?.status === 'observed');
    }
    setPeriod('apTodayValue', metrics.pageviews_today);
    setPeriod('apWeekValue', metrics.pageviews_7d, 'apWeekNote');
    setPeriod('apMonthValue', metrics.pageviews_30d, 'apMonthNote');
    const country = document.getElementById('apCountryValue');
    if (country) country.textContent = metrics.countries?.status === 'observed' ? 'Đã ghi nhận' : 'Chưa kết nối';
    const updated = document.getElementById('apChartUpdated');
    if (updated) updated.textContent = `Cập nhật ${formatDate(summary.updated_at)}`;
    const chartSource = document.getElementById('apChartSource');
    const sourceName = summary.series?.source || 'chưa kết nối';
    if (chartSource) {
      chartSource.textContent = `Nguồn: ${sourceName}`;
      chartSource.title = `Nguồn: ${sourceName} · chỉ pageview trình duyệt`;
    }
    const chart = document.getElementById('apTrafficChart');
    chart?.setAttribute('aria-label', `Biểu đồ pageview trình duyệt theo thời gian. Nguồn: ${sourceName}.`);
    if (chart) chart.title = `Nguồn: ${sourceName} · chỉ pageview trình duyệt`;
    drawChart(summary.series?.points || []);
    commandCenter?.updateData?.(summary);
    updateZonePanel();
  }

  function setPeriod(id, item, noteId) {
    const value = document.getElementById(id);
    if (value) {
      value.dataset.status = item?.status || 'unknown';
      if (!item || item.value == null) value.textContent = item?.status === 'insufficient_coverage' ? 'Chưa đủ dữ liệu' : 'Chưa có dữ liệu';
      else value.textContent = formatNumber(item.value);
    }
    if (noteId && item?.coverage_start) {
      const note = document.getElementById(noteId);
      if (note) note.textContent = item.status === 'partial_coverage' ? `Ghi nhận từ ${formatDate(item.coverage_start)}` : 'Pageview đã ghi nhận';
    }
  }

  function smoothPath(points) {
    if (!points.length) return '';
    if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
    let path = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i += 1) {
      const p0 = points[Math.max(0, i - 1)];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = points[Math.min(points.length - 1, i + 2)];
      const c1x = p1.x + (p2.x - p0.x) / 6;
      const c1y = p1.y + (p2.y - p0.y) / 6;
      const c2x = p2.x - (p3.x - p1.x) / 6;
      const c2y = p2.y - (p3.y - p1.y) / 6;
      path += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
    }
    return path;
  }

  function drawChart(points) {
    const svgRoot = document.getElementById('apTrafficChart');
    const pathEl = document.getElementById('apWavePath');
    const areaEl = document.getElementById('apWaveArea');
    const glowEl = document.getElementById('apWaveGlow');
    if (!svgRoot || !pathEl || !areaEl || !glowEl) return;
    chartPoints = points;
    const known = points.filter(point => point.value !== null && point.value !== undefined);
    const maximum = Math.max(1, ...known.map(point => Number(point.value) || 0));
    const coords = points.map((point, index) => ({
      x: points.length <= 1 ? 300 : index * 600 / (points.length - 1),
      y: point.value == null ? null : 112 - (Number(point.value) / maximum) * 82,
      value: point.value,
      timestamp: point.timestamp,
      status: point.status
    }));
    const segments = [];
    let segment = [];
    coords.forEach(point => {
      if (point.y === null) { if (segment.length) segments.push(segment); segment = []; }
      else segment.push(point);
    });
    if (segment.length) segments.push(segment);
    const path = segments.map(smoothPath).filter(Boolean).join(' ');
    pathEl.setAttribute('d', path);
    glowEl.setAttribute('d', path);
    const first = segments[0]?.[0];
    const last = segments[segments.length - 1]?.[segments[segments.length - 1].length - 1];
    areaEl.setAttribute('d', first && last ? `${path} L ${last.x} 130 L ${first.x} 130 Z` : '');
    const empty = document.getElementById('apChartTooltip');
    if (known.length === 0) {
      if (empty) { empty.hidden = false; empty.textContent = 'Chưa có dữ liệu trong khoảng thời gian này'; }
      svgRoot.classList.add('ap-chart-empty');
    } else {
      svgRoot.classList.remove('ap-chart-empty');
      if (empty) empty.hidden = true;
    }
    chartIndex = -1;
  }

  function showChartPoint(index) {
    const points = chartPoints;
    if (!points.length) return;
    const bounded = Math.max(0, Math.min(points.length - 1, index));
    chartIndex = bounded;
    const item = points[bounded];
    const marker = document.getElementById('apChartPoint');
    const tooltip = document.getElementById('apChartTooltip');
    if (!marker || !tooltip) return;
    if (item.value == null) {
      marker.hidden = true;
      tooltip.hidden = false;
      tooltip.textContent = `${formatDate(item.timestamp)} · Chưa thu thập`;
      return;
    }
    const maximum = Math.max(1, ...points.filter(point => point.value != null).map(point => Number(point.value) || 0));
    marker.setAttribute('cx', points.length <= 1 ? '300' : String(bounded * 600 / (points.length - 1)));
    marker.setAttribute('cy', String(112 - (Number(item.value) / maximum) * 82));
    marker.hidden = false;
    tooltip.hidden = false;
    tooltip.textContent = `${formatDate(item.timestamp)} · ${formatNumber(item.value)} pageview`;
  }

  function activityMarkup(event) {
    const status = String(event.status || 'UNKNOWN').toUpperCase();
    const label = status === 'RUNNING' ? 'Đang chạy' : status === 'DONE' || status === 'COMPLETED' ? 'Hoàn tất' : status === 'FAILED' ? 'Thất bại' : status;
    const role = event.agent_id || 'Backend task';
    const created = formatDate(event.timestamp);
    const percent = Number(event.progress_pct);
    const progress = status === 'RUNNING' && Number.isFinite(percent) ? `<div class="ap-task-progress" aria-label="Tiến độ ${Math.max(0, Math.min(100, percent))} phần trăm"><span style="width:${Math.max(0, Math.min(100, percent))}%"></span><small>${Math.max(0, Math.min(100, percent))}%</small></div>` : '';
    return `<article class="ap-activity-card ap-status-${escapeHtml(status.toLowerCase())}" data-task-id="${escapeHtml(event.task_id)}"><div class="ap-activity-person"><span class="ap-activity-avatar">${svg('bot')}</span><div><strong>${escapeHtml(role)}</strong><span class="ap-team">${escapeHtml(event.event_type || 'task_event')}</span></div><time>${escapeHtml(created)}</time></div><div class="ap-activity-title">${escapeHtml(event.title || 'Sự kiện tác vụ')}</div><p>${escapeHtml(event.description || `Task ${event.task_id} · trạng thái từ event store.`)}</p>${progress}<div class="ap-activity-footer"><span class="ap-status-label">${escapeHtml(label)}</span><span class="ap-activity-duration">${event.duration_ms == null ? '' : `${formatNumber(event.duration_ms)} ms`}</span><button type="button" class="ap-detail" data-ap-action="detail" data-event-id="${escapeHtml(event.event_id)}">Chi tiết ${svg('arrow')}</button></div></article>`;
  }

  function renderActivity() {
    const list = document.getElementById('apActivityList');
    const filter = document.getElementById('apActivityFilter')?.value || 'all';
    const agentFilter = document.getElementById('apAgentFilter')?.value || 'all';
    if (!list) return;
    const agents = [...new Set(feedEvents.map(event => event.agent_id).filter(Boolean))].sort();
    const agentSelect = document.getElementById('apAgentFilter');
    if (agentSelect) {
      const selected = agents.includes(agentFilter) ? agentFilter : 'all';
      agentSelect.innerHTML = `<option value="all">Tất cả agent</option>${agents.map(agent => `<option value="${escapeHtml(agent)}">${escapeHtml(agent)}</option>`).join('')}`;
      agentSelect.value = selected;
    }
    const filtered = feedEvents.filter(event => (filter === 'all' || String(event.status).toUpperCase() === filter) && (agentFilter === 'all' || String(event.agent_id) === agentFilter));
    const badge = document.getElementById('apFeedBadge');
    const badgeText = badge?.querySelector('span');
    if (badge) badge.dataset.state = feedState;
    if (badgeText) badgeText.textContent = feedState === 'live' ? 'Đã nhận event trong phiên' : feedState === 'connected' ? 'Đã kết nối · chờ event' : feedState === 'no_source' ? 'Nguồn chưa kết nối' : feedState === 'owner_auth_required' ? 'Cần xác thực chủ sở hữu' : feedState === 'error' ? 'Mất kết nối' : 'Đang kết nối';
    const streamLabel = document.getElementById('apStreamState');
    if (streamLabel) streamLabel.textContent = feedState === 'live' ? 'SSE · đã nhận event' : feedState === 'connected' ? 'SSE · đang chờ event' : feedState === 'no_source' ? 'Event store · chưa kết nối' : feedState === 'owner_auth_required' ? 'SSE · cần xác thực' : feedState === 'error' ? 'SSE · mất kết nối' : 'SSE · đang kết nối';
    const count = document.getElementById('apActivityCount');
    if (count) count.textContent = filtered.length ? `${filtered.length} sự kiện` : 'Chưa có sự kiện';
    if (!filtered.length) {
      const noRecords = feedEvents.length === 0;
      list.innerHTML = `<div class="ap-empty-state"><span>${svg('activity')}</span><strong>${feedState === 'no_source' ? 'Nguồn task/event chưa kết nối' : feedState === 'owner_auth_required' ? 'Nhật ký cần xác thực chủ sở hữu' : noRecords ? 'Chưa có hoạt động được ghi nhận' : 'Không có sự kiện phù hợp'}</strong><p>${feedState === 'owner_auth_required' ? 'Nhập khóa quản trị trong Trung tâm vận hành; khóa chỉ được gửi qua HTTPS.' : feedState === 'error' ? 'Không kết nối được event stream; thử tải lại lịch sử.' : feedState === 'no_source' ? 'Feed sẽ hiện dữ liệu sau khi runtime task kết nối event store.' : noRecords ? 'Nhật ký chỉ xuất hiện khi backend ghi một sự kiện task thực tế.' : 'Đổi bộ lọc để xem các sự kiện khác.'}</p></div>`;
    } else {
      list.innerHTML = filtered.map(activityMarkup).join('');
    }
    const more = document.getElementById('apMoreActivity');
    if (more) more.disabled = !activityBeforeId;
  }

  async function loadActivity(beforeId) {
    if (!ownerAdminKey()) {
      feedState = 'owner_auth_required';
      activitySourceStatus = 'owner_auth_required';
      renderActivity();
      return [];
    }
    try {
      const query = new URLSearchParams({ limit: '25' });
      if (beforeId) query.set('before_id', String(beforeId));
      const response = await fetch(`/api/dashboard/activity?${query}`, { headers: ownerHeaders(), cache: 'no-store', credentials: 'same-origin' });
      if (response.status === 401 || response.status === 403) {
        try { sessionStorage.removeItem('autoprofit_owner_admin_key'); } catch (_) {}
        feedState = 'owner_auth_required';
        activitySourceStatus = 'owner_auth_required';
        feedEvents = [];
        renderActivity();
        window.dispatchEvent(new Event('ap-owner-auth-change'));
        return [];
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      activitySourceStatus = result.status || 'unknown';
      const incoming = result.items || [];
      if (beforeId) feedEvents = uniqueTasks([...feedEvents, ...incoming]);
      else feedEvents = uniqueTasks(incoming);
      activityBeforeId = result.next_before_id || null;
      if (activitySourceStatus === 'not_connected') feedState = 'no_source';
      else if (activitySourceStatus === 'error') feedState = 'error';
      else if (feedState === 'no_source') feedState = 'connecting';
      renderActivity();
      return incoming;
    } catch (_) {
      feedState = 'error';
      renderActivity();
      return [];
    }
  }

  function uniqueTasks(items) {
    const byTask = new Map();
    items.forEach(item => {
      const key = String(item.task_id ?? item.event_id);
      const current = byTask.get(key);
      if (!current || Number(item.event_id) > Number(current.event_id)) byTask.set(key, item);
    });
    return [...byTask.values()].sort((a, b) => Number(b.event_id) - Number(a.event_id));
  }

  async function loadOlderActivity() {
    if (activityBeforeId) await loadActivity(activityBeforeId);
  }

  async function connectActivityStream() {
    if (!ownerAdminKey()) {
      feedState = 'owner_auth_required';
      activitySourceStatus = 'owner_auth_required';
      renderActivity();
      return;
    }
    const history = await loadActivity();
    if (!ownerAdminKey()) return;
    const lastId = Math.max(0, ...history.map(item => Number(item.event_id) || 0));
    if (!['observed', 'no_data'].includes(activitySourceStatus)) {
      feedState = activitySourceStatus === 'not_connected' ? 'no_source' : 'error';
      renderActivity();
      return;
    }
    if (!window.fetch || !window.ReadableStream) { feedState = 'error'; renderActivity(); return; }
    activityAbortController?.abort();
    const controller = new AbortController();
    activityAbortController = controller;
    try {
      const response = await fetch(`/api/dashboard/activity/stream?after_id=${lastId}`, {
        headers: { ...ownerHeaders(), Accept: 'text/event-stream' },
        credentials: 'same-origin', cache: 'no-store', signal: controller.signal
      });
      if (response.status === 401 || response.status === 403) {
        try { sessionStorage.removeItem('autoprofit_owner_admin_key'); } catch (_) {}
        activitySourceStatus = 'owner_auth_required';
        feedState = 'owner_auth_required';
        feedEvents = [];
        renderActivity();
        window.dispatchEvent(new Event('ap-owner-auth-change'));
        return;
      }
      if (!response.ok || !response.body) {
        if (response.status === 503) {
          const problem = await response.json().catch(() => ({}));
          activitySourceStatus = problem.status || 'not_connected';
          feedState = 'no_source';
        } else {
          activitySourceStatus = 'error';
          feedState = 'error';
        }
        renderActivity();
        scheduleActivityReconnect();
        return;
      }
      activitySourceStatus = 'connected';
      feedState = 'connected';
      renderActivity();
      refreshSummary(document.getElementById('apChartWindow')?.value || 'today');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (!controller.signal.aborted) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || '';
        blocks.forEach(handleActivitySseBlock);
      }
      if (!controller.signal.aborted) throw new Error('event_stream_closed');
    } catch (error) {
      if (error?.name === 'AbortError') return;
      activitySourceStatus = 'error';
      feedState = 'error';
      renderActivity();
      scheduleActivityReconnect();
    }
  }

  function handleActivitySseBlock(block) {
    let eventName = 'message';
    const dataLines = [];
    block.split(/\r?\n/).forEach(line => {
      if (!line || line.startsWith(':')) return;
      const separator = line.indexOf(':');
      const field = separator < 0 ? line : line.slice(0, separator);
      const value = separator < 0 ? '' : line.slice(separator + 1).replace(/^ /, '');
      if (field === 'event') eventName = value;
      else if (field === 'data') dataLines.push(value);
    });
    if (eventName !== 'activity' || !dataLines.length) return;
    try {
      const item = JSON.parse(dataLines.join('\n'));
      if (feedEvents.some(existing => Number(existing.event_id) === Number(item.event_id))) return;
      activitySourceStatus = 'observed';
      feedState = 'live';
      feedEvents = uniqueTasks([item, ...feedEvents]);
      renderActivity();
      refreshSummary(document.getElementById('apChartWindow')?.value || 'today');
    } catch (_) {}
  }

  function scheduleActivityReconnect() {
    window.clearTimeout(activityReconnectTimer);
    if (!ownerAdminKey()) return;
    activityReconnectTimer = window.setTimeout(() => connectActivityStream(), 15000);
  }

  async function openDetail(eventId) {
    const scrim = document.getElementById('apDetailScrim');
    const body = document.getElementById('apDetailBody');
    const title = document.getElementById('apDetailTitle');
    if (!scrim || !body || !title) return;
    if (!ownerAdminKey()) {
      scrim.hidden = false;
      body.innerHTML = '<p class="ap-detail-error">Nhập khóa quản trị trong Trung tâm vận hành để xem nhật ký.</p>';
      return;
    }
    scrim.hidden = false;
    body.innerHTML = '<p class="ap-detail-loading">Đang tải chi tiết sự kiện…</p>';
    try {
      const response = await fetch(`/api/dashboard/activity/${encodeURIComponent(eventId)}`, { headers: ownerHeaders(), cache: 'no-store', credentials: 'same-origin' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const event = await response.json();
      title.textContent = event.title || `Task ${event.task_id}`;
      const steps = (event.steps || []).map(step => `<li><time>${escapeHtml(formatDate(step.timestamp))}</time><strong>${escapeHtml(step.event_type)}</strong><span>${escapeHtml(step.status)}</span></li>`).join('');
      const sensitive = event.sensitive_details === 'restricted'
        ? '<p class="ap-restricted-note">Kết quả thô, log lỗi và artifact cần quyền quản trị; dashboard công khai chỉ hiển thị metadata sự kiện.</p>'
        : `<section><h3>Kết quả đã ghi nhận</h3><pre>${escapeHtml(event.result || 'Không có nội dung kết quả được lưu.')}</pre>${event.error_details ? `<h3>Chi tiết lỗi</h3><pre>${escapeHtml(event.error_details)}</pre>` : ''}<p>Artifact: ${escapeHtml((event.artifact_refs || []).join(', ') || 'Không có')}</p></section>`;
      body.innerHTML = `<dl><div><dt>Event ID</dt><dd>${escapeHtml(event.event_id)}</dd></div><div><dt>Task ID</dt><dd>${escapeHtml(event.task_id)}</dd></div><div><dt>Agent / role</dt><dd>${escapeHtml(event.agent_id || 'Chưa gán')}</dd></div><div><dt>Run ID</dt><dd>${escapeHtml(event.run_id || 'Chưa có')}</dd></div><div><dt>Trạng thái</dt><dd>${escapeHtml(event.status)}</dd></div><div><dt>Thời điểm</dt><dd>${escapeHtml(formatDate(event.timestamp))}</dd></div><div><dt>Bắt đầu</dt><dd>${escapeHtml(formatDate(event.started_at))}</dd></div><div><dt>Kết thúc</dt><dd>${escapeHtml(formatDate(event.finished_at))}</dd></div><div><dt>Tiến độ</dt><dd>${event.progress_pct == null ? 'Chưa ghi nhận' : `${Math.max(0, Math.min(100, Number(event.progress_pct)))}%`}</dd></div><div><dt>Thời lượng</dt><dd>${event.duration_ms == null ? 'Chưa ghi nhận' : `${formatNumber(event.duration_ms)} ms`}</dd></div></dl><h3>Timeline backend</h3><ol class="ap-detail-steps">${steps || '<li>Chưa có bước nào được ghi lại.</li>'}</ol>${sensitive}`;
      document.querySelector('.ap-detail-close')?.focus();
    } catch (_) {
      body.innerHTML = '<p class="ap-detail-error">Không tải được chi tiết từ backend.</p>';
    }
  }

  function closeDetail() {
    const scrim = document.getElementById('apDetailScrim');
    if (scrim && !scrim.hidden) scrim.hidden = true;
  }

  let selectedZone = 'command';
  let zoneUpdateSequence = 0;
  const zoneLabels = {
    command: ['Central AI Command', 'Điều phối trung tâm · trạng thái dịch vụ lấy từ backend'],
    agents: ['AI Agents Zone', 'Chỉ role có task RUNNING mới được đánh dấu đang thực thi.'],
    ads: ['Ad Network Zone', 'Chưa kết nối API campaign hoặc doanh thu quảng cáo.'],
    products: ['Web Apps Zone', 'Danh mục lấy từ /api/products.'],
    live: ['Data Hub', 'Traffic chart dùng pageview first-party đã ghi nhận.'],
    revenue: ['Revenue Zone', 'Doanh thu chỉ lấy từ giao dịch có trạng thái xác nhận.'],
    global: ['Global Traffic', 'Dữ liệu quốc gia chưa được kết nối.']
  };

  function selectZone(zone, objectInfo) {
    selectedZone = zoneLabels[zone] ? zone : 'command';
    selectedObjectInfo = objectInfo || { objectId: `zone:${selectedZone}`, objectType: 'zone', zone: selectedZone, name: zoneLabels[selectedZone][0] };
    zonePanelOpen = true;
    updateZonePanel();
  }

  async function updateZonePanel() {
    const sequence = ++zoneUpdateSequence;
    const currentZone = selectedZone;
    const currentObject = selectedObjectInfo;
    const panel = document.getElementById('apZonePanel');
    const title = document.getElementById('apZoneTitle');
    const description = document.getElementById('apZoneDescription');
    const data = document.getElementById('apZoneDataState');
    if (!panel || !title || !description || !data) return;
    if (!zonePanelOpen) return;
    panel.classList.add('is-visible');
    const zoneCopy = zoneLabels[currentZone] || zoneLabels.command;
    title.textContent = currentObject?.objectType === 'workstation' || currentObject?.objectType === 'landmark' ? currentObject.name : zoneCopy[0];
    description.textContent = `${zoneCopy[1]} · Object ID: ${currentObject?.objectId || `zone:${currentZone}`}`;
    const metrics = summary?.metrics || {};
    if (currentObject?.objectType === 'workstation') {
      if (!ownerAdminKey()) {
        data.innerHTML = '<strong>Chưa xác minh phân công</strong><small>Nhập khóa quản trị qua HTTPS trong Trung tâm vận hành để đọc assignment và task.</small>';
        return;
      }
      data.textContent = 'Đang kiểm tra workstation assignment với backend…';
      try {
        const response = await fetch('/api/employees', { headers: ownerHeaders(), cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        if (sequence !== zoneUpdateSequence || !zonePanelOpen) return;
        const items = Array.isArray(result.items) ? result.items : [];
        const assigned = items.find(agent => {
          const task = agent.latest_task || {};
          return [agent.workstation_id, agent.workstationId, agent.assignment?.workstation_id, task.workstation_id, task.metadata?.workstation_id].includes(currentObject.objectId);
        });
        if (!assigned) {
          data.innerHTML = `<strong>Chưa gán agent</strong><small>${result.status === 'observed' ? 'Backend chưa ghi nhận agent được gán cho workstation này.' : 'Backend runtime task chưa kết nối; chưa có agent được xác minh.'}</small>`;
          return;
        }
        const task = assigned.latest_task;
        const status = assigned.status === 'RUNNING' ? 'Đang chạy' : assigned.status === 'STALE' ? 'Trạng thái cũ' : escapeHtml(assigned.status || 'Chưa có trạng thái');
        data.innerHTML = `<strong>${escapeHtml(assigned.name || assigned.id || 'Agent')} · ${status}</strong><small>${task?.title ? escapeHtml(task.title) : 'Agent chưa có task hoạt động.'}</small>`;
      } catch (_) {
        if (sequence !== zoneUpdateSequence || !zonePanelOpen) return;
        data.innerHTML = '<strong>Chưa gán agent</strong><small>Không tải được assignment từ backend.</small>';
      }
      return;
    }
    if (currentZone === 'agents') {
      if (!ownerAdminKey()) {
        data.textContent = 'Trạng thái agent cần xác thực chủ sở hữu qua HTTPS.';
        return;
      }
      try {
        const response = await fetch('/api/employees', { headers: ownerHeaders(), cache: 'no-store' });
        if (!response.ok) throw new Error();
        const result = await response.json();
        if (sequence !== zoneUpdateSequence || !zonePanelOpen) return;
        if (result.status !== 'observed') { data.textContent = 'Trạng thái agent chưa kết nối với runtime task.'; return; }
        const working = (result.items || []).filter(agent => ['RUNNING', 'STALE'].includes(agent.status) && agent.latest_task);
        data.innerHTML = `<strong>${result.active_count == null ? 'Chưa có dữ liệu' : `${formatNumber(result.active_count)} agent đang chạy`}</strong>${working.length ? `<ul class="ap-zone-agents">${working.slice(0, 5).map(agent => `<li><span>${escapeHtml(agent.name)} · ${escapeHtml(agent.status === 'RUNNING' ? 'Đang chạy' : 'Trạng thái cũ')}</span>${agent.latest_task.latest_event_id ? `<button type="button" data-ap-action="detail" data-event-id="${escapeHtml(agent.latest_task.latest_event_id)}">${escapeHtml(agent.latest_task.title)}</button>` : `<small>${escapeHtml(agent.latest_task.title)}</small>`}</li>`).join('')}</ul>` : '<small>Không có task đang hoặc vừa chạy.</small>'}`;
      } catch (_) { if (sequence === zoneUpdateSequence && zonePanelOpen) data.textContent = 'Không tải được trạng thái agent từ backend.'; }
    } else if (currentZone === 'products') {
      try {
        const response = await fetch('/api/products', { cache: 'no-store' });
        if (!response.ok) throw new Error();
        const result = await response.json();
        if (sequence !== zoneUpdateSequence || !zonePanelOpen) return;
        data.textContent = `${formatNumber((result.items || []).length)} web app trong catalog cấu hình.`;
      } catch (_) { if (sequence === zoneUpdateSequence && zonePanelOpen) data.textContent = 'Không tải được catalog sản phẩm.'; }
    } else if (currentZone === 'revenue') {
      const revenue = metrics.revenue_usd;
      data.textContent = revenue?.value_usd == null ? 'Chưa có giao dịch xác thực.' : `${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(revenue.value_usd)} đã xác nhận.`;
    } else if (currentZone === 'live') {
      data.textContent = `${formatNumber(chartPoints.filter(point => point.value != null).length)} bucket có dữ liệu telemetry.`;
    } else if (currentZone === 'global' || currentZone === 'ads') {
      data.textContent = 'Chưa kết nối nguồn dữ liệu.';
    } else {
      data.textContent = summary?.status === 'ok' ? `Backend cập nhật ${formatDate(summary.updated_at)}.` : 'Đang chờ dữ liệu backend.';
    }
  }

  function selectScene(tab) {
    document.querySelectorAll('[data-ap-tab]').forEach(button => {
      const active = button.dataset.apTab === tab;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
    });
    const stage = document.getElementById('apCommandCenter');
    if (stage) stage.dataset.view = tab;
    const zone = tab === 'panorama' || tab === '3d' ? 'command' : tab;
    if (commandCenter) commandCenter.focus(tab);
    else selectZone(zone);
  }

  function navigateView(view) {
    if (!Object.prototype.hasOwnProperty.call(viewCopy, view)) return false;
    const section = document.getElementById(`view-${view}`);
    if (!section) return false;

    // The legacy dashboard's switchView is not consistently exposed on window.
    // Keep navigation functional even when that older bundle is unavailable.
    if (typeof window.switchView === 'function') {
      window.switchView(view);
    } else {
      document.querySelectorAll('.view-section').forEach(item => item.classList.toggle('active', item === section));
      document.querySelectorAll('.nav-item[data-view]').forEach(item => item.classList.toggle('active', item.dataset.view === view));
      const title = document.getElementById('currentViewTitle');
      if (title) title.textContent = viewCopy[view][0];
      document.getElementById('sidebar')?.classList.remove('open');
    }

    syncShellState();
    if (view !== 'overview') window.refreshAllData?.(false);
    const scrollTarget = view === 'overview' ? document.getElementById('apReferenceDashboard') || section : section;
    const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
    window.requestAnimationFrame(() => scrollTarget.scrollIntoView?.({ behavior, block: 'start' }));
    return true;
  }

  function toggleLanguage() {
    const next = localStorage.getItem('autoprofit_lang') === 'en' ? 'vi' : 'en';
    if (typeof window.setAppLanguage === 'function') {
      window.setAppLanguage(next);
    } else {
      localStorage.setItem('autoprofit_lang', next);
      document.documentElement.lang = next;
    }
    syncShellState();
  }

  function handleClick(event) {
    const button = event.target.closest('[data-ap-view], [data-ap-tab], [data-ap-action], .ap-brand-mark');
    if (!button || button.disabled) return;
    if (button.classList.contains('ap-brand-mark')) { navigateView('overview'); return; }
    if (button.dataset.apView) { navigateView(button.dataset.apView); return; }
    if (button.dataset.apTab) { selectScene(button.dataset.apTab); return; }
    const action = button.dataset.apAction;
    if (action === 'detail') openDetail(button.dataset.eventId);
    else if (action === 'close-detail') closeDetail();
    else if (action === 'close-zone') { zonePanelOpen = false; zoneUpdateSequence += 1; document.getElementById('apZonePanel')?.classList.remove('is-visible'); }
    else if (action === 'refresh') { refreshSummary(document.getElementById('apChartWindow')?.value || 'today'); loadActivity(); window.refreshAllData?.(true); }
    else if (action === 'mobile') {
      const active = document.body.classList.toggle('ap-mobile-preview');
      button.setAttribute('aria-pressed', String(active));
      button.title = active ? 'Tắt xem trước giao diện mobile' : 'Xem trước giao diện mobile';
    }
    else if (action === 'expand') toggleSceneFullscreen(button);
    else if (action === 'reset-scene') selectScene('panorama');
    else if (action === 'language') toggleLanguage();
    else if (action === 'export-report') exportDashboardReport();
  }

  function toggleSceneFullscreen(button) {
    const scene = document.getElementById('apCommandCenter');
    if (!scene) return;
    if (document.fullscreenElement === scene) {
      document.exitFullscreen?.().catch?.(() => {});
      return;
    }
    if (scene.classList.contains('ap-scene-expanded')) {
      scene.classList.remove('ap-scene-expanded');
      button?.setAttribute('aria-pressed', 'false');
      return;
    }
    if (typeof scene.requestFullscreen === 'function') {
      scene.requestFullscreen().then(() => button?.setAttribute('aria-pressed', 'true')).catch(() => {
        scene.classList.add('ap-scene-expanded');
        button?.setAttribute('aria-pressed', 'true');
      });
    } else {
      scene.classList.add('ap-scene-expanded');
      button?.setAttribute('aria-pressed', 'true');
    }
  }

  function exportDashboardReport() {
    const report = {
      exported_at: new Date().toISOString(),
      status: summary?.status || 'unavailable',
      updated_at: summary?.updated_at || null,
      metrics: summary?.metrics || {},
      traffic_series: summary?.series?.points || []
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `autoprofit-report-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  document.addEventListener('pointermove', event => {
    const svgRoot = document.getElementById('apTrafficChart');
    if (!svgRoot || event.target.closest('#apTrafficChart') !== svgRoot || !chartPoints.length) return;
    const rect = svgRoot.getBoundingClientRect();
    const index = Math.round((event.clientX - rect.left) / rect.width * (chartPoints.length - 1));
    showChartPoint(index);
  });
  function handleChartKeydown(event) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const index = event.key === 'Home' ? 0 : event.key === 'End' ? chartPoints.length - 1 : chartIndex < 0 ? 0 : chartIndex + (event.key === 'ArrowRight' ? 1 : -1);
    showChartPoint(index);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
