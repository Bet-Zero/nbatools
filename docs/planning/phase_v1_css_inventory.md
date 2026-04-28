# Phase V1 CSS Inventory

> Reconnaissance artifact for
> [`phase_v1_work_queue.md`](./phase_v1_work_queue.md) item 1.

## Scan Scope

- Walked `frontend/src/` recursively.
- CSS files found: `frontend/src/App.css`, `frontend/src/index.css`,
  `frontend/src/styles/tokens.css`.
- SCSS/Sass/Less files found: none.
- JSX inline styles found in `QueryHistory.tsx`, `ResultEnvelope.tsx`, and
  `SavedQueries.tsx`.
- `frontend/src/index.css` is empty.
- `frontend/src/styles/tokens.css` and `frontend/src/styles/team-colors.json`
  contain canonical raw values. They are cataloged below as source files, not
  replacement targets.

## Replacement Priorities

1. Item 2 should replace all app colors in `frontend/src/App.css` with the
   locked design tokens from `frontend/src/styles/tokens.css`.
2. Item 3 should replace spacing and radii with `--space-*` and
   `--radius-*`, while documenting true layout exceptions.
3. Item 4 should replace typography with `--font-*`, `--weight-*`, and
   `--tracking-*`.
4. Inline styles should move to CSS classes during the relevant item or the
   CSS modules pass.

## Canonical Raw-Value Sources

These files intentionally contain raw values because they define tokens or
brand data:

| File | Lines | Current values | Treatment |
| --- | --- | --- | --- |
| `frontend/src/styles/tokens.css` | 3-33, 42-88 | Color, spacing, radius, shadow, font, weight, family, tracking, and transition token values | Keep as token source. Future CSS should consume these variables. |
| `frontend/src/styles/team-colors.json` | 2-31 | NBA team primary and secondary brand colors | Keep as team brand source. Future team theming should set `--team-primary` and `--team-secondary` from this file. |

## Item 2 Color Punchlist

### Legacy Variable Block

`frontend/src/App.css` currently imports `tokens.css` and then overrides core
token names with the old blue/navy palette. Remove this compatibility block or
map each alias to the locked token.

| File:line | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:4` | `--bg: #0f1117` | Replace uses with `--bg-page`; remove alias. |
| `frontend/src/App.css:5` | `--surface: #181b24` | Replace by context with `--bg-elevated`, `--bg-card`, or `--bg-input`; remove alias. |
| `frontend/src/App.css:6` | `--surface-hover: #1e2230` | Replace by context with `--bg-elevated` or `--bg-card`; no dedicated hover token exists. |
| `frontend/src/App.css:7` | `--border: #2a2d38` | Replace with `--border-default` or `--border-subtle` by context; remove alias. |
| `frontend/src/App.css:8` | `--text: #e0e0e6` | Replace with `--text-primary`; remove alias. |
| `frontend/src/App.css:9` | `--muted: #8b8fa3` | Replace with `--text-secondary` or `--text-tertiary` by hierarchy; remove alias. |
| `frontend/src/App.css:10` | `--accent: #4a90d9` | Use locked `--accent` from tokens. This intentionally changes the accent from blue to orange. |
| `frontend/src/App.css:11` | `--accent-hover: #5da1ea` | Use locked `--accent-hover` from tokens. |
| `frontend/src/App.css:12` | `--ok: #4caf50` | Replace with `--success` for UI status or `--win` for basketball outcome semantics. |
| `frontend/src/App.css:13` | `--warn: #f5a623` | Replace with `--warning`. |
| `frontend/src/App.css:14` | `--err: #e74c3c` | Replace with `--danger` for UI errors or `--loss` for outcome semantics. |

### Direct Hex and Fallback Hex Values

