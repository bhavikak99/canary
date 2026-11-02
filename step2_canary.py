# Step 2: type a fake "canary" email into a page's form, DON'T submit,
# and check whether that email (or a disguised version of it) leaves the page.
import base64
import hashlib
import os
import sys
import uuid
from urllib.parse import quote, urlparse
from playwright.sync_api import sync_playwright

url = sys.argv[1]

# 1. Make a one-of-a-kind fake email. It exists nowhere else on earth,
#    so if we see it in traffic, it came from us.
canary = f"canary-{uuid.uuid4().hex[:8]}@example.com"

# 2. All the "disguises" the email might be wearing when it's sent.
#    Trackers often hash emails (scramble them) - same email = same hash,
#    so a hash still identifies you.
variants = {
    "plain text": canary,
    "URL-encoded": quote(canary, safe=""),
    "base64": base64.b64encode(canary.encode()).decode(),
    "MD5 hash": hashlib.md5(canary.encode()).hexdigest(),
    "SHA-1 hash": hashlib.sha1(canary.encode()).hexdigest(),
    "SHA-256 hash": hashlib.sha256(canary.encode()).hexdigest(),
}

leaks = []

def on_request(request):
    # Look everywhere a request can carry data: the URL, and the body.
    try:
        body = request.post_data or ""
    except Exception:
        body = ""  # some bodies are binary; skip those for now
    haystack = request.url + "\n" + body
    for name, value in variants.items():
        if value.lower() in haystack.lower():
            leaks.append((urlparse(request.url).hostname, name, request.method, request.url[:120]))

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH"))
    page = browser.new_page()
    page.on("request", on_request)
    page.goto(url, wait_until="load", timeout=45000)
    page.wait_for_timeout(3000)

    # 3. Find an email box on the page.
    email_box = page.locator(
        "input[type=email], input[name*=email i], input[id*=email i], input[autocomplete=email]"
    ).first
    if email_box.count() == 0:
        print("No email field found on this page. Try a signup/registration/checkout page.")
        browser.close()
        sys.exit()

    # 4. Type it like a human (one key at a time), then click away.
    #    Many trackers grab the value when you leave the field ("blur").
    email_box.click()
    email_box.press_sequentially(canary, delay=60)
    page.keyboard.press("Tab")

    # 5. DO NOT SUBMIT. Just wait and watch.
    page.wait_for_timeout(8000)
    browser.close()

print(f"\nCanary email: {canary}  (typed, never submitted)\n")
if not leaks:
    print("✅ No leak seen. The email didn't leave the page before submit.")
else:
    print("❌ LEAK: the email left the page before you hit submit:\n")
    for host, disguise, method, short_url in leaks:
        print(f"  → {host}  as {disguise}  ({method})")
        print(f"     {short_url}")