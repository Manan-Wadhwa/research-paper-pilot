# Figure plan

Project: <identity sentence from PROJECT_CONTEXT.md>
Venue and page budget: <venue, page limit, appendix policy, date checked>
Last updated: <date>

## The pitch (Figure 1 in one sentence)

<One sentence that a reader who skips the text should take away. Figure 1 renders this.>

## Story check

The three-bullet story from the outline, and which figure or table carries each bullet.

| Bullet | Carried by | Gap? |
|---|---|---|
| 1. <claim in plain words> | Fig <n> | <none / needs a figure / prose is enough> |
| 2. | | |
| 3. | | |

## Figures

One row per figure. A figure that needs "and" in its claim is split before it is built.

| Id | One-sentence claim | CLAIMS.md ids | Main or appendix | Anchor panel | Status |
|---|---|---|---|---|---|
| F1 | | | main | | planned |
| F2 | | | main | | planned |
| F3 | | | appendix | | planned |

## Panels

One row per panel. Each panel has exactly one role: evidence, definition, validation in a second
regime, comparison against baselines, practical consequence, illustration, or null result.

| Figure | Panel | Role | Data source (result file + fields) | Plot type | Notes |
|---|---|---|---|---|---|
| F1 | a | | results/<file>.json: <fields> | | |
| F1 | b | | | | |

## Build record

| Figure | Generator script | Output | Provenance file | Last run | Headline numbers printed |
|---|---|---|---|---|---|
| F1 | paper/figures/fig_<name>.py | paper/figures/fig_<name>.pdf | fig_<name>.provenance.json | <date> | <values> |

## Captions

For each figure: the bold takeaway sentence, then what is plotted (unit, n, interval method).

- F1: **<takeaway sentence>** <what is plotted; n = ...; error bars show ...>
- F2:

## Tables

| Id | One message | Source file or generated fragment | Direction arrows | Decimals | Status |
|---|---|---|---|---|---|
| T1 | | | | | planned |

## Caption-versus-data check

Run per figure after every re-run of its generator. Record failures and fixes.

| Figure | Numbers match | Directions match | Scope words match | n, interval, units match | Result |
|---|---|---|---|---|---|
| F1 | | | | | |

## Style decisions

- Palette: <name and values, or "Okabe-Ito">
- Column width and font size: <values>
- Shared style module: <path or "none yet">
- Palette check run with `dataviz`: <yes / no / not installed>

## Deferred to the appendix

<Panels and variants moved out of the main text, with the reason.>

## Open items

<Figures waiting on results, claims without a figure, decisions for the user.>
