# Hypothesis: pin down what the paper claims and how strongly

This mode produces the HYPOTHESIS section of `paper/PROJECT_CONTEXT.md` and the first rows of `paper/CLAIMS.md`. It works by questioning the user, not by announcing an answer, because the thesis has to be one the authors can defend under attack.

## Contents

- When to run this mode
- The Socratic procedure
- The hypothesis rubric
- The claim-strength ladder
- Original, evolved, current
- The one-sentence thesis tests
- When a pre-committed bar retires a headline
- Common traps
- Outputs

## When to run this mode

Run it when the user asks "what is our hypothesis", "what are we claiming", or "what is the paper about"; when `understand` found documents that disagree on the headline; when a result just failed a bar; or before outlining. Read `paper/PROJECT_CONTEXT.md` and `paper/CLAIMS.md` first. If they are missing, run `references/understand.md` first, because questions asked without that background waste the user's time.

## The Socratic procedure

Ask one question per message. Offer a draft answer built from the files so the user edits instead of composing from nothing. Wait for the reply before the next question. Order:

1. **The surprise.** "If a colleague outside the field read one sentence from this paper and said 'huh, I did not expect that', what would the sentence be?" The answer is the seed of the thesis.
2. **The belief it overturns or extends.** What do people in the field currently assume? This sets the contrast every strong paper needs.
3. **The original hypothesis.** What did the team first set out to show? Quote the first design note or first commit. Keep the wording verbatim.
4. **The test that could have failed.** For each hypothesis: what result would have refuted it? If nothing could, it is a description, not a hypothesis (see the rubric).
5. **What changed.** For each shift in wording, which result, audit or reviewer caused it? One row per shift.
6. **What survived.** Which claims passed their pre-committed bar, which passed only on the bare mean, which failed?
7. **The headline.** Offer the strongest sentence the evidence licenses. Ask whether the user agrees, and if not, which clause overstates.
8. **The scope.** Which models, datasets, populations, regimes does it hold for? Which does it not?
9. **The fallback.** If the headline were retired tomorrow, what is the paper? Name it now, while it is calm.

Stop asking when each answer is written in PROJECT_CONTEXT.md. Record the date and `[user]` beside each.

## The hypothesis rubric

Score each hypothesis against five checks. A hypothesis that fails a check gets rewritten or demoted to exploratory.

| Check | Question | Fails when |
|---|---|---|
| Falsifiable | What observed result would make you drop it? | Any outcome could be read as support |
| Names the comparison | Compared with what: a control, a null, a baseline, the other arm? | It says "X works" with no contrast |
| Names the failure mode | If it is wrong, what is true instead? | There is no rival explanation to rule out |
| Matches the lock | Is the wording the same as the pre-registered criterion? | The claim in the paper is looser or different from what was locked |
| Scoped | Which model, data and regime? | It says "language models" after testing one |

The "matches the lock" check is the one teams skip. When the paper's claim differs from the criterion note, write down both and say which one the evidence addresses.

## The claim-strength ladder

Every claim sits on exactly one rung. The rung decides which verbs the paper may use ("establishes", "shows", "suggests", "is consistent with").

| Rung | Definition | Typical wording |
|---|---|---|
| Established | Passed a bar fixed before the run, interval clear of the bar, survives at least one independent variation (new seed set, new pool, second model or arm), and has been audited adversarially | "We show" |
| Supported | Passed its bar in the main setting, but the interval touches the bar, or it was checked in one setting only, or the lock was weak (fixed in code, not registered) | "Our results indicate" |
| Equivocal | Clears one condition and not another, one direction and not the other, or the point estimate passes while the interval straddles the bar | "Mixed evidence", reported as such |
| Retired | Failed a pre-committed bar, or was overturned by an audit. Keep it in the ledger; the paper reports it as a negative finding or leaves it out with a log entry | "We did not find" |
| Exploratory | Not stated before the run; found while looking. Always labelled post hoc | "In an exploratory analysis" |

Rules for using the ladder:

- Strength follows the weakest link: a claim resting on one direction of a two-direction test is equivocal, however large the other direction is.
- Do not average away direction- or arm-specific results. Report each.
- A claim never moves up the ladder because of rewording. It moves up by new evidence, logged with the file that provides it.
- Pre-registered versus post hoc is a second axis, not a rung. A claim can be supported and post hoc. Say both.

### Claim type: what kind of statement is being made

