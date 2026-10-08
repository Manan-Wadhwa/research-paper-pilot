# Mode 7: Humanize (academic-register style pass)

This mode removes the habits that make a paper draft read as machine-generated, while leaving every fact, hedge, citation and number exactly as it was. It edits style and clarity. It does not certify who wrote the text, and it is not a way to avoid disclosing AI assistance.

## Contents

- What this mode does and does not do
- Preconditions
- Why the order is structure, staging, vocabulary, punctuation
- Step 0: decide whether to act, then classify each section
- Step 1: mark the protected regions
- Step 2: structure
- Step 3: staging
- Step 4: vocabulary
- Step 5: punctuation
- Step 6: verify (mandatory)
- Step 7: report and log
- Voice and the author profile
- The protections list
- The disclosure line
- Requests to beat a detector
- Optional second check

## What this mode does and does not do

Do: repair the shape and the wording of drafted prose so that it reads as one author's specific, uneven, accountable writing. Keep the meaning identical.

Do not: add a fact, drop a fact, change a number, change the strength of a claim, touch a citation, or rewrite a section the author has already made their own. Those are invariants I1, I2, I4 and I7 from `SKILL.md`; a style pass must never become a content pass in disguise.

Do not: claim afterwards that the text is "human" or "undetectable". A style edit proves nothing about authorship.

The pattern lookup table lives in `ai-patterns-academic.md`. Use its ids (C3, S5, ...) when logging. Its "Safe for papers?" column decides what may be repaired.

## Preconditions

Run this mode last, after the numbers and citations are frozen. Editing prose before then forces a second humanize pass whenever a figure or a reference changes, and each pass risks a silent fact change.

Before editing:

1. Read `paper/AUTHOR_PROFILE.md` if it exists (dash habit, hedge habit, first-person policy, never-change list). If the author gave voice samples, read one first; the sample overrides every default below.
2. Save the source text untouched beside the rewrite, for example `drafts/intro.v1.tex` next to `intro.tex`. The verification script needs both, and the author needs a way back.
3. Confirm `scripts/check_numbers.py` and `scripts/verify_citations.py` were run on this draft. If they were not, run them first or say they are outstanding.

## Why the order is structure, staging, vocabulary, punctuation

The order follows how much each layer carries and how fast each one decays.

- Classifiers trained on discourse structure alone separate human and machine prose well even when every stylistic cue is withheld, and rewriters that only scrub words barely move them. That evidence comes from fiction, so treat it as a strong hint for papers, not proof. What it supports is working on shape first.
- Word lists are model-specific and age quickly; a list-based detector tested on a different model's essays fell to near chance. Words are the weakest layer.
- Punctuation is cosmetic. Some detectors normalise dashes and quotes away before they classify.
- Surface scrubbing without a structure repair also tends to flatten sentence rhythm, which makes the prose more uniform than before.

So the order is: structure (rhythm, connective openers, preview-then-restate, forced triads, closing loop), then staging (sentence-level moves such as not-X-but-Y), then vocabulary (clusters only), then punctuation. Do not reverse it, and do not skip to vocabulary because it is easy.

A scanner run on a synthetic computer-science paper sample (abstract, methods, discussion, about 200 words in ordinary register) shows why the protections below exist. A general-purpose phrase scanner flagged a hard failure for "in conclusion", soft flags for "comprehensive" and "robust" in their plain technical senses, a "research suggests" that would carry a citation in a real paper, and the whole sample for uniform sentence length that was caused by the Methods paragraph. A structural scanner calibrated on blog prose scored two conventional connectives ("Furthermore", "Overall") at six times its human limit. A reading-grade flag fired on text no research paper could avoid. A scanner designed around regression against the source and preservation of facts passed the same sample, but its connective-opener ratio sat one paragraph from firing. Every finding that was wrong for a paper was a convention: formal connectives, scaffolding in conclusions, technical senses of ordinary words, Methods uniformity. Hence the protections list.

## Step 0: decide whether to act, then classify each section

Read the whole text before touching it, then choose one:

- **Nothing to do.** The prose already has specifics and uneven rhythm. Return it unchanged and say so in one line. A pass that always finds something damages good writing.
- **Audit only.** The author asked "does this sound like AI?" or "just flag it". Report patterns with ids and line numbers; leave the text alone. Never give a verdict on authorship; report patterns.
- **Rewrite.** The default when the author asked for a de-AI pass and the draft shows several tells.
- **Draft.** No source exists; follow the same rules while writing instead.

Then classify each section, because the layers apply differently:

| Section | Rhythm | Closing loop | Connective openers | Triads | Roadmap | Over-explaining | Notes |
|---|---|---|---|---|---|---|---|
| Abstract | advisory | allowed (it restates by design) | act | partial | n/a | partial | No em dashes; check contribution list for cliches. |
| Introduction | act | n/a | act | partial | keep one sentence | partial | Open on the gap, not on "in recent years". |
| Related work | act | n/a | partial | partial | n/a | partial | Group by approach; both-sidesism is allowed here. |
| Methods | advisory only | n/a | partial | keep | n/a | no | Passive and uniform sentences are conventions; protect. |
| Results | partial | n/a | partial | partial | n/a | partial | "This section shows" is fine; strip interpretation that belongs in Discussion. |
| Discussion | act | partial | act | partial | n/a | interprets by design | Replace restatement with mechanism or limitation. |
| Limitations | partial | n/a | partial | partial | n/a | no | Specific limitations stay specific. |
| Conclusion | partial | allowed with a new element | act | partial | n/a | partial | Must add a limitation, number or next step. |

