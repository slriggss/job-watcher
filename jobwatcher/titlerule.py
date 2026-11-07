"""The title rules.

in_role      - ESG / sustainability analyst work, compliance and risk analyst work, and engagement and policy
               work, at any employer.
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


# Compliance and risk analyst roles are also in role: the title needs `compliance` or `risk` together with `analyst`.
RISK_OR_COMPLIANCE = re.compile(r"\b(compliance|risk)\b")
ANALYST = re.compile(r"\banalyst\w*\b")


def esg_role(title: str) -> bool:
    """ESG / sustainability / stewardship work by title alone (the first group in the README's title rule)."""
    t = (title or "").lower()
    return bool(INCLUDE.search(t)) and not EXCLUDE.search(t)


# Engagement and policy roles are in role too, but a bare "engagement" is mostly client or consulting work, so it
# counts only with a stewardship word beside it (issuer, shareholder, investor, company, ESG, stakeholder...). Policy
# counts unless it is accounting, credit, cyber or insurance policy, or a legal role.
ADJACENT_INCLUDE = re.compile(
    r"\b((?:issuer|shareholder|investor|investee|company|corporate|esg|stakeholder|stewardship|climate|sustainability|"
    r"proxy|active) engagement|"
    r"policy)\b")
ADJACENT_EXCLUDE = re.compile(
    r"\b((?:accounting|technical accounting|credit|cyber|cybersecurity|security|lending|underwriting|pricing|fraud|"
    r"model|insurance) policy|policy (?:enforcement|administration|admin|servicing|operations|issuance|underwriting)|"
    r"policyholder|accounting|counsel|lawyer|attorney|intern|legal)\b")


def in_role(title: str) -> bool:
    t = (title or "").lower()
    if EXCLUDE.search(t):
        return False
    return (bool(INCLUDE.search(t)) or bool(RISK_OR_COMPLIANCE.search(t) and ANALYST.search(t))
            or bool(ADJACENT_INCLUDE.search(t) and not ADJACENT_EXCLUDE.search(t)))


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
    if esg_role(title) or (AM_INCLUDE.search(t) and not AM_EXCLUDE.search(t) and not EXCLUDE.search(t)):
        return "title"
    if strong >= TEXT_STRONG:
        return "text"
    if strong >= TEXT_RISK and RISK_TITLE.search(t):
        return "risk/compliance text"
    return ""


def am_esg(title: str, employer_type: str, strong: int = 0) -> bool:
    return bool(esg_via(title, employer_type, strong))

