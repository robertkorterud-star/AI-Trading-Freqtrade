from atlas.intelligence.volume import (
    VolumeIntelligence,
    analyze_volume,
)


def test_low_volume():

    result = analyze_volume(
        volume=700_000,
        average_volume=1_000_000,
    )

    assert isinstance(
        result,
        VolumeIntelligence,
    )

    assert result.level == "LOW"
    assert result.volume_ratio == 0.7
    assert "below" in result.interpretation.lower()


def test_normal_volume():

    result = analyze_volume(
        volume=1_000_000,
        average_volume=1_000_000,
    )

    assert result.level == "NORMAL"
    assert result.volume_ratio == 1.0


def test_strong_volume():

    result = analyze_volume(
        volume=2_000_000,
        average_volume=1_000_000,
    )

    assert result.level == "STRONG"
    assert result.volume_ratio == 2.0
    assert "above" in result.interpretation.lower()


def test_extreme_volume():

    result = analyze_volume(
        volume=3_500_000,
        average_volume=1_000_000,
    )

    assert result.level == "EXTREME"
    assert result.volume_ratio == 3.5
    assert "exceptionally" in result.interpretation.lower()


def test_volume_ratio_can_be_supplied():

    result = analyze_volume(
        volume=2_000_000,
        average_volume=1_000_000,
        volume_ratio=1.8,
    )

    assert result.level == "STRONG"
    assert result.volume_ratio == 1.8


def test_missing_volume_is_unknown():

    result = analyze_volume(
        volume=0,
        average_volume=0,
    )

    assert result.level == "UNKNOWN"
    assert result.volume_ratio == 0.0
    assert "unavailable" in result.interpretation.lower()


def test_boundary_075_is_normal():

    result = analyze_volume(
        volume=750_000,
        average_volume=1_000_000,
    )

    assert result.level == "NORMAL"


def test_boundary_150_is_strong():

    result = analyze_volume(
        volume=1_500_000,
        average_volume=1_000_000,
    )

    assert result.level == "STRONG"


def test_boundary_300_is_extreme():

    result = analyze_volume(
        volume=3_000_000,
        average_volume=1_000_000,
    )

    assert result.level == "EXTREME"
