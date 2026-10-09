# Claims ledger

<!-- One row per claim. Never delete a row; change its status and log why in LAB_LOG.md.
     Type values: existence | systematic | hedged | narrow | guarantee (claim types in references/hypothesis.md).
     Verdict values (output of the evidence check): Supported | Partially supported | Not supported | Equivocal.
     Status values: established | supported | equivocal | retired | exploratory, set from the verdict by the
     mapping in references/evidence.md (definitions in references/hypothesis.md). Exploratory means the claim
     was not stated as a hypothesis before looking at the data.
     Test fixed in advance: whether the test and its criterion were fixed before the run (pre-registered,
     fixed in code, stated in prose, with where and when) or chosen afterwards (post hoc). Exploratory claims are always post hoc.
     In paper: main | appendix | no.
     A claim with no evidence file is not a claim yet; list it under Open items. -->

| id | claim (plain words, with direction and scope) | type | falsifier | verdict | status | evidence file(s) | number source (macro, or file + field) | test fixed in advance? (pre-registered / fixed in code / stated in prose / post hoc; where, when) | caveat | In paper | where in the paper |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | | | | | | | | | | | |
| C2 | | | | | | | | | | | |

<!-- Example row (do not copy into the table above):
| C1 | Removing the late-layer heads lowers accuracy on held-out items for model M | systematic | accuracy drop under 0.05 against random heads | Supported | supported | results/exp1.json | `\numExampleRate` | fixed in code, commit abc1234, 2026-01-10 | one model only | main | Section 4, Figure 2 |
-->

## Open items

<!-- Statements the team believes but cannot yet back with a result file. -->

- 

## Retired claims

<!-- Move a row here in addition to changing its status, with the date, the bar it failed, the observed value and the margin by which it missed. -->

| id | date retired | bar | observed | margin | how the paper reports it |
|---|---|---|---|---|---|
| | | | | | |
