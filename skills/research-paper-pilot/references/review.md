# Review mode

Simulate peer review before real reviewers do. The mode runs three blind reviewers with different lenses, merges them, attacks the paper with the strongest possible rejection, and audits every number with a reader who has no context. It ends in a ranked revision roadmap, not a score. This is the third human checkpoint: the user reads the roadmap before anything is revised.

## Contents

- Why the review is blind
- Preconditions
- Step 1: assemble the review packet
- Step 2: three blind reviewers
- Step 3: the chair merge
- Step 4: the kill-argument pass
- Step 5: the zero-context numbers audit
- Step 6: mechanical checks
- Step 7: the report
- Severity scale
- Optional heavier panel
- Outputs and state updates

## Why the review is blind

A reviewer who has read the project notes fills gaps with what the authors meant, which is exactly what a real reviewer cannot do. A reviewer who sees the other reviewers' reports anchors on them. So each reviewer agent receives the manuscript, one lens, and the venue name, and nothing else. Do not hand over `PROJECT_CONTEXT.md`, `CLAIMS.md`, `LAB_LOG.md`, earlier reviews, or your own opinion of the paper's weaknesses. The same self-audit trap applies to you: the agent that wrote a draft rationalises its own phrasing, so the agent that reviews it must be a different one, and its raw findings must be shown, not summarised away.

Reviewer agents are the same model family as the author, so role separation reduces shared context but does not give independent error processes. Say this in the report header. If the user has access to a different model family, offer it for one reviewer seat and note which seat it was.

## Preconditions

