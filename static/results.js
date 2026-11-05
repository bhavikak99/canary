 // ---------- results ----------
function identChips(r){
  const id = r.identity || {email: r.canary};
  return `<div class="ident">${Object.entries(id).map(([k,v]) => `<span>${esc(k)}: ${esc(v)}</span>`).join("")}</div>`;
}
function showResult(r, o={}){
  const box = $("#resultsInner"); $("#results").style.display = "block";
  if (r.error || !r.found_email_box) {
    const t = r.error ? "We couldn't test this page" : "No email box on this page";
    const p = r.error ? String(r.error).slice(0,240) : "Even after saying no to cookies and clicking sign-up buttons. Try a sign-in or sign-up page.";
    box.innerHTML = `<div class="verdict meh"><span class="lbl">${ic(r.error?"x":"none")}${r.error?"Error":"No form found"}</span><h2>${esc(t)}</h2><p>${esc(p)}</p></div>`;
    if (!o.quiet) $("#results").scrollIntoView({behavior:"smooth"});
    return;
  }
  const outs = r.leaks.filter(l => l.third_party);
  const byCo = {};
  outs.forEach(l => { const c = byCo[l.company] = byCo[l.company] || {...l, fields:new Set()}; c.fields.add(l.field || "email"); });
  const cos = Object.values(byCo);
  const fields = [...new Set(outs.map(l => l.field || "email"))];
  const declined = r.cookie_choice === "rejected";
  let h = "";
  if (outs.length) {
    h += `<div class="verdict bad"><span class="lbl">${ic("leak")}Leak detected</span>
      <h2>Your ${fields.join(" and ")} left ${esc(r.site_name)} before you hit submit.</h2>
      <p>It went to ${cos.map(c=>`<b>${esc(c.company)}</b>`).join(", ")}${declined?", even after we said no to cookies":""}.</p>
      <div class="flow"><span class="node">${ic("user")}You</span><span class="arw">${ic("arrow")}</span><span class="node">${ic("open")}${esc(r.site_name)}</span><span class="arw">${ic("arrow")}</span>
      ${cos.map((c,i)=>`<span class="hit" style="animation-delay:${.4+i*.3}s">${esc(c.company)}<small>${esc(c.category)}</small></span>`).join("")}</div>
      ${identChips(r)}</div>`;
  } else {
    h += `<div class="verdict good"><span class="lbl">${ic("check")}All clear</span><h2>Nothing left ${esc(r.site_name)} before submit.</h2>
      <p>None of the fake details we typed went to an outside company.</p>${identChips(r)}</div>`;
  }
  const fastest = outs.length ? Math.min(...outs.map(l=>l.seconds_after_typing)) : null;
  h += `<div class="stats">
    <div class="panel stat"><div class="n">${Object.keys(r.third_parties).length}</div><div class="l">outside servers contacted</div></div>
    <div class="panel stat"><div class="n ${outs.length?"red":"green"}">${cos.length}</div><div class="l">companies got your info</div></div>
    <div class="panel stat"><div class="n">${fastest!==null ? fastest+"s" : "0"}</div><div class="l">${fastest!==null?"after typing started":"leaks found"}</div></div>
    <div class="panel stat"><div class="n">0</div><div class="l">times submit was pressed</div></div></div>`;
  const hist = r.history || [];
  if (hist.length >= 2) h += `<div class="histline">History for this page: leaked in <b>${hist.filter(x=>x.leaked).length} of ${hist.length}</b> tests <span class="hist">${hist.map(x=>`<i class="${x.leaked?"y":"n"}" title="${esc(x.time)}"></i>`).join("")}</span>${o.replay?"<span>(saved test)</span>":""}</div>`;

  if (outs.length) {
    h += `<div class="h3">The proof</div><p class="h3sub">The exact messages the page sent, and what was inside them.</p>`;
    cos.forEach(c => {
      const ls = outs.filter(l => l.company === c.company);
      const firsts = {}; ls.forEach(l => { const f = l.field||"email"; if (!firsts[f]) firsts[f] = l; });
      h += `<div class="panel card"><div class="top">${esc(c.company)} <span class="tag ${esc(c.risk)}">${esc(c.category)}</span></div>`;
      Object.entries(firsts).forEach(([f,l]) => {
        const val = (r.identity||{})[f] || r.canary;
        h += `<div class="desc" style="margin-top:8px"><span class="tag field">${esc(f)}</span> received as <b>${esc(l.disguise)}</b>, <b>${l.seconds_after_typing}s</b> after typing started, via <span class="mono">${esc(l.host)}</span></div>
          <details style="margin-top:6px"><summary>Show the exact request</summary><pre>${esc(l.request_url.slice(0,700))}</pre>
          ${l.disguise.includes("hash") ? `<div class="note">A hash looks random, but the same input always gives the same hash, so ${esc(c.company)} can still match it to you. Hash <code>${esc(val)}</code> yourself and compare.</div>` : ""}</details>`;
      });
      h += `</div>`;
    });
  }

  if (declined) {
    const ads = r.after_reject_ads || [];
    h += `<div class="h3">Did "Reject all" work?</div><p class="h3sub">We clicked "${esc((r.steps||[]).find(s=>s.includes("cookie"))?.match(/"(.*)"/)?.[1] || "Reject all")}" and then kept watching.</p>
      <div class="panel card reject"><div class="big ${ads.length?"":"ok"}">${ads.length}</div><div><b>${ads.length ? "ad and marketing companies were still contacted after we said no" : "No ad or marketing companies contacted after we said no"}</b>
      ${ads.length ? `<div class="cos">${ads.map(a=>`<span class="tag ${esc(a.risk)}">${esc(a.company)}</span>`).join("")}</div>` : ""}
      <div class="note" style="margin-top:6px">Some of these may only load scripts. Being contacted is not the same as receiving your details.</div></div></div>`;
  }

  if (o.aiLoading) h += `<div class="h3">What they promised</div><div class="panel card thinking"><span class="spinner"></span>Claude is reading their privacy policy. Then our code checks every quote.</div>`;
  else if (r.policy) h += policyHtml(r.policy, r.policy_url);
  else if (r.policy_error) h += `<div class="h3">What they promised</div><div class="panel card">The AI check didn't work: ${esc(String(r.policy_error).slice(0,300))}</div>`;

  if (outs.length) {
    h += `<div class="h3">Do something about it</div><p class="h3sub">Download the evidence, or send ${esc(r.site_name)} a message.</p><div class="actions">
      <a class="act dark" href="/api/scans/${encodeURIComponent(r.id)}/report">${ic("download")}Download evidence report</a>
      <button class="act light" id="msgBtn">${ic("mail")}Write to ${esc(r.site_name)}</button></div>
      <div class="panel card msg" id="msgBox"><pre id="msgText"></pre><button class="act light" id="copyBtn">${ic("copy")}Copy message</button></div>`;
  }
  h += `<div class="h3">Details</div>
    <div class="panel card"><details><summary>Everyone this page talked to (${Object.keys(r.third_parties).length} outside servers)</summary>
      <div class="cats">${(r.breakdown||[]).map(g=>`<div class="cat"><div class="h">${esc(g.category)} <span class="tag ${esc(g.risk)}">${g.companies.length}</span></div><div class="c">${g.companies.map(esc).join(", ")}</div></div>`).join("")}</div></details></div>
    <div class="panel card"><details><summary>What the robot did, step by step</summary><ol style="color:var(--ink-2)">${(r.steps||[]).map(s=>`<li>${esc(s)}</li>`).join("")}</ol></details></div>
    ${r.has_screenshot ? `<div class="panel card"><details><summary>Screenshot: details typed, submit never pressed</summary><img class="shot" src="/api/scans/${encodeURIComponent(r.id)}/screenshot" alt=""></details></div>` : ""}`;
  box.innerHTML = h;
  const mb = $("#msgBtn");
  if (mb) mb.onclick = async () => {
    const t = await (await fetch(`/api/scans/${encodeURIComponent(r.id)}/message`)).text();
    $("#msgText").textContent = t; $("#msgBox").style.display = "block";
    $("#copyBtn").onclick = () => { navigator.clipboard.writeText(t); $("#copyBtn").innerHTML = ic("check")+"Copied"; };
  };
  if (!o.quiet) $("#results").scrollIntoView({behavior:"smooth", block:"start"});
}
function policyHtml(pc, url){
  const lab = {contradicts:["Goes against what we caught","high"], discloses:["Admits this kind of sharing","medium"], unclear:["Too vague to tell","low"]};
  let h = `<div class="h3">What they promised</div><p class="h3sub">${esc(pc.summary)}</p>`;
  pc.statements.forEach(s => { const [t,k] = lab[s.verdict] || ["","low"];
    h += `<div class="panel card quote"><span class="tag ${k}">${t}</span><blockquote>"${esc(s.quote)}"</blockquote><div class="why">${esc(s.explanation)}</div></div>`; });
  if (pc.statements.length) h += `<span class="okline">${ic("check")}All ${pc.statements.length} quotes checked word-for-word against the <a href="${esc(url)}" target="_blank" rel="noopener">real policy</a></span>`;
  if (pc.rejected && pc.rejected.length) h += `<span class="okline warn">${ic("x")}${pc.rejected.length} AI quote(s) thrown out: not in the real policy</span>`;
  return h;
}
