# Literature review mode

Build a verified, venue-aware picture of the prior work around the project, so the paper positions itself against what exists and cannot be scooped by a paper you missed. Read `paper/PROJECT_CONTEXT.md` and `paper/CLAIMS.md` first: the review serves the claims, not the topic in general.

## Contents

- Principles
- Step 1: define the axes
- Step 2: the search protocol
- Step 3: per-paper notes
- Step 4: the verification rule
- Step 5: the scoop check
- Step 6: closest prior work
- Step 7: the must-cite table
- Step 8: venue-fit reading
- Step 9: parallel scouts
- Step 10: handoff to references.bib
- Outputs and state updates

## Principles

- A reference that does not exist, or that says something other than what you attribute to it, damages the paper more than a missing one. Verify before you cite, every time.
- The goal is positioning, not coverage. A reader wants to know what is known, what is contested, and what this paper adds. Collect only what bears on a claim in `CLAIMS.md`.
- Keep a record of how you searched. A reviewer who asks "did you check X?" gets an answer from the query log.
- Reviewers are often the authors of related work. Cite generously and describe other work fairly; a one-line dismissal of a likely reviewer's paper costs more than it saves.
- If the project already has a literature folder or a notes file, read it and extend it. Do not restart the search from scratch.

## Step 1: define the axes

Split the topic into 3 to 6 axes, each one a question the paper must answer for the reader. Derive them from the claims, for example:

- Axis A: the phenomenon (what has been observed before in this setting).
- Axis B: the method family (what techniques measure or produce it).
- Axis C: the competing explanation (what else could account for the result).
- Axis D: the evaluation practice (which benchmarks, controls and statistics the field accepts).
- Axis E: the venue's own conversation (what this community has published recently).

Write the axes into `paper/litreview/AXES.md` with one line each on why it matters to a named claim id. Axes are what you later hand to scouts, so make them non-overlapping.

## Step 2: the search protocol

For each axis, run the same three passes and log every query.

1. Seed papers. Ask the user for 3 to 8 papers they already consider central. Add any the project's own notes cite. These anchor the search.
2. Citation chasing. For each seed, read its related work, then look at who cites it (Semantic Scholar, OpenAlex, Google Scholar, an arXiv "cited by" view). Follow backward references for foundations and forward citations for the newest work. Stop an axis when two consecutive rounds surface nothing new.
3. Keyword sweeps. Search 4 to 10 phrasings per axis, including the field's synonyms and the older terminology. Search the venue's proceedings and the arXiv listing for the last 12 months, since the newest work is the scoop risk.

Keep the log in `paper/litreview/QUERY_LOG.md`:

```
| date | axis | source | query | hits scanned | kept | note |
```

A query with zero kept hits is still worth logging; it documents a negative.

## Step 3: per-paper notes

Write one note per kept paper in `paper/litreview/notes/<citekey>.md`, using the format below. Parallel scouts (Step 9) write to their own `paper/litreview/axis_<letter>/notes/` first; the merge copies the kept notes here. Answering "why" first stops you from summarising a paper without understanding what it was for.

```
# <citekey>: <title>
Status: verified | unverified      Checked: <date>      URL: <page you opened>
Authors / year / venue:
WHY it was written: the problem or gap the authors were responding to
HOW: the method or setup, in two or three sentences
WHAT it found: the result, with the number or the qualitative finding
Relation to us: supports | contradicts | reframes | scoops | background
  Which claim id it touches: C3
  One sentence on the difference between their setting and ours
Anchor: a quote or span (<= 25 words) with page or section
```

"Scoops" means the paper reports the same claim, in a comparable setting, before you. "Reframes" means it gives the same data a different explanation. Mark both loudly, because they change the paper's framing.

## Step 4: the verification rule

A reference counts as verified only when you opened its authoritative page in this session: the arXiv abstract page, the publisher or proceedings page, the DOI landing page, or an OpenReview or PMLR page. Record the URL in the note.

- Check that title, author list, year and venue on the page match your note. Two real papers blended into one entry is a common failure.
- Check that the paper says what you attribute to it. Search the text for the claim, not just the abstract.
- If you could not open a page, set `Status: unverified` and carry `[unverified]` wherever the reference appears. Never fill in authors, years or venues from memory.
- A search-engine snippet or a model's recollection is not verification.
- Prefer the published version over the preprint when both exist, and cite it; if only the preprint exists, cite the preprint with its id.

