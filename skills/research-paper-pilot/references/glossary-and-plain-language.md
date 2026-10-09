# Plain language: a paper the reader can follow without a glossary

A reader who meets an undefined term does one of two things: guesses, or leaves. A reader who meets a term defined three pages earlier does the same, and so does a reader who has to translate a code ("arm B", "S3") back into a thing in every sentence. Reviewers do all of these, and all of them hurt the paper. This file is used by `understand` (the explainer), `write` (the draft), `revise` (renaming) and `review` (the clarity pass).

The glossary in `paper/PROJECT_CONTEXT.md` is the team's tool for keeping its own words straight. The paper must never need one, in the appendix or anywhere else. The standard: a reader can open any page and follow it with only what the abstract and the introduction told them.

## Contents

- The rules
- A name has to earn its place
- Explain by role, in prose
- A worked example
- Replace project-internal words
- Renaming is a terminology edit
- The glossary table (internal)
- Define before use
- One term per concept
- The cold-read test
- A short checklist

## The rules

1. **The paper needs no glossary.** If a reader would need one to follow the main text, the paper has too many names. An appendix glossary does not fix that; it moves the work onto the reader.
2. **Plain words first; a name only if it earns it.** The default is to describe the thing: "the models trained with shuffled rewards", not a label for them. See the next section for when a name is worth it. Main text budget: three or four coined names and new acronyms in total.
3. **No letter codes in prose.** Codes for conditions, arms, cells, runs, instruments or datasets built in the project ("arm B", "C2", "run v3", "the S-split") make the reader decode every sentence. Use a short description instead. A table may use short column labels only if its caption spells out each one.
4. **No metaphor names without the literal meaning.** Words like "canary", "shield" or "leash" are vivid to the team and opaque to everyone else. Prefer the literal description. If a metaphor stays, state its literal meaning when it is introduced and again when it returns after a gap.
5. **Explain by role, in prose.** When a concept enters, say in running text what it is, why it is there (the question it answers or the alternative it rules out) and one concrete instance. Two or three sentences, not a list or a table row.
6. **Re-anchor after a gap.** A name that returns after a section or more comes back with a short reminder: "the shuffled-reward control, which went through the same training but could learn nothing, ...".
7. **Words before numbers.** Each sentence says in words what a comparison shows, then gives the one or two numbers that carry it. Every other value goes in a table the sentence points to. A paragraph of numbers is a table written as prose.
8. **Say the plain thing first.** Lead with the ordinary-language sentence, then attach the technical name if one is needed. "The model says it does not know" comes first; the label for that behavior second.
9. **Concrete before abstract.** Follow a definition with an instance from the data.
10. **One term per concept, one concept per term.** Do not alternate between synonyms for variety; readers assume a new word means a new thing.

## A name has to earn its place

A coined name costs the reader memory every time it appears. Keep one only when all three hold:

- the concept recurs across several sections, so a description every time would bloat the text;
- no plain phrase of about four words says it;
- the name describes itself: "the shuffled-reward control" passes, "control R" and "the canary" do not.

A name used in one section only should become a description. Field-standard terms (cross-entropy, attention head, odds ratio) are not coined names; use them as the field does and define them only for the venue's outsiders. `scripts/prose_gate.py` (rule M11) lists the label codes, the coined names (italicised at first use, then reused) and the acronyms in the main text, and flags a load above `--term-budget`. Pass `--allow-terms` for codes that are standard in the field.

## Explain by role, in prose

A definition says what a thing is. A reader also needs to know why it is in the paper, or the definition does not stick. For every condition, control, measure or instrument, write two or three sentences in running text:

1. What it is, in plain words.
2. What it is for: which question it answers or which alternative explanation it rules out.
3. What the reader should expect from it if the main claim holds, so the result can be read against that expectation.

Put these sentences where the concept enters, not in a list of conditions with one line each. When the result arrives, the sentence that reports it can then be short, because the reader already knows what to look for.

## A worked example

Invented, using the label-smoothing project from the README.

Before: "On S3, A beats B by 2.1 points (A 4.2, B 6.3, C 6.0), so C rules out the warm-up story. The shield holds on S1 to S3."

After: "We also trained a control model that used the same warm-up schedule as the smoothed model but no smoothing. If the warm-up alone explained the gain, this control would match the smoothed model. It did not: under blur, the smoothed model's calibration error was 4.2, against 6.0 for the control and 6.3 for the baseline. The gain comes from smoothing, not from the schedule."

What changed: four codes became descriptions; the control's purpose came before its result; the conclusion is stated in words; three numbers stay because the comparison needs them, and the rest belong in a table. The second sentence of the original ("the shield holds") is a metaphor for an unstated result and has to be rewritten as that result, or cut.

## Replace project-internal words

