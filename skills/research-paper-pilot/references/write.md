# Mode 6: write the paper

Turns a frozen set of claims and results into a manuscript, section by section. This mode drafts;
it does not search literature (litreview), judge evidence (evidence) or polish style (humanize).
Sentence-level rules are in `style-rules.md` and are cited here by id (W1 to W77).

## Contents

- Preconditions
- Step 1: compress to the narrative
- Step 2: contribution sentence and outline
- Step 3: drafting order
- Section by section
- Contributions as claims
- Terminology: plain words first, no reader glossary
- Venue register switch
- The rigor section
- Using one subagent per section
- The edit loop
- Mistakes that cost real projects
- Done check, state updates, output

## Preconditions

Read `paper/PROJECT_CONTEXT.md`, `paper/CLAIMS.md`, the numbers file (a generated macro file or
the result files it comes from) and `paper/AUTHOR_PROFILE.md` if one exists. Do not draft when:

- the claims ledger is missing or has no status column filled in (route to `evidence`);
- the headline claim has no one-sentence form (route to `hypothesis`);
- the venue, page limit and anonymity rule are unknown (ask once; record the answer and its date).

Numbers enter the draft only as macros or as values copied from a result file at the time of
writing (invariant I1). A literal typed from memory is a defect even when it happens to be right,
because it will go stale on the next re-run.

## Step 1: compress to the narrative

Before any prose, write the whole paper as three bullets, each a claim a reader could repeat to a
colleague. Then check three things:

- Each bullet maps to at least one claim in CLAIMS.md, and every claim marked "goes in the paper"
  serves a bullet. A claim that serves none moves to the appendix.
- The bullets form a story: what readers currently believe, what crack the evidence opens, what
  follows once the crack is accepted.
- A title can be written for them. A title that will not come is usually a sign of two papers in
  one (W1, W3).

Show the bullets to the user; this is part of checkpoint 2. Wording changes here cost nothing,
while the same change after drafting costs a rewrite.

## Step 2: contribution sentence and outline

1. Write the contribution sentence (W1) and the one-sentence thesis test: delete the setting and
   see if a question remains; swap in a different setting and see if the claim still reads true
   (W3).
2. Fill a claims-to-evidence table: claim, evidence file, figure or table, section. Every row
   needs all four cells (W2).
3. Write a Draft 0 introduction of one paragraph per move, marked disposable (W4).
4. Outline each section as a list of paragraph labels, each label one sentence long. The labels are
   the topic sentences-to-be; a paragraph that fits no label does not belong, and a missing label
   is a missing paragraph (W37).
5. Put the outline in `paper/OUTLINE.md` and stop for the user. Checkpoint 2 is passed only when
   the user approves the bullets, the contribution sentence and the outline.

## Step 3: drafting order

Draft in this order (W6). Each step produces text that constrains the next.

1. Figures and tables, using `figures.md`. A figure plan exists before results prose.
2. Results: one subsection per claim, each fitting "this section shows that [claim]" (W20).
3. Methods: complete enough to re-implement (W18).
4. Introduction: from a blank page, using the six moves (W13), then compare with Draft 0 and note
   what changed in the decision log.
5. Related work, using the scout notes from litreview.
6. Limitations (W27), then conclusion (W30).
7. Abstract, then title (W8 to W11).

Give the abstract, the introduction and Figure 1 the same effort as the rest combined; they are
what most readers will see (W7).

## Section by section

### Abstract

Use the five moves in W8: achievement, difficulty or stakes, method with searchable keywords,
evidence, one telling number. Assume the abstract is all anyone reads, so the key takeaway sits
inside it and is not merely promised. The first sentence must be specific to this paper (W9), no
citations, no undefined acronyms, no em dash, and every number is a macro that resolves (W10, W11).
Hedging words are rare here; state what was shown at the strength the claims ledger allows.

### Introduction

Write it as a short story with these moves (W13):

1. Stakes in the domain, in a sentence a smart outsider accepts.
2. The gap: what current practice believes or does, named, and where it fails structurally.
3. A named idea that closes the gap, introduced by what it does before what it is called.
4. A paragraph of design intuition, so the reader sees why it should work before seeing it work.
5. Contributions as claims with evidence pointers (see below).
6. A results preview that includes the headline number.

Lead with the best-audited evidence, not the newest. The result that has survived the most checks
is the one a skeptical reader will believe first, and belief transfers to the rest. Keep the
method out of the first two paragraphs (W16) and say plainly what is and is not new (W15).

A short roadmap sentence is allowed (W36). Do not end the introduction with a paragraph that
repeats the abstract.

### Methods

A stranger should be able to re-implement from this section (W18). Cover data and how labels were
obtained, the exact intervention or training setup, hyperparameters, seeds, compute, the evaluation
protocol, and the metric in one formula. Put the final design choices here, not their history. The
passive voice is fine when the agent is irrelevant (W39). If a data-construction step is a
contribution in itself, give it a named subsection, because reviewers look for it.

