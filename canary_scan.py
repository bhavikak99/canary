# The Canary engine: plant a fake identity (email, name, phone), never submit, catch where it goes.
# Run directly:  python canary_scan.py https://www.eventbrite.com/signin/
import base64
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime
from urllib.parse import quote, urljoin, urlparse
from playwright.sync_api import sync_playwright

from receivers import identify

# What a box for each kind of personal info usually looks like.
SELECTORS = {
    "email": ("input[type=email]:visible, input[name*=email i]:visible, input[id*=email i]:visible, "
              "input[autocomplete=email]:visible, input[placeholder*=email i]:visible"),
    "first": ("input[autocomplete=given-name]:visible, input[name*=first i]:visible, input[id*=first i]:visible, "
              "input[placeholder*='first name' i]:visible"),
    "last": ("input[autocomplete=family-name]:visible, input[name*=last i]:visible, input[id*=last i]:visible, "
             "input[placeholder*='last name' i]:visible"),
    "full": ("input[autocomplete=name]:visible, input[name=name i]:visible, input[name*=fullname i]:visible, "
             "input[name*=full_name i]:visible, input[placeholder*='full name' i]:visible, input[placeholder='Name' i]:visible"),
    "phone": ("input[type=tel]:visible, input[autocomplete=tel]:visible, input[name*=phone i]:visible, "
              "input[id*=phone i]:visible, input[name*=mobile i]:visible, input[placeholder*=phone i]:visible"),
}

# Words on buttons/links that usually lead to a form.
OPEN_FORM_WORDS = re.compile(r"^\s*(sign ?in|log ?in|sign ?up|register|create (an )?account|join( now| free)?|"
                             r"subscribe|get started|continue with email|use email)\s*$", re.I)
# Cookie banners: we prefer saying NO. If a site still tracks or leaks after we reject, that's even stronger.
REJECT_WORDS = re.compile(r"^\s*(reject( all)?|decline( all)?|deny( all)?|only (necessary|essential)|"
                          r"necessary only|refuse( all)?|reject (all )?cookies|decline (all )?cookies)\s*$", re.I)

LIVE = "--live" in sys.argv  # when the website runs us, print progress lines it can show in real time


def progress(msg):
    if LIVE:
        print("PROGRESS:" + msg, flush=True)


def h(algo, s):
    return hashlib.new(algo, s.encode()).hexdigest()


def make_identity():
    """A fake person who exists nowhere else. Every value is unique to this one test."""
    token = uuid.uuid4().hex[:8]
    letters = "".join("bcdfghjklmnpqrstv"[int(c, 16)] for c in token)  # unique, letters only (names can't have digits)
    digits = "".join(str(int(c, 16) % 10) for c in token)[:4]
    return {
        "token": token,
        "email": f"canary-{token}@example.com",
        "first": "Robin",
        "last": "Canary" + letters.capitalize(),        # e.g. CanaryKpqdmrtf: unique last name
        "phone": f"415555{digits}",                      # 415-555-xxxx: 555 numbers are reserved for fiction
    }


def make_variants(ident):
    """Every disguise each piece of info might wear when it's sent out. Trackers often hash (scramble) it."""
    e, last, ph = ident["email"], ident["last"].lower(), ident["phone"]
    return {
        "email": {
            "plain text": e, "URL-encoded": quote(e, safe=""), "base64": base64.b64encode(e.encode()).decode(),
            "MD5 hash": h("md5", e), "SHA-1 hash": h("sha1", e), "SHA-256 hash": h("sha256", e),
        },
        "name": {
            "plain text": last, "SHA-256 hash": h("sha256", last), "MD5 hash": h("md5", last),
        },
        "phone": {
            "plain text": ph, "with country code": "1" + ph,
            "SHA-256 hash": h("sha256", "1" + ph), "SHA-256 hash ": h("sha256", ph), "MD5 hash": h("md5", "1" + ph),
        },
    }


def same_site(host, site):
    """Rough check: is this host the site itself? (www.eventbrite.com vs cdn.eventbrite.com)"""
    base = ".".join(site.split(".")[-2:])
    return host == base or host.endswith("." + base)


def find_box(page, kind):
    """Look for a box on the page AND inside frames (embedded forms often live in iframes)."""
    for frame in page.frames:
        try:
            box = frame.locator(SELECTORS[kind]).first
            if box.count() > 0:
                return box
        except Exception:
            continue
    return None


