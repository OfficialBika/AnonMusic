# Production Hardening Notes

This branch is a proposed hardening pass. Do not merge or deploy until CI and a disposable MongoDB integration test pass.

## New configuration

- `ENABLE_EVAL=False` by default. Set true only for a trusted owner-controlled deployment.
- `EVAL_AUDIT=True` logs owner ID, message ID, runtime, and whether an error occurred. It intentionally does not log source code.
- `PLAYBACK_SKIP_LIMIT=8` bounds consecutive failed playback/download skips.
- `BROADCAST_RETRY_LIMIT=3` bounds FloodWait retries per destination.
- `BROADCAST_PROGRESS_EVERY=25` edits broadcast progress every N destinations.
- `BROADCAST_AUTO_LEAVE=False` preserves groups by default.
- `MIGRATION_DRY_RUN=True` is the safe default.
- `MIGRATION_BACKUP_DIR=migration_backups` controls where migration plans are written.

## MongoDB migration safety

The startup migration now writes a plan, validates legacy IDs, and defaults to dry-run. It does not drop or replace live collections. An explicitly acknowledged non-dry run stages normalized documents into separate `*_migration_new` collections and validates document counts. It still does not cut over live collections: that step must be reviewed and tested against a disposable database and a verified backup.

Before any manual migration:
1. Take an external MongoDB backup with your normal operations process.
2. Run with `MIGRATION_DRY_RUN=True` and inspect the generated JSON plan.
3. Test on a disposable database with a copy of production data.
4. Verify every destination document and application behavior.
5. Plan a manual cutover and restore procedure before applying to production.

The application does not claim an automatic rollback of live data because the safe startup migration deliberately leaves live collections untouched.

## Validation still required

CI compiles source, runs focused unit tests, and attempts a Docker build on Python 3.13. Before production approval, also run a disposable MongoDB integration test, verify PyTgCalls/ntgcalls compatibility and test real Telegram playback, Skip/StreamEnded race handling, FloodWait retry behavior, image/thumb generation, and Docker health reporting.
