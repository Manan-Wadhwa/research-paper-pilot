# Sources: the reading list behind the rules

## Contents

- How to use this list
- Core guides on writing ML papers
- Talks and slides
- Best-paper and research-craft advice
- Venue policies (check the live page before relying on these)
- Repackagings of the same advice
- Coverage notes

## How to use this list

Every rule in `style-rules.md`, `write.md` and `evidence.md` was re-expressed from one or more of these sources, or from the agent-skill packs listed in the repository's ATTRIBUTION file. Read a source when a rule needs its full argument, when the user wants the original, or before adding a rule. The "where it lives" column points to the part of this skill that carries the idea. Links were valid in October 2026; pages move, so search by title if one fails.

## Core guides on writing ML papers

| Source | Link | What it adds | Where it lives here |
|---|---|---|---|
| Neel Nanda, Highly Opinionated Advice on How to Write ML Papers | https://www.alignmentforum.org/posts/eJGptPbbFPZGLpjsp/highly-opinionated-advice-on-how-to-write-ml-papers | One to three claims, the narrative, claim type and strength, red-teaming evidence, pre vs post hoc, figures as the paper, iterative compress-then-expand | hypothesis.md ladders; evidence.md audit; write.md step 1; W1 to W7, W21 |
| Sebastian Farquhar, How to Write ML Papers | https://sebastianfarquhar.com/on-research/2024/11/04/how_to_write_ml_papers/ | Five-sentence abstract, Figure 1 placement, say what the reader should see before each experiment, read it aloud | W8, W19, W31, W60 |
| Jacob Steinhardt, Advice for Authors | https://jsteinhardt.stat.berkeley.edu/blog/advice-for-authors | Uncontroversial-then-surprising abstract opening, no vague hedges in the intro, theorem/proposition/lemma reservation, LaTeX habits | W8, W71, W54 |
| Zachary Lipton, Heuristics for Scientific Writing | https://www.approximatelycorrect.com/2018/01/29/heuristics-technical-scientific-writing-machine-learning-perspective/ | Delete the sentence that could open any paper, replace "performance" with the metric, hedge once, avoid incremental verbs for your own work | W9, W22, W43, W44 |
| Lipton and Steinhardt, Troubling Trends in Machine Learning Scholarship | https://arxiv.org/abs/1807.03341 | Explanation vs speculation, identify the sources of gains, mathiness, misuse of language (suggestive definitions, overloaded terms, suitcase words) | W65 to W68 |
| Ethan Perez, Easy Paper Writing Tips | https://ethanperez.net/easy-paper-writing-tips/ | Verbs early, fewer pronouns, no comparatives without the comparison, define terms, vary openers, filler list | W41, W42 |
| Pat Langley, Crafting Papers on Machine Learning | https://www.cs.williams.edu/~andrea/Carla/craft.html | State goals and tasks, dependent variables that contact the goal, lesion studies and learning curves, beyond bake-offs, informative headings, 3 to 6 sentence paragraphs, no single subsections | W36, W46, W66, W69, W70 |
| Gopen and Swan, The Science of Scientific Writing | https://cseweb.ucsd.edu/~swanson/papers/science-of-writing.pdf | Reader expectations: subject near verb, stress position at the end, old before new, action in the verb | W38 |
| Steve Easterbrook, How to write a scientific abstract in six easy steps | http://www.easterbrook.ca/steve/2010/01/how-to-write-a-scientific-abstract-in-six-easy-steps/ | A six-sentence abstract recipe: context, problem, why it is hard or what is missing, what you did, what you found, what it means. The page was behind a bot check when checked; recipe as commonly summarised | W8 (alternative formula) |
| Devi Parikh, Shortening papers to fit page limits | https://deviparikh.substack.com/p/shortening-papers-to-fit-page-limits-97601318681d | Tighten prose first, remove orphan lines, condense long sections, then figures, layout, negative space, supplementary last | W72 |
| Jennifer Widom, Tips for Writing Technical Papers | https://cs.stanford.edu/people/widom/paper-writing.html | Referenced by several guides; not read for this skill | none yet |
| Jakob Foerster, How to ML Paper; How to rebuttal; How to review | https://www.jakobfoerster.com/how-to-ml-paper | Embedded documents; not read for this skill | none yet |

## Talks and slides

