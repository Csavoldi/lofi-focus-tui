from httpx import AsyncBaseTransport, AsyncClient, HTTPError

from lofi_focus_tui.config import ServerConfig, load_config
from lofi_focus_tui.domain import BackendStatus, SessionRequest


class BackendClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8765",
        transport: AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url
        self.transport = transport

    @classmethod
    def from_config(cls, config: ServerConfig | None = None) -> "BackendClient":
        server = config or load_config().server
        return cls(base_url=f"http://{server.host}:{server.port}")

    async def get_status(self) -> BackendStatus:
        try:
            async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
                response = await client.get("/status")
                response.raise_for_status()
        except HTTPError:
            return BackendStatus(
                state="error",
                message="backend unavailable",
                backend="offline",
                device="unknown",
            )
        return BackendStatus.model_validate(response.json())

    async def start_session(self, request: SessionRequest) -> BackendStatus:
        try:
            async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
                response = await client.post("/sessions", json=request.model_dump(mode="json"))
                response.raise_for_status()
        except HTTPError:
            return BackendStatus(
                state="error",
                message="backend unavailable",
                backend="offline",
                device="unknown",
            )
        return BackendStatus.model_validate(response.json())

    async def pause_session(self) -> BackendStatus:
        return await self._post_status("/sessions/pause")

    async def resume_session(self) -> BackendStatus:
        return await self._post_status("/sessions/resume")

    async def stop_session(self) -> BackendStatus:
        return await self._post_status("/sessions/stop")

    async def _post_status(self, path: str) -> BackendStatus:
        try:
            async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
                response = await client.post(path)
                response.raise_for_status()
        except HTTPError:
            return BackendStatus(
                state="error",
                message="backend unavailable",
                backend="offline",
                device="unknown",
            )
        return BackendStatus.model_validate(response.json())