Teams working with coding agents accumulate shorthand: labels for versions ("v3", "pool B"), stage names ("step 5", "round 7"), arm nicknames, file-name fragments that crept into prose. None survives contact with an outside reader. Pattern for repair:

| Internal habit | What it looks like | Plain replacement |
|---|---|---|
| Version label as noun | "on the v3 pool" | "on the final filtered dataset (N = ...)" |
| Stage label as noun | "after step 5 we saw" | "after adding the held-out evaluation we saw" |
| Letter code for a condition | "arm B beats arm C" | "the baseline beats the warm-up-only control" |
| Arm nickname | "the confab arm" | "the group of items where the model answers confidently but wrongly" |
| Metaphor name | "the canary run" | "a run on the untouched model, kept as a fixed reference" |
| Column or function name | "the `recov_frac`" | "the fraction of the effect recovered" |
| Acronym coined in the repo | "the DCS test" | describe the test; spell an acronym out only if it passes the three tests above |
| Directional shorthand | "a-to-b patching" | "copying activations from the run on item A into the run on item B" (say which run gives and which receives) |

Procedure: run `prose_gate.py --academic` and read its reader-load block; then grep the draft for backticks, underscores, digits attached to letters and capitalised coined words. For each, replace it or justify it against the three tests. Record replaced terms in the glossary table so the team does not reintroduce them.

## Renaming is a terminology edit

Replacing codes and coined names changes the words that carry the paper's facts, so do it in `write` or `revise`, not in `humanize`. Update the glossary table first, then rename everywhere at once, including captions, tables and the appendix. If `verify_rewrite.py` is run afterwards, it reports each removed code as a DROPPED proper noun; check that each one is a rename recorded in the table, not a lost fact, and say so in the report.

## The glossary table (internal)

Keep one table in `paper/PROJECT_CONTEXT.md` (used by every mode). The author's plain-language explainer from `understand` may show it; the paper does not. Template:

| Term | Plain meaning | Where it appears | Replace with in the paper |
|---|---|---|---|
| gated pair | two inputs that differ in one factor, kept only if both pass the model's own labelling test | data file path | "matched pair", explained by role where it enters |
| recovery | fraction of the original effect restored after the intervention, 1 meaning fully restored | result file field | "fraction recovered" |

Column rules: the plain meaning is one sentence a non-specialist can follow, the location points to a real file or section, and the last column holds the plain phrase the paper uses. It is empty only when the term is standard in the field; a coined name kept in the paper needs a note saying which of the three tests it passes. Order rows by first appearance, not alphabetically, so a newcomer can read top to bottom.

## Define before use

Check the order of first appearance. A term that appears in the abstract must be understandable in the abstract, without the introduction. Acceptable patterns:

- A relative clause: "a matched pair, two inputs that differ in one word".
- An appositive: "the baseline, a model with no intervention".
- A short sentence before the term: "We remove a set of components and measure how much of the behavior disappears. We call this the removal effect."

Avoid: footnote-only definitions for terms the main claim depends on, definitions in an appendix the reader must find, and "as is well known" for anything a reader outside the subfield could not know.

## One term per concept

Build the term list before drafting. During drafting and editing, search for each concept's synonyms and unify them. This also protects against a failure in style editing: if an editor "improves" repetition by swapping in synonyms, defined terms drift. Defined terms are exempt from synonym variation (see `references/humanize.md`).

## The cold-read test

Run three readers, because they catch different failures. Use a fresh agent with no project context for the first two, and the blind reviewer template for the expert. Do not use the same agent twice.

- **The outsider.** A reader with general technical literacy and no knowledge of the subfield reads the abstract and introduction and answers: What is the question? What did they find? Why should I care? What is the one term I could not follow? Every "could not follow" is a missing definition or an internal word.
- **The cold open.** Give a fresh reader the abstract, the introduction and one Results paragraph chosen at random. Ask it to restate that paragraph's finding in its own words and to list every word it had to guess or look back for. Any guessed word, and any restatement that misses the point, is a finding against rules 2 to 7.
- **The expert.** A reader from the subfield reads methods and results and checks that each definition and each plain replacement is correct, complete and consistent with how the field uses the word. Simplification must not change meaning: an expert who sees a standard term used loosely will distrust everything near it.

## A short checklist

- The paper contains no glossary, and the cold-open reader guessed no word.
- No letter code, version label, file name or code identifier appears in prose; table labels are spelled out in the caption.
- The main text asks the reader to remember at most three or four coined names and acronyms, each passing the three tests.
- Every condition, control and measure is explained by role where it enters.
- Each sentence states its comparison in words; paragraphs carry only the numbers that support their claim.
- Each concept has one name throughout.
- Each definition is followed or preceded by an instance.
- The glossary table matches the text; renamed terms are recorded there.
- The expert found no definition or replacement that is wrong.
