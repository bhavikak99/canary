// The test page: runs one live test (or replays a saved one) and shows the full results.
let CONFIG = {ai_available:false, policies:{}};

function syncPolicy(){
  const on = $("#aiToggle").checked;
  $("#policyRow").style.display = on ? "flex" : "none";
  const known = CONFIG.policies[siteOf($("#url").value)];
  if (!$("#policyUrl").dataset.typed) $("#policyUrl").value = (on && known) ? known : "";
}

function setHeader(url, kicker){
  const site = siteOf(url);
  $("#tpKicker").textContent = kicker;
  $("#tpSite").textContent = site ? site.replace(/^www\./, "") : "Testing a page";
  $("#tpUrl").textContent = url || "";
  document.title = "Canary · " + (site || "Test");
}

async function startTest(url){
  setHeader(url, "Live test");
  const btn = $("#goBtn"); btn.disabled = true; btn.textContent = "Testing...";
  $("#results").style.display = "none"; $("#live").style.display = "block"; $("#feed").innerHTML = "";
  $("#spin").style.display = ""; $("#liveTitle").textContent = "Opening the page";
  const t0 = performance.now();
  const timer = setInterval(() => $("#liveTimer").textContent = ((performance.now()-t0)/1000).toFixed(1)+"s", 100);
  let r = await runScan(url, msg => {
    const [kind, text] = split(msg);
    $("#liveTitle").textContent = kind === "leak" ? "Leak caught" : "Testing " + siteOf(url);
    const li = document.createElement("li"); if (kind === "leak") li.className = "leak";
    li.innerHTML = `<span class="ts">${((performance.now()-t0)/1000).toFixed(1)}s</span>${ic(kind)}<span>${esc(text)}</span>`;
    $("#feed").appendChild(li);
  });
  clearInterval(timer); $("#spin").style.display = "none";
  const leaked = (r.leaks||[]).some(l => l.third_party);
  $("#liveTitle").textContent = r.error ? "Something went wrong" : leaked ? "Leak caught" : (r.found_email_box ? "Done. No leak seen" : "Done");
  setHeader(url, leaked ? "Test finished: leak found" : "Test finished");
  const wantAI = $("#aiToggle").checked && ($("#policyUrl").value.trim() || r.policy_url_found);
  if (!r.error && r.found_email_box && wantAI) {
    showResult(r, {aiLoading:true});
    try {
      const res = await fetch("/api/policy", {method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({id: r.id, policy_url: $("#policyUrl").value.trim()})});
      if (res.ok) r = await res.json(); else r.policy_error = (await res.json()).detail || "AI check failed";
    } catch { r.policy_error = "AI check failed"; }
    showResult(r, {quiet:true});
  } else showResult(r);
  btn.disabled = false; btn.textContent = "Run test";
}

(async () => {
  CONFIG = await loadConfig();
  const q = new URLSearchParams(location.search);
  if (CONFIG.ai_available) $("#aiToggle").checked = q.get("ai") !== "0";
  else { $("#aiSwitch").classList.add("off"); $("#aiToggle").disabled = true; $("#aiLabel").textContent = "Privacy policy check (needs an API key)"; }
  if (q.get("policy")) { $("#policyUrl").value = q.get("policy"); $("#policyUrl").dataset.typed = "1"; }
  $("#aiToggle").addEventListener("change", syncPolicy);
  $("#url").addEventListener("input", syncPolicy);
  $("#policyUrl").addEventListener("input", e => e.target.dataset.typed = e.target.value ? "1" : "");

  $("#tpForm").onsubmit = e => {
    e.preventDefault();
    const url = $("#url").value.trim(); if (!url) return;
    history.replaceState(null, "", "/test?url=" + encodeURIComponent(url));
    startTest(url);
  };

  if (q.get("id")) {
    const res = await fetch("/api/scans/" + encodeURIComponent(q.get("id")));
    if (!res.ok) { setHeader("", "Saved test"); $("#tpSite").textContent = "Saved test not found"; return; }
    const r = await res.json();
    setHeader(r.url, "Saved test · " + (r.time || ""));
    $("#url").value = r.url; syncPolicy();
    $("#live").style.display = "none";
    showResult(r, {replay:true, quiet:true});
  } else if (q.get("url")) {
    $("#url").value = q.get("url"); syncPolicy();
    startTest(q.get("url"));
  } else {
    $("#url").value = "https://www.eventbrite.com/signin/"; syncPolicy();
    setHeader("", "New test"); $("#tpSite").textContent = "Test a page";
  }
})();
