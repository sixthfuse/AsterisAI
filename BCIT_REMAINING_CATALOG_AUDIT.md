# BCIT Remaining Catalog Audit

Audit date: 2026-09-08

## Outcome

The six current official BCIT area catalogs contain **425 unique canonical entries** across **622 listing appearances**. PostgreSQL contains **209 active programs** and **3288 courses**. Exact program-ID matching finds **208 current catalog programs already loaded** and **1 loaded record absent from the current area catalogs**.

Exactly **165 legitimate BCIT programs remain to be loaded**. Importing those candidates with no cleanup or deactivation would take Asteris from 209 to **374 active programs**. The strictly current catalog-aligned legitimate universe is 373; the one-record difference is loaded program 5325ACERT, whose official page is live but absent from all six current catalogs.

## Current catalog classification

| Classification | Count |
|---|---:|
| already loaded | 208 |
| legitimate remaining import candidate | 165 |
| prior RED/holdback | 2 |
| apprenticeship/training structure without identifiable course IDs | 31 |
| non-program/special entry | 19 |
| **Total unique current entries** | **425** |

The classifications are mutually exclusive. Prior RED/holdback takes precedence over apprenticeship or special-entry type, so 3790APPR and 0120NOBCIT appear only in the RED count.

## Duplicate, renamed, inactive, and special records

The six catalogs repeat the same canonical program across subject areas 197 times. These are exact same-ID, same-URL cross-catalog appearances and were removed before matching.

The program sitemap contains 489 URLs. Compared with the current canonical list, 45 sitemap-only URLs redirect to current programs and are classified as duplicate/renamed/variant. Another 34 sitemap-only URLs are not in any current area catalog: 20 return 404 and 14 remain live but unlisted.

The mutually exclusive current classification contains 19 non-program/special entries, plus 0120NOBCIT in the RED count. There are therefore 20 current special/non-credential listings by type.

## RED and apprenticeship holdbacks

| Program | Classification | Reason |
|---|---|---|
| 0120NOBCIT — International Student Entry | prior RED/holdback | Official curriculum publishes no identifiable BCIT course references. |
| 3790APPR — Industrial Electrician | prior RED/holdback | Official matrix has apprenticeship levels and training credits but no course identifiers. |

An additional 31 current apprenticeship entries publish training levels/hours without identifiable BCIT course IDs. Together with 3790APPR, all 32 current apprenticeship entries remain outside the importable count.

## Candidate composition

### By credential

| Credential | Candidates |
|---|---:|
| Advanced Certificate | 7 |
| Associate Certificate | 24 |
| Bachelor of Health Science | 1 |
| Bachelor of Science | 5 |
| Certificate | 38 |
| Diploma | 36 |
| Graduate Certificate | 2 |
| Microcredential | 52 |

### By primary school label

| School | Candidates |
|---|---:|
| BCIT International | 4 |
| Learning and Teaching Centre | 2 |
| School of Business + Media | 62 |
| School of Computing and Academic Studies | 12 |
| School of Construction and the Environment | 39 |
| School of Energy | 13 |
| School of Health Sciences | 22 |
| School of Transportation | 11 |

## Recommended next batch

Use a 50-program batch drawn from the 165 candidates, balanced across schools and credentials. Keep all apprenticeship, special/non-program, and prior RED entries out of the batch. At the same rate, completion is three batches of 50, 50, and 65 programs. Refresh each chosen official page immediately before contract generation because BCIT catalog membership and redirects can change.

## Discovery limits

BCIT's six area pages explicitly describe their contents as programs currently listed in the Program Catalogue, so they are the active-catalog authority for this audit. The sitemap is useful for aliases and stale URLs but cannot establish active status by itself.

The sitemap is not a clean superset: 15 current canonical URLs are absent from it, while 79 sitemap URLs are absent from the current canonical list. A live page omitted from every current area catalog is reported as not currently listed rather than guessed to be administratively discontinued.

## Change statement

This was discovery only. No programs or courses were imported. PostgreSQL was queried read-only. No production code, schema, advisor wording, or conversational behavior was changed.

Row-level results are in `program_extractor_audit/remaining_catalog_audit/summary.csv` and the complete machine-readable audit is in `BCIT_REMAINING_CATALOG_AUDIT.json`.