| File:line(s) | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:122`, `frontend/src/App.css:684`, `frontend/src/App.css:1127` | `color: #fff` | Use `--text-on-accent` for accent buttons. Verify contrast after orange accent lands. |
| `frontend/src/App.css:842` | `color: var(--text-secondary, #888)` | Use `--text-secondary`; remove fallback. |
| `frontend/src/App.css:846` | `background: var(--surface-alt, #2a2a3a)` | Use `--bg-card`; remove undefined `--surface-alt` fallback. |
| `frontend/src/App.css:847` | `border: 1px solid var(--accent, #4a9eff)` | Use `--accent`; remove fallback. Keep `1px` as a border-width exception. |
| `frontend/src/App.css:848` | `color: var(--accent, #4a9eff)` | Use `--accent`; remove fallback. |
| `frontend/src/App.css:859` | `background: var(--accent, #4a9eff)` | Use `--accent`; remove fallback. |
| `frontend/src/App.css:860` | `color: var(--bg, #1a1a2e)` | Use `--text-on-accent`. |

### RGBA Washes and Overlays

| File:line(s) | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:232` | `rgba(231, 76, 60, 0.1)` | Use a danger wash. Token gap: no `--danger-muted`; either use `color-mix()` with `--danger` or add a justified status-wash token. |
| `frontend/src/App.css:720`, `frontend/src/App.css:1441` | `rgba(231, 76, 60, 0.15)` | Same danger wash decision as above. |
| `frontend/src/App.css:452` | `rgba(231, 76, 60, 0.3)` | Use `--danger` directly if acceptable, or a documented danger-border wash. |
| `frontend/src/App.css:710`, `frontend/src/App.css:1429` | `rgba(76, 175, 80, 0.15)` | Use a success wash. Token gap: no `--success-muted`; either use `color-mix()` with `--success` or add a justified status-wash token. |
| `frontend/src/App.css:715`, `frontend/src/App.css:1433` | `rgba(245, 166, 35, 0.15)` | Use a warning wash. Token gap: no `--warning-muted`; either use `color-mix()` with `--warning` or add a justified status-wash token. |
| `frontend/src/App.css:788` | `rgba(245, 166, 35, 0.06)` | Same warning wash decision as above, lower emphasis. |
| `frontend/src/App.css:1437` | `rgba(139, 143, 163, 0.15)` | Use a neutral muted wash. Token gap: no neutral wash token; consider `color-mix()` with `--text-secondary` or `--bg-card`. |
| `frontend/src/App.css:339`, `frontend/src/App.css:1220` | `rgba(74, 144, 217, 0.15)` | Use `--accent-muted` after accent becomes orange. |
| `frontend/src/App.css:610`, `frontend/src/App.css:1338` | `rgba(74, 144, 217, 0.1)` | Use `--accent-muted` or define a lower-emphasis accent wash if the stronger token is visually too loud. |
| `frontend/src/App.css:401`, `frontend/src/App.css:764` | `rgba(74, 144, 217, 0.08)` | Use `--accent-muted` or a lower-emphasis accent wash decision. |
| `frontend/src/App.css:432`, `frontend/src/App.css:783` | `rgba(74, 144, 217, 0.06)` | Use `--accent-muted` or a lower-emphasis accent wash decision. |
| `frontend/src/App.css:428`, `frontend/src/App.css:1273` | `rgba(74, 144, 217, 0.03)` | Use a very subtle accent wash. Token gap if exact subtlety matters. |
| `frontend/src/App.css:421` | `rgba(255, 255, 255, 0.02)` | Replace with a background-depth token if possible (`--bg-elevated`/`--bg-card`). Token gap if a generic hover overlay is needed. |
| `frontend/src/App.css:960`, `frontend/src/App.css:1329` | `rgba(255, 255, 255, 0.05)` | Replace with `--bg-card`/`--border-subtle` treatment where possible. Token gap if a neutral chip wash is needed. |
| `frontend/src/App.css:1026` | `rgba(0, 0, 0, 0.6)` | Modal scrim. Token gap: no overlay/scrim token currently exists. |

## Item 3 Spacing, Radius, and Layout Punchlist

### Legacy Radius Alias

| File:line | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:15` | `--radius: 6px` | Remove alias. Replace uses with `--radius-sm` for compact controls or `--radius-md` for standard cards/inputs. |