State what was fixed before seeing data and what was decided afterwards (invariant I4); a single
"analysis timing" paragraph here saves repeated qualifiers later.

### Results

Each subsection opens with the claim it tests and what to look at in the figure or table (W19). Say
what the figure shows and what it means, never "see Figure 3" alone (W35). Report uncertainty as in
W21 and keep nulls next to the effect they control. End each subsection with a takeaway paragraph
that states the pattern, written so a skim-reader gets the message from it alone (W20).

Write each comparison as words first, then the one to three numbers that carry it, and point to the
table for the rest (W74). A paragraph that reads "X reads a against b; Y reads c against d" is a
table in disguise: make the table and keep the sentence that says what it shows. Findings are
paragraphs, not bullet lists (W75), because the links between them are the argument. State each
caveat once, where its claim is first reported (W76).

Order by argument. Controls and ablations sit beside the claim they protect, not in a trailing
section where they look like afterthoughts.

When a result is post hoc, say so where it first appears, in plain words ("we found this while
checking X, so we treat it as exploratory"), and once in the claims table; do not repeat the label in
every later sentence (W76). Exploratory results are welcome; hidden ones are not.

When an outcome was predicted and failed, say so. A stated half-failure is among the most credible
sentences a paper can contain.

### Related work

Group by approach, two to four groups, each with one structural limitation and one positioning
sentence (W23). Name the closest prior work explicitly and say how this paper differs in a
sentence a reviewer could check (W24). Use the verified notes and bibliography from litreview only;
anything unverified keeps its `[VERIFY]` mark in the draft (W26). If the venue allows, place this
section after the results and keep the introduction's treatment short.

### Limitations

Two to four material limits, each stated once, as scope, each pointing forward to the experiment
that would settle it (W27). Choose the limits a hostile but fair reviewer would find, and state
them before they do; this gains trust with exactly the readers who matter. Do not defend, and do
not repeat generic caveats elsewhere (W28).

### Conclusion

State the moral: what a reader should now do or doubt in their own work. Do not narrate the paper
in the past tense, and do not introduce a new reservation in the last paragraph (W30). Ending on a
question to the reader is acceptable when it is the real open question.

### Tacit knowledge

What broke, what was tried and abandoned, which settings mattered and why, and the intuitions that guided the search are often the most useful part of the work to the next team, and the first thing cut for space. Keep them: an appendix titled along the lines of "Practical notes" or a companion post, pointed to from the main text. The lab log and the retired rows of the claims ledger are the raw material.

### Title

The title names the finding or the question in plain words. Avoid puns, colons that split a slogan
from a subject, and project-internal names. Test it on the three-bullet story: a reader who sees
only the title should guess the claim.

## Contributions as claims

Phrase each contribution as a finding with a pointer: "We show that X (Section 4, Figure 2)".
Avoid "We study", "We propose" (unless a method is the contribution) and "We provide extensive
experiments" (W14). Two to four contributions is typical. Check each one against CLAIMS.md: its
status must permit the verb. An exploratory claim takes "we observe" or "we find preliminary
evidence", a supported claim takes "we show", and a retired claim does not appear.

## Terminology: plain words first, no reader glossary

The glossary in PROJECT_CONTEXT.md is for the team; the paper must read without one (W73). Before
drafting, take each term in that glossary and classify it: used by the field as is, worth keeping
as a name (it recurs across sections, no short phrase says it, and the name describes itself), or
to be replaced by a plain description. Project-internal words, letter codes and metaphor names go
in the last group. The main text keeps three or four coined names and acronyms at most; write the
plain phrase for each term into the glossary's last column so every section uses the same one. See
`glossary-and-plain-language.md` for the procedure, the explain-by-role pattern and a worked
example.

Then lock one term per concept for the whole paper (W45). Introduce each condition, control and
measure by its role, in prose, where it enters, and re-anchor a name that returns after a gap.

Avoid attributing human mental states to model internals unless the term is defined
operationally, and then use it consistently (W22).

## Venue register switch

Ask where the paper is going and set the register before drafting results and limitations.

- **Rigor-themed or reproducibility-themed venue.** Keep an explicit section, usually near the end
  of the results, on what the authors' own criteria could not decide: which comparisons landed at
  a boundary, which checks raised a worry and which follow-up resolved it, which labelled
  predictions failed. Name the decisive follow-up for each. This is the part of the paper such
  venues remember, so write it as findings, not as apology.
- **General or application venue.** Convert audit voice into design facts. "This check was verified
  and passed" becomes a sentence in Methods that states the design ("pairs were kept only when the
  model's own answers disagreed"). Move boundary cases to the appendix and keep one or two
  sentences in the main text (W29).
- **Short workshop or page-limited venue.** Keep three claims at most, one figure per claim, and
  move the rest to an appendix the venue allows. Check whether the appendix counts toward the limit.

Record the chosen register in PROJECT_CONTEXT.md as a locked decision with the reason (invariant
I5). If the venue is unknown, write for the general register and flag the choice as open.

## The rigor section

Whatever the venue, a paper that has been audited should show the audit's results in the form of
findings. Typical entries and how to write them:

- A criterion that landed on its boundary: report the value, the bar, and the follow-up that
  decided it, in that order.
- A check that raised a worry and was resolved: one sentence on the worry, one on the resolution,
  one pointer to the evidence.
- A prediction fixed before the run: label it as such (invariant I4) and report it whether it held
  or failed.
- A claim that a pre-committed bar retired: say so, then state the fallback claim the bar named.

Keep this material in the voice of findings, not in the voice of a log (W29). The audit record
itself belongs in LAB_LOG.md.

## Using one subagent per section

Sections draft well in parallel when each writer sees only what it needs. Use
`agents/section-writer.md` once per section with these inputs: PROJECT_CONTEXT.md, `OUTLINE.md`,
the CLAIMS.md rows for that section, the numbers file or macro names, the style rules by id, and
the author profile. Require the writer to:

- cite macros, not literals, and list every macro it used;
- use the plain phrases from the glossary's last column, and report any new name it introduced;
- return the section plus the list of claim ids it relied on;
- insert `[VERIFY]` where it wanted a citation it had not been given;
- avoid forward references to numbers in sections it has not seen.

Merge the sections yourself. After merging, read the whole paper for term drift (W45) and for
repeated claims, then run the reverse outline (W37). Subagents write fluent text that can drift
from the evidence, so the claims-used list is the audit trail: diff it against CLAIMS.md before
accepting the section.

## The edit loop

1. Draft, then reverse-outline each section (W37). Cut or move paragraphs whose topic sentence
   serves no claim.
2. Run the compression pass (W47). Roughly a third of the words go; more than half means the
   framing is wrong and the section needs a structural rewrite, not trimming.
3. When the framing changes, rewrite from a blank page with the same results and the new story,
   rather than polishing the old text. Framing decisions are baked into sentence structure and
   survive polishing.
4. Run `scripts/check_numbers.py` on the draft and fix every flagged literal.
5. Run `scripts/prose_gate.py --academic` and clear the worklist (W40 to W45, W49, W73 to W75).
   Read its reader-load block: every label code goes, and every coined name beyond the budget
   becomes a description.
6. Seek outside reading at each stage: an outsider on the three-bullet story, an expert on the
   results, a fresh agent reading only the manuscript (W59, W60). Tell each reader what to focus on.
7. Read the paper aloud once at the end; double readings and clumsy sentences surface this way.
8. Hand off to `humanize` only after numbers and citations are frozen, then to `review`.

## Mistakes that cost real projects

- **Prose that drifts from code.** The text states the opposite direction of an effect, or names
  conditions in the wrong order, because it was written from memory of the code. Check each
  directional word against the result file.
- **Numbers quoted from memory.** A magnitude claim ("orders of magnitude") later turns out to be
  a factor of a hundred. Every number comes from a file.
- **Leading with the newest result** instead of the best-audited one.
- **Saying "pre-registered"** when criteria were merely fixed in code beforehand. Use the exact
  phrase the record supports and point to the dated note (invariant I4).
- **Averaging away direction or arm.** A result that holds in one direction or one condition is
  reported as that, not as a general effect.
- **Hiding a failed prediction.** Reviewers find it anyway, and the paper looks evasive.
- **Leaked voices** (W29): file paths, run names, "verified" and "PASS" in the manuscript.
- **The audit trail written into the prose.** Every number carries its bar, its seed count, its
  pre-registration status and the date its criterion changed, so no sentence can be read. Keep the
  trail in the repository and one appendix table (W76, W77); the paper states the result.
- **A private vocabulary.** Letter codes and nicknames for conditions that the team knows by heart
  and the reader has to decode every line (W73).
- **A surviving Draft 0 introduction** that promises what the evaluation cannot deliver (W4).

## Done check, state updates, output

The draft is ready for review when: every claim in the three-bullet story has a section; every
number is a macro or a value traced in the numbers file; `check_numbers.py` has no unexplained
flags; every citation is fetched or marked `[VERIFY]`; the gate worklist is clear or each
remaining item has a reason; a fresh reader given only the abstract, introduction and one random
Results paragraph can restate that paragraph's finding without guessing a word; and the venue's page
limit is met with the appendix policy known.

Append to LAB_LOG.md: "Mode write ran on <date>; produced <files>; decisions: register, claim
status changes, any claim moved to the appendix; open: [VERIFY] count, pending figures." Update the
status line of PROJECT_CONTEXT.md. End with the standard output contract: files written,
decisions taken, open items, next mode (usually `humanize` then `review`).
