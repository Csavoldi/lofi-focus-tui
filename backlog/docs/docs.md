---
tags:
- lessons
- ace-step
- http
id: DOC-1
title: Lessons — ACE-Step HTTP integration
---

# Lessons — ACE-Step HTTP integration

## A `/v1/audio` 403 is not an allowlist problem

**Claim:** ACE-Step's REST `GET /v1/audio` has no configurable allowed-paths list. It serves a file only when the resolved path lies inside `app.state.temp_audio_dir`, which is `$ACESTEP_TMPDIR/api_audio` (default `<repo>/.cache/acestep/tmp/api_audio`). The `path` in the URL returned by `/query_result` is the **server's** absolute path, so no client-side directory change can affect whether the download succeeds. The API server CLI exposes no allowed-path flag; only the Gradio pipeline has a repeatable `--allowed-path`, and that does not apply to the REST `/v1/audio` route.

**Incident (2026-10-05):** the UAT report recorded the download 403 as a critical production blocker and recommended "add the client's cache dir to the ACE-Step server's allowed-paths configuration". No such configuration exists (`acestep/api/http/audio_route.py` compares against `temp_audio_dir` only). Re-testing on the host showed the served directory already covered the generated files; the actual reason audio was unavailable was that the service was not running at all, and no `.env` pinned the served directory.

**Action:** when a download 403 appears, (1) confirm the service is running before theorising about ACLs, (2) compare the returned path against the server's configured temp root rather than hunting for an allowlist, and (3) pin the served directory explicitly in the service's `.env` (`ACESTEP_TMPDIR=...`), which `api_server.py` loads via `load_dotenv(..., override=False)` and which is git-ignored so it survives updates.

**Useful probe:** request a non-existent file *inside* the expected directory — `404 {"detail":"Audio file not found"}` means the ACL passed and only the file is missing, while `403 "Access denied: path outside allowed directory"` means the path is genuinely outside the served directory.

## `/query_result`'s `file` field is a URL, not a path — re-wrapping it is a 403

**Claim:** `/query_result` returns each result's `file` as the **service's own download URL**, `/v1/audio?path=<urlencoded server path>`, not a bare filesystem path. A client that copies that value straight into the `path` query parameter sends `path=/v1/audio?path=C%3A%5C...`; `Path(...).resolve()` then lands outside `temp_audio_dir` and the route answers `403 {"detail":"Access denied: path outside allowed directory"}`. The ACL is not misconfigured — the request is malformed, and the 403 body is byte-identical to a genuinely-outside-path rejection, so the log's *request URL* is the only way to tell them apart.

**Incident (2026-10-06):** a UAT burst against `192.168.2.220:8001` logged ~35 repeats of `GET /v1/audio?path=%2Fv1%2Faudio%3Fpath%3D...` → 403 while, for the same task id, the app's own adapter download returned 200. The lofi client unwraps the URL (`AceStepHttpAdapter._audio_download_path`, commit `3087364`); the failing caller was the `omp` (oh-my-pi) coding agent passing the URL through verbatim (`httpx.get("/v1/audio", params={"path": "/v1/audio?path=C%3A%5C...wav"})`). Diagnosis trap: the app was suspected first, but a live adapter run (and the unit-level unwrap check) proved the client was fine — always separate "is the caller wrapping the value" from "is the path outside the served dir".

**Action:** (1) client authors must take the `path` *query parameter* out of `file`, not `file` itself; (2) on the ACE-Step host, `acestep/api/http/audio_route.py` was patched (marker `LOFI_UAT_WRAPPED_PATH_COMPAT`) to unwrap a nested `/v1/audio?path=...` or absolute-URL value before the allowed-dir check — the ACL is unchanged and still rejects genuinely outside paths (verified: wrapped-inside → 200, wrapped-outside → 403, missing-inside → 404); (3) that patch sits in a tracked upstream file, so `git status` shows `M acestep/api/http/audio_route.py` and an upstream update will drop it — the pre-patch copy is kept beside it as `audio_route.py.bak-lofi-uat-20261006`.

**Useful probes:** `curl -G --data-urlencode "path=/v1/audio?path=C:\Users\Clem\ACE-Step-1.5\.cache\acestep\tmp\api_audio\<id>.wav" http://HOST:8001/v1/audio` must return 200, while the same wrapped form pointing at `C:\Users\Clem\Documents\nope.wav` must still return 403. The service log is written as **UTF-16**, so convert it (`iconv -f UTF-16 -t UTF-8`) before grepping; uvicorn's access lines are the only place the *requested* `path` value is visible.

## Follow-up traps: `/C:/` drive paths and keeping the service alive

- `/C:/Users/...` (a leading slash before the drive letter) is a *second* 403 shape: on Windows `Path("/C:/Users/...").resolve()` yields the drive-relative `C:Users\...`, not `C:\Users\...`. The route now also drops a single leading `/` or `\` before `X:` (marker `LOFI_UAT_DRIVE_SLASH_COMPAT`), still gated by the allowed-dir check.
- The operator's `start_api_server.bat` can fail with "Both online and offline modes failed" when `uv` cannot resolve online, even though `uv run --offline` works. The API runs without `uv` via `C:\Users\Clem\ACE-Step-1.5\.venv\Scripts\acestep-api.exe --host 0.0.0.0 --port 8001` (with `ACESTEP_TMPDIR` set). Processes detached from an SSH session are torn down when the session closes, so a durable host needs a Windows scheduled task — `ACE-Step API (lofi UAT)` runs `\.cache\run_api_direct.ps1` on demand and keeps the API up across sessions.
