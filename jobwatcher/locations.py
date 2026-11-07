"""Turn the many spellings of a job location into one comparable place.

normalize_location("New York, New York, United States of America") -> ("New York, NY", False)
US places become "City, ST"; other places "City, Country"; "Remote, US" for remote-only. The original text is
always kept in the `location` column; this only feeds the `location_norm` and `remote` columns."""
import re

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
STATE_CODES = set(US_STATES.values())
COUNTRIES = {"us": "US", "usa": "US", "u.s.": "US", "united states": "US", "united states of america": "US",
             "uk": "UK", "gb": "UK", "united kingdom": "UK", "great britain": "UK", "england": "UK",
             "br": "Brazil", "brasil": "Brazil", "ca": None}  # "CA" is California, never Canada
COUNTRY_NAMES = {"india", "japan", "china", "canada", "ireland", "singapore", "philippines", "brazil", "spain",
                 "luxembourg", "germany", "france", "australia", "hong kong", "switzerland", "netherlands",
                 "poland", "mexico", "italy", "korea", "south korea", "taiwan", "israel", "uae"}
# A bare city name that is unambiguous enough to complete.
BARE_CITIES = {"new york": "New York, NY", "new york city": "New York, NY", "nyc": "New York, NY",
               "chicago": "Chicago, IL", "boston": "Boston, MA", "san francisco": "San Francisco, CA",
               "seattle": "Seattle, WA", "atlanta": "Atlanta, GA", "denver": "Denver, CO",
               "london": "London, UK", "dublin": "Dublin, Ireland", "mumbai": "Mumbai, India",
               "singapore": "Singapore", "hong kong": "Hong Kong", "toronto": "Toronto, Canada",
               "tokyo": "Tokyo, Japan", "pune": "Pune, India", "bangalore": "Bangalore, India",
               "hyderabad": "Hyderabad, India"}
MULTI = re.compile(r"^\d+ locations?$", re.I)
REMOTE = re.compile(r"\bremote\b|\bvirtual\b|work from home", re.I)
PAREN = re.compile(r"\([^)]*\)")


def _country(token):
    t = token.strip().lower().rstrip(".")
    if t in COUNTRIES:
        return COUNTRIES[t]
    if t in COUNTRY_NAMES:
        return token.strip().title() if t not in ("uae",) else "UAE"
    return None


def _state(token):
    t = token.strip()
    if t.upper() in STATE_CODES and (len(t) == 2):
        return t.upper()
    return US_STATES.get(t.lower())


def _single(text):
    """One location (no list) -> normalized place, or ''."""
    t = PAREN.sub("", text).replace("�", "ã" if "S�o" in text else "")
    t = re.sub(r"^(?:US|USA)\s*-\s*", "", t.strip(), flags=re.I)             # "US-Chicago"
    m = re.match(r"^([A-Z]{2})\s*-\s*(.+)$", t)                               # "CA - San Francisco"
    if m and m.group(1) in STATE_CODES:
        t = f"{m.group(2).title()}, {m.group(1)}"
    t = re.split(r"\s+-\s+", t)[0] if "," in t.split(" - ")[0] else t         # "New York, NY - 375 Park Avenue"
    t = t.strip(" ;,")
    parts = [p.strip() for p in t.split(",") if p.strip()]
    if parts and parts[-1].lower() in ("us", "usa", "united states", "united states of america", "u.s."):
        parts = parts[:-1]
        us = True
    else:
        us = False
    if not parts:
        return ""
    if len(parts) == 1:
        p = parts[0]
        for name, code in US_STATES.items():  # "Burlington Massachusetts"
            if p.lower().endswith(" " + name) and len(p) > len(name) + 1:
                return f"{p[:-len(name)].strip()}, {code}"
        return BARE_CITIES.get(p.lower(), p if not _state(p) else "")
    if len(parts) >= 3:  # "5335 Ballantyne Commons Pkwy, Charlotte, NC": keep the last two
        parts = parts[-2:]
    city, second = parts
    city_l = city.lower()
    st = _state(second)
    if st and (us or second.upper() == st or second.lower() in US_STATES):
        return f"{BARE_CITIES[city_l].split(',')[0] if city_l in ('new york city', 'nyc') else city}, {st}"
    country = _country(second)
    if country == "US":
        return BARE_CITIES.get(city_l, city)
    if country:
        return city if city.lower() == country.lower() else f"{city}, {country}"
    if second.lower() == city_l:
        return city
    return f"{city}, {second}"


def normalize_location(text):
    """Return (place, remote). place is '' when the text names no single place ("2 Locations", a bare "Remote")."""
    t = " ".join((text or "").split())
    if not t or MULTI.match(t):
        return "", False
    remote = bool(REMOTE.search(t))
    segments = [s.strip() for s in t.split(";") if s.strip()]
    if len(segments) == 1:
        parts = [p.strip() for p in segments[0].split(",")]
        # a list of cities has no 2-letter state code and no country in it ("New York" here is a city)
        if len(parts) >= 3 and not any(p.upper() in STATE_CODES or _country(p) for p in parts):
            segments = parts  # "San Francisco, Seattle, New York": a list of cities, not City, State
    first = segments[0] if segments else t
    if REMOTE.search(first):
        rest = REMOTE.sub(" ", first)
        us = bool(re.search(r"(?i)\b(?:us|usa)\b", first))
        rest = re.sub(r"(?i)\b(?:us|usa)\b", " ", rest)
        rest = [w for w in re.sub(r"[-–,/]", " ", rest).split() if w.isalpha()]
        country = "US" if us and not rest else (_country(" ".join(rest)) if rest else None)
        return (f"Remote, {country}" if country else ("Remote, " + " ".join(rest).title() if rest else "Remote")), True
    return _single(first), remote


def country_of(place):
    """The country of a normalized place: "US", a country name, or "" when it cannot be told ("Remote" alone, an
    unresolved string). "Hyderabad, Telangana" gives "Telangana": outside the US, country not named."""
    if not place or place == "Remote":
        return ""
    if "," not in place:
        return place if place in ("Singapore", "Hong Kong") else ""
    last = place.rsplit(",", 1)[1].strip()
    return "US" if last in STATE_CODES or last == "US" else last


def all_places(text):
    """Every distinct place named in a location string that lists several (separated by ';')."""
    out = []
    for seg in (text or "").split(";"):
        place, _ = normalize_location(seg)
        if place and place not in out:
            out.append(place)
    return out
