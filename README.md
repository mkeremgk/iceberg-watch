# Iceberg Watch

Iceberg Watch uses OpenCV 5 and AWS batch processing to detect iceberg candidates around Coulman Island, associate provisional objects across four satellite dates and calculate their effects on a colony's modelled access. The comparison holds the August boundary, colony start and passability assumptions fixed while changing candidate barriers, so its results describe conditional access rather than observed penguin movements or verified July water conditions.

[Explore the public demonstration](https://iceberg-watch-mkgking.mkgking1.chatgpt.site) to view the acquisitions from 16, 22 and 28 July and 21 August 2025, compare routes with and without candidate barriers and inspect corridor failures. The Antarctic maps display recorded analysis results, while a separate editable grid demonstrates the routing algorithm in the browser. Selecting a date does not start a new AWS job.

[Watch the project video](https://youtu.be/t0JKZINMlS4) for a walkthrough of the application, methods and results.

## Results

Four Sentinel 1 SAR acquisitions span 36 days and contain 142 offshore candidate observations in total. These are observations across dates, not 142 unique confirmed icebergs. The comparison evaluates 16 nominal scenarios at 80 and 200 metre grid spacing, plus 48 corridor scenarios. Across the nominal settings, candidate barriers add between 0 and 414 metres relative to the corresponding baseline. The two consecutive July image pairs support provisional temporal associations, while the longer gap to August is not treated as a verified identity link.

At 80 metre spacing with offshore candidates, the analysis produces the following results. Each candidate is tested both alone and by removing it from the complete barrier set, and effects from these tests cannot be added together.

| Acquisition | Detected candidates | Candidates intersecting the route domain | Candidates with a tested effect | Extra distance with all candidates |
|---|---:|---:|---:|---:|
| 16 July 2025 | 37 | 13 | 1 | 33 m |
| 22 July 2025 | 28 | 7 | 1 | 137 m |
| 28 July 2025 | 33 | 7 | 1 | 66 m |
| 21 August 2025 | 44 | 7 | 1 | 66 m |

Across both grid spacings and barrier policies, zero to four candidates affect the tested result. A separate corridor experiment finds a path in 35 of 48 trials and reports 13 as unavailable. These small distance changes depend on the model assumptions and do not establish feeding disruption, detection accuracy or complete iceberg coverage.

## Install and check

The supported environment is Ubuntu 24.04 x86_64 with Python 3.12.3. From the repository root, run:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r main_project/requirements-aws-lock.txt
python main_project/submission/smoke_test.py
```

This runs the software tests and a synthetic detour and closed passage example without satellite data. The current suite has 53 tests; the recorded 23 October AWS run passed 56, including three checks for exploratory water experiments that are no longer distributed. The 26 stage analysis and its recorded results are retained, while that earlier AWS evidence is not presented as a fresh execution of this cleaned checkout.

The [data guide](main_project/submission/DATA_SETUP.md) explains how to supply the real inputs, and the [runbook](main_project/RUNBOOK.md) covers analysis, review, website export and verification. Raw satellite archives, private annotations, paper reference imagery, generated outputs and credentials are not included in Git. The attributed SCAR reference clip is included.

For optional browser algorithm checks, install Node.js and run `make test-web`. The application integration check additionally needs generated website exports, as described in the runbook. `make test` runs the data-free Python checks, and `make verify` checks the prepared source snapshot against its manifest.

## Repository contents

This checkout contains the analysis and website source, tests, final documentation, the attributed SCAR reference clip and selected recorded numerical results. `RESULTS_SUMMARY.json` contains the nominal route distances, `CANDIDATE_IMPACT.json` contains the individual intervention outcomes, and `RECORDED_AWS_CHECKS.json` records the historical cloud verification. These are saved evidence rather than a fresh computation after cloning.

The GitHub preparation preserves the submitted analysis code and numerical evidence. Only repository documentation, ignore rules and local command helpers have been added or adjusted. No open source licence has been selected for the project code; reference data attribution is documented separately.

## Documentation

| Document | Purpose |
|---|---|
| [Technical report](main_project/submission/TECHNICAL_REPORT.md) | Methods, results, evaluation and scientific limitations |
| [Architecture](main_project/submission/ARCHITECTURE.md) | How preparation, AWS analysis and the website connect |
| [Runbook](main_project/RUNBOOK.md) | Commands for execution, review and verification |
| [Data setup](main_project/submission/DATA_SETUP.md) | Exact satellite products and required reference inputs |
| [Sources and publication](main_project/submission/ASSET_RIGHTS.md) | Attribution, licences and distribution boundaries |

The source snapshot includes selected recorded results and a SHA256 manifest. From the repository root, run `python3 main_project/submission/verify_package.py` to verify its contents and open `START_HERE.html` for its result summary. No GitHub account is required. The manifest describes this prepared snapshot. Intentional edits to listed files require regenerating it before using it as a new integrity baseline. Reproducing the Antarctic results requires the separate inputs documented above.
