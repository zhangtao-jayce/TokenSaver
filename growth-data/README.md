# Growth Data

The weekly `Growth metrics` workflow appends one JSON object to `github.jsonl`.

Tracked fields:

- stars, forks, watchers, and open issues
- repository views and unique visitors over GitHub's available 14-day window
- clones and unique cloners over the same window
- top external referrers

Use these snapshots to compare README, release, demo, case-study, and distribution experiments. Traffic data is repository-level aggregate data; no visitor identities are collected.

`experiments.jsonl` records public launch placements and their GitHub baseline. Community interaction counts are only added when they can be observed reliably; missing values are not estimated.
