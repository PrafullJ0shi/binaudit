# Design

binaudit is a measurement tool. Its screens and documents should read like the results
section of a short field report: plain, exact and calm. The one thing a reader must see
first is where waste went into the wrong bin, so that is the only thing that gets colour.

## The problem it answers

A hostel floor or a ward puts up three bins and a poster. A month later nobody knows if
the poster changed anything. binaudit turns a ten-minute bin check into numbers that can
answer that question:

1. **Audit.** Open a bin, note each item and where it should have gone.
2. **Measure.** Contamination rate per bin, with an honest 95% interval.
3. **Act.** Print a sign for that bin that names its own most common wrong items.
4. **Re-audit.** Compare before and after, and say "no clear change" when the data cannot
   tell.

## Principles

1. Evidence before decoration. Every number on screen comes from the user's own audit
   rows. Sample data is labelled as synthetic everywhere it appears.
2. Show uncertainty. A rate is never shown without its interval and its sample size.
   Small samples are flagged, not hidden.
3. One accent colour, used for one meaning: misplaced waste. Correctly sorted waste,
   axes, rules and text are graphite.
4. Same arithmetic everywhere. The browser and the Python CLI compute identical numbers
   from the same CSV, and a test checks it.
5. Local first. No account, no server, no network call after the page loads. Data stays
   in the browser until the user exports it.

## Tokens

| Role | Light | Dark | Use |
|---|---|---|---|
| paper | `#F7F6F2` | `#141517` | page background |
| paper-2 | `#EDEBE5` | `#1D1F22` | table stripes, input wells |
| ink | `#1B1C1E` | `#E6E4DF` | body text |
| muted | `#5E6166` | `#9A9DA3` | secondary text, axes |
| rule | `#D6D3CB` | `#34373C` | hairlines, borders |
| accent | `#B3401E` | `#E8835F` | misplaced waste only: bars, counts, sign highlights |

Stream labels are words, not colours. Wet, dry and hazardous are never colour-coded,
because bin colours differ between cities and colour alone fails for colour-blind users.

## Type

Two families, both self-hosted under the SIL Open Font License.

- **Source Serif 4**: headings and body text.
- **JetBrains Mono**: numbers, table figures, CSV, commands. Tabular figures line up.

Not used: Inter, Roboto, Space Grotesk, any display or icon font.

Scale (px): 12 / 14 / 16 / 20 / 28 / 40. Body is 16. Line length at most 72 characters.

Spacing scale (px): 4 / 8 / 12 / 16 / 24 / 32 / 48. Every margin and padding is one of
these.

## Layout

- One column, max width 960 px. Sections are separated by a hairline and a 48 px gap,
  not by boxes.
- Tables, not card grids. Each result is a row: site, bin, audits, items, rate, interval,
  and an inline interval bar.
- Interval bar: a 160 px graphite axis from 0 to 100%, a 2 px accent tick at the rate and
  a 1 px accent line across the interval.
- Corners: 2 px radius on inputs and buttons. No shadows, no gradients, no glows, no
  emoji, no illustrations.

## Printed sign

A5 portrait, black on white, prints on any office printer. Bin name in 40 px serif at the
top, then "Most often put here by mistake" and up to three items, each with the bin it
belongs in. The accent is replaced by a heavy underline in print so the sign works in
black and white. The footer gives the audit dates and item counts the sign is based on.

## Writing

- Short sentences. No marketing adjectives. No emoji.
- Name the unit every time: "items", "audits", "g".
- Say what the data cannot show. "No clear change" is a valid result.

## Figures in the repository

- README banner in light and dark variants, served with `<picture>` and
  `prefers-color-scheme`.
- Screenshots are real captures of the app running on the labelled synthetic sample.
- Diagrams use orthogonal connectors, at most nine nodes, no shadows.
