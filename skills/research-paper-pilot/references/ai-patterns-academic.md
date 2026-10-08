# AI-Writing Pattern Catalog for Academic Papers

This catalog lists the habits that make a draft read as machine-written, and says which ones are safe to repair in a research paper. Most de-slopping advice was written for blogs and marketing copy. Applied unchanged to a paper it deletes hedges, flips Methods into active voice, strips "Moreover" from legitimate argument chains and breaks the reader's trust. The "Safe for papers?" column exists to prevent that.

## Contents

- How to read the catalog
- A. Content and claims
- B. Vocabulary
- C. Structure and staging
- D. Punctuation and format
- E. Leftovers and hygiene
- Not tells in a paper: do not act
- Keep what carries a person
- When not to act
- Maintenance notes

## How to read the catalog

"Safe for papers?" has three values:

- **yes**: repair on sight; the pattern has no legitimate use in a paper.
- **with care**: the pattern is also ordinary scholarly practice; repair only when the condition in the Rule column holds.
- **no**: do not touch; the pattern is a paper convention or a template matter.

Rows are candidates, not verdicts. Read the sentence in context, check the condition in the Rule column, and prefer leaving a sentence alone over a doubtful edit. One sighting of a weak tell means nothing; several tells in one passage justify action. Structure rows (group C) carry more signal than vocabulary rows (group B), so spend effort in that order. `humanize.md` gives the procedure; this file is the lookup table.

Ids (C1, V2, S5, ...) are stable so that review reports and the humanize log can cite them.

## A. Content and claims

| Id | Pattern | Looks like | Repair | Safe? | Rule |
|---|---|---|---|---|---|
| C1 | Significance inflation | "marks a pivotal moment", "a paradigm shift", "a testament to" | State the concrete contribution or result in plain words | yes | Keep the fact, drop the verdict on its importance. |
| C2 | Hype adjectives and novelty padding | "groundbreaking", "novel" in every sentence, "first to" without a search | Name the difference from the closest prior work | with care | "Novel" or "state-of-the-art" may appear once as a technical claim tied to a stated comparison. |
| C3 | Superficial -ing rider | ", highlighting the importance of X", ", underscoring the need for" | Delete the rider, or turn it into a sentence the evidence supports | yes | Keep the fact before the comma; keep the rider only if a result backs it. |
| C4 | Borrowed authority | "studies show", "experts argue", "it is widely accepted" with no source | Add the citation and what it found, or cut the claim | yes | Every attribution carries a key or goes; never invent the source (invariant I2). |
| C5 | Citation dumping | "[3-14]" after a generic sentence | Cite the one or two works that bear on the claim and say why | with care | Field norms differ; a survey sentence may legitimately cite many. |
| C6 | Formulaic opener | "In recent years, X has attracted considerable attention", "With the advent of" | Open on the specific gap or the problem | yes | The first sentence survives only if it names something concrete. |
| C7 | Generic positive closer | "holds great promise", "paves the way for", "opens new avenues" | End on a concrete limitation or the next experiment | yes | A closing sentence earns its place by adding a fact or a boundary. |
| C8 | Content-free challenges section | A "Challenges and Outlook" block of generic obstacles and vague optimism | Replace with specific limitations and named follow-ups | with care | The section is required by many venues; the tell is emptiness, not the heading. |
| C9 | Over-claiming verb | "prove", "demonstrate", "establish" on correlational or small-n evidence | Match verb strength to the evidence ladder (invariant I4) | yes | Never raise a claim's strength while humanizing; lowering it to fit the evidence is allowed and must be logged. |
| C10 | Vague hedging | "somewhat", "fairly", "relatively" with no comparison | Give the number or the comparison class, or delete | yes | A hedge that carries no information is padding; an evidence-tied hedge is content (see the protections). |
| C11 | Empty intensifier | "extensive experiments", "numerous studies", "significantly" with no test | Give counts, datasets, effect sizes, test names | yes | Keep "significantly" only where a test backs it. |
| C12 | Unnamed concrete world | "a popular model", "a large benchmark", "standard settings" | Name the model, dataset, hyperparameters | with care | Only if the facts are in the source; blind-review anonymity may require the vague form on purpose. |
| C13 | Content-free evaluation | "This is an important finding." standing alone; "In other words..." restating the line above | Delete, or replace with the mechanism or consequence | with care | Discussion must interpret; cut only a sentence that adds no mechanism, number or implication. |
| C14 | Both-sidesism without a verdict | "on the one hand... on the other" where the paper owes a conclusion | Commit to the reading the evidence favors | with care | Related Work may present both sides; Results and Discussion should commit. |
| C15 | Arguing with no one | "To be clear, we are not claiming...", "One might think..." answering nobody | Cut it, or state the real claim | with care | Pre-empting a real reviewer objection is good practice; cut only invented ones. |
| C16 | Contribution-list cliche | "We make three contributions: a novel framework, extensive experiments, and insights" | Restate each contribution as a claim with its quantity | yes | Each bullet names a result, a number or an artifact. |
| C17 | Fabricated or garbled reference | A DOI that resolves to another paper, a plausible title nobody published | Run `scripts/verify_citations.py`; fix or mark `[VERIFY]` | yes | Mandatory check outside the humanize pass; never repair a citation by guessing. |
| C18 | Audit or defensive voice | "this was verified rather than assumed", "the pipeline was confirmed to", sentences arguing with an imagined reviewer, repository chatter | State the design fact once where the reader needs it; move process detail to Methods or an appendix | with care | Keep reproducibility facts and mandated statistics reporting; delete governance language and self-congratulation. |

