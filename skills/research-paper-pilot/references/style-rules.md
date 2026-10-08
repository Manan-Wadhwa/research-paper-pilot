# Style rules for research papers (W1 to W77)

The shared rulebook behind the write, humanize, review and revise modes. Each rule has an id so
that reports, gate output and reviewer findings can point at it ("violates W42"). Every rule gives
its reason in one clause; if the reason does not hold for the paper in front of you, say so in the
decision log and move on, because these are working rules and not laws.

## Contents

- Settled points (read first)
- Before writing: W1 to W7
- Abstract: W8 to W11
- Introduction: W12 to W16
- Background, methods, results: W17 to W22
- Related work: W23 to W26
- Limitations and conclusion: W27 to W30
- Figures and tables: W31 to W35
- Sentence and paragraph level: W36 to W47
- De-AI pass: W48 to W52
- Venue and LaTeX: W53 to W56
- Review before submission: W57 to W60
- Rules from the classic guides: W61 to W72
- Readable without a glossary: W73 to W77
- How the mechanical gate uses these rules

## Settled points

Style guides disagree with each other on a handful of points. These rulings are final for this
skill; an author profile may override them for one author, nothing else may.

| Point | Ruling | Rule |
|---|---|---|
| Em dashes | Capped, not banned. None in the abstract, at most one per paragraph, never a bracketing pair. Numeric ranges such as 5-10 are exempt. | W49 |
| Passive voice | Allowed in Methods when the actor is irrelevant. Elsewhere name the actor. | W39 |
| Hedges | Keep one calibrated hedge where evidence is suggestive; collapse stacks; no hedge where the claim is established. | W43 |
| "Significantly" | Only with a statistical test named or reported next to it. Otherwise say what changed and by how much. | W44 |
| Roadmap sentences | Allowed ("Section 4 tests this"). They help a reader who skips around, but at most one per section. | W36 |
| Conclusion-style headings | Allowed where the venue accepts them; use topic headings where it does not. | W46 |
| Restating results | A conclusion states the moral, not a recap; a short summary section the venue requires is the exception. | W30, W50 |
| First person | "We" is the default for choices and findings. The author profile may change it. | W41 |
| Glossaries | The paper never needs one. Terms are explained where they enter; the team's glossary stays in the project context. | W73 |
| Numbers in prose | The one to three that carry the sentence's claim, after the words that say what they show. The rest go in a table. | W74 |

## Before writing

**W1** State the contribution in one sentence before drafting; if you cannot, the paper is not ready
and more text will not fix it. Aim for one to three concrete claims that form one theme, and match
each claim's strength to its evidence (existence proof, systematic trend, hedged, narrow).

**W2** Build a claims-to-evidence map first: every claim points to an experiment, table or figure,
and every experiment points to a claim. An experiment that supports no claim moves to the appendix
or is cut, because readers punish unexplained material.

**W3** Run the deletion test: strip the specific model, dataset and setting from the claim and see
whether a question remains. If nothing remains the framing is too small; if the claim survives with
no evidence behind it the framing is too large. Choose the boldest claim the evidence supports.

**W4** Write a disposable Draft 0 introduction early (stakes, gap, rough contributions) so the
experiments have a purpose, then rewrite the introduction from a blank page after results are in.
A surviving Draft 0 promises what the authors hoped for, not what they showed.

**W5** Give each result a verdict before claiming it (supported, partial, not supported,
equivocal). One positive result on one setting does not support a general claim. Mark which
analyses were fixed before seeing data and which came after, and say how selective any qualitative
examples are.

**W6** Draft in this order: figures and tables, results, methods, introduction, related work,
limitations, abstract, title. Figures come first because the argument lives in them, and the
abstract comes last because it can only summarise what exists.

**W7** Spend comparable effort on title, abstract, introduction and figures as on the body. Most
readers never get past those four.

## Abstract

