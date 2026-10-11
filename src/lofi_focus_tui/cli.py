from lofi_focus_tui.config import load_config
from lofi_focus_tui.runtime import build_session_manager
from lofi_focus_tui.tui.app import LofiFocusApp


def main() -> None:
    config = load_config()
    manager = build_session_manager(config)
    LofiFocusApp(session_manager=manager, config=config).run()
