import pytest

from lofi_focus_tui.domain import BackendStatus
from lofi_focus_tui.tui.app import LofiFocusApp


class FakeBackendClient:
    def __init__(self) -> None:
        self.started = False

    async def get_status(self) -> BackendStatus:
        return BackendStatus(state="idle", message="ready", backend="mock", device="cpu")

    async def start_session(self, request):
        self.started = True
        return BackendStatus(
            state="playing",
            message="playing",
            active_session_id="session-1",
            backend="mock",
            device="cpu",
        )


@pytest.mark.asyncio
async def test_tui_renders_session_labels():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        text = pilot.app.query_one("#status").content

    assert "focus:" in str(text)
    assert "backend: mock" in str(text)


@pytest.mark.asyncio
async def test_tui_start_action_updates_session_state():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.app.action_start_session()
        text = pilot.app.query_one("#status").content

    assert backend_client.started is True
    assert "state: playing" in str(text)
