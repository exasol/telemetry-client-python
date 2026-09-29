# 0.2.1 - 2026-09-28

## Summary

Fix of threading block at the process exit. Fixes `setup()` logic of reconfiguration (semi-private API).

## Bugs

- #10: Threading blocks at python exit
- Setup logic was wrong in one of tests.
