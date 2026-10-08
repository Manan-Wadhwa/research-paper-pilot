# Mode 5: figures and tables

Plans the paper's figures around claims, builds each from a result file with a script, and checks
that every caption says what the data shows. Style rules W31 to W35 in `style-rules.md` are the
short form; this file is the procedure.

## Contents

- Inputs and outputs
- The figure plan
- One claim per figure; Figure 1 is the pitch
- Panel roles and the main-versus-appendix split
- Captions and legends
- Colour, type and format
- Plot types for common evidence
- One generator script per figure
- The caption-versus-data check
- Tables
- Delegating palette checks
- Common failure modes
- Done check, state updates, output

## Inputs and outputs

Read PROJECT_CONTEXT.md, CLAIMS.md and the result files each claim cites. Write
`paper/FIGURE_PLAN.md` from the template in `templates/FIGURE_PLAN.md`, one script per figure under
`paper/figures/`, and the rendered figures next to them. Figures are built after claims are
settled and before results prose is written (W6); a plan made after the prose just describes the
prose.

## The figure plan

Build the plan in this order for each candidate figure:

1. Write the figure's claim as one sentence. If it needs "and", split the figure.
2. List the fewest panels that establish the claim.
3. Give each panel one role (see below).
4. Pick the anchor panel: the one the results paragraph will revolve around.
5. Move everything else to another figure, the appendix, or the caption.
6. Record the data source for each panel as a result file plus field names, so the figure can be
   regenerated and audited.
7. Draft the caption's first sentence (the takeaway) now; it is the claim restated as a finding.

Then check the set as a whole: the figures together should tell the three-bullet story from
`write.md`, and no claim in CLAIMS.md marked "goes in the paper" may lack a figure or table unless a
sentence of prose suffices. A paper with more results subsections than ideas has figures driven by
plotting convenience; merge or cut.

## One claim per figure; Figure 1 is the pitch

Each main figure earns its place by carrying one dominant claim (W31). If a figure cannot be
summarised in one clean sentence, split it, demote part of it, or rewrite it around a clearer claim.

Figure 1 renders the paper's one-sentence pitch as data or as a clear schematic: what question is
asked and what the answer looks like. It should make sense to a reader who has not read a word of
the text. Place it near the top of the first page in a two-column layout, or the top of the second
page in one column. Later figures carry mechanism, evidence, robustness and application, in that
order. Judge each later panel against the pitch as well as its own claim.

## Panel roles and the main-versus-appendix split

Give each panel exactly one of these roles before writing its legend:

- evidence for the claim;
- a definition or bridge (shows what a new metric measures);
- validation under a second regime (another model, dataset or setting);
- a comparison against baselines;
- a practical consequence;
- an illustrative example;
- a null or negative result stated as a finding.

Keep in the main figure what is required to establish the claim, the key comparison the reader must
see at once, and any panel that defines a new metric the argument depends on. Move to the appendix
the robustness variants, dense method-by-method grids, extra examples, secondary ablations, and
compatibility matrices (which method accepts which input). A matrix of which checks passed explains
why a bar is missing; it does not answer a scientific question, so it is one appendix table or one
sentence in Methods.

A worked example earns a place in the main text when it lets a newcomer picture the data: show one
real item and one real output next to the aggregate plot.

## Captions and legends

