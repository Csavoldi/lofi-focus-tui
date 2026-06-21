from pydantic import BaseModel, Field, field_validator

VALID_OUTPUT_FORMATS = ("wav", "mp3", "flac", "opus", "aac")


class GenerationSettings(BaseModel):
    output_format: str = "wav"
    inference_steps: int = Field(default=27, ge=1, le=100)
    guidance_scale: float = Field(default=15.0, ge=0.0, le=30.0)
    batch_size: int = Field(default=1, ge=1, le=8)
    seed: int = Field(default=-1, ge=-1)
    scheduler_type: str = "euler"
    cfg_type: str = "apg"
    omega_scale: float = Field(default=10.0, ge=0.0, le=20.0)

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, value: str) -> str:
        if value not in VALID_OUTPUT_FORMATS:
            raise ValueError(f"output_format must be one of {VALID_OUTPUT_FORMATS}")
        return value
