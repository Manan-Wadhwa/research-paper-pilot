# Glossary and plain language: write for the reader who punishes jargon

A reader who meets an undefined term does one of two things: guesses, or leaves. Reviewers do both, and both hurt the paper. This file is used by `understand` (the explainer), `write` (the draft) and `review` (the clarity pass).

## Contents

- The rules
- Replace project-internal words
- The glossary table
- Define before use
- One term per concept
- The two-reader test
- A short checklist

## The rules

1. **Define before use.** The first time a term appears, define it in the same sentence or the one before. If the paper cannot define it in a clause, the concept needs its own short paragraph.
2. **Replace project-internal words.** Words coined inside the team (nicknames for datasets, runs, rounds, arms) mean nothing outside it. Replace them with a description of what the thing is, or define them once and keep them constant.
3. **One term per concept, one concept per term.** Do not alternate between synonyms for variety; readers assume a new word means a new thing.
4. **Say the plain thing first.** Lead with the ordinary-language sentence, then attach the technical name. "The model says it does not know" first, the label for that behavior second.
5. **Concrete before abstract.** Follow a definition with an instance from the data.
6. **Cut or demote.** If a term is used once, replace it with plain words and drop the glossary row.

## Replace project-internal words

Teams working with coding agents accumulate shorthand: labels for versions ("v3", "pool B"), stage names ("step 5", "round 7"), arm nicknames, file-name fragments that crept into prose. None survives contact with an outside reader. Pattern for repair:

| Internal habit | What it looks like | Plain replacement |
|---|---|---|
| Version label as noun | "on the v3 pool" | "on the final filtered dataset (N = ...)" |
| Stage label as noun | "after step 5 we saw" | "after adding the held-out evaluation we saw" |
| Arm nickname | "the confab arm" | "the group of items where the model answers confidently but wrongly" |
| Column or function name | "the `recov_frac`" | "the fraction of the effect recovered" |
| Acronym coined in the repo | "the DCS test" | spell out once or describe the test |
| Directional shorthand | "a-to-b patching" | "replacing activations from item B into item A" |

Procedure: grep the draft for backticks, underscores, digits attached to letters, and capitalized coined words; for each, either replace or define. Keep a list of replaced terms in the glossary so the team does not reintroduce them.

## The glossary table

Keep one table in `paper/PROJECT_CONTEXT.md` (used by every mode) and a reader-facing version in the explainer. Template:

| Term | Plain meaning | Where it appears | Replace with in the paper |
|---|---|---|---|
| gated pair | two inputs that differ in one factor, kept only if both pass the model's own labelling test | data file path | "matched pair" with a definition on first use |
| recovery | fraction of the original effect restored after the intervention, 1 meaning fully restored | result file field | "fraction recovered" |

Column rules: the plain meaning is one sentence a non-specialist can follow, the location points to a real file or section, and the last column is empty when the term is standard in the field and needs no change. Order rows by first appearance, not alphabetically, so a newcomer can read top to bottom.

## Define before use

Check the order of first appearance. A term that appears in the abstract must be understandable in the abstract. Acceptable patterns:

- A relative clause: "a matched pair, two inputs that differ in one word".
- An appositive: "the baseline, a model with no intervention".
- A short sentence before the term: "We remove a set of components and measure how much of the behavior disappears. We call this the removal effect."

Avoid: footnote-only definitions for terms the main claim depends on, definitions in an appendix the reader must find, and "as is well known" for anything a reader outside the subfield could not know.

## One term per concept

Build the term list before drafting. During drafting and editing, search for each concept's synonyms and unify them. This also protects against a failure in style editing: if an editor "improves" repetition by swapping in synonyms, defined terms drift. Defined terms are exempt from synonym variation (see `references/humanize.md`).

## The two-reader test

Run both readers, because they catch different failures.

- **The outsider.** A reader with general technical literacy and no knowledge of the subfield reads the abstract and introduction and answers: What is the question? What did they find? Why should I care? What is the one term I could not follow? Every "could not follow" is a missing definition or an internal word.
- **The expert.** A reader from the subfield reads methods and results and checks that each definition is correct, complete and consistent with how the field uses the word. Simplification must not change meaning: an expert who sees a standard term used loosely will distrust everything near it.

Use a fresh agent with no project context for the outsider, and the blind reviewer template for the expert. Do not use the same agent for both.

## A short checklist

- Every term in the abstract is defined or ordinary.
- No coined nickname, version label, file name or code identifier appears in prose.
- Each concept has one name throughout.
- Each definition is followed or preceded by an instance.
- The glossary table matches the text; terms dropped from the text are dropped from the table.
- The outsider could state the finding after reading the introduction.
- The expert found no definition that is wrong.