"Advisory" means report it, do not rewrite it.

## Step 1: mark the protected regions

Before any edit, list the spans that must not change (see "The protections list"). In LaTeX, treat everything inside math, `\cite{}`, `\ref{}`, `\label{}`, `\begin{...}` environments other than prose, and all commands as inert. Work on the prose between them. The verification script will catch a slip, but marking first prevents the slip.

## Step 2: structure

Work paragraph by paragraph, whole section in view. Four to six edits per section is typical; more means the draft needs rewriting by its author, not polishing.

**Rhythm.** Measure before you edit: `python scripts/prose_gate.py <file> --academic` reports mean sentence length and its coefficient of variation. A paragraph is uniform when most sentences sit within five words of each other. Fix by merging two supporting sentences into one longer sentence, or by trimming one to its core. Rules that keep clarity intact:

- Never merge two sentences that each state a claim; never hide which condition belongs to which comparison.
- Keep any short sentence that states a claim outright. Take the variation from the supporting material around it.
- Do not create staccato. Several new very short sentences in a row is its own tell.

Example (invented). Before, four sentences of 16, 15, 14 and 15 words: "The model was evaluated on three tasks. Each task used a held-out split of the data. Accuracy was measured at every checkpoint. The scores were averaged over five seeds." After: "We evaluated the model on three tasks, each with a held-out split. Accuracy was measured at every checkpoint and averaged over five seeds." The facts are identical; the lengths now differ.

**Connective openers.** If more than a third of paragraphs open with Moreover, Furthermore or Additionally, open on the claim instead. Keep however, thus, in contrast, although and similar words that name a real relation, and never delete a connective without restoring the link in another form. Never swap one connective for another to look varied.

**Preview then restate.** Keep the single roadmap sentence in the Introduction. Remove the second preview that appears at the top of each section and the sentence that echoes a heading.

**Forced triads.** Where three items are listed by reflex, develop the strongest one or two. Keep any triad that matches three real things (three metrics, three datasets).

**Closing loop.** If the Conclusion repeats the Introduction with no new element, add one real element (a limitation, a number from the results file, a named next experiment) and cut the echo. Take the number from the numbers file, never from memory.

## Step 3: staging

Act on a single sighting for these; they are the patterns readers notice consciously. Pattern ids in brackets.

- Not-X-but-Y [S8]: state the positive claim, unless both halves carry a fact.
- One-line closers and dramatic fragments [S9]: delete.
- Run-ups and throat-clearing [S10]: delete, except the one roadmap sentence.
- Arguing with no one [C15]: cut invented objections; keep ones a reviewer actually raised.
- Borrowed authority [C4]: attach the citation key and what the source found, or cut the claim. Never invent a source; if the claim matters and the source is missing, write `[VERIFY]` and tell the author.
- Inflated significance [C1] and generic positive closers [C7]: keep the fact, drop the verdict.
- -ing riders [C3]: keep the fact, drop the rider unless a result supports it.
- Copula avoidance [V3]: use "is", "are", "has".
- Over-explaining sentences [S6]: cut, or move the interpretation to Discussion.
- Audit and defensive voice [C18]: state the design fact once, in the section where it is needed; move process detail to Methods or an appendix.

Staging repairs are small. When a repair needs a new fact, stop and ask the author.

## Step 4: vocabulary

Last and lightest. Flag clusters, not words: three or more entries from [V1] or [V2] in one paragraph justify action; a single "robust" or "landscape" does not. Keep technical senses (a robust estimator, a loss landscape, a statistically significant difference). Do not ban ordinary words that merely became more frequent, such as across, within, findings or potential.

Fix synonym cycling [V4] first, because it is the highest-value vocabulary repair in a paper: choose one term per concept and repeat it. Then filler phrases [V6], then ornamental adverbs [V8].

Never swap a predictable word for a surprising one to look less machine-like; precision beats surprise.

## Step 5: punctuation

Em dashes are capped, not banned: none in the abstract, at most one per paragraph elsewhere, and range dashes are exempt. Replace the extra ones with the punctuation that names the relation (comma, colon, parentheses, full stop). If the author profile or the venue style sets a different rate, follow it. Leave quotation marks, hyphenation of terms of art and LaTeX typography alone [P3, P4, P5]. Remove invisible or look-alike characters [P7] and any leaked markup [L3].

## Step 6: verify (mandatory)

After every rewrite, with no exceptions, run:

```
python scripts/verify_rewrite.py drafts/intro.v1.tex intro.tex
```

Add `--strict` when the author wants structural regressions to fail as well. The script compares the rewrite with the source and reports:

