# Progress

## 2026-10-12: PR #202 CI follow-up

- User-selected target: fix PR #202 using subagents.
- Merged origin/master (ad71d89, including #203) into an isolated checkout without conflicts. Original checkout and Claude worktrees retain their existing changes.
- Subagents investigate the failing Ubuntu oldest-dependency job and independently review lifecycle guards and cancellation behavior.
- Independent review found lifecycle gaps: closing in a progress callback invoked a closed nested pipeline; cross-loop closure during the final stage could finish and update a closed diagram; a stage error after immediate closure was reported as failure; and a queued completion callback reported errors after closure. Added cancellation checks, closed-diagram and closed-pipe callback guards, and deterministic regression tests. Completion callbacks still consume task exceptions, and unsuccessful runs restore source flow.
- CI investigation confirmed the previous failed job completed nbconvert successfully, then Firefox ran out of memory in Linking/Transformer across both GitHub attempts and their internal retries. This is issue #199, not the kernel race fixed by #203; its allocation source remains unresolved.
- Validation: `pixi run lint`, `pixi run lint-mypy`, and `pixi run build-js-ext` pass. `.pixi/envs/utest/bin/python -m pytest -o addopts='' -q`: 419 passed, 2 skipped. The same command in `utest-oldest`: 417 passed, 7 skipped. Both `pixi run itest-nbconvert` and `pixi run itest-oldest-nbconvert` executed all 17 notebooks. `pixi run bench-check` passes on the final patch (81 baseline counts). Eight new regression cases failed without their guards and pass with them. Final independent review is clean; 207 relevant tests pass in each dependency environment.
- Initial local pytest collection failed before editable installation. The first full run then hit an unhydrated Git LFS data archive; restoring the archive made its seven notebook tests pass on both dependency versions. No application changes were needed for these setup failures.
- Completion requires resolving final review findings and checking refreshed PR CI. Browser OOM remains tracked separately under #199.
- Lesson: distinguish Firefox OOM from kernel stalls before changing runtime code; cancellation must be checked after user callbacks and final-stage completion, not only between stages.
