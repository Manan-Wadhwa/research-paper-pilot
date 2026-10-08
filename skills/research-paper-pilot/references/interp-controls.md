# Optional domain pack: controls for mechanistic interpretability papers

Read this file only when the paper's evidence comes from patching, ablation, probing, steering,
circuit analysis or lens-style readouts on a trained model. It is a checklist of controls and a
guide to what a methods section must state. It is one domain pack; other fields can add their own
beside it (a clinical-trial pack, a causal-inference pack, a benchmark-evaluation pack). If your
project is outside this domain, skip it.

Used by: `evidence` (claim verdicts and pre-registration notes), `write` (methods and limitations),
`review` (reviewer lens: methods and statistics), `revise` (answering "is this an artifact?").

## Contents

- Why this pack exists
- 1. Define the metric first
- 2. Sanity checks before any analysis
- 3. Choose the control that matches the claim
- 4. Floors and normalisation
- 5. Minimal pairs and alignment
- 6. Held-out discipline and sample size
- 7. Seeds, distributions and multiple comparisons
- 8. Faithfulness, completeness, minimality
- 9. Attribution patching is a screen, not a proof
- 10. Direction claims versus component-set claims
- 11. Ablation types
- 12. Lens and readout conventions
- 13. Probing and steering controls
- 14. Claim language for interpretability results
- 15. What the methods section must state
- 16. Ways to be confidently wrong
- Reporting checklist

## Why this pack exists

Interpretability results are easy to produce and easy to misread. A patched activation that moves
an output is not yet a mechanism; a probe that decodes a label is not yet evidence that the model
uses it. Most failures come from a missing control, a metric that hides a floor, or a claim worded
one rung higher than the experiment. The checklist below turns those failure modes into things to
verify before a result is allowed into CLAIMS.md as supported.

If an installed skill covers the code side (for example, a library-specific skill from the
maintainers of a tracing library), use it for implementation details and keep this file for the
design and reporting side. If it is not installed, continue with this file.

## 1. Define the metric first

- Pick one primary metric before looking at results (a difference between the two competing output
  scores is usually better than a raw probability, because probabilities saturate and hide
  movement).
- Express effects as a fraction of the gap between the two reference runs: effect = (patched minus
  corrupted) / (clean minus corrupted), so 0 means no recovery and 1 means full recovery. Say what
  the two reference runs are.
- State whether values outside 0 to 1 are clipped, and report how many were clipped. A normalised
  effect over 1 is a finding about the scale, not about a stronger mechanism.
- Write the metric in one formula in Methods and use one name for it everywhere (W45).

## 2. Sanity checks before any analysis

Run these three and record the result (even "ran, passed") in the lab log, because a wiring bug
looks exactly like a finding.

1. **No-op patch.** Patch an activation with itself. The output must not change. A change means the
   hook, indexing or batching is wrong.
2. **Extreme intervention.** Apply an intervention that must change the output a lot (replace the
   whole residual stream, or ablate every component). A small change means the intervention does not
   reach the output.
3. **Baseline reproduces.** The unmodified run reproduces the known behaviour in the same trace or
   code path used for the interventions. Without it, a "clean" baseline may differ in padding,
   precision or hook placement.

## 3. Choose the control that matches the claim

| Claim | Matching control |
|---|---|
| "Component X is important" | Random components of the same size, same layer type and, if relevant, same norm |
| "Direction d carries the feature" | Random directions of the same norm, and the orthogonal complement |
| "Probe decodes feature f" | Shuffled labels, and a probe on a random or untrained model |
| "Patching from donor A moves the output" | Control donors: the target's own activation (self-patch), positions that should not matter (suffix or padding), and a norm-matched random activation |
| "The effect is specific to this behaviour" | The same intervention on a different behaviour or prompt set |
| "The circuit explains the behaviour" | The empty circuit and random sets of equal size (see floors) |

The null must inherit the confound. If the effect set was chosen by selection on the same data, the
null must be selected the same way (or, better, evaluated on held-out data), otherwise the
comparison flatters the effect.

