// @trace: REQ-WP-074
//
// The row of timeframe buttons. PRD section 27 does not name one; the sections
// that imply it are §5.1's set, §28.2's parameter, §27.1's link and §27.2/§27.3's
// controls -- see the requirement note.
//
// No state and no address here: the page owns the in-force token, so what is
// displayed and what is requested are one value (FR-013), and a component that
// remembered its own selection could disagree with the chart.

import type { TimeframeOption } from "./timeframes";

export function TimeframeControl({
  offered,
  selected,
  onSelect,
}: {
  offered: readonly TimeframeOption[];
  selected: string;
  onSelect: (token: string) => void;
}): JSX.Element {
  return (
    <section aria-label="Timeframe">
      {offered.map((option) => (
        <button
          key={option.token}
          type="button"
          aria-pressed={option.token === selected}
          onClick={() => onSelect(option.token)}
        >
          {option.token}
        </button>
      ))}
    </section>
  );
}