Open every caption with a bold, one-sentence takeaway that states the finding ("Ablating the head
removes the effect in all three settings."). Then say what is plotted, with the unit, the number of
items or runs, and what the error bars mean. The caption should let a reader skip the text and still
get the point (W32).

Legends and captions:

- define the role of each panel and keep panel letters consistent with the text;
- keep the quantitative anchors that the shortened main text omits;
- never claim more than the plot shows;
- carry no defences against imagined objections ("listed for completeness", "should not be compared
  across panels"); instead state the fact that sets comparability, such as "panel B uses a smaller
  sample (n = 24)";
- explain a surprising value by saying what the quantity is, not by apologising for it (for example,
  an overlap statistic can be slightly negative when it is a corrected estimate);
- mention a supporting data file only if one is actually shipped.

Interpret the figure in the text as well, naming the pattern and what it supports (W35).

## Colour, type and format

- **Palette.** Use a colour-blind-safe palette. The Okabe-Ito set is a safe categorical default:
  black `#000000`, orange `#E69F00`, sky blue `#56B4E9`, bluish green `#009E73`, yellow `#F0E442`,
  blue `#0072B2`, vermillion `#D55E00`, reddish purple `#CC79A7`. For continuous data use viridis or
  cividis. Never rely on red against green. Use line style or marker shape as well as colour so
  greyscale prints remain readable (W32).
- **Colour maps for matrices.** White at zero for non-negative magnitudes; a diverging map centred
  on zero for signed values, with symmetric limits so that equal magnitudes look equal (W33).
- **Consistency.** The same category keeps the same colour in every figure. Accidental salience (one
  panel much darker than its neighbours) misleads; use it only when emphasis is deliberate.
- **Annotation.** Mark the window or region that matters (a shaded band, a labelled arrow) so the
  reader sees it without searching. Put labels on the lines instead of a distant legend when there
  are few series.
- **Type.** Axis labels and tick labels at least as large as the body text at final size; keep
  figure fonts consistent across figures. Do not put a title inside the figure; the caption is the
  title.
- **Format.** Save plots as vector PDF. Use raster only for photographic or very dense images, and
  then at 300 dpi or more. Size the figure to the column width it will occupy, so no rescaling
  changes the font sizes.
- **Axes.** Bar charts start at zero. Name the unit and the quantity on each axis, and say what the
  interval shows (standard deviation, bootstrap interval, range) in the caption.
- **Whitespace.** Trim dead margins around panels; let alignment and grouping carry structure, and
  reduce text inside the figure.

## Plot types for common evidence

| Evidence | Plot | Note |
|---|---|---|
| Effect across many conditions | Dot plot with interval, one row per condition | Easier to read than grouped bars; sort by effect size |
| Distribution of an effect | Violin, box or strip plot with points | Show the distribution, not only the peak or the mean |
| Effect against a null or control | Paired bars or points, control beside effect | The null must inherit the same confound; put them adjacent |
| Layer or position profile | Line plot with band | Annotate the window where the effect lives |
| Component-by-position grid | Heatmap, centred diverging map | Fixed colour limits across panels |
| Two methods agreeing | Scatter with identity line and rank correlation | Report n and the correlation method in the caption |
| Ranking or comparison table | Table, not a bar chart, when more than about eight rows | See tables below |
| Illustrative example | Annotated text or a small schematic | Real item, real output, no mock-up |

When a quantity is bounded (a fraction in 0 to 1), set the axis limits to the bounds so clipped
values are visible, and disclose clipping in the caption if any value was clipped for display.

## One generator script per figure

Name scripts `fig_<name>.py` and outputs `fig_<name>.pdf` in the same folder. Each script:

- reads from the result files named in the plan, never from numbers typed into the script;
- takes no arguments needed to reproduce the published figure (defaults are the published setting);
- fixes the random seed for any resampling it does;
- writes the PDF, and optionally a small `fig_<name>.provenance.json` listing the input files with
  modification times and the exact values plotted;
- prints the headline numbers it plotted, so the caption check below is a copy-and-compare.

A minimal skeleton, stdlib plus matplotlib:

```python
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00"]  # colour-blind safe
RESULTS = "results/exp3.json"                            # source of every number

def main():
    with open(RESULTS) as f:
        data = json.load(f)
    fig, ax = plt.subplots(figsize=(3.25, 2.4))          # one column
    for i, arm in enumerate(data["arms"]):
        ax.errorbar(i, arm["mean"], yerr=arm["ci"], fmt="o", color=PALETTE[i % 4])
        print(arm["name"], arm["mean"], arm["ci"])       # printed for the caption check
    ax.set_ylabel("Recovered fraction")
    fig.tight_layout()
    fig.savefig("paper/figures/fig_exp3.pdf")

if __name__ == "__main__":
    sys.exit(main())
```

Keep one shared style module (fonts, sizes, palette) so figures match. If the project already has
plotting helpers, use them. Re-run every generator after any result file changes, and let
`check_numbers.py` catch caption numbers that no longer match.

## The caption-versus-data check

Run this on every figure before the draft is reviewed:

1. For each number or ordering stated in the caption and in the paragraph that cites the figure,
   find the plotted value (from the script's printed output or the provenance file).
2. Check direction words ("higher", "removes", "increases") against the plotted direction.
3. Check scope words ("all", "consistently", "in every setting") against the number of settings
   actually plotted.
4. Check that the n, the interval method and the units in the caption match the script.
5. Check that the same quantity has the same value in text, table, abstract and figure; mismatches
   mean one source is stale.
6. Record failures as findings in the figure plan, with the fix.

A reviewer with no project context repeats this check in `review.md`; doing it first means that
pass finds little.

## Tables

Use a table when readers need exact values, when there are many conditions, or when the comparison
is across several metrics (W34). Rules:

- booktabs rules only (`\toprule`, `\midrule`, `\bottomrule`), no vertical lines, no double rules;
- caption above the table, and the caption states setting and protocol, not discussion;
- direction arrows in headers for metrics where higher or lower is better, and units where needed;
- the same number of decimals within each metric column; align numeric columns on the decimal point;
- bold the best entry and nothing else; avoid colouring many cells;
- group settings with `\multicolumn` and `\cmidrule`, not with vertical separators;
- one table, one message; split unrelated results;
- every cell comes from a result file, ideally through a generated `.tex` fragment, so the table
  cannot disagree with the data (invariant I1);
- if a table is a list of ablations, name the removed component in the row label.

Say in the text what the table shows; the reader should not have to scan for the point.

## Delegating palette checks

If the `dataviz` skill is installed, invoke it for palette validation and chart-form choices before
final export. If it is not installed, say so in one line and use the palette and map rules above.
Do not block on it.

## Common failure modes

- One figure carrying several unrelated claims, or one claim spread over six panels.
- Figures chosen because they were easy to plot, not because a claim needs them.
- A caption that describes the axes but not the finding.
- A caption stronger than the plot, or a legend that pre-empts critics.
- Fonts that are unreadable at column width; titles inside images.
- Colour used as the only channel; red against green.
- A mean shown without its distribution, or a peak shown without its sweep.
- A control omitted from the plot that the text relies on.
- Numbers in the caption typed by hand and stale after a re-run.
- Main-text space spent on a compatibility matrix.

## Done check, state updates, output

Done when every planned figure has a script and a rendered PDF, the caption check has no open
failures, every figure is referenced and interpreted in the text, and the plan lists each figure's
status. Append to LAB_LOG.md: "Mode figures ran on <date>; produced <files>; decisions: panel moves,
claims that lost a figure; open: figures awaiting results". Update the status line in
PROJECT_CONTEXT.md. End with the standard output contract (files, decisions, open items, next mode,
usually `write`).
