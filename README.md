# research-paper-pilot

A skill for AI coding agents that takes a research project, meaning code, result files, notes, git history and agent transcripts, to a submitted academic paper. It works in any field and on any project. It is built for the common situation where an agent did much of the experimental work over many sessions, and you now have to understand it all well enough to write it up honestly.

## Contents

- What it is
- Install
- A 60-second tour
- The three-layer model
- The output contract
- FAQ
- Licence and attribution

## What it is

One skill, ten modes. Each mode has a reference file the agent reads first, and each ends by recording what it did in a project file, so the next session picks up where the last one stopped.

| Mode | What it does |
|---|---|
| `understand` | Reconstructs the project from files, git history and transcripts, then explains it in plain language. |
| `hypothesis` | Sharpens the research question and the claims, and assigns each claim an honest strength. |
| `litreview` | Searches, verifies and summarises prior work; checks for scoops; builds a clean bibliography. |
| `evidence` | Turns results into a claims ledger; checks statistics; guards every number. |
| `figures` | Plans one figure per claim and writes a generator script for each. |
| `write` | Drafts the paper in an order that works, section by section. |
| `humanize` | Edits AI-sounding prose in academic register and proves that no fact changed. |
| `review` | Runs blind reviewer agents, a chair, and a hostile area-chair pass. |
| `revise` | Parses reviewer comments and builds the response letter and the change trail. |
| `submit` | Runs the pre-submission checklist: anonymity, references, page limits, disclosures. |

What makes it different from a general writing prompt is a short list of invariants that hold in every mode: every number traces to a result file, every citation is verified or marked `[VERIFY]`, claim strength follows evidence strength, pre-registered and post hoc results are labelled, and reviewer agents stay blind. The full list is in `skills/research-paper-pilot/SKILL.md`.

## Install

The commands below point at the public repository `punctualprocrastinator/research-paper-pilot`. If you fork it, replace the owner here and in `.claude-plugin/marketplace.json`.

### 1. With the skills CLI

```
npx skills add punctualprocrastinator/research-paper-pilot
```

The CLI finds `skills/research-paper-pilot/SKILL.md` and installs it for the agents you select. Add `-g` for a global install.

### 2. As a Claude Code plugin

```
claude plugin marketplace add punctualprocrastinator/research-paper-pilot
claude plugin install research-paper-pilot@research-paper-pilot
```

### 3. By hand

Copy the folder `skills/research-paper-pilot` into your agent's skills directory:

| Agent | Global location | Project location |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Codex | `~/.codex/skills/` | `.agents/skills/` |

Requirements: Python 3.9 or newer on your path as `python`, for the scripts. They use only the standard library. Network access is needed only for online citation verification.

## A 60-second tour

The project in these examples is invented: a study of whether label smoothing improves calibration under distribution shift, with "arm A" (smoothed) and "arm B" (baseline).

**understand**

> You: I inherited this repo from three months of agent sessions. What is it?
> Agent: Runs the inventory, reads the README and `RESULTS.md`, scans git history, then asks one question: "Was arm B ever trained with the shifted validation set, or only evaluated on it?" Writes `paper/PROJECT_CONTEXT.md` and a plain-language explainer with a dated story and a claims table. It notes that `NOTES_v2.md` is cited in the README but missing from disk.

**hypothesis**

> You: I think smoothing always helps calibration.
> Agent: "Always" is not testable as phrased. Which comparison would show you wrong, and on which shift types? It rewrites the claim as "arm A has lower expected calibration error than arm B on shifts 1 to 3", marks shift 4 as equivocal, and records the change in the hypotheses table.

**litreview**

> You: Find who else studied smoothing and calibration, and check I am not scooped.
> Agent: Splits the search by axis, logs every query, opens each page before keeping a paper, marks anything it cannot open `[unverified]`, and returns a must-cite table plus a "closest prior work" paragraph.

**evidence**

> You: Does the data support the headline?
> Agent: Reads `results/exp3.json`, checks the comparison against the criterion note written before the run, and gives a verdict of "supported, with a caveat: three seeds, one dataset". It adds the row to `CLAIMS.md` and runs the number check on the draft.

**figures**

