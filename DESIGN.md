# DESIGN.md · DejaViewed

> Drop this file at the root of the DejaViewed repo. Any AI coding agent — Claude Code, Cursor, Stitch — that reads it will generate UI that matches the rest of the product.

**Tagline:** "You've saved this before."
**Product:** An agent-friendly repo / brain that pulls every random save from Instagram, TikTok, Twitter/X, Reddit, YouTube, Pinterest, and browser bookmarks into one curated catalog, then turns the worth-it ones into actionable deep-dive guides. A skill that makes Claude your librarian.
**One-liner for agents:** Dark-mode terminal × glassmorphism × violet-pink dusk. Confident curator energy. Opinionated, dense, readable.

---

## 1 · Visual Theme & Atmosphere

**Mood.** Late-night dev console meets indie design portfolio. The user is awake at 1am rescuing their Saved tab from itself. The UI should feel like a trusted CLI that happens to be beautiful — not a SaaS app, not a social feed.

**Density.** Dense and information-rich. Prefer 3–4 column catalog grids, tight line-heights, and small type over sparse hero-only layouts. The product's value is the *pile* becoming legible; show the pile.

**Design philosophy.**
- **Weight over size.** Hierarchy comes from `font-weight` (800–900), not XL type. Display sizes stay moderate.
- **Color as semantic.** Every accent color *means* something (tier, category). No decorative color.
- **Glass on dark.** Every floating surface uses translucent rgba + `backdrop-filter: blur`. Body never blurs.
- **One atmosphere.** Every page shares the same `#0a0a0f` field with two radial violet+pink gradients. Never solid backgrounds.
- **Terminal fingerprints.** Monospace labels, `/dejaviewed` command chips, `$` prompts, Unicode glyphs (`◉ ◆ ▪ ⬡ ⬢`) as icons.
- **Voice is second-person, mildly conspiratorial.** "You scroll, you tap save, you swear you'll come back. You don't." The em-dash is a fingerprint — always with spaces.

**Anti-patterns.** Not neon-cyberpunk. Not minimalist startup white. Not rounded-bouncy-friendly. Not gradient-soup. Not emoji-decorated.

---

## 2 · Color Palette & Roles

All colors live as CSS custom properties. Never hardcode hex.

### Surface scale

| Token | Hex | Role |
|---|---|---|
| `--bg` | `#0a0a0f` | Page background. Near-black with violet tint. **Never pure black.** |
| `--bg-2` | `#0f0f1a` | Subtle elevation lift under hero sections |
| `--surface` | `#12121a` | Card surface base (before translucency applied) |
| `--panel` | `rgba(255,255,255,0.03)` | Translucent card/panel background — default resting state |
| `--panel-2` | `rgba(255,255,255,0.05)` | Translucent panel — hover state |

### Canonical brand atmosphere (mandatory on `<body>`)

```css
background: #0a0a0f;
background-image:
  radial-gradient(ellipse 80% 50% at 50% -20%, rgba(167,139,250,0.14), transparent),
  radial-gradient(ellipse 60% 40% at 80% 10%, rgba(244,114,182,0.08), transparent);
background-attachment: fixed;
```

### Text

| Token | Hex | Role |
|---|---|---|
| `--text` | `#e8e8f0` | Primary body text. **Never `#fff` for prose.** |
| `--text-dim` | `#a0a0b8` | Secondary, captions, card summaries |
| `--text-mute` | `#6a6a80` | Labels, timestamps, metadata, uppercase eyebrows |
| `#ffffff` | pure white | **Reserved:** card titles, `h1` gradient endpoint, active pill text |

### Brand accents (used as a 135° triad gradient)

| Token | Hex | Role |
|---|---|---|
| `--accent` | `#a78bfa` | Violet — primary accent, tier A, guide category |
| `--accent-2` | `#f472b6` | Pink — secondary accent, gradient midpoint |
| `--accent-3` | `#60a5fa` | Blue — tertiary, tier B, UI/UX category, links-into-graph |

**Brand gradient** (wordmark, hero `h1`, active pills):
```css
background: linear-gradient(135deg, #fff 0%, #a78bfa 50%, #f472b6 100%);
-webkit-background-clip: text;
background-clip: text;
color: transparent;
```

### Tier colors (semantic — used everywhere tier is shown)

