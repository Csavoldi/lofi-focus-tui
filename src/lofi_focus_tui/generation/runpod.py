import importlib.util

from lofi_focus_tui.generation.http_ace_step import AceStepHttpAdapter


class RunPodAceStepAdapter(AceStepHttpAdapter):
    name = "runpod"

    def __init__(
        self,
        api_key: str = "",
        gpu_type: str = "NVIDIA GeForce RTX 4090",
        template_id: str = "",
        volume_id: str = "",
        auto_destroy: bool = True,
        base_url: str = "http://127.0.0.1:8001",
        timeout_seconds: float = 1800.0,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
        self.gpu_type = gpu_type
        self.template_id = template_id
        self.volume_id = volume_id
        self.auto_destroy = auto_destroy

    @property
    def available(self) -> bool:
        return importlib.util.find_spec("runpod") is not None
