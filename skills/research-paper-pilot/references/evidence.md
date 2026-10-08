# Evidence: from results to claims a skeptic cannot easily break

This mode turns result files into a claims ledger with verdicts, decides what must be pre-registered before the next run, and fixes the way numbers travel from results to paper. It applies invariants I1, I3, I4 and I5.

## Contents

- When to run this mode
- The claims ledger
- Result-to-claim verdicts
- Pre-registration and criterion notes
- What counts as a lock
- Statistics reporting rules
- One source of numbers
- Knife-edge reporting
- Post hoc labelling
- Ten experiment-design principles
- The adversarial audit
- Outputs

## When to run this mode

Run it for "what did we find", "what are our claims", "check my numbers", "is this significant", "is this pre-registered", and before any confirmatory run. Read `paper/PROJECT_CONTEXT.md` first. If the hypothesis is unsettled, run `references/hypothesis.md` first, because verdicts need a claim to be about.

## The claims ledger

`paper/CLAIMS.md` has one row per claim. Create it from `templates/CLAIMS.md`. Columns:

| Column | Content |
|---|---|
| id | `C1`, `C2`, ... never reused, even for retired claims |
| claim | One sentence in plain words, stating direction and scope |
| type | existence, systematic, hedged, narrow, guarantee (claim types in `references/hypothesis.md`) |
| falsifier | The result that would make the team retract or narrow the claim |
| verdict | Output of the evidence check below: Supported, Partially supported, Not supported, Equivocal |
| status | established, supported, equivocal, retired, exploratory (definitions in `references/hypothesis.md`; set from the verdict by the mapping below) |
| evidence | Result file path(s) the claim rests on |
| number source | Macro name, or file plus field, for the headline number |
| test fixed in advance | Lock strength (see What counts as a lock) with where and when, or "post hoc" |
| caveat | The one limitation a hostile reader would raise first |
| in paper | main, appendix or no |
| paper location | Section or figure where the claim appears |

Rules: a claim without an evidence file is not in the ledger, it is a rumor and goes in the open list. Edit a row by changing it and logging why in `paper/LAB_LOG.md`; never delete a row. Retired claims stay, because the list of what failed shapes the rigor section.

## Result-to-claim verdicts

For each candidate claim, read the primary result file (not a summary of it) and assign one verdict:

- **Supported.** The result clears the bar that was set for it, in every condition the claim asserts, and the interval does not undercut the point estimate.
- **Partially supported.** Clears in some conditions or arms; the claim must be narrowed to those.
- **Not supported.** Fails the bar. The claim is retired or reframed as a negative result.
- **Equivocal.** The point estimate passes while the interval straddles the bar, or one direction passes and the other fails, or the readout depends on a detector choice. Report as mixed.

Procedure per claim: (1) restate the claim and the bar in one line, (2) open the file and copy the number with its interval and n, (3) compare with the bar, (4) check the denominator (a rate over discordant items is a rate over fewer items than the pool), (5) check which analysis variant the file names as primary, (6) write the verdict and the margin. Record disagreements between documents about the same number in the drift list.

### From verdict to status

The verdict is the output of this check; the status is the claim's place on the ladder in `references/hypothesis.md`. Write the verdict into the CLAIMS.md Verdict column, then set the status by this mapping:

| Verdict | Status |
|---|---|
| Supported | supported, or established if it also meets the established criteria in `references/hypothesis.md` |
| Partially supported | Narrow the claim to the part that passed, which becomes supported; record the rest as a separate row, equivocal or retired |
| Not supported | retired |
| Equivocal | equivocal |

An exploratory claim keeps the status exploratory whatever its verdict, until a confirmatory test fixed in advance gives it a new verdict.

## Pre-registration and criterion notes

A criterion note is a short document written before a confirmatory run that fixes what will count as success. Its value comes entirely from being written, and time-stamped, before the data are seen: a rule written after the result is a rationalization in a pre-registration costume. Use `templates/PREREG_criterion_note.md`.

### When to write one

Write one before any run whose outcome will support a headline claim, any run that uses held-out data for the first time, and any re-run after a change to the pipeline. Skip it for pure exploration, but then label everything from that run exploratory. Choose the weight deliberately:

- **A falsification test** carries the full note: thresholds, pool, primary metric, bar, power check, per-outcome consequences, a pre-committed fallback.
- **A validity check** may carry a lighter note: metric, bar, consequences, what will not be changed. Say in the note that it is lighter and why. If the team decides the note should not exist, delete it before reading the results, never after.

### What the note fixes

