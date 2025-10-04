import numpy as np
import pytest

pytest.importorskip("skimage")

from pynetworkgt_app.algorithms.digitising.thresholding import (
    ThresholdOptions,
    threshold_array,
)


def test_threshold_otsu_binary_cross():
    image = np.zeros((9, 9), dtype=np.uint8)
    image[:, 4] = 255
    image[4, :] = 255

    binary = threshold_array(image, options=ThresholdOptions(method="otsu"))
    assert binary.sum() > 0


def test_threshold_adaptive_auto_block():
    image = np.linspace(0, 1, 100, dtype=float).reshape(10, 10)
    opts = ThresholdOptions(method="adaptive", block_size=0)
    binary = threshold_array(image, options=opts)
    assert binary.shape == image.shape


def test_threshold_percentile_blur():
    rng = np.random.default_rng(0)
    image = rng.random((32, 32))
    opts = ThresholdOptions(method="percentile", percentile=0.2, modal_blur=3)
    binary = threshold_array(image, options=opts)
    assert binary.dtype == np.uint8
    assert binary.shape == image.shape


def test_threshold_inversion_and_rgb():
    rgb = np.zeros((16, 16, 3), dtype=np.uint8)
    rgb[:, :] = [255, 0, 0]
    rgb[4:12, 4:12] = [0, 0, 0]
    opts = ThresholdOptions(method="otsu", invert=True)
    binary = threshold_array(rgb, options=opts)
    assert binary.sum() > 0
