# Run Canary on every URL in sites.txt and save the results.
# Usage: python batch_scan.py            (uses sites.txt)
#        python batch_scan.py mylist.txt
import json
import subprocess
import sys

list_file = sys.argv[1] if len(sys.argv) > 1 else "sites.txt"
urls = [line.strip() for line in open(list_file)
        if line.strip() and not line.strip().startswith("#")]

results = []
for i, url in enumerate(urls, 1):
    print(f"[{i}/{len(urls)}] {url} ... ", end="", flush=True)
    try:
        # Each site runs as its own process, so one broken site can't crash the whole batch.
        proc = subprocess.run([sys.executable, "canary_scan.py", url, "--json"],
                              capture_output=True, text=True, timeout=90)
        r = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception as e:
        r = {"url": url, "error": f"scan failed: {e}", "leaks": [], "third_parties": {},
             "found_email_box": False, "canary": None, "time": None}

    outside = [l for l in r["leaks"] if l.get("third_party")]
    if r.get("error"):
        status = "error"
    elif not r["found_email_box"]:
        status = "no email box"
    elif outside:
        status = "LEAK"
    else:
        status = "clean"
    r["status"] = status
    r["leaked_to"] = sorted({l["host"] for l in outside})
    r.pop("screenshot", None)
    results.append(r)
    print(status + (f" -> {', '.join(r['leaked_to'])}" if outside else ""))

    # Save after every site, so stopping early (Ctrl+C) still keeps what we have.
    with open("batch_results.json", "w") as f:
        json.dump(results, f, indent=2)

tested = [r for r in results if r["status"] in ("LEAK", "clean")]
leaked = [r for r in results if r["status"] == "LEAK"]
print(f"\nTested {len(tested)} pages with an email box. {len(leaked)} leaked the email before submit.")
for r in leaked:
    print(f"  ❌ {r['url']} -> {', '.join(r['leaked_to'])}")
print("Saved to batch_results.json")
