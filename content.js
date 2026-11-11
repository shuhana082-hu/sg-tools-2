(function () {
  if (window.__siteCaptureInjected) return;
  window.__siteCaptureInjected = true;

  const seen = new Set();
  const mainHost = location.host;
  let active = false;
  let poller = null;

  function hostOf(u) {
    try { return new URL(u).host; } catch (e) { return ""; }
  }

  function classify(initiatorType) {
    return (initiatorType === "fetch" || initiatorType === "xmlhttprequest") ? "api" : "asset";
  }

  async function capture(url, kind) {
    if (!url || seen.has(url) || !/^https?:/i.test(url)) return;
    seen.add(url);
    let opts;
    try {
      opts = await chrome.storage.local.get(["includeOtherHosts", "saveApi"]);
    } catch (e) {
      return; // extension context gone
    }
    const h = hostOf(url);
    const cross = h && h !== mainHost;
    if (cross && !opts.includeOtherHosts) return;
    const bucket = kind === "api" && opts.saveApi !== false ? "api" : (kind === "api" ? "asset" : kind);
    try {
      const r = await fetch(url, { credentials: "same-origin", cache: "force-cache" });
      if (!r.ok) return;
      const buf = await r.arrayBuffer();
      if (!buf.byteLength) return;
      let p;
      try { p = new URL(url).pathname; } catch (e) { p = "/" + url; }
      if (!p || p === "/") p = "/index";
      if (p.endsWith("/")) p += "index";
      p = p.replace(/^\/+/, "");
      let path = bucket === "api" ? "_api/" + h + "/" + p : cross ? "_ext/" + h + "/" + p : p;
      path = path.replace(/[^\w.\-/]/g, "_").slice(0, 220);
      const mime = r.headers.get("content-type") || "";
      chrome.runtime.sendMessage({ type: "sc_file", path, mime, buf }, () => { void chrome.runtime.lastError; });
    } catch (e) { /* cross-origin without CORS, or network error: skip */ }
  }

  function scan() {
    if (!active) return;
    try {
      performance.getEntriesByType("resource").forEach((e) => capture(e.name, classify(e.initiatorType)));
    } catch (e) {}
    document.querySelectorAll("link[href],script[src],img[src],source[src],video[src],audio[src]").forEach((el) => {
      const v = el.href || el.src;
      if (v) capture(v, "asset");
    });
  }

  function start() {
    active = true;
    capture(location.href, "asset");
    scan();
    try {
      new PerformanceObserver((list) => {
        if (active) list.getEntries().forEach((e) => capture(e.name, classify(e.initiatorType)));
      }).observe({ type: "resource", buffered: true });
    } catch (e) {}
    poller = setInterval(scan, 2000);
  }

  chrome.storage.local.get(["capturing"], (r) => {
    if (r.capturing) start();
  });

  try {
    chrome.storage.onChanged.addListener((changes) => {
      if (!changes.capturing) return;
      if (changes.capturing.newValue) {
        if (!active) start();
      } else {
        active = false;
        if (poller) clearInterval(poller);
      }
    });
  } catch (e) {}
})();
