import pytest

from jobwatcher.titlerule import in_role


@pytest.mark.parametrize("title", [
    "Senior ESG Analyst",
    "Sustainability data advisor",
    "Global Stewardship Team, Vice President",
    "Calvert Engagement and Proxy Voting - Associate",
    "Climate Risk Analyst",
    "Manager, Corporate Governance",
    "Net-Zero Strategy Lead",
    "Responsible Investing Specialist",
])
def test_in_role(title):
    assert in_role(title)


@pytest.mark.parametrize("title", [
    "Software Engineer II, Backend",
    "Lead Web Proxy & AI Security Engineer",
    "Data Governance Analyst",
    "Environmental Health and Safety Coordinator",
    "Registered Wealth Service Associate",
    "",
    None,
])
def test_not_in_role(title):
    assert not in_role(title)


def test_case_and_word_boundaries():
    assert in_role("esg analyst")
    assert not in_role("Resg Operations")  # a word boundary, not a substring, is required