| Source | Link | What it adds | Where it lives here |
|---|---|---|---|
| Simon Peyton Jones, How to Write a Great Research Paper (video and slides) | https://www.microsoft.com/en-us/research/video/how-to-write-a-great-research-paper-3/ and https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/How-to-write-a-great-research-paper.pdf | Write the paper first, one key idea ("one ping"), narrative flow at a whiteboard, structure with reader counts per section, introduction = problem plus contributions in one page, example-first, molehills not mountains, contributions as refutable claims with forward references, related work after the idea, put readers first, listen to readers | W61 to W64; write.md introduction section |
| Bill Freeman, How to write a conference paper (quoting Jim Kajiya) | https://courses.csail.mit.edu/6.869/lectnotes/lect23/lect23-slides.pdf | Reviewing is a bazaar, not a monastery; the most dangerous mistake is assuming the reviewer will understand the point; state the problem, context, what differs from prior work and the implications explicitly | W64 |
| Michael Black, Writing a good scientific paper | https://is.mpg.de/ps/news/writing-a-good-scientific-paper | Page blocked when checked; read via excerpts only | none yet |

## Best-paper and research-craft advice

| Source | Link | What it adds | Where it lives here |
|---|---|---|---|
| Nicholas Carlini, How to win a best paper award | https://nicholas.carlini.com/writing/2026/how-to-win-a-best-paper-award.html | One singular idea, formula abstract, story introduction, lead with the best-supported evidence, conclusion states the moral, read it aloud | write.md steps 1 and 3; W2, W30, W60 |
| Andrej Karpathy, A Survival Guide to a PhD | http://karpathy.github.io/2016/09/07/phd/ | The paper as a story, the title and Figure 1 carry the pitch | W31 |
| Ethan Perez, Tips for Empirical Alignment Research | https://www.alignmentforum.org/posts/dZFpEdKyb9Bf4xYn7/tips-for-empirical-alignment-research | Fast iteration, baselines first, write up negative results | evidence.md principles |
| John Schulman, An Opinionated Guide to ML Research | https://joschu.net/blog/opinionated-guide-ml-research.html | Problem selection and keeping a research log | understand.md (lab log), evidence.md |
| Richard Hamming, You and Your Research | https://www.cs.virginia.edu/~robins/YouAndYourResearch.html | Working on important problems; not a writing guide; not mined | none |
| Chris Olah and Shan Carter, Research Debt | https://distill.pub/2017/research-debt/ | Exposition as research work; the cost of undigested ideas | glossary-and-plain-language.md (spirit) |
| Jacob Steinhardt, Film Study for Research | https://bounded-regret.ghost.io/film-study-for-research/ | Learn by close reading of good papers; not mined | none |

## Venue policies (check the live page before relying on these)

| Venue document | Link | Why it matters |
|---|---|---|
| NeurIPS paper checklist guidelines | https://neurips.cc/public/guides/PaperChecklist | The checklist items the submit mode asks for |
| NeurIPS 2026 reviewer guidelines | https://neurips.cc/Conferences/2026/ReviewerGuidelines | What reviewers are told to look for; feed to the blind reviewer lens |
| NeurIPS 2026 Evaluations and Datasets guidelines | https://neurips.cc/Conferences/2026/EvaluationsDatasetsReviewerGuidelines | For benchmark or dataset papers |
| NeurIPS 2025 LLM policy | https://neurips.cc/Conferences/2025/LLM | Disclosure of LLM use; the humanize mode's disclosure line follows it |
| NeurIPS 2026 position track, AI-generated papers | https://blog.neurips.cc/2026/06/02/ai-generated-papers-in-the-neurips-2026-position-paper-track/ | Venue stance on AI authorship |
| Conference AI-agent policy FAQ (secondary source) | https://aicards.uni-goettingen.de/ai-agent-conference/ | Cross-venue summary; verify against each venue's own page |

The rule from `submit.md` applies: fetch the official call for papers, record the URL and the date checked, and never guess this year's limits from last year's.

## Repackagings of the same advice

These restate the guides above and add nothing the skill does not already carry: the `ml-paper-writing` skill on skills.sh (smithery), `ai-paper-writing` (jumyungpark), the claudecodehq playbook, and `research-paper-writing` in oh-my-skills. Useful as checklists, not as new sources.

## Coverage notes

Read in full when building the rules: Nanda, Farquhar, Steinhardt (blog), Lipton (blog), Lipton and Steinhardt (paper, via the HTML version), Perez, Langley, Peyton Jones (slides), Parikh, Carlini, Karpathy. Read via abstract or excerpt only: Gopen and Swan, Schulman, Freeman. Not read: Foerster, Widom, Black, Hamming, Film Study, the body of Research Debt, Easterbrook's page itself. Not covered by this skill's rules: pure theory papers, and systems- or vision-specific norms beyond what Freeman quotes.