**W8** Use five moves: what was achieved, why it is hard or matters, how it was done (with the
keywords a searcher would use), the evidence, and the single most telling number. An alternative
opens with an uncontroversial situating sentence, then the need, then the contribution, a metric,
and the implication. Pick one and keep every move to a sentence or two.

**W9** Delete a first sentence that could open any paper in the field; it carries no information
and spends the reader's best attention.

**W10** Keep it self-contained: roughly 150 to 250 words, no citations, no undefined acronyms, at
least one concrete number, no em dash. The abstract must be readable without the paper in hand.

**W11** Every number in the abstract matches the body and traces to a result file or macro. The
abstract is the most-quoted text, so drift here does the most damage.

## Introduction

**W12** Keep it to about a page and a half, and start the methods by page two or three. A long
introduction delays the evidence and invites the skim-reader to leave.

**W13** Use six moves: stakes in the domain (not the technology), a structural gap that names the
prior approaches, a named key abstraction, a short paragraph of design intuition, contributions
phrased as findings ("we show that X") each with an evidence pointer, and a results preview with the
headline number. "Machine learning has shown great promise" is a rejected-paper opening.

**W14** List two to four contributions of one or two lines each. Bullets such as "we study X" or
"we run extensive experiments" describe effort, not a contribution; replace them with the claim.

**W15** Say exactly what is new and what is not. Overclaiming novelty is the fastest way to lose a
knowledgeable reviewer, and under-claiming it wastes your real result.

**W16** Open with the problem, not the method. The method or model should not appear before the
third paragraph, so the paper competes on the question and not on the tool.

## Background, methods, results

**W17** Include background only if it is essential, not new, and unfamiliar to the reader; define
terms before use because readers have less context than authors think. Do not lean on a glossary:
a term the reader needs is explained where it enters (W73).

**W18** Write the methods so a stranger could re-implement them: data, hyperparameters, seeds,
compute, preprocessing, evaluation protocol. Put final design choices here and ablations with the
experiments.

**W19** Before each experiment, state which claim it tests and what to look at in the output. Order
results by the argument, not by the order you ran them, and place each control next to the claim it
protects.

**W20** Make every results subsection fit the sentence "This section shows that [claim]", and end
it with a short takeaway paragraph that names the pattern rather than repeating the numbers.

**W21** Report uncertainty with its method (standard deviation or standard error, bootstrap or
analytic), the number of runs or items, and the test used. Compare against strong, tuned baselines
and design experiments that separate competing hypotheses, not ones that all hypotheses predict.

**W22** Avoid attributing human mental states to model internals ("the model knows") unless you
define the term operationally. Replace the word "performance" with the metric it stands for.

## Related work

**W23** Group prior work into two to four approaches, name one structural limitation of each, and
close each group with one positioning sentence ("unlike X, we ..."). The baselines named here are
the baselines in the evaluation.

**W24** Compare and contrast instead of listing. If a prior method applies to your setting, either
compare against it or say why it cannot be compared.

**W25** Cite generously and fairly, since reviewers are often the authors of the related papers. In
venues that allow it, related work can follow the main results.

**W26** Never write a bibliography entry from memory. Fetch it from a bibliographic database or the
publisher page, mark anything unfetched `[VERIFY]`, prefer the published version over the preprint,
and confirm the cited paper really makes the claim you attach to it.

## Limitations and conclusion

**W27** Write a limitations section even when the venue does not require one: two to four material
limits, each stated once as scope, each pointing forward to the experiment that would settle it. Do
not argue that the limitations leave the claims intact; the reader will judge that.

**W28** Generic caveats ("may not generalise", "interpret with caution") live only in the
limitations section. Elsewhere, scope that defines the claim stays attached to the claim itself.

**W29** Keep six leaked voices out of the manuscript: audit voice ("locked", "verified", "PASS"),
defensive voice ("we do not claim"), self-critical voice (verdict columns), commentary voice,
developer voice (file paths, run configs, loader names) and commitment voice ("will be released").
They read as notes to oneself. Never write "we do not address X" merely because an instruction said
to omit X.