## B. Vocabulary

| Id | Pattern | Looks like | Repair | Safe? | Rule |
|---|---|---|---|---|---|
| V1 | General AI-vocabulary cluster | delve, tapestry, realm, intricate, meticulous, pivotal, underscore, showcase, foster, bolster, vibrant, multifaceted, holistic | Use the plain verb or noun, or cut | with care | Act on three or more in a paragraph; one word proves nothing, and single words age out within a year. |
| V2 | Academic excess vocabulary | elucidate, delineate, unveil, noteworthy, seamless, invaluable, "shed new light", "warrants further investigation", "a deeper understanding of" | Say what was found or done | yes | Mined from abstracts, so it is the right list here; never ban ordinary words such as across, within, findings or potential. |
| V3 | Copula avoidance | "serves as", "stands as", "represents", "functions as", "boasts" | Use is, are, has | yes | Plain "is" is normal scholarly prose; repair on sight. |
| V4 | Synonym cycling | participants, then subjects, then individuals, then the cohort, all for one group | Pick one term and repeat it | yes | One term per concept; repeating a defined term is correct and is the highest-value fix in a paper. |
| V5 | False range | "from X to Y" joining things that are not on one scale | List the items, or name the real span | yes | Keep real ranges such as "from 8 to 64 layers". |
| V6 | Filler phrase | "It is worth noting that", "in order to", "due to the fact that", "at the present time" | Delete or shorten | yes | Delete the frame and keep the sentence it introduced. |
| V7 | Business jargon | lean into, deep dive, game-changer, synergy, actionable | Plain verb | yes | Rare in papers; "scalable" and "ecosystem" can be technical, so read context. |
| V8 | Ornamental adverb | markedly, strikingly, remarkably, truly, genuinely | Delete, or give the number the adverb stands in for | with care | Keep functional adverbs: independently, randomly, significantly-with-a-test. |
| V9 | Vague connection | "associated with", "linked to", "tied to" used for a specific relation | Pick the verb that names the relation (predicts, increases, mediates) | with care | In observational work "associated with" is the honest word; never upgrade it to a causal verb. |
| V10 | Field-specific word tics | "Beyond,", "via", non-locative "where", "yield", "Given" repeated | Vary only where the same word recurs within a few lines | with care | These are conventions in many subfields; check how published papers in your venue write. |

## C. Structure and staging

Structure first: this group carries the strongest signal and is the first thing a rewrite should touch. Rows S1 to S7 are document shape; S8 to S16 are sentence-level staging.

