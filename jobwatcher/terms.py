"""Count ESG terms in posting text. Shared by enrich.py (which fetches the text) and build.py (which scans the
saved text), so the history can be rebuilt from the raw files and a change to the term list reaches every posting."""
import html
import re

# Terms that, in the body of a posting, point at ESG / stewardship / sustainable-finance work.
STRONG = re.compile(
    r"\b(esg|environmental,? social|stewardship|proxy voting|responsible invest\w*|sustainab\w* invest\w*|"
    r"impact invest\w*|climate (?:risk|change|transition)|net[- ]zero|tcfd|sfdr|issb|csrd|greenwash\w*|"
    r"corporate governance|sustainable finance|sustainability[- ]linked)\b", re.I)
TAGS = re.compile(r"<[^>]+>")


def plain_text(description_html):
    return html.unescape(TAGS.sub(" ", description_html or ""))


def scan(text):
    """Return (number of strong-term mentions, 'term:count;...' for the distinct terms, most frequent first)."""
    hits = [m.group(1).lower() for m in STRONG.finditer(text or "")]
    counts = {}
    for h in hits:
        counts[h] = counts.get(h, 0) + 1
    terms = ";".join(f"{k}:{v}" for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return len(hits), terms
