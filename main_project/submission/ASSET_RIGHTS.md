# Sources and what is published

Updated 23 October 2026. This inventory explains the project’s packaging decisions and does not constitute a legal certification.

## Satellite observations and reference surfaces

The analysis uses four Sentinel 1 products obtained through [ASF Vertex](https://search.asf.alaska.edu/). The data guide lists their exact identifiers so that another researcher can obtain the measurements from the provider. The repository does not contain the large raw archives; the website instead shows selected project generated previews of those observations.

The land reference is a clipped and reprojected extract from [SCAR Antarctic Digital Database v7.10](https://data.bas.ac.uk/items/4ecd795d-e038-412f-b430-251b33fc880e/). The extract is included with its source notice and recorded CC BY 4.0 attribution. It supports environmental filtering and should not be interpreted as a current observed coastline or a water classification.

## The paper reference and calculated paths

[Park et al., Figure 5](https://www.nature.com/articles/s43247-026-03764-w/figures/5) supplies the approximate August reference used in the recorded scenarios. The project’s source notice records CC BY NC ND 4.0 for the figure. The original image, modified figure composites and digitised boundary layers remain outside the public package pending clarification of distribution rights. Attribution alone is not being treated as permission to redistribute modified figure material.

The website displays the project’s own solver output over satellite previews, including calculated paths and their start and endpoint. It does not reproduce the paper image or draw the digitised boundary layer. These numerical paths still depend on the approximate paper reference, so they are explicitly described as conditional calculations rather than an independent reconstruction of observed penguin travel. This packaging distinction does not certify the legal status of every possible derivative use.

The complete local research output folder contains additional reference material and should not be uploaded wholesale. Public exports are selected by the website build script. Full reproduction of the Antarctic calculation requires separately supplying the reference described in the data guide, or validating a genuinely independent replacement and regenerating the results.

## Code, review evidence and operational information

The source archive contains project source code, documentation and selected reference material. No open source licence has yet been chosen for the project code, so public visibility should not be confused with an unrestricted reuse licence.

Human review is reported through aggregate outcomes. Raw identity fields and private notes are not published, and the uncertain nature of the visual assessments remains part of the report. AWS credentials, local environments and private operational material are excluded from both the repository and the site.

The public website is the accessible demonstration for visitors and judges. Its recorded Antarctic outputs and separate synthetic routing example are described in the technical report, together with the limits of what they establish.