## 4. Floors and normalisation

Find the floor before normalising to it. Two floors matter in circuit work:

- the **corrupted baseline**: the output with no intervention on corrupted input;
- the **empty-circuit floor**: the output when the proposed circuit is kept and everything else is
  replaced, but the circuit is empty.

Say which floor each reported fraction is scaled against. Scaling a random-set control against the
wrong floor can make random sets look better (or worse) than they are, which silently changes the
meaning of "the circuit beats random". Report the raw values beside the normalised ones in the
appendix.

## 5. Minimal pairs and alignment

- Build pairs that differ in one factor. State the factor and how you verified nothing else varies.
- Assert equal token counts between the paired prompts at the positions being patched; a one-token
  shift moves every position-specific result.
- State how labels were obtained. If the model's own answers define the label (for example, which
  items it answers consistently), say so; it makes the label a property of the model and not of an
  annotator.
- Report how many candidate pairs were discarded by gating and why. A gate that removes half the
  pairs is part of the method.
- Match length, format and frequency across the two sides of a pair or give the residual
  difference.

## 6. Held-out discipline and sample size

- Selection data and evaluation data never mix. Choose components, thresholds and layers on one
  split and report on another, and say how the split was made.
- If the set is small, say so in the claim. As a rough guide, a few dozen prompts can support a
  qualitative existence claim; quantitative claims about effect size need more, and the interval
  should show it.
- Report the number of items per arm, not only the total. A second model or arm with a much
  smaller sample carries correspondingly weaker claims; label it as such.
- Do not generalise across model families without re-validating. A result on one family is a claim
  about that family until a second family confirms or contradicts it.

## 7. Seeds, distributions and multiple comparisons

- Where there is randomness (data order, random controls, resampling, initialisation), average over
  seeds and report the spread, with the number of seeds.
- Report distributions across layers, positions or components, not the peak. A sweep with hundreds
  of cells will produce a high maximum by chance; a peak is a hypothesis for a held-out test.
- Correct for multiple comparisons or label the analysis exploratory. For exploratory
  interpretability claims, be sceptical of any result that does not clear a stringent threshold, and
  prefer an interval and an effect size over a bare p-value.
- Report effect sizes, not only whether a threshold was crossed.
- State the interval method (bootstrap over items, over seeds, or analytic) and the resampling unit.
  Resampling over the wrong unit (tokens instead of items) gives intervals that are too narrow.

## 8. Faithfulness, completeness, minimality

Use these three words with fixed meanings when you claim a circuit:

- **Faithfulness**: keeping only the circuit (and replacing the rest) recovers the behaviour,
  measured against a floor and a random-set control.
- **Completeness**: removing the circuit removes the behaviour, so no parallel path carries it
  unnoticed. A faithful but incomplete circuit is a sufficient subgraph, not the mechanism.
- **Minimality**: each member earns its place; dropping any one member hurts. State how pruning was
  done and on which data.

Claim only the ones you tested. "Sufficient" and "necessary" are different experiments.

## 9. Attribution patching is a screen, not a proof

Gradient-based attribution is a linear approximation, cheap enough to rank every component at once
and unreliable where the response is saturated or non-linear. Use it to propose candidates, then
verify the shortlisted components by real activation patching. Do not put an attribution score in the
paper as if it were a causal effect, and say in Methods which numbers came from which method.
Agreement between the two on a held-out set is worth reporting as its own result.

## 10. Direction claims versus component-set claims

Separate these in the claim, the figure and the limitations:

- a claim about **a direction** in activation space (a vector that reads or writes a feature)
  needs controls with random directions and tests of causal use, not only decodability;
- a claim about **a set of components** (heads, neurons, layers) needs random-set controls and
  faithfulness and completeness tests;
- a claim that two components are **the same mechanism** needs an interaction test, not two
  separate effects of similar size.

A rank-one change that turns a behaviour on and off is a strong claim about direction; say what
else it leaves open.

