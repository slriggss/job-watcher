"""One place per posting, whatever spelling the board uses."""
import pytest

from jobwatcher.locations import all_places, country_of, normalize_location


@pytest.mark.parametrize("text", [
    "New York, New York, United States of America", "New York, NY", "New York, NY (HQ)", "New York",
    "New York, New York, United States", "New York, NY - 375 Park Avenue", "NYC", "NY - New York City"])
def test_every_new_york_spelling_is_one_place(text):
    assert normalize_location(text) == ("New York, NY", False)


@pytest.mark.parametrize("text,place", [
    ("Boston, Massachusetts", "Boston, MA"), ("Burlington Massachusetts", "Burlington, MA"),
    ("San Francisco, California, United States", "San Francisco, CA"), ("O'Fallon, Missouri", "O'Fallon, MO"),
    ("Purchase, New York, United States of America", "Purchase, NY"), ("CA - San Francisco", "San Francisco, CA"),
    ("5335 Ballantyne Commons Pkwy, Charlotte, NC", "Charlotte, NC"), ("Chicago", "Chicago, IL"),
    ("London", "London, UK"), ("London, United Kingdom", "London, UK"), ("Pune, India", "Pune, India"),
    ("Singapore, Singapore", "Singapore"), ("Hong Kong, Hong Kong", "Hong Kong"), ("Madrid, Spain - Nuveen", "Madrid, Spain")])
def test_places_are_city_plus_state_or_country(text, place):
    assert normalize_location(text) == (place, False)


@pytest.mark.parametrize("text,place", [("Remote - USA", "Remote, US"), ("Remote US", "Remote, US"),
                                        ("US-Remote", "Remote, US"), ("Remote Canada", "Remote, Canada")])
def test_remote_postings_carry_the_flag(text, place):
    assert normalize_location(text) == (place, True)


def test_n_locations_is_not_a_place():
    for text in ("2 Locations", "3 Locations", "10 locations", "", None):
        assert normalize_location(text) == ("", False)


def test_lists_use_the_first_place_and_all_places_lists_them_all():
    assert normalize_location("New York, NY; San Francisco, CA; Seattle, WA") == ("New York, NY", False)
    assert normalize_location("San Francisco, Seattle, New York") == ("San Francisco, CA", False)  # "New York" is a city here
    assert all_places("New York, NY; San Francisco, CA; Seattle, WA") == ["New York, NY", "San Francisco, CA", "Seattle, WA"]
    assert normalize_location("Chicago, Atlanta, US-Remote") == ("Chicago, IL", True)


@pytest.mark.parametrize("place,country", [
    ("New York, NY", "US"), ("Remote, US", "US"), ("London, UK", "UK"), ("Pune, India", "India"),
    ("Remote, Canada", "Canada"), ("Singapore", "Singapore"), ("Hong Kong", "Hong Kong"),
    ("Hyderabad, Telangana", "Telangana"), ("Remote", ""), ("", ""), ("Non Office - United States", "")])
def test_country_of_a_place(place, country):
    assert country_of(place) == country