### Border Radius Values

| File:line(s) | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:103`, `123`, `234`, `265`, `294`, `394`, `446`, `481`, `496`, `539`, `561`, `654`, `676`, `777`, `946`, `1036`, `1072`, `1109`, `1126`, `1181`, `1263`, `1372` | `border-radius: var(--radius)` | Replace by context with `--radius-sm` or `--radius-md`; cards/panels should usually use `--radius-md`. |
| `frontend/src/App.css:151`, `199` | `12px` | `--radius-lg`. |
| `frontend/src/App.css:336`, `702`, `762`, `1207` | `10px` | Round to `--radius-lg` unless compact-chip density argues for `--radius-md`. |
| `frontend/src/App.css:849` | `1rem` | `--radius-xl`. |
| `frontend/src/App.css:612` | `8px` | `--radius-md`. |
| `frontend/src/App.css:962`, `1331`, `1340` | `6px` | Round to `--radius-sm` for compact badges. |
| `frontend/src/App.css:1421` | `3px` | Round to `--radius-sm`. |
| `frontend/src/App.css:75`, `218`, `579` | `50%` | Keep as a documented circular-shape exception. |

### Spacing Values

| File:line(s) | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:24`, `25`, `143`, `307`, `383`, `810`, `811`, `1063` | `0` | Keep as reset/zero exception. |
| `frontend/src/App.css:56`, `95`, `173`, `258`, `296`, `472`, `497`, `639`, `659`, `776`, `994`, `1077` | `12px` or equivalent single-axis value | `--space-3`. |
| `frontend/src/App.css:41`, `49`, `119`, `167`, `184`, `235`, `236`, `248`, `360`, `443`, `448`, `470`, `511`, `513`, `624`, `626`, `672`, `1037`, `1047`, `1091`, `1147`, `1149`, `1229`, `1370` | `16px`, `20px`, `24px`, `32px`, `48px` combinations | Map directly to `--space-4`, `--space-5`, `--space-6`, `--space-8`, and `--space-12` by side. |
| `frontend/src/App.css:66`, `142`, `257`, `753`, `974`, `1088`, `1106`, `1123`, `1169`, `1235`, `1284`, `1451`, `1460`, `1472`, `1473` | `6px` or `6px` in compound values | Round to `--space-2` for gaps and action padding, or `--space-1` for very dense labels if visual density requires it. |
| `frontend/src/App.css:94`, `179`, `191`, `220`, `302`, `366`, `372`, `400`, `412`, `456`, `520`, `538`, `550`, `556`, `558`, `602`, `651`, `693`, `700`, `744`, `746`, `760`, `761`, `778`, `816`, `834`, `836`, `850`, `886`, `929`, `945`, `988`, `1055`, `1069`, `1102`, `1180`, `1198`, `1199`, `1203`, `1254`, `1260`, `1261`, `1321`, `1352`, `1380`, `1382`, `1459` | `2px`, `4px`, `8px`, and `0.5rem` family values | Use `--space-1` for 2-4px micro spacing and `--space-2` for 8px spacing. `0.5rem` should become `--space-2`. |
| `frontend/src/App.css:89`, `100`, `147`, `196`, `262`, `295`, `335`, `373`, `461`, `479`, `493`, `609`, `645`, `701`, `754`, `797`, `959`, `980`, `1003`, `1106`, `1123`, `1180`, `1203`, `1328`, `1337`, `1420` | Off-grid `1px`, `3px`, `5px`, `10px`, `14px` in compact padding/margins | Round to nearest 4px-grid token. For `10px 14px`, use `--space-3 --space-4`; for `5px 12px`, use `--space-1 --space-3`; for 1px badge padding, use `--space-1` if the resulting badge still looks compact. |
| `frontend/src/App.css:873` | `padding-right: 34px` | Round to `--space-8` (32px) for the clear-button affordance. |
| `frontend/src/components/QueryHistory.tsx:40`, `frontend/src/components/SavedQueries.tsx:100` | `style={{ marginLeft: 6 }}` | Move to a CSS class and use `margin-left: var(--space-2)`. |

