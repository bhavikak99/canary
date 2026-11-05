# Run Canary on every URL in sites.txt (3 at a time) and save the results.
# Usage: python batch_scan.py            (uses sites.txt)
#        python batch_scan.py mylist.txt
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKERS = 3  # how many sites to test at the same time

list_file = sys.argv[1] if len(sys.argv) > 1 else "sites.txt"
urls = [line.strip() for line in open(list_file) if line.strip() and not line.strip().startswith("#")]


def scan_one(url):
    try:
        # Each site runs as its own program, so one broken site can't crash the whole batch.
        proc = subprocess.run([sys.executable, "canary_scan.py", url, "--json"],
                              capture_output=True, text=True, timeout=150)
        line = [l for l in proc.stdout.splitlines() if l.startswith("RESULT:")][-1]
        r = json.loads(line[len("RESULT:"):])
    except Exception as e:
        r = {"url": url, "error": f"scan failed: {e}", "leaks": [], "third_parties": {},
             "found_email_box": False, "canary": None, "time": None}
    outside = [l for l in r["leaks"] if l.get("third_party")]
    if r.get("error"):
        r["status"] = "error"
    elif not r["found_email_box"]:
        r["status"] = "no email box"
    elif outside:
        r["status"] = "LEAK"
    else:
        r["status"] = "clean"
    r["leaked_to"] = sorted({l["host"] for l in outside})
    r["leaked_companies"] = sorted({l.get("company", l["host"]) for l in outside})
    r["leaked_fields"] = sorted({l.get("field", "email") for l in outside})
    return r


results, done = [], 0
print(f"Testing {len(urls)} pages, {WORKERS} at a time...\n")
with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    futures = {pool.submit(scan_one, u): u for u in urls}
    for f in as_completed(futures):
        r = f.result()
        results.append(r)
        done += 1
        extra = f" -> {', '.join(r['leaked_companies'])} got your {', '.join(r['leaked_fields'])}" if r["status"] == "LEAK" else ""
        print(f"[{done}/{len(urls)}] {r['url']} ... {r['status']}{extra}", flush=True)
        # Save after every site, so stopping early (Ctrl+C) still keeps what we have.
        order = {u: i for i, u in enumerate(urls)}
        with open("batch_results.json", "w") as fh:
            json.dump(sorted(results, key=lambda x: order.get(x["url"], 0)), fh, indent=2)

tested = [r for r in results if r["status"] in ("LEAK", "clean")]
leaked = [r for r in results if r["status"] == "LEAK"]
print(f"\nTested {len(tested)} pages with an email box. {len(leaked)} leaked something before submit.")
for r in leaked:
    print(f"  LEAK {r['url']} -> {', '.join(r['leaked_companies'])} ({', '.join(r['leaked_fields'])})")
print("Saved to batch_results.json")