1. **Classification thresholds** for any gate that sorts items into groups. Lock the values already validated, not new ones fitted to the data the test will run on.
2. **The pool and split.** Which items, which held-out set, how many. Name the file.
3. **The primary metric**, defined exactly, including the denominator (for example "restricted to items where the two twins differ in clean behavior").
4. **The bar**, as a number, and the statistic it applies to: a bare point estimate or an interval bound. Decide this in advance, give the reason, and still report the interval. With few items, apply the bar to the interval bound, or raise the bar on the point estimate by a stated amount; never use the bare point estimate, which is most lenient exactly when n is small and its noise is largest.
5. **Direction handling.** If the claim runs both ways (removal and injection, forward and reverse), the bar must hold in both, scored against each direction's own expected sign, never pooled.
6. **Power or sample note**, run after the criteria are frozen, acting as a go/no-go gate and never as an input that can move the bar. If underpowered, the pre-written responses are: widen the pool before running, or report the result as exploratory. Loosening the bar to compensate is the one forbidden response.
7. **What each outcome licenses.** One line per outcome (clears both, clears one, clears neither), including the headline framing it permits and the fallback it triggers.
8. **What will not be changed after seeing results**: thresholds, pooling of directions, the denominator restriction, the primary metric, the split, generation length, the detector.
9. **Known limitation**, stated in advance, so a null result is read for what it can say. Example: an intervention applied only during the prompt pass shows that changing the state at that point does not change the output, not that the component is inert under every intervention.
10. **Commit hash**, filled in after committing the note and before running anything.

### Borrowed inputs

If the power check used a standard deviation or correlation borrowed from another experiment, say so in the note, and re-run the check with the real values after the first evaluation (kept separate from the confirmatory run). Report how far the real values moved the minimum detectable effect. A go decision justified by borrowed inputs is a weaker go than it looks.

### Corrections to a note

If the note contained an error (a default that implemented a stricter rule than the one argued for), correct it in a dated, visible correction block that states what was wrong and what changed. Never silently edit the criterion.

## What counts as a lock

Use exact words for the strength of each lock. Paper text must match.

| Phrase | Means | Evidence required |
|---|---|---|
| Pre-registered | Criteria written and registered externally or in an immutable, time-stamped record before the data were seen | Registry entry or commit hash with date before the run |
| Fixed in code beforehand | The threshold is in the script from a commit that predates the held-out run | Commit hash and line |
| Stated in prose beforehand | The prediction appears in a draft or note before the run | File and date; weak unless a commit proves the date |
| Post hoc | Chosen or found after seeing the data | Say so, once, where the result is reported |

Do not say "pre-registered" for the second row. Reviewers at rigor-minded venues check.

## Statistics reporting rules

- **Interval method.** Name it (percentile bootstrap, exact, Wilson) and the number of resamples. Resample the independent unit (pairs, items, prompts), not rows that share an item.
- **n everywhere.** Give the n behind each rate, especially a filtered subset. A rate over a handful of items hides behind its percentage.
- **Seeds.** State how many, and whether the claim holds across them. A single seed is a pilot.
- **Nulls inherit the confound.** See principle 3 under Ten experiment-design principles.
- **Multiple comparisons.** Count every test run on the question, not only those reported. Apply a stated correction (FDR or Bonferroni) and give the family size.
- **Effect sizes.** Report the size, not only the significance; large samples make trivial differences significant.
- **Clipping and caps.** If a metric is clipped, normalized or capped (for example a recovery fraction bounded to a range), say so and show how many items hit the cap.
- **Detector sensitivity.** If a label comes from a regex, lexicon or classifier, report how the headline moves under a reasonable alternative detector. A conclusion that flips with the detector is equivocal.
- **Scope variants.** If one test has two analysis scopes, name the primary one in the criterion note before the run, quote its interval consistently, and report the other as secondary.
- **Power.** For a null or a bar-crossing claim, say what effect the test could have detected.
- **"Significant".** Use it only with a test and its statistic.
- **Distributions, not peaks.** Report the spread across items or seeds, not the best case.

## One source of numbers

Typed numbers drift. The paper's numbers come from one place.

1. A script reads result files and writes `paper/numbers.tex`: one `\newcommand` per number, with a name that says what it is, for example `\numFlipRate`. Each macro cites its file and field in a comment.
2. Prose and captions use macros. Tables are generated or filled from the same file.
3. Each result file has a provenance sidecar (script, git hash, date, config) so a number can be traced back.
4. Run `python3 <skill>/scripts/check_numbers.py paper/main.tex --numbers paper/numbers.tex --results-dir results`. It flags literals in prose that are not macros and numbers that appear in no result file. A WARN for a missing optional input is fine; continue.
5. Never edit a result file to make a number match (invariant I3). Fix the script or the claim.

Rounding: round once, at the macro, to the precision the interval supports. Do not round a number and then compute with the rounded value.