### Sizing, Borders, and Other Layout Constants

These are not all spacing-token violations, but they are the hardcoded layout
values that item 3 should consciously keep, round, or document.

| File:line(s) | Current | Proposed mapping or decision |
| --- | --- | --- |
| `frontend/src/App.css:50`, `102`, `150`, `198`, `233`, `264`, `293`, `374`, `404`, `413`, `447`, `471`, `477`, `495`, `512`, `560`, `625`, `653`, `673`, `837`, `847`, `941`, `1035`, `1071`, `1108`, `1148`, `1206`, `1262`, `1371`, `1452`, `1474` | `1px` borders | Keep as documented border-width exception; replace color variables only. |
| `frontend/src/App.css:216`, `784`, `789` | `3px` borders | Keep if spinner/left accent stripe requires visual weight; otherwise round to a documented border-width convention. |
| `frontend/src/App.css:33`, `1039`, `1040` | `100vh`, `90vw`, `90vh` | Keep as viewport sizing exceptions. |
| `frontend/src/App.css:39`, `183`, `311`, `501`, `663`, `1038`, `1464` | `960px`, `480px`, `110px`, `400px`, `80px`, `440px`, `180px` | Layout constraints. Keep or convert to named component-level custom properties during CSS architecture work; not spacing-token replacements. |
| `frontend/src/App.css:73`, `74`, `214`, `215`, `577`, `578`, `725`, `726`, `878` | `1px`, `6px`, `8px`, `16px`, `24px` component dimensions/positioning | Use spacing tokens where they represent physical component size (`--space-2`, `--space-4`, `--space-6`); keep `1px` separator width as an exception. |

## Item 3 Completion Notes

Item 3 replaced app spacing and radii with the existing 4px-grid tokens:

- `padding`, `margin`, and `gap` declarations in `frontend/src/App.css` now
  use `--space-*` tokens or zero/reset values.
- Component dimensions that are visual spacing objects, such as status dots,
  spinners, separator height, and clear-button offset, now use `--space-*`
  tokens.
- Border radii now use `--radius-sm`, `--radius-md`, `--radius-lg`, or
  `--radius-xl`; circular dots and spinners keep `border-radius: 50%`.
- The inline `marginLeft: 6` styles in `QueryHistory.tsx` and
  `SavedQueries.tsx` moved to `.section-count-inline` with
  `margin-left: var(--space-2)`.

Documented hardcoded exceptions that remain after item 3:

- CSS reset and intentional zero values: `margin: 0`, `padding: 0`, `inset: 0`,
  `min-width: 0`, and `letter-spacing: 0`.
- Border widths and accent stripes: `1px` standard borders, `3px` spinner and
  left accent borders, and the `1px` envelope separator width.
- Viewport and layout constraints: app `max-width: 960px`, empty-copy
  `max-width: 480px`, raw JSON `max-height: 400px`, dev textarea
  `height: 80px`, save dialog `width: 440px`, dialog `max-width: 90vw`,
  dialog `max-height: 90vh`, and freshness label `min-width: 180px`.
- Fluid dimensions: `width: 100%` and `min-height: 100vh`.
- Typography and motion constants are intentionally left for item 4 and the
  later CSS architecture pass.

## Item 4 Typography Punchlist

### Legacy Font Aliases

