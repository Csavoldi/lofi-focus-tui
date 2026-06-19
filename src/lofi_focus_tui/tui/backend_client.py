from httpx import AsyncClient, AsyncBaseTransport, HTTPError

from lofi_focus_tui.domain import BackendStatus, SessionRequest


class BackendClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8765",
        transport: AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url
        self.transport = transport

    async def get_status(self) -> BackendStatus:
        try:
            async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
                response = await client.get("/status")
                response.raise_for_status()
        except HTTPError:
            return BackendStatus(state="error", message="backend unavailable", backend="offline", device="unknown")
        return BackendStatus.model_validate(response.json())

    async def start_session(self, request: SessionRequest) -> BackendStatus:
        try:
            async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
                response = await client.post("/sessions", json=request.model_dump(mode="json"))
                response.raise_for_status()
        except HTTPError:
            return BackendStatus(state="error", message="backend unavailable", backend="offline", device="unknown")
        return BackendStatus.model_validate(response.json())
