// ---------- sticky phone story ----------
const phone = $("#phone"); const EMAIL = "you@gmail.com"; let typeTimer;
function setStep(s){
  if (phone.dataset.s === String(s)) return;
  phone.dataset.s = s;
  document.querySelectorAll(".dots i").forEach((d,i) => d.classList.toggle("on", i === s-1));
  document.querySelectorAll(".stp").forEach(el => el.classList.toggle("on", el.dataset.step === String(s)));
  clearInterval(typeTimer);
  const t = $("#typed"), ph = $("#ph"), caret = $("#caret");
  if (s === 1) { t.textContent = ""; ph.style.display = ""; caret.style.display = "none"; }
  else if (s === 2) {
    ph.style.display = "none"; caret.style.display = ""; t.textContent = ""; let i = 0;
    typeTimer = setInterval(() => { t.textContent = EMAIL.slice(0, ++i); if (i >= EMAIL.length) clearInterval(typeTimer); }, 90);
  } else { ph.style.display = "none"; caret.style.display = s === 4 ? "none" : ""; t.textContent = EMAIL; }
}
const so = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) setStep(+e.target.dataset.step); }), {rootMargin:"-45% 0px -45% 0px"});
document.querySelectorAll(".stp").forEach(el => so.observe(el));
setStep(1);

// ---------- hero: start a test on its own page ----------
let CONFIG = {ai_available:false, policies:{}};
function syncPolicy(){
  const on = $("#aiToggle").checked;
  $("#policyRow").style.display = on ? "flex" : "none";
  const known = CONFIG.policies[siteOf($("#url").value)];
  if (!$("#policyUrl").dataset.typed) $("#policyUrl").value = (on && known) ? known : "";
}
loadConfig().then(c => {
  CONFIG = c;
  if (c.ai_available) $("#aiToggle").checked = true;
  else { $("#aiSwitch").classList.add("off"); $("#aiToggle").disabled = true; $("#aiLabel").textContent = "Privacy policy check (needs an API key)"; }
  syncPolicy();
});
$("#aiToggle").addEventListener("change", syncPolicy);
$("#url").addEventListener("input", syncPolicy);
$("#policyUrl").addEventListener("input", e => e.target.dataset.typed = e.target.value ? "1" : "");
document.querySelectorAll(".chip[data-url]").forEach(b => b.onclick = e => { e.preventDefault(); $("#url").value = b.dataset.url; syncPolicy(); });
$("#scanForm").onsubmit = e => {
  e.preventDefault();
  const url = $("#url").value.trim(); if (!url) return;
  const q = new URLSearchParams({url, ai: $("#aiToggle").checked ? "1" : "0"});
  if ($("#policyUrl").dataset.typed && $("#policyUrl").value.trim()) q.set("policy", $("#policyUrl").value.trim());
  location.href = "/test?" + q.toString();
};

// ---------- replay: open a saved test on the test page ----------
$("#replayToggle").onclick = async () => {
  const row = $("#replayRow");
  if (row.style.display === "flex") { row.style.display = "none"; return; }
  const scans = await (await fetch("/api/scans")).json();
  $("#replaySelect").innerHTML = scans.length ? scans.map(s =>
    `<option value="${esc(s.id)}">${esc(s.site_name)}, ${esc((s.time||"").slice(0,16))}: ${s.leaks ? "leaked to "+s.leaks : (s.found_email_box ? "clear" : "no form")}${s.has_policy?" (with AI)":""}</option>`).join("")
    : `<option value="">No saved tests yet</option>`;
  row.style.display = "flex";
};
$("#replayGo").onclick = () => { const id = $("#replaySelect").value; if (id) location.href = "/test?id=" + encodeURIComponent(id); };

// ---------- flip cards ----------
document.querySelectorAll(".flip").forEach(card => card.onclick = () => card.classList.toggle("on"));

