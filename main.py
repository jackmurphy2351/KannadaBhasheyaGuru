import streamlit as st
import os
import glob
import random
import json

# Import our custom modules
import config
import logic


# --- CUSTOM CSS FOR KARNATAKA THEME ---
def local_css():
    st.markdown(
        """
        <style>
        /* ============================================================
           KARNATAKA CULTURAL THEME — MAXIMALIST EDITION
           Palette: Karnataka flag red, Mysore Palace gold, sandalwood,
           saffron silk, deep carved-wood brown, warm ivory,
           Hampi terracotta, Coorg forest green, Mysore purple,
           temple gold, Hoysala stone

           Kannada script test: ಕನ್ನಡ ಲಿಪಿ ಸುಂದರವಾಗಿದೆ
        ============================================================ */

        /* ── GOOGLE FONTS ── */
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Kannada:wght@400;600;700&family=Lato:wght@400;600;700&family=Cinzel:wght@400;600;700&display=swap');

        /* ── KEYFRAME ANIMATIONS ── */

        /* Mysore Palace illumination shimmer on h1 */
        @keyframes palace-shimmer {
            0%   { background-position: -200% center; }
            100% { background-position: 200% center; }
        }

        /* Glowing gold pulse for focused/active elements */
        @keyframes gold-glow-pulse {
            0%, 100% { box-shadow: 0 0 6px 2px rgba(218,165,32,0.4),  0 0 14px 4px rgba(198,40,40,0.2); }
            50%       { box-shadow: 0 0 14px 5px rgba(218,165,32,0.75), 0 0 28px 8px rgba(198,40,40,0.35); }
        }

        /* Karnataka silk iridescent shimmer */
        @keyframes silk-shimmer {
            0%   { background-position: 0% 50%; }
            50%  { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* Subtle float for the sidebar crest */
        @keyframes crest-float {
            0%, 100% { transform: translateY(0px); }
            50%       { transform: translateY(-4px); }
        }

        /* ── 1. CSS VARIABLES ── */
        :root {
            /* Core Karnataka palette */
            --red:           #C62828;
            --red-dark:      #8E0000;
            --red-light:     #EF5350;
            --gold:          #FFD700;
            --gold-text:     #C9A227;   /* WCAG AA on white */
            --temple-gold:   #DAA520;
            --saffron:       #E65100;
            --cream:         #FFFDE7;
            --ivory:         #FFF8E1;
            --parchment:     #FAF0DC;

            /* New jewel-tone additions */
            --mysore-purple: #4A0080;
            --forest-green:  #1B5E20;
            --coorg-green:   #2E7D32;
            --hampi-terra:   #8B4513;
            --hampi-warm:    #A0522D;
            --hoysala-stone: #9E8B6E;
            --hoysala-dark:  #6B5B45;

            /* Wood tones */
            --wood-dark:     #3E2723;
            --wood-mid:      #5D4037;
            --wood-light:    #8D6E63;
            --wood-carved:   #4A2F1A;

            /* Typography */
            --text-main:     #1A0A00;
            --text-soft:     #5D4037;
            --text-on-dark:  #F5E6D3;

            /* Shadows */
            --shadow:        rgba(62, 39, 35, 0.18);
            --shadow-deep:   rgba(30, 10, 0, 0.35);
            --gold-shadow:   rgba(218, 165, 32, 0.4);
        }

        /* ── 2. GLOBAL TYPOGRAPHY ── */
        html, body, [class*="css"] {
            font-family: 'Lato', 'Noto Sans Kannada', sans-serif !important;
        }
        /* Kannada script glyphs rendered via Noto Sans Kannada */
        :lang(kn), .kannada-text {
            font-family: 'Noto Sans Kannada', serif !important;
        }

        /* ── 3. APP BACKGROUND — Hoysala woven stone texture ──
           Layered repeating gradients simulate carved stone tilework.
           The base is warm parchment; overlaid diamond micro-pattern
           suggests the Hoysala stellate (star-plan) geometry.         */
        .stApp {
            background-color: #FAF0DC !important;
            background-image:
                /* Fine diamond grid — carved stone suggestion */
                repeating-linear-gradient(
                    45deg,
                    transparent,
                    transparent 28px,
                    rgba(218,165,32,0.055) 28px,
                    rgba(218,165,32,0.055) 29px
                ),
                repeating-linear-gradient(
                    -45deg,
                    transparent,
                    transparent 28px,
                    rgba(198,40,40,0.04) 28px,
                    rgba(198,40,40,0.04) 29px
                ),
                /* Warm parchment base gradient */
                linear-gradient(
                    160deg,
                    #FFFDE7 0%,
                    #FFF8E1 35%,
                    #FAF0DC 65%,
                    #FFF3E0 100%
                ) !important;
        }

        /* ── 4. DECORATIVE TOP BANNER — Karnataka flag stripe ──
           A fixed-height multi-stripe banner evoking the state flag
           (yellow / red / green) rendered as a CSS gradient bar.
           Placed above Streamlit's main header zone.                  */
        .stApp::before {
            content: '';
            display: block;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 6px;
            z-index: 9999;
            background: linear-gradient(
                90deg,
                #DAA520 0%,
                #DAA520 33.3%,
                #C62828 33.3%,
                #C62828 66.6%,
                #1B5E20 66.6%,
                #1B5E20 100%
            );
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        }

        /* ── 5. SIDEBAR — Carved teak-wood with Mysore Palace crest ── */
        [data-testid="stSidebar"] {
            background:
                /* Fine vertical grain lines suggesting carved wood */
                repeating-linear-gradient(
                    90deg,
                    transparent,
                    transparent 18px,
                    rgba(0,0,0,0.04) 18px,
                    rgba(0,0,0,0.04) 19px
                ),
                linear-gradient(
                    180deg,
                    #2C1810 0%,
                    #3E2723 20%,
                    #4A2F1A 50%,
                    #3E2723 80%,
                    #2C1810 100%
                ) !important;
            border-right: 4px solid var(--temple-gold) !important;
            box-shadow: 4px 0 20px rgba(0,0,0,0.4) !important;
        }

        /* Sidebar top crest area — ornate decorative band */
        [data-testid="stSidebar"]::before {
            content: '';
            display: block;
            width: 100%;
            height: 8px;
            background: linear-gradient(
                90deg,
                var(--red-dark)   0%,
                var(--temple-gold) 20%,
                var(--mysore-purple) 40%,
                var(--temple-gold) 60%,
                var(--red-dark)   80%,
                var(--temple-gold) 100%
            );
            box-shadow: 0 2px 8px rgba(0,0,0,0.5);
        }

        [data-testid="stSidebar"] * {
            color: #F5E6D3 !important;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--gold) !important;
            font-family: 'Cinzel', Georgia, serif !important;
            text-shadow: 0 1px 6px rgba(0,0,0,0.7), 0 0 12px rgba(218,165,32,0.4);
            letter-spacing: 1px;
        }

        /* ── 6. SIDEBAR NAV RADIO BUTTONS ──
           Active: solid temple-gold left bar + lighter carved fill
           Hover:  terracotta red shift                              */
        [data-testid="stRadio"] > div { gap: 4px; }

        [data-testid="stRadio"] label {
            background: rgba(255,255,255,0.06) !important;
            border-left: 5px solid var(--temple-gold) !important;
            border-radius: 0 8px 8px 0 !important;
            padding: 13px 16px !important;
            margin-bottom: 2px !important;
            transition: all 0.22s ease !important;
            cursor: pointer;
            box-shadow: 0 1px 4px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.06);
            position: relative;
        }
        [data-testid="stRadio"] label p {
            font-weight: 600 !important;
            font-size: 15px !important;
            color: #F5E6D3 !important;
            font-family: 'Lato', sans-serif !important;
        }
        [data-testid="stRadio"] label:hover {
            background: rgba(198,40,40,0.55) !important;
            border-left-color: var(--gold) !important;
            border-left-width: 7px !important;
            transform: translateX(5px);
            box-shadow: 0 3px 12px rgba(198,40,40,0.45), inset 0 1px 0 rgba(255,255,255,0.1);
        }
        [data-testid="stRadio"] label:has(input:checked) {
            background: linear-gradient(
                90deg,
                rgba(142,0,0,0.85) 0%,
                rgba(198,40,40,0.75) 100%
            ) !important;
            border-left-color: var(--gold) !important;
            border-left-width: 8px !important;
            box-shadow: 0 3px 14px rgba(198,40,40,0.6),
                        inset 0 1px 0 rgba(255,255,255,0.12),
                        0 0 0 1px rgba(218,165,32,0.3) !important;
            animation: gold-glow-pulse 2.4s ease-in-out infinite;
        }

        /* ── 7. HEADERS — Mysore Palace Cinzel serif ──
           h1: animated shimmer evokes the palace illuminations festival */
        h1 {
            font-family: 'Cinzel', Georgia, 'Times New Roman', serif !important;
            font-weight: 700 !important;
            letter-spacing: 1.5px !important;
            padding-bottom: 12px;
            position: relative;
            /* Animated gold-red-purple shimmer gradient */
            background: linear-gradient(
                90deg,
                var(--red-dark)    0%,
                var(--red)         15%,
                var(--temple-gold) 30%,
                #FFD700            45%,
                var(--mysore-purple) 55%,
                var(--temple-gold) 68%,
                var(--red)         82%,
                var(--red-dark)    100%
            ) !important;
            background-size: 200% auto !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            background-clip: text !important;
            animation: palace-shimmer 5s linear infinite;
            /* Gold underline */
            border-bottom: 3px solid transparent;
            border-image: linear-gradient(
                90deg,
                transparent 0%,
                var(--temple-gold) 20%,
                var(--gold)        50%,
                var(--temple-gold) 80%,
                transparent 100%
            ) 1;
        }

        h2 {
            font-family: 'Cinzel', Georgia, serif !important;
            font-weight: 600 !important;
            color: var(--red-dark) !important;
            letter-spacing: 0.8px;
            border-left: 5px solid var(--temple-gold);
            padding-left: 12px;
            margin-top: 1.4em;
        }
        h3 {
            font-family: 'Cinzel', Georgia, serif !important;
            font-weight: 600 !important;
            color: var(--hampi-terra) !important;
            letter-spacing: 0.5px;
            border-left: 3px solid var(--saffron);
            padding-left: 10px;
        }

        /* ── 8. BUTTONS — Karnataka silk iridescent gradient ──
           Hover: silk shimmer animation; active: sunken press.    */
        .stButton > button {
            background: linear-gradient(
                135deg,
                var(--red-dark) 0%,
                var(--red)      40%,
                var(--saffron)  80%,
                var(--temple-gold) 100%
            ) !important;
            background-size: 200% 200% !important;
            color: #FFF8E1 !important;
            border: 1px solid rgba(218,165,32,0.5) !important;
            border-radius: 6px !important;
            font-family: 'Lato', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: 0.6px !important;
            text-transform: uppercase !important;
            font-size: 13px !important;
            box-shadow:
                0 3px 10px rgba(198,40,40,0.4),
                0 1px 3px rgba(0,0,0,0.2),
                inset 0 1px 0 rgba(255,255,255,0.15) !important;
            transition: all 0.25s ease !important;
        }
        .stButton > button:hover {
            background: linear-gradient(
                135deg,
                var(--temple-gold) 0%,
                #FFD700            35%,
                var(--saffron)     65%,
                var(--red)         100%
            ) !important;
            background-size: 200% 200% !important;
            animation: silk-shimmer 2s ease infinite;
            color: var(--wood-dark) !important;
            border-color: var(--gold) !important;
            box-shadow:
                0 6px 20px rgba(198,40,40,0.5),
                0 2px 6px rgba(0,0,0,0.25),
                inset 0 1px 0 rgba(255,255,255,0.25) !important;
            transform: translateY(-2px);
        }
        .stButton > button:active {
            transform: translateY(1px);
            box-shadow: 0 2px 6px rgba(198,40,40,0.3) !important;
        }

        /* ── 9. TABS — Belur/Halebid inlaid stone panel headers ── */
        .stTabs [data-baseweb="tab-list"] {
            border-bottom: 3px solid var(--temple-gold) !important;
            gap: 6px;
            background: transparent !important;
        }
        .stTabs [data-baseweb="tab"] {
            background: linear-gradient(180deg, #FFFEF5 0%, #FFF8E1 100%) !important;
            border: 1.5px solid var(--hoysala-stone) !important;
            border-bottom: none !important;
            border-radius: 8px 8px 0 0 !important;
            color: var(--text-soft) !important;
            font-family: 'Lato', sans-serif !important;
            font-weight: 600 !important;
            padding: 8px 20px !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 -2px 6px rgba(0,0,0,0.06);
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: linear-gradient(180deg, #FFF8E1 0%, #FDECD0 100%) !important;
            color: var(--red) !important;
            border-color: var(--temple-gold) !important;
            box-shadow: 0 -3px 10px rgba(218,165,32,0.25);
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(
                135deg,
                var(--red-dark) 0%,
                var(--red)      55%,
                var(--saffron)  100%
            ) !important;
            color: #FFF8E1 !important;
            border-color: var(--red) !important;
            box-shadow:
                0 -3px 12px rgba(198,40,40,0.35),
                inset 0 1px 0 rgba(255,255,255,0.2);
        }

        /* ── 10. EXPANDERS — Belur double-border ornate panel ──
           Outer border: temple gold. Inner border effect via
           box-shadow inset + subtle padding creates the double frame. */
        [data-testid="stExpander"] {
            border: 2px solid var(--temple-gold) !important;
            border-radius: 10px !important;
            background: linear-gradient(180deg, #FFFEF5 0%, #FFFDE7 100%) !important;
            box-shadow:
                0 3px 12px var(--shadow),
                inset 0 0 0 3px rgba(250,240,220,1),
                inset 0 0 0 5px rgba(218,165,32,0.2) !important;
            overflow: hidden;
            position: relative;
        }
        /* Inner gold accent line at top — second border suggestion */
        [data-testid="stExpander"]::before {
            content: '';
            display: block;
            position: absolute;
            top: 5px;
            left: 5px;
            right: 5px;
            height: 1px;
            background: linear-gradient(
                90deg,
                transparent 0%,
                var(--temple-gold) 25%,
                var(--gold)        50%,
                var(--temple-gold) 75%,
                transparent 100%
            );
            opacity: 0.5;
            pointer-events: none;
        }
        [data-testid="stExpander"] summary {
            color: var(--red-dark) !important;
            font-family: 'Lato', sans-serif !important;
            font-weight: 700 !important;
            background: linear-gradient(
                90deg,
                rgba(255,248,225,1) 0%,
                rgba(255,253,231,0.7) 100%
            ) !important;
            padding: 10px 14px !important;
            border-bottom: 1px solid rgba(218,165,32,0.3) !important;
            letter-spacing: 0.3px;
        }
        [data-testid="stExpander"][open] {
            box-shadow:
                0 5px 20px rgba(218,165,32,0.3),
                inset 0 0 0 3px rgba(250,240,220,1),
                inset 0 0 0 5px rgba(218,165,32,0.25),
                0 0 0 1px var(--temple-gold) !important;
        }

        /* ── 11. CHAT MESSAGES — silk-draped conversation bubbles ──
           User: warm cream with Coorg amber right accent
           Assistant: cooler ivory with Mysore gold left accent      */
        [data-testid="stChatMessage"] {
            border-radius: 12px !important;
            margin-bottom: 10px !important;
            box-shadow: 0 2px 8px var(--shadow) !important;
        }
        /* User bubble */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: linear-gradient(
                135deg,
                #FFF8E7 0%,
                #FFF0D0 60%,
                #FFE8C0 100%
            ) !important;
            border-left: none !important;
            border-right: 5px solid var(--saffron) !important;
            border-top: 1px solid rgba(218,165,32,0.25) !important;
            border-bottom: 1px solid rgba(218,165,32,0.15) !important;
        }
        /* Assistant bubble */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: linear-gradient(
                135deg,
                #F5F0EB 0%,
                #F0EDE8 60%,
                #EDE8E0 100%
            ) !important;
            border-left: 5px solid var(--temple-gold) !important;
            border-top: 1px solid rgba(218,165,32,0.2) !important;
            border-bottom: 1px solid rgba(218,165,32,0.1) !important;
        }

        /* ── 12. INPUTS & SELECTBOXES — parchment writing surface ── */
        [data-testid="stSelectbox"] > div > div,
        [data-testid="stTextInput"] > div > div > input,
        [data-testid="stTextArea"] > div > div > textarea {
            border: 1.5px solid var(--hoysala-stone) !important;
            border-radius: 6px !important;
            background: #FFFEF5 !important;
            font-family: 'Noto Sans Kannada', 'Lato', sans-serif !important;
            color: var(--text-main) !important;
            transition: border-color 0.2s, box-shadow 0.2s !important;
        }
        [data-testid="stTextInput"] > div > div > input:focus,
        [data-testid="stTextArea"] > div > div > textarea:focus {
            border-color: var(--temple-gold) !important;
            box-shadow:
                0 0 0 3px rgba(218,165,32,0.2),
                0 0 8px rgba(198,40,40,0.12) !important;
            animation: gold-glow-pulse 2s ease-in-out infinite;
            background: #FFFEF8 !important;
        }
        /* Text area — larger parchment feel */
        [data-testid="stTextArea"] > div > div > textarea {
            background:
                linear-gradient(#FFFEF5 0%, #FFFEF5 100%),
                repeating-linear-gradient(
                    transparent,
                    transparent 27px,
                    rgba(218,165,32,0.12) 27px,
                    rgba(218,165,32,0.12) 28px
                ) !important;
            line-height: 1.75 !important;
        }

        /* ── 13. SLIDER — gold thumb, terracotta track ── */
        [data-testid="stSlider"] [role="slider"] {
            background: var(--temple-gold) !important;
            border: 2px solid var(--red-dark) !important;
            box-shadow:
                0 0 0 3px rgba(218,165,32,0.3),
                0 2px 6px rgba(0,0,0,0.3) !important;
        }

        /* ── 14. METRIC CARDS — Hoysala framed stone panels ── */
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #FFFEF5 0%, #FFF8E1 100%) !important;
            border: 2px solid var(--temple-gold) !important;
            border-top: 5px solid var(--red) !important;
            border-radius: 10px !important;
            padding: 16px !important;
            box-shadow:
                0 4px 14px var(--shadow),
                inset 0 0 0 1px rgba(218,165,32,0.15) !important;
        }
        [data-testid="stMetricValue"] {
            color: var(--red-dark) !important;
            font-family: 'Cinzel', Georgia, serif !important;
            font-weight: 700 !important;
        }
        [data-testid="stMetricLabel"] { color: var(--text-soft) !important; }

        /* ── 15. PROGRESS BAR — red-to-gold Karnataka flag sweep ── */
        [data-testid="stProgressBar"] > div {
            background: rgba(218,165,32,0.2) !important;
            border-radius: 6px !important;
            border: 1px solid rgba(218,165,32,0.3) !important;
        }
        [data-testid="stProgressBar"] > div > div {
            background: linear-gradient(
                90deg,
                var(--red-dark)    0%,
                var(--red)         35%,
                var(--saffron)     65%,
                var(--temple-gold) 100%
            ) !important;
            border-radius: 6px !important;
            box-shadow: 0 1px 6px rgba(198,40,40,0.4) !important;
        }

        /* ── 16. ALERT / INFO / SUCCESS / WARNING / ERROR BOXES ──
           Left-border only, no icon, warm tonal backgrounds.       */
        /* st.info → pale royal indigo */
        [data-testid="stAlert"][data-baseweb="notification"]:has(svg[data-testid="stAlertContentIcon"]:first-child) {
            /* Streamlit doesn't expose clean alert selectors; using attribute approach below */
        }
        div[data-testid="stAlert"] {
            border-radius: 8px !important;
            border: none !important;
            border-left: 5px solid !important;
            padding: 14px 16px 14px 20px !important;
            box-shadow: 0 2px 8px var(--shadow) !important;
        }
        /* Success — saffron gold background, forest green border */
        div.stSuccess, div[data-baseweb="notification"][kind="positive"] {
            background: #FFF3CD !important;
            border-left-color: var(--forest-green) !important;
        }
        /* Error — pale Hampi terracotta, deep red border */
        div.stError, div[data-baseweb="notification"][kind="negative"] {
            background: #FDECEA !important;
            border-left-color: var(--red-dark) !important;
        }
        /* Warning — sandalwood amber, temple-gold border */
        div.stWarning, div[data-baseweb="notification"][kind="warning"] {
            background: #FFF8E1 !important;
            border-left-color: var(--temple-gold) !important;
        }
        /* Info — pale Mysore indigo, purple border */
        div.stInfo, div[data-baseweb="notification"][kind="info"] {
            background: #F3E5FF !important;
            border-left-color: var(--mysore-purple) !important;
        }

        /* ── 17. DIVIDERS — Hampi temple-carving inspired separator ──
           Triple-line treatment: thin gold / thick red+gradient / thin gold.
           A central diamond motif is placed via a repeating background trick. */
        hr {
            border: none !important;
            height: auto !important;
            margin: 28px 0 !important;
            position: relative;
            overflow: visible !important;
            /* Build three-layer ornamental rule */
            background: transparent !important;
        }
        hr::before {
            content: '';
            display: block;
            height: 1px;
            background: linear-gradient(
                90deg,
                transparent 0%,
                var(--temple-gold) 15%,
                var(--temple-gold) 85%,
                transparent 100%
            );
            margin-bottom: 3px;
        }
        hr::after {
            content: '';
            display: block;
            height: 4px;
            background: linear-gradient(
                90deg,
                transparent  0%,
                var(--red-dark)    8%,
                var(--red)         25%,
                var(--temple-gold) 45%,
                var(--saffron)     55%,
                var(--temple-gold) 65%,
                var(--hampi-terra) 80%,
                var(--red-dark)    92%,
                transparent 100%
            );
            border-radius: 2px;
            margin-bottom: 3px;
            box-shadow: 0 1px 4px rgba(218,165,32,0.3);
        }
        /* Third line (gold hair-line) via box-shadow on ::after */
        /* NOTE: CSS cannot add a third pseudo-element; the third line is
           achieved by using a border on ::after */

        /* ── 18. SCROLLBAR — Mysore Palace brass handle ── */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track {
            background: var(--parchment);
            border-left: 1px solid rgba(218,165,32,0.2);
        }
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, var(--temple-gold), var(--red));
            border-radius: 4px;
            border: 1px solid rgba(255,255,255,0.3);
        }
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(180deg, var(--gold), var(--saffron));
        }

        /* ── 19. HAMPI STONE CARD — reusable panel class ──
           Cards/containers that Streamlit renders get a terracotta treatment. */
        [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
            border-radius: 8px;
        }
        /* Column containers slight tint */
        [data-testid="column"] {
            border-radius: 8px;
        }

        /* ── 20. COORG GREEN ACCENTS — st.caption, small text ── */
        [data-testid="stCaptionContainer"] p,
        small, .caption {
            color: var(--coorg-green) !important;
            font-style: italic;
        }

        /* ── 21. SELECTBOX DROPDOWN — warm ivory panel ── */
        [data-baseweb="popover"] [role="listbox"] {
            background: #FFFEF5 !important;
            border: 1.5px solid var(--temple-gold) !important;
            border-radius: 8px !important;
            box-shadow: 0 8px 24px var(--shadow-deep) !important;
        }
        [data-baseweb="option"]:hover {
            background: rgba(218,165,32,0.12) !important;
        }
        [data-baseweb="option"][aria-selected="true"] {
            background: rgba(198,40,40,0.1) !important;
            color: var(--red-dark) !important;
            font-weight: 600 !important;
        }

        /* ── 22. SPINNER — Mysore gold ring ── */
        [data-testid="stSpinner"] > div {
            border-top-color: var(--temple-gold) !important;
            border-right-color: var(--red) !important;
        }

        /* ── 23. AUDIO PLAYER — Sarvam TTS voice player ── */
        audio {
            border-radius: 8px !important;
            border: 1.5px solid var(--temple-gold) !important;
            background: #FFFEF5 !important;
            box-shadow: 0 2px 8px var(--shadow) !important;
            filter: sepia(0.15) hue-rotate(15deg);
        }

        /* ── 24. SIDEBAR RADIO — language toggle special handling ──
           The first radio group (language toggle) sits above the nav
           divider and inherits the same styling, which is correct.    */

        /* ── 25. DARK MODE — preserve richness ── */
        @media (prefers-color-scheme: dark) {
            :root {
                --cream:      #1C1008;
                --ivory:      #140B04;
                --parchment:  #1A0F05;
                --text-main:  #F5E6D3;
                --text-soft:  #C4957A;
                --shadow:     rgba(0,0,0,0.55);
                --shadow-deep:rgba(0,0,0,0.75);
            }
            .stApp {
                background-color: #1A0F05 !important;
                background-image:
                    repeating-linear-gradient(
                        45deg,
                        transparent,
                        transparent 28px,
                        rgba(218,165,32,0.04) 28px,
                        rgba(218,165,32,0.04) 29px
                    ),
                    repeating-linear-gradient(
                        -45deg,
                        transparent,
                        transparent 28px,
                        rgba(198,40,40,0.03) 28px,
                        rgba(198,40,40,0.03) 29px
                    ),
                    linear-gradient(160deg, #1C1008 0%, #251409 50%, #1A0F05 100%) !important;
            }
            [data-testid="stExpander"] {
                background: linear-gradient(180deg, #2A1810 0%, #231208 100%) !important;
            }
            [data-testid="stExpander"] summary {
                background: linear-gradient(90deg, #2A1810, #1C1008) !important;
                color: var(--gold) !important;
            }
            [data-testid="stMetric"] {
                background: linear-gradient(135deg, #2A1810 0%, #231208 100%) !important;
            }
            h1 {
                /* Slightly adjusted shimmer for dark mode readability */
                background: linear-gradient(
                    90deg,
                    #EF5350 0%,
                    var(--gold) 25%,
                    #FFD700 50%,
                    var(--mysore-purple) 65%,
                    var(--gold) 80%,
                    #EF5350 100%
                ) !important;
                background-size: 200% auto !important;
                -webkit-background-clip: text !important;
                -webkit-text-fill-color: transparent !important;
                background-clip: text !important;
                animation: palace-shimmer 5s linear infinite;
            }
            h2 { color: var(--gold) !important; }
            h3 { color: var(--saffron) !important; }
            [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
                background: linear-gradient(135deg, #2D1A00, #3D2500) !important;
                border-right-color: var(--saffron) !important;
            }
            [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
                background: linear-gradient(135deg, #1E1510, #2A1E14) !important;
                border-left-color: var(--temple-gold) !important;
            }
            .stTabs [data-baseweb="tab"] {
                background: linear-gradient(180deg, #2A1810 0%, #1C1008 100%) !important;
                border-color: var(--hoysala-dark) !important;
                color: #C4957A !important;
            }
            [data-testid="stSelectbox"] > div > div,
            [data-testid="stTextInput"] > div > div > input,
            [data-testid="stTextArea"] > div > div > textarea {
                background: #2A1810 !important;
                color: #F5E6D3 !important;
                border-color: var(--hoysala-dark) !important;
            }
            div.stSuccess { background: #0D2B0D !important; }
            div.stError   { background: #2B0808 !important; }
            div.stWarning { background: #2B1F00 !important; }
            div.stInfo    { background: #1A0A2B !important; }
            [data-testid="stCaptionContainer"] p, small {
                color: #4CAF50 !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# ============================================================================
# VOICE CHAT SUB-PAGE (Sarvam STT + Sarvam Chat + Sarvam TTS)
# ============================================================================

def render_voice_chat(lang_mode):
    """
    Voice Chat mode: user records audio → Sarvam STT → Sarvam chatbot → Sarvam TTS.
    Runs as a parallel feature alongside the existing text chat.
    """
    st.markdown("### 🎙️ Voice Conversation Practice")
    st.caption(
        "Speak in Kannada → AI transcribes, responds, and speaks back. "
        "Uses Sarvam AI for speech and conversation."
    )

    # --- Check API key availability ---
    if not config.SARVAM_API_KEY:
        st.error(
            "**Sarvam API key not found.** "
            "Add `SARVAM_API_KEY=your_key` to your `.env` file and restart the app."
        )
        return

    # --- Voice Chat Session State ---
    if "vc_active" not in st.session_state:
        st.session_state.vc_active = False
        st.session_state.vc_show_review = False
        st.session_state.vc_history = []       # chat API history
        st.session_state.vc_display = []       # UI display messages
        st.session_state.vc_errors = []        # Logged grammar errors
        st.session_state.vc_last_audio_id = None  # Dedup recordings
        st.session_state.vc_scenario = ""

    # --- STATE A: Setup (only when NOT active AND NOT in review) ---
    if not st.session_state.vc_active and not st.session_state.vc_show_review:
        st.write("#### Configure your voice partner")

        vc_col1, vc_col2 = st.columns(2)
        with vc_col1:
            vc_persona_options = list(config.CHARACTER_CARDS.keys()) + ["Custom Scenario 🌐"]
            vc_role_display = st.selectbox(
                "Persona", vc_persona_options, key="vc_role_sel"
            )
            vc_focus = st.selectbox(
                "Grammar Focus", config.GRAMMAR_GOALS, key="vc_focus_sel"
            )
        with vc_col2:
            vc_speaker = st.selectbox(
                "AI Voice (Sarvam TTS)",
                list(config.SARVAM_SPEAKERS.keys()),
                key="vc_speaker_sel",
            )
            vc_pace = st.slider(
                "Speech Pace", 0.5, 2.0, config.SARVAM_TTS_PACE,
                step=0.05, key="vc_pace_sl",
                help="Lower = slower (good for beginners). Default 0.85."
            )

        vc_is_custom = vc_role_display == "Custom Scenario 🌐"
        vc_role = "Custom Scenario" if vc_is_custom else vc_role_display

        if vc_is_custom:
            vc_scenario = st.text_area(
                "Describe your scenario",
                placeholder=(
                    "Describe who you're talking to and what the situation is — e.g., "
                    "'I am about to meet a trekking guide in Chikmagalur who will lead "
                    "me on a 2-day hike through the coffee estates.'"
                ),
                height=120,
                key="vc_scenario_input",
            )
        else:
            vc_scenario = st.text_area(
                "Real-world scenario (optional)",
                placeholder="Describe a real situation you'll face this week.",
                height=80,
                key="vc_scenario_input",
            )

        if st.button("Start Voice Chat", key="vc_start_btn"):
            st.session_state.vc_active = True
            st.session_state.vc_role = vc_role
            st.session_state.vc_focus = vc_focus
            st.session_state.vc_speaker = config.SARVAM_SPEAKERS[vc_speaker]
            st.session_state.vc_pace = vc_pace
            st.session_state.vc_scenario = vc_scenario

            # Bot speaks first — generate opening line
            with st.spinner("Your conversation partner is getting ready..."):
                init_prompt = "Please start the conversation in character. You speak first."
                # Force Script mode so the model returns Kannada script (needed for TTS)
                res = logic.generate_chat_turn_ai(
                    init_prompt, [], vc_focus, vc_role, "Kannada (Script)",
                    scenario=st.session_state.vc_scenario,
                )

                if "error" not in res:
                    # Save to chat history
                    st.session_state.vc_history.append({"role": "user", "content": init_prompt})
                    st.session_state.vc_history.append({"role": "assistant", "content": res.get("raw_text", res.get("bot_reply_kannada", ""))})

                    kannada_text = res.get("bot_reply_kannada", "")
                    english_text = res.get("bot_reply_english_translation", "")

                    # Generate TTS audio for the opening line
                    tts_result = logic.sarvam_text_to_speech(
                        kannada_text,
                        speaker=st.session_state.vc_speaker,
                        pace=st.session_state.vc_pace,
                    )

                    st.session_state.vc_display.append({
                        "role": "assistant",
                        "kannada": kannada_text,
                        "english": english_text,
                        "audio": tts_result.get("audio_bytes"),
                        "tts_error": tts_result.get("error"),
                    })
                else:
                    st.error(f"Chat error: {res['error']}")
                    st.session_state.vc_active = False

            st.rerun()

    # --- STATE B: Active Voice Chat ---
    elif st.session_state.vc_active:
        # End button
        col_end1, col_end2 = st.columns([4, 1])
        with col_end2:
            if st.button("End Chat & Review", key="vc_end_btn"):
                st.session_state.vc_active = False
                st.session_state.vc_show_review = True
                st.rerun()

        st.markdown("---")

        # Render conversation history
        for i, msg in enumerate(st.session_state.vc_display):
            with st.chat_message(msg["role"]):
                if msg["role"] == "user":
                    # Show transcribed text
                    st.write(msg.get("kannada", msg.get("content", "")))
                else:
                    # Bot: show Kannada text
                    display_text = logic.toggle_script(msg["kannada"], lang_mode)
                    st.write(display_text)

                    # Play TTS audio if available
                    if msg.get("audio"):
                        st.audio(msg["audio"], format="audio/wav")
                    elif msg.get("tts_error"):
                        st.caption(f"🔇 TTS: {msg['tts_error']}")

                    # Translation expander
                    with st.expander("Show Translation"):
                        st.write(msg.get("english", ""))

        # --- Audio Input Widget ---
        st.markdown("---")
        st.write("**Record your reply in Kannada:**")
        audio_data = st.audio_input(
            "🎙️ Click to record",
            key="vc_audio_input",
        )

        # Process new recording
        if audio_data is not None:
            # Read bytes and create a simple ID for dedup
            audio_bytes = audio_data.getvalue()
            audio_id = hash(audio_bytes)

            if audio_id != st.session_state.vc_last_audio_id:
                st.session_state.vc_last_audio_id = audio_id

                # Step 1: STT — transcribe the user's Kannada speech
                with st.spinner("Transcribing your speech (Sarvam STT)..."):
                    stt_result = logic.sarvam_speech_to_text(audio_bytes)

                if "error" in stt_result:
                    st.error(f"STT Error: {stt_result['error']}")
                else:
                    user_text = stt_result["transcript"]

                    # Show user message immediately
                    st.session_state.vc_display.append({
                        "role": "user",
                        "kannada": user_text,
                    })

                    # Step 2: Send transcribed text to Sarvam chatbot
                    with st.spinner("Thinking..."):
                        res = logic.generate_chat_turn_ai(
                            user_text,
                            st.session_state.vc_history,
                            st.session_state.vc_focus,
                            st.session_state.vc_role,
                            "Kannada (Script)",  # Always Script for TTS compatibility
                            scenario=st.session_state.vc_scenario,
                        )

                    if "error" not in res:
                        # Update chat history
                        st.session_state.vc_history.append({"role": "user", "content": user_text})
                        st.session_state.vc_history.append({"role": "assistant", "content": res.get("raw_text", res.get("bot_reply_kannada", ""))})

                        kannada_reply = res.get("bot_reply_kannada", "")
                        english_reply = res.get("bot_reply_english_translation", "")

                        # Log errors silently
                        errors = res.get("user_errors", [])
                        if errors:
                            st.session_state.vc_errors.extend(errors)

                        # Step 3: TTS — convert bot reply to speech
                        with st.spinner("Generating speech (Sarvam TTS)..."):
                            tts_result = logic.sarvam_text_to_speech(
                                kannada_reply,
                                speaker=st.session_state.vc_speaker,
                                pace=st.session_state.vc_pace,
                            )

                        st.session_state.vc_display.append({
                            "role": "assistant",
                            "kannada": kannada_reply,
                            "english": english_reply,
                            "audio": tts_result.get("audio_bytes"),
                            "tts_error": tts_result.get("error"),
                        })
                    else:
                        st.error(f"Chat error: {res['error']}")

                    st.rerun()

        # --- Error log preview (collapsible) ---
        if st.session_state.vc_errors:
            with st.expander(f"📝 Grammar errors so far ({len(st.session_state.vc_errors)})"):
                for i, err in enumerate(st.session_state.vc_errors):
                    corr = logic.toggle_script(err.get('correction', ''), lang_mode)
                    st.write(
                        f"**{i+1}.** _{err.get('original', '')}_ → **{corr}** — {err.get('reason', '')}"
                    )

    # --- STATE C: Post-Conversation Review ---
    elif st.session_state.vc_show_review:
        st.markdown("### 📝 Voice Chat — Post-Conversation Error Log")

        if not st.session_state.vc_errors:
            st.success("Great job! No grammatical errors were logged during this session.")
        else:
            st.warning(f"You made {len(st.session_state.vc_errors)} errors to review.")
            for i, err in enumerate(st.session_state.vc_errors):
                with st.expander(f"Error {i + 1}: {err.get('original', '')}"):
                    corr = logic.toggle_script(err.get('correction', ''), lang_mode)
                    st.write(f"**Correction:** {corr}")
                    st.write(f"**Reason:** {err.get('reason', '')}")

        st.markdown("---")
        if st.button("Start New Voice Conversation", key="vc_new_btn"):
            # Full reset of all voice chat state
            st.session_state.vc_active = False
            st.session_state.vc_show_review = False
            st.session_state.vc_history = []
            st.session_state.vc_display = []
            st.session_state.vc_errors = []
            st.session_state.vc_last_audio_id = None
            st.session_state.vc_scenario = ""
            st.rerun()


# ============================================================================
# STREAMLIT UI (main)
# ============================================================================

def main():
    st.set_page_config(page_title="Kannada Bhasheya Guru", page_icon="🪔", layout="wide")
    local_css()

    # 1. Load Context
    if "context" not in st.session_state:
        with st.spinner("Loading Knowledge Base..."):
            st.session_state.context = logic.load_knowledge_base()

    # --- SIDEBAR SETTINGS (Language Toggle) ---

    # 1. Create a placeholder at the TOP of the sidebar
    settings_header = st.sidebar.empty()

    # 2. Render the Radio Button to get the current language choice
    lang_mode = st.sidebar.radio("App Language / ಭಾಷೆ:",
                                 [
                                     "English",
                                     "Kannada (Roman - Natural)",
                                     "Kannada (Roman - Strict)",
                                     "Kannada (Script)"
                                 ])

    # 3. Now that we have 'lang_mode', write the translated text
    settings_header.header(logic.get_ui_text("HDR_SETTINGS", lang_mode))

    st.sidebar.markdown("---")

    # UPDATED: Translate "NAVIGATION" Header
    st.sidebar.header(logic.get_ui_text("HDR_NAV", lang_mode))

    nav_options = {
        "Home": "NAV_HOME",
        "Conversation Practice": "NAV_CHAT",
        "Send Email Lesson": "NAV_EMAIL",
        "Mastery Quiz": "NAV_QUIZ",
        "Writing Critique": "NAV_WRITE",
        "Reading Comprehension": "NAV_READ"
    }

    # UPDATED: Translate "Go to:" Label
    mode = st.sidebar.radio(
        logic.get_ui_text("LBL_GOTO", lang_mode),
        options=list(nav_options.keys()),
        format_func=lambda x: logic.get_ui_text(nav_options[x], lang_mode)
    )

    # --- MAIN APP TITLE (UPDATED) ---
    st.title(logic.get_ui_text("APP_TITLE", lang_mode))
    st.markdown("---")

    # --- MODE: HOME ---
    if mode == "Home":
        st.subheader(logic.get_ui_text("TITLE_HOME", lang_mode))
        st.markdown(logic.get_ui_text("WELCOME_MSG", lang_mode))

        file_count = len(glob.glob(os.path.join(config.KNOWLEDGE_DIR, '*.txt')))
        st.info(f"System Status: {file_count} grammar modules loaded.")

    # --- MODE: CONVERSATION PRACTICE (Text + Voice tabs) ---
    elif mode == "Conversation Practice":
        st.subheader(logic.get_ui_text("NAV_CHAT", lang_mode))

        # ── Tab selector: Text Chat vs Voice Chat ──
        tab_text, tab_voice = st.tabs(["💬 Text Chat", "🎙️ Voice Chat"])

        # ================================================================
        # TAB 1: TEXT CHAT (unchanged from original)
        # ================================================================
        with tab_text:
            # 1. Initialize State Variables
            if "chat_active" not in st.session_state:
                st.session_state.chat_active = False
                st.session_state.show_review = False
                st.session_state.chat_history = []
                st.session_state.chat_display = []
                st.session_state.user_errors = []
                st.session_state.chat_scenario = ""
                st.session_state.error_quiz_active = False
                st.session_state.error_quiz_questions = []
                st.session_state.error_quiz_index = 0
                st.session_state.error_quiz_score = 0
                st.session_state.error_quiz_history = []

            # 2. STATE A: Setup Phase
            if not st.session_state.chat_active and not st.session_state.show_review:
                st.write("### Configure your conversational partner")
                persona_options = list(config.CHARACTER_CARDS.keys()) + ["Custom Scenario 🌐"]
                selected_role_display = st.selectbox("Persona", persona_options)
                is_custom = selected_role_display == "Custom Scenario 🌐"
                selected_role = "Custom Scenario" if is_custom else selected_role_display

                selected_focus = st.selectbox("Grammar Focus", config.GRAMMAR_GOALS)

                if is_custom:
                    chat_scenario = st.text_area(
                        "Describe your scenario",
                        placeholder=(
                            "Describe who you're talking to and what the situation is — e.g., "
                            "'I am about to meet a trekking guide in Chikmagalur who will lead "
                            "me on a 2-day hike through the coffee estates. I want to practise "
                            "discussing the route, what gear to bring, and local wildlife.'"
                        ),
                        height=120,
                        key="chat_scenario_input",
                    )
                else:
                    chat_scenario = st.text_area(
                        "Real-world scenario (optional)",
                        placeholder=(
                            "Describe a real situation you'll face this week — e.g. "
                            "'I need to buy vegetables at the local market and haggle over the price.'"
                        ),
                        height=80,
                        key="chat_scenario_input",
                    )

                if st.button("Start Conversation"):
                    st.session_state.chat_active = True
                    st.session_state.chat_role = selected_role
                    st.session_state.chat_focus = selected_focus
                    st.session_state.chat_scenario = chat_scenario

                    # Trigger bot to speak first
                    with st.spinner("Connecting to Bengaluru..."):
                        init_prompt = "Please start the conversation in character. You speak first."
                        res = logic.generate_chat_turn_ai(
                            init_prompt, [], selected_focus, selected_role, lang_mode,
                            scenario=st.session_state.chat_scenario,
                        )

                        if "error" not in res:
                            st.session_state.chat_history.append({"role": "user", "content": init_prompt})
                            st.session_state.chat_history.append({"role": "assistant", "content": res.get("raw_text", res.get("bot_reply_kannada", ""))})
                            st.session_state.chat_display.append({
                                "role": "assistant",
                                "kannada": res.get("bot_reply_kannada", ""),
                                "english": res.get("bot_reply_english_translation", "")
                            })
                    st.rerun()

            # 3. STATE B: Active Chat Phase
            elif st.session_state.chat_active:
                col1, col2 = st.columns([4, 1])
                with col2:
                    if st.button("End Chat & Review"):
                        st.session_state.chat_active = False
                        st.session_state.show_review = True
                        st.rerun()

                st.markdown("---")

                # Render existing messages
                for msg in st.session_state.chat_display:
                    with st.chat_message(msg["role"]):
                        if msg["role"] == "user":
                            st.write(msg["content"])
                        else:
                            if "Script" in lang_mode:
                                display_text = logic.toggle_script(msg["kannada"], lang_mode)
                            else:
                                display_text = msg["kannada"]

                            st.write(display_text)
                            with st.expander("Show Translation"):
                                st.write(msg["english"])

                # Input field
                if prompt := st.chat_input("Type your reply in Kannada (Script or Roman)..."):
                    st.session_state.chat_display.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)

                    with st.spinner("Typing..."):
                        res = logic.generate_chat_turn_ai(
                            prompt,
                            st.session_state.chat_history,
                            st.session_state.chat_focus,
                            st.session_state.chat_role,
                            lang_mode,
                            scenario=st.session_state.chat_scenario,
                        )

                        if "error" not in res:
                            st.session_state.chat_history.append({"role": "user", "content": prompt})
                            st.session_state.chat_history.append({"role": "assistant", "content": res.get("raw_text", res.get("bot_reply_kannada", ""))})
                            st.session_state.chat_display.append({
                                "role": "assistant",
                                "kannada": res.get("bot_reply_kannada", ""),
                                "english": res.get("bot_reply_english_translation", "")
                            })
                            errors = res.get("user_errors", [])
                            if errors:
                                st.session_state.user_errors.extend(errors)
                            st.rerun()
                        else:
                            st.error(f"API Error: {res['error']}")

            # 4. STATE C: Review Phase
            elif st.session_state.show_review:
                st.markdown("### 📝 Post-Conversation Error Log")

                if not st.session_state.user_errors:
                    st.success("Great job! No grammatical errors were logged during this session.")
                else:
                    st.warning(f"You made {len(st.session_state.user_errors)} errors to review.")
                    for i, err in enumerate(st.session_state.user_errors):
                        with st.expander(f"Error {i + 1}: {err.get('original', '')}"):
                            corr = logic.toggle_script(err.get('correction', ''), lang_mode)
                            st.write(f"**Correction:** {corr}")
                            st.write(f"**Reason:** {err.get('reason', '')}")

                    st.markdown("---")
                    if not st.session_state.error_quiz_active:
                        if st.button("Practice These Errors 🎯"):
                            with st.spinner("Generating targeted practice questions..."):
                                qs = logic.generate_error_quiz(
                                    st.session_state.user_errors, st.session_state.context
                                )
                                st.session_state.error_quiz_questions = qs
                                st.session_state.error_quiz_index = 0
                                st.session_state.error_quiz_score = 0
                                st.session_state.error_quiz_history = []
                                st.session_state.error_quiz_active = True
                                st.rerun()
                    else:
                        total = len(st.session_state.error_quiz_questions)
                        st.markdown("### 🎯 Error Practice Mini-Quiz")

                        if st.session_state.error_quiz_history:
                            st.markdown("#### Previous Answers")
                            for i, item in enumerate(st.session_state.error_quiz_history):
                                with st.expander(f"Q{i + 1}: {item['question']}", expanded=False):
                                    st.write(f"**Your Answer:** {item['user_answer']}")
                                    feed = logic.toggle_script(item['feedback'], lang_mode)
                                    corr = logic.toggle_script(item['correct_translation'], lang_mode)
                                    if item['correct']:
                                        st.success(feed)
                                        st.info(f"Standard Kannada: {corr}")
                                    else:
                                        st.error(feed)
                                        st.write(f"**Correct:** {corr}")
                            st.markdown("---")

                        q_idx = st.session_state.error_quiz_index
                        if q_idx < total:
                            q_text = st.session_state.error_quiz_questions[q_idx]
                            st.progress(q_idx / total)
                            st.markdown(f"### Q{q_idx + 1}: {q_text}")

                            if len(st.session_state.error_quiz_history) == q_idx:
                                st.write(logic.get_ui_text("LBL_TRANS", lang_mode))
                                user_ans = st.text_input(
                                    "Answer", key=f"eq_input_{q_idx}",
                                    label_visibility="collapsed"
                                )
                                if st.button(logic.get_ui_text("BTN_SUBMIT", lang_mode), key="eq_submit"):
                                    with st.spinner("Grading..."):
                                        res = logic.grade_answer_ai(
                                            q_text, user_ans, st.session_state.context
                                        )
                                        history_item = {
                                            'question': q_text,
                                            'user_answer': user_ans,
                                            'correct': res['is_correct'],
                                            'feedback': res['feedback'],
                                            'correct_translation': res.get('correct_translation', '')
                                        }
                                        st.session_state.error_quiz_history.append(history_item)
                                        if res['is_correct']:
                                            st.session_state.error_quiz_score += 1
                                        st.rerun()
                            else:
                                last = st.session_state.error_quiz_history[-1]
                                feed_text = logic.toggle_script(last['feedback'], lang_mode)
                                corr_text = logic.toggle_script(last['correct_translation'], lang_mode)
                                if last['correct']:
                                    st.success(f"Correct! {feed_text}")
                                    st.info(f"Standard Kannada: {corr_text}")
                                else:
                                    st.error(f"Incorrect. {feed_text}")
                                    st.write(f"**Correct Answer:** {corr_text}")

                                is_last = (q_idx == total - 1)
                                btn_label = "See Results 🏁" if is_last else logic.get_ui_text("BTN_NEXT", lang_mode)
                                if st.button(btn_label, key="eq_next"):
                                    st.session_state.error_quiz_index += 1
                                    st.rerun()
                        else:
                            score = st.session_state.error_quiz_score
                            st.markdown(f"## Score: {score}/{total}")
                            if st.button("Back to Review"):
                                st.session_state.error_quiz_active = False
                                st.rerun()

                st.markdown("---")
                if st.button("Start New Conversation"):
                    st.session_state.chat_active = False
                    st.session_state.show_review = False
                    st.session_state.chat_history = []
                    st.session_state.chat_display = []
                    st.session_state.user_errors = []
                    st.session_state.chat_scenario = ""
                    st.session_state.error_quiz_active = False
                    st.session_state.error_quiz_questions = []
                    st.session_state.error_quiz_index = 0
                    st.session_state.error_quiz_score = 0
                    st.session_state.error_quiz_history = []
                    st.rerun()

        # ================================================================
        # TAB 2: VOICE CHAT (Sarvam STT/TTS + Sarvam Chat)
        # ================================================================
        with tab_voice:
            render_voice_chat(lang_mode)

    # --- MODE: SEND LESSON ---
    elif mode == "Send Email Lesson":
        st.subheader(logic.get_ui_text("TITLE_EMAIL", lang_mode))
        st.write(logic.get_ui_text("DESC_EMAIL", lang_mode))

        if st.button(logic.get_ui_text("BTN_SEND", lang_mode)):
            with st.spinner("Compiling lesson..."):
                result = logic.send_email_lesson(st.session_state.context)
                if "Error" in result:
                    st.error(result)
                else:
                    st.success(result)

    # --- MODE: MASTERY QUIZ ---
    elif mode == "Mastery Quiz":
        st.subheader(logic.get_ui_text("TITLE_QUIZ", lang_mode))

        if "quiz_questions" not in st.session_state:
            st.session_state.quiz_questions = []
            st.session_state.quiz_history = []
            st.session_state.current_q_index = 0
            st.session_state.quiz_score = 0

        # State 1: Setup
        if not st.session_state.quiz_questions:
            sheet, topics = logic.get_quiz_data(st.session_state.context)
            if topics:
                topic_names = [t['topic'] for t in topics]
                st.write(logic.get_ui_text("LBL_TOPIC", lang_mode))
                selected_topic = st.selectbox("Topic", topic_names, label_visibility="collapsed")

                if st.button(logic.get_ui_text("BTN_START_QUIZ", lang_mode)):
                    row = next(t['row'] for t in topics if t['topic'] == selected_topic)
                    with st.spinner("Generating 10 questions..."):
                        qs = logic.generate_quiz(selected_topic, st.session_state.context)
                        st.session_state.quiz_questions = qs
                        st.session_state.quiz_topic = selected_topic
                        st.session_state.quiz_sheet_row = row
                        st.session_state.quiz_score = 0
                        st.session_state.current_q_index = 0
                        st.session_state.quiz_history = []
                        st.rerun()
            else:
                st.warning("No 'Sent' topics available.")

        # State 2: Active Quiz
        else:
            total = len(st.session_state.quiz_questions)

            # History
            if st.session_state.quiz_history:
                st.markdown("### Previous Answers")
                for i, item in enumerate(st.session_state.quiz_history):
                    display_q = logic.toggle_script(item['question'], lang_mode)
                    with st.expander(f"Q{i + 1}: {display_q}", expanded=False):
                        st.write(f"**Your Answer:** {item['user_answer']}")

                        feed = logic.toggle_script(item['feedback'], lang_mode)
                        corr = logic.toggle_script(item['correct_translation'], lang_mode)

                        if item['correct']:
                            st.success(feed)
                            st.info(f"Standard Kannada: {corr}")
                        else:
                            st.error(feed)
                            st.write(f"**Correct:** {corr}")
                st.markdown("---")

            # Current Question
            if st.session_state.current_q_index < total:
                q_idx = st.session_state.current_q_index
                q_text = st.session_state.quiz_questions[q_idx]

                display_q = logic.toggle_script(q_text, lang_mode)

                st.progress(q_idx / total)
                st.markdown(f"### Q{q_idx + 1}: {display_q}")

                if len(st.session_state.quiz_history) == q_idx:
                    st.write(logic.get_ui_text("LBL_TRANS", lang_mode))
                    user_ans = st.text_input("Answer", key=f"input_{q_idx}", label_visibility="collapsed")

                    if st.button(logic.get_ui_text("BTN_SUBMIT", lang_mode)):
                        with st.spinner("Grading..."):
                            res = logic.grade_answer_ai(q_text, user_ans, st.session_state.context)

                            history_item = {
                                'question': q_text,
                                'user_answer': user_ans,
                                'correct': res['is_correct'],
                                'feedback': res['feedback'],
                                'correct_translation': res.get('correct_translation', '')
                            }
                            st.session_state.quiz_history.append(history_item)
                            if res['is_correct']: st.session_state.quiz_score += 1
                            st.rerun()
                else:
                    last_result = st.session_state.quiz_history[-1]
                    feed_text = logic.toggle_script(last_result['feedback'], lang_mode)
                    corr_text = logic.toggle_script(last_result['correct_translation'], lang_mode)

                    if last_result['correct']:
                        st.success(f"Correct! {feed_text}")
                        st.info(f"Standard Kannada: {corr_text}")
                    else:
                        st.error(f"Incorrect. {feed_text}")
                        st.write(f"**Correct Answer:** {corr_text}")

                    is_last_question = (st.session_state.current_q_index == total - 1)

                    if is_last_question:
                        btn_label = "See Results 🏁"
                    else:
                        btn_label = logic.get_ui_text("BTN_NEXT", lang_mode)

                    if st.button(btn_label):
                        st.session_state.current_q_index += 1
                        st.rerun()
            else:
                score = st.session_state.quiz_score
                st.markdown(f"## Score: {score}/{total}")
                if score >= (total * 0.9):
                    st.success("Topic Mastered! Sheet updated.")
                    logic.update_mastery(st.session_state.quiz_sheet_row)
                else:
                    st.warning("Not yet! Keep trying.")

                if st.button(logic.get_ui_text("BTN_BACK", lang_mode)):
                    st.session_state.quiz_questions = []
                    st.rerun()

    # --- MODE: WRITING CRITIQUE ---
    elif mode == "Writing Critique":
        st.subheader(logic.get_ui_text("TITLE_WRITE", lang_mode))

        col1, col2 = st.columns(2)
        with col1:
            st.write(logic.get_ui_text("LBL_STYLE", lang_mode))
            style = st.selectbox(
                "Style",
                ["Formal", "Colloquial"],
                label_visibility="collapsed",
                format_func=lambda x: logic.get_ui_text(f"OPT_{x}", lang_mode)
            )
        with col2:
            st.write(logic.get_ui_text("LBL_INPUT", lang_mode))
            method = st.radio(
                "Input",
                ["Paste Text", "Get Prompt"],
                label_visibility="collapsed",
                format_func=lambda x: logic.get_ui_text(f"OPT_{x}", lang_mode)
            )

        if method == "Get Prompt":
            st.write(logic.get_ui_text("LBL_TOPIC", lang_mode))
            topic = st.selectbox("Topic", config.WRITING_TOPICS, label_visibility="collapsed")
            if st.button(logic.get_ui_text("BTN_GEN_PROMPT", lang_mode)):
                with st.spinner("Generating..."):
                    prompt_res = logic.generate_content(f"Create a 1-sentence writing prompt regarding {topic}",
                                                        st.session_state.context)
                    st.info(logic.toggle_script(prompt_res, lang_mode))

        st.write(logic.get_ui_text("LBL_PASTE", lang_mode))
        user_text = st.text_area("User Text", height=150, label_visibility="collapsed")

        if st.button(logic.get_ui_text("BTN_ANALYZE", lang_mode)):
            if len(user_text) < 5:
                st.error("Text is too short.")
            else:
                with st.spinner("Analyzing..."):
                    res = logic.critique_text_ai(user_text, style, st.session_state.context)
                    if "overall_summary" in res:
                        st.info(logic.toggle_script(res.get('overall_summary'), lang_mode))
                        for item in res.get('analysis', []):
                            orig = logic.toggle_script(item.get('original', ''), lang_mode)
                            with st.expander(f"{orig[:40]}..."):
                                if item.get('status') != 'CORRECT':
                                    corr = logic.toggle_script(item.get('corrected'), lang_mode)
                                    feed = logic.toggle_script(item.get('feedback'), lang_mode)
                                    st.write(f"**Correction:** {corr}")
                                    st.write(f"**Feedback:** {feed}")
                                else:
                                    st.caption("Correct")

    # --- MODE: READING COMPREHENSION ---
    elif mode == "Reading Comprehension":
        st.subheader(logic.get_ui_text("TITLE_READ", lang_mode))

        st.write(logic.get_ui_text("LBL_INPUT", lang_mode))
        input_method = st.radio(
            "Method",
            ("Paste Kannada Text", "Generate (AI)"),
            label_visibility="collapsed",
            format_func=lambda x: logic.get_ui_text(f"OPT_{x}", lang_mode)
        )

        if input_method == "Paste Kannada Text":
            st.write(logic.get_ui_text("LBL_PASTE", lang_mode))
            user_text = st.text_area("Paste", height=200, label_visibility="collapsed")
            if st.button(logic.get_ui_text("BTN_LOAD", lang_mode)):
                if len(user_text) > 5:
                    st.session_state['current_article'] = user_text
                    st.session_state.pop('qa_content', None)
                    st.success("Loaded.")
                else:
                    st.warning("Please paste some text first.")

        elif input_method == "Generate (AI)":
            col1, col2 = st.columns(2)
            with col1:
                st.write(logic.get_ui_text("LBL_TOPIC", lang_mode))
                topic = st.selectbox("Topic", config.WRITING_TOPICS, key="rc_topic", label_visibility="collapsed")
            with col2:
                st.write(logic.get_ui_text("LBL_STYLE", lang_mode))
                style = st.selectbox(
                    "Style",
                    ["Formal", "Colloquial"],
                    key="rc_style",
                    label_visibility="collapsed",
                    format_func=lambda x: logic.get_ui_text(f"OPT_{x}", lang_mode)
                )

            if st.button(logic.get_ui_text("BTN_GEN_TEXT", lang_mode)):
                with st.spinner("Generating..."):
                    generated_text = logic.generate_kannada_article_ai(topic, style, st.session_state.context)
                    st.session_state['current_article'] = generated_text
                    st.session_state.pop('qa_content', None)
                    st.success("Generated.")

        if 'current_article' in st.session_state and st.session_state['current_article']:
            st.markdown("### Article")
            st.info(logic.toggle_script(st.session_state['current_article'], lang_mode))
            st.markdown("---")

            if st.button(logic.get_ui_text("BTN_GEN_QS", lang_mode)):
                with st.spinner("Creating questions..."):
                    qa_response = logic.generate_comprehension_questions(st.session_state['current_article'],
                                                                         st.session_state.context)
                    st.session_state['qa_content'] = qa_response

            if 'qa_content' in st.session_state and isinstance(st.session_state['qa_content'], list):
                if len(st.session_state['qa_content']) == 0:
                    st.error("Rate limit hit or no questions generated.")
                else:
                    st.markdown("### Questions")
                    for i, item in enumerate(st.session_state['qa_content']):
                        q_text = logic.toggle_script(item.get('question'), lang_mode)
                        st.markdown(f"**Q{i + 1}: {q_text}**")

                        user_ans = st.text_input(f"Answer {i + 1}", key=f"rc_answer_{i}", label_visibility="collapsed")

                        if st.button(logic.get_ui_text("BTN_CHECK", lang_mode) + f" {i + 1}", key=f"btn_check_{i}"):
                            if not user_ans:
                                st.warning("Write an answer first.")
                            else:
                                with st.spinner("Grading..."):
                                    res = logic.grade_reading_ai(item.get('question'),
                                                                 st.session_state['current_article'], user_ans,
                                                                 st.session_state.context)

                                    feed = logic.toggle_script(res['feedback'], lang_mode)
                                    expl = logic.toggle_script(res['detailed_explanation'], lang_mode)

                                    if res['is_correct']:
                                        st.success(f"Correct. {feed}")
                                    else:
                                        st.error(f"Incorrect. {feed}")

                                    with st.expander("Explanation"):
                                        st.write(expl)
                        st.markdown("---")


if __name__ == "__main__":
    main()