def click_first(page, pattern):
    """Click the first visible button/link whose text matches the pattern. Returns its text or None."""
    for el in page.locator("button:visible, a:visible, [role=button]:visible").all()[:200]:
        try:
            text = (el.inner_text(timeout=500) or "").strip()
        except Exception:
            continue
        if text and len(text) < 40 and pattern.match(text):
            try:
                el.click(timeout=3000)
                return text
            except Exception:
                continue
    return None


def find_privacy_link(page):
    """Find the site's OWN privacy policy link (usually in the footer).
    Skips other companies' policies, like the 'protected by reCAPTCHA, Google Privacy Policy' link."""
    try:
        links = page.eval_on_selector_all("a[href]", "els => els.map(a => [a.innerText || '', a.getAttribute('href')])")
    except Exception:
        return None
    site = urlparse(page.url).hostname or ""
    SKIP = ("google.com", "recaptcha", "hcaptcha.com", "cloudflare.com", "apple.com", "facebook.com", "microsoft.com")
    strong, weak = [], []
    for text, href in links:
        t = (text or "").strip().lower()
        hr = (href or "").lower()
        if not href or hr.startswith(("javascript:", "mailto:", "#")):
            continue
        full = urljoin(page.url, href)
        host = urlparse(full).hostname or ""
        if any(x in host for x in SKIP):
            continue
        own = same_site(host, site)
        if "privacy policy" in t or "privacy notice" in t or "privacy statement" in t:
            strong.append((not own, full))
        elif ("privacy" in t or "privacy" in hr) and "choices" not in t and "settings" not in t:
            weak.append((not own, full))
    # Prefer links on the site's own domain, then strong wording.
    for group in (strong, weak):
        group.sort(key=lambda x: x[0])
    for own_first in (False, True):
        for group in (strong, weak):
            for not_own, url in group:
                if not_own == own_first:
                    return url
    return None


