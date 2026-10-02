# My IPTV Playlist (auto-updating)

This repository builds one clean IPTV playlist from several public lists.
GitHub does all the work on a schedule, so no PC or Raspberry Pi needs to
be on.

**What it does**

1. Downloads the source lists you choose (iptv-org, Free-TV, etc.)
2. Sorts channels into your own categories (Malayalam, News, Movies...)
3. Removes duplicate channels
4. Removes dead channels (tests every stream)
5. Publishes the result as `merged_cleaned.m3u`

**Your permanent playlist link** (use this in OwnTV):

```
https://raw.githubusercontent.com/vasudevanmv/my-iptv-list/main/merged_cleaned.m3u
```

> Always use the `raw.githubusercontent.com` link. The normal
> `github.com/.../blob/...` link is a web page, not a playlist, and
> players will reject it.

---

## Files in this repo

| File | Purpose |
|---|---|
| `update_playlist.py` | The script. Contains your category rules. |
| `.github/workflows/update-playlist.yml` | Tells GitHub when to run the script (weekly, or manually). |
| `merged_cleaned.m3u` | The output playlist. Created automatically, do not edit by hand. |
| `README.md` | This guide. |

---

## How the categories work

Open `update_playlist.py` and look for the `CATEGORY_RULES` block near the
top. This is the only part you normally need to edit.

```python
CATEGORY_RULES = [
    (MAL,           "Malayalam",   []),
    (MOVIES,        "Movies",      []),
    (NEWS,          "News",        [("in", ENG)]),
    (DOCUMENTARY,   "Documentary", [("in", ENG)]),
    (FREE_TV,       None,          []),
    (COUNTRY_INDEX, None,          []),
]
```

Each line is a rule with three parts:

```
(source_list,  "Category Name" or None,  [filters])
```

- **source_list**: which list the channels come from (`MAL`, `NEWS`, etc.
  are short names defined just above the rules).
- **Category Name**: the category the channels will appear under in your
  player. `None` means keep each channel's own original category (used for
  the country index, so channels stay under their country name).
- **filters**: conditions a channel must pass to be kept.
  - `[]` means keep every channel from the source.
  - `("in", ENG)` means keep only channels that are also in the English list.
  - `("not_in", ENG)` means keep only channels that are NOT in the English list.
  - You can use several filters; a channel must pass all of them.

### Two rules to remember

1. **Order matters.** Rules run top to bottom. If the same channel is
   picked by more than one rule, the first rule wins and the later copy is
   dropped. So put specific categories on top and broad lists (Free-TV,
   country index) at the bottom.
2. **Matching is by stream URL.** This works well between iptv-org lists
   (they come from the same database). It does not work reliably between
   different providers, since the same channel often has a different
   stream URL there.

### Examples (copy a line into `CATEGORY_RULES`)

Put these **above** the broader rule they take channels from, for example
"Malayalam News" must come above the plain `"Malayalam"` line, otherwise
`"Malayalam"` claims those channels first.

```python
(NEWS,   "Malayalam News",       [("in", MAL)]),
(MOVIES, "Malayalam Movies",     [("in", MAL)]),
(MOVIES, "English Movies",       [("in", ENG)]),
(MOVIES, "International Movies", [("not_in", ENG)]),
(NEWS,   "International News",   [("not_in", ENG), ("not_in", MAL)]),
```

### Adding a new list

1. Find the list at https://iptv-org.github.io/iptv/ (languages,
   categories, countries are all there). Copy the `.m3u` link.
2. Add a short name for it near the top, for example:
   ```python
   HINDI = f"{BASE}/languages/hin.m3u"
   ```
3. Use it in a rule, for example:
   ```python
   (HINDI, "Hindi", []),
   ```

**Tip:** every line in `CATEGORY_RULES` except the last must end with a
comma, and every `"` and `(` must be closed. A missing comma or bracket
makes the run fail.

---

## How to edit a file on GitHub

1. Open the file in your repo (for example `update_playlist.py`).
2. Click the **pencil icon** (Edit this file), top right of the file.
3. Make your change.
4. Click **Commit changes...** then **Commit changes** again.

To replace a whole file with a new version: open it, click the pencil,
select all the text (Ctrl+A), paste the new content, and commit.

---

## Running the update

- **Automatic:** every Sunday at 04:00 UTC. To change this, edit the
  `cron` line in `.github/workflows/update-playlist.yml`. For daily use
  `"0 4 * * *"`, for weekly on Sunday use `"0 4 * * 0"`.
- **Manual (do this after changing the rules):**
  1. Open the **Actions** tab
  2. Click **Update IPTV Playlist** on the left
  3. Click **Run workflow**, then **Run workflow** again
  4. Wait about 30 to 40 minutes (every stream gets tested)

When it finishes with a green tick, `merged_cleaned.m3u` is updated and the
same link keeps working.

### Reading the run log

Open the finished run, then the step **Run merge and cleanup script**. You
will see one line per rule showing how many channels it picked, for example:

```
->   120 channels  Malayalam   <- https://iptv-org.github.io/iptv/languages/mal.m3u
->    45 channels  News   <- https://iptv-org.github.io/iptv/categories/news.m3u
```

If a category shows `0 channels`, its rule matched nothing (see
Troubleshooting).

---

## Using the playlist in OwnTV

1. Open OwnTV, go to add playlist (M3U URL)
2. Paste the raw link from the top of this page
3. Save. After a new weekly update, refresh the playlist in OwnTV to pick
   up the changes.

---

## TV guide (EPG)

The playlist does not include program schedules. Those come from a
separate XMLTV file, which OwnTV takes in its own EPG URL field. This is
not set up yet.

Workaround: Open https://epgshare01.online in a browser, look for country/category codes matching India, Documentary, and English/general entertainment, and paste those .xml.gz links into OwnTV's separate EPG field (not the playlist URL). If OwnTV lets you add multiple EPG URLs, add all three; if it only takes one, the India one will cover the bulk of what you watch.


---

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| Player says the playlist is invalid or rejected | You used the `github.com/.../blob/...` link. Use the `raw.githubusercontent.com` link. |
| Run fails (red cross) | Open the run and read the error. Usually a missing comma, quote or bracket in `CATEGORY_RULES`. |
| Log says `failed to download ... 404` | That list URL is wrong or moved. Open it in a browser to check. |
| A category shows `0 channels` | Either the rule is below another rule that already took those channels (move it up), or the two lists share no identical stream URLs. |
| Fewer channels than expected | Some streams may only work from certain countries, so the test from GitHub's servers marks them dead. |
| Edited a file but nothing changed | The playlist only updates when the workflow runs. Run it manually from the Actions tab. |
