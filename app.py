# Canary web app. Run with:  streamlit run app.py
import json
import subprocess
import sys
import streamlit as st

st.set_page_config(page_title="Canary", page_icon="🐤", layout="centered")
st.title("🐤 Canary")
st.write("We give a website a fake email, **never click submit**, and catch where it goes.")

url = st.text_input("Page with an email box (sign-in, signup, registration):",
                    "https://www.eventbrite.com/signin/")
with st.expander("Beta: compare against the site's privacy policy (needs an Anthropic API key)"):
    policy_url = st.text_input("Privacy policy URL:", "")

if st.button("Run Canary test", type="primary"):
    with st.spinner("Opening the page, typing a fake email, watching the traffic (~20s)..."):
        # Run the scan in a separate process so Playwright and Streamlit don't fight.
        proc = subprocess.run([sys.executable, "canary_scan.py", url, "--json"],
                              capture_output=True, text=True, timeout=120)
    try:
        r = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        st.error("Scan crashed.")
        st.code(proc.stderr[-2000:])
        st.stop()

    if r["error"]:
        st.error(f"Couldn't load the page: {r['error'][:300]}")
        st.stop()
    if not r["found_email_box"]:
        st.warning("No email box found on this page. Try a sign-in or signup page.")
        st.stop()

    st.caption(f"Fake email used: `{r['canary']}` · tested {r['time']}")
    outside = [l for l in r["leaks"] if l["third_party"]]

    if outside:
        companies = sorted({l["host"] for l in outside})
        st.error(f"### ❌ Your email left this page before you clicked submit\n"
                 f"It was sent to **{len(companies)}** outside compan{'y' if len(companies)==1 else 'ies'}: "
                 + ", ".join(f"`{c}`" for c in companies))
        st.subheader("The proof")
        for l in outside:
            with st.container(border=True):
                st.write(f"**{l['host']}** received your email as a **{l['disguise']}** ({l['method']} request)")
                st.code(l["request_url"][:400], language=None)
                if "hash" in l["disguise"]:
                    st.caption("A hash looks like gibberish, but the same email always makes the same hash, "
                               "so the receiver can still match it to you.")

        st.subheader("What you can do")
        st.markdown(
            "**If you're an organizer choosing this page for your attendees:**\n"
            "- **Consider another platform.** In our tests, Luma, Meetup, Devfolio and Universe "
            "did not leak the email before submit.\n"
            "- **Send this proof to the platform.** The request above shows exactly what was sent and to whom. "
            "You usually can't remove their trackers yourself; only they can.\n"
            "- **Tell your attendees** if you keep using it, so they can choose what email to use.\n\n"
            "**If you're signing up yourself:**\n"
            "- Use an email alias (e.g. iCloud Hide My Email, SimpleLogin) so the real address never reaches them.\n"
            "- A tracker blocker such as uBlock Origin blocks many of these requests."
        )
    else:
        st.success("### ✅ No leak seen\nYour email didn't leave the page before submit.")

    if policy_url.strip():
        st.subheader("What they promised vs. what we caught")
        with open("last_scan.json", "w") as f:
            json.dump(r, f)
        with st.spinner("Reading the privacy policy and checking every quote (~30-60s)..."):
            pproc = subprocess.run([sys.executable, "policy_check.py", policy_url, "last_scan.json"],
                                   capture_output=True, text=True, timeout=300)
        try:
            pc = json.loads(pproc.stdout.strip().splitlines()[-1])
            st.write(pc["summary"])
            icons = {"contradicts": "❌ Contradicts what we caught",
                     "discloses": "⚠️ Admits this kind of sharing",
                     "unclear": "❔ Too vague to judge"}
            for s_ in pc["statements"]:
                with st.container(border=True):
                    st.markdown(f"**{icons[s_['verdict']]}**")
                    st.markdown(f"> {s_['quote']}")
                    st.caption(s_["explanation"])
            if pc["statements"]:
                st.caption(f"✔ Every quote above was checked word-for-word against the [policy]({policy_url}).")
            if pc["rejected"]:
                st.caption(f"🛡 {len(pc['rejected'])} AI-suggested quote(s) were thrown out because "
                           "they don't appear in the actual policy.")
        except Exception:
            st.warning("Policy check failed.")
            st.code(pproc.stderr[-1500:])

    if r["screenshot"]:
        st.subheader("What the page looked like")
        st.image(r["screenshot"], caption="Email typed. Submit never clicked.")

    with st.expander(f"Every outside server this page talked to ({len(r['third_parties'])})"):
        for host, n in sorted(r["third_parties"].items(), key=lambda x: -x[1]):
            st.write(f"{n} × `{host}`")
