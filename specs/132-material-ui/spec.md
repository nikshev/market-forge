---
traces: [REQ-WP-083]
status: draft
---

# Feature Specification: The overview and the chart are a Material UI interface that follows the theme

**Feature Branch**: `132-material-ui`

**Created**: 2026-10-04

**Status**: Draft

**Input**: [[REQ-WP-083]] — PRD §27, §27.1, §27.3; the owner's direction of 2026-10-04.

## Context

The overview was shown to the owner as five bare lines on white with default buttons, and the chart page is
the same: unstyled markup that works. The product is about to be shown in a browser and in Telegram, where the
page inherits the user's theme or fails to.

Nothing here changes what a page shows or asks for. It changes how the same facts are presented, and it keeps
the **accessible contract** the existing 297 web tests assert: headings, roles, accessible names, the pressed
state of a toggle, the roles of statuses and alerts. A restyle that quietly renamed a button would pass for a
redesign and fail for a reader using a screen reader, and the tests are the only place that contract is written.

### What there is to preserve

Read from the existing components and tests: the `h1` brand and the `h2` "Markets" / chart title; a
`section` "Timeframe" holding one `aria-pressed` button per token; a `section` "Channel mode" with the mode in
bold, its explanation and a "Show …" button; a `group` "Pane" of `aria-pressed` buttons; `status` and `alert`
paragraphs from `LoadState`; a list named "Markets" whose items are links named by their symbol.

### The theme

One theme, a pure function. Its inputs are the scheme (`light` or `dark`) and, inside Telegram, Telegram's
`themeParams` (`bg_color`, `text_color`, `secondary_bg_color`, `button_color`, `button_text_color`). Where
Telegram supplies a colour the theme uses it; where it does not the theme's own palette applies. Outside
Telegram the scheme is the browser's `prefers-color-scheme`. The chart canvas, which is not Material, takes
its colours from the same theme so the page does not become a light chart on a dark card.

### Why spot and perp get colours

The market type was the thing this deployment first got wrong (Binance is `spot`, not `perp`,
[[REQ-WP-081]]). A chip whose colour differs makes the difference visible at a glance on the first screen.

### What this is not

Not a design system, not new pages or data, not an animation layer, not the chart library's rendering, not the
lower panes' content (only their selector).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One theme, light and dark (Priority: P1)

**Independent Test**: build the theme for each input and read its palette.

**Acceptance Scenarios**:

1. **Given** the scheme `light` or `dark`, **Then** the theme's palette mode is that scheme.
2. **Given** Telegram's theme parameters, **Then** background, text, paper and primary come from them.
3. **Given** a parameter Telegram does not supply, **Then** the theme's own colour is used for it.
4. **Given** no Telegram, **Then** the scheme follows the browser's `prefers-color-scheme`; inside Telegram,
   Telegram's.
5. **Then** the text colour has enough contrast on the background in both schemes (a computed ratio of at least 4.5).

---

### User Story 2 - The overview is cards (Priority: P1)

**Acceptance Scenarios**:

1. **Given** five markets, **Then** five cards in a list named "Markets", each a link named by its symbol.
2. **Then** each card shows its venue and a market-type chip; `spot` and `perp` differ in text **and** colour.
3. **Then** absent scores read "unscored" and are visibly de-emphasised, not zero.
4. **Given** no markets, **Then** an alert with role `status` says so.
5. **Given** the timeframe group, **Then** one pressed button per token, the chosen one pressed.

---

### User Story 3 - The chart page's controls (Priority: P1)

**Acceptance Scenarios**:

1. **Then** the page keeps the heading, the timeframe group, the channel-mode control and the lower-pane group
   with the roles and names the existing tests find.
2. **Then** the channel-mode control names the mode in a chip whose colour differs between AS-SEEN-THEN and
   CURRENT REFIT, and still carries the explanation and the switch button.
3. **Then** load states are alerts that keep the roles `status` and `alert`.
4. **Then** the chart sits in a surface that takes the theme's background, and the canvas follows the scheme.

---

### User Story 4 - The shell (Priority: P2)

**Acceptance Scenarios**:

1. **Then** an app bar shows the logo and the product's name once, as the page's single `h1`.
2. **Given** a chart page in a browser, **Then** a back control returns to the overview; **given** Telegram,
   **Then** none is shown (Telegram's own back button does that).

---

### User Story 5 - Phone width (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a 390 px viewport, **Then** neither page has a horizontal page scroll; a wide control row scrolls
   within itself.
2. **Then** the screenshots of both pages, light and dark, at desktop and 390 px, are taken from the running
   build and committed under `docs/ui/`.

### Edge Cases

- Telegram supplies only some theme parameters: the rest come from the theme.
- A very long symbol (`1000PEPEUSDT`, `BTC-USDT-SWAP`) on a narrow card: wraps, does not overflow.
- A timeframe list of eight tokens at 390 px: scrolls inside the group.
- `prefers-color-scheme` changes while the page is open: the theme follows.
- Reduced motion: no animation is added.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pages MUST render under one `ThemeProvider` with `CssBaseline`.
- **FR-002**: The theme MUST be a pure function of the scheme and of Telegram's theme parameters.
- **FR-003**: Outside Telegram the scheme MUST follow `prefers-color-scheme`; inside it, Telegram's.
- **FR-004**: The overview MUST list one card per market in a list named "Markets", each a link named by its symbol, with venue and a market-type chip that differs for `spot` and `perp`.
- **FR-005**: Every role and accessible name the existing web tests use MUST be unchanged.
- **FR-006**: The channel-mode control MUST show the mode in a chip that differs between the two modes.
- **FR-007**: The chart canvas MUST follow the theme.
- **FR-008**: Neither page MUST have a horizontal page scroll at 390 px.
- **FR-009**: Screenshots, light and dark, desktop and 390 px, of both pages MUST be committed under `docs/ui/`.
- **FR-010**: The production bundle MUST still contain no signed launch string.

### Key Entities

- **Theme**: palette, shape and typography derived from the scheme and Telegram's parameters.
- **Scheme**: `light` or `dark`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing web tests pass; any edit to an existing test is listed with its reason.
- **SC-002**: Text contrast of at least 4.5 on the theme background in light and dark, computed.
- **SC-003**: At 390 px, `document.documentElement.scrollWidth <= innerWidth` on both pages, measured in a browser.
- **SC-004**: Eight screenshots (two pages, two schemes, two widths) exist and were looked at.
- **SC-005**: The gzip size of the bundle before and after is recorded.

## Assumptions

- Material UI 9 with Emotion works with the React 18 the app uses.
- The logos in `assets/` are the product's and suit an app bar at about 28 px.
- Telegram's `themeParams` keys are those the SDK documents and the page already reads.
