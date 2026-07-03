# archive/

Historical one-off backfill scripts. **Not for regular use** — superseded by `../schedules/sofascore_queue.txt` + `run_next_from_queue.sh`.

| File | When used | Status |
|---|---|---|
| `backfill_all.sh` | 2026-07-01: one-shot for all 12 seasons × 6 leagues | Superseded by queue |
| `backfill_retry.sh` | 2026-07-02: retry of 9 failed seasons with 15-min inter-league pauses | Failed — IP ban after ~3 hours |
| `backfill_retry2.sh` | 2026-07-03: retry with stricter pauses | Failed — IP ban after 2 seasons |

Both retries failed because even 2 consecutive full seasons (~50 min) triggers a 24-hour Cloudflare ban. Solution: 1 season/slot, 2 slots/day.
