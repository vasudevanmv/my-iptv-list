"""
update_playlist.py
-------------------
Runs inside GitHub Actions (not on your PC). Downloads the M3U lists
named in CATEGORY_RULES, sorts channels into your categories, removes
duplicate channels, checks which streams are actually alive, and writes
merged_cleaned.m3u.

You normally do NOT need to run this yourself - GitHub Actions runs it
on a schedule automatically. To change categories, only edit the
CATEGORY_RULES block below. See README.md for details.
"""

import os
import re
import sys
import subprocess
import concurrent.futures
import urllib.request

# ---------------------------------------------------------------------
# SETTINGS - this is the only part you normally need to edit
# ---------------------------------------------------------------------

# Handy names for lists, so the rules below stay short and readable.
# Add your own (e.g. HINDI = ".../languages/hin.m3u") and use them in rules.
BASE = "https://iptv-org.github.io/iptv"
MAL = f"{BASE}/languages/mal.m3u"
ENG = f"{BASE}/languages/eng.m3u"
MOVIES = f"{BASE}/categories/movies.m3u"
NEWS = f"{BASE}/categories/news.m3u"
DOCUMENTARY = f"{BASE}/categories/documentary.m3u"
COUNTRY_INDEX = f"{BASE}/index.country.m3u"
FREE_TV = "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"

# CATEGORY_RULES - one list, processed top to bottom. Each rule is:
#
#     (source_list, "Category Name" or None, [filters])
#
# source_list   : which list the channels are taken from.
# Category Name : every channel kept by this rule is renamed into this
#                 category. Use None to keep each channel's own original
#                 category (used for the country index and Free-TV).
# filters       : a list of conditions a channel must pass to be kept.
#                 Each condition is ("in", some_list) or ("not_in", some_list)
#                 meaning "the channel must be (or must not be) present in
#                 that other list". Matching is done on the stream URL.
#                 An empty list [] means keep every channel from the source.
#                 With several filters, a channel must pass ALL of them.
#
# ORDER MATTERS: rules run top to bottom. If the same stream appears in
# more than one rule, the FIRST rule that picked it wins and later copies
# are dropped. So put specific categories first and broad catch-all
# lists (Free-TV, country index) last.
CATEGORY_RULES = [
    (MAL,         "Malayalam",   []),
    (DOCUMENTARY, "Documentary", [("in", ENG)]),
    (NEWS,        "News",        [("in", ENG)]),
    (MOVIES, "Movies English",       [("in", ENG)]),
    (MOVIES, "Movies International", [("not_in", ENG)]),
    (FREE_TV,     "FreeTV",          []),
    (COUNTRY_INDEX, None,        []),
]

# ---- Ideas for later (copy a line into CATEGORY_RULES above, ABOVE the
# ---- broader rule it should take channels from) ----
#
#   (NEWS,   "Malayalam News",   [("in", MAL)]),               # news channels that are Malayalam
#   (MOVIES, "Malayalam Movies", [("in", MAL)]),               # movie channels that are Malayalam
#   (MOVIES, "English Movies",       [("in", ENG)]),           # split Movies in two ...
#   (MOVIES, "International Movies", [("not_in", ENG)]),       # ... instead of one "Movies" line
#   (NEWS,   "International News",   [("not_in", ENG), ("not_in", MAL)]),

OUTPUT_FILE = "merged_cleaned.m3u"
MAX_WORKERS = 20
TIMEOUT_SECONDS = 8

# ---------------------------------------------------------------------


def download_m3u_text(url):
    print(f"  Downloading {url} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  WARNING: failed to download {url} ({e}), skipping.")
        return ""


def parse_m3u_text(text):
    channels = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    current_extinf = None
    for line in lines:
        if line.startswith("#EXTINF"):
            current_extinf = line
        elif line.startswith("#"):
            continue
        else:
            if current_extinf is not None:
                channels.append((current_extinf, line))
                current_extinf = None
    return channels


def set_group_title(extinf_line, new_group):
    """Force the group-title="..." attribute on an #EXTINF line to new_group.
    If the line has no group-title attribute at all, one is inserted."""
    if re.search(r'group-title="[^"]*"', extinf_line):
        return re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', extinf_line)
    # No group-title present - insert one right before the trailing
    # ",Channel Name" part.
    if "," in extinf_line:
        head, name = extinf_line.rsplit(",", 1)
        return f'{head} group-title="{new_group}",{name}'
    return extinf_line


def get_channel_name(extinf_line):
    if "," in extinf_line:
        return extinf_line.rsplit(",", 1)[-1].strip()
    return extinf_line


def check_stream_alive(url):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-timeout", str(TIMEOUT_SECONDS * 1_000_000),
                "-select_streams", "v:0",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS + 5,
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def main():
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True, timeout=5)
    except FileNotFoundError:
        print("ERROR: ffprobe not found on this runner.")
        sys.exit(1)

    # Every list is downloaded only once, even if several rules or filters
    # use it. get_channels() remembers what it already fetched.
    cache = {}

    def get_channels(url):
        if url not in cache:
            cache[url] = parse_m3u_text(download_m3u_text(url))
        return cache[url]

    def stream_urls_of(url):
        return {stream_url for _, stream_url in get_channels(url)}

    print("Processing each rule in order...")
    all_channels = []
    for source, category_name, filters in CATEGORY_RULES:
        channels = get_channels(source)

        for mode, filter_list in filters:
            if mode not in ("in", "not_in"):
                print(f"  ERROR: unknown filter '{mode}' - use \"in\" or \"not_in\".")
                sys.exit(1)
            wanted = stream_urls_of(filter_list)
            if mode == "in":
                channels = [(e, u) for e, u in channels if u in wanted]
            else:
                channels = [(e, u) for e, u in channels if u not in wanted]

        if category_name:
            channels = [(set_group_title(e, category_name), u) for e, u in channels]

        all_channels.extend(channels)
        label = category_name if category_name else "(original categories kept)"
        print(f"  -> {len(channels):5d} channels  {label}   <- {source}")

    print(f"\nTotal channels found (before dedup): {len(all_channels)}")

    print("\nStep 1: Removing duplicate channels (same stream URL)...")
    seen_urls = set()
    deduped = []
    for extinf, url in all_channels:
        if url not in seen_urls:
            seen_urls.add(url)
            deduped.append((extinf, url))
    print(f"  Channels remaining after dedup: {len(deduped)}")

    print(f"\nStep 2: Checking which of {len(deduped)} streams are alive...")
    alive_channels = []
    checked_count = 0
    total = len(deduped)

    def worker(item):
        extinf, url = item
        return (extinf, url, check_stream_alive(url))

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for extinf, url, is_alive in executor.map(worker, deduped):
            checked_count += 1
            name = get_channel_name(extinf)
            status = "OK  " if is_alive else "DEAD"
            print(f"  [{checked_count}/{total}] {status} - {name}")
            if is_alive:
                alive_channels.append((extinf, url))

    print(f"\nStep 3: Writing {len(alive_channels)} live channels to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, url in alive_channels:
            f.write(extinf + "\n")
            f.write(url + "\n")

    print("\nDone!")
    print(f"  Started with: {len(all_channels)} channels")
    print(f"  After dedup:  {len(deduped)} channels")
    print(f"  Final (live): {len(alive_channels)} channels")


if __name__ == "__main__":
    main()
