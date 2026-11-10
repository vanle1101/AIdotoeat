/* Phase 00: disable retired traffic/reward flows and unverified ad telemetry. */
(() => {
  const noAdTelemetry = () => null;
  const disabledAction = () => {
    if (typeof window.showToast === 'function') {
      window.showToast('Tính năng này đã tắt; không tạo view, click hoặc doanh thu quảng cáo giả.');
    }
    return null;
  };

  [
    'syncRealAAdsTelemetry',
    'syncLiveAadsAndAdsterraApiFromBackend',
    'applyAAdsTelemetryToUI',
    'applyLiveAdTelemetryPayload',
    'pollLiveBinanceWalletOnChain',
    'syncLiveBinanceExchangePricesAndBalance',
    'syncAllLiveBranchCountersUI',
    'recalculateAndSyncTotalVerifiedRevenueUI',
    'generateNextRealActivityDialogueTurn',
    'buildUniqueRealtimeDiaryEntry',
    'getRotatingYoutubeCampaignByIndex',
    'getRotatingYoutubeCampaignForWebApp',
  ].forEach((name) => { window[name] = noAdTelemetry; });

  window.getRotatingYoutubeCampaignByIndex = () => ({ title: 'Video engagement tools are disabled', bridgeUrl: '#' });
  window.getRotatingYoutubeCampaignForWebApp = () => ({ title: 'Video engagement tools are disabled', bridgeUrl: '#' });

  [
    'startYoutube30sWatchAndEarn',
    'createCustomMonetizedBridgeLink',
    'openAdNetworksApiConfigModal',
  ].forEach((name) => { window[name] = disabledAction; });

  window.renderAdLinkEvenDistributionStats = () => {
    const status = document.getElementById('adLinkEvenDistributionStatus');
    if (status) status.textContent = 'Chưa có dữ liệu xác minh';
    return null;
  };

  window.AADS_LIVE_STATE = { status: 'not_connected', units: {} };
  window.ADSTERRA_LIVE_STATE = { status: 'not_connected' };
  window.MONETAG_LIVE_STATE = { status: 'not_connected' };

  function scrubRetiredControls() {
    const impressionLabel = document.getElementById('aadsImpressionsCounter');
    if (impressionLabel) impressionLabel.textContent = 'Chưa có dữ liệu xác minh';
    const unitLabel = document.getElementById('aadsUnitIdBadge');
    if (unitLabel) unitLabel.textContent = 'Chưa cấu hình';
    const syncBadge = document.getElementById('live10sAdSyncBadge');
    if (syncBadge) syncBadge.textContent = 'Không có telemetry quảng cáo đã xác minh';
    const campaignList = document.getElementById('ytActiveCampaignsListBox');
    if (campaignList) campaignList.replaceChildren();
    const campaignBadge = document.getElementById('tabBadgeYoutubeCampaigns');
    if (campaignBadge) campaignBadge.textContent = '—';
    const appBadge = document.getElementById('tabBadgeWebAppCount');
    if (appBadge) appBadge.textContent = '—';
    const agentBadge = document.getElementById('badge-agents');
    if (agentBadge) agentBadge.textContent = '—';
    const runtimeStatus = document.getElementById('world3DStatusChip');
    if (runtimeStatus) runtimeStatus.textContent = 'AI runtime chưa kết nối';
    const youtubeViews = document.getElementById('ytLiveViewsDeliveredBadge');
    if (youtubeViews) youtubeViews.textContent = 'Tăng lượt xem tự động đã tắt';
    const youtubeLinks = document.getElementById('ytLiveBacklinksCountBadge');
    if (youtubeLinks) youtubeLinks.textContent = 'Chưa có backlink được xác minh';
    const youtubeRotation = document.getElementById('ytRotationCurrentPointerBadge');
    if (youtubeRotation) youtubeRotation.textContent = 'Không có video đang luân phiên';
    document.getElementById('ytWatchTimerChip')?.remove();

    const youtubeFrame = document.getElementById('ytFeaturedEmbedIframe');
    if (youtubeFrame) {
      youtubeFrame.removeAttribute('data-postload-src');
      youtubeFrame.src = 'about:blank';
      youtubeFrame.remove();
    }
    document.querySelectorAll('iframe[data-postload-src]').forEach((frame) => {
      const target = frame.getAttribute('data-postload-src') || '';
      if (/youtube\.com|youtu\.be/i.test(target)) {
        frame.removeAttribute('data-postload-src');
        frame.src = 'about:blank';
        frame.remove();
      }
    });

    document.querySelectorAll('[onclick*="startYoutube30sWatchAndEarn"]').forEach((button) => {
      button.removeAttribute('onclick');
      button.disabled = true;
      button.textContent = 'Tính năng tăng view đã tắt';
    });
    document.querySelectorAll(
      '[onclick*="requestLaunchYoutubeCampaign"], [onclick*="openYoutubePromoCheckoutModal"], ' +
      '[onclick*="generateCustomAdUnlockLinkNow"]'
    ).forEach((button) => {
      button.removeAttribute('onclick');
      button.disabled = true;
      button.textContent = 'Tính năng tăng tương tác video đã tắt';
    });
    document.querySelectorAll('a[href*="youtube-watch"], a[href*="youtube.com"], a[href*="youtu.be"]').forEach((link) => {
      link.removeAttribute('href');
      link.setAttribute('aria-disabled', 'true');
      link.textContent = 'Tính năng tăng lượt xem video đã tắt';
    });
    document.querySelectorAll('iframe[src*="youtube.com"], iframe[src*="youtu.be"]').forEach((frame) => frame.remove());
    document.getElementById('ytDirectChannelSubscribeBtn')?.remove();
    document.getElementById('ytWatchRewardUnlockedBox')?.remove();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scrubRetiredControls, { once: true });
  } else {
    scrubRetiredControls();
  }
})();
