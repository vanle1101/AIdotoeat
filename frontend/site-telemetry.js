/* First-party pageview and liveness telemetry. Stores no IP or query strings. */
(function () {
  'use strict';

  const storageKey = 'autoprofit.telemetry.session.v1';
  const endpoint = '/api/telemetry/';
  let sessionId = '';

  function newSessionId() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return window.crypto.randomUUID();
    }
    if (!window.crypto || typeof window.crypto.getRandomValues !== 'function') return '';
    const bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }

  function getSessionId() {
    try {
      const saved = sessionStorage.getItem(storageKey) || '';
      if (/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(saved)) return saved;
      const created = newSessionId();
      if (created) sessionStorage.setItem(storageKey, created);
      return created;
    } catch (_) {
      return newSessionId();
    }
  }

  function send(kind, includePath) {
    if (!sessionId || document.visibilityState === 'prerender') return;
    const body = { session_id: sessionId };
    if (includePath) body.path = window.location.pathname.slice(0, 200) || '/';
    fetch(endpoint + kind, {
      method: 'POST',
      credentials: 'same-origin',
      cache: 'no-store',
      keepalive: kind === 'heartbeat',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).catch(() => {});
  }

  function start() {
    if (!/^https?:$/.test(window.location.protocol) || window.location.pathname.startsWith('/api/')) return;
    sessionId = getSessionId();
    if (!sessionId) return;
    send('pageview', true);
    window.setInterval(() => {
      if (document.visibilityState === 'visible') send('heartbeat', false);
    }, 25000);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') send('heartbeat', false);
    });
    window.addEventListener('pagehide', () => send('heartbeat', false), { once: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
