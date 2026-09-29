# IPTV Auto-Updating Playlist — Setup Guide

This sets up a GitHub repository that automatically downloads IPTV
channel lists, removes duplicates and dead channels, and publishes one
clean, permanent playlist link — with no PC or Raspberry Pi needing to
stay on. GitHub runs the update for you on a schedule.

## What you'll end up with

- A permanent link like:
  `https://raw.githubusercontent.com/yourusername/my-iptv-list/main/merged_cleaned.m3u`
- This link auto-refreshes every day with a deduped, dead-channel-free
  playlist, and you just point OwnTV at it once.

---

## Step 1: Create the repository

1. Go to https://github.com and sign in (or sign up if you don't have
   an account).
2. Click the **+** icon top-right → **New repository**.
3. Name it `my-iptv-list` (or anything you like).
4. Set it to **Public** (required for the free raw link to work).
5. Click **Create repository**.

## Step 2: Add the script file

1. In your new (empty) repo, click **Add file** → **Create new file**.
2. Name it exactly: `update_playlist.py`
3. Open the `update_playlist.py` file I generated, copy its full
   contents, and paste them into the GitHub editor box.
4. Scroll down, click **Commit changes**.

   Before committing, you can edit the `SOURCE_URLS` list near the top
   of the file to add more iptv-org playlists. Browse available lists
   at https://github.com/iptv-org/iptv/tree/master/streams — click any
   file, click **Raw**, and copy that URL into the list.

## Step 3: Add the workflow file

GitHub Actions workflow files must live in a specific folder path.

1. Click **Add file** → **Create new file** again.
2. In the filename box, type exactly:
   `.github/workflows/update-playlist.yml`
   (typing the `/` characters automatically creates the folders — this
   is normal and expected.)
3. Paste in the contents of the `update-playlist.yml` file I generated.
4. Click **Commit changes**.

## Step 4: Run it for the first time

1. Go to the **Actions** tab at the top of your repo.
2. You should see a workflow called **Update IPTV Playlist**.
3. Click it, then click **Run workflow** (dropdown button) → **Run workflow**.
4. Wait a few minutes — click into the running job to watch progress
   live (it prints OK/DEAD for each channel, just like the local script).
5. When it finishes, go back to your repo's main page — you should now
   see a new file: `merged_cleaned.m3u`.

## Step 5: Get your permanent link

1. Click on `merged_cleaned.m3u` in your repo.
2. Click the **Raw** button.
3. Copy the URL from your browser's address bar. It will look like:
   `https://raw.githubusercontent.com/yourusername/my-iptv-list/main/merged_cleaned.m3u`

This link never changes, even as the file content updates daily.

## Step 6: Add it to OwnTV

1. Open OwnTV on your TV.
2. Go to **Settings** → playlist/source management → **Add Playlist**
   (or equivalent, wording may vary).
3. Paste the raw GitHub link from Step 5.
4. Save.

## Step 7: Done — how updates work from here

- Every Sunday at 04:00 UTC, GitHub automatically re-downloads all the
  source lists, removes dead channels and duplicates, and updates
  `merged_cleaned.m3u` in your repo — with no action from you.
- The link never changes, so OwnTV keeps working. Some players
  auto-refresh playlists periodically; if yours doesn't, just re-open
  or "refresh" the playlist inside OwnTV occasionally.
- If you ever want to add more channel sources: edit `SOURCE_URLS` in
  `update_playlist.py` (click the file → pencil/Edit icon → change →
  Commit changes). The next scheduled run (or a manual run via the
  Actions tab) will pick it up.
- To trigger an update immediately instead of waiting for the daily
  schedule: **Actions** tab → **Update IPTV Playlist** → **Run workflow**.

## Troubleshooting

- **Workflow shows a red X / failed**: click into it to see the log.
  Usually means a source URL in `SOURCE_URLS` is broken — check the
  URL still works by pasting it in a browser.
- **merged_cleaned.m3u never appears**: make sure Step 3's filename is
  exactly `.github/workflows/update-playlist.yml` (folders included).
- **Too few channels survive**: some streams fail the liveness check
  due to region restrictions on GitHub's servers rather than being
  truly dead. This is a known limitation of checking from the cloud
  instead of your home network.

## EPG Workaround

Open https://epgshare01.online in a browser, look for country/category codes matching India, Documentary, and English/general entertainment, and paste those .xml.gz links into OwnTV's separate EPG field (not the playlist URL). If OwnTV lets you add multiple EPG URLs, add all three; if it only takes one, the India one will cover the bulk of what you watch.