| Tier | Token | Hex | Usage |
|---|---|---|---|
| S | `--c-entry-s` | `#fbbf24` | Gold — top tier. Rare. |
| A | `--c-entry-a` | `#a78bfa` | Violet — high value (matches `--accent`) |
| B | `--c-entry-b` | `#60a5fa` | Blue — solid |
| C | `--c-entry-c` | `#6a6a80` | Gray — reference only |

### Category colors (left-border on cards, dot in legend, graph nodes)

| Category | Hex | | Category | Hex |
|---|---|---|---|---|
| repo     | `#4cda8c` | | platform  | `#e0d040` |
| tool     | `#f0a050` | | resource  | `#40d0e0` |
| skill    | `#e060a0` | | art       | `#f05060` |
| guide    | `#a78bfa` | | design    | `#fb7185` |
| uiux     | `#60a5fa` | | technique | `#60a5fa` |

### Borders & state

| Token | Value | Role |
|---|---|---|
| `--border` | `rgba(255,255,255,0.08)` | Default border on every panel/card |
| `--border-hi` | `rgba(255,255,255,0.15)` | Hover border |
| `--ok` | `#4cda8c` | Success, "dive loaded", hint strip glyph |
| `--warn` | `#fbbf24` | Warning, tier-S indicator |
| *(no `--error`)* | — | Use `--warn` or `--c-art` `#f05060` if needed |

### Active-state tint (pills, filter chips)

```css
background: linear-gradient(135deg, rgba(167,139,250,.25), rgba(244,114,182,.25));
border: 1px solid rgba(167,139,250,.5);
color: #fff;
```

---

## 3 · Typography Rules

**Primary font:** **Inter** (400, 500, 600, 700, 800, 900) — Google Fonts.
**Mono font:** **JetBrains Mono** (400, 500, 700) — Google Fonts.
**Never use font-weight < 400.** DejaViewed has no light weights. Period.

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap">
```

### Hierarchy

| Level | Family | Size | Weight | Tracking | Line-height | Notes |
|---|---|---|---|---|---|---|
| **h1 / hero** | Inter | `clamp(32px, 5vw, 56px)` | 900 | `-0.02em` | 1.05 | Gradient-clipped through `#fff → --accent → --accent-2` |
| **h2 / section head** | Inter | 22–24px | 800–900 | `-0.015em` | 1.2 | Sometimes uppercase with `0.1em` tracking |
| **h3 / card title** | Inter | 13–14px | 800 | `-0.005em` | 1.35 | Color: `#fff` (not `--text`) |
| **eyebrow / kicker** | JetBrains Mono | 11px | 700 | `0.14em` | 1 | ALL CAPS, `--accent` color |
| **section label** | Inter | 10–11px | 700–800 | `0.08–0.10em` | 1 | ALL CAPS, `--text-mute` |
| **body** | Inter | 14px | 400 | 0 | 1.55 | `--text` |
| **card summary** | Inter | 12.5px | 400 | 0 | 1.6 | `--text-dim` |
| **meta / timestamp** | JetBrains Mono | 10–11px | 600 | `0.04em` | 1 | `--text-mute` |
| **tier chip** | Inter | 9px | 900 | `0.08em` | 1 | ALL CAPS, tinted bg + same-color border @ 0.4 alpha |
| **code / kbd** | JetBrains Mono | 12–13px | 500–600 | 0 | 1.55 | — |
| **prose (guide pages)** | Inter | 16–17px | 400 | 0 | 1.75 | Long-form reading rhythm |

### Casing rules

- **Section headers, nav pills, tier badges, button labels:** ALL CAPS with tracking.
- **Card titles:** Title-case fragment with em-dash: `Subject — why I saved it`.
- **Body copy:** Sentence case, normal punctuation.
- **Never use all-caps for body text.**

### Voice signatures

- Em-dash with spaces: `Subject — clause`. Never `Subject—clause` or `Subject-clause`.
- Second person: "you scroll", "your saved tab", never "we" or "our".
- Hook opens: "You scroll, you tap save, you swear you'll come back. You don't."
- Section labels: `CLONE THESE REPOS` · `INSTALL THESE TOOLS` · `READ THESE GUIDES` · `TRY THESE TECHNIQUES`.

---

## 4 · Component Stylings

### Buttons

