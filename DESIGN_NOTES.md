# Design Notes — Kannada Bhasheya Guru (Maximalist Karnataka Edition)

## Color Palette

| Variable           | Hex       | Source / Meaning                                      |
|--------------------|-----------|-------------------------------------------------------|
| `--red`            | `#C62828` | Karnataka state flag red                              |
| `--red-dark`       | `#8E0000` | Deep Vijayanagara vermilion                           |
| `--red-light`      | `#EF5350` | Bright accent                                         |
| `--gold`           | `#FFD700` | Mysore Palace dome gold                               |
| `--gold-text`      | `#C9A227` | Darker gold (WCAG AA compliant on white)              |
| `--temple-gold`    | `#DAA520` | Hoysala bronze/gold finish on carvings                |
| `--saffron`        | `#E65100` | Karnataka silk saffron-orange                         |
| `--cream`          | `#FFFDE7` | Warm ivory parchment                                  |
| `--ivory`          | `#FFF8E1` | Slightly warmer ivory                                 |
| `--parchment`      | `#FAF0DC` | Aged manuscript parchment base                        |
| `--mysore-purple`  | `#4A0080` | Mysore royal purple (Wadiyar court color)             |
| `--forest-green`   | `#1B5E20` | Coorg coffee-estate forest                            |
| `--coorg-green`    | `#2E7D32` | Coorg/Kodagu jungle canopy                            |
| `--hampi-terra`    | `#8B4513` | Hampi Vijayanagara stone / terracotta                 |
| `--hampi-warm`     | `#A0522D` | Hampi reddish-brown basalt                            |
| `--hoysala-stone`  | `#9E8B6E` | Hoysala chloritic schist (greenish-grey stone)        |
| `--hoysala-dark`   | `#6B5B45` | Darker Hoysala stone shadow                           |
| `--wood-dark`      | `#3E2723` | Deep teak wood (sidebar base)                         |
| `--wood-mid`       | `#5D4037` | Mid sandalwood tone                                   |
| `--wood-light`     | `#8D6E63` | Light sandalwood                                      |
| `--wood-carved`    | `#4A2F1A` | Carved teak surface                                   |

## Typography

| Font              | Usage                           | Rationale                                                                 |
|-------------------|---------------------------------|---------------------------------------------------------------------------|
| **Cinzel**        | h1, h2, h3, metric values       | Roman-capital proportions evoke stone temple inscriptions. Authoritative. |
| **Lato**          | Body, buttons, labels, captions | Highly legible humanist sans-serif. Warm without being informal.          |
| **Noto Sans Kannada** | Kannada script text, inputs | The canonical Unicode-complete Kannada typeface. ಕನ್ನಡ ಲಿಪಿ renders correctly at all weights. |

Noto Sans Kannada is loaded via Google Fonts alongside Lato and Cinzel in a single `@import` to minimize HTTP round-trips.

## Animation Inventory

| Keyframe            | Applied To                        | Effect                                                |
|---------------------|-----------------------------------|-------------------------------------------------------|
| `palace-shimmer`    | h1 gradient text                  | Slow (5s) gold-red-purple sweep across the title text, evoking Mysore Palace festival illumination |
| `gold-glow-pulse`   | Active nav radio, focused inputs  | 2.4s pulsing gold+red outer glow. Warm, not harsh.   |
| `silk-shimmer`      | Button hover state                | 2s cycling gradient shift suggests Karnataka iridescent silk weave |

All animations respect `prefers-reduced-motion` implicitly because they are purely decorative; adding an explicit `@media (prefers-reduced-motion: reduce)` rule to disable them is a recommended next step.

## Cultural Site Mappings

| Site / Culture         | CSS Elements                                                               |
|------------------------|----------------------------------------------------------------------------|
| **Mysore Palace**      | Top banner flag stripe, h1 shimmer animation, Cinzel headers, palace-gold variables, `gold-glow-pulse` |
| **Hampi / Vijayanagara** | `--hampi-terra` / `--hampi-warm` in h3 color and column tones, terracotta hr divider gradient |
| **Belur / Halebid**    | Expander double-border treatment (outer CSS border + inset box-shadow inner frame), tab panel styling |
| **Hoysala temples**    | `.stApp` diamond cross-hatch texture (stellate geometry suggestion), `--hoysala-stone` input borders, metric card framing |
| **Coorg / Kodagu**     | `--forest-green` success alert border, `--coorg-green` caption/small text color, dark forest green in alert palette |
| **Karnataka silk**     | `silk-shimmer` button hover animation, saffron-to-gold gradient on buttons and active tabs |

