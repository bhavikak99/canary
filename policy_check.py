# Compare what a privacy policy PROMISES with what Canary actually CAUGHT.
# The AI finds relevant quotes; normal code then checks every quote really exists in the policy.
import os
import re
import sys
import json
from typing import List, Literal
import anthropic
from pydantic import BaseModel
from playwright.sync_api import sync_playwright


class PolicyStatement(BaseModel):
    quote: str  # copied word-for-word from the policy
    verdict: Literal["contradicts", "discloses", "unclear"]
    explanation: str  # one plain-English sentence


class PolicyComparison(BaseModel):
    statements: List[PolicyStatement]
    summary: str


def fetch_policy_text(policy_url):
    """Open the policy in a real browser (many policies need JavaScript) and grab the visible text."""
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH"))
        page = browser.new_page()
        page.goto(policy_url, wait_until="load", timeout=45000)
        page.wait_for_timeout(2000)
        text = page.inner_text("body")
        browser.close()
    return text


def normalize(s):
    """Lowercase, straighten quotes, squash whitespace, so tiny formatting differences don't fail the check."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_is_real(quote, policy_text):
    return len(quote) >= 20 and normalize(quote) in normalize(policy_text)


def compare(policy_text, site, leaks, third_parties):
    findings = "\n".join(f"- {l['host']} received the email as a {l['disguise']}, BEFORE the user clicked submit"
                         for l in leaks) or "- No email leak was observed."
    trackers = ", ".join(sorted(third_parties)[:60])

    prompt = f"""We tested {site}. A robot typed a fake email into the form and NEVER clicked submit.
What we actually observed:
{findings}
Other outside servers the page contacted: {trackers}

Below is the site's privacy policy. Find the statements (at most 6) that matter most for what we observed:
promises about sharing personal info / email with advertisers or third parties, statements about tracking
pixels or "enhanced matching", and anything about when data is collected.

Rules:
- "quote" must be copied EXACTLY, word for word, from the policy. No paraphrasing. One or two sentences max.
- verdict "contradicts" = the observed behavior goes against this statement.
  "discloses" = the policy openly admits this kind of sharing.
  "unclear" = related but too vague to judge.
- explanation: one short, plain-English sentence a non-lawyer understands.
- summary: 2 sentences max. Be fair; don't accuse the site of breaking the law.
- If the policy says nothing relevant, return an empty list and say so in the summary.

PRIVACY POLICY:
<policy>
{policy_text}
</policy>"""

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model="claude-opus-5-5",
        max_tokens=16000,
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": prompt}],
        output_format=PolicyComparison,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return {"statements": [], "rejected": [], "summary": "The AI couldn't analyze this policy."}

    result = response.parsed_output
    verified, rejected = [], []
    for s in result.statements:
        (verified if quote_is_real(s.quote, policy_text) else rejected).append(s.model_dump())
    return {"statements": verified, "rejected": rejected, "summary": result.summary}


if __name__ == "__main__":
    # Usage: python policy_check.py <policy_url> <scan_result.json>
    policy_url, scan_file = sys.argv[1], sys.argv[2]
    scan = json.load(open(scan_file))
    text = fetch_policy_text(policy_url)
    outside = [l for l in scan["leaks"] if l.get("third_party")]
    out = compare(text, scan["url"], outside, scan["third_parties"])
    out["policy_url"] = policy_url
    print(json.dumps(out))
