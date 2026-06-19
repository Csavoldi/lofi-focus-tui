from textual.app import App, ComposeResult
from textual.widgets import Static


class LofiFocusApp(App[None]):
    CSS = """
    Screen {
        align: center middle;
    }
    #status {
        width: 64;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            "focus: deep work       30:00 remaining\n"
            "sound: lofi / neo soul\n"
            "state: idle            backend: local\n"
            "energy: steady",
            id="status",
        )
