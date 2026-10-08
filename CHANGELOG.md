# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog, and versions follow semantic versioning.

## 0.1.0

Initial release.

- One router skill, `research-paper-pilot`, with ten modes: understand, hypothesis, litreview, evidence, figures, write, humanize, review, revise, submit.
- Three-layer model: the skill, an optional author profile, and a per-project `PROJECT_CONTEXT.md` that serves as cross-session memory.
- Fourteen reference files, nine templates, six blind-subagent prompt templates.
- Eight stdlib-only Python scripts: project inventory, transcript digest, number check, citation verification, prose gate, rewrite verification, submission check, and a maintainer self-check.
- Plugin and marketplace manifests for Claude Code; layout compatible with `npx skills add`.
- Trigger evals (10 positive, 10 near-miss) and 3 task evals in `evals/evals.json`.
