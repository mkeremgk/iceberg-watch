# Iceberg Watch: what changing ice barriers could mean for access

Updated 24 October 2026.

## The question behind the project

Iceberg Watch examines how changing ice features around Coulman Island could affect a colony’s access to an assumed open water boundary. It combines four Sentinel observations with image processing, provisional object associations and a shortest path model, then makes the results available for inspection. The intended use is exploratory analysis and teaching, rather than field navigation.

The comparison asks a deliberately limited question: when the August boundary, colony start and traversable domain stay fixed, how much does the calculated route change as candidate barriers change between dates? This allows a controlled comparison even though the actual July water boundaries have not been established. The resulting July scenarios are therefore counterfactuals, and none of the paths represents an observed penguin GPS track.

## From satellite scenes to candidate barriers

The inputs are Sentinel 1 HH scenes acquired on 16, 22 and 28 July and 21 August 2025. Experimental GCP/TPS geolocation maps them onto a shared EPSG:32759 grid with 40 metre cells. This preparation is not terrain correction, so geolocation uncertainty remains relevant, especially near steep coastal terrain. Reference geometry from SCAR ADD supports land and coastal filtering but does not establish the current coastline or classify open water.

OpenCV performs contrast scaling, median filtering, Otsu thresholding, morphological closing and connected component analysis in `extract_candidates.py`. Components smaller than the configured 0.1 square kilometre threshold are discarded. That setting controls the algorithm; it is not an experimentally established detection limit. Environmental filters then separate offshore proposals from coastal, shelf and edge regions that require more cautious interpretation.

