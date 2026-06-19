from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.mock import MockModelAdapter


def test_start_session_generates_playing_status():
    manager = SessionManager(model=MockModelAdapter())
    status = manager.start_session(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            style_tags=["lofi"],
            avoid_tags=["vocals"],
        )
    )

    assert status.state == "playing"
    assert status.active_session_id is not None
    assert status.backend == "mock"