> You: Make figure 1.
> Agent: Proposes one claim for the figure, writes `fig_calibration.py`, outputs a vector PDF in a colour-blind palette, and drafts a caption that opens with the takeaway.

**write**

> You: Draft the introduction.
> Agent: First asks you to confirm the one-sentence contribution, then writes the introduction from the context file, the claims ledger and the numbers file, citing macros instead of typing values.

**humanize**

> You: This paragraph sounds like a chatbot.
> Agent: Fixes structure before vocabulary, leaves the hedge and the citation alone, then runs the verification script and shows that nothing was dropped or added.

**review**

> You: Be harsh.
> Agent: Starts three reviewers with different lenses, none of which see your notes, merges their reports, then argues the strongest rejection and answers it point by point. You receive severity-ranked findings with locations and concrete fixes.

**revise**

> You: Reviewer 2 says the baseline is unfair.
> Agent: Puts the comment in a table, classes it as "disagreement", checks the result files, and proposes either a pushback with evidence or a concession written into the Limitations. It builds the response letter and records every change.

**submit**

> You: Ready to submit?
> Agent: Fetches the official call, records the date it checked, runs the submission checker, and lists what is left: two unresolved references and an acknowledgement that breaks anonymity.

## The three-layer model

1. **The skill** is global and fixed: the pipeline, the rules and the scripts. Everyone gets the same one.
2. **The author profile** is optional and personal: `paper/AUTHOR_PROFILE.md` holds voice samples, preferred venues, dash and hedge habits, first-person policy and citation style. The skill offers to create it once and never requires it.
3. **The project context** is per project: `paper/PROJECT_CONTEXT.md` holds the identity sentence, the question, the hypotheses (original and current), the claims pointer, venue and deadline, locked and open decisions, a glossary and a map of key files. Every mode reads it first and updates it when a decision changes. It is the memory across sessions, and the skill keeps none elsewhere.

Alongside the context file, the skill maintains `paper/CLAIMS.md` (the claims ledger), `paper/LAB_LOG.md` (an append-only dated log) and `paper/PREREG/` (criterion notes written before confirmatory runs).

## The output contract

Every mode ends with the same four parts: files written, decisions taken, open items for you, and the next recommended mode. It does not summarise the files in prose, so the reply stays short and you read the files themselves.

## FAQ

**Is this a humanizer?**
No. `humanize` is one mode of ten, and a narrow one: it removes patterns that make academic prose read as machine-made, such as inflated significance and not-X-but-Y constructions, and it protects what must not change, including hedges tied to evidence, the Methods passive, numbers, citations and defined terms. A script verifies that no fact was dropped or added. It edits style and clarity. It does not certify that a text is human-written, and it is not designed to defeat detectors, which are unreliable and sometimes biased against non-native writers.

**What about my venue's AI policy?**
Follow it. Venues differ on what must be disclosed, and the rules change between years. The `submit` mode fetches the official call, records the URL and the date it was checked, and adds disclosure to the checklist where the venue requires it. The skill never hides AI assistance, and you remain responsible for every claim, number and citation in the paper.

**Can I use it with Codex?**
The layout follows the open skills format, so it installs under `~/.codex/skills/` or `.agents/skills/`. The Claude Code specific frontmatter fields are optional and other agents ignore what they do not know. The prompt templates in `agents/` are plain markdown, so any harness that can start a fresh session or subagent can run the blind review. Where an agent cannot start subagents, run each reviewer prompt in a new session yourself, so the review stays blind. Codex support has not been tested as extensively as Claude Code.

**Does it write the paper for me?**
It drafts sections, and it stops at four checkpoints where you decide: after the project context, after the outline, after the review, and before submission. The scientific judgement stays with you.

**Does it work for non-ML fields?**
Yes. The core is field-neutral. A mechanistic-interpretability controls pack ships as an optional reference file; other fields can add their own pack in the same format.

## Licence and attribution

MIT. See `LICENSE`. The skill's text was written fresh; the ideas it builds on, and the licence of each source, are listed in `ATTRIBUTION.md`. Release notes are in `CHANGELOG.md`. Trigger and task evals are in `evals/evals.json`.
