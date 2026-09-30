# Cross-session handoff protocol

Two Claude sessions work on Movement Solutions automation and cannot message each other
directly:

- **cloud**: "PracticeQ/IntakeQ API access" at claude.ai/code (this repo's author).
- **cockpit**: "Movement Solutions Cockpit repo", Remote Control on Tim's Mac, owns ms-cockpit.

This directory is the shared channel. Rules:

1. Repo `timboj55/first_one`, branch `claude/practiceq-intakeq-api-9f5a9g`. Always
   `git pull` before reading, and push right after writing.
2. Each session writes only its own file: `from-cloud.md` or `from-cockpit.md`. Append a dated
   entry at the top; never edit the other session's file.
3. An entry has three parts: **Status** (what changed), **Decisions needed** (from Tim),
   **Questions for the other session** (numbered so replies can cite them).
4. No client names, emails, phone numbers or keys. Counts and column names are fine.
5. Tim triggers a read by telling either session "check handoff". The cloud session also
   checks on its own schedule while work is active.
6. Things settled here get folded into README.md by the cloud session and into the cockpit's
   own docs by the cockpit session.
