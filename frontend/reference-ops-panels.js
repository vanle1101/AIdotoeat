/* Aggregate operations panels for the existing reference dashboard. */
(function () {
  'use strict';

  const rootId = 'apOperationsWorkspace';
  const money = value => value == null || value === '' || !Number.isFinite(Number(value))
    ? '—'
    : new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(Number(value));
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  const dateText = value => {
    if (!value) return '—';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? '—' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(parsed);
  };
  const statusText = status => ({
    observed: 'Đã ghi nhận', no_data: 'Chưa có dữ liệu', no_verified_data: 'No verified data',
    not_connected: 'Not connected', not_instrumented: 'Chưa được đo', owner_auth_required: 'Cần xác thực chủ sở hữu',
    pending_review: 'Pending review', partial_instrumentation: 'Đo lường một phần', degraded_demo: 'Demo · degraded mode',
    insufficient_coverage: 'Chưa đủ dữ liệu', error: 'Nguồn dữ liệu lỗi'
  }[status] || status || 'Chưa rõ trạng thái');
  const badge = (status, label) => `<span class="ap-ops-badge" data-state="${escapeHtml(status || 'unknown')}">${escapeHtml(label || statusText(status))}</span>`;
  const countValue = (value, status) => {
    if (value != null) return money(value);
    if (['not_connected', 'not_instrumented', 'owner_auth_required', 'pending_review', 'degraded_demo', 'error', 'no_data', 'no_verified_data', 'insufficient_coverage', 'partial_instrumentation'].includes(status)) return statusText(status);
    return 'No verified data';
  };
  const currencyText = row => {
    const currency = String(row.currency || 'VND').toUpperCase();
    if (row.amount_minor == null || row.amount_minor === '') return 'No verified data';
    const amount = Number(row.amount_minor);
    if (!Number.isFinite(amount)) return 'No verified data';
    const divisor = currency === 'VND' || currency === 'JPY' || currency === 'KRW' ? 1 : 100;
    return `${new Intl.NumberFormat('vi-VN', { maximumFractionDigits: divisor === 1 ? 0 : 2 }).format(amount / divisor)} ${currency}`;
  };
  const sourceLink = value => {
    try {
      const url = new URL(value);
      if (url.protocol !== 'https:') return '';
      return `<a href="${escapeHtml(url.href)}" target="_blank" rel="noopener noreferrer">Mở nguồn ↗</a>`;
    } catch (_) { return ''; }
  };
  const adminKey = () => {
    if (window.location.protocol !== 'https:') return '';
    try { return sessionStorage.getItem('autoprofit_owner_admin_key') || ''; } catch (_) { return ''; }
  };
  const requestHeaders = (json = false) => {
    const headers = {};
    const key = adminKey();
    if (key) headers['X-Admin-Key'] = key;
    if (json) headers['Content-Type'] = 'application/json';
    return headers;
  };

  function shellMarkup() {
    return `<section class="ap-ops-workspace" id="${rootId}" aria-labelledby="apOpsTitle">
      <header class="ap-ops-header"><div><span class="ap-ops-eyebrow">OWNER OPERATIONS · AGGREGATES ONLY</span><h2 id="apOpsTitle">Trung tâm vận hành</h2><p>Chỉ số lấy từ ledger và event đã lưu. Chưa nối nguồn hoặc chưa có bản ghi sẽ được ghi rõ.</p></div><div class="ap-ops-header-actions"><span id="apOpsStatus" role="status" aria-live="polite">Đang kiểm tra quyền truy cập…</span><form id="apOpsAuthForm" class="ap-ops-auth-form" autocomplete="off"><label class="ap-ops-visually-hidden" for="apOpsAdminKey">Khóa quản trị</label><input id="apOpsAdminKey" type="password" name="admin-key" placeholder="Khóa quản trị · chỉ lưu trong tab" autocomplete="off" spellcheck="false" required><button type="submit" class="ap-ops-button" id="apOpsAuthSubmit">Xác thực</button></form><button type="button" class="ap-ops-button" data-ops-action="refresh">Làm mới</button></div></header>
      <div class="ap-ops-grid">
        <section class="ap-ops-card ap-ops-executive" id="apOpsExecutive" aria-labelledby="apOpsExecutiveTitle"><div class="ap-ops-card-head"><div><span>01 · EXECUTIVE</span><h3 id="apOpsExecutiveTitle">Tiền mặt &amp; pipeline</h3></div><span id="apOpsExecutiveState"></span></div><div id="apOpsExecutiveBody" class="ap-ops-card-body"><p class="ap-ops-empty">Cần xác thực chủ sở hữu để đọc số liệu tổng hợp.</p></div></section>
        <section class="ap-ops-card" id="apOpsOpportunity" aria-labelledby="apOpsOpportunityTitle"><div class="ap-ops-card-head"><div><span>02 · OPPORTUNITY LAB</span><h3 id="apOpsOpportunityTitle">Cơ hội có bằng chứng</h3></div><span id="apOpsOpportunityState"></span></div><div id="apOpsOpportunityBody" class="ap-ops-card-body"><p class="ap-ops-empty">Chỉ hiển thị cơ hội có nguồn xác thực.</p></div></section>
        <section class="ap-ops-card ap-ops-agents" id="apOpsAgents" aria-labelledby="apOpsAgentsTitle"><div class="ap-ops-card-head"><div><span>03 · AGENT WORKBENCH</span><h3 id="apOpsAgentsTitle">50 vai trò logic · không phải 50 model</h3></div><span id="apOpsAgentsState"></span></div><div id="apOpsAgentsBody" class="ap-ops-card-body"><p class="ap-ops-empty">Chờ trạng thái từ runtime task và lease.</p></div></section>
        <section class="ap-ops-card" id="apOpsProduction" aria-labelledby="apOpsProductionTitle"><div class="ap-ops-card-head"><div><span>04 · PRODUCTION</span><h3 id="apOpsProductionTitle">Sản phẩm, QA &amp; artifacts</h3></div><span id="apOpsProductionState"></span></div><div id="apOpsProductionBody" class="ap-ops-card-body"><p class="ap-ops-empty">Chờ catalog sản phẩm.</p></div></section>
        <section class="ap-ops-card" id="apOpsFunnel" aria-labelledby="apOpsFunnelTitle"><div class="ap-ops-card-head"><div><span>05 · SALES FUNNEL</span><h3 id="apOpsFunnelTitle">Từ lượt truy cập đến doanh thu xác thực</h3></div><span id="apOpsFunnelState"></span></div><div id="apOpsFunnelBody" class="ap-ops-card-body"><p class="ap-ops-empty">Đang chờ telemetry, CRM và cash ledger.</p></div></section>
        <section class="ap-ops-card" id="apOpsRisk" aria-labelledby="apOpsRiskTitle"><div class="ap-ops-card-head"><div><span>06 · RISK CONSOLE</span><h3 id="apOpsRiskTitle">Duyệt, đối soát &amp; hạn mức</h3></div><span id="apOpsRiskState"></span></div><div id="apOpsRiskBody" class="ap-ops-card-body"><p class="ap-ops-empty">Chờ dữ liệu approval và policy engine.</p></div></section>
      </div>
      <div id="apOpsTraceDrawer" class="ap-ops-trace" role="status" aria-live="polite" hidden></div>
    </section>`;
  }

  function init() {
    const dashboard = document.getElementById('apReferenceDashboard');
    if (!dashboard || document.getElementById(rootId)) return;
    dashboard.insertAdjacentHTML('afterend', shellMarkup());
    const root = document.getElementById(rootId);
    root.addEventListener('click', onClick);
    const authForm = document.getElementById('apOpsAuthForm');
    const authInput = document.getElementById('apOpsAdminKey');
    const authSubmit = document.getElementById('apOpsAuthSubmit');
    if (window.location.protocol !== 'https:') {
      authInput.disabled = true;
      authSubmit.disabled = true;
      authInput.placeholder = 'Cần HTTPS để gửi khóa';
    }
    window.addEventListener('ap-owner-auth-change', () => {
      if (adminKey()) return;
      if (authForm) authForm.hidden = false;
      renderLocked('owner_auth_required');
      setStatus(window.location.protocol === 'https:'
        ? 'Nhập lại khóa quản trị đã được cấp quyền.'
        : 'Cần HTTPS trước khi nhập khóa quản trị.');
    });
    authForm?.addEventListener('submit', async event => {
      event.preventDefault();
      if (window.location.protocol !== 'https:') {
        setStatus('Khóa quản trị chỉ được gửi qua HTTPS.');
        return;
      }
      const key = authInput?.value.trim();
      if (!key) return;
      try { sessionStorage.setItem('autoprofit_owner_admin_key', key); } catch (_) {}
      if (authInput) authInput.value = '';
      const accepted = await loadOperations();
      if (accepted) authForm.hidden = true;
      if (accepted) window.dispatchEvent(new Event('ap-owner-auth-change'));
      else {
        setStatus('Khóa không hợp lệ hoặc đã bị thu hồi. Kiểm tra lại khóa quản trị.');
        authInput?.focus();
      }
    });
    renderLocked('owner_auth_required');
    if (adminKey()) {
      authForm.hidden = true;
      loadOperations().then(accepted => {
        if (!accepted) authForm.hidden = false;
        window.dispatchEvent(new Event('ap-owner-auth-change'));
      });
    } else if (window.location.protocol === 'https:') {
      setStatus('Nhập khóa quản trị để mở dữ liệu vận hành trong tab này.');
    } else {
      setStatus('Cần HTTPS trước khi nhập khóa quản trị.');
    }
  }

  function setStatus(text) {
    const element = document.getElementById('apOpsStatus');
    if (element) element.textContent = text;
  }

  function renderLocked(status) {
    const message = status === 'owner_auth_required'
      ? 'Dữ liệu vận hành chỉ hiển thị sau khi xác thực chủ sở hữu qua HTTPS.'
      : 'Không kết nối được endpoint tổng hợp. Kiểm tra quyền truy cập và thử lại.';
    ['apOpsExecutiveBody', 'apOpsOpportunityBody', 'apOpsAgentsBody', 'apOpsProductionBody', 'apOpsFunnelBody', 'apOpsRiskBody']
      .forEach(id => { const el = document.getElementById(id); if (el) el.innerHTML = `<p class="ap-ops-empty">${escapeHtml(message)}</p>`; });
    ['apOpsExecutiveState', 'apOpsOpportunityState', 'apOpsAgentsState', 'apOpsProductionState', 'apOpsFunnelState', 'apOpsRiskState']
      .forEach(id => { const el = document.getElementById(id); if (el) el.innerHTML = badge(status); });
    setStatus(statusText(status));
  }

  async function loadOperations() {
    if (!adminKey()) { renderLocked('owner_auth_required'); return false; }
    setStatus('Đang tải số liệu tổng hợp…');
    try {
      const response = await fetch('/api/dashboard/operations', { headers: requestHeaders(), credentials: 'same-origin', cache: 'no-store' });
      if (response.status === 401 || response.status === 403) {
        try { sessionStorage.removeItem('autoprofit_owner_admin_key'); } catch (_) {}
        const authForm = document.getElementById('apOpsAuthForm');
        if (authForm) authForm.hidden = false;
        renderLocked('owner_auth_required');
        setStatus('Khóa không hợp lệ hoặc đã bị thu hồi. Kiểm tra lại khóa quản trị.');
        return false;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      render(data);
      setStatus(`Đã đồng bộ ${dateText(data.updated_at)} · dữ liệu aggregate-only`);
      return true;
    } catch (_) {
      renderLocked('error');
      setStatus('Không tải được dashboard operations.');
      return false;
    }
  }

  function renderExecutive(data) {
    const cash = data.cash || {};
    const balances = cash.settled_balance_by_currency || [];
    const cashMarkup = cash.status === 'observed' && balances.length
      ? balances.map(item => `<li><strong>${escapeHtml(currencyText(item))}</strong><small>Thu đã xác minh · ${escapeHtml(item.assurance_label || 'owner attestation')}</small></li>`).join('')
      : `<li><strong>${escapeHtml(statusText(cash.status || 'no_verified_data'))}</strong><small>Không chuyển đổi FX · không cộng BTC/USDT.</small></li>`;
    const last = cash.last_sale ? `${currencyText(cash.last_sale)} · ${dateText(cash.last_sale.verified_at)}` : statusText(cash.status || 'no_verified_data');
    const orders = data.orders || {};
    const pipeline = data.pipeline || {};
    const exposures = data.cost_exposures || {};
    const exposureText = exposures.status === 'observed'
      ? `${money(exposures.count)} lần phơi nhiễm · ${money(exposures.blocked_count)} bị chặn (ước tính, không phải chi phí đã trả)`
      : statusText(exposures.status);
    const freshness = data.evidence_freshness || {};
    const freshnessText = freshness.latest_captured_at
      ? `${dateText(freshness.latest_captured_at)} · ${freshness.age_days == null ? 'tuổi dữ liệu chưa rõ' : `${money(freshness.age_days)} ngày`}`
      : statusText(freshness.status || 'not_connected');
    const pipelineText = pipeline.lead_count == null
      ? statusText(pipeline.status)
      : `${countValue(pipeline.lead_count, pipeline.status)} leads · ${countValue(pipeline.qualified_count, pipeline.status)} qualified · ${countValue(pipeline.quote_count, pipeline.status)} quotes`;
    return `<div class="ap-ops-kpi-grid">
      <article><span>NET CASH RECEIVED · VND</span><ul class="ap-ops-value-list">${cashMarkup}</ul><small>${escapeHtml(cash.assurance_label === 'OWNER_MANUAL_ATTESTATION' ? 'Xác nhận thủ công của chủ sở hữu' : statusText(cash.status))}</small></article>
      <article><span>OUTSTANDING ORDERS</span><strong>${escapeHtml(countValue(orders.open_count, orders.status))}</strong><small>Đếm đơn đang mở · không chứa PII</small></article>
      <article><span>PIPELINE</span><strong>${escapeHtml(pipelineText)}</strong><small>Gộp theo trạng thái CRM</small></article>
      <article><span>COST EXPOSURES</span><strong>${escapeHtml(exposureText)}</strong><small>Ước tính policy ledger; actual cost chưa được xác minh</small></article>
      <article><span>LAST SUCCESSFUL SALE</span><strong>${escapeHtml(last)}</strong><small>${escapeHtml(cash.last_sale?.assurance_label || 'No verified data')}</small></article>
      <article><span>EVIDENCE FRESHNESS</span><strong>${escapeHtml(freshnessText)}</strong><small>${freshness.verified_evidence_count == null ? 'Nguồn chưa kết nối' : `${money(freshness.verified_evidence_count)} evidence đã xác minh`}</small></article>
    </div>`;
  }

  function renderOpportunities(data) {
    const items = data.items || [];
    if (!items.length) return `<p class="ap-ops-empty">${escapeHtml(statusText(data.status || 'no_data'))} · chưa có cơ hội nào được xác minh từ nguồn.</p>`;
    return `<ol class="ap-ops-opportunity-list">${items.map(item => `<li><article>
      <div class="ap-ops-item-title"><strong>${escapeHtml(item.title)}</strong><span>${item.score == null ? '—' : `${escapeHtml(item.score)} / 100`}</span></div>
      <p>${escapeHtml(item.pain_point || 'Pain point chưa được trích xuất.')}</p>
      <div class="ap-ops-meta"><span>${money(item.evidence_count)} source evidence</span><span>${escapeHtml(item.buyer_persona || 'Buyer persona chưa rõ')}</span><span>${escapeHtml(dateText(item.captured_at))}</span>${sourceLink(item.source_url)}</div>
      <small class="ap-ops-hypothesis">${escapeHtml(item.willingness_to_pay_hypothesis || 'HYPOTHESIS · chưa xác minh willingness to pay')}</small>
      ${item.experiment ? `<div class="ap-ops-experiment"><b>Experiment · ${escapeHtml(item.experiment.status)}</b><p>${escapeHtml(item.experiment.hypothesis || item.experiment.name || 'Chưa ghi giả thuyết.')}</p></div>` : '<div class="ap-ops-experiment">Chưa có experiment được lưu.</div>'}
    </article></li>`).join('')}</ol>`;
  }

  function renderAgents(data) {
    const counts = data.counts || {};
    const items = data.items || [];
    if (!items.length) return `<p class="ap-ops-empty">${escapeHtml(statusText(data.status || 'not_connected'))}</p>`;
    return `<div class="ap-ops-state-counts">${['active', 'idle', 'degraded', 'disabled'].map(key => `<span><b>${money(counts[key])}</b> ${key}</span>`).join('')}</div>
      <p class="ap-ops-note">Trạng thái dựa trên task gần nhất và lease. Cancel / approval được kiểm tra lại bởi backend.</p>
      <details class="ap-ops-details"><summary>Xem toàn bộ ${money(data.logical_roles)} vai trò</summary><ul class="ap-ops-role-list">${items.map(item => {
        const canCancel = item.task_id != null && ['QUEUED', 'RUNNING', 'WAITING_APPROVAL', 'RETRY_PENDING', 'BLOCKED'].includes(item.task_state);
        const canDecide = item.task_id != null && item.task_state === 'WAITING_APPROVAL';
        const job = item.job ? `<span class="ap-ops-role-job">${escapeHtml(item.job)}</span>` : '';
        return `<li data-state="${escapeHtml(item.readiness_state)}"><div class="ap-ops-role-heading"><strong>${escapeHtml(item.name)}</strong><code>${escapeHtml(item.role_id)}</code>${badge(item.readiness_state, item.readiness_state)}</div>
          <div class="ap-ops-role-meta"><span>${escapeHtml(item.department || '—')}</span><span>${escapeHtml(item.task_state)}</span>${item.task_id == null ? '' : `<span>Task #${escapeHtml(item.task_id)}</span>`}${item.trace_id ? `<code>trace ${escapeHtml(item.trace_id)}</code>` : ''}${job}</div>
          <div class="ap-ops-role-actions">${item.task_id == null ? '' : `<button type="button" class="ap-ops-button" data-ops-action="events" data-task-id="${escapeHtml(item.task_id)}">Mở trace</button>`}${canDecide ? `<button type="button" class="ap-ops-button" data-ops-action="task-approve" data-task-id="${escapeHtml(item.task_id)}">Tiếp tục</button><button type="button" class="ap-ops-button ap-ops-danger" data-ops-action="task-reject" data-task-id="${escapeHtml(item.task_id)}">Chặn</button>` : ''}${canCancel ? `<button type="button" class="ap-ops-button ap-ops-danger" data-ops-action="cancel-task" data-task-id="${escapeHtml(item.task_id)}">Hủy task</button>` : ''}</div></li>`;
      }).join('')}</ul></details>`;
  }

  function renderProduction(data) {
    const products = data.products || {};
    const artifactBody = `<div id="apOpsArtifacts" class="ap-ops-artifact-list"><p class="ap-ops-empty">Chưa tải artifact. Mở danh sách theo yêu cầu để giảm tải ban đầu.</p></div><button type="button" class="ap-ops-button" data-ops-action="load-artifacts">Tải builds &amp; artifacts</button>`;
    const assetCounts = products.asset_status_counts ? Object.entries(products.asset_status_counts).map(([state, count]) => `${escapeHtml(state)} ${money(count)}`).join(' · ') || 'No verified data' : 'Not connected';
    return `<div class="ap-ops-product-summary"><article><span>CATALOG</span><strong>${escapeHtml(countValue(products.count, products.status))}</strong><small>${products.active_count == null ? 'Active: —' : `Active: ${money(products.active_count)}`}</small></article><article><span>PRODUCT ASSETS</span><strong>${escapeHtml(countValue(products.asset_count, products.asset_count == null ? 'not_connected' : 'observed'))}</strong><small>${assetCounts}</small></article><article><span>ACTIVE DELIVERIES</span><strong>${escapeHtml(countValue(products.active_delivery_count, products.delivery_source === 'not_connected' ? 'not_connected' : 'no_data'))}</strong><small>Expiring delivery authorizations recorded by cash ledger</small></article></div><p class="ap-ops-note">Artifacts ở staging chỉ là bản QA, chưa đồng nghĩa đã phát hành hoặc giao hàng.</p>${artifactBody}`;
  }

  function renderFunnel(data) {
    const stages = data.stages || {};
    const sources = data.stage_sources || {};
    const revenue = data.revenue || {};
    const definitions = [['visits', 'Visits'], ['opted_in_leads', 'Opted-in leads'], ['qualified_quotes', 'Qualified quotes'], ['paid_orders', 'Paid orders']];
    const items = definitions.map(([key, title]) => `<li><span>${title}</span><strong>${escapeHtml(countValue(stages[key], sources[key]))}</strong><small>${escapeHtml(statusText(sources[key]))}</small></li>`).join('');
    const balances = revenue.settled_balance_by_currency || [];
    const revenueValue = revenue.status === 'observed' && balances.length ? balances.map(currencyText).join(' · ') : statusText(revenue.status || 'no_verified_data');
    return `<ol class="ap-ops-funnel-list">${items}<li><span>Verified revenue</span><strong>${escapeHtml(revenueValue)}</strong><small>${escapeHtml(revenue.assurance_label === 'OWNER_MANUAL_ATTESTATION' ? 'Owner manual attestation · no FX' : statusText(revenue.status))}</small></li></ol><p class="ap-ops-note">Traffic is consent-limited and does not represent unique people. BTC/USDT balances are excluded from earned fiat revenue.</p>`;
  }

  function renderRisk(data) {
    const approval = data.pending_approvals || {};
    const quota = data.provider_quota || {};
    const claims = data.payment_claims_pending || {};
    const blocks = data.known_policy_blocks || {};
    const quotaLabel = quota.status === 'observed'
      ? `${escapeHtml(countValue(quota.requests_today, quota.status))} request(s) recorded today${quota.daily_quota == null ? ' · quota cap unknown' : ` / ${escapeHtml(money(quota.daily_quota))} configured`}`
      : quota.status === 'degraded_demo' ? 'DEMO provider · no real model usage' : statusText(quota.status || 'not_connected');
    const approvals = approval.items || [];
    const approvalsMarkup = approvals.length ? `<ul class="ap-ops-approval-list">${approvals.map(item => `<li><div><strong>${escapeHtml(item.tool_name)}</strong><small>${escapeHtml(item.permission)} · expires ${escapeHtml(dateText(item.expires_at))}</small><code>trace ${escapeHtml(item.trace_id)}</code></div><div><button type="button" class="ap-ops-button" data-ops-action="approval-approve" data-approval-id="${escapeHtml(item.id)}">Duyệt</button><button type="button" class="ap-ops-button ap-ops-danger" data-ops-action="approval-reject" data-approval-id="${escapeHtml(item.id)}">Từ chối</button></div></li>`).join('')}</ul>` : `<p class="ap-ops-empty">${approval.status === 'observed' ? 'Không có approval đang chờ.' : escapeHtml(statusText(approval.status))}</p>`;
    return `<div class="ap-ops-risk-grid"><article><span>PENDING APPROVALS</span><strong>${escapeHtml(countValue(approval.count, approval.status))}</strong></article><article><span>PAYMENT CLAIMS</span><strong>${escapeHtml(countValue(claims.count, claims.status))}</strong><small>${escapeHtml(statusText(claims.status))}</small></article><article><span>DUPLICATE CLAIM ATTEMPTS</span><strong>${escapeHtml(statusText(data.duplicate_claim_attempts?.status || 'not_instrumented'))}</strong></article><article><span>POLICY BLOCKS</span><strong>${escapeHtml(countValue(blocks.count, blocks.status))}</strong><small>Exposure estimates, not actual spend</small></article><article><span>MODEL PROVIDER QUOTA</span><strong>${quotaLabel}</strong><small>${escapeHtml(quota.quota_source || 'No provider usage telemetry')}</small></article><article><span>UNAUTHORIZED ATTEMPTS</span><strong>${escapeHtml(statusText(data.unauthorized_attempts?.status || 'not_instrumented'))}</strong><small>No zero claim: this event is not instrumented.</small></article></div><h4>Yêu cầu cần người duyệt</h4>${approvalsMarkup}`;
  }

  function render(data) {
    const sections = [
      ['apOpsExecutiveState', data.executive?.cash?.status, 'apOpsExecutiveBody', renderExecutive(data.executive || {})],
      ['apOpsOpportunityState', data.opportunity_lab?.status, 'apOpsOpportunityBody', renderOpportunities(data.opportunity_lab || {})],
      ['apOpsAgentsState', data.agents?.status, 'apOpsAgentsBody', renderAgents(data.agents || {})],
      ['apOpsProductionState', data.production?.products?.status, 'apOpsProductionBody', renderProduction(data.production || {})],
      ['apOpsFunnelState', data.sales_funnel?.status, 'apOpsFunnelBody', renderFunnel(data.sales_funnel || {})],
      ['apOpsRiskState', data.risk?.pending_approvals?.status, 'apOpsRiskBody', renderRisk(data.risk || {})],
    ];
    sections.forEach(([stateId, status, bodyId, html]) => {
      const state = document.getElementById(stateId);
      const body = document.getElementById(bodyId);
      if (state) state.innerHTML = badge(status);
      if (body) body.innerHTML = html;
    });
  }

  async function loadArtifacts(button) {
    button.disabled = true;
    button.textContent = 'Đang đọc artifact…';
    const target = document.getElementById('apOpsArtifacts');
    try {
      const response = await fetch('/api/product-studio/artifacts', { headers: requestHeaders(), credentials: 'same-origin', cache: 'no-store' });
      if (response.status === 401 || response.status === 403) throw new Error('owner_auth_required');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      const items = result.items || [];
      target.innerHTML = items.length ? `<ul>${items.map(item => `<li><div><strong>${escapeHtml(item.file_name || item.artifact_id)}</strong><small>${escapeHtml(item.track || 'Track chưa rõ')} · ${escapeHtml(item.status || 'Trạng thái chưa rõ')} · QA ${item.quality_score == null ? '—' : `${escapeHtml(item.quality_score)}%`} · ${money(item.acceptance_test_count)} acceptance checks</small><code>SHA-256 ${escapeHtml(item.sha256 || '—')}</code></div><a href="${escapeHtml(item.download_url)}" rel="noopener">Tải bản staging</a></li>`).join('')}</ul>` : `<p class="ap-ops-empty">No verified staged artifacts.</p>`;
      button.textContent = 'Đã tải danh sách artifacts';
    } catch (error) {
      if (target) target.innerHTML = `<p class="ap-ops-empty">${error.message === 'owner_auth_required' ? 'Cần phiên chủ sở hữu HTTPS để xem artifacts.' : 'Không đọc được danh sách artifacts.'}</p>`;
      button.textContent = 'Thử tải lại';
      button.disabled = false;
    }
  }

  async function postAction(url, body, successText) {
    const response = await fetch(url, { method: 'POST', headers: requestHeaders(true), credentials: 'same-origin', cache: 'no-store', body: body == null ? undefined : JSON.stringify(body) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    setStatus(successText);
    await loadOperations();
  }

  async function showEvents(taskId) {
    const drawer = document.getElementById('apOpsTraceDrawer');
    if (!drawer) return;
    drawer.hidden = false;
    drawer.textContent = `Đang tải event cho task ${taskId}…`;
    try {
      const response = await fetch(`/api/engine/tasks/${encodeURIComponent(taskId)}/events`, { headers: requestHeaders(), credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) throw new Error();
      const result = await response.json();
      const lines = (result.items || []).map(item => `${dateText(item.timestamp)} · ${item.event_type} · ${item.status} · ${item.trace_id || 'trace chưa có'}`);
      drawer.textContent = lines.length ? lines.join('\n') : `Task ${taskId}: chưa có event chi tiết.`;
    } catch (_) { drawer.textContent = `Không tải được event cho task ${taskId}.`; }
  }

  async function onClick(event) {
    const button = event.target.closest('[data-ops-action]');
    if (!button || button.disabled) return;
    const action = button.dataset.opsAction;
    if (action === 'refresh') { await loadOperations(); return; }
    if (action === 'load-artifacts') { await loadArtifacts(button); return; }
    if (action === 'events') { await showEvents(button.dataset.taskId); return; }
    try {
      button.disabled = true;
      if (action === 'cancel-task') await postAction(`/api/engine/tasks/${encodeURIComponent(button.dataset.taskId)}/cancel`, null, 'Task đã được hủy bởi chủ sở hữu.');
      else if (action === 'task-approve') await postAction(`/api/engine/tasks/${encodeURIComponent(button.dataset.taskId)}/decision`, { decision: 'APPROVED' }, 'Task đã được tiếp tục sau quyết định của chủ sở hữu.');
      else if (action === 'task-reject') await postAction(`/api/engine/tasks/${encodeURIComponent(button.dataset.taskId)}/decision`, { decision: 'REJECTED' }, 'Task đã bị chặn theo quyết định của chủ sở hữu.');
      else if (action === 'approval-approve') await postAction(`/api/engine/approvals/${encodeURIComponent(button.dataset.approvalId)}/decision`, { decision: 'APPROVED', reason: 'Owner review from dashboard' }, 'Approval đã được ghi nhận.');
      else if (action === 'approval-reject') await postAction(`/api/engine/approvals/${encodeURIComponent(button.dataset.approvalId)}/decision`, { decision: 'REJECTED', reason: 'Owner review from dashboard' }, 'Approval đã bị từ chối.');
    } catch (_) {
      setStatus('Backend từ chối thao tác hoặc trạng thái task đã đổi. Đang tải lại…');
      await loadOperations();
    } finally {
      button.disabled = false;
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