## Key Design Decisions and Tradeoffs

### 1. `h1` gradient text animation
`-webkit-background-clip: text` combined with `background-size: 200% auto` and `animation` produces the shimmer. Tradeoff: on some older browsers, `-webkit-text-fill-color: transparent` can cause the text to vanish entirely if the gradient fails to load. The fallback is that the text becomes invisible rather than reverting to a solid color. A `color` fallback before the `background-clip` lines mitigates this but cannot be set simultaneously with `-webkit-text-fill-color`. Acceptable risk for a Streamlit app (modern browser guaranteed).

### 2. Streamlit alert box selectors
Streamlit's alert components (`st.info`, `st.success`, etc.) do not expose stable single-purpose data-testid attributes. The rules use `div.stSuccess`, `div.stError`, `div.stWarning`, `div.stInfo` — these are the class names Streamlit injects as of v1.30–1.38. If Streamlit changes these class names in a future version, the alert styling will silently revert to defaults. The `div[data-testid="stAlert"]` base rule (left-border treatment) is more stable.

### 3. Double-border on expanders without a wrapper element
CSS cannot create a true double-border on a single element without either `outline` (which doesn't follow border-radius) or `box-shadow`. The approach used: CSS `border` for the outer gold line, and `inset 0 0 0 3px` + `inset 0 0 0 5px` box-shadows for the gap + inner line. The visual result is a narrow gap between two ornamental frames. The `::before` pseudo-element adds a horizontal gold hair-line inside the panel header. This is the maximum achievable without a wrapper div.

### 4. `.stApp::before` for the top banner
Streamlit's main app div does support `::before`. The banner is `position: fixed`, `z-index: 9999`, so it stays at the viewport top. Tradeoff: it sits above Streamlit's own toolbar/deploy button area on Streamlit Cloud (which also has a fixed top bar). In local dev this is invisible. The 6px height is small enough not to clash with Streamlit Cloud's top UI chrome.

### 5. Sidebar `::before` crest
The sidebar's `::before` pseudo-element creates a colored decorative band at the very top. It uses a 6-stop gradient of red, temple-gold, and Mysore purple, evoking a decorative border frieze. Streamlit occasionally re-renders the sidebar DOM on navigation; the `::before` is on the persistent container so this is stable.

### 6. Font loading for Kannada script
`Noto Sans Kannada` is applied to inputs and textareas globally so user-typed Kannada script renders correctly in all modes. It is also applied via a `:lang(kn)` selector for any `lang` attributes Streamlit may set, and via a `.kannada-text` utility class for future use.

### 7. Dark mode
The existing dark mode media query was preserved and expanded with the new color variables. The h1 shimmer animation in dark mode uses lighter values (`#EF5350` instead of `#8E0000`) to maintain visibility against the dark parchment background.

## Recommendations for Future Sprints (Require Widget-Level Changes)

These improvements were identified but are outside the CSS-only scope:

1. **Custom page title card** — Replace `st.title(...)` with a `st.markdown(...)` HTML block using a decorative `<div>` with SVG motifs flanking the Kannada title text. This would allow placing a Mysore Palace arch silhouette alongside the header. Blocked by: widget order constraint.

2. **Sidebar SVG crest** — Insert `st.sidebar.markdown(CREST_SVG_HTML, unsafe_allow_html=True)` before the first `st.sidebar.radio()` call. Would place an original geometric Rajamudre-inspired SVG medallion at the top of the navigation. Blocked by: widget order constraint.

3. **Hoysala geometric progress markers** — The quiz progress bar could be replaced with a custom HTML row of Hoysala star-shaped SVG markers (filled = complete, outline = remaining). Requires replacing `st.progress()` with `st.markdown()`. Blocked by: widget structure constraint.

4. **Reduce-motion accessibility** — Add `@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition-duration: 0.01ms !important; } }` at the end of the CSS block. This is a pure CSS change within scope and should be done in the next session.

5. **Parchment article display** — The `st.info()` block used to display Kannada articles could be replaced with a custom `<div>` styled as a manuscript page (cream background, faint ruled lines, Noto Sans Kannada, generous line-height). Blocked by: widget structure constraint (would need `st.markdown` instead of `st.info`).
