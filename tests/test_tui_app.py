import pytest

from lofi_focus_tui.domain import BackendStatus
from lofi_focus_tui.options import (
    ENERGY_OPTIONS,
    FOCUS_OPTIONS,
    PRESET_OPTIONS,
    STYLE_OPTIONS,
)
from lofi_focus_tui.tui import app as app_module
from lofi_focus_tui.tui import widgets as widgets_module
from lofi_focus_tui.tui.app import LofiFocusApp
from lofi_focus_tui.tui.widgets import DURATIONS


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
async def test_tui_initializes_independent_focus_and_preset():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    assert app.focus == "deep_work"
    assert app.preset == "classic_lofi"


@pytest.mark.asyncio
async def test_tui_renders_session_labels_with_descriptions():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        text = status_text(pilot.app)

    assert f"focus: deep_work — {FOCUS_OPTIONS['deep_work'].description}" in str(text)
    assert "backend: mock" in str(text)
    assert f"preset: classic_lofi — {PRESET_OPTIONS['classic_lofi'].description}" in str(text)
    assert f"energy: steady — {ENERGY_OPTIONS['steady'].description}" in str(text)
    assert f"style: lofi, neo_soul — {STYLE_OPTIONS['lofi, neo_soul'].description}" in str(text)


def test_tui_duration_options_include_short_real_generation_smoke_test():
    assert 5 in DURATIONS


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
        await pilot.press("1")
        await pilot.press("p")
        await pilot.press("2")
        await pilot.press("3")
        await pilot.press("4")
        await pilot.app.action_start_session()

    request = backend_client.requests[0]
    assert request.focus == "reading"
    assert request.preset == "neo_soul"
    assert request.duration_minutes == 45
    assert request.energy == "high"
    assert request.style_tags == ["ambient", "tape"]


@pytest.mark.asyncio
async def test_tui_keys_cycle_focus_preset_and_duration_independently():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        await pilot.press("1")
        assert pilot.app.focus == "reading"
        assert pilot.app.preset == "classic_lofi"

        await pilot.press("p")
        assert pilot.app.preset == "neo_soul"

        await pilot.press("2")
        assert pilot.app.duration_minutes == 45


def test_tui_registers_all_non_help_bindings():
    keys = {binding[0] for binding in LofiFocusApp.BINDINGS}

    assert keys == {"1", "p", "2", "3", "4", "s", "space", "x", "r", "q"}
    assert "h" not in keys


def test_tui_uses_shared_option_catalogs_without_duplicate_lists():
    for module in (app_module, widgets_module):
        assert module.FOCUS_OPTIONS is FOCUS_OPTIONS
        assert module.PRESET_OPTIONS is PRESET_OPTIONS
        assert module.ENERGY_OPTIONS is ENERGY_OPTIONS
        assert module.STYLE_OPTIONS is STYLE_OPTIONS

    for name in ("PRESETS", "ENERGIES", "STYLE_TAG_SETS"):
        assert not hasattr(widgets_module, name)


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
