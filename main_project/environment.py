import numpy as np
from rasterio.features import rasterize

def apply_surface_annotation(labels, geometry, class_code, transform):
    if class_code not in (2, 3):
        raise ValueError("surface class must be 2 or 3")

    annotation_mask = rasterize(
        shapes=[(geometry, 1)],
        out_shape=labels.shape,
        transform=transform,
        fill=0,
        dtype="uint8",
    ).astype(bool)

    unknown_pixels = labels == 0
    writable_pixels = annotation_mask & unknown_pixels

    updated_labels = labels.copy()
    updated_labels[writable_pixels] = class_code

    change_count = int(np.count_nonzero(writable_pixels))

    return updated_labels, change_count