| Id | Pattern | Looks like | Repair | Safe? | Rule |
|---|---|---|---|---|---|
| S1 | Uniform sentence rhythm | Every sentence 15 to 25 words; low coefficient of variation | Merge supporting sentences, trim others, vary openings | with care | Never merge two claim sentences, never create staccato; Methods may be uniform by nature. |
| S2 | Uniform paragraph or section length | Every subsection is three paragraphs of four sentences | Let the material set the length | with care | Do not pad to vary; Methods detail is not padding. |
| S3 | Connective paragraph openers | More than a third of paragraphs open with Moreover, Furthermore, Additionally | Open on the claim; keep a connective that names a real relation | with care | Preserve however, thus, in contrast when they mark a real logical turn; cap runs of identical openers at two. |
| S4 | Preview and restate | Intro lists the sections; each section's first sentence echoes its heading | Say the thing once | with care | The one roadmap sentence in the Introduction is a venue convention and stays; remove the echoes inside sections. |
| S5 | Closing loop | Conclusion repeats the Introduction in the same words with no new fact | Add a limitation, a number or a next step; cut the rest | with care | Conclusions restate by design; require at least one new element. |
| S6 | Over-explaining | A second or third sentence after the evidence restating what it meant | Cut the repeats; move speculation about mechanism to Discussion | with care | Keep the one sentence per paragraph that ties the numbers to the claim they support (W74); a Results paragraph without it is a list of numbers. Never delete the only sentence stating the mechanism. |
| S7 | Forced triad | Three adjectives, three examples, three clauses by reflex | Keep the strongest one or two | with care | Keep real triads, such as three measured metrics. |
| S8 | Negative parallelism | "not only X but also Y", "it is not X, it is Y", "This does not mean X. It means Y." | State the positive claim | with care | Keep when both halves carry a fact (method A against method B); cut when the negative half is a claim nobody made. |
| S9 | One-line closer | "That is the real win.", "Let that sink in.", dramatic fragments | Delete | yes | Cut when it restates the paragraph above. |
| S10 | Run-up | "Let us dive in", "Here is the thing", "In this section we will explore" | Delete the run-up | yes | Keep the one-sentence roadmap venues expect; delete all other throat-clearing. |
| S11 | Rhetorical question setup | "Why does this matter? Because..." | State the answer | yes | Interrogative openers that frame the analytic question are legitimate in Introduction and Discussion; do not add them either. |
| S12 | Stacked hedge | "may potentially suggest the possibility that" | Collapse to one hedge: "may suggest" | with care | Never remove the last hedge; never turn "suggests" into "shows". |
| S13 | Clause-stacked sentence | More than 30 words with three or more subordinate clauses; piled noun compounds | Split at the logical seam; expand compounds on first use | with care | Split without hiding which condition belongs to which comparison. |
| S14 | Repeated sentence openers | Five sentences in a row opening "We then...", "The model..." | Reorder or merge only where the sequence is not a procedure | with care | Procedural steps in Methods may repeat; leave them. |
| S15 | Register shift between sections | Generic Methods and specific Results, or the reverse | Audit per section; raise the vague one to the other's level of detail | yes | A pronounced shift is a stronger tell than any phrase; fix it with true detail, never with flourish. |
| S16 | Question-format headings | "Why Does X Fail?" | Use a descriptive heading | with care | Some venues like them; follow the template and the author profile. |
| S17 | List standing in for an argument | Findings, reasons or steps as bullet fragments with no sentence saying how they connect | Rewrite as prose that states the links (because, unless, which rules out); keep a list only for parallel, separable items | with care | Contribution lists, datasets and hyperparameters may stay lists, with one sentence saying what they add up to (W75). |
| S18 | Private vocabulary | Letter codes or nicknames for conditions ("arm B", "C2", "the canary run") that the reader must decode in every sentence | Report it and route to `write` or `revise`: renaming is a terminology edit | no (route) | Replace with plain descriptions and record them in the glossary table (W73); never rename inside a humanize pass, because the verification script reads each removed code as a dropped fact. |
| S19 | Number dump | A paragraph of values in "X reads a against b" form with no sentence saying what they show | Report it and route to `write`: the values move to a table and the prose keeps the one to three that carry the claim | no (route) | Moving numbers is a content edit; a humanize rewrite must keep every number (W74, I7). |

## D. Punctuation and format

| Id | Pattern | Looks like | Repair | Safe? | Rule |
|---|---|---|---|---|---|
| P1 | Em-dash overuse | A dash as the universal connector, several per paragraph | Replace with the punctuation that names the relation: comma, colon, parentheses, full stop | with care | Capped, never banned by rule: none in the abstract, at most one per paragraph elsewhere; range dashes are exempt; follow the venue and the author profile. |
| P2 | Bold-label lists and bare-noun bullets | "**Robustness**: ..." rows in a LaTeX paper | Convert to prose, or keep a real contribution list | with care | Papers seldom use them; a contribution list may. |
| P3 | Decorative headings, emoji, rules, forced Title Case | Emoji in a heading, a horizontal rule between sections | Remove | no | The template controls heading case; fix only stray Markdown that leaked into LaTeX. |
| P4 | Mixed quote marks | Curly and straight quotes after pasting | Normalise to what the source format uses | no | LaTeX sets quotes; aim for consistency only, and never alter quoted material. |
| P5 | Hyphenation drift | "high-quality" after the noun, inconsistent compound modifiers | Follow the house style | with care | Standard hyphenation rules decide; do not change terms of art. |
| P6 | Colon reveal and exclamation | "The answer is:", "The key takeaway:", exclamation marks | Write the sentence | yes | Colons that introduce a real list or definition stay. |
| P7 | Unicode obfuscation | Homoglyphs, zero-width characters, odd spaces | Remove and normalise | yes | Invisible characters break search and signal evasion; clean them whatever their origin. |

