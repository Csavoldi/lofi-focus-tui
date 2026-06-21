from lofi_focus_tui.backend import tasks as task_module
from lofi_focus_tui.backend.tasks import GenerationTask
from lofi_focus_tui.domain import BackendState, BackendStatus


def test_generation_task_defaults_to_planning_status():
    task = GenerationTask(task_id="task-1", session_id="session-1")

    assert task.state == BackendState.PLANNING
    assert task.message == "planning"
    assert task.progress == 0.0


def test_generation_task_update_clamps_progress_below_zero():
    task = GenerationTask(task_id="task-1", session_id="session-1")

    task.update(BackendState.GENERATING, "working", -0.25)

    assert task.state == BackendState.GENERATING
    assert task.message == "working"
    assert task.progress == 0.0


def test_generation_task_update_clamps_progress_above_one():
    task = GenerationTask(task_id="task-1", session_id="session-1")

    task.update(BackendState.GENERATING, "working", 1.5)

    assert task.state == BackendState.GENERATING
    assert task.message == "working"
    assert task.progress == 1.0


def test_generation_task_update_changes_updated_at(monkeypatch):
    task = GenerationTask(task_id="task-1", session_id="session-1")
    original_updated_at = task.updated_at
    monkeypatch.setattr(task_module, "monotonic", lambda: original_updated_at + 1.0)

    task.update(BackendState.GENERATING, "working", 0.5)

    assert task.updated_at == original_updated_at + 1.0


def test_backend_status_accepts_backend_state_and_serializes_state_as_string():
    status = BackendStatus(
        state=BackendState.GENERATING,
        message="working",
        active_task_id="task-1",
        progress=0.5,
    )

    assert status.state == BackendState.GENERATING
    assert status.model_dump(mode="json")["state"] == "generating"
