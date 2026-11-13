# Sealed foundation and historical evidence

`source-closeout/payout-source-closeout-v5-20261111.tar.gz` is the accepted source archive, copied unchanged from the private planning workspace. Expected SHA-256:

`c92edadfc65a46627d673b3e1d265dd2861bdd4fdcdea0a7cd5e72abc8105efe`

`source-closeout/REVIEW.md` and `review-evidence/` are original November 11 technical acceptance and finite regression evidence. Counts are historical, not fresh local behavior checks. Source artifact and review/evidence copies are byte-identical; product-specific adaptations must live outside these originals.

The original review contains links relative to its original workspace; its complete substantive acceptance text and local evidence are included here. No product task may require following a parent-workspace link.

The harness `source-closeout/review-evidence/check_v5.py` finds the archive relative to itself, extracts into a temporary directory, executes offline checks and writes results beside the harness. Copy the archive plus review-evidence layout to a disposable directory before running it; preserve historical evidence unchanged. It requires Python with tarfile's data extraction filter (Python 3.13+ is the product default). This is a check utility, not application code.

The archive includes historical research/competitor and raw provider material. It is a private build input, not a pre-approved public distribution. Before publication select/review necessary reader/test/example files and resolve license/attribution. Do not publicly ship unrelated private planning or competitor material by default.

Product runtime reader import/extraction and new fixtures are implementation Batch 1, not starter preparation.