**Primary (gradient action):**
```css
padding: 9px 14px;
border-radius: 8px;
font: 800 11px/1 Inter;
letter-spacing: .08em;
text-transform: uppercase;
background: linear-gradient(135deg, rgba(167,139,250,.3), rgba(244,114,182,.3));
border: 1px solid rgba(167,139,250,.55);
color: #fff;
/* hover */ filter: brightness(1.18);
```

**Secondary (panel):**
```css
background: rgba(255,255,255,0.03);
border: 1px solid rgba(255,255,255,0.15);
color: #e8e8f0;
/* hover */ background: rgba(255,255,255,0.08);
```

**Nav pill (default / active):**
```css
/* default */
padding: 6px 12px; border-radius: 999px;
font: 700 11px/1 Inter; letter-spacing: .05em; text-transform: uppercase;
background: rgba(255,255,255,0.03);
border: 1px solid rgba(255,255,255,0.08);
color: #a0a0b8;

/* active (.on) */
background: linear-gradient(135deg, rgba(167,139,250,.25), rgba(244,114,182,.25));
border-color: rgba(167,139,250,.5);
color: #fff;

/* hover */
background: rgba(255,255,255,0.05);
color: #e8e8f0;
border-color: rgba(255,255,255,0.15);
```

### Cards (the catalog primitive)

```
┌─────────────────────────────────────────┐  ← 2px gradient top bar @ 0.35 opacity
│ ▌ Card title — terse subject        [S] │  ← 3px colored left border (category)
│ ▌                                       │
│ ▌ One to three sentences of summary in  │  ← --text-dim, 12.5px, line-height 1.6
│ ▌ dim gray, second-person.              │
│ ▌                                       │
│ ▌ [optional 5:2 thumbnail with hover    │
│ ▌  scale(1.04) @ 300ms]                 │
│ ▌ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │  ← 1px dashed divider
│ ▌ [repo] [tool]                         │  ← category chips (tinted + bordered)
│ ▌ @creator · 4 days ago                 │  ← JetBrains Mono meta row
└─────────────────────────────────────────┘
```

```css
padding: 18px;
background: rgba(255,255,255,0.03);
border: 1px solid rgba(255,255,255,0.08);
border-left: 3px solid var(--c-[category]);   /* REQUIRED when categorized */
border-radius: 14px;
transition: all .18s;
/* gradient top bar via ::before at 2px height, 35% opacity */

/* hover */
background: rgba(255,255,255,0.05);
border-color: rgba(255,255,255,0.15);
transform: translateY(-2px);
box-shadow: 0 4px 16px rgba(0,0,0,.25);
```

### Tier chip (top-right of card head)

```css
padding: 3px 8px; border-radius: 5px;
font: 900 9px/1 Inter; letter-spacing: .08em; text-transform: uppercase;
/* S */ color: #fbbf24; background: rgba(251,191,36,.08); border: 1px solid rgba(251,191,36,.4);
/* A */ color: #a78bfa; background: rgba(167,139,250,.08); border: 1px solid rgba(167,139,250,.4);
/* B */ color: #60a5fa; background: rgba(96,165,250,.08); border: 1px solid rgba(96,165,250,.4);
/* C */ color: #a0a0b8; background: rgba(106,106,128,.12); border: 1px solid rgba(106,106,128,.4);
```

### Category chip (bottom of card)

```css
font: 700 9px/1 Inter; letter-spacing: .05em; text-transform: uppercase;
padding: 2px 6px; border-radius: 4px;
color: var(--c-[cat]);
background: rgba(255,255,255,0.03);
border: 1px solid color-mix(in srgb, var(--c-[cat]) 34%, transparent);
```

### Inputs

```css
background: rgba(0,0,0,.55);
border: 1px solid rgba(255,255,255,0.08);
border-radius: 8px;
padding: 9px 11px;
color: #e8e8f0;
font: 400 13px/1.4 'JetBrains Mono', monospace;
/* placeholder: color #6a6a80 */
/* focus: border rgba(167,139,250,.5), no ring, no outline */
```

### Header / nav

```css
position: sticky; top: 0; z-index: 100;
height: 56px;
padding: 14px 22px;
display: flex; align-items: center; gap: 24px;
background: rgba(10,10,15,0.88);
backdrop-filter: blur(20px);
border-bottom: 1px solid rgba(255,255,255,0.08);
```

The **wordmark** inside the header is literal text styled with the brand gradient — there is no separate logo SVG required (though `assets/wordmark.svg` exists).

### Sidebar

