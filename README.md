
🐤 Canary
Canary gives a website a fake identity and catches it sending your personal data to other companies before you ever click submit.

Built for ETHIS AI for Greater Good, Personal Data Privacy track.

The problem
When you type your email into a sign-in or registration form, you assume nothing happens until you press Submit. On some sites, hidden tracking scripts grab what you type and send it to ad companies immediately, often scrambled (hashed) so it looks anonymous, even though the same email always produces the same hash and can be matched back to you.

Nobody can see this happening. Privacy policies are written in vague terms, and the people most affected (event attendees, hackathon participants, students signing up for things) have no way to check.

What we found (real test, Nov 2, 2026)
On Eventbrite's sign-in page, Canary typed a fake email and never clicked Sign in. Within seconds, the page sent a SHA-256 hash of that email to Pinterest (ct.pinterest.com). The request was labeled LISTENER_SCRAPE by Pinterest's own tag.

Reproduced 4 times with 4 different fake emails, same result every time.
For comparison, Luma and Meetup sign-in pages showed no pre-submit leak, so Canary doesn't just flag everything.
The same Eventbrite page contacted ~40 outside servers, including TikTok, Meta, Pinterest, Bing, Spotify, ZoomInfo, and session-recording tools.
These are observations from our tests, not legal conclusions.

How it works
Plant a canary. Generate a one-of-a-kind fake email (canary-xxxxxxxx@example.com). It exists nowhere else, so if we see it, it came from our test.
Act like a real visitor. A real Chrome browser (driven by Playwright) opens the page, finds the email box, types the email key by key, and clicks away. It never submits.
Watch everything the page sends. Every network request is recorded: URLs and request bodies.
Search for the canary, including disguises. We search for the plain email plus its URL-encoded, base64, MD5, SHA-1, and SHA-256 versions. Trackers often hash emails; hashing doesn't make them anonymous.
Show the proof. The exact request, which company received it, in what disguise, and a screenshot proving submit was never clicked.
Why this isn't just "ask an AI" or another tracker scanner
A chatbot can't see a website's network traffic. Canary observes what the page actually does, not what it claims.
Tracker scanners list which scripts are on a page. Canary proves your specific data left, before consent, with evidence anyone can re-verify (re-hash the fake email yourself and compare).
In progress: promises vs. reality (AI)
policy_check.py reads the site's privacy policy and asks Claude to pull out the exact statements relevant to what we caught: does the policy contradict it, disclose it, or stay vague? Normal code then verifies every quote word-for-word against the real policy and throws out anything the AI made up. The code is written, and live testing is pending API credits.

Who it's for & where it goes next
Event & hackathon organizers checking a registration page or tool before sending it to hundreds of attendees. One check protects everyone who signs up.
Next: test "Reject all" cookie choices (does the site keep tracking after you say no?), re-test after a vendor claims a fix to prove it changed, and a shareable evidence report organizers can send to vendors.
Run it
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
playwright install chromium
python -m streamlit run app.py
Command-line version: python canary_scan.py https://www.eventbrite.com/signin/

Fake emails use @example.com, a domain reserved for testing, so no real person is ever emailed. Canary never submits forms.

