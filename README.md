# Canary

**Canary gives a website a fake identity and catches it sending your personal info to other companies before you ever click submit.**

Built for ETHIS *AI for Greater Good* (Personal Data Privacy track).

## The problem

When you type your email into a sign-in or registration form, you assume nothing happens until you press **Submit**. On some sites, tracking scripts grab what you type and send it to other companies right away, often scrambled (hashed) so it *looks* anonymous. But the same email always produces the same hash, so it can still be matched back to you.

Nobody can see this happening. Privacy policies are vague, and the people affected (event attendees, students, anyone signing up for something) have no way to check.

## What we found (tests run Nov 2 to Nov 5, 2026)

We ran Canary on 87 real sign-in, sign-up and newsletter pages. 40 had a form Canary could test automatically. **5 of the 40 sent typed details to an outside company before submit was pressed, and 4 of those 5 were event platforms.** On Cvent, a major conference platform, that included a typed name and phone number in readable text.

| Site | What left the page before submit | Received by | Repeated |
|---|---|---|---|
| Eventbrite (sign-in) | email, SHA-256 hash | Pinterest | every test |
| Cvent (homepage) | email, readable | Adobe Marketo Measure (Bizible), okt.to | every test |
| Cvent (homepage) | **name and phone number, readable** | okt.to | 2 of 2 |
| Hubilo (homepage) | email, readable | HubSpot Forms, Unify (likely) | 2 of 2 |
| Punchbowl (sign-in) | email, SHA-256 hash | Pinterest | 2 of 2 |
| theSkimm (homepage) | email, SHA-256 hash | Pinterest | 3 of 3 |

Luma, Meetup, Universe, Whova, Devfolio, MLH, Substack, Typeform and others showed no pre-submit leak, so Canary doesn't just flag everything. Raw results are in `batch_results.json` and `scans/`.

These are observations from automated tests, not legal conclusions.

## How it works

1. **Plant a fake identity.** Every test gets a one-of-a-kind email (`canary-xxxxxxxx@example.com`), name and phone number (415-555-xxxx, a reserved fictional range). They exist nowhere else, so a match is proof.
2. **Act like a real visitor.** A real Chrome browser (Playwright) opens the page, clicks "Reject all" on cookie banners when it can, finds the form (including behind "Sign up" buttons and inside iframes), and types like a person. It never presses submit.
3. **Watch every request.** Canary records everything the page sends and searches it for each detail, in plain text, URL-encoded, base64, MD5, SHA-1 and SHA-256 form.
4. **Name the receiver.** Server addresses are mapped to companies and categories (advertising, marketing, analytics...).
5. **Check "Reject all".** After declining cookies, Canary lists the ad and marketing companies the page still contacts.
6. **Compare with the privacy policy (AI).** Canary finds the site's privacy policy link. Claude reads the policy and pulls out the exact sentences that relate to what was caught. Normal code then checks every quote word-for-word against the real policy and throws out anything the AI made up.
7. **Help people act.** One-click evidence report (HTML) and a ready-to-send message to the company. Organizers can check every page of an event at once.

## Why this isn't just "ask an AI" or another tracker scanner

- A chatbot can't see a website's network traffic. Canary observes what the page actually does, not what it claims.
- Tracker scanners list which scripts are on a page. Canary proves that **your specific details** left, **before consent**, with evidence anyone can re-check (hash the fake email yourself and compare).

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
playwright install chromium
python server.py            # opens http://localhost:8000
```

Optional, for the privacy-policy check: `export ANTHROPIC_API_KEY=...` before starting the server.

- Test one page from the terminal: `python canary_scan.py https://www.eventbrite.com/signin/`
- Test a whole list (3 at a time): `python batch_scan.py` (reads `sites.txt`)

## Files

| File | What it does |
|---|---|
| `canary_scan.py` | The engine: fake identity, browser automation, leak detection, cookie and privacy-link handling |
| `batch_scan.py` | Runs the engine on many sites and saves `batch_results.json` |
| `receivers.py` | Maps server addresses to company names and categories |
| `policy_check.py` | AI privacy-policy comparison with word-for-word quote verification |
| `report.py` | Evidence report and vendor message |
| `server.py` | Small web server (FastAPI) for the website |
| `static/` | The website (home page and test page) |

Canary never submits a form and only uses fake details.
