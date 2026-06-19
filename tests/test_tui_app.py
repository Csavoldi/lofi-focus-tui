import pytest

from lofi_focus_tui.tui.app import LofiFocusApp


@pytest.mark.asyncio
async def test_tui_renders_session_labels():
    app = LofiFocusApp()

    async with app.run_test() as pilot:
        text = pilot.app.query_one("#status").content

    assert "focus:" in str(text)
