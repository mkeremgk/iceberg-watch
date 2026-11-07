# SCAR ADD coastline reference

Retrieved 2026-10-14. Version 7.10, published 2024-11-12.
Source: https://data.bas.ac.uk/items/4ecd795d-e038-412f-b430-251b33fc880e/
DOI: 10.5285/4ecd795d-e038-412f-b430-251b33fc880e
Authors: Gerrish, Ireland, Fretwell, Cooper (2024).
Data license: CC BY 4.0. Attribution: Data from the SCAR Antarctic Digital Database, 2024.

`coastline_v7_10.gpkg` is the original download, EPSG:3031.
`coulman_surfaces.json` is a derived clipped geometry collection (custom JSON,
not RFC 7946 GeoJSON). Its explicit CRS is EPSG:32759. Geometries were selected
using the GeoPackage spatial index, made valid with Shapely 2.2.0, clipped in
3031, transformed with Rasterio, and clipped to the common SAR map bounds.
Contains 4 land, 22 ice shelf, 1 ice tongue features.

This is not a July 2025 observation or an open-water map. Source dates vary.
Ice shelf/tongue fronts may change; do not equate all mapped classes with land
or automatically use them as current route barriers. Check local correspondence
with SAR before filtering. Absence from this map does not establish open water.