Strength says how well the evidence holds; type says what shape the claim has. State both, because a reviewer who reads an existence proof as a systematic claim will reject it for the wrong reason.

| Type | Shape | What it needs |
|---|---|---|
| Existence | "There is at least one case where X happens" | One trustworthy, fully reported case; cherry-picking is allowed here and must be said |
| Systematic | "X happens across a range of settings" | Breadth: several models, datasets or regimes, with the range stated |
| Hedged | "There is suggestive evidence that X" | Honest wording and a named follow-up that would settle it |
| Narrow | "X holds under conditions V and W for objective Y" | The conditions stated in the claim itself, not in a footnote |
| Guarantee | "X always holds" | A proof or an exhaustive argument; rare in empirical work |

For every claim also write its falsifier: the result that would make the team retract or narrow it. A claim with no falsifier is a description, not a claim.

## Original, evolved, current

Fill this table in PROJECT_CONTEXT.md. It is the honest history of the hypothesis and the source of the paper's rigor section.

| Round or date | Hypothesis wording | What triggered the change | Evidence file | Locked in advance? |
|---|---|---|---|---|
| Original (first note) | quoted verbatim | n/a | design note | yes or no |
| Evolved 1 | | audit, null result, reviewer, new data | path | |
| Current | | | | |

Include shifts that look embarrassing. A hypothesis that was narrowed after a null result is a normal part of research, and a reviewer who finds the shift unreported will assume concealment. State the shift once, plainly, with the trigger.

## The one-sentence thesis tests

Write the thesis as one sentence with one claim, then run these tests.

- **Single-idea test.** The sentence contains no "and" that joins two separate findings. If it does, the paper has two ideas; pick one and move the other to a supporting role.
- **Deletion test.** Delete the sentence from the paper. If every result still has a reason to be there, the sentence is not the thesis. A real thesis is what the results are for.
- **Substitution test.** Replace the key noun or verb with the strongest rival explanation. If the sentence is still as defensible on your evidence, the thesis does not distinguish your story from the rival, and the missing evidence is the control that would.
- **Outsider test.** Read it to someone outside the subfield. If they cannot say what would count against it, it is too vague.
- **Evidence test.** For each clause, name the claims-ledger row that supports it. A clause without a row is an aspiration.

If two candidate headlines compete, prefer the one supported by the most-audited, most-replicated evidence over the newest or most striking one. Lead the paper with what has survived the most scrutiny.

## When a pre-committed bar retires a headline

If a result file or criterion note says "if X fails, report Y", then when X fails, do Y. Procedure:

1. State the failure in plain words in the log: which bar, which number, which margin.
2. Open the criterion note and find the fallback it named. Adopt that fallback as the paper's headline unless the user gives a reason, recorded in the log, to choose otherwise.
3. If the note named no fallback, the choice is a new decision made after seeing results. Label it post hoc, record the reason, and choose the framing the evidence supports, not the one the team prefers.
4. Move the retired claim to `retired` in the ledger. Decide with the user whether the paper reports it as a negative result; for a rigor-minded venue it usually should, because a failed pre-committed test is credible evidence of honest reporting.
5. Check every sentence in the draft that used the retired headline. List them for the write mode; do not edit the draft here.

An equivocal result (one condition passes, one fails) does not license the headline. Say so in the status line and in the ledger.

## Common traps

- **Rewriting the hypothesis to match the data.** Quote the original, show the shift, label it post hoc.
- **Choosing the headline by novelty.** Choose by audit survival.
- **Calling something pre-registered when it was only fixed in code.** Use the precise phrase for each lock strength (see `references/evidence.md`).
- **Stating the broadest scope available.** Scope to what was run.
- **Letting two framings coexist in different files.** One headline, one wording, in PROJECT_CONTEXT.md; the draft follows it.
- **Hiding the half-failed prediction.** A prediction that partly failed, stated before the run, is one of the most credible sentences a paper can contain.

## Outputs

- The HYPOTHESIS section of PROJECT_CONTEXT.md: headline claim, its rung, the original, evolved and current table, scope, fallback.
- New or updated rows in `paper/CLAIMS.md` for every claim discussed, each with status, evidence file, pre-registered flag, caveat.
- A LAB_LOG entry: "Hypothesis ran on <date>; headline now <...>; retired <...>; open <...>".
- The output contract from SKILL.md. Next recommended mode: `evidence` if any claim lacks a result file or a verdict, otherwise `litreview`.