## Knife-edge reporting

A knife edge is a result that clears a bar by a margin smaller than its own uncertainty. List every one in `CLAIMS.md` caveats and in the paper:

- Write the margin: "0.52 against a bar of 0.50, margin 0.02".
- Write the interval and whether it crosses the bar.
- If the pass is carried by a subset (the few items with a real effect), say how many and what the rest show.
- Say what the pre-declared ambiguous band was, if one existed, and whether the result sits inside it.
- Never describe a knife-edge pass as a confirmation. "Passes as specified, but is underpowered at this n" is accurate and credible.

## Post hoc labelling

Mark every post hoc item where it is reported ("found while checking X; not pre-stated"), in the ledger (`pre-registered: no`), and in the explainer table. Post hoc findings are legitimate and often the most interesting ones; unlabelled, they become the reason a reviewer distrusts the rest. Do not re-describe a post hoc finding as a corroboration of a pre-registered claim unless the paper says the reframing was made afterward.

## Ten experiment-design principles

Use these as a checklist when planning runs or judging existing ones.

1. **One-variable counterfactuals.** Build pairs that differ in exactly one factor. A within-pair difference is then caused by that factor, which no between-group comparison can promise.
2. **The system certifies its own labels.** When a label depends on what the model knows or does, derive it from the model's own sampled behavior, not from annotators' guesses about what it should find hard.
3. **Nulls inherit the confound.** Every control matches the real condition on everything except the property under test: random sets of the same size, random directions of the same norm, the same prompts. A null that differs in several ways proves little.
4. **Held-out discipline.** Data used to select a component, threshold or pool never appears in the evaluation of that choice. Write down the split before the first look.
5. **Screen cheap, verify expensive.** Use a fast approximation to propose candidates and a slow, direct intervention to confirm them. Report the screen only as a screen.
6. **State predictions first.** Write what you expect, including predictions that might fail, before running. A prediction that partly failed and was published as such is worth more than ten that were fitted.
7. **Fix criteria in code before the final run,** and call that what it is. It is stronger than nothing and weaker than registration.
8. **Triangulate methods.** Support a conclusion with at least two independent kinds of evidence (an intervention, a statistical null, an observational readout), so no single method's artifact carries it.
9. **Report what your own criteria could not decide.** When a criterion is ambiguous on your data, say so, and run the follow-up that settles it. This section is what rigor-minded reviewers remember.
10. **Audit adversarially, repeatedly.** Give an agent or colleague the job of breaking the result. Let the code, not the prose, define what each quantity means, and repeat the audit after every change.

## The adversarial audit

Before a claim is marked established:

- A reader with zero context receives the paper text and the result files only and re-derives every number (`agents/numbers-auditor.md`).
- Another reader tries to write the strongest rejection (`references/review.md`).
- Check that prose semantics match code semantics: direction labels, which arm is "source" and which "target", whether a rate is over all items or a filtered subset. Direction inversions between prose and code are a common and costly error.
- Check that no number came from memory. Every number has a macro or a file and field.

### Per-claim evidence audit

Before the paper leans on a claim, fill these fields for it and keep them in CLAIMS.md or a linked note:

- Hypotheses the evidence discriminates between (if a result is equally likely under the rival account, it is not evidence for ours).
- The strongest boring explanation: the simplest reason the result could appear with the claim being false (a bug, a confound, label leakage, a weak baseline, a selection effect). Name the test that rules it out, or record that none has been run.
- Reliability risks: seeds, variance, implementation confidence, how surprised the team would be if a rerun disagreed.
- The decisive follow-up: the single experiment whose outcome would differ most between the claim and its best rival.

### Selected examples

Qualitative examples persuade more than they prove. Whenever the paper shows an example, say how it was chosen (random, first N, chosen to illustrate). Prefer random or exhaustive selection; "chosen to illustrate" is acceptable only for existence claims, and the caption must say so. Report the share of cases the example represents.

### Inform, do not persuade

The paper's job is to let a skeptical reader reach the team's conclusion from the evidence, not to sell it. Where the evidence is thin, the text says so in the same sentence as the claim.


## Outputs

- Updated `paper/CLAIMS.md` with a verdict (Verdict column), the status that follows from it by the mapping above, evidence path, number source, pre-registered flag and caveat per row.
- Criterion notes under `paper/PREREG/<name>.md` for any run about to happen, with the commit hash placeholder.
- `paper/numbers.tex` generator status, and the output of `check_numbers.py` summarized as counts, with the disagreement list for the user.
- A LAB_LOG entry listing verdicts changed, notes written, and open items.
- The output contract from SKILL.md. Next mode: `figures` when claims are settled, `litreview` when positioning is missing.
