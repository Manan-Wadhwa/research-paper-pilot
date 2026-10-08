# Submit mode

Run the final gate before a paper leaves the building. This mode is triggered only by the user ("is this ready to submit", "submission checklist", "anonymize", "arXiv version"); never start it on your own, because it freezes decisions and the fourth human checkpoint belongs to the user. The mode finds problems and reports them; it does not submit anything and never certifies that a paper will be accepted or complies with a policy it has not read.

## Contents

- Step 1: fetch the venue rules
- Step 2: run the mechanical checks
- Step 3: the manual checklist
- Step 4: anonymity scrub
- Step 5: statements and disclosures
- Step 6: final numbers and citations audit
- Step 7: the reading tests
- Step 8: packaging
- Step 9: the decision record
- Outputs and state updates

## Step 1: fetch the venue rules

Open the venue's official call for papers or author instructions page in this session. Record in `paper/SUBMISSION_CHECKLIST.md`: the URL, the date you checked, the page limit and what counts toward it (references, appendix, checklist), the template and style file name as the venue names it, the anonymity rule, the supplementary-material rule, the mandatory statements, and the deadline with its time zone.

Do not guess any of this from last year's rules or from memory. Style-file names and limits change between years, and a derived filename that looks right can be wrong. If the page cannot be opened, write "unverified" next to the item and ask the user to confirm it; do not fill in a plausible value.

If the venue is not chosen, ask once. If the user has no venue yet, run the generic items and mark every venue-specific item "not checked (no venue)" in the checklist.

## Step 2: run the mechanical checks

```
python scripts/check_submission.py paper --venue-pages <N>
python scripts/check_numbers.py paper/main.tex --numbers paper/numbers.tex --results-dir results
python scripts/verify_citations.py paper/references.bib --online --out paper/CITATION_REPORT.md
python scripts/prose_gate.py paper/main.tex --academic
```

`check_submission.py` covers: every `\ref` and `\cite` resolves; the bibliography holds only cited entries; no `[VERIFY]`, `TODO`, `XXX` or `FIXME` remains; figure files exist and are referenced; an anonymity grep for names, repository URLs and phrases like "our previous work"; the page count of a compiled PDF; whether a checklist file is present; stub sections and long verbatim blocks of pasted script output; and, from the compile log, overfull boxes where text runs past the margin. Read its output in full and fix what it finds. A script that cannot run prints a warning; list those warnings in the checklist as "not checked" rather than treating them as passes.

Compile the paper from a clean state and read the log for undefined references, overfull boxes and missing fonts. The log tells you what the venue's build will see. Then render every page of the PDF to an image and look at it, appendix included: clipped text inside figures, tables or verbatim running off the page, a section that is only a heading and a sentence, and figure text too small to read at print size. The log misses most of these, and reviewers see all of them.

## Step 3: the manual checklist

Fill `templates/SUBMISSION_CHECKLIST.md`. Items the scripts cannot decide:

- Every claim in the abstract and introduction is in `CLAIMS.md` with a status that supports its wording; no claim is stronger than its ledger row.
- Pre-registered versus post hoc results are labelled once, where each is first reported, and in a status table; the label, bar and amendment history are not repeated in every sentence.
- The paper reads without a glossary: no letter codes or project nicknames in prose, each condition explained by its role where it enters, and a fresh reader can follow a random Results paragraph after the abstract and introduction (W73).
- Raw script output, logs, commit hashes and internal file names are in the released code, not pasted into the paper (W77).
- No leaked process voice: no file paths, run names, "locked", "verified" or "PASS" labels, no developer commentary in the prose or captions.
- Limitations appear once, as scope, and point forward.
- Figures read in grayscale and at column width; captions state the takeaway.
- The page limit is met with the real template, not a shrunk one. Do not edit the style file or squeeze margins and spacing to fit.
- Code, data and model availability statements say what is actually released and when; no promise the authors cannot keep.
- Compute, seeds and hyperparameters are stated well enough for reimplementation.
- Ethics, broader-impact or reproducibility checklist answers are filled in honestly, each with a pointer to where the paper supports the answer. An answer of "yes" with no pointer is a defect. Read each question in the venue's own checklist; do not answer from a remembered version.