```css
position: sticky; top: 80px;
width: 260px;
padding: 18px;
background: rgba(18,18,26,0.85);
backdrop-filter: blur(14px);
border: 1px solid rgba(255,255,255,0.08);
border-radius: 14px;
```

Active category button uses `box-shadow: inset 3px 0 0 var(--c-[cat])` — a colored left rail, never a border swap.

### BANs (big-ass numbers — hero stats)

```
┌──────────────┐
│  334         │  ← 28px / 900 / #fff / line-height 1
│  POSTS       │  ← 10.5px / 700 / --text-mute / letter-spacing .09em
└──────────────┘
```

Used in grids of 3–4 under the hero. Never in body.

### Detail panel (modal)

```css
width: min(560px, 100%);
padding: 28px;
background: rgba(18,18,26,0.95);
border: 1px solid rgba(255,255,255,0.12);
border-radius: 14px;
box-shadow: 0 10px 32px rgba(0,0,0,.45);
```

Backdrop: `rgba(5,5,10,0.7)` + `backdrop-filter: blur(6px)`. Entrance: `ddFadeIn` keyframe — `opacity 0→1` + `translateY(-8px → 0)` over 0.2s ease. No bounces.

### Hint strip (floating help, bottom-right)

```css
position: fixed; right: 20px; bottom: 20px;
padding: 10px 14px;
background: rgba(18,18,26,0.85);
backdrop-filter: blur(14px);
border: 1px solid rgba(255,255,255,0.08);
border-radius: 10px;
font: 400 12px/1.4 Inter;
color: #a0a0b8;
/* leading glyph (◉) in --ok green */
```

### Keyboard (kbd)

```css
padding: 2px 8px;
border-radius: 4px;
background: rgba(167,139,250,.18);
border: 1px solid rgba(167,139,250,.35);
font: 600 11px/1 'JetBrains Mono', monospace;
color: #e8e8f0;
```

### Command chip (inline code)

```css
/* inline */ background: rgba(0,0,0,.45); border: 1px solid var(--border);
padding: 2px 8px; border-radius: 6px;
color: #a78bfa; font: 500 12.5px/1 'JetBrains Mono';

/* block (command row) */
background: rgba(0,0,0,.55); padding: 10px 12px; border-radius: 8px;
/* always prefixed with a dim "$" in --text-mute */
```

---

## 5 · Layout Principles

**Grid.** Static 12-col is not used. Catalog uses responsive `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` with `gap: 14px`. Sidebar pages use fixed `260px | 1fr` at ≥900px.

**Max content width.** 1500px for catalog, 1280px for long-form prose, 720px for reading-column pages.

**Page padding.** `28px 22px 60px` desktop, collapsing to `0 14px 40px` on mobile.

**Spacing scale** (4-px base, but values are mostly inline — these are the common stops):

```
4  8  10  12  14  16  18  20  22  28  32  40  48  60
```

- Card padding: **18px** desktop, **14px** mobile.
- Section margin: **40px** between blocks.
- Section head margin: **32px 0 14px** (above a new group).
- Form field gap: **8px**.

**Whitespace philosophy.** Tight but never cramped. The page breathes because of the atmosphere (radial gradients) and glass panels, not because of huge empty margins. Never add vertical space just to "feel clean" — density is a feature.

**Sticky rules.**
- Header: always sticky, `top: 0`, `z-index: 100`.
- Sidebar: sticky `top: 80px`, `align-self: start`, `max-height: calc(100vh - 100px)`, own scroll.
- Hint strip: `position: fixed`, bottom-right, `z-index: 50`.

---

## 6 · Depth & Elevation

Shadow is **support for the border, not a substitute.** Every elevated surface is: translucent fill + 1px border + (optional) shadow + (mandatory on floating chrome) backdrop blur.

| Token | Value | Use |
|---|---|---|
| `--shadow-1` | `0 4px 16px rgba(0,0,0,.25)` | Cards (hover only), notes |
| `--shadow-2` | `0 10px 32px rgba(0,0,0,.45)` | Modals, popovers, detail panel |
| *(no `--shadow-3`)* | — | No heavy drop shadows exist in this system |

**Glassmorphism formula** (mandatory on floating chrome):

```css
background: rgba(18,18,26, 0.85 or 0.94 or 0.95);  /* body-matched tint */
backdrop-filter: blur(14px);       /* tooltips, hint, sidebar */
backdrop-filter: blur(20px);       /* header */
border: 1px solid rgba(255,255,255,0.08);
```

