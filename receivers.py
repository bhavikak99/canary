# Who are these servers? Map tracker domains to a company + what they do,
# so results make sense to normal people. Matches the domain or any parent domain.

KNOWN = {
    # Advertising / ad measurement
    "pinterest.com":        ("Pinterest", "Advertising network"),
    "pinimg.com":           ("Pinterest", "Advertising network"),
    "facebook.net":         ("Meta (Facebook)", "Advertising network"),
    "facebook.com":         ("Meta (Facebook)", "Advertising network"),
    "tiktok.com":           ("TikTok", "Advertising network"),
    "tiktokw.us":           ("TikTok", "Advertising network"),
    "doubleclick.net":      ("Google", "Advertising network"),
    "googleadservices.com": ("Google", "Advertising network"),
    "googlesyndication.com":("Google", "Advertising network"),
    "bing.com":             ("Microsoft Bing", "Advertising network"),
    "snapchat.com":         ("Snapchat", "Advertising network"),
    "linkedin.com":         ("LinkedIn", "Advertising network"),
    "licdn.com":            ("LinkedIn", "Advertising network"),
    "twitter.com":          ("X (Twitter)", "Advertising network"),
    "t.co":                 ("X (Twitter)", "Advertising network"),
    "ads-twitter.com":      ("X (Twitter)", "Advertising network"),
    "reddit.com":           ("Reddit", "Advertising network"),
    "redditstatic.com":     ("Reddit", "Advertising network"),
    "spotify.com":          ("Spotify", "Advertising network"),
    "byspotify.com":        ("Spotify", "Advertising network"),
    "rokt.com":             ("Rokt", "E-commerce advertising"),
    "rokt-api.com":         ("Rokt", "E-commerce advertising"),
    "criteo.com":           ("Criteo", "Advertising network"),
    "criteo.net":           ("Criteo", "Advertising network"),
    "taboola.com":          ("Taboola", "Advertising network"),
    "outbrain.com":         ("Outbrain", "Advertising network"),
    "impactcdn.com":        ("Impact.com", "Affiliate marketing"),
    "pxf.io":               ("Impact.com", "Affiliate marketing"),
    "ojrq.net":             ("Impact.com", "Affiliate marketing"),
    # Ad exchanges, ad buying and identity matching (often seen together on ad-heavy sites)
    "adthrive.com":         ("Raptive (AdThrive)", "Advertising network"),
    "raptivecdn.com":       ("Raptive (AdThrive)", "Advertising network"),
    "pubmatic.com":         ("PubMatic", "Ad exchange (real-time ad auctions)"),
    "rubiconproject.com":   ("Magnite", "Ad exchange (real-time ad auctions)"),
    "openx.net":            ("OpenX", "Ad exchange (real-time ad auctions)"),
    "casalemedia.com":      ("Index Exchange", "Ad exchange (real-time ad auctions)"),
    "3lift.com":            ("TripleLift", "Ad exchange (real-time ad auctions)"),
    "adnxs.com":            ("Xandr (Microsoft)", "Ad exchange (real-time ad auctions)"),
    "smartadserver.com":    ("Equativ", "Ad exchange (real-time ad auctions)"),
    "bidswitch.net":        ("BidSwitch", "Ad exchange (real-time ad auctions)"),
    "adsrvr.org":           ("The Trade Desk", "Ad buying platform"),
    "rlcdn.com":            ("LiveRamp", "Identity matching (links you across sites)"),
    "pippio.com":           ("LiveRamp", "Identity matching (links you across sites)"),
    "quantserve.com":       ("Quantcast", "Audience tracking for ads"),
    "quantcount.com":       ("Quantcast", "Audience tracking for ads"),
    "scorecardresearch.com":("Comscore", "Audience measurement"),
    "adara.com":            ("Adara", "Advertising data"),
    "ketchjs.com":          ("Ketch", "Cookie consent tool"),
    "ketchcdn.com":         ("Ketch", "Cookie consent tool"),
    "googleapis.com":       ("Google", "Google services (fonts, login, reCAPTCHA)"),
    "cdn-apple.com":        ("Apple", "Sign in with Apple"),
    # Marketing / sales data
    "bizible.com":          ("Adobe Marketo Measure (Bizible)", "Marketing attribution"),
    "marketo.net":          ("Adobe Marketo", "Marketing automation"),
    "mktoresp.com":         ("Adobe Marketo", "Marketing automation"),
    "hubspot.com":          ("HubSpot", "Marketing automation"),
    "hs-scripts.com":       ("HubSpot", "Marketing automation"),
    "hs-analytics.net":     ("HubSpot", "Marketing automation"),
    "hs-banner.com":        ("HubSpot", "Marketing automation"),
    "hsforms.com":          ("HubSpot", "Marketing automation"),
    "zoominfo.com":         ("ZoomInfo", "Sells business contact data"),
    "zi-scripts.com":       ("ZoomInfo", "Sells business contact data"),
    "6sc.co":               ("6sense", "Visitor identification for sales"),
    "demandbase.com":       ("Demandbase", "Visitor identification for sales"),
    "klaviyo.com":          ("Klaviyo", "Email marketing"),
    "mparticle.com":        ("mParticle", "Customer data platform"),
    "segment.io":           ("Segment", "Customer data platform"),
    "segment.com":          ("Segment", "Customer data platform"),
    "unifyintent.com":      ("Unify (likely)", "Visitor identification for sales"),
    "t.co":                 ("X (Twitter)", "Advertising network"),
    "okt.to":               ("okt.to (unconfirmed, possibly Oktopost)", "Marketing link tracking"),
    # Analytics / session recording / monitoring
    "google-analytics.com": ("Google", "Analytics"),
    "analytics.google.com": ("Google", "Analytics"),
    "googletagmanager.com": ("Google", "Tag manager (loads other trackers)"),
    "heapanalytics.com":    ("Heap", "Product analytics"),
    "contentsquare.net":    ("Contentsquare / Hotjar", "Session recording"),
    "hotjar.com":           ("Hotjar", "Session recording"),
    "fullstory.com":        ("FullStory", "Session recording"),
    "clarity.ms":           ("Microsoft Clarity", "Session recording"),
    "mouseflow.com":        ("Mouseflow", "Session recording"),
    "datadoghq.com":        ("Datadog", "Website monitoring / logging"),
    "browser-intake-datadoghq.com": ("Datadog", "Website monitoring / logging"),
    "browser-intake-datadoghq.eu":  ("Datadog", "Website monitoring / logging"),
    "sentry.io":            ("Sentry", "Error monitoring"),
    "newrelic.com":         ("New Relic", "Website monitoring"),
    "nr-data.net":          ("New Relic", "Website monitoring"),
    "amplitude.com":        ("Amplitude", "Product analytics"),
    "mixpanel.com":         ("Mixpanel", "Product analytics"),
    "google.com":           ("Google", "Google services (fonts, login, reCAPTCHA)"),
    "gstatic.com":          ("Google", "Google services (fonts, login, reCAPTCHA)"),
    # AI
    "openai.com":           ("OpenAI", "Unconfirmed: likely ad measurement"),
}

