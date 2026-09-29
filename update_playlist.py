"""
update_playlist.py
-------------------
Runs inside GitHub Actions (not on your PC). Downloads the M3U lists
listed in SOURCE_URLS, merges them, removes duplicate channels, checks
which streams are actually alive, and writes merged_cleaned.m3u.

You normally do NOT need to run this yourself - GitHub Actions runs it
on a schedule automatically. See SETUP_INSTRUCTIONS.md for the one-time
setup.
"""

import os
import sys
import subprocess
import concurrent.futures
import urllib.request

# ---------------------------------------------------------------------
# SETTINGS - edit this list to add/remove source playlists
# ---------------------------------------------------------------------

# Raw URLs of M3U files from https://github.com/iptv-org/iptv
# Browse https://github.com/iptv-org/iptv/tree/master/streams to find
# more country/category/language files, then use the "Raw" link for each.
SOURCE_URLS = [
    "https://iptv-org.github.io/iptv/index.language.m3u",
    "https://iptv-org.github.io/iptv/index.country.m3u",
    "https://iptv-org.github.io/iptv/index.category.m3u",
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    # add more lines here, one URL per line, comma at the end
]

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

    print("Step 1: Downloading and merging source lists...")
    all_channels = []
    for url in SOURCE_URLS:
        text = download_m3u_text(url)
        all_channels.extend(parse_m3u_text(text))
    print(f"  Total channels found (before dedup): {len(all_channels)}")

    print("\nStep 2: Removing duplicate channels (same stream URL)...")
    seen_urls = set()
    deduped = []
    for extinf, url in all_channels:
        if url not in seen_urls:
            seen_urls.add(url)
            deduped.append((extinf, url))
    print(f"  Channels remaining after dedup: {len(deduped)}")

    print(f"\nStep 3: Checking which of {len(deduped)} streams are alive...")
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

    print(f"\nStep 4: Writing {len(alive_channels)} live channels to {OUTPUT_FILE}...")
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