- A compilable or at least readable manuscript (`paper/main.tex` or the user's named file) with its bibliography and figures.
- Numbers and citations are at least roughly frozen. If they are not, say that the review will flag churn, and proceed.
- The venue name, so reviewers judge against the right norms. If none is chosen, use "a general ML or science venue" and say so.

## Step 1: assemble the review packet

Create `paper/review/round<N>/` and copy or reference in it only:

- the manuscript text (flatten `\input` files into one file if needed; keep the labels),
- the bibliography,
- the figure files or their captions,
- the venue's reviewer form or criteria, if the user supplies it or you can fetch the official page (record the URL and date).

Strip anything the reviewers should not see: comments containing author notes, `% TODO` lines, and any acknowledgements that identify people if the venue is double blind. Record what you stripped in the round's `README`.

## Step 2: three blind reviewers

Run three agents in parallel, each from `agents/reviewer-blind.md`, each with one lens. Parallel runs matter because sequential reviewers drift toward each other's framing.

| Lens | What this reviewer attacks |
|---|---|
| Methods and statistics | Whether the evidence supports the claims: controls, baselines, sample sizes, seeds, intervals, multiple comparisons, selection of what was reported, whether a null inherits the same confound as the effect |
| Framing and novelty | Whether the contribution is new and clearly scoped relative to the closest prior work, whether the title and abstract match the body, whether the claims are strong where the evidence is weak |
| Clarity and a fresh reader | Whether a reader outside the sub-field can follow: undefined terms, missing motivation, figures that do not carry their claim, order of presentation, what a skim of abstract, figures and conclusion conveys |

Each returns a findings list (severity, location, evidence span of at most 125 characters, concrete fix) and a recommendation with reasons. No numeric score: a scalar hides which problem drove it and invites arguing with the number instead of fixing the paper. If a reviewer returns an empty or unstructured reply, treat that reviewer as failed and rerun it; do not fill in for it.

Reviewers must ground every claim about prior work in a page they opened or mark it `[unverified]`; a hallucinated "this was already done by X" wastes a revision round.

## Step 3: the chair merge

Run one agent from `agents/chair.md` on the three reports. Give it the reports and the manuscript, nothing else. It must:

1. Split bundled findings into single issues and deduplicate across reviewers.
2. Rank by severity and by how many reviewers raised the issue. Silence is not agreement: an issue raised by one reviewer in the lens that owns it still counts.
3. List real disagreements between reviewers and say which one the evidence favours, or mark the dissent unresolved. Do not average a split into a middle verdict.
4. Produce the revision roadmap: each item with severity, an obligation class (must fix, should fix, consider), the manuscript location, and a cost note (rewording, new analysis, new experiment, new data).

If any reviewer recommends reject and the chair's overall verdict is softer, state the reject recommendation in the report in so many words.

## Step 4: the kill-argument pass

Balanced weakness lists dilute the single most damaging point. This pass forces a commitment.

1. Attack. Run an agent from `agents/red-team.md` in attack mode with only the manuscript. It writes the strongest case for rejection in about 200 words, as a hostile area chair, as one argument rather than a list, citing locations.
2. Adjudicate. Run a second, fresh agent in defence mode with the manuscript and the attack memo only. It splits the memo into 3 to 7 atomic points and classifies each as answered by the current text, partially answered, or unresolved, citing the passage that answers it. A point the authors chose deliberately (a narrow scope, for instance) is at best partially answered unless the text itself justifies the choice.
3. Anything unresolved or partial that touches the headline claim goes to the top of the roadmap. Do not run the pair more than once per manuscript version; a second run on unchanged text adds no signal.

## Step 5: the zero-context numbers audit

Run an agent from `agents/numbers-auditor.md`. It receives the `.tex` files and the result files and nothing else: no notes, no earlier reviews, no summaries of what the numbers should be. It extracts each quantitative claim, traces it to a result file, and flags mismatches, rounding that goes the wrong way, best-versus-mean substitution, comparisons across different configurations, run counts that do not match, arithmetic errors in relative changes, caption-versus-table disagreements, and scope words ("all", "consistently", "always") not backed by the coverage actually tested.

Merge its mismatches into the roadmap as critical when they change a conclusion and major otherwise. Fixing them follows the revise-mode rule: the paper adapts to the result file, never the reverse.

## Step 6: mechanical checks

These need no judgement, so run them rather than asking an agent:

```
python scripts/check_numbers.py paper/main.tex --numbers paper/numbers.tex --results-dir results
python scripts/verify_citations.py paper/references.bib --out paper/review/round<N>/CITATION_REPORT.md
python scripts/prose_gate.py paper/main.tex --academic
```

Paste the raw output into the report appendix. An audit claimed without its output is not an audit. If a script cannot run, print its one-line warning in the report and continue.

## Step 7: the report

Fill `templates/REVIEW_REPORT.md` and save it as `paper/review/round<N>/REVIEW_REPORT.md`. Every finding carries severity, location, the evidence span, and a concrete fix that says what to change, not "improve clarity". Keep reviewer wording where it is specific; do not paraphrase it into vagueness. Lead the report with the kill-argument result and the critical items, because that is what the user must decide on.

Present the roadmap to the user and wait. The user decides which items to act on, which to push back on, and which to move into Limitations; record those decisions in `PROJECT_CONTEXT.md` before revising (invariant I5). Then move to revise mode.

## Severity scale

Use a per-finding impact test, never a quota of each level.

- Critical: uncorrected, this single defect invalidates a core claim or would justify rejection by itself.
- Major: materially weakens confidence in a core claim, and fixing it needs new analysis, new data or substantial rewriting.
- Minor: clarity, presentation or polish; fixable by editing.

A finding without a locatable anchor cannot be critical or major. If a reviewer asserts something is missing, the finding must say where it looked.

## Optional heavier panel

If the `academic-research-skills:academic-paper-reviewer` skill is installed and the user wants a deeper or field-configured panel, invoke it by name on the same packet, then merge its output into the roadmap through the chair step. If it cannot be loaded, say so and continue with the built-in three-lens path. Do not copy its prompts or wording into the project's files.

## Outputs and state updates

Files: `paper/review/round<N>/` containing the packet, three reviewer reports, the chair merge, the attack and adjudication memos, the numbers audit, the script outputs, and `REVIEW_REPORT.md`.

Update `PROJECT_CONTEXT.md` with the Status line and any decision the report forces. Append to `LAB_LOG.md`: "Review round <N> ran on <date>; produced <files>; decisions: <what the user chose>; open: <unresolved critical items>". End with the output contract from SKILL.md, naming `revise` as the next mode.
