# Canary web app. Run with:  python -m streamlit run app.py
import glob
import json
import os
import subprocess
import sys
import streamlit as st

from receivers import identify_any, pretty_site
from report import evidence_html, vendor_message

st.set_page_config(page_title="Canary", page_icon="🐤", layout="centered")

# Known privacy-policy pages, so the AI check works with one click for our main examples.
POLICIES = {
    "www.eventbrite.com": "https://www.eventbrite.com/help/en-us/articles/460838/eventbrite-privacy-policy/",
    "www.cvent.com": "https://www.cvent.com/en/privacy-policy",
}

st.markdown("""
<style>
.block-container {padding-top: 2.2rem; max-width: 820px;}
.hero {background: linear-gradient(135deg,#FFE27A 0%,#FFC93C 100%); border-radius: 20px; padding: 28px 30px 22px;
       margin-bottom: 18px; color:#1E1E24;}
.hero h1 {font-size: 2.7rem; margin: 0; line-height: 1.1;}
.hero p {font-size: 1.15rem; margin: .5rem 0 0; opacity:.85;}
.steps {display:flex; gap:10px; margin-top:18px; flex-wrap:wrap;}
.steps div {flex:1; min-width:180px; background: rgba(255,255,255,.55); border-radius: 12px; padding: 10px 12px; font-size:.92rem;}
.steps b {display:block; font-size:1rem;}
.verdict {border-radius: 16px; padding: 20px 22px; margin: 6px 0 14px;}
.verdict h2 {margin:0 0 6px; font-size:1.55rem; line-height:1.25;}
.verdict p {margin:0; font-size:1.05rem;}
.v-bad {background:#FFE4E1; border:2px solid #E5484D; color:#7A1218;}
.v-good {background:#E3F7E8; border:2px solid #30A46C; color:#14532D;}
.v-meh {background:#F1F1F3; border:2px solid #C8C8CE; color:#333;}
.pill {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem; font-weight:600; margin-left:6px;}
.high {background:#FFD6D6; color:#A11;} .medium {background:#FFEDC2; color:#7A5200;}
.low, .unknown {background:#ECECEF; color:#444;}
.cat {margin: 4px 0 10px;} .cat b {font-size:.98rem;} .cat span {opacity:.8;}
.bignum {font-size: 3.4rem; font-weight: 800; line-height: 1;}
.flow {display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin: 4px 0 18px;}
.node {background:#FFF; border:2px solid #E8E2CF; border-radius:14px; padding:10px 14px; text-align:center;
       min-width:120px; font-size:1.6rem;}
.node b {display:block; font-size:1rem;} .node small, .chip small {display:block; font-size:.75rem; opacity:.7;}
.arrow {font-size:2rem; font-weight:700; color:#999;} .arrow.red {color:#E5484D;}
.targets {display:flex; flex-direction:column; gap:6px;}
.chip {border-radius:12px; padding:8px 12px; font-weight:700; border:2px solid;}
.chip.high {background:#FFE4E1; border-color:#E5484D; color:#7A1218;}
.chip.medium {background:#FFF1D0; border-color:#E0A800; color:#6B4A00;}
.chip.low, .chip.unknown {background:#F1F1F3; border-color:#C8C8CE; color:#333;}
.footer {text-align:center; opacity:.55; font-size:.85rem; margin-top:40px;}
</style>
<div class="hero">
  <h1>🐤 Canary</h1>
  <p>Does a website grab your email <b>before</b> you click submit? We test it with a fake one and catch it in the act.</p>
  <div class="steps">
    <div><b>1 · Plant</b>A one-of-a-kind fake email that exists nowhere else.</div>
    <div><b>2 · Type, never submit</b>A real browser rejects cookies, types it in, then stops.</div>
    <div><b>3 · Catch</b>We search everything the page sends, even scrambled copies.</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers
def site_history(url):
    rows = []
    for p in glob.glob("scans/*.json"):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if d.get("url") == url and d.get("found_email_box"):
            rows.append((d["time"], len({l["host"] for l in d["leaks"] if l.get("third_party")})))
    return sorted(rows)


def show_breakdown(third_parties):
    """Group the raw server list into understandable categories."""
    groups = {}
    for host, n in third_parties.items():
        company, category, risk = identify_any(host)
        g = groups.setdefault(category, {"risk": risk, "companies": set()})
        g["companies"].add(company if company != "Unknown company" else host)
    order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    for cat, g in sorted(groups.items(), key=lambda x: (order.get(x[1]["risk"], 9), x[0])):
        st.markdown(f"<div class='cat'><b>{cat}</b> <span class='pill {g['risk']}'>{len(g['companies'])}</span><br>"
                    f"<span>{', '.join(sorted(g['companies']))}</span></div>", unsafe_allow_html=True)


def show_policy(pc, policy_url):
    st.markdown("### 📜 What they promised vs. what we caught")
    st.caption("Our AI read the site's privacy policy and pulled out the sentences that matter. "
               "Then our code checked every quote word-for-word against the real policy.")
    st.write(pc["summary"])
    icons = {"contradicts": "❌ Goes against what we caught",
             "discloses": "⚠️ Admits this kind of sharing",
             "unclear": "❔ Too vague to tell"}
    for s_ in pc["statements"]:
        with st.container(border=True):
            st.markdown(f"**{icons[s_['verdict']]}**")
            st.markdown(f"> {s_['quote']}")
            st.caption(s_["explanation"])
    if pc["statements"]:
        st.caption(f"✔ All {len(pc['statements'])} quotes verified word-for-word against the [real policy]({policy_url}).")
    if pc.get("rejected"):
        st.caption(f"🛡 {len(pc['rejected'])} quote(s) the AI suggested were thrown out because they're not actually "
                   "in the policy.")


def show_result(r, key):
    if r.get("error"):
        st.markdown(f"<div class='verdict v-meh'><h2>Couldn't test this page</h2><p>{r['error'][:200]}</p></div>",
                    unsafe_allow_html=True)
        return
    if not r["found_email_box"]:
        st.markdown("<div class='verdict v-meh'><h2>No email box found</h2>"
                    "<p>Even after rejecting cookies and clicking sign-up buttons. Try a sign-in or sign-up page.</p></div>",
                    unsafe_allow_html=True)
        return

    outside = [l for l in r["leaks"] if l.get("third_party")]
    companies = sorted({l["company"] for l in outside})
    rejected = r.get("cookie_choice") == "rejected"
    if outside:
        st.markdown(f"<div class='verdict v-bad'><h2>❌ Your email left this page before you clicked submit</h2>"
                    f"<p>{pretty_site(r['site'])} sent it to <b>{', '.join(companies)}</b>"
                    f"{' — even after we rejected cookies' if rejected else ''}.</p></div>", unsafe_allow_html=True)
        show_flow(r, outside)
    else:
        st.markdown(f"<div class='verdict v-good'><h2>✅ No leak seen</h2><p>Your email didn't leave "
                    f"{pretty_site(r['site'])} for an outside company before submit.</p></div>", unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Outside servers contacted", len(r["third_parties"]))
    m2.metric("Got your email", len(companies))
    m3.metric("Submit clicked?", "Never")

    hist = site_history(r["url"])
    hist_txt = ""
    if len(hist) >= 2:
        leaked = sum(1 for _, n in hist if n)
        hist_txt = f"**History for this page:** leaked in {leaked} of {len(hist)} tests " + " ".join("❌" if n else "✅" for _, n in hist)
    st.markdown(f"<small>Fake email: <code>{r['canary']}</code> · tested {r['time']}</small>", unsafe_allow_html=True)
    if hist_txt:
        st.markdown(hist_txt)

    with st.expander("🤖 What the robot did, step by step"):
        for s in r.get("steps", []):
            st.write("· " + s)

    if outside:
        st.markdown("### 🔍 Who got it, and the proof")
        for l in outside:
            with st.container(border=True):
                st.markdown(f"**{l['company']}** <span class='pill {l['risk']}'>{l['category']}</span>",
                            unsafe_allow_html=True)
                st.write(f"Got your email as a **{l['disguise']}**, **{l['seconds_after_typing']} seconds** after "
                         f"typing started.")
                with st.expander("Show the exact request"):
                    st.code(l["request_url"][:500], language=None)
                    if "hash" in l["disguise"]:
                        st.caption("A hash looks like gibberish, but the same email always makes the same hash, "
                                   "so the receiver can still match it to you. Hash the fake email above with "
                                   + l["disguise"].split()[0] + " and compare.")

    if r.get("policy"):
        show_policy(r["policy"], r.get("policy_url", ""))

    if outside:
        st.markdown("### ✋ Do something about it")
        d1, d2 = st.columns(2)
        d1.download_button("⬇️ Evidence report", evidence_html(r), file_name=f"canary-report-{r['site']}.html",
                           mime="text/html", use_container_width=True, key=f"rep-{key}")
        d2.download_button("✉️ Message to the company", vendor_message(r), file_name=f"canary-message-{r['site']}.txt",
                           use_container_width=True, key=f"msg-{key}")
        with st.expander("Preview the message"):
            st.text(vendor_message(r))

    if r.get("screenshot") and os.path.exists(r["screenshot"]):
        with st.expander("📸 Screenshot: email typed, submit never clicked"):
            st.image(r["screenshot"])

    with st.expander(f"🌐 Everyone this page talked to ({len(r['third_parties'])} outside servers)"):
        show_breakdown(r["third_parties"])


def run_scan_live(url, label=""):
    """Run a scan and show its progress messages on screen as they happen."""
    with st.status(f"Testing {label or url}...", expanded=True) as box:
        proc = subprocess.Popen([sys.executable, "canary_scan.py", url, "--json", "--live"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        result = None
        for line in proc.stdout:
            line = line.rstrip()
            if line.startswith("PROGRESS:"):
                msg = line[len("PROGRESS:"):]
                st.markdown(f"**{msg}**" if msg.startswith("🚨") else msg)
            elif line.startswith("RESULT:"):
                result = json.loads(line[len("RESULT:"):])
        proc.wait()
        if result is None:
            box.update(label="Scan crashed", state="error")
            st.code(proc.stderr.read()[-2000:])
            return None
        n = len({l["host"] for l in result["leaks"] if l.get("third_party")})
        if n:
            box.update(label=f"🚨 Caught it: your email reached {n} outside compan{'y' if n == 1 else 'ies'}",
                       state="error", expanded=False)
        elif result.get("found_email_box"):
            box.update(label="✅ Done: no leak seen", state="complete", expanded=False)
        else:
            box.update(label="Done: no email box found", state="complete", expanded=False)
        return result


def show_flow(r, outside):
    """A simple picture: You -> Site -> companies that got the email."""
    chips = "".join(f"<div class='chip {l['risk']}'>{l['company']}<small>{l['category']}</small></div>"
                    for l in {l['company']: l for l in outside}.values())
    st.markdown(f"""
    <div class='flow'>
      <div class='node'>🙂<b>You</b><small>typed an email</small></div>
      <div class='arrow'>→</div>
      <div class='node'>🌐<b>{pretty_site(r['site'])}</b><small>never clicked submit</small></div>
      <div class='arrow red'>→</div>
      <div class='targets'>{chips}</div>
    </div>""", unsafe_allow_html=True)


def run_policy_check(r, policy_url):
    """Run the AI policy check and save the answer into the scan file (so replay shows it too)."""
    with st.spinner("AI is reading the privacy policy, then our code checks every quote (~30-60s)..."):
        proc = subprocess.run([sys.executable, "policy_check.py", policy_url, r["saved_as"]],
                              capture_output=True, text=True, timeout=300)
    try:
        pc = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        st.warning("Policy check failed. Is your ANTHROPIC_API_KEY set in this terminal?")
        st.code(proc.stderr[-1500:])
        return r
    r["policy"], r["policy_url"] = pc, policy_url
    with open(r["saved_as"], "w") as f:
        json.dump(r, f, indent=2)
    return r


tab_test, tab_event, tab_study = st.tabs(["🔎 Test a page", "🎟️ Check my event", "📊 Our investigation"])

# ---------------------------------------------------------------- Test a page
with tab_test:
    mode = st.radio("Mode", ["Run a live test", "Replay a saved test"], horizontal=True, label_visibility="collapsed")

    if mode == "Run a live test":
        url = st.text_input("Page with an email box (sign-in, sign-up, registration, newsletter):",
                            "https://www.eventbrite.com/signin/")
        site = url.split("/")[2] if "//" in url else ""
        use_ai = st.toggle("Also compare with the site's privacy policy (AI)", value=bool(os.environ.get("ANTHROPIC_API_KEY")))
        policy_url = st.text_input("Privacy policy page:", POLICIES.get(site, "")) if use_ai else ""

        if st.button("Run Canary test", type="primary", use_container_width=True):
            r = run_scan_live(url)
            if r is None:
                st.stop()
            if policy_url.strip() and r.get("found_email_box"):
                r = run_policy_check(r, policy_url.strip())
            st.session_state["live"] = r

        if "live" in st.session_state:
            show_result(st.session_state["live"], "live")
    else:
        saved = sorted(glob.glob("scans/*.json"), reverse=True)
        if not saved:
            st.info("No saved tests yet. Every live test is saved automatically.")
        else:
            def label(p):
                d = json.load(open(p))
                n = len({l["host"] for l in d["leaks"] if l.get("third_party")})
                tag = f"❌ leaked to {n}" if n else ("✅ clean" if d["found_email_box"] else "— no form")
                return f"{pretty_site(d['site'])} · {d['time'][:16]} · {tag}" + (" · 📜 AI" if d.get("policy") else "")
            choice = st.selectbox("Saved test:", saved, format_func=label)
            st.caption("A real test we ran earlier, shown exactly as it was recorded.")
            show_result(json.load(open(choice)), "replay")

# ---------------------------------------------------------------- Check my event
with tab_event:
    st.markdown("**Running an event?** Paste every page your attendees will type their email into: "
                "registration, tickets, sign-up forms, newsletter. Canary checks them all before you send the link.")
    event_name = st.text_input("Event name:", "My Hackathon 2026")
    pages = st.text_area("One page per line:",
                         "https://www.eventbrite.com/signin/\nhttps://lu.ma/signin\nhttps://www.cvent.com/", height=110)
    if st.button("Check all pages", type="primary", use_container_width=True):
        urls = [u.strip() for u in pages.splitlines() if u.strip()]
        results = []
        for i, u in enumerate(urls):
            r = run_scan_live(u, f"page {i + 1} of {len(urls)}: {u}")
            results.append(r or {"url": u, "site": u.split("/")[2] if "//" in u else u, "error": "scan crashed",
                                 "found_email_box": False, "leaks": [], "third_parties": {}})
        st.session_state["event"] = (event_name, results)

    if "event" in st.session_state:
        name, results = st.session_state["event"]
        tested = [r for r in results if r.get("found_email_box") and not r.get("error")]
        bad = [r for r in tested if any(l.get("third_party") for l in r["leaks"])]
        if bad:
            st.markdown(f"<div class='verdict v-bad'><h2>⚠️ {len(bad)} of {len(tested)} pages for {name} leak attendee "
                        f"emails before submit</h2><p>Consider switching tools for these pages, or ask the company to turn "
                        f"this off.</p></div>", unsafe_allow_html=True)
        elif tested:
            st.markdown(f"<div class='verdict v-good'><h2>✅ All {len(tested)} tested pages for {name} look safe</h2>"
                        f"<p>No attendee email left for an outside company before submit.</p></div>",
                        unsafe_allow_html=True)
        for r in results:
            outs = [l for l in r.get("leaks", []) if l.get("third_party")]
            with st.container(border=True):
                if r.get("error"):
                    st.write(f"⚪ **{r['url']}** · couldn't test ({r['error'][:80]})")
                elif not r.get("found_email_box"):
                    st.write(f"⚪ **{r['url']}** · no email box found, check this one by hand")
                elif outs:
                    st.write(f"❌ **{r['url']}** · sends emails to " +
                             ", ".join(f"**{c}**" for c in sorted({l['company'] for l in outs})))
                    st.download_button("⬇️ Evidence report", evidence_html(r), file_name=f"canary-report-{r['site']}.html",
                                       mime="text/html", key=f"ev-{r['saved_as']}")
                else:
                    st.write(f"✅ **{r['url']}** · no leak seen")

# ---------------------------------------------------------------- Investigation
with tab_study:
    if not os.path.exists("batch_results.json"):
        st.info("No investigation yet. Run `python batch_scan.py` to test every site in sites.txt.")
    else:
        results = json.load(open("batch_results.json"))
        tested = [r for r in results if r["status"] in ("LEAK", "clean")]
        leaked = [r for r in results if r["status"] == "LEAK"]
        st.markdown(f'<div class="bignum">{len(leaked)} of {len(tested)}</div>', unsafe_allow_html=True)
        st.markdown("**sign-up & sign-in pages we tested sent a typed email to another company before submit was "
                    "ever clicked.** Each page got its own fresh fake email.")
        dates = sorted(r["time"] for r in results if r.get("time"))
        if dates:
            st.caption(f"Tested {dates[0][:10]}. {len(results) - len(tested)} more pages couldn't be tested "
                       "automatically (no email box found, or the site blocked our browser).")
        if leaked:
            st.markdown("### ❌ Leaked before submit")
            for r in leaked:
                with st.container(border=True):
                    st.write(f"**{pretty_site(r.get('site') or r['url'].split('/')[2])}** · {r['url']}")
                    seen = {}
                    for l in [l for l in r["leaks"] if l.get("third_party")]:
                        seen.setdefault(l.get("company", l["host"]), (l.get("category", ""), l.get("risk", "unknown")))
                    st.markdown(" ".join(f"**{c}** <span class='pill {rk}'>{cat}</span> &nbsp;"
                                         for c, (cat, rk) in seen.items()), unsafe_allow_html=True)
        clean = [r for r in results if r["status"] == "clean"]
        if clean:
            st.markdown("### ✅ No leak seen")
            st.write(" · ".join(pretty_site(r.get("site") or r["url"].split("/")[2]) for r in clean))
        with st.expander("Full results table"):
            st.dataframe([{"site": r["url"], "result": r["status"], "email sent to": ", ".join(r["leaked_to"]),
                           "outside servers": len(r.get("third_parties", {}))} for r in results],
                         use_container_width=True)

st.markdown("<div class='footer'>🐤 Canary · built for ETHIS AI for Greater Good · "
            "uses fake @example.com emails and never submits a form</div>", unsafe_allow_html=True)