**Elevation ladder (logical, not literal z-index):**

0. Body atmosphere — flat
1. Cards — panel bg + 1px border (no shadow at rest)
2. Hover cards — translate `-2px` + shadow-1
3. Sidebar — glass rgba(18,18,26,.85) + blur(14)
4. Header — glass rgba(10,10,15,.88) + blur(20)
5. Hint strip — glass + shadow-1
6. Detail modal — glass rgba(18,18,26,.95) + shadow-2
7. Tooltip / context menu — glass rgba(18,18,26,.94) + shadow-2

**Body content is never blurred.** Blur is a signal for "this chrome is floating above".

---

## 7 · Do's and Don'ts

### DO

- ✅ Use `#0a0a0f` + the two radial gradients as the body background **on every page**.
- ✅ Build hierarchy with weight (800–900) before you reach for larger type.
- ✅ Use the brand gradient (`#fff → --accent → --accent-2` @ 135°) for **exactly one element per view** — usually the `h1` or wordmark.
- ✅ Apply category color as a **3px left border** on cards, not a full tint.
- ✅ Apply tier color as a **tinted chip** with same-color 0.4-alpha border in the card's top-right.
- ✅ Use Unicode glyphs first for icons: `◉ ◆ ▪ ⬤ ⬡ ⬢ ★`.
- ✅ Write in second person. Use em-dashes with spaces.
- ✅ Use ALL CAPS + tracking for section labels, nav pills, buttons, tier badges.
- ✅ Keep transitions ≤ 200ms, always `ease`. Use `translateY(-2px)` for card hovers.
- ✅ Use `backdrop-filter: blur()` on every floating chrome surface.

### DON'T

- ❌ Don't use pure black (`#000`) or pure white (`#fff`) for surfaces or body text.
- ❌ Don't add `font-weight: 300` or lower. DejaViewed has no light weights.
- ❌ Don't use solid-color category backgrounds (green repo card with green bg). The category is a *rail*, not a paint.
- ❌ Don't introduce new accent colors. The palette is closed: violet/pink/blue + tier + category only.
- ❌ Don't use decorative emoji in body copy. Glyph-emoji in headings only (`👥 creators cited`).
- ❌ Don't use Lucide / Heroicons / Phosphor unless you've checked no Unicode glyph fits first.
- ❌ Don't use entrance animations over 200ms. No bounces, no springs, no staggered reveals.
- ❌ Don't blur body content. Blur is only for floating chrome.
- ❌ Don't write in first-person plural ("we believe", "our catalog"). Voice is always "you".
- ❌ Don't use illustration or hand-drawn graphics. Only real thumbnails (user content) or gradient-haze placeholders.
- ❌ Don't leave empty hero space. Density is the product.

---

## 8 · Responsive Behavior

**Breakpoints:**

| Width | Change |
|---|---|
| ≥ 1500px | Max catalog width caps at 1500, centered. |
| ≥ 900px | 260px sidebar + 1fr content with 28px gap. |
| < 900px  | Sidebar becomes a collapsible bottom-sheet or stacked block above the grid. Layout becomes single-column. |
| < 640px  | Card padding 18 → 14. BANs grid 4-col → 2-col. Hero `h1` clamps down to 32px. |
| < 400px  | Nav pills wrap to two lines; hint strip becomes full-width bottom bar. |

**Touch targets.** All interactive surfaces are ≥ 36px tall on touch. Nav pills enforce `padding: 10px 14px` below 640px (up from 6/12).

**Collapsing strategy.**
- **Sidebar** → collapsible sheet accessed from a `FILTERS` pill in the header.
- **BANs** → 4 across desktop, 2×2 tablet, 2×2 (smaller) mobile. Never stack 1×4.
- **Nav** → if pills exceed width, wrap to new line inside header; do NOT hamburger the nav.
- **Card grid** → always `auto-fill, minmax(280px, 1fr)`. Don't force single column before 500px.

**Scroll behavior.** Body scrolls normally. Sidebar has its own `overflow-y: auto` with a max-height tied to viewport. Header is always visible (sticky). Never intercept scroll.

---

## 9 · Agent Prompt Guide

Paste one of these into your agent to keep output on-brand.

### Fast reference

