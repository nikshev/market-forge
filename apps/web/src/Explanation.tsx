// @trace: REQ-US-004
//
// PRD section 27.4's explanation panel, over section 22.4's stored items.
//
// Every one of section 22.1's six groups appears, always. A group left off the
// panel because it had no data reads as "not relevant here", when what happened
// was "we could not see it" — and those two produce the same silence on screen
// while meaning opposite things about the setup.

import { GROUPS } from "./types";
import type { ExplanationOut, FactorOut, Group } from "./types";

const LABELS: Record<Group, string> = {
  channel_structure: "Channel",
  rejection_quality: "Rejection",
  order_flow_confirmation: "Order flow",
  volume_confirmation: "Volume profile",
  derivatives_context: "Derivatives",
  defi_crossvenue_context: "DeFi / cross-venue",
};

function Row({ factor }: { factor: FactorOut }): JSX.Element {
  return (
    <li>
      <span>{LABELS[factor.group]}</span>
      <span>
        {factor.value} / {factor.cap}
      </span>
      {factor.names.length > 0 ? <span>{factor.names.join(", ")}</span> : null}
    </li>
  );
}

export function ExplanationPanel({
  explanation,
}: {
  explanation: ExplanationOut | null;
}): JSX.Element {
  if (explanation === null) {
    // Not an empty panel. A signal from before scoring existed has no
    // explanation, and an empty list of factors would say it scored on nothing.
    return (
      <section aria-label="Why this score">
        <p>This signal was not scored, so there is nothing to explain.</p>
      </section>
    );
  }

  const present = new Map(explanation.factors.map((f) => [f.group, f]));
  return (
    <section aria-label="Why this score">
      <p>Model {explanation.model_version}</p>
      <ul aria-label="Contribution factors">
        {GROUPS.map((group) => {
          const factor = present.get(group);
          return factor === undefined ? (
            <li key={group} data-missing="true">
              <span>{LABELS[group]}</span>
              <span>no data — not scored, not zero</span>
            </li>
          ) : (
            <Row key={group} factor={factor} />
          );
        })}
      </ul>
    </section>
  );
}