**W30** Write the conclusion as a moral, not a recap: what changes for the reader's own work. Add no
new self-negation in the last paragraph. A separate conclusion is often redundant; if the venue
wants one, keep it short.

## Figures and tables

**W31** Make Figure 1 the one-sentence pitch rendered as data, near the top of the first or second
page. Give each figure one dominant claim and each panel one role, and move robustness checks to the
appendix.

**W32** Draw plots as vector graphics with a colour-blind-safe palette, readable in greyscale, with
line styles as well as colours, no red against green, no title inside the image, and axis text at
least as large as body text. Captions must stand alone.

**W33** Match the colour map to the data: white at zero for magnitudes, a diverging map centred on
zero for signed values. Annotate the window or line that matters so the reader does not have to
find it.

**W34** Build tables with booktabs rules and no vertical lines, the caption above, direction arrows
in headers, bold for the best entry, equal decimals per column, uncertainty with a consistent
symbol, and one message per table. Fill cells only from result files.

**W35** Interpret every figure in prose ("Figure 3 shows that X, which supports Y"); "see Figure 3"
alone makes the reader do the authors' work.

## Sentence and paragraph level

**W36** Give each paragraph one message stated in its first sentence, and link sentences by cause,
contrast, consequence or refinement. Four to six sentences is typical. A one-line roadmap sentence is
allowed, once per section.

**W37** Reverse-outline each section: list the topic sentences alone and check that they form the
argument. A paragraph whose topic sentence serves no claim gets cut or moved.

**W38** Follow reader expectations: subject near the verb, new and important information at the end
of the sentence, old before new, action in the verb ("we analysed", not "we performed an analysis").

**W39** Use the active voice with a named actor by default. The passive is fine in Methods when the
agent is irrelevant ("samples were drawn without replacement").

**W40** Keep one idea per sentence, split anything past about 40 words, aim for a mean near 20, and
vary length so that short sentences land after long ones.

**W41** Put verbs early, avoid bare pronouns ("this result shows", not "this shows"), never use a
comparative without naming the comparison, define each uncommon term at first use, and do not start
every sentence with "We".

**W42** Delete filler such as "actually", "a bit", "very", "really", "quite", "basically",
"essentially", "in order to", "due to the fact that", "it is worth noting", "note that", and "to our
knowledge". Expand contractions. Cutting these costs nothing and shortens the paper.

**W43** Hedge once per uncertain claim, at the claim, and not at all where the evidence is
established. Never stack hedges ("may possibly suggest that ... could"). A calibrated hedge on a
suggestive result is honesty and stays; see invariant I4 in SKILL.md.

**W44** Replace unearned adjectives with a number or delete them: novel, substantial, impressive,
promising, comprehensive, powerful, robust (when figurative), state-of-the-art (unless naming a
system). "Significantly" requires a test. Avoid weak verbs for your own contribution such as
"combine", "modify" or "extend".

**W45** Use one term per concept across abstract, methods, results and captions. Repeating a
technical term is required; rotating synonyms makes the reader wonder whether two things exist.
Define acronyms at first use and avoid inventing convenience acronyms.

