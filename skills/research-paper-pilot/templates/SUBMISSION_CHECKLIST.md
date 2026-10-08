# Submission checklist: <paper short title>

Venue: <name>   Track: <main / workshop / other>
Rules source: <official URL>   Date checked: <YYYY-MM-DD>   (items below not confirmed on the official page are marked "unverified")
Deadline: <date and time with time zone>
Manuscript version: <commit, tag or archive name>

## 1. Venue rules (from the official page)

| item | value from the page | unverified? |
|---|---|---|
| Page limit and what counts toward it (references, appendix, checklist) | | |
| Template and style file name as the venue names it | | |
| Anonymity rule (double blind / single blind / open) | | |
| Supplementary material rule | | |
| Mandatory statements and checklists | | |
| LLM or AI-use disclosure rule and where it goes | | |
| Preprint posting policy | | |
| File size and format limits | | |

## 2. Mechanical checks

Run `python scripts/check_submission.py paper --venue-pages <N>` and record each result. A check that could not run is "not checked", never "pass".

- [ ] Every `\ref` and `\cite` resolves
- [ ] The bibliography holds only cited entries
- [ ] No `[VERIFY]`, `TODO`, `XXX` or `FIXME` remains in text, captions or bibliography
- [ ] Every figure file exists and every figure is referenced in the text
- [ ] Anonymity grep is clean (names, repository URLs, "our previous work", branch names)
- [ ] Page count within the limit with the unmodified venue template
- [ ] `check_numbers.py`: no literal numbers outside macros except allowed constants; each "in no result file" item explained
- [ ] `verify_citations.py`: no unresolved `mismatch` or `unresolved` entry left unexamined
- [ ] `prose_gate.py --academic`: findings reviewed
- [ ] Clean compile, log read for undefined references and overfull boxes

## 3. Content checks

- [ ] Every claim in the abstract and introduction appears in CLAIMS.md with a status that supports its wording
- [ ] Pre-registered and post hoc results are labelled where they appear
- [ ] No process voice in prose or captions (paths, run names, "locked", "verified", "PASS", developer commentary)
- [ ] Limitations stated once as scope, each pointing forward
- [ ] Figures are readable in grayscale and at column width; captions lead with the takeaway
- [ ] Methods give enough detail to reimplement: hyperparameters, seeds, compute
- [ ] Statistics reported with method, n and intervals; multiple comparisons and clipping disclosed where relevant
- [ ] Code, data and model availability statement says what is actually released and when

## 4. Anonymity scrub (skip only for single blind or open venues; note why)

- [ ] Names, affiliations and emails removed from text, headers, footers and PDF metadata
- [ ] Embedded text and image metadata in figure files checked
- [ ] Acknowledgements and funding lines removed or deferred
- [ ] Repository, dataset and model-hub links anonymised
- [ ] Self-citations in the third person
- [ ] Supplementary archive checked (file names, notebook outputs, log paths, version-control history)
- [ ] LaTeX comments removed if source is uploaded

## 5. Statements and disclosures

- [ ] AI-tool use disclosed as the venue's policy requires (what the assistance was, where the statement goes)
- [ ] Venue paper checklist answered; each "yes" has a pointer to the supporting passage
- [ ] Ethics, consent, licence and conflict-of-interest statements complete where the form asks
- [ ] Reviewer-duty confidentiality reminder given to authors who will also review

## 6. Final audits

- [ ] Zero-context numbers audit rerun on the final `.tex` (output saved: <path>)
- [ ] Citation sentences spot-checked against the cited papers
- [ ] Scoop check rerun for the last window; verdict: <none / partial / full>
- [ ] Read aloud pass done
- [ ] Fresh-reader test done; its three-sentence summary matches the identity sentence: <yes / no, notes>

## 7. Packaging

- [ ] Main PDF built by the venue template
- [ ] Supplementary archive within limits
- [ ] Preprint package (sources, bibliography file, supported figure formats) compiled from a clean folder, if posting
- [ ] Tagged copy of exactly what was submitted: <tag or archive>

## 8. Open items knowingly left

| item | reason | owner |
|---|---|---|

## 9. Decision record

Decision to submit: <go / no-go>   Date: <YYYY-MM-DD>   Approved by: <name or role, in the user's words>
Reason and conditions: <text>
Copy this block to LAB_LOG.md and update the Status line in PROJECT_CONTEXT.md.