## Step 5: the scoop check

Run this near the start, again before writing related work, and again before submission, because the window moves.

1. State the window: from the date the project's earliest result existed to today.
2. Re-run the sharpest three queries from each axis, limited to that window, on arXiv and the venue's listing.
3. For each hit, read enough to decide: same claim, same setting, same evidence? Record `scoop-risk: none | partial | full` with the paper id and the date checked.
4. A partial scoop usually means reframing the contribution around what remains different. A full scoop is a decision for the user. Present it in the output contract; never bury it.

## Step 6: closest prior work

For each of the one to three closest papers, write a paragraph with this shape. It is the paragraph reviewers read hardest.

1. What the prior paper did, in one sentence, in their terms.
2. What it did not do or could not show, stated fairly.
3. What this paper does that differs, as a claim with an evidence pointer.
4. One sentence on what the two together suggest.

If the honest answer to point 3 is "very little", say so to the user before the paper is written.

## Step 7: the must-cite table

Maintain `paper/litreview/MUST_CITE.md`:

```
| citekey | why it must appear | where in the paper | status (verified/unverified) |
```

Include the origin paper of each method used, the standard benchmarks or datasets, the closest prior work, any paper whose result this one contradicts, and the venue organisers' own relevant work when it is on topic. Omitting a foundational reference is a visible gap; padding with tangential ones is a visible tell.

## Step 8: venue-fit reading

Read 4 to 8 recent papers from the target venue, including any award or spotlight papers the venue lists. Note their length, how they open, how they treat limitations, how many references they carry, and the vocabulary the community uses for your topic. Adopt the community's terms where they fit, since a reader scans for them. Record the observations in `paper/litreview/VENUE_FIT.md`. If the venue is not chosen yet, say so and list candidates with the evidence for each.

## Step 9: parallel scouts

When there are three or more axes, run one scout per axis in parallel, using `agents/scout.md` as the prompt. Give each scout:

- the axis question and the claim ids it serves,
- the seed papers,
- the note format and verification rule above,
- its output folder, `paper/litreview/axis_<letter>/`, and instructions to write only inside it (its own `notes/` and `QUERY_LOG.md`).

Scouts return their notes plus a closest-prior-work verdict for the axis. Merge on return: copy each kept note into `paper/litreview/notes/`, one file per citekey; where several axes kept the same paper, keep the verified, most complete note; resolve any note where two scouts disagree about what a paper says by opening it yourself; write the combined `paper/litreview/QUERY_LOG.md` from the per-axis logs, keeping the axis column; and rebuild the must-cite table. Leave the `axis_<letter>/` folders in place as the scouts' raw record. Never accept a scout's reference as verified because the scout said so; spot-check at least three per axis by opening the page.

## Step 10: handoff to references.bib

1. For each verified note, take the BibTeX from the publisher, DOI or arXiv export, not from memory. Keep the entry's key equal to the note's citekey.
2. Mark any entry from an unverified note with a `note = {[VERIFY]}` field so the submission check catches it.
3. Run `python3 <skill>/scripts/verify_citations.py paper/references.bib --online --out paper/litreview/CITATION_REPORT.md`. Treat `mismatch` and `unresolved` as work items. If the script cannot go online, it warns and still gives the offline checks; say so in the output.
4. Resolve every `mismatch` by opening the page. Do not delete an entry just because the script flagged it; the script is a screen, not a judge.

## Outputs and state updates

Files written under `paper/litreview/`: `AXES.md`, `QUERY_LOG.md`, `notes/*.md`, `MUST_CITE.md`, `VENUE_FIT.md`, a `SYNTHESIS.md` (one page per axis: state of knowledge, the gap, where the paper sits), the scouts' `axis_<letter>/` folders when Step 9 ran, and `paper/references.bib` updated.

Update `PROJECT_CONTEXT.md`: the closest prior work, any scoop verdict, and the Status line. Append to `LAB_LOG.md`: "Litreview ran on <date>; produced <files>; decisions: <framing changes>; open: <unverified references, scoop questions>". End with the output contract from SKILL.md.
