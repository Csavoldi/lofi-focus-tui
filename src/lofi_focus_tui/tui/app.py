from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from lofi_focus_tui.config import AppConfig, load_config
from lofi_focus_tui.domain import BackendState, BackendStatus, EnergyLevel, SessionRequest
from lofi_focus_tui.options import ENERGY_OPTIONS, FOCUS_OPTIONS, PRESET_OPTIONS, STYLE_OPTIONS
from lofi_focus_tui.tui.backend_client import BackendClient
from lofi_focus_tui.tui.themes import DEFAULT_THEME, THEMES, Theme
from lofi_focus_tui.tui.widgets import (
    DURATIONS,
    cycle_value,
    parse_style_tags,
    render_controls,
    render_history,
    render_option_guide,
    render_session,
    render_status,
)


class OptionGuideScreen(ModalScreen[None]):
    BINDINGS = [
        ("h", "app.pop_screen", "Close guide"),
        ("escape", "app.pop_screen", "Close guide"),
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(render_option_guide(self.app.active_theme), id="option-guide")


class ExportScreen(ModalScreen[None]):
    AUTO_FOCUS = "*"
    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel export"),
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("export directory:", id="export-prompt")
        yield Input(value="~/Music/lofi-focus-tui", id="export-directory")
        yield Static("", id="export-error")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            response = await self.app.backend_client.export_session(event.value)
        except Exception as exc:
            self.query_one("#export-error", Static).update(str(exc))
            return
        self.app.notify(response.message)
        self.app.pop_screen()


class LofiFocusApp(App[None]):
    AUTO_FOCUS = None
    BINDINGS = [
        ("i", "focus_prompt", "Edit prompt"),
        ("v", "toggle_vocal_mode", "Vocal mode"),
        ("escape", "blur_prompt", "Stop editing prompt"),
        ("s", "start_session", "Start"),
        ("space", "toggle_pause", "Pause/Resume"),
        ("x", "stop_session", "Stop"),
        ("r", "refresh_status", "Refresh"),
        ("1", "cycle_focus", "Focus"),
        ("p", "cycle_preset", "Music preset"),
        ("2", "cycle_duration", "Duration"),
        ("3", "cycle_energy", "Energy"),
        ("4", "cycle_style_tags", "Style"),
        ("t", "cycle_theme", "Theme"),
        ("left_square_bracket", "volume_down", "Volume down"),
        ("right_square_bracket", "volume_up", "Volume up"),
        ("comma", "rewind", "Rewind"),
        ("full_stop", "forward", "Forward"),
        ("0", "restart", "Restart"),
        ("e", "show_export", "Export"),
        ("h", "show_guide", "Guide"),
        ("q", "quit", "Quit"),
    ]
    CSS = """
    Screen {
        align: center middle;
    }
    #status, #session, #prompt, #history, #controls {
        width: 64;
        height: auto;
        margin: 1 0;
    }
    """

    def __init__(
        self,
        backend_client: BackendClient | None = None,
        config: AppConfig | None = None,
    ) -> None:
        super().__init__()
        self.backend_client = backend_client or BackendClient.from_config()
        config = config or load_config()
        self.active_theme: Theme = THEMES.get(config.theme, THEMES[DEFAULT_THEME])
        self.status = BackendStatus(
            state="idle",
            message="starting",
            backend="local",
            device="unknown",
        )
        self.focus = "deep_work"
        self.preset = "classic_lofi"
        self.duration_minutes = 30
        self.energy = EnergyLevel.STEADY
        self.style_tags = "lofi, neo_soul"
        self.prompt = ""
        self.vocal_mode = "instrumental"

    def compose(self) -> ComposeResult:
        yield Static(render_status(self.status, self.active_theme), id="status")
        yield Static(
            render_session(
                self.focus,
                self.preset,
                self.duration_minutes,
                self.energy,
                self.style_tags,
                self.prompt,
                self.vocal_mode,
                self.active_theme,
            ),
            id="session",
        )
        yield Input(value=self.prompt, max_length=512, id="prompt")
        yield Static(render_controls(self.status, self.active_theme), id="controls")
        yield Static(render_history(self.status, self.active_theme), id="history")

    async def on_mount(self) -> None:
        await self.refresh_status()
        self.set_interval(1.0, self.refresh_status)
        self.set_focus(None)

    async def refresh_status(self) -> None:
        self.status = await self.backend_client.get_status()
        self._refresh_display()

    def action_focus_prompt(self) -> None:
        self.set_focus(self.query_one("#prompt", Input))

    def action_blur_prompt(self) -> None:
        self.set_focus(None)
        self._refresh_display()

    def action_toggle_vocal_mode(self) -> None:
        self.vocal_mode = "vocals" if self.vocal_mode == "instrumental" else "instrumental"
        self._refresh_display()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "prompt":
            self._refresh_display()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "prompt":
            self.set_focus(None)
            self._refresh_display()

    def on_input_blurred(self, event: Input.Blurred) -> None:
        if event.input.id == "prompt":
            self._refresh_display()

    async def action_start_session(self) -> None:
        self.prompt = self.query_one("#prompt", Input).value.strip()
        request = SessionRequest(
            focus=self.focus,
            preset=self.preset,
            duration_minutes=self.duration_minutes,
            energy=self.energy,
            style_tags=parse_style_tags(self.style_tags),
            prompt=self.prompt,
            vocal_mode=self.vocal_mode,
            avoid_tags=["vocals"] if self.vocal_mode == "instrumental" else [],
        )
        self.status = await self.backend_client.start_session(request)
        self._refresh_display()

    async def action_toggle_pause(self) -> None:
        if self.status.state == BackendState.PAUSED:
            self.status = await self.backend_client.resume_session()
        else:
            self.status = await self.backend_client.pause_session()
        self._refresh_display()

    async def action_stop_session(self) -> None:
        self.status = await self.backend_client.stop_session()
        self._refresh_display()

    async def action_volume_down(self) -> None:
        self.status = await self.backend_client.adjust_volume(-0.1)
        self._refresh_display()

    async def action_volume_up(self) -> None:
        self.status = await self.backend_client.adjust_volume(0.1)
        self._refresh_display()

    async def action_rewind(self) -> None:
        self.status = await self.backend_client.seek(-10.0)
        self._refresh_display()

    async def action_forward(self) -> None:
        self.status = await self.backend_client.seek(10.0)
        self._refresh_display()

    async def action_restart(self) -> None:
        self.status = await self.backend_client.restart()
        self._refresh_display()

    async def action_refresh_status(self) -> None:
        await self.refresh_status()

    async def action_cycle_focus(self) -> None:
        self.focus = cycle_value(FOCUS_OPTIONS, self.focus)
        self._refresh_display()

    async def action_cycle_preset(self) -> None:
        self.preset = cycle_value(PRESET_OPTIONS, self.preset)
        self._refresh_display()

    async def action_cycle_duration(self) -> None:
        self.duration_minutes = cycle_value(DURATIONS, self.duration_minutes)
        self._refresh_display()

    async def action_cycle_energy(self) -> None:
        self.energy = cycle_value(ENERGY_OPTIONS, self.energy)
        self._refresh_display()

    async def action_cycle_style_tags(self) -> None:
        self.style_tags = cycle_value(STYLE_OPTIONS, self.style_tags)
        self._refresh_display()

    async def action_cycle_theme(self) -> None:
        names = list(THEMES)
        self.active_theme = THEMES[names[(names.index(self.active_theme.name) + 1) % len(names)]]
        self._refresh_display()

    def action_show_guide(self) -> None:
        self.push_screen(OptionGuideScreen())

    def action_show_export(self) -> None:
        self.push_screen(ExportScreen())

    def _refresh_display(self) -> None:
        self.prompt = self.query_one("#prompt", Input).value.strip()
        self.query_one("#status", Static).update(render_status(self.status, self.active_theme))
        self.query_one("#session", Static).update(
            render_session(
                self.focus,
                self.preset,
                self.duration_minutes,
                self.energy,
                self.style_tags,
             self.prompt,
                self.vocal_mode,
                self.active_theme,
            )
        )
        self.query_one("#controls", Static).update(render_controls(self.status, self.active_theme))
        self.query_one("#history", Static).update(render_history(self.status, self.active_theme))