**W46** Where the venue allows, write headings that state the finding ("Removing the head erases
the effect") rather than the topic ("Ablations"); a skim-reader then gets the argument from the
headings. Use sentence case.

**W47** Run a compression pass that removes roughly a third of the words. If more than half would
have to go, the framing is wrong and the fix is a structural rewrite, not trimming.

## De-AI pass

**W48** Edit structure before vocabulary: uniform rhythm, connective paragraph openers,
preview-then-restate, forced triads and closing loops first; then staging patterns (not-X-but-Y,
one-line closers, "the key insight is"); then word clusters. Fixing words in a badly shaped
paragraph changes nothing. The catalogue is in `ai-patterns-academic.md`, the procedure in
`humanize.md`.

**W49** Keep dashes under the cap in the settled-points table, and do not swap them for a colon
tic: if every sentence ends "...: expansion", the habit has only moved.

**W50** Keep legitimate academic connectives ("in contrast", "furthermore") when a citation or datum
follows them; flag them only when they cluster. A summary section the venue asks for may restate.

**W51** A rewrite adds no number, name, citation or claim and drops none. Prove it mechanically with
`scripts/verify_rewrite.py`; do not rely on rereading.

**W52** Treat detector-style signals as candidates, not verdicts. Never label a passage
"AI-generated" from style alone, and never use the pass to evade a disclosure policy (invariant I8).

## Venue and LaTeX

**W53** Fetch the official call or author instructions, record the URL and the date checked, and
take page limits, anonymity rules and style-file names from that page, never from last year's
paper. Workshops often differ from the main track.

**W54** Copy the whole template directory, compile it unchanged first, never edit the style file,
and compile after each section. Use `\citet` for in-sentence citations and `\citep` otherwise,
load `cleveref`, put `\label` after `\caption`, punctuate equations, and avoid one-word last lines.

**W55** Keep the bibliography to cited entries only, leave no `TODO` or `[VERIFY]` marks, make every
reference resolve, and check anonymity before upload. `scripts/check_submission.py` automates this.

**W56** Include whatever the venue demands: the checklist or reproducibility statement, code and
data availability, compute, and any disclosure of language-model use. Missing items are desk
rejections, not style points.

## Review before submission

**W57** Run a reverse outline and a five-question self-review (contribution, clarity, experimental
strength, completeness of evaluation, soundness of method). Mark each item pass, needs revision or
needs a new experiment.

**W58** Have a reader with no project context audit numbers: every figure in the text against raw
result files, checking rounding, best-versus-mean, configuration mismatch, delta arithmetic,
caption-versus-table disagreement and scope words such as "consistently" and "all".

**W59** Use a reviewer who did not write the text. Ask for a findings list with rule ids rather
than a yes or no, a single strongest-rejection paragraph, and a point-by-point adjudication of it.
Add a cold-read test from a fresh agent that has only the manuscript.

**W60** Chain human readers one at a time: an outsider for framing, an expert for correctness, the
senior author last, telling each what to look for. Read the paper aloud once; clumsy sentences and
double readings surface that silent reading hides.

## Rules from the classic guides

Added after checking the skill against the standard reading list in `sources.md`. Numbering continues from the rules above.

- **W61 Write the paper before the research is finished.** Drafting the abstract and introduction early exposes what is not yet understood and which experiment is missing. Treat the draft as an instrument of the research, not its report.
- **W62 One key idea per paper.** The reader should be able to say in one sentence what the paper's idea is. If the project has several, write several papers; if the idea is unclear at the start, it must be clear by the end, and the text must state it outright ("The main idea of this paper is...").
- **W63 Introduce the problem with an example before any generality.** A concrete instance the reader can hold in mind beats a paragraph of motivation. Molehills, not mountains: never open with how important the field is.
- **W64 Readers are in a hurry and reading in a bazaar, not a monastery.** Title, abstract and introduction get most readers; the details get a handful. Put the contribution, what is new and what is not, and the implications in the first page, stated so plainly that a tired reviewer cannot miss them. Never assume the reviewer will work out the point.
- **W65 Quarantine speculation.** Keep intuitions and conjectures in a clearly labelled place (a "Motivation" or "Why we think this happens" paragraph) and never let them read as established explanation. The test: would you rely on this account to make a prediction or get a system to work?
- **W66 Identify the source of every gain.** When a method has several changed parts, report what each part contributes; otherwise the reader cannot tell a new idea from a tuning budget. Lesion the components, vary one thing at a time, and show how the effect scales rather than one bake-off number.
- **W67 No mathiness.** Mathematics earns its place only when it makes a statement more precise than prose can. Formalism that never appears in a proof or a computation is decoration and slips between the formal and the informal claim.
- **W68 Guard the vocabulary.** Three failures to check for: suggestive definitions (a technical term whose everyday meaning smuggles in a claim, such as calling a score "understanding"), overloaded terms (reusing an established word with a new meaning), and suitcase words (one word carrying several meanings, such as "generalization"). Define the term, or pick a plainer one.
- **W69 Measure what the goal is.** The dependent variable must make direct contact with the stated goal; a proxy needs one sentence saying why it stands in for the goal and where it fails to.
- **W70 Do not repeat the abstract in the introduction**, and never write a section with a single subsection.
- **W71 Reserve the heavy labels.** Call something a theorem only if it is a main contribution, a proposition if it is a non-trivial intermediate step, a lemma if routine; re-state a variable's meaning when it returns after a gap.
- **W72 Shorten by tightening before anything else.** To fit a page limit: cut words that say the same thing, remove lines that carry only a few words, condense sections long for their point, then drop redundant figures, then fix layout gaps; negative spacing and supplementary material come last.

## Readable without a glossary

These rules exist because careful, honest papers fail in a predictable way: every name, number,
caveat and audit detail is correct, and the reader cannot follow any of it. The procedure behind
W73 is in `glossary-and-plain-language.md`.

- **W73 The paper needs no glossary.** Describe things in plain words by default. Keep a coined name only if the concept recurs across sections, no phrase of about four words says it, and the name describes itself; the main text asks the reader to carry three or four such names and acronyms at most. Never use letter codes for conditions, arms, runs or instruments in prose, and spell out any short labels a table uses in its caption. Introduce each condition, control and measure by its role (what it is, what it rules out, what to expect if the claim holds) in running text where it enters, and remind the reader what a name means when it returns after a gap.
- **W74 Words before numbers.** Each sentence says in words what a comparison shows, then gives the one to three numbers that carry it; every other value goes in a table the sentence points to. Every Results paragraph keeps at least one sentence that ties its numbers to the claim they support. Pointing at what a number supports is not interpretation, so it stays even where Discussion holds the mechanism (see S6 in `ai-patterns-academic.md`).
- **W75 Lists only for parallel, separable items.** Datasets, hyperparameters, released artifacts and the contribution list can be lists. Findings, steps of an argument and reasons that depend on each other are prose, because the links between them (because, unless, which rules out) are the content. A list that stays gets a sentence before or after saying what its items add up to.
- **W76 State each caveat once, where it bites.** A specific caveat stays attached to its claim at the claim's main statement, not repeated at every mention, and the abstract carries at most one. Label a result pre-registered or post hoc once, where it is first reported, and in the claims table; do not restate the label, the bar and the amendment history in every sentence that uses the number.
- **W77 Provenance lives in the repository, not in the prose.** Every number traces to a file (I1), and the trace is kept in the numbers file, the released code and, if the venue needs it, one compact table. Raw script output, log excerpts, commit hashes, internal file and run names, and amendment dates stay out of the main text; an amendment log, when one is owed, is a short table in the appendix. Every appendix section delivers what its heading promises or is cut.

## How the mechanical gate uses these rules

`scripts/prose_gate.py` checks the countable subset: dash counts (W49), filler and hype words
(W42, W44), stacked hedges (W43), same-opener runs and sentence-length statistics (W40, W41), and
passive voice (W39, reported but never failed in Methods), label codes and the load of coined
names and acronyms (W73, rule M11), numbers per sentence and paragraph (W74, M12), and lists of
short fragments in body sections (W75, M13). `check_submission.py` finds stub sections and pasted
script output (W77). It cannot judge W1 to W7 or the
structure rules; those need the reviewer agents in `review.md`. Treat its output as a worklist, and
run it before and after the de-AI pass so the numbers show what changed.
