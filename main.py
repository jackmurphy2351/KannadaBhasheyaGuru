import streamlit as st
import streamlit.components.v1 as components
import os
import glob
import random
import json

# Import our custom modules
import auth
import config
import learner
import logic
import storage


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
                caret-color: #F5E6D3 !important;
                border-color: var(--hoysala-dark) !important;
            }
            /* The light-mode :focus rule has higher specificity and would
               flip the background back to near-white under cream text —
               keep the writing surface dark while typing. */
            [data-testid="stTextInput"] > div > div > input:focus,
            [data-testid="stTextArea"] > div > div > textarea:focus {
                background: #321D12 !important;
                color: #F5E6D3 !important;
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

def render_voice_chat(lang_mode, profile):
    """
    Voice Chat mode: user records audio → Sarvam STT → Sarvam chatbot → Sarvam TTS.
    Runs as a parallel feature alongside the existing text chat.

    ``lang_mode`` is the learner's content script: the model and TTS always
    work in Kannada script, and only what is *displayed* is transliterated.
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
        st.caption("Your partner always speaks Kannada; the transcript is shown "
                   "in your script (set under Settings → Learning profile).")

        vc_mode = st.radio(
            "Session mode",
            ["Choose a Persona", "Custom Scenario 🌐"],
            horizontal=True,
            key="vc_mode_sel",
        )
        vc_is_custom = vc_mode == "Custom Scenario 🌐"
        vc_role = "Custom Scenario" if vc_is_custom else None

        vc_col1, vc_col2 = st.columns(2)
        with vc_col1:
            if not vc_is_custom:
                vc_role = st.selectbox(
                    "Persona",
                    learner.order_personas(profile, config.CHARACTER_CARDS),
                    key="vc_role_sel",
                    format_func=lambda n: persona_label(profile, n),
                )
            vc_focus = st.selectbox(
                "Grammar Focus", grammar_goals_for(profile), key="vc_focus_sel"
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

        if vc_is_custom:
            st.info(
                "**Write a character card for your conversation partner, starting with "
                "\"You are...\"** — just like the predefined personas.  \n"
                "Include their role, personality, background, and any quirks. "
                "The more detail you provide, the more authentic the conversation. "
                "*(Max 1500 characters)*"
            )
            vc_scenario = st.text_area(
                "Describe your conversation partner",
                placeholder=(
                    "You are a trekking guide in your thirties based in Chikmagalur. You are "
                    "deeply knowledgeable about the local coffee estates, wildlife, and trails, "
                    "and you speak enthusiastically about the region's history. You are practical "
                    "and direct about gear requirements and safety, but warm and encouraging with "
                    "first-time visitors."
                ),
                height=150,
                max_chars=1500,
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
            # Fixed for the whole conversation, like the text chat.
            st.session_state.vc_learner_block = learner.prompt_block(profile)

            # Bot speaks first — generate opening line
            with st.spinner("Your conversation partner is getting ready..."):
                init_prompt = "Please start the conversation in character. You speak first."
                # Force Script mode so the model returns Kannada script (needed for TTS)
                res = logic.generate_chat_turn_ai(
                    init_prompt, [], vc_focus, vc_role, "Kannada (Script)",
                    scenario=st.session_state.vc_scenario,
                    learner_block=st.session_state.vc_learner_block,
                )

                if "error" not in res:
                    # Save to chat history
                    st.session_state.vc_history.append({"role": "user", "content": init_prompt})
                    st.session_state.vc_history.append({"role": "assistant", "content": res.get("bot_reply_kannada", "")})

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
                    st.write(logic.toggle_script(
                        msg.get("kannada", msg.get("content", "")), lang_mode))
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
                            learner_block=st.session_state.get("vc_learner_block"),
                        )

                    if "error" not in res:
                        # Update chat history
                        st.session_state.vc_history.append({"role": "user", "content": user_text})
                        st.session_state.vc_history.append({"role": "assistant", "content": res.get("bot_reply_kannada", "")})

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
            vc_err_count = len(st.session_state.vc_errors)
            st.warning(f"You made {vc_err_count} {'error' if vc_err_count == 1 else 'errors'} to review.")
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

# ---------------------------------------------------------------------------
# Shared quiz runner
#
# The Mastery Quiz and the Daily Review present questions identically — same
# grading path, same feedback tiers, same history list — and differ only in
# where the questions come from and what happens at the end. They therefore
# share one renderer. The earlier copy-paste between two quiz UIs is how the
# same "question shown twice" bug had to be fixed twice.
#
# Session state is namespaced by `prefix`, so the two can be part-way through
# independently: <prefix>_questions / _history / _index / _score / _context.
# ---------------------------------------------------------------------------

def quiz_key(prefix, field):
    """Session-state key for one field of a quiz session."""
    return f"{prefix}_{field}"


def init_quiz_state(prefix):
    """Create this quiz session's state keys once."""
    defaults = {"questions": [], "history": [], "index": 0, "score": 0,
                "context": "", "topic": None, "recorded": False}
    for field, default in defaults.items():
        st.session_state.setdefault(quiz_key(prefix, field), default)


def start_quiz(prefix, questions, topic, context):
    """Begin a new run, clearing any previous one."""
    st.session_state[quiz_key(prefix, "questions")] = questions
    st.session_state[quiz_key(prefix, "topic")] = topic
    st.session_state[quiz_key(prefix, "context")] = context
    st.session_state[quiz_key(prefix, "history")] = []
    st.session_state[quiz_key(prefix, "index")] = 0
    st.session_state[quiz_key(prefix, "score")] = 0
    st.session_state[quiz_key(prefix, "recorded")] = False


def end_quiz(prefix):
    """Return to the setup screen for this quiz."""
    st.session_state[quiz_key(prefix, "questions")] = []


def render_quiz_result(entry, lang_mode, show_answer=True, content_mode=None):
    """Render one graded answer.

    The correct answer shown always comes from the bank item, so LLM feedback
    can never override it. The learner's own answer is shown beside it: without
    it there is nothing to compare the correction against, since the input box
    is gone by the time the verdict appears.
    """
    content_mode = content_mode or lang_mode
    if show_answer:
        st.write(f"**Your answer:** {entry['user_answer']}")
    canonical = logic.toggle_script(entry['item']['canonical'], content_mode)
    if entry['tier'] == "exact":
        st.success("Correct! ✅")
        st.info(f"Standard Kannada: {canonical}")
    elif entry['tier'] == "variant":
        st.success("Correct! ✅ Your variant is also valid.")
        st.info(f"Standard / literary form for reference: {canonical}")
    elif entry['tier'] == "accepted":
        st.success("Correct! ✅ Your phrasing works too.")
        st.info(f"Reference answer for comparison: {canonical}")
    else:
        st.error("Incorrect.")
        st.write(f"**Correct Answer:** {canonical}")
        st.write(logic.toggle_script(entry['feedback'], content_mode))


def render_quiz_runner(prefix, lang_mode, show_topic=False, *, content_mode=None,
                       record=True, judge=True, learner_block=None):
    """Render the current question or its feedback.

    Returns True once every question has been answered and advanced past, at
    which point the caller renders its own results screen.

    ``lang_mode`` is for UI chrome; ``content_mode`` is the script Kannada
    answers are shown in. The placement check passes ``record=False`` (it must
    not seed the SRS deck with items the learner never studied) and
    ``judge=False`` (bank matches only: free, reproducible, and biased low,
    which is the safe direction for a level suggestion).
    """
    questions = st.session_state[quiz_key(prefix, "questions")]
    total = len(questions)
    history = st.session_state[quiz_key(prefix, "history")]
    q_idx = st.session_state[quiz_key(prefix, "index")]

    # History — only questions BEFORE the current one; the current question's
    # result renders once below (it used to appear twice).
    prev_entries = history[:q_idx]
    if prev_entries:
        st.markdown("### Previous Answers")
        for i, entry in enumerate(prev_entries):
            with st.expander(f"Q{i + 1}: {entry['item']['english']}", expanded=False):
                render_quiz_result(entry, lang_mode, content_mode=content_mode)
        st.markdown("---")

    if q_idx >= total:
        return True

    item = questions[q_idx]
    st.progress(q_idx / total)
    if show_topic:
        st.caption(item["topic"])
    st.markdown(f"### Q{q_idx + 1}: {item['english']}")

    if len(history) == q_idx:
        st.write(logic.get_ui_text("LBL_TRANS", lang_mode))
        user_ans = st.text_input("Answer", key=f"{prefix}_input_{q_idx}",
                                 label_visibility="collapsed")

        if st.button(logic.get_ui_text("BTN_SUBMIT", lang_mode),
                     key=f"{prefix}_submit_{q_idx}"):
            # Deterministic match against the bank's acceptable forms decides
            # the fast path; a non-match gets one constrained LLM equivalence
            # check (Kannada has many valid surface forms) before being marked
            # wrong.
            tier = logic.classify_answer(user_ans, item)
            feedback = ""
            if tier == "incorrect":
                quiz_ctx = st.session_state[quiz_key(prefix, "context")] or \
                    st.session_state.context
                known = logic.match_common_error(user_ans, item)
            else:
                known = None

            if known:
                # A near-miss the bank already knows about. It is graded wrong
                # every time and explained from stored text, so the verdict
                # never depends on the model agreeing with itself twice.
                feedback = logic.explain_common_error(known, item)
            elif tier == "incorrect" and judge:
                with st.spinner("Checking your phrasing..."):
                    verdict = logic.judge_equivalence(user_ans, item, quiz_ctx)
                if verdict is None:
                    # The API was unreachable, so there is no verdict. Grading
                    # the answer wrong here would punish a network blip, and
                    # scheduling it as a lapse would corrupt the SRS interval
                    # for an item the learner may well know. Keep the question
                    # open and let them submit again.
                    st.error(
                        "Couldn't reach the grading service, so this answer "
                        "wasn't checked. Your answer is still below — press "
                        "Submit again when you're back online.")
                    st.stop()
                if verdict:
                    tier = "accepted"
                if tier == "incorrect":
                    with st.spinner("Preparing explanation..."):
                        feedback = logic.explain_mistake(
                            user_ans, item, quiz_ctx,
                            learner_block=learner_block,
                        )["feedback"]

            history.append({
                'item': item,
                'user_answer': user_ans,
                'tier': tier,
                'feedback': feedback,
            })
            if tier != "incorrect":
                st.session_state[quiz_key(prefix, "score")] += 1
            # Persist and reschedule. Runs here, once per question, because
            # this branch ends in a rerun; putting it in the render path would
            # re-grade the same answer on every rerun.
            if record:
                logic.record_quiz_answer(item, tier, profile_id=current_profile())
            st.rerun()
    else:
        render_quiz_result(history[-1], lang_mode, content_mode=content_mode)
        is_last = (q_idx == total - 1)
        label = "See Results 🏁" if is_last else logic.get_ui_text("BTN_NEXT", lang_mode)
        if st.button(label, key=f"{prefix}_next_{q_idx}"):
            st.session_state[quiz_key(prefix, "index")] += 1
            st.rerun()
    return False


def render_progress_panel(lang_mode):
    """Durable per-topic history: attempts, best score, and what is due."""
    stats = storage.get_topic_stats(profile_id=current_profile())
    due = storage.get_due_counts_by_topic(profile_id=current_profile())
    if not stats and not due:
        return
    with st.expander(f"📊 {logic.get_ui_text('LBL_YOUR_PROGRESS', lang_mode)}",
                     expanded=False):
        for topic in sorted(set(stats) | set(due)):
            row = stats.get(topic)
            bits = []
            if row:
                bits.append(f"{row['attempts']} attempt"
                            f"{'s' if row['attempts'] != 1 else ''}")
                bits.append(f"best {row['best']}/{row['total']}")
                bits.append(f"last {row['last_attempt'][:10]}")
            if due.get(topic):
                bits.append(f"**{due[topic]} due**")
            st.markdown(f"- **{topic}** — {' · '.join(bits)}")


# ---------------------------------------------------------------------------
# Learning tracks
#
# The onboarding answers live in storage (keyed by profile_id) and are cached
# in st.session_state.learner. learner.py turns them into prompt text and
# display choices; nothing here writes prompt text of its own.
# ---------------------------------------------------------------------------

def load_learner():
    """The signed-in learner's LearnerProfile, or None before onboarding."""
    if st.session_state.get("learner") is None:
        st.session_state.learner = learner.LearnerProfile.from_row(
            storage.get_learner_profile(profile_id=current_profile()))
    return st.session_state.learner


def save_learner(level, motivation, reads_script):
    learner.validate(level, motivation, reads_script)
    storage.set_learner_profile(level, motivation, reads_script,
                                profile_id=current_profile())
    st.session_state.learner = None     # re-read, so the cache matches the DB
    return load_learner()


def persona_label(profile, name):
    return f"★ {name}" if name in learner.recommended_personas(profile) else name


def grammar_goals_for(profile):
    return [config.GRAMMAR_GOAL_TEXT[k]
            for k in learner.grammar_goal_keys(profile)]


def render_learner_form(lang_mode, form_key, current=None):
    """The three onboarding questions. Returns True once saved.

    With no ``current`` profile nothing is preselected, so a new learner has to
    actually choose rather than drift through on the defaults.
    """
    levels = list(learner.LEVELS)
    motivations = list(learner.MOTIVATIONS)
    with st.form(form_key):
        level = st.radio(
            logic.get_ui_text("LBL_Q_LEVEL", lang_mode), levels,
            index=levels.index(current.level) if current else None,
            format_func=lambda k: (f"**{learner.LEVELS[k]['label']}** — "
                                   f"{learner.LEVELS[k]['description']}"),
            captions=[f"≈ CEFR {learner.LEVELS[k]['cefr']}" for k in levels],
        )
        motivation = st.radio(
            logic.get_ui_text("LBL_Q_MOTIVATION", lang_mode), motivations,
            index=motivations.index(current.motivation) if current else None,
            format_func=lambda k: learner.MOTIVATIONS[k]["label"],
        )
        reads_script = st.radio(
            logic.get_ui_text("LBL_Q_SCRIPT", lang_mode), [True, False],
            index=(0 if current.reads_script else 1) if current else None,
            format_func=lambda b: "Yes" if b else "No",
            horizontal=True,
        )
        if current:
            st.caption(logic.get_ui_text("CAP_PROFILE_APPLIES", lang_mode))
        submitted = st.form_submit_button(
            logic.get_ui_text("BTN_SAVE_PROFILE", lang_mode))
    if not submitted:
        return False
    if level is None or motivation is None or reads_script is None:
        st.error("Please answer all three questions.")
        return False
    save_learner(level, motivation, reads_script)
    return True


def render_onboarding(lang_mode):
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title(logic.get_ui_text("TITLE_ONBOARDING", lang_mode))
        st.write(logic.get_ui_text("DESC_ONBOARDING", lang_mode))
        if render_learner_form(lang_mode, "onboarding"):
            st.session_state.placement_stage = "offer"
            st.rerun()


def render_learning_profile_sidebar(profile, lang_mode):
    with st.sidebar.expander(
            logic.get_ui_text("HDR_LEARNING_PROFILE", lang_mode)):
        if render_learner_form(lang_mode, "settings_profile", current=profile):
            st.session_state["_profile_saved"] = True
            st.rerun()
        if st.session_state.pop("_profile_saved", False):
            st.success(logic.get_ui_text("MSG_PROFILE_SAVED", lang_mode))
        if st.button(logic.get_ui_text("BTN_PLACEMENT", lang_mode),
                     key="settings_placement"):
            _start_placement()
            st.rerun()


# --- Placement check ---
# Session keys: placement_stage ("offer" | "quiz" | "script" | "result"),
# placement_band (index into learner.LEVEL_ORDER), placement_passed (bands
# passed so far), placement_script_ok. The quiz itself runs through the shared
# render_quiz_runner under the "placement" prefix.

def _start_placement_band(band_idx):
    # Each band restarts at question 0, so its input keys repeat; never let a
    # previous band's typed answer prefill the next band's box.
    for key in [k for k in st.session_state.keys()
                if k.startswith("placement_input_")]:
        del st.session_state[key]
    init_quiz_state("placement")
    start_quiz("placement",
               logic.build_placement_band(learner.LEVEL_ORDER[band_idx],
                                          n=learner.PLACEMENT_PER_BAND),
               None, "")
    st.session_state.placement_band = band_idx


def _start_placement():
    st.session_state.placement_stage = "quiz"
    st.session_state.placement_passed = 0
    _start_placement_band(0)


def _end_placement():
    for key in [k for k in st.session_state.keys()
                if k.startswith("placement_")]:
        del st.session_state[key]


def render_placement(profile, lang_mode):
    stage = st.session_state.placement_stage
    st.title(logic.get_ui_text("TITLE_PLACEMENT", lang_mode))

    if stage == "offer":
        st.success(logic.get_ui_text("MSG_PROFILE_SAVED", lang_mode))
        col_a, col_b = st.columns(2)
        if col_a.button(logic.get_ui_text("BTN_PLACEMENT", lang_mode)):
            _start_placement()
            st.rerun()
        if col_b.button(logic.get_ui_text("BTN_SKIP_PLACEMENT", lang_mode)):
            _end_placement()
            st.rerun()
        return

    if stage != "result" and st.button(
            logic.get_ui_text("BTN_CANCEL_PLACEMENT", lang_mode)):
        _end_placement()
        st.rerun()

    if stage == "quiz":
        st.write(logic.get_ui_text("DESC_PLACEMENT", lang_mode))
        band = st.session_state.placement_band
        st.caption(f"Part {band + 1} of {len(learner.LEVEL_ORDER)}")
        if render_quiz_runner("placement", lang_mode,
                              content_mode=learner.content_script(profile),
                              record=False, judge=False):
            if learner.band_passed(st.session_state.placement_score):
                st.session_state.placement_passed += 1
                if band + 1 < len(learner.LEVEL_ORDER):
                    _start_placement_band(band + 1)
                    st.rerun()
            st.session_state.placement_stage = "script"
            st.rerun()

    elif stage == "script":
        with st.form("script_check"):
            answers = []
            for i, item in enumerate(learner.SCRIPT_CHECK):
                st.markdown(f"### {item['word']}")
                answers.append(st.radio(
                    logic.get_ui_text("LBL_SCRIPT_CHECK", lang_mode),
                    item["choices"], index=None, key=f"placement_sc_{i}",
                    horizontal=True))
            if st.form_submit_button(logic.get_ui_text("BTN_SUBMIT", lang_mode)):
                st.session_state.placement_script_ok = \
                    learner.script_check_passed(answers)
                st.session_state.placement_stage = "result"
                st.rerun()

    elif stage == "result":
        level = learner.placement_level(st.session_state.placement_passed)
        reads = st.session_state.placement_script_ok
        info = learner.LEVELS[level]
        st.subheader(f"{logic.get_ui_text('LBL_PLACEMENT_SUGGESTS', lang_mode)}: "
                     f"{info['label']} (≈ CEFR {info['cefr']})")
        st.write(info["description"])
        st.write("Kannada script: " + ("you can read it." if reads
                 else "we'll show Kannada in Roman letters."))
        yours = learner.LEVELS[profile.level]["label"]
        st.caption(f"Your current answers: {yours}, "
                   f"{'reads' if profile.reads_script else 'does not read'} "
                   f"Kannada script.")
        col_a, col_b = st.columns(2)
        if col_a.button(logic.get_ui_text("BTN_USE_SUGGESTION", lang_mode)):
            save_learner(level, profile.motivation, reads)
            _end_placement()
            st.rerun()
        if col_b.button(logic.get_ui_text("BTN_KEEP_MINE", lang_mode)):
            _end_placement()
            st.rerun()


# ---------------------------------------------------------------------------
# Accounts
#
# Streamlit drops st.session_state on every browser refresh, so "remember me"
# is a random token in a cookie (only its hash is in the database; see
# auth.py). The cookie is read server-side from st.context.cookies, which is
# captured when the session starts; it is written from the browser by a
# zero-height component, because Streamlit has no server-side Set-Cookie.
#
# Revocation in the database is what actually logs a token out. Clearing the
# cookie is tidiness: a revoked token that is still in the browser (or still in
# this session's st.context.cookies snapshot) simply fails to resume.
# ---------------------------------------------------------------------------

SESSION_COOKIE = "vani_session"


def current_profile():
    """The signed-in learner's profile_id. Only valid after require_login()."""
    return st.session_state.user["profile_id"]


def _queue_cookie(token):
    """Write (token) or expire (None) the session cookie on the next render.

    Deferred to the next run because every caller then calls st.rerun(),
    which would discard a component emitted in this run before it executes.
    """
    st.session_state["_pending_cookie"] = token or ""


def _flush_cookie():
    if "_pending_cookie" not in st.session_state:
        return
    token = st.session_state.pop("_pending_cookie")
    max_age = auth.SESSION_DAYS * 86400 if token else 0
    # Secure only over https: some browsers refuse Secure cookies on
    # http://localhost, which would silently break remember-me in local dev.
    components.html(
        "<script>"
        "const d = window.parent.document;"
        "const secure = window.parent.location.protocol === 'https:' ? '; Secure' : '';"
        f"d.cookie = '{SESSION_COOKIE}={token}; Path=/; Max-Age={max_age}; "
        "SameSite=Strict' + secure;"
        "</script>",
        height=0,
    )


def _sign_in(user, remember):
    st.session_state.user = user
    if remember:
        token = auth.issue_session(user["profile_id"])
        st.session_state["_session_token"] = token
        _queue_cookie(token)
        storage.purge_expired_sessions()


def sign_out():
    """Revoke this device's session and drop every per-user bit of state, so
    the next person on this browser never inherits a half-finished quiz."""
    auth.revoke_session(st.session_state.get("_session_token")
                        or st.context.cookies.get(SESSION_COOKIE))
    for key in list(st.session_state.keys()):
        if key != "context":            # the knowledge base is not per-user
            del st.session_state[key]
    _queue_cookie(None)


def _handle_email_confirmation():
    """Redeem a ``?confirm=<token>`` link and sign the person straight in.

    Runs unconditionally, before the session-state/cookie checks in
    require_login(): a confirmation click is a fresh, cookie-less visit, not
    a resumed session. Clearing the query param immediately means a page
    refresh right after confirming can never replay the (already single-use,
    now-deleted) token.
    """
    token = st.query_params.get("confirm")
    if not token:
        return
    st.query_params.clear()
    user = auth.confirm_signup(token)
    if user is None:
        st.session_state["_confirm_error"] = True
        return
    _sign_in(user, remember=True)
    st.session_state["_just_confirmed"] = True
    st.rerun()


def _render_signup_tab(lang_mode):
    email = st.text_input(logic.get_ui_text("LBL_EMAIL", lang_mode))
    pw1 = st.text_input(logic.get_ui_text("LBL_PASSWORD", lang_mode),
                        type="password", key="signup_pw1")
    pw2 = st.text_input(logic.get_ui_text("LBL_CONFIRM_PASSWORD", lang_mode),
                        type="password", key="signup_pw2")
    submitted = st.form_submit_button(
        logic.get_ui_text("BTN_CREATE_ACCOUNT", lang_mode))
    if not submitted:
        return
    if pw1 != pw2:
        st.error(logic.get_ui_text("ERR_PASSWORD_MISMATCH", lang_mode))
        return
    try:
        kind, token, profile_id = auth.start_signup(email, pw1)
    except ValueError as e:
        st.error(str(e))
        return
    # Both branches below are wrapped in one broad try/except and always end
    # in the same success message — an SMTP hiccup, and whether the email was
    # already registered, must never change what the submitter sees.
    try:
        if kind == "new":
            logic.send_signup_confirmation_email(email, token)
        else:
            existing = storage.get_user(profile_id)
            logic.send_duplicate_signup_notice_email(existing["username"])
    except Exception as e:  # pragma: no cover - defensive
        print(f"[signup] failed to send email for {kind}: {e}")
    storage.purge_expired_email_confirmations()
    st.success(logic.get_ui_text("MSG_SIGNUP_CHECK_EMAIL", lang_mode))


def require_login(lang_mode):
    """Return the signed-in user, or render the sign-in/signup UI and stop."""
    _flush_cookie()
    _handle_email_confirmation()
    if "user" in st.session_state:
        return st.session_state.user

    token = st.context.cookies.get(SESSION_COOKIE)
    user = auth.resume_session(token)
    if user is not None:
        st.session_state.user = user
        st.session_state["_session_token"] = token
        return user

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title(logic.get_ui_text("APP_TITLE", lang_mode))
        if st.session_state.pop("_confirm_error", False):
            st.error(logic.get_ui_text("ERR_CONFIRM_LINK_INVALID", lang_mode))
        tab_signin, tab_signup = st.tabs([
            logic.get_ui_text("TAB_SIGNIN", lang_mode),
            logic.get_ui_text("TAB_SIGNUP", lang_mode)])

        with tab_signin:
            with st.form("login"):
                username = st.text_input(
                    logic.get_ui_text("LBL_USERNAME", lang_mode))
                password = st.text_input(
                    logic.get_ui_text("LBL_PASSWORD", lang_mode),
                    type="password")
                remember = st.checkbox(
                    logic.get_ui_text("LBL_REMEMBER_ME", lang_mode), value=True)
                submitted = st.form_submit_button(
                    logic.get_ui_text("BTN_LOGIN", lang_mode))
            if submitted:
                try:
                    user = auth.authenticate(username, password)
                except auth.LockedOut:
                    st.error(logic.get_ui_text("ERR_LOCKED", lang_mode))
                except auth.PendingConfirmation:
                    st.error(logic.get_ui_text("ERR_PENDING_CONFIRMATION",
                                               lang_mode))
                else:
                    if user is None:
                        # One message for every failure, so the form can't be
                        # used to discover which usernames exist.
                        st.error(logic.get_ui_text("ERR_LOGIN", lang_mode))
                    else:
                        _sign_in(user, remember)
                        st.rerun()

        with tab_signup:
            with st.form("signup"):
                _render_signup_tab(lang_mode)
    st.stop()


def render_account_sidebar(user, lang_mode):
    st.sidebar.markdown(
        f"{logic.get_ui_text('LBL_SIGNED_IN_AS', lang_mode)} "
        f"**{user['username']}**")
    with st.sidebar.expander(logic.get_ui_text("HDR_ACCOUNT", lang_mode)):
        with st.form("change_password", clear_on_submit=True):
            current = st.text_input(
                logic.get_ui_text("LBL_CURRENT_PASSWORD", lang_mode),
                type="password")
            new = st.text_input(logic.get_ui_text("LBL_NEW_PASSWORD", lang_mode),
                                type="password")
            confirm = st.text_input(
                logic.get_ui_text("LBL_CONFIRM_PASSWORD", lang_mode),
                type="password")
            if st.form_submit_button(
                    logic.get_ui_text("BTN_CHANGE_PASSWORD", lang_mode)):
                if new != confirm:
                    st.error(logic.get_ui_text("ERR_PASSWORD_MISMATCH", lang_mode))
                else:
                    try:
                        ok = auth.change_password(
                            user["profile_id"], current, new,
                            keep_token=st.session_state.get("_session_token"))
                    except ValueError as e:
                        st.error(str(e))
                    else:
                        if ok:
                            st.success(logic.get_ui_text(
                                "MSG_PASSWORD_CHANGED", lang_mode))
                        else:
                            st.error(logic.get_ui_text(
                                "ERR_WRONG_PASSWORD", lang_mode))
    if st.sidebar.button(logic.get_ui_text("BTN_LOGOUT", lang_mode)):
        sign_out()
        st.rerun()


def main():
    st.set_page_config(page_title="Vāṇi", page_icon="🪔", layout="wide")
    local_css()
    # Before anything touches storage. A no-op on reruns (same URL).
    storage.configure(config.DATABASE_URL)

    lang_mode = "English"
    user = require_login(lang_mode)
    if st.session_state.pop("_just_confirmed", False):
        st.success(logic.get_ui_text("MSG_ACCOUNT_CONFIRMED", lang_mode))

    # 1. Load Context
    if "context" not in st.session_state:
        with st.spinner("Loading Knowledge Base..."):
            st.session_state.context = logic.load_knowledge_base()

    # --- SIDEBAR SETTINGS ---
    st.sidebar.header("SETTINGS")
    render_account_sidebar(user, lang_mode)

    # Learning-track gate: nobody reaches a mode without a learner profile,
    # the same way require_login() gates on a signed-in user. Rendered after
    # the account sidebar so "Sign out" stays reachable.
    profile = load_learner()
    if profile is None:
        render_onboarding(lang_mode)
        st.stop()
    render_learning_profile_sidebar(profile, lang_mode)
    if st.session_state.get("placement_stage"):
        render_placement(profile, lang_mode)
        st.stop()
    # Kannada content script (never used for UI chrome — that is lang_mode)
    # and the prompt section every tailored LLM call receives.
    cscript = learner.content_script(profile)
    lblock = learner.prompt_block(profile)

    st.sidebar.markdown("---")

    # UPDATED: Translate "NAVIGATION" Header
    st.sidebar.header(logic.get_ui_text("HDR_NAV", lang_mode))

    nav_options = {
        "Home": "NAV_HOME",
        "Lessons": "NAV_LESSONS",
        "Conversation Practice": "NAV_CHAT",
        "Send Email Lesson": "NAV_EMAIL",
        "Mastery Quiz": "NAV_QUIZ",
        "Daily Review": "NAV_REVIEW",
        "Writing Critique": "NAV_WRITE",
        "Reading Comprehension": "NAV_READ"
    }
    # The email lesson goes to the owner's inbox and advances the shared
    # Google Sheet, so an invited learner must not be able to trigger it.
    if not user["is_admin"]:
        del nav_options["Send Email Lesson"]

    # A mode can hand off to another (Lessons → "Quiz me on this"). A
    # widget's key can only be set before the widget is created, hence the
    # pending value applied here rather than at the button.
    if "_goto_mode" in st.session_state:
        st.session_state.nav_mode = st.session_state.pop("_goto_mode")

    # UPDATED: Translate "Go to:" Label
    mode = st.sidebar.radio(
        logic.get_ui_text("LBL_GOTO", lang_mode),
        options=list(nav_options.keys()),
        format_func=lambda x: logic.get_ui_text(nav_options[x], lang_mode),
        key="nav_mode",
    )

    # --- MAIN APP TITLE (UPDATED) ---
    st.title(logic.get_ui_text("APP_TITLE", lang_mode))
    st.markdown("---")

    # --- MODE: HOME ---
    if mode == "Home":
        st.subheader(logic.get_ui_text("TITLE_HOME", lang_mode))
        st.markdown(logic.get_ui_text("WELCOME_MSG", lang_mode))

        file_count = len(
            glob.glob(os.path.join(config.KNOWLEDGE_DIR, '*.txt'))
            + glob.glob(os.path.join(config.KNOWLEDGE_DIR, '*.md'))
        )
        st.info(f"System Status: {file_count} grammar modules loaded.")
        level_info = learner.LEVELS[profile.level]
        st.caption(
            f"Your track: {level_info['label']} (≈ CEFR {level_info['cefr']}) · "
            f"{learner.MOTIVATIONS[profile.motivation]['label']} · "
            f"{'Kannada script' if profile.reads_script else 'Roman letters'}"
            f" — change it under Settings → Learning profile.")

    # --- MODE: LESSONS ---
    elif mode == "Lessons":
        st.subheader(logic.get_ui_text("TITLE_LESSONS", lang_mode))
        show_harder = profile.level != "total_beginner" and st.checkbox(
            logic.get_ui_text("LBL_SHOW_HARDER", lang_mode), key="lessons_harder")
        lessons = learner.visible_topics(profile, logic.get_lessons(), show_harder)
        names = [l["name"] for l in lessons]
        chosen = st.selectbox("Lesson", names, label_visibility="collapsed")
        lesson = lessons[names.index(chosen)]
        doc_text = logic.load_topic_doc(lesson["file"])
        if doc_text:
            # A Roman reader gets the whole doc transliterated; markdown and
            # English pass through toggle_script untouched.
            st.markdown(logic.toggle_script(doc_text, cscript))
        if lesson["quiz"] and st.button(
                logic.get_ui_text("BTN_QUIZ_ME", lang_mode)):
            init_quiz_state("quiz")
            start_quiz("quiz", logic.build_quiz(lesson["quiz"], n=10),
                       lesson["quiz"], doc_text or st.session_state.context)
            st.session_state["_goto_mode"] = "Mastery Quiz"
            st.rerun()

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
                st.session_state.chat_script_mode = "Kannada (Script)"
                st.session_state.error_quiz_active = False
                st.session_state.error_quiz_questions = []
                st.session_state.error_quiz_index = 0
                st.session_state.error_quiz_score = 0
                st.session_state.error_quiz_history = []

            # 2. STATE A: Setup Phase
            if not st.session_state.chat_active and not st.session_state.show_review:
                st.write("### Configure your conversational partner")
                session_mode = st.radio(
                    "Session mode",
                    ["Choose a Persona", "Custom Scenario 🌐"],
                    horizontal=True,
                )
                is_custom = session_mode == "Custom Scenario 🌐"

                if not is_custom:
                    selected_role = st.selectbox(
                        "Persona",
                        learner.order_personas(profile, config.CHARACTER_CARDS),
                        format_func=lambda n: persona_label(profile, n),
                        help=logic.get_ui_text("LBL_RECOMMENDED", lang_mode),
                    )
                    selected_focus = st.selectbox("Grammar Focus",
                                                  grammar_goals_for(profile))
                    chat_scenario = st.text_area(
                        "Real-world scenario (optional)",
                        placeholder=(
                            "Describe a real situation you'll face this week — e.g. "
                            "'I need to buy vegetables at the local market and haggle over the price.'"
                        ),
                        height=80,
                        key="chat_scenario_input",
                    )
                else:
                    selected_role = "Custom Scenario"
                    selected_focus = st.selectbox("Grammar Focus",
                                                  grammar_goals_for(profile))
                    st.info(
                        "**Write a character card for your conversation partner, starting with "
                        "\"You are...\"** — just like the predefined personas.  \n"
                        "Include their role, personality, background, and any quirks. "
                        "The more detail you provide, the more authentic the conversation. "
                        "*(Max 1500 characters)*"
                    )
                    chat_scenario = st.text_area(
                        "Describe your conversation partner",
                        placeholder=(
                            "You are a pet store employee in your mid-twenties who is passionate about "
                            "cats and dogs. You are knowledgeable about a wide range of brands of cat "
                            "and dog food, toys, and accessories, and you enjoy making recommendations "
                            "based on a customer's specific needs. You are friendly and enthusiastic, "
                            "and you always ask customers about their pets before suggesting products."
                        ),
                        height=150,
                        max_chars=1500,
                        key="chat_scenario_input",
                    )

                chat_script_mode = st.radio(
                    "Chat Language Mode",
                    ["Kannada (Script)", "Kannada (Roman - Natural)", "Kannada (Roman - Strict)"],
                    index=0 if profile.reads_script else 1,
                    horizontal=True,
                    help="Script: bot responds in ಕನ್ನಡ ಲಿಪಿ (recommended). Roman modes: romanised Kannada for users who cannot yet read the script.",
                )

                if st.button("Start Conversation"):
                    st.session_state.chat_active = True
                    st.session_state.chat_role = selected_role
                    st.session_state.chat_focus = selected_focus
                    st.session_state.chat_scenario = chat_scenario
                    st.session_state.chat_script_mode = chat_script_mode
                    # Fixed for the whole conversation: a profile change in
                    # Settings applies from the next chat, not mid-dialogue.
                    st.session_state.chat_learner_block = lblock

                    # Trigger bot to speak first
                    with st.spinner("Connecting to Bengaluru..."):
                        init_prompt = "Open the conversation with a natural, in-character greeting appropriate to your role and setting. Your entire response must be in-character — do not reference or acknowledge this instruction."
                        res = logic.generate_chat_turn_ai(
                            init_prompt, [], selected_focus, selected_role,
                            st.session_state.chat_script_mode,
                            scenario=st.session_state.chat_scenario,
                            learner_block=st.session_state.chat_learner_block,
                        )

                        if "error" not in res:
                            st.session_state.chat_history.append({"role": "user", "content": init_prompt})
                            st.session_state.chat_history.append({"role": "assistant", "content": res.get("bot_reply_kannada", "")})
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
                            display_text = logic.toggle_script(
                                msg["kannada"], st.session_state.chat_script_mode
                            )
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
                            st.session_state.chat_script_mode,
                            scenario=st.session_state.chat_scenario,
                            learner_block=st.session_state.get("chat_learner_block"),
                        )

                        if "error" not in res:
                            st.session_state.chat_history.append({"role": "user", "content": prompt})
                            st.session_state.chat_history.append({"role": "assistant", "content": res.get("bot_reply_kannada", "")})
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
                    err_count = len(st.session_state.user_errors)
                    st.warning(f"You made {err_count} {'error' if err_count == 1 else 'errors'} to review.")
                    for i, err in enumerate(st.session_state.user_errors):
                        with st.expander(f"Error {i + 1}: {err.get('original', '')}"):
                            corr = logic.toggle_script(err.get('correction', ''), st.session_state.chat_script_mode)
                            st.write(f"**Correction:** {corr}")
                            st.write(f"**Reason:** {err.get('reason', '')}")

                    st.markdown("---")
                    if not st.session_state.error_quiz_active:
                        if st.button("Practice These Errors 🎯"):
                            with st.spinner("Generating targeted practice questions..."):
                                qs = logic.generate_error_quiz(
                                    st.session_state.user_errors, st.session_state.context,
                                    learner_block=lblock,
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

                        # Only questions BEFORE the current one — the current
                        # question's result renders once below.
                        eq_prev = st.session_state.error_quiz_history[
                            :st.session_state.error_quiz_index]
                        if eq_prev:
                            st.markdown("#### Previous Answers")
                            for i, item in enumerate(eq_prev):
                                with st.expander(f"Q{i + 1}: {item['question']}", expanded=False):
                                    st.write(f"**Your Answer:** {item['user_answer']}")
                                    feed = logic.toggle_script(item['feedback'], st.session_state.chat_script_mode)
                                    corr = logic.toggle_script(item['correct_translation'], st.session_state.chat_script_mode)
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
                                            q_text, user_ans, st.session_state.context,
                                            learner_block=lblock,
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
                                # Same reason as the mastery quiz: the input
                                # box is gone, so without this there is nothing
                                # to compare the correction against.
                                st.write(f"**Your answer:** {last['user_answer']}")
                                feed_text = logic.toggle_script(last['feedback'], st.session_state.chat_script_mode)
                                corr_text = logic.toggle_script(last['correct_translation'], st.session_state.chat_script_mode)
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
                    st.session_state.chat_script_mode = "Kannada (Script)"
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
            render_voice_chat(cscript, profile)

    # --- MODE: SEND LESSON ---
    elif mode == "Send Email Lesson" and user["is_admin"]:
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
        init_quiz_state("quiz")

        # State 1: Setup (read-then-quiz — every topic is always available)
        if not st.session_state.quiz_questions:
            show_harder = profile.level != "total_beginner" and st.checkbox(
                logic.get_ui_text("LBL_SHOW_HARDER", lang_mode), key="quiz_harder")
            topics = learner.visible_topics(
                profile, logic.get_quiz_topics(profile_id=current_profile()),
                show_harder)

            # Beginners first; ✓ for mastered, a count for anything due.
            def _label(t):
                check = "✓ " if t["mastered"] else ""
                due = f"  ·  {t['due']} due" if t["due"] else ""
                return f"{check}{t['name']}  ·  {t['level']}{due}"

            labels = [_label(t) for t in topics]
            st.write(logic.get_ui_text("LBL_TOPIC", lang_mode))
            selected_label = st.selectbox("Topic", labels, label_visibility="collapsed")
            selected = topics[labels.index(selected_label)]

            render_progress_panel(lang_mode)

            # Read-then-quiz: show the lesson doc inline before testing.
            doc_text = logic.load_topic_doc(selected["file"])
            if doc_text:
                with st.expander("📖 Read the lesson", expanded=False):
                    st.markdown(logic.toggle_script(doc_text, cscript))

            if st.button(logic.get_ui_text("BTN_START_QUIZ", lang_mode)):
                # Deterministic: questions come from the fixed bank, no LLM.
                # The topic doc is kept only as context for explain_mistake.
                start_quiz("quiz",
                           logic.build_quiz(selected["name"], n=10),
                           selected["name"],
                           doc_text or st.session_state.context)
                st.rerun()

        # State 2: active quiz, then results once every question is done
        elif render_quiz_runner("quiz", lang_mode, content_mode=cscript,
                                learner_block=lblock):
            score = st.session_state.quiz_score
            total = len(st.session_state.quiz_questions)
            topic = st.session_state.quiz_topic
            st.markdown(f"## Score: {score}/{total}")

            # Record the finished attempt exactly once. This is the results
            # render path, which reruns on every interaction, so an unguarded
            # write here would log the same attempt repeatedly and keep
            # rewriting mastered_at.
            if not st.session_state.quiz_recorded:
                storage.record_attempt(topic, score, total,
                                       profile_id=current_profile())
                if score >= (total * 0.9):
                    storage.set_mastered(topic, score=f"{score}/{total}",
                                         profile_id=current_profile())
                st.session_state.quiz_recorded = True

            attempts = storage.get_attempts(topic=topic,
                                            profile_id=current_profile())
            if len(attempts) > 1:
                best = max(a["score"] for a in attempts)
                st.caption(f"Attempts: {len(attempts)} · best: {best}/{total}")
            if score >= (total * 0.9):
                st.success("Topic Mastered! 🎉")
            else:
                st.warning("Not yet! Keep trying.")

            missed = sum(1 for e in st.session_state.quiz_history
                         if e["tier"] == "incorrect")
            if missed:
                st.info(f"📌 {missed} item{'s' if missed != 1 else ''} "
                        f"scheduled for review — see **Daily Review**.")

            if st.button(logic.get_ui_text("BTN_BACK", lang_mode)):
                end_quiz("quiz")
                st.rerun()

    # --- MODE: DAILY REVIEW (spaced repetition) ---
    elif mode == "Daily Review":
        st.subheader(logic.get_ui_text("TITLE_REVIEW", lang_mode))
        init_quiz_state("review")

        if not st.session_state.review_questions:
            summary = logic.get_review_summary(profile_id=current_profile())
            col_a, col_b = st.columns(2)
            col_a.metric(logic.get_ui_text("LBL_DUE_NOW", lang_mode),
                         summary["due"])
            col_b.metric(logic.get_ui_text("LBL_TRACKED", lang_mode),
                         summary["tracked"])

            if summary["due"]:
                due_by_topic = storage.get_due_counts_by_topic(
                    profile_id=current_profile())
                st.markdown("  \n".join(
                    f"- **{t}** — {n} due"
                    for t, n in sorted(due_by_topic.items())))
                if st.button(logic.get_ui_text("BTN_START_REVIEW", lang_mode)):
                    # Mixed topics, soonest-due first. Context is the whole
                    # knowledge base since a session can span topics.
                    start_quiz("review",
                               logic.build_review_quiz(
                                   n=10, profile_id=current_profile()),
                               None,
                               st.session_state.context)
                    st.rerun()
            elif summary["tracked"]:
                # Items exist but none are ripe yet. FSRS puts a freshly
                # missed item minutes away, not seconds, so this is the normal
                # state straight after a quiz — say when, not "go take a quiz".
                st.info(logic.get_ui_text("LBL_ALL_CAUGHT_UP", lang_mode))
                if summary["next_due"]:
                    when = storage.from_iso(summary["next_due"])
                    st.caption(
                        f"{logic.get_ui_text('LBL_NEXT_DUE', lang_mode)}: "
                        f"{when.strftime('%Y-%m-%d %H:%M UTC')}")
            else:
                st.info(logic.get_ui_text("LBL_NOTHING_TRACKED", lang_mode))

            render_progress_panel(lang_mode)

        elif render_quiz_runner("review", lang_mode, show_topic=True,
                                content_mode=cscript, learner_block=lblock):
            score = st.session_state.review_score
            total = len(st.session_state.review_questions)
            st.markdown(f"## {logic.get_ui_text('LBL_REVIEW_DONE', lang_mode)} "
                        f"{score}/{total}")
            remaining = logic.get_review_summary(
                profile_id=current_profile())["due"]
            if remaining:
                st.info(f"{remaining} still due.")
            else:
                st.success("Everything due has been reviewed. 🎉")
            if st.button(logic.get_ui_text("BTN_BACK", lang_mode)):
                end_quiz("review")
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
            topic = st.selectbox(
                "Topic", learner.order_writing_topics(profile, config.WRITING_TOPICS),
                label_visibility="collapsed")
            if st.button(logic.get_ui_text("BTN_GEN_PROMPT", lang_mode)):
                with st.spinner("Generating..."):
                    prompt_res = logic.generate_content(
                        f"Create a 1-sentence writing prompt regarding {topic}, "
                        f"asking for a piece of writing whose length and "
                        f"complexity suit the learner's level.",
                        st.session_state.context, learner_block=lblock)
                    st.info(logic.toggle_script(prompt_res, cscript))

        st.write(logic.get_ui_text("LBL_PASTE", lang_mode))
        user_text = st.text_area("User Text", height=150, label_visibility="collapsed")

        if st.button(logic.get_ui_text("BTN_ANALYZE", lang_mode)):
            if len(user_text) < 5:
                st.error("Text is too short.")
            else:
                with st.spinner("Analyzing..."):
                    res = logic.critique_text_ai(user_text, style, st.session_state.context,
                                                 learner_block=lblock)
                    if "overall_summary" in res:
                        st.info(logic.toggle_script(res.get('overall_summary'), cscript))
                        for item in res.get('analysis', []):
                            orig = logic.toggle_script(item.get('original', ''), cscript)
                            with st.expander(f"{orig[:40]}..."):
                                if item.get('status') != 'CORRECT':
                                    corr = logic.toggle_script(item.get('corrected'), cscript)
                                    feed = logic.toggle_script(item.get('feedback'), cscript)
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
                topic = st.selectbox(
                    "Topic", learner.order_writing_topics(profile, config.WRITING_TOPICS),
                    key="rc_topic", label_visibility="collapsed")
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
                    generated_text = logic.generate_kannada_article_ai(
                        topic, style, st.session_state.context, learner_block=lblock)
                    st.session_state['current_article'] = generated_text
                    st.session_state.pop('qa_content', None)
                    st.success("Generated.")

        if 'current_article' in st.session_state and st.session_state['current_article']:
            st.markdown("### Article")
            st.info(logic.toggle_script(st.session_state['current_article'], cscript))
            st.markdown("---")

            if st.button(logic.get_ui_text("BTN_GEN_QS", lang_mode)):
                with st.spinner("Creating questions..."):
                    qa_response = logic.generate_comprehension_questions(
                        st.session_state['current_article'], st.session_state.context,
                        learner_block=lblock)
                    st.session_state['qa_content'] = qa_response

            if 'qa_content' in st.session_state and isinstance(st.session_state['qa_content'], list):
                if len(st.session_state['qa_content']) == 0:
                    st.error("Rate limit hit or no questions generated.")
                else:
                    st.markdown("### Questions")
                    for i, item in enumerate(st.session_state['qa_content']):
                        q_text = logic.toggle_script(item.get('question'), cscript)
                        st.markdown(f"**Q{i + 1}: {q_text}**")

                        user_ans = st.text_input(f"Answer {i + 1}", key=f"rc_answer_{i}", label_visibility="collapsed")

                        if st.button(logic.get_ui_text("BTN_CHECK", lang_mode) + f" {i + 1}", key=f"btn_check_{i}"):
                            if not user_ans:
                                st.warning("Write an answer first.")
                            else:
                                with st.spinner("Grading..."):
                                    res = logic.grade_reading_ai(item.get('question'),
                                                                 st.session_state['current_article'], user_ans,
                                                                 st.session_state.context,
                                                                 learner_block=lblock)

                                    feed = logic.toggle_script(res['feedback'], cscript)
                                    expl = logic.toggle_script(res['detailed_explanation'], cscript)

                                    if res['is_correct']:
                                        st.success(f"Correct. {feed}")
                                    else:
                                        st.error(f"Incorrect. {feed}")

                                    with st.expander("Explanation"):
                                        st.write(expl)
                        st.markdown("---")


if __name__ == "__main__":
    main()