```
Background: #0a0a0f + radial(80% 50% at 50% -20%, rgba(167,139,250,.14), transparent),
            radial(60% 40% at 80% 10%, rgba(244,114,182,.08), transparent).
Primary text #e8e8f0. Dim #a0a0b8. Mute #6a6a80.
Accent violet #a78bfa, pink #f472b6, blue #60a5fa.
Tiers: S #fbbf24, A #a78bfa, B #60a5fa, C #6a6a80.
Fonts: Inter 400/500/700/800/900, JetBrains Mono 400/500/700.
Radius: 14 cards, 8 inputs, 999 pills, 4 chips.
Border: rgba(255,255,255,0.08) default, 0.15 hover.
Glass chrome: rgba(18,18,26,0.85) + backdrop-filter blur(14–20).
```

### Ready-to-use prompts

**New page:**
> Build a [PAGE] for DejaViewed. Use DESIGN.md. Body must have the #0a0a0f base with the two radial violet+pink gradients. Sticky 56px glassy header with the gradient-text wordmark. Content inside a 260 sidebar + 1fr layout at ≥900px. All type Inter (no weight below 400), mono is JetBrains Mono. Voice: second person, em-dash with spaces, mildly conspiratorial. Use Unicode glyphs for icons (◉ ◆ ▪ ⬡ ⬢ ★). One gradient-clipped h1 per view. No pure black, no pure white for prose.

**New card variant:**
> Extend the catalog card pattern from DESIGN.md for a [NEW TYPE]. Keep the 14px radius, 18px padding, 3px colored left border for the primary category, 2px gradient top bar at 0.35 opacity, tier chip top-right, em-dash title pattern, 12.5px dim summary, category chips above a 1px dashed divider, JetBrains-Mono meta row. Hover translates -2px with shadow-1.

**New marketing section:**
> Add a section to the DejaViewed landing that uses one of these label patterns: CLONE THESE REPOS / INSTALL THESE TOOLS / READ THESE GUIDES / TRY THESE TECHNIQUES. The label is Inter 800 10-11px, letter-spacing .10em, --text-mute, ALL CAPS. Below it, a grid of catalog cards. No icon beside the label unless it's a single Unicode glyph in accent color.

**New interactive element:**
> Use the pill-button pattern. Default: rgba(255,255,255,0.03) bg, 1px rgba(255,255,255,0.08) border, --text-dim color, 999 radius, 11px 700 Inter uppercase with .05em tracking. Active (.on): gradient rgba(167,139,250,.25)→rgba(244,114,182,.25), border rgba(167,139,250,.5), color #fff. Hover: bg .05, border .15, color --text. Transitions all 150ms ease. No scale, no bounce.

### When unsure, default to this

> Dark-mode terminal × glassmorphism × violet-pink dusk. Confident curator, not breathless launcher. Weight over size. Unicode glyphs over icon libraries. Glass on floating chrome only. "You've saved this before."

---

## 10 · What this product is (for agents who need context)

DejaViewed is a **Claude Code plugin** — a `SKILL.md`-packaged agent skill installable to `~/.claude/skills/dejaviewed/`. It:

1. **Ingests** user saves from Instagram, TikTok, Twitter/X, Reddit, YouTube, Pinterest, browser bookmarks.
2. **Classifies** each save by category (repo · tool · skill · guide · platform · resource · art · design · uiux) and tier (S/A/B/C).
3. **Dives** — for worth-it entries, generates a deep-dive guide at `site/deeper/<slug>.html` with the links the creator wouldn't give you.
4. **Connects** — cross-links creators, tools, techniques into a force-directed knowledge graph and a WebGL cosmos.
5. **Acts** — a drag-to-connect thought board turns the saves pile into actionable project/idea graphs.

The static site (this design system) is the **demo surface** for the skill — it's what you look at to understand what the skill produces.

Agent-friendly artifacts in the repo:
- `SKILL.md` — skill manifest, entrypoint for Claude Code.
- `site/api/catalog.json` — machine-readable entry list.
- `site/.well-known/ai-plugin.json` — plugin discovery.
- `DESIGN.md` — **this file** — so any agent can re-generate new UI on-brand.

---

**Version:** 1.0 · April 2026
**Canonical source:** `dejaviewed-plugin/site/shared.css`
**Substitutions flagged:** icons default to Unicode glyphs; Lucide allowed as fallback with review. Fonts via Google Fonts CDN; `.woff2` swap-in supported.
