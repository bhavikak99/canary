# Canary website server.
# Run with:  python server.py      then open http://localhost:8000
#
# The page (static/index.html) talks to these small "API" addresses.
# The scanning itself is still done by canary_scan.py, exactly like before.
import glob
import json
import os
import subprocess
import sys
import webbrowser
from threading import Timer

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from receivers import identify_any, pretty_site
from report import evidence_html, vendor_message

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)  # so scans/ and batch_results.json are always found
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Known privacy-policy pages, so the AI check works with one click for our main examples.
POLICIES = {
    "www.eventbrite.com": "https://www.eventbrite.com/help/en-us/articles/460838/eventbrite-privacy-policy/",
    "www.cvent.com": "https://www.cvent.com/en/privacy-policy",
}


def scan_path(name):
    """Turn a scan id into its file path, refusing anything outside scans/."""
    path = os.path.join("scans", os.path.basename(name) + ".json")
    if not os.path.exists(path):
        raise HTTPException(404, "scan not found")
    return path


def enrich(r):
    """Add the extra info the page needs: nice names, grouped servers, history."""
    r = dict(r)
    r["id"] = os.path.splitext(os.path.basename(r.get("saved_as", "")))[0]
    r["site_name"] = pretty_site(r.get("site", ""))
    groups = {}
    for host in r.get("third_parties", {}):
        company, category, risk = identify_any(host)
        g = groups.setdefault(category, {"category": category, "risk": risk, "companies": set()})
        g["companies"].add(company if company != "Unknown company" else host)
    order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    r["breakdown"] = sorted(
        [{"category": g["category"], "risk": g["risk"], "companies": sorted(g["companies"])} for g in groups.values()],
        key=lambda g: (order.get(g["risk"], 9), g["category"]))
    hist = []
    for p in glob.glob("scans/*.json"):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if d.get("url") == r.get("url") and d.get("found_email_box"):
            hist.append({"time": d["time"],
                         "leaked": any(l.get("third_party") for l in d.get("leaks", []))})
    r["history"] = sorted(hist, key=lambda h: h["time"])
    ar = []
    for host in r.get("after_reject", {}):
        company, category, risk = identify_any(host)
        if risk in ("high", "medium"):
            ar.append({"host": host, "company": company, "category": category, "risk": risk})
    seen_c = set()
    r["after_reject_ads"] = [a for a in ar if not (a["company"] in seen_c or seen_c.add(a["company"]))]
    r["has_screenshot"] = bool(r.get("screenshot") and os.path.exists(r["screenshot"]))
    return r


@app.get("/", response_class=HTMLResponse)
def home():
    return open("static/index.html", encoding="utf-8").read()


@app.get("/test", response_class=HTMLResponse)
def test_page():
    return open("static/test.html", encoding="utf-8").read()


@app.get("/api/config")
def config():
    return {"ai_available": bool(os.environ.get("ANTHROPIC_API_KEY")), "policies": POLICIES}


@app.get("/api/scan")
def scan(url: str):
    """Run a scan and stream its progress to the page, line by line, as it happens."""
    def events():
        proc = subprocess.Popen([sys.executable, "canary_scan.py", url, "--json", "--live"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        got_result = False
        for line in proc.stdout:
            line = line.rstrip()
            if line.startswith("PROGRESS:"):
                yield f"event: progress\ndata: {json.dumps(line[9:])}\n\n"
            elif line.startswith("RESULT:"):
                got_result = True
                yield f"event: result\ndata: {json.dumps(enrich(json.loads(line[7:])))}\n\n"
        proc.wait()
        if not got_result:
            yield f"event: failed\ndata: {json.dumps(proc.stderr.read()[-800:])}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream")


class PolicyRequest(BaseModel):
    id: str
    policy_url: str = ""


@app.post("/api/policy")
def policy(req: PolicyRequest):
    """Run the AI privacy-policy check for a saved scan and store the answer in it."""
    path = scan_path(req.id)
    saved = json.load(open(path))
    # Use the link the person typed, else one we know, else the one Canary found on the page itself.
    policy_url = req.policy_url.strip() or POLICIES.get(saved.get("site", "")) or saved.get("policy_url_found") or ""
    if not policy_url:
        raise HTTPException(400, "We couldn't find a privacy policy link on this page.")
    req.policy_url = policy_url
    proc = subprocess.run([sys.executable, "policy_check.py", req.policy_url, path],
                          capture_output=True, text=True, timeout=300)
    try:
        pc = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        raise HTTPException(500, proc.stderr[-800:] or "policy check failed")
    r = json.load(open(path))
    r["policy"], r["policy_url"] = pc, req.policy_url
    json.dump(r, open(path, "w"), indent=2)
    return enrich(r)


@app.get("/api/scans")
def list_scans():
    out = []
    for p in sorted(glob.glob("scans/*.json"), reverse=True):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        out.append({"id": os.path.splitext(os.path.basename(p))[0], "site_name": pretty_site(d.get("site", "")),
                    "url": d.get("url"), "time": d.get("time"), "found_email_box": d.get("found_email_box"),
                    "leaks": len({l["host"] for l in d.get("leaks", []) if l.get("third_party")}),
                    "has_policy": bool(d.get("policy"))})
    return out


@app.get("/api/scans/{name}")
def get_scan(name: str):
    return enrich(json.load(open(scan_path(name))))


@app.get("/api/scans/{name}/screenshot")
def screenshot(name: str):
    r = json.load(open(scan_path(name)))
    if not r.get("screenshot") or not os.path.exists(r["screenshot"]):
        raise HTTPException(404)
    return FileResponse(r["screenshot"])


@app.get("/api/scans/{name}/report")
def report(name: str):
    r = json.load(open(scan_path(name)))
    return HTMLResponse(evidence_html(r), headers={
        "Content-Disposition": f'attachment; filename="canary-report-{r["site"]}.html"'})


@app.get("/api/scans/{name}/message")
def message(name: str):
    r = json.load(open(scan_path(name)))
    return PlainTextResponse(vendor_message(r))


@app.get("/api/findings")
def findings():
    if not os.path.exists("batch_results.json"):
        return {"results": []}
    results = json.load(open("batch_results.json"))
    for r in results:
        r["site_name"] = pretty_site(r.get("site") or (r["url"].split("/")[2] if "//" in r["url"] else r["url"]))
        r["companies"] = sorted({(l.get("company") or l["host"]) for l in r.get("leaks", []) if l.get("third_party")})
        r["fields"] = sorted({l.get("field", "email") for l in r.get("leaks", []) if l.get("third_party")})
        r.pop("third_parties", None)
    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    if "--no-browser" not in sys.argv:
        Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    print(f"\nCanary is running at http://localhost:{port}  (press Ctrl+C to stop)\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
