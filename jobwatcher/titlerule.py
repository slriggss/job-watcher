"""The title rules.

in_role      - ESG / sustainability analyst work, at any employer.
am_esg       - the same work at an investment management firm, using a broader rule: titles that imply
               stewardship or governance work without naming ESG (a bare "Governance Analyst", "Proxy Analyst",
               "Issuer Engagement"). Everything in_role at an asset manager is also am_esg.
"""
import re

# A title is in role when it contains one of these terms...
INCLUDE = re.compile(
    r"\b(esg|sustainab\w*|stewardship|climate|decarboni[sz]ation|net[- ]zero|carbon|"
    r"responsible invest\w*|impact invest\w*|proxy (?:voting|research|advis\w*|analyst\w*)|corporate responsibility|"
    r"corporate governance|environmental|social impact|ethics|energy transition)\b"
)
# ...unless it is a different kind of work that happens to share a word.
EXCLUDE = re.compile(r"\b(data governance|model governance|environmental health|ehs)\b")

# At an asset manager, these also count: governance and engagement words that normally mean stewardship work there.
AM_INCLUDE = re.compile(
    r"\b(proxy|(?:issuer|shareholder|investor|company|corporate|active|esg) engagement|"
    r"engagement (?:analyst|specialist|associate)|responsible)\b"
)
# ...but not web proxies or client / employee "engagement". A bare "governance" is deliberately NOT included:
# at asset managers it almost always means IT, data, operations or fund-board governance, not stewardship.
AM_EXCLUDE = re.compile(
    r"\b(proxy (?:server|engineer|security)|web proxy|"
    r"(?:client|customer|employee|talent|community|donor|candidate|member|user) engagement)\b"
)


def in_role(title: str) -> bool:
    t = (title or "").lower()
    return bool(INCLUDE.search(t)) and not EXCLUDE.search(t)


# Risk and compliance teams: their titles say nothing about ESG, so only the posting text can qualify them.
RISK_TITLE = re.compile(r"\b(risk|compliance|regulat\w+|legal|counsel|audit|controls?|oversight|conduct|policy|ethics)\b")
TEXT_STRONG = 3    # this many ESG-term mentions in the text qualify any role at an asset manager...
TEXT_RISK = 2      # ...and this many qualify a risk or compliance role (1 is too loose: "data stewardship").


def esg_via(title: str, employer_type: str, strong: int = 0) -> str:
    """Why a posting counts as asset-manager ESG: "title", "text", "risk/compliance text", or "" if it does not.

    strong is the number of ESG-term mentions found in the posting text (see enrich.py); 0 when not fetched."""
    if employer_type != "asset manager":
        return ""
    t = (title or "").lower()
    if in_role(title) or (AM_INCLUDE.search(t) and not AM_EXCLUDE.search(t) and not EXCLUDE.search(t)):
        return "title"
    if strong >= TEXT_STRONG:
        return "text"
    if strong >= TEXT_RISK and RISK_TITLE.search(t):
        return "risk/compliance text"
    return ""


def am_esg(title: str, employer_type: str, strong: int = 0) -> bool:
    return bool(esg_via(title, employer_type, strong))