## Step 4: anonymity scrub

Skip this step only if the venue is single blind or open, and say that you skipped it and why. Otherwise check, beyond what the script greps:

- Author names, affiliations and emails in the text, headers, footers, PDF metadata and figure files (embedded text and image metadata).
- Acknowledgements and funding lines, which usually go in only after acceptance.
- Repository, branch, dataset and model-hub URLs that carry a username or organisation; use an anonymised mirror if the venue allows one.
- Self-citations written in a way that reveals identity ("in our earlier work"); cite in the third person.
- Supplementary files: archive names, notebook outputs, log paths containing a home directory, git history in an included repository.
- Comments left in the LaTeX source if the source is uploaded.

A name that appears in the bibliography as a normal citation is fine; the problem is wording that tells the reader the authors are the same.

## Step 5: statements and disclosures

- LLM and AI-tool use: read the venue's policy and write the disclosure the policy requires, in the place it requires. State what the assistance was (for example code, analysis scripts, drafting, language editing) at the level the policy asks. This skill edits style and clarity; it does not certify human authorship and is not a way around a disclosure rule (invariant I8). If the policy is unclear, quote the unclear sentence to the user and let them decide.
- Reviewer-confidentiality rules: if the user will be reviewing for the same venue, remind them that review material may not be put into outside tools.
- Data and code licences, human-subjects or consent statements, and conflicts of interest where the form asks.

## Step 6: final numbers and citations audit

This is the last time numbers can change without a decision.

1. `check_numbers.py` shows no literal in prose or captions that is not a macro or an allowed constant, and every flagged "no result file" item is explained.
2. Re-run the zero-context numbers audit from review mode (`agents/numbers-auditor.md`) on the final `.tex`, because edits since the last review may have introduced drift. Give it only the `.tex` and the result files.
3. `verify_citations.py` reports no `mismatch` or `unresolved` that you have not opened and resolved by hand. Check that every citation sentence still says what the cited paper says; a bibliography can be valid while a sentence misuses it.
4. Re-run the scoop check from `references/litreview.md` for the last window, since a new preprint can change the framing.

## Step 7: the reading tests

- Read the paper aloud, or have text-to-speech do it. Stumbles mark sentences that are too long, undefined terms and broken logic that silent reading skips.
- Fresh-reader test: give an agent that has seen nothing from the project only the final PDF text and ask it for a three-sentence summary of the contribution, the single most doubtful claim, and any term it could not follow. Compare its summary with the user's identity sentence in `PROJECT_CONTEXT.md`. A mismatch means the abstract is not doing its job.
- Chain human readers one at a time if time allows: an outsider for framing, an expert for correctness, and the senior author last, each told what to look for.

## Step 8: packaging

- Venue upload: the main PDF built by the venue's template, the supplementary archive if allowed, and any separate checklist file. Confirm file-size and format limits on the venue page.
- arXiv, if the user posts there: check the venue's preprint policy first, including whether a double-blind rule limits posting. Package the `.tex` sources with the compiled bibliography file the build needs, remove comments and unused files, make sure figures are included in a supported format, and compile once from the packaged folder before uploading. Keep the archive small. Decide the licence the user wants and do not choose it for them.
- Keep a tagged copy of exactly what was submitted: a git tag or a zipped folder, named by date, so a later revision can be diffed against it.

## Step 9: the decision record

Write to `LAB_LOG.md` the decision to submit: date, venue, which version (commit or archive name), who approved, the checks run with their results, and the items knowingly left open with the reason. The user makes that decision; record it in their words. Update `PROJECT_CONTEXT.md`: status "submitted to <venue> on <date>", the locked decision, and what remains (rebuttal window dates, camera-ready needs).

## Outputs and state updates

Files: `paper/SUBMISSION_CHECKLIST.md` (filled), `paper/CITATION_REPORT.md`, the script outputs pasted or linked, the submitted archive or tag. Append to `LAB_LOG.md`: "Submit mode ran on <date>; produced <files>; decisions: <go or no-go and why>; open: <items>". End with the output contract from SKILL.md; the next mode is `revise` when reviews arrive.