The four dates contain 37, 28, 33 and 44 offshore proposals respectively. Their identities are local to each image, so a component number on one date does not identify the same physical object on another date. `associate_candidates.py` proposes temporal links, while `register_paper.py` uses OpenCV feature matching and robust registration to transfer an approximate reference from [Park et al., Figure 5](https://www.nature.com/articles/s43247-026-03764-w/figures/5). OpenCV consequently determines substantive analysis inputs rather than serving only as a display library.

## How the paths are calculated

The solver searches a grid of permitted cells and prevents diagonal movement through blocked corners. It measures geometric path length, without treating that length as an energy estimate or a biological cost. Filled candidate contours become obstacle hypotheses, while the start, shared valid coverage and August target set remain fixed within each comparison. The solver may select a different endpoint on that same target set when an obstacle blocks a shorter alternative.

Four dates, two grid spacings of 80 and 200 metres, and two barrier policies produce 16 nominal routes. One policy retains offshore candidates only, while the other includes all retained candidates. The website shows those saved paths on the corresponding satellite images, together with the reference path calculated without candidate barriers. These geometries come from the actual research solver, whereas the editable grid further down the page is a separate synthetic demonstration.

A second experiment confines the search to a corridor around the reference path. Total widths of 500, 1000 and 2000 metres produce 48 trials, of which 35 have a path and 13 do not. A failed search remains unavailable rather than becoming a zero length route. The corridor is another explicit modelling assumption, not a verified strip of solid ice. For 22 July at 80 metre spacing with offshore candidates, the two narrower corridors have no path, while the 2000 metre corridor gives 13.957 kilometres compared with 13.937 kilometres in the unrestricted case.

## What the results support

Across the nominal settings, the change between 16 July and 21 August ranges from an additional 33 to 180 metres. Between 22 and 28 July, the range runs from a reduction of 71 metres to an increase of 131 metres, so even the direction depends on the setting. The 28 July and 21 August paths have equal lengths in the tested settings despite differences in their geometry.

Some 80 metre solutions for 22 July choose an endpoint roughly four kilometres away along the same boundary set while changing total distance only slightly. That is a change in endpoint selection, not four kilometres of additional travel. Equal cost alternatives on the grid also limit how much meaning can be assigned to a particular bend in the plotted path.

Eighty additional trials perturb candidate boundaries by 40 or 80 metres in either direction. All remain feasible, but the 16 July to 21 August change spans 0 to 297 metres when offsets are shared across dates and minus 80 to plus 414 metres when offsets vary independently. These are selected stress tests rather than measured uncertainty bounds or confidence intervals. Taken together, the experiments show sensitivity to obstacle and routing assumptions; they do not establish a significant ecological effect.

## Which detected candidates actually affect access?

An additional intervention audit tests every retained candidate twice: once as the only barrier and once by removing it from the complete barrier set. The analysis checks all 16 nominal settings and distinguishes a distance or feasibility change from a change between equal length grid paths. Individual effects are not additive, because candidates can overlap in coarse cells or obstruct different alternative passages.

At 80 metre spacing with offshore candidates, the four dates contain 37, 28, 33 and 44 detected candidates. Of these, 13, seven, seven and seven intersect the permitted route domain, and one candidate per date changes the calculated result in the individual tests. The corresponding extra distances with all barriers are approximately 33, 137, 66 and 66 metres. The other candidates remain part of the detected inventory but do not change the selected route under these tests. A zero effect here does not establish that an object is irrelevant to another colony, target or passability model.

Across both spacings and policies, the number of candidates showing an effect ranges from zero to four. Including coastal review regions can increase that count while also admitting more uncertain obstacles. These results explain why two plotted paths can almost coincide despite many detections, and they constrain the project's impact claim rather than justify tuning the model to produce a larger detour.

The audit reconstructs component identities from source masks, verifies their areas and classes, and checks that the union of individual filled masks exactly matches the production barrier mask. Conservative aggregation loses none of the retained candidate pixels that lie in the reference surface. All 16 full routes reproduce the saved paths, and every recalculated path is checked for blocked cells, diagonal corners, target membership and length. Synthetic tests additionally cover overlapping obstacles and a passage closed only by multiple barriers together.

## What human review established

A reviewer assessed 34 proposed associations, accepting 25, rejecting three and leaving six uncertain. This acceptance fraction is not tracking accuracy because unproposed links were not assessed, and some rejections concern fragmented segmentation rather than identity. Reliable split and merge handling remains unresolved, and no identity link is claimed across the 24 day gap before August.

A separate blinded pilot used two coastal and two offshore tiles repeated across the four dates. It produced 24 marks, comprising ten candidate labels and fourteen uncertain labels, with the reviewer qualifying all marks as uncertain. Eight point centres overlap raw proposal pixels and five overlap retained review pixels. Those descriptive overlap counts cannot be interpreted as precision, recall or verified true positives. The pilot provides useful feedback but not independent physical ground truth or a representative assessment of every iceberg in the region.

## Execution, verification and access

The current prepared map pipeline contains 26 stages and was checked on AWS EC2 with Python 3.12.3 and OpenCV 5.0.0. The 23 October verification records 56 passing tests locally and on AWS, together with seven matching output comparisons, including the candidate intervention scenarios. Raw satellite preparation was performed locally and is outside that AWS execution claim. The current distribution contains 53 tests after removing three checks belonging only to retired water experiments. The recorded AWS run remains historical evidence rather than a fresh execution of the cleaned distribution. Dependencies are pinned in `requirements-aws-lock.txt`, while the runbook documents setup and execution.

The tests cover grid contracts, blocked cells, diagonal corners, distance sums, fixed targets and review provenance. Execution logs record stage order and source hashes, and a failed stage stops the batch. Review decisions are bound to the candidate geometry and input evidence so that changed component identities do not silently inherit earlier opinions. These checks establish software behaviour, not environmental truth.

The public website serves selected outputs from the recorded analysis, including the saved route coordinates and their source hashes. Changing a date or policy selects an existing result and does not launch a new AWS job. The separate synthetic example recalculates locally in the browser. Source code is supplied as a downloadable archive, while the data guide explains the external inputs needed to reproduce the Antarctic analysis. The archive can be inspected and tested without a GitHub account.

## Limits that remain

The main unresolved issues are independent detection assessment, fragmented objects, geolocation error, actual water boundaries for each date and the biological relevance of the modelled domain. A dark radar return alone does not prove that a cell is open water or safe ice. The public route maps should therefore be read as conditional calculations, not as validated travel recommendations.

The system is a deterministic analysis pipeline with human review and does not acquire new observations or track penguins automatically. The original paper figure and digitised boundary layer are not bundled with the public website; the calculated paths retain their stated dependence on that approximate reference. The accompanying source inventory explains this distinction and the remaining reproduction requirements.
