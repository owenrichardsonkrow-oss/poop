"""
Pure-math tests. These run without demoparser2 and without a demo file, so
they're the fastest way to confirm the environment works and the geometry
hasn't regressed.

    python -m pytest tests/ -v
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from demo_audit import angle_between, forward_vectors, view_delta, zscore

A = np.array


# --- forward_vectors ---------------------------------------------------------

def test_forward_origin_points_down_positive_x():
    v = forward_vectors(A(0.0), A(0.0))
    assert np.allclose(v, [1, 0, 0], atol=1e-9)


def test_forward_yaw_90_points_down_positive_y():
    v = forward_vectors(A(0.0), A(90.0))
    assert np.allclose(v, [0, 1, 0], atol=1e-9)


def test_negative_pitch_is_up():
    """CS2 convention: negative pitch looks up. If this flips, every aim-error
    number in the report is wrong."""
    v = forward_vectors(A(-90.0), A(0.0))
    assert np.allclose(v, [0, 0, 1], atol=1e-9)


def test_positive_pitch_is_down():
    v = forward_vectors(A(90.0), A(0.0))
    assert np.allclose(v, [0, 0, -1], atol=1e-9)


def test_forward_vectors_are_unit_length():
    rng = np.random.default_rng(0)
    p = rng.uniform(-89, 89, 500)
    y = rng.uniform(-180, 180, 500)
    assert np.allclose(np.linalg.norm(forward_vectors(p, y), axis=-1), 1.0)


def test_forward_vectors_broadcast_over_2d():
    p = np.zeros((7, 3))
    y = np.zeros((7, 3))
    assert forward_vectors(p, y).shape == (7, 3, 3)


# --- angle_between -----------------------------------------------------------

def test_angle_between_identical_is_zero():
    v = A([[1.0, 0.0, 0.0]])
    assert np.allclose(angle_between(v, v), 0.0, atol=1e-6)


def test_angle_between_perpendicular_is_90():
    assert np.allclose(angle_between(A([1.0, 0, 0]), A([0, 1.0, 0])), 90.0)


def test_angle_between_opposite_is_180():
    assert np.allclose(angle_between(A([1.0, 0, 0]), A([-1.0, 0, 0])), 180.0)


def test_angle_between_normalises_magnitude():
    """Vectors to targets are not unit length; magnitude must not matter."""
    a = angle_between(A([1.0, 0, 0]), A([500.0, 500.0, 0]))
    assert np.allclose(a, 45.0)


def test_angle_between_never_nans_on_parallel_input():
    """Floating point can push the dot product past 1.0 and produce NaN from
    arccos. The clip in angle_between must prevent that."""
    v = A([[0.577350269, 0.577350269, 0.577350269]])
    assert np.isfinite(angle_between(v, v)).all()


# --- view_delta --------------------------------------------------------------

def test_view_delta_wraps_around_360():
    """Yaw 0 to yaw -350 is a 10 degree movement, not 350."""
    d = view_delta(A(0.0), A(0.0), A(0.0), A(-350.0))
    assert np.allclose(d, 10.0, atol=1e-6)


def test_view_delta_180_flip():
    d = view_delta(A(0.0), A(0.0), A(0.0), A(180.0))
    assert np.allclose(d, 180.0, atol=1e-6)


def test_view_delta_combines_pitch_and_yaw():
    d = view_delta(A(0.0), A(0.0), A(-45.0), A(0.0))
    assert np.allclose(d, 45.0, atol=1e-6)


# --- zscore ------------------------------------------------------------------

def test_zscore_centres_on_mean():
    z = zscore(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert np.allclose(z.mean(), 0.0, atol=1e-9)
    assert np.allclose(z.iloc[2], 0.0, atol=1e-9)


def test_zscore_constant_series_returns_zeros_not_nan():
    """A lobby where everyone scores identically must not produce NaN, or the
    triage sum silently becomes NaN for every player."""
    z = zscore(pd.Series([3.0] * 10))
    assert np.isfinite(z).all()
    assert np.allclose(z, 0.0)


def test_zscore_handles_nan_members():
    z = zscore(pd.Series([1.0, 2.0, np.nan, 4.0]))
    assert z.notna().sum() == 3


# --- a realistic end-to-end aim-error case ----------------------------------

def test_aim_error_for_a_shooter_looking_straight_at_a_target():
    """Shooter at origin, target 1000 units down +X on flat ground. With eye
    height 64 and target point 58, the crosshair should need a slight downward
    pitch. Confirms the sign convention end to end."""
    eye = A([0.0, 0.0, 64.0])
    tgt = A([1000.0, 0.0, 58.0])
    rel = tgt - eye
    correct_pitch = np.degrees(np.arctan2(6.0, 1000.0))  # positive = down
    fwd = forward_vectors(A(correct_pitch), A(0.0))
    assert angle_between(fwd, rel) < 0.01


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