// ---------- check my event ----------
$("#evGo").onclick = async () => {
  const urls = $("#evPages").value.split("\n").map(s=>s.trim()).filter(Boolean);
  if (!urls.length) return;
  const btn = $("#evGo"); btn.disabled = true;
  $("#evOut").innerHTML = `<div id="evSum"></div><div id="evList"></div>`;
  const results = [];
  for (let i = 0; i < urls.length; i++) {
    btn.textContent = `Checking ${i+1} of ${urls.length}...`;
    const row = document.createElement("div"); row.className = "panel pass wait";
    row.innerHTML = `<span class="st"></span><div class="grow"><div class="u">${esc(urls[i])}</div><div class="d">Starting</div></div><span class="lab">Checking</span>`;
    $("#evList").appendChild(row);
    const r = await runScan(urls[i], msg => { row.querySelector(".d").textContent = split(msg)[1]; });
    results.push(r);
    const outs = (r.leaks||[]).filter(l=>l.third_party);
    const cos = [...new Set(outs.map(l=>l.company))]; const fs = [...new Set(outs.map(l=>l.field||"email"))];
    let cls="good", lab="Clear", d="Nothing left before submit", extra="";
    if (r.error) { cls="meh"; lab="Skipped"; d="Couldn't test this page"; }
    else if (!r.found_email_box) { cls="meh"; lab="Skipped"; d="No email box found. Check this one by hand."; }
    else if (outs.length) { cls="bad"; lab="Leaks"; d=`Sends attendee ${fs.join(" and ")} to ${cos.join(", ")}`;
      extra = `<a class="act light" style="padding:7px 12px;font-size:.82rem" href="/api/scans/${encodeURIComponent(r.id)}/report">${ic("download")}Proof</a>`; }
    row.className = "panel pass " + cls;
    row.innerHTML = `<span class="st"></span><div class="grow"><div class="u">${esc(urls[i])}</div><div class="d">${esc(d)}</div></div>${extra}<span class="lab">${lab}</span>`;
  }
  const tested = results.filter(r => !r.error && r.found_email_box);
  const bad = tested.filter(r => r.leaks.some(l=>l.third_party));
  const name = esc($("#evName").value || "your event");
  $("#evSum").innerHTML = bad.length ? `<div class="evsum bad">${bad.length} of ${tested.length} pages for ${name} leak attendee info before submit</div>`
                                     : `<div class="evsum good">All ${tested.length} tested pages for ${name} look safe</div>`;
  btn.disabled = false; btn.textContent = "Check all pages";
};

// ---------- findings + ticker ----------
const EVENT_SITES = ["eventbrite","cvent","hubilo","punchbowl","lu.ma","meetup","universe","whova","addevent","ticketspice",
  "paperlesspost","evite","partiful","splashthat","bizzabo","airmeet","swapcard","accelevents","eventzilla","humanitix",
  "tickettailor","ticketleap","seatgeek","stubhub","ticketmaster","axs","dice.fm","sched","on24","goldcast"];
const isEvent = u => EVENT_SITES.some(s => (u||"").includes(s));

(async function loadFindings(){
  const {results} = await (await fetch("/api/findings")).json();
  const tested = results.filter(r => r.status === "LEAK" || r.status === "clean");
  const tk = tested.length ? tested.map(r => ({name:r.site_name, bad:r.status==="LEAK", note: r.status==="LEAK" ? "to "+r.companies.join(", ") : "clear"}))
    : [{name:"Eventbrite",bad:true,note:"to Pinterest"},{name:"Luma",bad:false,note:"clear"},{name:"Cvent",bad:true,note:"to Adobe, okt.to"},
       {name:"Meetup",bad:false,note:"clear"},{name:"Substack",bad:false,note:"clear"},{name:"Devfolio",bad:false,note:"clear"}];
  const items = tk.map(t => `<span class="tk"><i class="dot ${t.bad?"bad":""}"></i>${esc(t.name)} <small>${esc(t.note)}</small></span>`).join("");
  $("#tickerRow").innerHTML = items + items;
  if (!results.length) return;

  const leaked = results.filter(r => r.status === "LEAK");
  const clean = results.filter(r => r.status === "clean");
  const evTested = tested.filter(r => isEvent(r.url)), evLeaked = leaked.filter(r => isEvent(r.url));
  const cell = arr => arr.length ? arr.map(esc).join(", ") : "–";

  $("#findOut").innerHTML = `<div class="fg">
    <div class="bigcard">
      <div class="n"><em class="grad-text">${leaked.length}</em><span>/</span>${tested.length}</div>
      <p>pages we could test sent typed details to another company before submit was ever pressed.</p>
      ${evTested.length ? `<div class="evstat"><b>${evLeaked.length} of ${evTested.length}</b> event platforms leaked, compared to <b>${leaked.length-evLeaked.length} of ${tested.length-evTested.length}</b> other sites.</div>` : ""}
      <p class="small">${results.length - tested.length} more pages couldn't be tested automatically (no email box, or the site blocked our browser).</p>
    </div>
    <div class="panel ftable">
      <div class="frow fhead"><span>Site</span><span>What leaked</span><span>Sent to</span></div>
      ${leaked.map(r => `<div class="frow">
        <span class="fsite"><b>${esc(r.site_name)}</b>${isEvent(r.url) ? `<em class="evbadge">Event</em>` : ""}<small class="mono">${esc(r.url.replace(/^https?:\/\//,""))}</small></span>
        <span class="ffields">${(r.fields||["email"]).map(f=>`<i>${esc(f)}</i>`).join("")}</span>
        <span class="fto">${cell(r.companies)}</span></div>`).join("")}
      <div class="fclean"><span class="lbl">${ic("check")}No leak seen</span><div class="cleanlist">${clean.map(r=>`<span>${esc(r.site_name)}</span>`).join("")}</div></div>
    </div></div>`;
  $("#findOut").classList.add("in");
})();