## 11. Ablation types

State which ablation you used and why. Zero ablation can overstate importance because zero may be far
off the activation distribution. Mean ablation replaces with a dataset average and preserves scale.
Resample ablation replaces with activation from another input and is usually the most faithful to
the natural distribution. Noise ablation tests robustness. Different types can give different
answers; when the claim is important, report two types and note disagreement.

## 12. Lens and readout conventions

- Decode intermediate states through the final normalisation and unembedding in the same way the
  model does, and say if a learned lens was used instead of the raw one.
- Treat a lens readout as a projection of the state, not as the model's belief at that layer.
- Check the wiring with a known layer: the last layer's readout must reproduce the model's output.
- If a model applies logit scaling or softcapping, apply it or state that you did not.
- Report readouts for matched controls so a reader can see what a "no information" readout looks like.

## 13. Probing and steering controls

- Probes: report a shuffled-label baseline and a baseline on a randomly initialised or otherwise
  uninformative representation; choose probe capacity before seeing results; a probe that decodes a
  label shows the information exists, not that the model uses it. Use an intervention to test use.
- Steering: compare against a random vector of equal norm, report the coefficient sweep, and show
  fluency or off-target damage next to the effect size; an effect bought by breaking the output is
  not a steering result.

## 14. Claim language for interpretability results

Match the verb to the rung the experiment reached (invariant I4):

| Rung reached | Wording that fits |
|---|---|
| Correlational (feature co-varies with behaviour) | "is associated with", "co-varies with" |
| Decodable (a probe reads it) | "is linearly decodable", "is represented" (define represented) |
| Sufficient (patching in recovers behaviour) | "is sufficient to recover", "carries" |
| Necessary (ablating removes behaviour) | "is necessary for", "removing it abolishes" |
| Mechanism (necessary, sufficient, specific, replicated) | "implements", "computes" |

Avoid human mental-state words for model internals unless defined operationally (W22). Avoid
"circuit" for a ranked list of components that was not tested for faithfulness.

## 15. What the methods section must state

Model and checkpoint, precision, and the code path for interventions; the metric formula and the two
reference runs; the pair construction and gating, with counts; the splits; the ablation or patching
type and site (which activation, which position); the floors and controls and the number of random
draws; seeds; interval method and resampling unit; multiple-comparison handling; and what was fixed
before seeing data versus found afterwards (invariant I4). If any item is missing, `review` will
ask for it; supplying it up front costs a paragraph.

## 16. Ways to be confidently wrong

- A normalisation that mixes up the direction of the two reference runs, so effects flip sign.
- Position misalignment from unequal token counts, or from patching a padded position.
- A control drawn from a different distribution than the effect set.
- A peak from a large sweep presented as a finding.
- A circuit validated only on the data used to find it.
- Treating attribution scores as measured effects.
- Readouts through the wrong normalisation.
- Averaging over arms or directions that behave differently, so a one-sided effect looks general.
- Quoting "recovery" above 100 percent without saying that the scale was clipped or not.
- Generalising from a single model family.

## Reporting checklist

Tick each before a patching or ablation claim is marked supported in CLAIMS.md.

- [ ] Metric defined once, with both reference runs named
- [ ] No-op, extreme and baseline sanity checks recorded
- [ ] Control matches the claim type and inherits the confound
- [ ] Floor named and raw values reported
- [ ] Token-length equality asserted for patched positions
- [ ] Held-out evaluation set separate from selection set
- [ ] Seeds counted; distributions shown, not only peaks
- [ ] Multiple comparisons handled or analysis labelled exploratory
- [ ] Faithfulness, completeness and minimality claimed only if tested
- [ ] Attribution results verified by real patching
- [ ] Direction and component-set claims kept separate
- [ ] Ablation type named; second type run for key claims
- [ ] Lens wiring verified; readout described as projection
- [ ] Claim verb matches the rung reached
- [ ] Per-arm sample sizes and second-model limits stated in the paper
