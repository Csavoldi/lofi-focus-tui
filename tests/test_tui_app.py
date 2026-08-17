from enum import Enum

import pytest
from textual.widgets import Input

from lofi_focus_tui.domain import BackendStatus, ExportResponse
from lofi_focus_tui.options import (
    ENERGY_OPTIONS,
    FOCUS_OPTIONS,
    PRESET_OPTIONS,
    STYLE_OPTIONS,
)
from lofi_focus_tui.tui import app as app_module
from lofi_focus_tui.tui import widgets as widgets_module
from lofi_focus_tui.tui.app import LofiFocusApp
from lofi_focus_tui.tui.widgets import DURATIONS, prompt_summary, render_session


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


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("", "(category-generated)"),
        ("  \n\t", "(category-generated)"),
        ("  warm piano  ", "warm piano"),
        ("é" * 80, "é" * 80),
        ("x" * 81, f"{'x' * 77}..."),
    ],
)
def test_prompt_summary_strips_and_limits_prompt(prompt, expected):
    assert prompt_summary(prompt) == expected


def test_render_session_includes_prompt_summary_and_vocal_mode():
    rendered = render_session(
        "deep_work", "classic_lofi", 30, "steady", "lofi, neo_soul",
        "  warm piano  ", "instrumental",
    )

    assert "prompt: warm piano" in rendered
    assert "mode: instrumental" in rendered


@pytest.mark.asyncio
async def test_tui_composes_blurred_prompt_editor_with_max_length():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        prompt = pilot.app.query_one("#prompt", Input)

        assert prompt.max_length == 512
        assert prompt.value == ""
        assert pilot.app.focused is None


@pytest.mark.asyncio
async def test_tui_prompt_focus_lifecycle_preserves_editor_value():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        prompt = pilot.app.query_one("#prompt", Input)
        await pilot.press("i")
        assert pilot.app.focused is prompt

        await pilot.press("space", "space", *"freeform", "space", *"idea", "space", "space")
        value = prompt.value
        await pilot.press("escape")
        assert pilot.app.focused is None
        assert prompt.value == value

        await pilot.press("i")
        await pilot.press("enter")
        assert pilot.app.focused is None
        assert prompt.value == value
        assert "prompt: freeform idea" in str(pilot.app.query_one("#session").render())


@pytest.mark.asyncio
async def test_tui_focused_command_keys_edit_prompt_without_actions():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.press("i")
        await pilot.press(*"sv1p234")

        assert pilot.app.query_one("#prompt", Input).value == "sv1p234"
        assert backend_client.requests == []
        assert pilot.app.vocal_mode == "instrumental"
        assert pilot.app.focus == "deep_work"
        assert pilot.app.preset == "classic_lofi"


@pytest.mark.asyncio
async def test_tui_unfocused_command_keys_dispatch_actions():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.press("s")
        await pilot.press("v", "1", "p", "2", "3", "4")

    assert backend_client.started is True
    assert pilot.app.vocal_mode == "vocals"
    assert pilot.app.focus == "reading"
    assert pilot.app.preset == "neo_soul"
    assert pilot.app.duration_minutes == 45
    assert pilot.app.energy == "high"
    assert pilot.app.style_tags == "ambient, tape"


@pytest.mark.asyncio
async def test_tui_prompt_summary_refreshes_from_editor_value():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        prompt = pilot.app.query_one("#prompt", Input)
        await pilot.press("i")
        await pilot.press("space", "space", *"freeform", "space", *"idea", "space", "space")
        assert "prompt: freeform idea" in str(pilot.app.query_one("#session").render())

        await pilot.press("escape")
        await pilot.app.action_cycle_focus()
        await pilot.app.refresh_status()

        assert prompt.value == "  freeform idea  "
        assert "prompt: freeform idea" in str(pilot.app.query_one("#session").render())


@pytest.mark.asyncio
async def test_tui_prompt_input_max_length_reaches_request_limit():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.press("i")
        prompt = pilot.app.query_one("#prompt", Input)
        for _ in range(513):
            prompt.insert_text_at_cursor("x")
        assert prompt.value == "x" * 512
        await pilot.press("enter")
        await pilot.press("s")

    assert backend_client.requests[0].prompt == "x" * 512


@pytest.mark.asyncio
async def test_tui_start_request_uses_stripped_prompt_and_vocal_mode():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        prompt = pilot.app.query_one("#prompt", Input)
        prompt.value = "  late night  "
        await pilot.app.action_start_session()
        await pilot.press("v")
        await pilot.app.action_start_session()

    instrumental, vocal = backend_client.requests
    assert instrumental.prompt == "late night"
    assert instrumental.vocal_mode == "instrumental"
    assert instrumental.avoid_tags == ["vocals"]
    assert vocal.prompt == "late night"
    assert vocal.vocal_mode == "vocals"
    assert vocal.avoid_tags == []


@pytest.mark.asyncio
async def test_tui_prompt_editor_value_survives_category_changes():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        prompt = pilot.app.query_one("#prompt", Input)
        prompt.value = "  freeform idea  "
        await pilot.app.action_cycle_focus()

        assert prompt.value == "  freeform idea  "
        assert "prompt: freeform idea" in str(pilot.app.query_one("#session").render())


