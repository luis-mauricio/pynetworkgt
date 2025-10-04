"""Raster thresholding utilities used in the digitising workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Tuple

import numpy as np

try:  # pragma: no cover
    import rasterio
except ImportError:  # pragma: no cover
    rasterio = None

from skimage.color import rgb2gray
from skimage.filters import threshold_local, threshold_otsu
from skimage.util import img_as_float, invert
from skimage.morphology import disk
from skimage.filters.rank import modal, threshold_percentile, otsu
from skimage.util import img_as_ubyte


ThresholdMethod = Literal["otsu", "adaptive", "percentile"]
AdaptiveMethod = Literal["gaussian", "mean", "median"]


@dataclass
class ThresholdOptions:
    """Options controlling thresholding behaviour."""

    method: ThresholdMethod = "otsu"
    invert: bool = False
    block_size: float = 0.0
    adaptive_method: AdaptiveMethod = "gaussian"
    modal_blur: float = 0.0
    percentile: float = 0.05


@dataclass
class ThresholdResult:
    array: np.ndarray
    transform: Optional[Tuple[float, float, float, float, float, float]] = None


DEFAULT_THRESHOLD_OPTIONS = ThresholdOptions()


def threshold_array(array: np.ndarray, *, options: Optional[ThresholdOptions] = None) -> np.ndarray:
    """Apply thresholding to a numpy array following the legacy plugin logic."""

    if array.ndim not in (2, 3):
        raise ValueError("Input array must be 2D or 3D (grayscale or RGB)")

    opts = options or DEFAULT_THRESHOLD_OPTIONS

    grayscale = _to_grayscale(array)
    grayscale = img_as_float(grayscale)

    if opts.invert:
        grayscale = invert(grayscale)

    block_size = int(opts.block_size)
    if block_size % 2 == 0 and block_size > 0:
        block_size += 1

    if opts.method == "otsu":
        binary = _threshold_otsu(grayscale, block_size)
    elif opts.method == "adaptive":
        binary = _threshold_adaptive(grayscale, block_size, opts.adaptive_method)
    elif opts.method == "percentile":
        binary = _threshold_percentile(grayscale, block_size, opts.percentile)
    else:  # pragma: no cover
        raise ValueError(f"Unknown thresholding method: {opts.method}")

    if opts.modal_blur > 0:
        radius = int(opts.modal_blur)
        if radius % 2 == 0:
            radius += 1
        binary = modal(binary.astype(np.uint8), disk(radius))
        binary = (binary > 1).astype(np.uint8)

    return binary.astype(np.uint8)


def threshold_raster(
    path: Path,
    *,
    band: int = 1,
    options: Optional[ThresholdOptions] = None,
) -> ThresholdResult:
    """Threshold a raster file, returning the binary array + affine transform."""

    if rasterio is None:  # pragma: no cover
        raise RuntimeError("rasterio is required to threshold rasters from disk")

    with rasterio.open(path) as dataset:
        array = dataset.read() if dataset.count > 1 else dataset.read(1, out_dtype=np.float32)
        transform = dataset.transform
    binary = threshold_array(array, options=options)
    return ThresholdResult(array=binary, transform=(transform.a, transform.b, transform.c, transform.d, transform.e, transform.f))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_grayscale(array: np.ndarray) -> np.ndarray:
    if array.ndim == 2:
        return array
    if array.ndim == 3 and array.shape[0] in (3, 4):
        arr = np.moveaxis(array, 0, -1)
        return rgb2gray(arr)
    if array.ndim == 3 and array.shape[-1] in (3, 4):
        return rgb2gray(array)
    raise ValueError("Unsupported raster shape for grayscale conversion")


def _threshold_otsu(grayscale: np.ndarray, block_size: int) -> np.ndarray:
    if block_size > 0:
        image = img_as_ubyte(grayscale)
        thresh = otsu(image, disk(block_size))
        binary = image < thresh
    else:
        thresh = threshold_otsu(grayscale)
        binary = grayscale < thresh
    return binary.astype(np.uint8)


def _threshold_adaptive(
    grayscale: np.ndarray,
    block_size: int,
    adaptive_method: AdaptiveMethod,
) -> np.ndarray:
    if block_size <= 0:
        height, width = grayscale.shape
        block_size = int((height * 0.01) * (width * 0.01))
        if block_size % 2 == 0:
            block_size += 1
    local_thresh = threshold_local(grayscale, block_size=block_size, method=adaptive_method)
    binary = grayscale < local_thresh
    return binary.astype(np.uint8)


def _threshold_percentile(grayscale: np.ndarray, block_size: int, percentile: float) -> np.ndarray:
    if block_size <= 0:
        height, width = grayscale.shape
        block_size = int((height * 0.01) * (width * 0.01))
        if block_size % 2 == 0:
            block_size += 1
    image = img_as_ubyte(grayscale)
    thresh = threshold_percentile(image, disk(block_size), p0=percentile)
    binary = image > thresh
    return binary.astype(np.uint8)