RISK = {  # how worried a normal person should be if their email goes here
    "Advertising network": "high", "E-commerce advertising": "high", "Affiliate marketing": "high",
    "Sells business contact data": "high", "Visitor identification for sales": "high",
    "Ad exchange (real-time ad auctions)": "high", "Ad buying platform": "high",
    "Identity matching (links you across sites)": "high", "Audience tracking for ads": "high", "Advertising data": "high",
    "Audience measurement": "medium",
    "Marketing attribution": "medium", "Marketing automation": "medium", "Email marketing": "medium",
    "Customer data platform": "medium", "Marketing link tracking": "medium",
    "Session recording": "medium",
}


def identify(host):
    """Return (company, category, risk) for a hostname. Unknown hosts get a neutral label."""
    host = (host or "").lower()
    parts = host.split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in KNOWN:
            company, category = KNOWN[candidate]
            return company, category, RISK.get(category, "low")
    return "Unknown company", "Not in our list yet", "unknown"


# Some sites load files from their own differently-named servers. These aren't outside companies.
OWN_SERVERS = {
    "evbstatic.com": "Eventbrite", "evbuc.com": "Eventbrite",
    "cvent-assets.com": "Cvent", "cvent.net": "Cvent",
}


def identify_any(host):
    """Like identify(), but also recognises a site's own servers."""
    parts = (host or "").lower().split(".")
    for i in range(len(parts) - 1):
        if ".".join(parts[i:]) in OWN_SERVERS:
            return OWN_SERVERS[".".join(parts[i:])], "The site's own servers", "low"
    return identify(host)


# Sites whose name can't be guessed from the web address.
NICE_NAMES = {"lu.ma": "Luma", "theskimm.com": "theSkimm", "dice.fm": "DICE", "my.mlh.io": "MLH", "mlh.io": "MLH",
              "joinhandshake.com": "Handshake", "axs.com": "AXS", "on24.com": "ON24", "edx.org": "edX",
              "leetcode.com": "LeetCode", "github.com": "GitHub", "hubspot.com": "HubSpot", "seatgeek.com": "SeatGeek",
              "stubhub.com": "StubHub", "surveymonkey.com": "SurveyMonkey", "signupgenius.com": "SignUpGenius",
              "tickettailor.com": "Ticket Tailor", "ticketleap.com": "TicketLeap", "ticketspice.com": "TicketSpice",
              "addevent.com": "AddEvent", "paperlesspost.com": "Paperless Post", "morningbrew.com": "Morning Brew",
              "theverge.com": "The Verge", "techcrunch.com": "TechCrunch", "warbyparker.com": "Warby Parker",
              "fashionnova.com": "Fashion Nova", "urbanoutfitters.com": "Urban Outfitters", "opentable.com": "OpenTable",
              "hellofresh.com": "HelloFresh", "awaytravel.com": "Away", "devpost.com": "Devpost",
              "hackerearth.com": "HackerEarth", "dorahacks.io": "DoraHacks", "cognitoforms.com": "Cognito Forms",
              "constantcontact.com": "Constant Contact", "splashthat.com": "Splash", "goldcast.io": "Goldcast"}


def pretty_site(site):
    """www.eventbrite.com -> Eventbrite"""
    s = (site or "").lower()
    for k, v in NICE_NAMES.items():
        if s == k or s.endswith("." + k):
            return v
    parts = (site or "").lower().split(".")
    if all(p.isdigit() for p in parts):  # an IP address like 127.0.0.1
        return site
    name = parts[-2] if len(parts) >= 2 else site
    return name[:1].upper() + name[1:]
