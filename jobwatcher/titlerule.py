"""The title rule: decides whether a posting is in role (ESG / sustainability analyst work)."""
import re

# A title is in role when it contains one of these terms...
INCLUDE = re.compile(
    r"\b(esg|sustainab\w*|stewardship|climate|decarboni[sz]ation|net[- ]zero|carbon|"
    r"responsible invest\w*|impact invest\w*|proxy (?:voting|research|advis\w*|analyst\w*)|corporate responsibility|"
    r"corporate governance|environmental|social impact|ethics|energy transition)\b"
)
# ...unless it is a different kind of work that happens to share a word.
EXCLUDE = re.compile(r"\b(data governance|model governance|environmental health|ehs)\b")


def in_role(title: str) -> bool:
    t = (title or "").lower()
    return bool(INCLUDE.search(t)) and not EXCLUDE.search(t)