| File:line(s) | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:16` | `--font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` | Remove alias and use `--font-sans`. |
| `frontend/src/App.css:17` | `--mono: "SF Mono", "Fira Code", "Consolas", monospace` | Remove alias and use `--font-mono`. |
| `frontend/src/App.css:29`, `106`, `154`, `269`, `483`, `537`, `564`, `910`, `948`, `1075`, `1113`, `1131`, `1179`, `1210` | `font-family: var(--font)` | `font-family: var(--font-sans)`. |
| `frontend/src/App.css:201`, `392`, `498`, `656`, `1316` | `font-family: var(--mono)` | `font-family: var(--font-mono)`. Ensure stat/table numerals also get tabular numeral settings. |

### Font Sizes

| File:line(s) | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:172` | `2.5rem` | No exact text token. If this remains emoji/icon sizing, document as icon sizing or map to `--font-display` if acceptable. |
| `frontend/src/App.css:455`, `1234` | `1.5rem` | `--font-h2` or `--font-stat-md` by context. |
| `frontend/src/App.css:59` | `1.4rem` | `--font-h2`. |
| `frontend/src/App.css:176` | `1.2rem` | `--font-h3`. |
| `frontend/src/App.css:1045` | `1rem` | `--font-body`. |
| `frontend/src/App.css:105`, `124`, `182` | `0.95rem`, `0.9rem` | `--font-body`. |
| `frontend/src/App.css:297`, `464`, `631`, `677`, `742`, `885`, `1074`, `1239`, `1296`, `1387` | `0.85rem` | `--font-small` unless the component is body copy, then `--font-body`. |
| `frontend/src/App.css:391`, `563`, `657`, `779`, `817`, `841`, `981`, `1089`, `1111`, `1128` | `0.82rem` | `--font-small`. |
| `frontend/src/App.css:67`, `367`, `524`, `644`, `851`, `995`, `1160`, `1453` | `0.8rem` | `--font-small`. |
| `frontend/src/App.css:148`, `200`, `480`, `732`, `763`, `1053`, `1246`; `frontend/src/components/ResultEnvelope.tsx:86` | `0.78rem` | `--font-small`; move inline style to CSS class. |
| `frontend/src/App.css:267`, `337`, `406`, `499`, `535`, `703`, `1004`, `1177`, `1277` | `0.75rem` | `--font-small` for labels/buttons; `--font-micro` only if the component must stay very compact. |
| `frontend/src/App.css:378`, `608`, `616`, `1204`, `1311` | `0.72rem` | `--font-micro`. |
| `frontend/src/App.css:793`, `944`, `970`, `1061`, `1397`, `1422`, `1446` | `0.7rem` | `--font-micro`. |
| `frontend/src/App.css:770`, `1344` | `0.68rem` | `--font-micro`. |
| `frontend/src/App.css:958`, `1327`, `1336` | `0.65rem` | `--font-micro`; verify legibility on mobile. |

### Font Weights

| File:line(s) | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:379` | `400` | `--weight-regular`. |
| `frontend/src/App.css:126`, `338`, `632`, `738`, `1129`, `1240`, `1297` | `500` | `--weight-medium`. |
| `frontend/src/App.css:60`, `177`, `241`, `319`, `323`, `327`, `368`, `403`, `459`, `525`, `704`, `794`, `908`, `1046`, `1161`, `1423` | `600` | `--weight-semibold`. |
| `frontend/src/App.css:902` | `700` | `--weight-bold`. |

### Letter Spacing

| File:line(s) | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:383`, `1063` | `letter-spacing: 0` | Keep as normal-text reset. |
| `frontend/src/App.css:706`, `772`, `964` | `0.03em` | Use `--tracking-uppercase` if the text remains uppercase label/chip text. |
| `frontend/src/App.css:408`, `796`, `1006`, `1057`, `1425` | `0.04em` | Use `--tracking-uppercase`. |
| `frontend/src/App.css:370`, `527`, `973`, `1163` | `0.05em` | Use `--tracking-uppercase`. |

