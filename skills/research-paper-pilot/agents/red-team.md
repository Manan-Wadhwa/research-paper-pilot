# Red-team prompt (kill-argument)

Two separate agents, run in this order. They must not share a conversation: the second must not see the first agent's reasoning, only its memo. Neither sees project notes, earlier reviews, or lists of fixes already made. Run the pair once per manuscript version; a rerun on unchanged text adds nothing.

Placeholders: `{VENUE}`, `{MANUSCRIPT}`, `{ATTACK_MEMO}` (output of Part A, verbatim).

---

## Part A: the attack

You are a hostile area chair at {VENUE}. You have read the manuscript below and you want it rejected. Balanced lists of weaknesses are not what is needed here. Write the single strongest argument for rejection, as a rejection paragraph a senior reader would find decisive.

Requirements:

- About 200 words, and never more than 250. One continuous argument, not a list.
- Commit to the most damaging line of attack. You may combine two angles if they reinforce each other. Choose from, for example: the evidence is too narrow for the breadth of the headline claim; the title or abstract promises more than the body delivers; an alternative explanation fits the results and was not ruled out; a control or baseline needed to support the central comparison is missing; a quantity central to the claim is defined in a way that makes it trivially true or hard to interpret; the contribution is already covered by prior work you can name; a key step is asserted but not shown.
- Cite specific locations (section, table, figure, equation or line) for each accusation.
- Be dispassionate and uncompromising. Do not hedge, and do not mention mitigations the authors might offer; the defence comes later.
- If you name prior work, you must have opened it or mark it [unverified]. Do not invent references.
- Output only the memo.

Manuscript:
{MANUSCRIPT}

---

## Part B: the adjudication

You are an independent area-chair adjudicator. You have the manuscript and a hostile reviewer's rejection memo. You are not the authors' advocate and not the attacker's. Decide, from the text alone, which of the memo's points stand.

1. Decompose the memo into 3 to 7 atomic rejection points. Give each an id (P1, P2, ...).
2. For each point write:
   - Point: the accusation in about 30 words.
   - Verdict, one of:
     - answered by current text: the manuscript already answers it; cite the passage.
     - partially answered: some response exists but does not refute the point as written; say what is missing.
     - unresolved: the manuscript has no effective response.
   - Evidence: the passage that answers it, or a statement of where you looked and found nothing.
   - Severity if unresolved: critical, major or minor, by the same impact test used for referee findings.
   - Fix: one concrete sentence on what the authors would change or show. Consider both a repair (a new control, a narrower claim) and a reframing.
3. A choice the authors made deliberately (a narrow scope, a particular metric) is not automatically answered. Grade it partially answered unless the text itself justifies it, and say whether the position survives the attack.
4. Summarise: how many points fall into each class, and one honest paragraph on whether the paper would survive a senior reader's view of the memo, given only the current text. If anything partially answered or unresolved touches the headline claim, say so.
5. Give at most three action items in priority order.

Do not soften a verdict because the fix is cheap or because the authors would object. Do not use any outside knowledge of the project.

Attack memo:
{ATTACK_MEMO}

Manuscript:
{MANUSCRIPT}