def run_scan(url, save_dir="scans"):
    ident = make_identity()
    variants = make_variants(ident)
    site = urlparse(url).hostname or ""
    now = datetime.now()
    os.makedirs(save_dir, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", site.lower()).strip("-") + now.strftime("_%Y%m%d_%H%M%S")
    result = {
        "url": url, "site": site,
        "canary": ident["email"],
        "identity": {"email": ident["email"], "name": f"{ident['first']} {ident['last']}", "phone": ident["phone"]},
        "fields_typed": [],    # which kinds of info we managed to type
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "steps": [],           # what the robot did, in order (shown for transparency)
        "cookie_choice": None,
        "after_reject": {},    # outside servers contacted AFTER we clicked "reject"
        "leaks": [],
        "third_parties": {},
        "found_email_box": False,
        "policy_url_found": None,
        "screenshot": None,
        "error": None,
    }
    state = {"typing": False, "rejected": False, "at": None}
    seen = set()  # (host, field) pairs already reported, so each leak shows once

    def on_request(request):
        host = urlparse(request.url).hostname or ""
        outside = bool(host) and not same_site(host, site)
        if outside:
            result["third_parties"][host] = result["third_parties"].get(host, 0) + 1
            if state["rejected"]:
                result["after_reject"][host] = result["after_reject"].get(host, 0) + 1
        if not state["typing"]:
            return
        try:
            body = request.post_data or ""
        except Exception:
            body = ""
        haystack = (request.url + "\n" + body).lower()
        for field, forms in variants.items():
            for disguise, value in forms.items():
                if value.lower() in haystack:
                    company, category, risk = identify(host)
                    secs = round((datetime.now() - state["at"]).total_seconds(), 1)
                    result["leaks"].append({
                        "field": field, "host": host, "company": company, "category": category, "risk": risk,
                        "disguise": disguise.strip(), "method": request.method, "request_url": request.url,
                        "body_snippet": body[:500], "seconds_after_typing": secs, "third_party": outside,
                    })
                    if outside and (host, field) not in seen:
                        seen.add((host, field))
                        progress(f"leak|{company} just received your {field} ({disguise.strip()}), {secs}s after typing")
                    break

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH"))
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.on("request", on_request)
            page.goto(url, wait_until="load", timeout=45000)
            page.wait_for_timeout(3000)
            try:  # let slow trackers finish loading, so they're listening before we type
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            result["steps"].append("Opened the page")
            progress(f"open|Opened {site}: it already contacted {len(result['third_parties'])} outside servers")

            result["policy_url_found"] = find_privacy_link(page)
            if result["policy_url_found"]:
                progress("doc|Found their privacy policy link")

            # 1. Cookie banner: say no if we can, then keep watching who the page still talks to.
            rejected = click_first(page, REJECT_WORDS)
            if rejected:
                result["cookie_choice"] = "rejected"
                state["rejected"] = True
                result["steps"].append(f'Clicked "{rejected}" on the cookie banner')
                progress(f'cookie|Clicked "{rejected}" on the cookie banner')
                page.wait_for_timeout(1500)

            # 2. Find the form. If there's no email box, try clicking "Sign up"-style buttons (max 2 tries).
            box = find_box(page, "email")
            for _ in range(2):
                if box:
                    break
                clicked = click_first(page, OPEN_FORM_WORDS)
                if not clicked:
                    break
                result["steps"].append(f'Clicked "{clicked}" to find the form')
                progress(f'click|Clicked "{clicked}" to find the form')
                page.wait_for_timeout(3000)
                box = find_box(page, "email")

            if not box:
                result["steps"].append("No email box found")
                progress("none|No email box found")
                browser.close()
                return save(result, save_dir, slug)
            result["found_email_box"] = True

            # 3. Type the fake identity like a human. Click away after each box. NEVER submit.
            page.wait_for_timeout(2000)  # give scripts a moment to attach to the form we just found
            state["typing"], state["at"] = True, datetime.now()
            to_type = []
            for kind, value, label in [("first", ident["first"], "name"), ("last", ident["last"], "name"),
                                       ("full", f"{ident['first']} {ident['last']}", "name"),
                                       ("phone", ident["phone"], "phone")]:
                b = find_box(page, kind)
                if b and not (kind == "full" and "name" in [t[2] for t in to_type]):
                    to_type.append((b, value, label))
            to_type.append((box, ident["email"], "email"))

            for b, value, label in to_type:
                try:
                    progress(f"type|Typing a fake {label}: {value}")
                    b.click(timeout=3000)
                    b.press_sequentially(value, delay=50)
                    page.keyboard.press("Tab")
                    if label not in result["fields_typed"]:
                        result["fields_typed"].append(label)
                except Exception:
                    continue
            result["steps"].append(f"Typed a fake {', '.join(result['fields_typed'])} and clicked away. Never pressed submit")
            progress("watch|Done typing. We will never press submit. Now just watching what the page sends")
            for sec in range(12):
                page.wait_for_timeout(1000)
                if sec in (3, 7, 11):
                    progress(f"watch|Still watching... {len(result['third_parties'])} outside servers contacted so far")
            result["steps"].append("Watched the traffic for 12 seconds")

            shot = os.path.join(save_dir, slug + ".png")
            page.screenshot(path=shot)
            result["screenshot"] = shot
            browser.close()
    except Exception as e:
        result["error"] = str(e)

    return save(result, save_dir, slug)


def save(result, save_dir, slug):
    """Every scan is saved, so it can be replayed in the demo and used as evidence later."""
    path = os.path.join(save_dir, slug + ".json")
    result["saved_as"] = path
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
    return result


if __name__ == "__main__":
    out = run_scan(sys.argv[1])
    if "--json" in sys.argv:
        print("RESULT:" + json.dumps(out), flush=True)
    else:
        print(f"\nFake identity: {out['identity']['name']} · {out['canary']} · {out['identity']['phone']}")
        print(f"Tested {out['time']}. Typed: {', '.join(out['fields_typed']) or 'nothing'}. Never submitted.")
        for s in out["steps"]:
            print("  -", s)
        print()
        outside = [l for l in out["leaks"] if l["third_party"]]
        if out["error"]:
            print("Error:", out["error"])
        elif not out["found_email_box"]:
            print("No email field found on this page.")
        elif not outside:
            print("No leak to outside companies seen.")
        else:
            print("LEAK before submit:")
            done = set()
            for l in outside:
                if (l["host"], l["field"]) in done:
                    continue
                done.add((l["host"], l["field"]))
                print(f"  -> {l['company']} ({l['category']}) got your {l['field']} as {l['disguise']}, "
                      f"{l['seconds_after_typing']}s after typing started")
        if out["after_reject"]:
            ads = [h for h in out["after_reject"] if identify(h)[2] in ("high", "medium")]
            print(f"\nAfter we clicked reject, the page still contacted {len(out['after_reject'])} outside servers"
                  f" ({len(ads)} advertising/marketing).")
        if out["policy_url_found"]:
            print("Privacy policy found:", out["policy_url_found"])
        print(f"\nSaved: {out['saved_as']}")