- **DROPPED**: a number, unit, year, proper noun, citation key, URL, quoted string or LaTeX reference present in the source and absent in the rewrite. This is a lost fact. The run fails.
- **ADDED**: the same kinds of token present in the rewrite and absent in the source. This is an invented fact, the worse error. The run fails.
- **Structural regression**: sentence-length variation and paragraph-length variance before and after. If either fell, the rewrite removed surface tells and flattened the prose beneath them. This warns (fails under `--strict`).

How to respond:

1. Any DROPPED or ADDED line: restore or remove the change, then re-run. Never explain a preservation failure away.
2. A flattening warning: re-do Step 2 for that section, merging supporting sentences and keeping short claim sentences short, then re-run.
3. Run the script on the whole section or file, not on a single sentence, so the rhythm comparison is meaningful.
4. Re-run until PASS or until only warnings you can justify remain. Two full passes is the ceiling; beyond that the edits are churning, and the right move is to hand back the remaining items to the author.

The script has no banned-word list on purpose. Grading a rewrite with the word list that guided it proves only that you followed your own instructions. If the script is missing or fails to run, print a one-line warning, do the check by hand (list every number, citation key and quoted string in both versions and compare), and say so in the report.

Also run `scripts/check_numbers.py` and `scripts/verify_citations.py` again if the author edited the file after your pass.

## Step 7: report and log

End with the output contract from `SKILL.md`: files written, decisions taken, open items, next mode. Add:

- the ids of patterns repaired per section (C3, S5, ...), as a short list;
- the verify_rewrite result (PASS or WARN lines kept verbatim);
- anything left alone on purpose and why (protected hedge, Methods passive, venue roadmap);
- questions for the author where phrasing was unusual but possibly deliberate.

Append one entry to `paper/LAB_LOG.md`: date, "humanize ran on <files>", patterns repaired, verification result, and the disclosure status. Do not paste the rewritten text into the report.

## Voice and the author profile

If the author supplies a sample of their own writing, read it before editing and match its sentence-length range, how paragraphs open, hedge habits, dash rate, first-person policy and jargon level. A measured baseline from prior papers beats any default in this file. Without a sample, take register from the section and venue, say once that the output carries a neutral default voice, and offer to calibrate; do not repeat the offer.

Never invent a person. Do not inject first-person opinions, contractions, rhetorical questions or personality the data do not support. In technical prose, neutral is the human voice.

Treat the author's unusual but correct phrasing as deliberate. Raise it as a question, not as a defect.

## The protections list

Do not alter any of the following, whatever a pattern table says.

- Hedges tied to evidence ("may", "suggests", "is consistent with", "preliminary") and their position. Only collapse stacked, redundant hedges to one, and never remove the last one.
- Passive voice in Methods and anywhere the agent is irrelevant.
- "We", and the author's first-person policy.
- Citations and the sentences that carry them: "Prior work has shown X [12]" is correct as written. Keep keys, order and punctuation around `\cite`.
- Every number, unit, interval, p-value, sample size, year, version and identifier, and the macro that produces them.
- Defined terms and their repetition; one term per concept.
- Standard connectives followed by data or a real logical turn (However, Thus, In contrast, Although).
- The roadmap sentence in the Introduction.
- Conclusion and abstract scaffolding the venue uses ("To the best of our knowledge", "We leave X to future work", "Taken together"), provided each is concrete rather than a replacement for a concrete statement.
- Quoted text, titles, proper names, dataset and model names.
- Math, LaTeX commands, labels, references, environments, tables and code.
- Technical senses of ordinary words: robust, significant (with a test), landscape, comprehensive when it describes real coverage.
- Required headings (Limitations, Related Work, Broader Impact, and so on). Judge their content, not their existence.
- The claim-strength label of every sentence: do not upgrade "suggests" to "shows", and do not downgrade "shows" without logging a decision in `LAB_LOG.md`.
- Anonymization choices in a blind submission.

## The disclosure line

State this to the author at the end of every humanize run, in your own words, in one or two sentences: this pass edits style and clarity, it does not establish or certify that a human wrote the text, and it does not replace disclosing AI assistance where the venue asks for it.

Then point to the venue's policy: look up the official policy page, record its URL and the date checked, and suggest the author add a short disclosure of the tools used where required. A neutral example the author can adapt: "An AI assistant was used for language editing of the manuscript; the authors reviewed all text and take responsibility for its content." Do not draft the disclosure for a venue whose wording you have not read.

## Requests to beat a detector

If the request is to make text pass an AI detector, decline that aim and say why in two sentences: detectors are unreliable and are known to over-flag non-native writers, and surface rewriting does not defeat the stronger ones. Offer what helps instead: keep dated drafts and version history as evidence of the writing process, disclose assistance per the venue's policy, and run this mode for clarity. If an author is defending against a false positive, help them assemble the drafts, notes and log entries that show how the text was produced.

## Optional second check

If a skill named `unslop-max` is installed, you may run its verifier as an independent second opinion on the same pair of files. If it cannot be loaded, say so in one line and continue with `scripts/verify_rewrite.py`; the built-in check is sufficient. Never run both rewriters on the same text.
