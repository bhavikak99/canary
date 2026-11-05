const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const P = {
  open:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
  cookie:'<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/>',
  click:'<path d="M5 3l13 7-5.5 1.8L10.7 17z"/><path d="M13 13l5 5"/>',
  type:'<rect x="2.5" y="6" width="19" height="12" rx="2"/><path d="M6.5 10h.01M10 10h.01M14 10h.01M17.5 10h.01M7 14h10"/>',
  watch:'<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  leak:'<path d="M12 3.5l9.5 16.5h-19z"/><path d="M12 10v4M12 17h.01"/>',
  none:'<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>',
  at:'<circle cx="12" cy="12" r="4"/><path d="M16 12v1.5a2.5 2.5 0 0 0 5 0V12a9 9 0 1 0-3.5 7.1"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  proof:'<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  doc:'<path d="M14 3H6.5A1.5 1.5 0 0 0 5 4.5v15A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3v5h5M8.5 13h7M8.5 17h5"/>',
  download:'<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
  mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
  copy:'<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  check:'<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  x:'<path d="M6 6l12 12M18 6L6 18"/>',
  arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
  back:'<path d="M19 12H5M11 6l-6 6 6 6"/>',
  flip:'<path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 21v-5h5"/>',
};
const ic = k => `<svg class="ico" viewBox="0 0 24 24">${P[k]||P.open}</svg>`;
document.querySelectorAll("[data-i]").forEach(el => el.innerHTML = ic(el.dataset.i));

// ---------- reveal on scroll ----------
const ro = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); ro.unobserve(e.target); } }), {threshold:.12});
document.querySelectorAll(".rv").forEach(el => ro.observe(el));

// ---------- live scan ----------
function runScan(url, onProgress){
  return new Promise(resolve => {
    const es = new EventSource("/api/scan?url=" + encodeURIComponent(url));
    es.addEventListener("progress", e => onProgress(JSON.parse(e.data)));
    es.addEventListener("result", e => { es.close(); resolve(JSON.parse(e.data)); });
    es.addEventListener("failed", e => { es.close(); resolve({error: JSON.parse(e.data) || "scan crashed", url, leaks:[], third_parties:{}}); });
    es.onerror = () => { es.close(); resolve({error:"Lost connection to the Canary server", url, leaks:[], third_parties:{}}); };
  });
}
const split = m => { const i = m.indexOf("|"); return i > 0 ? [m.slice(0,i), m.slice(i+1)] : ["open", m]; };
const siteOf = u => { try { return new URL(u).hostname } catch { return "" } };
const loadConfig = () => fetch("/api/config").then(r => r.json()).catch(() => ({ai_available:false, policies:{}}));
