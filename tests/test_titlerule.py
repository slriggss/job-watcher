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



# ---- compliance and risk analysts ---------------------------------------------------------------------------
def test_compliance_and_risk_analysts_are_in_role():
    for title in ("Senior Compliance Analyst", "Risk Analyst II", "Analyst, Investment Compliance",
                  "Operational Risk Analyst", "Analyst, Global Compliance Regulatory Change"):
        assert in_role(title), title


def test_other_compliance_and_risk_titles_are_not_widened_into_the_role():
    for title in ("Compliance Manager", "Chief Risk Officer", "Senior Risk Manager", "Equity Analyst"):
        assert not in_role(title), title


def test_environmental_health_still_excludes_a_risk_analyst():
    assert not in_role("EHS Risk Analyst")


def test_a_risk_analyst_at_an_asset_manager_is_not_asset_manager_esg():
    from jobwatcher.titlerule import esg_via
    assert esg_via("Senior Compliance Analyst", "asset manager") == ""
    assert esg_via("Stewardship Analyst", "asset manager") == "title"


# ---- engagement and policy ----------------------------------------------------------------------------------
def test_engagement_and_policy_titles_are_in_role():
    for title in ("Senior Policy Analyst", "Policy & Communications Lead", "Public Policy Director",
                  "Issuer Engagement Specialist", "ESG Engagement Associate", "Shareholder Engagement Manager"):
        assert in_role(title), title


def test_client_engagement_and_policy_administration_are_not():
    for title in ("VP, Aladdin Client Engagement", "Customer Engagement Associate", "Employee Engagement Partner",
                  "Field Engagement Coordinator", "Insurance Policy Administration Specialist", "Policy Servicing Associate",
                  "Engagement Manager, Professional Services", "Consumer Acquisition & Engagement", "Credit Policy Analyst",
                  "Technical Accounting Policy Manager", "Engagement Letter Lawyer", "Cyber Policy Enforcement Lead"):
        assert not in_role(title), title


def test_adding_engagement_and_policy_does_not_make_them_asset_manager_esg_by_title():
    from jobwatcher.titlerule import esg_via
    assert esg_via("Senior Policy Analyst", "asset manager") == ""
