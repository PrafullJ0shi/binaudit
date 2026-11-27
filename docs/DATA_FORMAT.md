# Data format

One CSV row per distinct item found in one audit. UTF-8, comma separated, header row
required. This is the file the web app exports and imports, and the file the command line
tool reads.

| Column | Required | Example | Notes |
|---|---|---|---|
| `audit_id` | yes | `HA2-DRY-0706-k3f9` | same value for every row of one audit |
| `date` | yes | `2026-07-06` | ISO date |
| `site` | yes | `Hostel A, floor 2` | quote it if it contains a comma |
| `bin_stream` | yes | `dry` | `wet`, `dry` or `hazardous`: the bin the item was found in |
| `phase` | no | `before sign` | any label; phases are compared in the order they first appear |
| `item` | yes | `tea leaves` | free text; catalogue names are suggested |
| `item_stream` | yes | `wet` | where the item belongs |
| `count` | yes | `3` | whole number; empty means 1 |
| `grams` | no | `42.5` | weight of these items |

An item is misplaced when `item_stream` differs from `bin_stream`.

Rows are checked on import. A bad stream name, a fractional count or a non-numeric weight
stops the import with the line number.
