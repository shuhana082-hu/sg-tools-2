const DB_NAME = "sitecapture", STORE = "files";

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) req.result.createObjectStore(STORE, { keyPath: "path" });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function saveFile(rec) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(rec);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "sc_file") {
    saveFile({ path: msg.path, mime: msg.mime, buf: msg.buf, size: msg.buf ? msg.buf.byteLength : 0, ts: Date.now() })
      .then(() => sendResponse({ ok: true }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }
});

chrome.runtime.onInstalled.addListener(async () => {
  const cur = await chrome.storage.local.get(["capturing", "includeOtherHosts", "saveApi"]);
  const defaults = {};
  if (cur.capturing === undefined) defaults.capturing = false;
  if (cur.includeOtherHosts === undefined) defaults.includeOtherHosts = false;
  if (cur.saveApi === undefined) defaults.saveApi = true;
  if (Object.keys(defaults).length) await chrome.storage.local.set(defaults);
});
