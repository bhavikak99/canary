# The Canary engine: plant a fake email, don't submit, catch where it goes.
# Run directly:  python canary_scan.py https://www.eventbrite.com/signin/
import base64
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime
from urllib.parse import quote, urlparse
from playwright.sync_api import sync_playwright

EMAIL_SELECTOR = ("input[type=email]:visible, input[name*=email i]:visible, input[id*=email i]:visible, "
                  "input[autocomplete=email]:visible, input[placeholder*=email i]:visible")


def make_variants(email):
    """Every disguise the email might wear when it's sent out."""
    return {
        "plain text": email,
        "URL-encoded": quote(email, safe=""),
        "base64": base64.b64encode(email.encode()).decode(),
        "MD5 hash": hashlib.md5(email.encode()).hexdigest(),
        "SHA-1 hash": hashlib.sha1(email.encode()).hexdigest(),
        "SHA-256 hash": hashlib.sha256(email.encode()).hexdigest(),
    }


def same_site(host, site):
    """Rough check: is this host the site itself? (www.eventbrite.com vs cdn.eventbrite.com)"""
    base = ".".join(site.split(".")[-2:])  # eventbrite.com
    return host == base or host.endswith("." + base)


def run_scan(url, screenshot_path="screenshot.png"):
    canary = f"canary-{uuid.uuid4().hex[:8]}@example.com"
    variants = make_variants(canary)
    site = urlparse(url).hostname or ""
    result = {
        "url": url,
        "canary": canary,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "leaks": [],
        "third_parties": {},
        "found_email_box": False,
        "screenshot": None,
        "error": None,
    }
    typing_started = {"flag": False}

    def on_request(request):
        host = urlparse(request.url).hostname or ""
        if host and not same_site(host, site):
            result["third_parties"][host] = result["third_parties"].get(host, 0) + 1
        if not typing_started["flag"]:
            return
        try:
            body = request.post_data or ""
        except Exception:
            body = ""
        haystack = (request.url + "\n" + body).lower()
        for name, value in variants.items():
            if value.lower() in haystack:
                result["leaks"].append({
                    "host": host,
                    "disguise": name,
                    "method": request.method,
                    "request_url": request.url,
                    "third_party": not same_site(host, site),
                })
                break  # one match per request is enough

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH"))
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.on("request", on_request)
            page.goto(url, wait_until="load", timeout=45000)
            page.wait_for_timeout(3000)

            box = page.locator(EMAIL_SELECTOR).first
            if box.count() == 0:
                browser.close()
                return result
            result["found_email_box"] = True

            typing_started["flag"] = True
            box.click()
            box.press_sequentially(canary, delay=60)
            page.keyboard.press("Tab")
            page.wait_for_timeout(8000)  # never submit; just watch

            page.screenshot(path=screenshot_path)
            result["screenshot"] = screenshot_path
            browser.close()
    except Exception as e:
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    out = run_scan(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(out))
    else:
        print(f"\nCanary email: {out['canary']}  (typed, never submitted)  at {out['time']}\n")
        if out["error"]:
            print("Error:", out["error"])
        elif not out["found_email_box"]:
            print("No email field found on this page.")
        elif not out["leaks"]:
            print("✅ No leak seen.")
        else:
            print("❌ LEAK before submit:")
            for l in out["leaks"]:
                print(f"  → {l['host']} as {l['disguise']} ({l['method']})")
