from textual.app import App, ComposeResult
from textual.widgets import Static

from lofi_focus_tui.domain import BackendStatus, EnergyLevel, SessionRequest
from lofi_focus_tui.tui.backend_client import BackendClient


class LofiFocusApp(App[None]):
    BINDINGS = [("s", "start_session", "Start session")]
    CSS = """
    Screen {
        align: center middle;
    }
    #status {
        width: 64;
        height: auto;
    }
    """

    def __init__(self, backend_client: BackendClient | None = None) -> None:
        super().__init__()
        self.backend_client = backend_client or BackendClient()
        self.status = BackendStatus(state="idle", message="starting", backend="local", device="unknown")

    def compose(self) -> ComposeResult:
        yield Static(self._render_status(), id="status")

    async def on_mount(self) -> None:
        self.status = await self.backend_client.get_status()
        self._refresh_status()

    async def action_start_session(self) -> None:
        request = SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            style_tags=["lofi", "neo_soul"],
            avoid_tags=["vocals"],
        )
        self.status = await self.backend_client.start_session(request)
        self._refresh_status()

    def _refresh_status(self) -> None:
        self.query_one("#status", Static).update(self._render_status())

    def _render_status(self) -> str:
        return (
            "focus: deep work       30:00 remaining\n"
            "sound: lofi / neo soul\n"
            f"state: {self.status.state:<15} backend: {self.status.backend}\n"
            "energy: steady"
        )
