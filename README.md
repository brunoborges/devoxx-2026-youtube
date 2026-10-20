# Devoxx 2026 YouTube audience insights

**[Open the dashboard](https://brunoborges.github.io/devoxx-2026-youtube/)**

A standalone, interactive report covering 192 public videos from the
[YouTube @DevoxxForever Videos tab](https://www.youtube.com/@DevoxxForever/videos),
with a publication cutoff of October 1, 2026. The October 20, 2026 snapshot
contains 291,615 views and 2,352 likes; median views are 780.

Explore title keywords (all/any, quoted phrases, exclusions, case/accent
normalization), date/topic/view filters, rankings, distributions, reach versus
response, publication cohorts, overlapping title topics, word exploration,
selection-versus-rest comparisons, and a sortable, paginated video explorer
with filtered CSV export. All report data is embedded; there are no CDN or
runtime dependencies.

## Build and preview

Requires Python 3, with no third-party packages:

```sh
python3 scripts/build.py
python3 -m http.server 8000
```

Open <http://localhost:8000/>. The builder resolves its inputs relative to its
own repository location, not the current working directory. It deterministically
rebuilds the committed `index.html` from:

- `src/devoxx-dashboard.template.html`: authored HTML, CSS, and JavaScript.
- `data/devoxx_stats.json`: authoritative snapshot, preserving titles, video URLs,
  publication dates/timestamps, view and like counts, UTC capture timestamps,
  and channel IDs.

Full snapshot exports are also available as
[CSV](data/devoxx-videos-since-2026-10-01.csv) and
[Excel](data/devoxx-videos-since-2026-10-01.xlsx). Filtered CSV exports are generated
locally in the browser by the dashboard.

## Provenance and limitations

The dataset records public YouTube metadata captured on October 20, 2026 for
videos appearing in the channel's Videos tab and published on or after October 1,
2026, up to the snapshot. It is a fixed snapshot, not a live feed or an exhaustive
inventory of other channel tabs. Per-record `captured_at_utc` values preserve
capture timing.

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