### Line Height

| File:line(s) | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/App.css:32` | `line-height: 1.5` | Keep as base reading rhythm or promote to a typography token if line-height tokens are added. |
| `frontend/src/App.css:185` | `line-height: 1.6` | Keep as readable empty-state copy rhythm or promote to a typography token if line-height tokens are added. |
| `frontend/src/App.css:887`, `1398` | `line-height: 1` | Keep as compact icon/dot alignment exception. |

## Inline Style Punchlist

| File:line | Current | Proposed mapping |
| --- | --- | --- |
| `frontend/src/components/QueryHistory.tsx:40` | `style={{ marginLeft: 6 }}` | Move to a shared count-spacing class; `margin-left: var(--space-2)`. |
| `frontend/src/components/SavedQueries.tsx:100` | `style={{ marginLeft: 6 }}` | Same shared count-spacing class. |
| `frontend/src/components/ResultEnvelope.tsx:86` | `style={{ fontSize: "0.78rem" }}` | Move to an envelope reason class; `font-size: var(--font-small)`. |
| `frontend/src/components/SavedQueries.tsx:117` | `style={{ display: "none" }}` | Move to a file-input utility/class, e.g. `.saved-import-input { display: none; }`. No token mapping needed. |

## Additional Style Constants

These are outside the explicit item 2-4 color/spacing/type scope, but they
were found during the frontend scan and should be treated deliberately when
the CSS architecture is cleaned up.

| File:line(s) | Current | Proposed mapping or decision |
| --- | --- | --- |
| `frontend/src/App.css:108`, `127`, `155`, `270`, `484`, `540`, `567`, `679`, `853-855`, `889-891`, `932`, `947`, `1078`, `1114`, `1132`, `1182`, `1211`, `1264`, `1303`, `1355` | `0.15s` transitions | Replace with `--transition-fast` or `--transition-default`; choose one interaction-speed convention. |
| `frontend/src/App.css:219` | `animation: spin 0.8s linear infinite` | No direct token. Keep as loading-animation exception or add a motion-duration token if broader motion work appears. |
| `frontend/src/App.css:135`, `381`, `618`, `888`, `895`, `931`, `936`, `1064`, `1140`, `1346`, `1354`, `1359` | Opacity constants | Keep as component-state values or introduce opacity tokens only if repetition becomes a maintenance problem. |
| `frontend/src/App.css:1025`, `1030` | `inset: 0`, `z-index: 100` | Keep as modal overlay layout constants unless a z-index scale is introduced. |
| `frontend/src/components/CopyButton.tsx:25`, `26` | Programmatic `textarea.style.position = "fixed"` and `textarea.style.opacity = "0"` | Not a JSX `style={...}` attribute. Keep as clipboard fallback implementation detail or replace with a reusable visually-hidden class if this pattern repeats. |

## Open Design Decisions

- Status wash tokens: current UI uses success/warning/danger translucent
  backgrounds, but the token file only defines solid status colors. Decide
  whether item 2 should use `color-mix()` with existing tokens or add
  explicit status wash tokens.
- Overlay scrim: the save-query dialog uses `rgba(0, 0, 0, 0.6)`. Decide
  whether to add an overlay token or document it as an overlay-only exception.
- Accent wash scale: several blue washes have different alpha values. Existing
  tokens provide only `--accent-muted` and `--accent-glow`; item 2 should
  collapse them to `--accent-muted` unless visual density needs a second
  muted accent token.
- Icon/emoji sizing: large icon font sizes do not map exactly to the text
  scale. Item 4 should either treat these as typography tokens or document
  them as icon-size exceptions.
- Layout widths/heights: max widths, dialog dimensions, and textarea heights
  are structural layout constants. Item 3 should keep them documented or move
  them to named component-level custom properties during the CSS architecture
  pass.