class FakeBackendClient:
    def __init__(self) -> None:
        self.started = False
        self.paused = False
        self.resumed = False
        self.stopped = False
        self.volume_deltas = []
        self.seek_seconds = []
        self.restarted = False
        self.exported_directories = []
        self.export_error = None
        self.status_calls = 0
        self.requests = []
        self.statuses = [
            BackendStatus(state="idle", message="ready", backend="mock", device="cpu")
        ]

    async def get_status(self) -> BackendStatus:
        self.status_calls += 1
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

    async def adjust_volume(self, delta: float) -> BackendStatus:
        self.volume_deltas.append(delta)
        return BackendStatus(state="playing", message="playing", backend="mock", device="cpu")

    async def seek(self, seconds: float) -> BackendStatus:
        self.seek_seconds.append(seconds)
        return BackendStatus(state="playing", message="playing", backend="mock", device="cpu")

    async def restart(self) -> BackendStatus:
        self.restarted = True
        return BackendStatus(state="playing", message="playing", backend="mock", device="cpu")

    async def export_session(self, directory: str) -> ExportResponse:
        self.exported_directories.append(directory)
        if self.export_error:
            raise RuntimeError(self.export_error)
        return ExportResponse(
            message="session exported",
            audio_path=f"{directory}/audio.wav",
            metadata_path=f"{directory}/metadata.json",
        )


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


@pytest.mark.asyncio
async def test_tui_renders_string_values_after_legacy_enum_cycles(monkeypatch):
    class LegacyValue(str, Enum):
        READING = "reading"
        NEO_SOUL = "neo_soul"
        AMBIENT_TAPE = "ambient, tape"

    cycled_values = iter(
        (LegacyValue.READING, LegacyValue.NEO_SOUL, LegacyValue.AMBIENT_TAPE)
    )
    monkeypatch.setattr(app_module, "cycle_value", lambda *_: next(cycled_values))
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        await pilot.press("1")
        await pilot.press("p")
        await pilot.press("4")
        text = str(status_text(pilot.app))

    assert (
        "focus: reading" in text
        and "preset: neo_soul" in text
        and "style: ambient, tape" in text
    )


def test_tui_registers_main_and_help_bindings():
    keys = {binding[0] for binding in LofiFocusApp.BINDINGS}

    assert keys == {
        "i", "v", "escape", "1", "p", "2", "3", "4", "s", "space", "x", "r", "q", "h",
        "left_square_bracket", "right_square_bracket", "comma", "full_stop", "0", "e",
    }


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
async def test_tui_playback_keys_call_backend_controls():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        pilot.app.status = BackendStatus(
            state="playing", message="playing", backend="mock", device="cpu"
        )
        await pilot.press("]", "[", ".", ",", "0")

    assert backend_client.volume_deltas == [0.1, -0.1]
    assert backend_client.seek_seconds == [10.0, -10.0]
    assert backend_client.restarted is True


@pytest.mark.asyncio
async def test_tui_export_modal_submits_default_directory():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.press("e")
        assert pilot.app.screen is not pilot.app.default_screen
        await pilot.press("enter")

    assert backend_client.exported_directories == ["~/Music/lofi-focus-tui"]


@pytest.mark.asyncio
async def test_tui_export_modal_keeps_open_on_error_and_closes_on_escape():
    backend_client = FakeBackendClient()
    backend_client.export_error = "permission denied"
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.press("e")
        await pilot.press("enter")
        assert pilot.app.screen is not pilot.app.default_screen
        assert "permission denied" in str(pilot.app.screen.query_one("#export-error").render())
        await pilot.press("escape")
        assert pilot.app.screen is pilot.app.default_screen


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


@pytest.mark.asyncio
async def test_tui_option_guide_renders_every_shared_catalog_description():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        await pilot.press("h")
        guide = pilot.app.screen
        text = str(guide.query_one("#option-guide").render())

    assert guide is not pilot.app.default_screen
    for catalog in (FOCUS_OPTIONS, PRESET_OPTIONS, ENERGY_OPTIONS, STYLE_OPTIONS):
        for option in catalog.values():
            assert option.description in text


@pytest.mark.asyncio
async def test_tui_option_guide_blocks_main_controls_and_backend_calls():
    backend_client = FakeBackendClient()
    app = LofiFocusApp(backend_client=backend_client)

    async with app.run_test() as pilot:
        await pilot.press("h")
        selections = (
            pilot.app.focus,
            pilot.app.preset,
            pilot.app.duration_minutes,
            pilot.app.energy,
            pilot.app.style_tags,
        )
        status_calls = backend_client.status_calls
        await pilot.press("1", "p", "2", "3", "4", "s", "space", "x", "r")

    assert (
        pilot.app.focus,
        pilot.app.preset,
        pilot.app.duration_minutes,
        pilot.app.energy,
        pilot.app.style_tags,
    ) == selections
    assert backend_client.status_calls == status_calls
    assert backend_client.requests == []
    assert backend_client.started is False
    assert backend_client.paused is False
    assert backend_client.resumed is False
    assert backend_client.stopped is False


@pytest.mark.asyncio
async def test_tui_option_guide_q_quits_through_app_binding():
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        await pilot.press("h")
        assert any(binding[1] == "app.quit" for binding in pilot.app.screen.BINDINGS)
        await pilot.press("q")

    assert pilot.app._exit is True


@pytest.mark.asyncio
@pytest.mark.parametrize("close_key", ["escape", "h"])
async def test_tui_option_guide_closes_with_escape_or_h(close_key):
    app = LofiFocusApp(backend_client=FakeBackendClient())

    async with app.run_test() as pilot:
        await pilot.press("h")
        assert pilot.app.screen is not pilot.app.default_screen
        await pilot.press(close_key)
        assert pilot.app.screen is pilot.app.default_screen
