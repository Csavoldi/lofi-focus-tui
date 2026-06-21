from textual.app import App, ComposeResult
from textual.widgets import Static

from lofi_focus_tui.domain import BackendState, BackendStatus, EnergyLevel, SessionRequest
from lofi_focus_tui.tui.backend_client import BackendClient
from lofi_focus_tui.tui.widgets import (
    DURATIONS,
    ENERGIES,
    PRESETS,
    STYLE_TAG_SETS,
    cycle_value,
    parse_style_tags,
    render_controls,
    render_history,
    render_session,
    render_status,
)


class LofiFocusApp(App[None]):
    BINDINGS = [
        ("s", "start_session", "Start"),
        ("space", "toggle_pause", "Pause/Resume"),
        ("x", "stop_session", "Stop"),
        ("r", "refresh_status", "Refresh"),
        ("1", "cycle_preset", "Preset"),
        ("2", "cycle_duration", "Duration"),
        ("3", "cycle_energy", "Energy"),
        ("4", "cycle_style_tags", "Style"),
        ("q", "quit", "Quit"),
    ]
    CSS = """
    Screen {
        align: center middle;
    }
    #status, #session, #history, #controls {
        width: 64;
        height: auto;
        margin: 1 0;
    }
    """

    def __init__(self, backend_client: BackendClient | None = None) -> None:
        super().__init__()
        self.backend_client = backend_client or BackendClient.from_config()
        self.status = BackendStatus(
            state="idle",
            message="starting",
            backend="local",
            device="unknown",
        )
        self.preset = "deep_work"
        self.duration_minutes = 30
        self.energy = EnergyLevel.STEADY
        self.style_tags = "lofi, neo_soul"

    def compose(self) -> ComposeResult:
        yield Static(render_status(self.status), id="status")
        yield Static(
            render_session(
                self.preset,
                self.duration_minutes,
                self.energy,
                self.style_tags,
            ),
            id="session",
        )
        yield Static(render_controls(self.status), id="controls")
        yield Static(render_history(self.status), id="history")

    async def on_mount(self) -> None:
        await self.refresh_status()
        self.set_interval(1.0, self.refresh_status)

    async def refresh_status(self) -> None:
        self.status = await self.backend_client.get_status()
        self._refresh_display()

    async def action_start_session(self) -> None:
        request = SessionRequest(
            preset=self.preset,
            duration_minutes=self.duration_minutes,
            energy=self.energy,
            style_tags=parse_style_tags(self.style_tags),
            avoid_tags=["vocals"],
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

    async def action_refresh_status(self) -> None:
        await self.refresh_status()

    async def action_cycle_preset(self) -> None:
        self.preset = cycle_value(PRESETS, self.preset)
        self._refresh_display()

    async def action_cycle_duration(self) -> None:
        self.duration_minutes = cycle_value(DURATIONS, self.duration_minutes)
        self._refresh_display()

    async def action_cycle_energy(self) -> None:
        self.energy = cycle_value(ENERGIES, self.energy)
        self._refresh_display()

    async def action_cycle_style_tags(self) -> None:
        self.style_tags = cycle_value(STYLE_TAG_SETS, self.style_tags)
        self._refresh_display()

    def _refresh_display(self) -> None:
        self.query_one("#status", Static).update(render_status(self.status))
        self.query_one("#session", Static).update(
            render_session(
                self.preset,
                self.duration_minutes,
                self.energy,
                self.style_tags,
            )
        )
        self.query_one("#controls", Static).update(render_controls(self.status))
        self.query_one("#history", Static).update(render_history(self.status))
