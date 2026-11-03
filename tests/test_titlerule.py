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


from jobwatcher.titlerule import am_esg


@pytest.mark.parametrize("title", [
    "Proxy Analyst",
    "Proxy Operations Associate",
    "Senior Associate, Issuer Engagement",
    "Shareholder Engagement Specialist",
    "Vice President, Corporate Governance",   # already in role: also counts here
    "Climate Solutions Strategist",
])
def test_am_esg_at_an_asset_manager(title):
    assert am_esg(title, "asset manager")


@pytest.mark.parametrize("title", [
    "Governance Analyst",                      # bare governance is IT/ops/fund-board work at asset managers
    "Senior Manager, Distribution Governance",
    "Senior IT Project Manager - Delivery and Governance",
    "Data Governance Lead",
    "Web Proxy Engineer",
    "Client Engagement Specialist",
    "Employee Engagement Manager",
    "Software Engineer",
    "",
    None,
])
def test_not_am_esg_at_an_asset_manager(title):
    assert not am_esg(title, "asset manager")


def test_am_esg_only_applies_to_asset_managers():
    assert not am_esg("Proxy Analyst", "bank")
    assert not am_esg("Proxy Analyst", "fintech")
    assert am_esg("Senior ESG Analyst", "asset manager")
    assert not am_esg("Senior ESG Analyst", "fintech")
