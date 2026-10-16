<!-- BACKLOG_MD_INSTRUCTIONS_START -->
## Backlog.md Workflow

This project uses Backlog.md task tracking for lofi-focus-tui.

### Search before creating tasks

- Use `backlog-py --cwd <repo> search "query" --plain`, `backlog-py --cwd <repo> task list --plain`, or the MCP `task_search` / `task_list` tools to find related work first.
- Create a new task only when no existing task covers the same reviewable unit: `backlog-py --cwd <repo> task create "Title" --plain`.

### Task lifecycle

- Before editing project files, link the work to a Backlog.md task.
- Keep task status current: move it to `In Progress` when work starts and mark the task Done only after verification is recorded.
- During execution, append implementation notes with important decisions, blockers, changed files, and verification commands.
- Before completion, check all relevant Acceptance Criteria and Definition of Done items, then add a Final Summary explaining what changed and why.

### Project lessons

- If `backlog/docs/lessons-*.md` files exist, list them with `backlog-py --cwd <repo> doc list lessons` and read the relevant themed file with `backlog-py --cwd <repo> doc view <path>` before starting.
- Before completing a task, if it exposed a reusable trap, costly wrong assumption, or verification constraint, record the guidance in the relevant themed lesson through the normal document workflow. Record a concise claim, the actual incident that proves it, and the resulting action, only when the guidance is reusable and evidence-backed. Most tasks produce no lesson; do not invent one to satisfy this hook.

### MCP and CLI fallback

- MCP agents should read `backlog://workflow/overview` and `backlog://docs/task-workflow`; if project discovery fails, read `backlog://init-required`.
- Prefer explicit project paths for automation: pass the MCP `project` argument, set `BACKLOG_CWD`, or use CLI `--cwd <repo>`.
- If MCP is unavailable, use the CLI fallback. For example, `backlog-py --cwd <repo> task edit <id> --status "In Progress" --plain`.
- Do not manually edit files under `backlog/` unless MCP and CLI paths are unavailable and the human explicitly approves the exception.

### Multi-agent guidance

- In multi-agent environments, prefer one shared daemon: `backlog-py daemon ensure` and verify it with `backlog-py daemon status --json`.
- Use the MCP `project_status` tool for a cheap coordination check before write-heavy work.

### Orchestration coordination

- When orchestration metadata exists, check `project_status`, `orchestration_status`, and `orchestration_eligible` before choosing work. CLI fallback: `backlog-py --cwd <repo> orchestration status --plain` and `backlog-py --cwd <repo> orchestration eligible --plain`.
- Always claim before editing with `orchestration_claim_task` and the latest expected version: `backlog-py --cwd <repo> orchestration claim <id> --actor <agent> --expected-version <version> --plain`.
- Always record files and verification commands with `orchestration_record_run` before handing off or completing work: `backlog-py --cwd <repo> orchestration record-run <id> --actor <agent> --result succeeded --summary "..." --file <path> --verification "pytest ..." --plain`.
- After verification, use `orchestration_transition_task` to transition to `review` or `triage`; do not jump directly to terminal states unless project policy allows it. CLI fallback: `backlog-py --cwd <repo> orchestration transition <id> review --actor <agent> --expected-version <version> --plain`.
- Release blocked or paused work with `orchestration_release_task`, then document the reason in run history.
- Troubleshoot stale leases with `orchestration_stale_leases`; fix version conflicts by refreshing queue/status and retrying with the latest expected version; fix malformed run history before recording new events; handle MCP discovery with an explicit `project` argument, `BACKLOG_CWD`, or CLI `--cwd`; check daemon health with `backlog-py daemon status --json`.
<!-- BACKLOG_MD_INSTRUCTIONS_END -->
