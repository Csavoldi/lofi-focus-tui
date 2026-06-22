import pytest

from lofi_focus_tui.domain import BackendStatus
from lofi_focus_tui.tui.app import LofiFocusApp


def status_text(app: LofiFocusApp) -> str:
    parts = []
    for selector in ("#status", "#session", "#history", "#controls"):
        widget = app.query_one(selector)
        if hasattr(widget, "renderable"):
            renderable = widget.renderable
        else:
            renderable = widget.render()
        parts.append(str(renderable))
    return "\n".join(parts)


class FakeBackendClient:
    def __init__(self) -> None:
        self.started = False
        self.paused = False
        self.resumed = False
        self.stopped = False
        self.requests = []
        self.statuses = [
            BackendStatus(state="idle", message="ready", backend="mock", device="cpu")
        ]

    async def get_status(self) -> BackendStatus:
        if len(self.statuses) > 1:
            return self.statuses.pop(0)
        return self.statuses[0]

    async def start_session(self, request):
        self.started = True
        self.requests.append(request)
        return BackendStatus(
            state="generating",
            message="generating",
            active_session_id="session-1",
            active_task_id="task-1",
            backend="mock",
            device="cpu",
        )

    async def pause_session(self) -> BackendStatus:
        self.paused = True
        return BackendStatus(state="paused", message="paused", backend="mock", device="cpu")

    async def resume_session(self) -> BackendStatus:
        self.resumed = True
        return BackendStatus(state="playing", message="playing", backend="mock", device="cpu")

    async def stop_session(self) -> BackendStatus:
        self.stopped = True
        return BackendStatus(state="idle", message="stopped", backend="mock", device="cpu")


@pytest.mark.asyncio
async def test_tui_renders_session_labels():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        text = status_text(pilot.app)

    assert "focus:" in str(text)
    assert "backend: mock" in str(text)
    assert "preset: deep_work" in str(text)


@pytest.mark.asyncio
async def test_tui_start_action_updates_session_state():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.app.action_start_session()
        text = status_text(pilot.app)

    assert backend_client.started is True
    assert "state: generating" in str(text)


@pytest.mark.asyncio
async def test_tui_start_action_uses_selected_session_values():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.app.action_cycle_preset()
        await pilot.app.action_cycle_duration()
        await pilot.app.action_cycle_energy()
        await pilot.app.action_cycle_style_tags()
        await pilot.app.action_start_session()

    request = backend_client.requests[0]
    assert request.preset == "reading"
    assert request.duration_minutes == 45
    assert request.energy == "high"
    assert request.style_tags == ["ambient", "tape"]


@pytest.mark.asyncio
async def test_tui_pause_resume_and_stop_actions_call_backend():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        pilot.app.status = BackendStatus(
            state="playing", message="playing", backend="mock", device="cpu"
        )
        await pilot.app.action_toggle_pause()
        await pilot.app.action_toggle_pause()
        await pilot.app.action_stop_session()
        text = status_text(pilot.app)

    assert backend_client.paused is True
    assert backend_client.resumed is True
    assert backend_client.stopped is True
    assert "state: idle" in str(text)


@pytest.mark.asyncio
async def test_tui_refresh_status_updates_progress_text():
    backend_client = FakeBackendClient()
    backend_client.statuses = [
        BackendStatus(state="idle", message="ready", backend="mock", device="cpu"),
        BackendStatus(
            state="generating",
            message="rendering",
            backend="mock",
            device="cpu",
            progress=0.42,
        ),
    ]
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.app.refresh_status()
        text = status_text(pilot.app)

    assert "progress: 42%" in str(text)
    assert "message: rendering" in str(text)


@pytest.mark.asyncio
async def test_tui_renders_recent_history():
    backend_client = FakeBackendClient()
    backend_client.statuses = [
        BackendStatus(
            state="playing",
            message="playing",
            backend="mock",
            device="cpu",
            recent_sessions=["abc12345 deep_work", "def67890 reading *"],
        )
    ]
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        text = status_text(pilot.app)

    assert "recent:" in str(text)
    assert "abc12345 deep_work" in str(text)
    assert "def67890 reading *" in str(text)


@pytest.mark.asyncio
async def test_tui_renders_chunk_progress():
    backend_client = FakeBackendClient()
    backend_client.statuses = [
        BackendStatus(
            state="generating",
            message="generated chunk 2/5",
            backend="mock",
            device="cpu",
            progress=0.6,
            chunk_index=2,
            chunk_count=5,
        )
    ]
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        text = status_text(pilot.app)

    assert "chunks: 2/5" in str(text)


@pytest.mark.asyncio
async def test_tui_registers_periodic_status_polling():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)
    intervals = []

    def record_interval(seconds, callback, *args, **kwargs):
        intervals.append((seconds, callback.__name__))

    app.set_interval = record_interval

    async with app.run_test():
        pass

    assert intervals == [(1.0, "refresh_status")]
