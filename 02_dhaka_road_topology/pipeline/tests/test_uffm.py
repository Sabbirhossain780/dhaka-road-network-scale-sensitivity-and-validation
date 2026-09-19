"""Unit tests for UFFM fingerprint functions."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dhaka_topology.uffm import bearing_fingerprint, length_fingerprint, _safe_hist


def test_safe_hist_sums_to_one():
    h = _safe_hist([1, 2, 3, 4, 5, 6, 7, 8], n_bins=4, val_range=(0, 10))
    assert h.sum() == pytest.approx(1.0)


def test_safe_hist_uniform_fallback_for_sparse_input():
    h = _safe_hist([1, 2], n_bins=5, val_range=(0, 10))
    assert h == pytest.approx(np.ones(5) / 5)


def test_bearing_fingerprint_sums_to_one():
    nodes = pd.DataFrame({
        "node_id": [0, 1, 2, 3],
        "x_utm": [0, 10, 0, 10],
        "y_utm": [0, 0, 10, 10],
    })
    links = pd.DataFrame({
        "from_node": [0, 0, 1, 2],
        "to_node": [1, 2, 3, 3],
    })
    fp = bearing_fingerprint(nodes, links, n_bins=36)
    assert fp.sum() == pytest.approx(1.0)
    assert len(fp) == 36


def test_length_fingerprint_caps_at_max_len():
    links = pd.DataFrame({"length_m": [10, 50, 600, 1000]})
    fp = length_fingerprint(links, n_bins=10, max_len=500)
    assert fp.sum() == pytest.approx(1.0)
    # The two long segments should land in the final bin (clipped to 500).
    assert fp[-1] > 0


# ── bearing metric options (Experiments 10 & 12) ────────────────────────────

from dhaka_topology.uffm import (  # noqa: E402
    bearing_harmonics, circular_wasserstein, harmonic_distance, _bearing_distance,
)


def _grid_bearings(rot_bins: int, n_bins: int = 36) -> np.ndarray:
    """Two street families 90 degrees apart, rotated by `rot_bins` bins."""
    h = np.zeros(n_bins)
    h[rot_bins % n_bins] = 0.5
    h[(rot_bins + n_bins // 2) % n_bins] = 0.5
    return h


def test_harmonic_distance_is_rotation_invariant():
    """A rotated grid is still a grid -- distance must be ~0 at every rotation."""
    base = _grid_bearings(0)
    for shift in range(1, 36):
        assert harmonic_distance(base, _grid_bearings(shift)) == pytest.approx(0.0, abs=1e-9)


def test_linear_metric_is_not_rotation_invariant():
    """Documents the defect the default still has (Experiment 12)."""
    x = np.linspace(0, 1, 36)
    d = _bearing_distance(_grid_bearings(0), _grid_bearings(9), x, "linear")
    assert d > 0.1, "linear bearing distance should (wrongly) separate a rotated grid"


def test_circular_wasserstein_handles_wraparound():
    """Bins 0 and 35 are 5 degrees apart, not maximally distant."""
    a, b = np.zeros(36), np.zeros(36)
    a[0] = 1.0
    b[35] = 1.0
    far = np.zeros(36)
    far[18] = 1.0
    assert circular_wasserstein(a, b) < circular_wasserstein(a, far)


def test_grid_shows_in_second_harmonic_not_first():
    """Experiment 10 (C3/C4): grid = low |c1| AND high |c2|; a corridor has high |c2| too."""
    grid = bearing_harmonics(_grid_bearings(0))
    corridor = np.zeros(36)
    corridor[7] = 1.0
    corr = bearing_harmonics(corridor)
    assert grid[1] > 0.9 and grid[0] < 0.05          # grid: |c2| high, |c1| ~0
    assert corr[0] > 0.9 and corr[1] > 0.9           # corridor: BOTH high
    assert corr[0] - grid[0] > 0.5                   # |c1| is what separates them


def test_unknown_bearing_metric_raises():
    with pytest.raises(ValueError, match="unknown uffm_bearing_metric"):
        _bearing_distance(np.ones(36) / 36, np.ones(36) / 36, np.linspace(0, 1, 36), "nope")