## E. Leftovers and hygiene

| Id | Pattern | Looks like | Repair | Safe? | Rule |
|---|---|---|---|---|---|
| L1 | Chatbot residue | "I hope this helps", "Certainly!", "Would you like me to..." | Delete | yes | Never belongs in a paper. |
| L2 | Cutoff or availability disclaimer | "As of my last update", "specific details are limited" | Delete, then supply the fact or mark `[VERIFY]` | yes | Do not fill the gap from memory. |
| L3 | Markup and reference leaks | `oaicite`, `contentReference`, `utm_source=chatgpt.com`, `[Your Name]`, stray Markdown in LaTeX | Delete and re-source the claim | yes | Mandatory; a leaked citation token often marks an unverified claim. |
| L4 | Writing about the document | "This section was generated to...", "compiled from the above" | Delete | yes | The paper never describes how the text was produced; tool use goes in the disclosure line. |
| L5 | Reasoning-chain residue | "First, let me consider...", "Wait, actually" | Delete | yes | Remove, then re-read the paragraph for gaps. |

## Not tells in a paper: do not act

Several popular lists flag the items below. A paper needs them, and flagging them produces false repairs.

| Item | Why it stays |
|---|---|
| Formal, academic register | Formality is not an AI marker; lists that name it as one are wrong for this genre. |
| Evidence-tied hedging ("may", "suggests", "preliminary") | The venue and the evidence require it; the tell is generic hedging with no evidence attached (C10, S12). |
| Passive voice in Methods | A convention where the agent is irrelevant; keep it. |
| "The results show / suggest" | Standard scientific phrasing, even though some lists call it false agency; leave it. |
| "We" | Normal in CS, ML and many sciences; keep it. |
| Standard connectives followed by data | However, thus, in contrast mark real logic; see S3. |
| Perfect grammar and plain prose | Not evidence of anything. |
| Semicolons and colons in moderation | Ordinary punctuation. |
| Statements that look unsourced | They may be the author's own result; check, do not assume. |
| "Perplexity injection": swapping predictable words for surprising ones | It lowers precision and the strongest detectors do not reward it; precision beats surprise. |
| Defined-term repetition | Correct practice (V4). |
| Readability grade and "reading level" flags | A research paper reads at a high grade by design; ignore the number. |

## Keep what carries a person

A rewrite that removes these makes the text cleaner and worse, and it also scores worse on structure. Leave them:

- an oddly specific detail, such as a particular seed, a run date, or a number that is strange because it is true;
- an unresolved tension stated honestly ("we do not know why this happens");
- a hedge the author chose on purpose, and its position;
- a short sentence that states a claim outright;
- a first-person choice the author can defend ("we chose X because Y");
- a limitation that stings;
- phrasing that is unusual but correct, especially from a non-native writer: raise it as a question to the author, never as a defect.

## When not to act

Act on nothing in these cases:

- Quoted text, titles, proper names, and passages that discuss a phrase rather than use it.
- Math, LaTeX commands, labels, references, code, and tables.
- Text written before late 2022: the author wrote it, and many of these habits are older than chatbots.
- A passage with a single weak tell and nothing else.
- A section whose rhythm and specifics already look like the author's own: say in one line that nothing needs doing and return it unchanged.
- Any edit that would add, drop or alter a number, a citation, a hedge that carries meaning, or the strength of a claim. Those are not style edits; send them to the evidence or write modes.

## Maintenance notes

Vocabulary lists in group B are the most perishable part of this file: a word can fall out of use within a year, and newer models suppress some habits on their own. Treat the structure and staging rows as durable and the vocabulary rows as examples of a cluster, not as a vocabulary to ban. When a venue or field disagrees with a "safe" verdict here, follow the venue and record the exception in the author profile.
