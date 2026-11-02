import os
import sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

url = sys.argv[1]
requests_seen = []

def on_request(request):
    requests_seen.append(request)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH"))
    page = browser.new_page()
    page.on("request", on_request)
    page.goto(url, wait_until="load", timeout=45000)
    page.wait_for_timeout(5000)
    browser.close()

page_domain = urlparse(url).hostname
print(f"\n{len(requests_seen)} requests made by {page_domain}\n")

third_party = {}
for r in requests_seen:
    host = urlparse(r.url).hostname or ""
    if page_domain not in host:
        third_party[host] = third_party.get(host, 0) + 1

print("Other companies' servers this page talked to:")
for host, count in sorted(third_party.items(), key=lambda x: -x[1]):
    print(f"  {count:3}  {host}")