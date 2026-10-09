# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog, and versions follow semantic versioning.

## Unreleased

Readability: a paper that reads without a glossary.

- New invariant I11 and style rules W73 to W77: plain words before coined names, no letter codes in prose, each condition explained by its role where it enters, words before numbers, lists only for parallel items, each caveat stated once, and provenance kept in the repository rather than the prose.
- `references/glossary-and-plain-language.md` rewritten around the no-glossary standard, with a name budget, the explain-by-role pattern, a worked example and a cold-read test.
- `prose_gate.py`: M11 reader load (label codes, coined names and acronyms against `--term-budget`, with `--allow-terms`), M12 number density per sentence and paragraph, M13 lists of short fragments in body sections.
- `check_submission.py`: stub sections, long verbatim blocks of pasted output, overfull boxes from the compile log, and `[NUM: ...]`, `[unverified]` and `\cite{TODO_...}` markers.
- New catalog rows S17 to S19 (list standing in for an argument, private vocabulary, number dump); S6 now keeps the sentence that ties numbers to their claim.
- Pre-registered and post hoc labels are given once per result, where it is first reported. Every mode's reply opens with two or three sentences on where the project stands.
- `submit` renders and inspects every page; a plain-language task eval was added.
- CHANGELOG now counts fifteen reference files.

Correctness: fixes from the file-by-file review.

- `verify_rewrite.py` keeps exponents, fails by default on lost or moved negations and lost hedges or approximators, and no longer reads sentence-initial words as proper nouns. I7 now says what the script checks rather than claiming proof.
- `check_numbers.py`, `verify_citations.py`, `check_submission.py`, `check_skill.py`, `inventory_project.py`, `transcripts_digest.py` and `prose_gate.py`: the confirmed bugs from the review are fixed (biblatex citations, duplicate and case-only bib keys, whole-surname author matching, year filtering, one-decimal table values, `--include-parents`, non-UTF-8 filenames, a 70-fold speed-up on large projects, and more; see the commit log).
- `check_skill.py` warns when the version differs across SKILL.md and the plugin manifests, and when a document names a script that does not exist.
- One claim vocabulary: evidence verdicts map onto the status ladder, `hypothesis.md` holds the only verb table, and the CLAIMS template gains Type, Falsifier, Verdict and In paper columns.
- Contradictions resolved across humanize, style rules, the pattern catalog, review, revise, submit, litreview and the templates; humanize never adds a fact or changes claim strength.
- Script commands in every reference read `python3 <skill>/scripts/...`; I10 no longer requires `python`.
- Evals: a write-mode positive, a two-mode "ask" case, genuine near misses, and unambiguous task setups. The plugin manifests drop the redundant `skills` arrays.

## 0.1.0

Initial release.

- One router skill, `research-paper-pilot`, with ten modes: understand, hypothesis, litreview, evidence, figures, write, humanize, review, revise, submit.
- Three-layer model: the skill, an optional author profile, and a per-project `PROJECT_CONTEXT.md` that serves as cross-session memory.
- Fifteen reference files, nine templates, six blind-subagent prompt templates.
- Eight stdlib-only Python scripts: project inventory, transcript digest, number check, citation verification, prose gate, rewrite verification, submission check, and a maintainer self-check.
- Plugin and marketplace manifests for Claude Code; layout compatible with `npx skills add`.
- Trigger evals (10 positive, 10 near-miss) and 3 task evals in `evals/evals.json`.
