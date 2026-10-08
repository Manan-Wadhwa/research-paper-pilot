# Criterion note: <name of the test>

<!-- Write this before any confirmatory run touches the evaluation data, then commit it, then fill in the hash below.
     A rule written after the result is not pre-registration. If this note is a lighter validity check rather than a falsification test, say so under "Weight" and why.
     If you decide the note should not exist, delete it before reading the results, never after. -->

- **Date written:** 
- **Commit hash (fill in after committing, before running):** 
- **Weight:** falsification test | validity check (lighter; no power analysis, no fallback procedure)
- **Lock strength this provides:** pre-registered (immutable record) | fixed in code beforehand | stated in prose beforehand

## What runs

<!-- Script, config, seeds, pool file, held-out split, generation settings. Name files. -->

## Classification thresholds

<!-- Values for any gate that sorts items into groups. Lock values already validated; do not fit new ones on the data the test will run on. -->

| Parameter | Value |
|---|---|
| | |

## Primary metric

<!-- Exact definition, including the denominator (for example, restricted to matched pairs whose two members differ on the baseline measure). -->

## Bar

<!-- A number, and the statistic it applies to: bare point estimate or an interval bound. Give the reason for the choice. Report the interval either way.
     If the claim runs in two directions, the bar must hold in both, each scored against its own expected sign, never pooled. -->

## What each outcome licenses

| Outcome | Headline framing it permits | Fallback triggered |
|---|---|---|
| Clears the bar in every required condition | | none |
| Clears some conditions only (equivocal) | does not license the headline | |
| Clears none | | <the fallback, named now> |

## What will not be changed after seeing results

<!-- Thresholds, pooling of directions, the denominator restriction, the primary metric, the data split, the measurement instrument and its settings, the sample or item pool. -->

- 

## Known limitation, stated in advance

<!-- What a null result will and will not mean. -->

## Power or sample note

<!-- Run after the criteria above are frozen. It is a go/no-go gate and cannot move the bar.
     Pre-written response if underpowered: widen the pool before running, or report the result as exploratory. Loosening the bar is not allowed.
     If inputs (standard deviation, correlation) are borrowed from another experiment, say so, and re-run with real values after the first evaluation. -->

- Items available: 
- Effect size assumed and where it comes from: 
- Minimum detectable effect at the target power: 

## Corrections

<!-- Dated, visible corrections only. State what was wrong and what changed. Never edit the criterion silently. -->
