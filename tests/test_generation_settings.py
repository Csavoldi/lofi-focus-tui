import pytest
from pydantic import ValidationError

from lofi_focus_tui.generation.settings import VALID_OUTPUT_FORMATS, GenerationSettings


def test_generation_settings_defaults_match_expected_values():
    settings = GenerationSettings()

    assert settings.output_format == "wav"
    assert settings.inference_steps == 27
    assert settings.guidance_scale == 15.0
    assert settings.batch_size == 1
    assert settings.seed == -1
    assert settings.scheduler_type == "euler"
    assert settings.cfg_type == "apg"
    assert settings.omega_scale == 10.0


@pytest.mark.parametrize("output_format", ["mp3", "flac", "opus", "aac", "ogg"])
def test_non_wav_output_format_raises_value_error(output_format):
    with pytest.raises(ValidationError):
        GenerationSettings(output_format=output_format)


def test_valid_output_formats_are_accepted():
    for output_format in VALID_OUTPUT_FORMATS:
        settings = GenerationSettings(output_format=output_format)

        assert settings.output_format == output_format

    assert VALID_OUTPUT_FORMATS == ("wav",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("inference_steps", 0),
        ("inference_steps", 101),
        ("batch_size", 0),
        ("batch_size", 9),
        ("omega_scale", -0.1),
        ("omega_scale", 20.1),
    ],
)
def test_numeric_bounds_reject_invalid_values(field, value):
    with pytest.raises(ValidationError):
        GenerationSettings(**{field: value})
