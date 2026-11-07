"""The site's files agree with each other: a missing file in the service worker's list would stop it installing,
and one stale ?v= would serve old code next to new."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "browse.html", "market.html"]
sw = (ROOT / "sw.js").read_text(encoding="utf-8")
CACHE_VERSION = re.search(r'const CACHE = "job-watcher-v(\d+)"', sw).group(1)
SHELL = re.search(r"const SHELL = \[(.*?)\];", sw, re.S).group(1)
SHELL_FILES = re.findall(r'"([^"]+)"', SHELL)


def test_every_file_the_service_worker_caches_exists():
    for f in SHELL_FILES:
        name = f.split("?")[0]
        assert name == "./" or (ROOT / name).exists(), f


def test_every_script_and_stylesheet_a_page_loads_is_cached_at_the_current_version():
    for page in PAGES:
        html = (ROOT / page).read_text(encoding="utf-8")
        for ref in re.findall(r'(?:src|href)="([^"]+\.(?:js|css)\?v=\d+)"', html):
            assert ref.endswith("?v=" + CACHE_VERSION), (page, ref)  # one version everywhere
            assert ref in SHELL_FILES, (page, ref)


def test_manifest_icons_and_shortcuts_exist():
    manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["id"] and any(i.get("purpose") == "maskable" for i in manifest["icons"])
    for icon in manifest["icons"]:
        assert (ROOT / icon["src"]).exists(), icon
    for shortcut in manifest["shortcuts"]:
        assert (ROOT / shortcut["url"].split("?")[0]).exists(), shortcut


def test_every_page_has_a_light_and_a_dark_theme_color_and_a_main():
    for page in PAGES:
        html = (ROOT / page).read_text(encoding="utf-8")
        colors = re.findall(r'<meta name="theme-color" content="(#[0-9a-f]{6})" media="\(prefers-color-scheme: (\w+)\)">', html)
        assert sorted(c[1] for c in colors) == ["dark", "light"], page
        assert "<main" in html, page


def test_fonts_ship_with_their_licenses():
    for font, lic in (("EBGaramond.woff2", "OFL-EBGaramond.txt"), ("Inter.woff2", "OFL-Inter.txt")):
        assert (ROOT / "fonts" / font).exists() and (ROOT / "fonts" / lic).exists()
    assert not (ROOT / "fonts" / "EBGaramond-Italic.woff2").exists()  # nothing on the site is italic
