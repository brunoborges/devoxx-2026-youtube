# Devoxx 2026 YouTube audience insights

**[Open the dashboard](https://brunoborges.github.io/devoxx-2026-youtube/)**

A standalone, interactive report covering 192 public videos from the
[YouTube @DevoxxForever Videos tab](https://www.youtube.com/@DevoxxForever/videos),
with a publication cutoff of October 1, 2026. The October 20, 2026 snapshot
contains 291,615 views and 2,352 likes; median views are 780. The separate
October 20 comment collection obtained **191/192 exact public counts**, totaling
125 comments, including **139 genuine zeros**. There are 0 disabled, 0 unavailable,
and **1 failed** count (YouTube HTTP 429 rate limiting). Missing counts remain
`null`, never zero; the dashboard shows coverage and per-video status.

Explore title keywords (all/any, quoted phrases, exclusions, case/accent
normalization), date/topic/view filters, rankings, distributions, reach versus
response, publication cohorts, overlapping title topics, word exploration,
selection-versus-rest comparisons, and a sortable, paginated video explorer
with filtered CSV export. Speaker benchmarks add views/likes/comments cumulative
distribution charts, selected-talk markers, percentile ranks, and
P50/P90/P95/P99 count thresholds. All report data is embedded; there are no CDN
or runtime dependencies.

## Build and preview

Requires Python 3, with no third-party packages:

```sh
python3 scripts/build.py
python3 -m http.server 8000
```

Open <http://localhost:8000/>. The builder resolves its inputs relative to its
own repository location, not the current working directory. It deterministically
rebuilds the committed `index.html` and full CSV/XLSX exports from:

- `src/devoxx-dashboard.template.html`: authored HTML, CSS, and JavaScript.
- `data/devoxx_stats.json`: authoritative snapshot, preserving titles, video URLs,
  publication dates/timestamps, view and like counts, UTC capture timestamps,
  and channel IDs, plus public comment counts, status, source, reported header,
  separate collection timestamps, and any extraction error.

Full snapshot exports are also available as
[CSV](data/devoxx-videos-since-2026-10-01.csv) and
[Excel](data/devoxx-videos-since-2026-10-01.xlsx). Filtered CSV exports are generated
locally in the browser by the dashboard.

The CSV and XLSX are generated from the same canonical JSON by the standard-library
builder. Null counts are blank cells with an explicit status column; real zeros
are numeric zero. CSV exports escape spreadsheet formula prefixes, and XLSX
titles are stored as literal strings, not formulas.

To collect comments again (network access required):

```sh
python3 scripts/collect_comments.py --resume
python3 scripts/build.py
```

`--resume` retries only unavailable/failed counts and preserves successful
collections. Omit it to collect all comments again. The collector uses public
watch-page metadata and its initial comments continuation, saves progress
per video, uses at most three concurrent requests, and reports failures with a
nonzero exit status. It never refreshes the original views, likes, or their
capture timestamps and never saves comment text/authors or raw responses.
Do not retry repeatedly when YouTube rate-limits access.

## Speaker comparisons

Choose a title from the independent **Your talk** list. The comparison population
defaults to **all 192 videos**, ignoring title searches and dashboard filters,
so finding one talk does not accidentally benchmark it against itself. Explicitly
choosing **Current dashboard filters** instead compares with that cohort; the
selected talk need not belong to it. Each chart displays the available sample
size. Missing comment counts are excluded from that metric only.

- **P50/P90/P95/P99** are count thresholds, not ranks. Sort the available counts
  ascending and interpolate linearly at zero-based index `(n - 1) * p`
  (inclusive percentiles). Fractional thresholds are possible.
- **Percentile rank** is `100 * count(values <= selected count) / n`. Ties receive
  the same upper cumulative rank. Thus a talk with zero comments can have a
  nonzero rank if other videos also have zero comments.
- **Charts** show empirical cumulative distributions as steps, with a selected-talk
  dot. The count axis uses `log(1 + count)` so zero and the long tail both fit.
  Empty samples have no rank/thresholds; one-item samples have identical
  thresholds and little comparative meaning.

These are comparisons of public audience counts, **not talk-quality scores**.
Comments were collected separately (see each record's
`comments_captured_at_utc`), so comparisons across metric types are not simultaneous.

## Checks

The regression checks use only Python 3 and Node.js (no third-party test packages):

```sh
python3 scripts/build.py
python3 -m unittest discover -s tests -v
node --test tests/dashboard.test.cjs
```

## Provenance and limitations

The dataset records public YouTube metadata captured on October 20, 2026 for
videos appearing in the channel's Videos tab and published on or after October 1,
2026, up to the snapshot. It is a fixed snapshot, not a live feed or an exhaustive
inventory of other channel tabs. Per-record `captured_at_utc` values preserve
capture timing. Exact public comment counts come from YouTube's comments header,
with the initial comments continuation resolved when necessary. Only integer
counts are accepted; abbreviated/missing labels are unavailable, explicit
disabled messages are disabled, and failed requests/parsing are failed.
Counts reflect YouTube's aggregate header (potentially including replies), not
unique commenters; moderation, removals, and later activity can change them.

There is no historical growth series: differences between videos do not establish
growth, causality, or like-for-like performance. Topic rules use titles only,
are transparent in the dashboard's methodology, and overlap; topic totals must
not be added together. Views/day is a lifetime age-normalized average, not a
measured daily rate or trend. Upload age, exposure, and audience differences
affect comparisons.

## Publication

GitHub Pages serves the committed `index.html` from the root of `main`.
After changing the template or JSON, rebuild and commit the generated page
alongside its source. The site can also be downloaded and opened offline.
