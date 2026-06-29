---
name: Git operations in main agent
description: Which git commands work in the main agent sandbox and which are blocked
---

## Blocked (raises exit 254 with "Destructive git operations are not allowed")
- `git commit`
- `git add`
- `git rm`, `git reset`, `git clean`, `git rebase`, `git restore`, `git checkout`
- `git push --force` / `git push -f`

## Allowed
- `git push <url> main` (no force flag) — works fine
- `git --no-optional-locks status`, `git log`, `git ls-remote` — read-only ops

## Workflow for committing + pushing
1. Write all files to disk (the platform checkpoints the full file tree).
2. Call `mark_task_complete` — the platform auto-creates a checkpoint git commit.
3. In the **next** interaction, run `git push "https://Stemesss:${GITHUB_PAT}@github.com/Stemesss/AstrumManager.git" main` to push the checkpoint commit.

**Why:** The Replit sandbox intentionally blocks destructive git ops in the main agent to prevent accidental history rewrites; checkpoints are the safe commit mechanism.
