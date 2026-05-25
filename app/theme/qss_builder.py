"""QssBuilder — generates the application stylesheet from a ThemeSpec.

The *entire* visual definition lives here.  To change how the app looks:

* Swap the active ``ThemeSpec``    → colour / font changes
* Adjust ``base_pt``               → font-scale changes
* Edit this file                   → shape / layout / structural changes

**No widget may call ``setStyleSheet``.**
Widgets express styling intent via ``setObjectName`` and ``setProperty``,
and these rules make them look correct automatically.
"""
from __future__ import annotations

from theme.spec import (
    FONT_SIZE_BASE_PX,
    ColorRole,
    FontRole,
    FontSize,
    ThemeSpec,
)

# Reference authored scale — the px values in FONT_SIZE_BASE_PX were written
# assuming a 13-px UI base font (matching the original styles.qss).
QSS_BASE_PX: int = 13


def _px(authored: int, scale: float, min_px: int = 8) -> int:
    """Scale *authored* px by *scale*, clamping to *min_px*."""
    return max(min_px, round(authored * scale))


def _font_sizes(scale: float) -> dict[FontSize, int]:
    """Return a mapping of every FontSize token → scaled px value."""
    return {fs: _px(base, scale) for fs, base in FONT_SIZE_BASE_PX.items()}


class QssBuilder:
    """Builds the complete application QSS from a ThemeSpec and a font scale."""

    @staticmethod
    def build(spec: ThemeSpec, base_pt: int, use_orbitron_headings: bool = True) -> str:
        """Return the full application QSS string.

        Parameters
        ----------
        spec:
            The active ThemeSpec that supplies all colour and font values.
        base_pt:
            User-chosen base font size in points.  All ``font-size`` values
            are scaled relative to the authored 13-px reference scale.
        use_orbitron_headings:
            When False, the body font is used for heading elements instead of
            the Orbitron display font.
        """
        scale = base_pt / QSS_BASE_PX
        sz    = _font_sizes(scale)
        p     = spec.palette
        f     = spec.fonts

        # Convenience shortcuts
        body    = f[FontRole.BODY]
        display = f[FontRole.DISPLAY] if use_orbitron_headings else body
        mono    = f[FontRole.MONO]
        tp      = p[ColorRole.TEXT_PRIMARY]
        ts      = p[ColorRole.TEXT_SECONDARY]
        tm      = p[ColorRole.TEXT_MUTED]
        ap      = p[ColorRole.ACCENT_PRIMARY]   # cyan
        aa      = p[ColorRole.ACCENT_ALT]       # gold
        suc     = p[ColorRole.SUCCESS]
        wrn     = p[ColorRole.WARNING]
        err     = p[ColorRole.ERROR]

        # Interactive-widget height scales with the font
        input_h = max(24, round(30 * scale))

        return f"""/**
 * Gravity Nexus — Generated Stylesheet
 * Theme   : {spec.name}
 * Base pt : {base_pt}
 * Source  : app/theme/qss_builder.py  –  DO NOT edit this output directly.
 */
/* ═══ GLOBAL ════════════════════════════════════════════════════════════════ */
QWidget {{
    background-color: transparent;
    color: {tp};
    font-family: "{body}";
    font-size: {sz[FontSize.MEDIUM]}px;
    border: none;
    selection-background-color: rgba(87, 199, 255, 80);
    selection-color: {tp};
}}
/* ═══ MAIN WINDOW ══════════════════════════════════════════════════════════ */
#AppContent {{
    background: qlineargradient(x1:0, y1:0, x2:0.4, y2:1,
        stop:0 #0B1730, stop:0.45 #081120, stop:1 #0B1730);
    border-radius: 0px;
    border: 1px solid rgba(87, 199, 255, 30);
}}
/* ═══ TITLE BAR ════════════════════════════════════════════════════════════ */
#TitleBar {{
    background: rgba(14, 28, 62, 255);
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom: 1px solid rgba(87, 199, 255, 80);
    min-height: 44px;
    max-height: 44px;
}}
#AppTitleLabel {{
    color: {aa};
    font-family: "{display}";
    font-size: {sz[FontSize.MEDIUM]}px;
    font-weight: bold;
}}
#AppSubtitleLabel {{
    color: {ts};
    font-size: {sz[FontSize.TINY]}px;
}}
#TitleBarBtn {{
    background: transparent;
    border-radius: 7px;
    color: {ts};
    font-size: {sz[FontSize.MEDIUM]}px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
}}
#TitleBarBtn:hover {{ background: rgba(87, 199, 255, 25); color: {tp}; }}
#TitleBarBtn[btnType="close"]:hover    {{ background: rgba(255, 107, 107, 35); color: {err}; }}
#TitleBarBtn[btnType="maximize"]:hover {{ background: rgba(216, 179, 106, 25); color: {aa};  }}
#TitleBarBtn:pressed {{ background: rgba(87, 199, 255, 45); }}
/* ═══ SIDEBAR ══════════════════════════════════════════════════════════════ */
#Sidebar {{
    background: rgba(8, 17, 32, 245);
    border-right: 1px solid rgba(87, 199, 255, 30);
    min-width: 240px;
    max-width: 240px;
}}
#SidebarLogoArea {{
    background: transparent;
    border-bottom: 1px solid rgba(87, 199, 255, 25);
    padding: 6px 0px;
}}
#SidebarLogoTitle {{
    color: {aa};
    font-family: "{display}";
    font-size: {sz[FontSize.LARGE]}px;
    font-weight: bold;
}}
#SidebarLogoSub        {{ color: {ap}; font-size: {sz[FontSize.TINY]}px; }}
#SidebarSectionLabel   {{ color: {ts}; font-size: {sz[FontSize.TINY]}px;  font-weight: bold; padding: 4px 18px 2px 18px; }}
#ParseStatusWidget {{
    background: rgba(17, 34, 64, 180);
    border: 1px solid rgba(87, 199, 255, 30);
    border-radius: 8px;
    margin: 6px 12px;
    padding: 6px 10px;
}}
#ParseStatusLabel {{ color: {ts}; font-size: {sz[FontSize.SMALL]}px; }}
#ProfileUsername  {{ color: {tp}; font-size: {sz[FontSize.SMALL]}px; }}
#ProfilePopupHeader {{ color: {ts}; font-size: {sz[FontSize.SMALL]}px; }}
#ProfilePopupName   {{ color: {tp}; font-size: {sz[FontSize.MEDIUM]}px; font-weight: bold; }}
#ProfilePopupSep    {{ background: rgba(87, 199, 255, 30); }}
/* ═══ STATUS BAR ═══════════════════════════════════════════════════════════ */
#StatusBar {{
    background: rgba(8, 17, 32, 200);
    border-top: 1px solid rgba(87, 199, 255, 30);
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px 14px;
}}
#StatusBarText    {{ color: {ts};                        font-size: {sz[FontSize.SMALL]}px; }}
#StatusBarVersion {{ color: rgba(147, 164, 195, 60);     font-size: {sz[FontSize.SMALL]}px; }}
#StatusBarSeparator {{ background: rgba(87, 199, 255, 30); }}
/* ═══ SETTINGS CARD ════════════════════════════════════════════════════════ */
#SettingsCard {{
    background: rgba(17, 34, 64, 210);
    border: 1px solid rgba(87, 199, 255, 45);
    border-radius: 10px;
}}
#SettingsCardHeader {{
    background: rgba(22, 43, 77, 160);
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border-bottom: 1px solid rgba(87, 199, 255, 30);
    padding: 10px 16px;
    min-height: 46px;
}}
#SettingsCardTitle    {{ color: {tp}; font-size: {sz[FontSize.MEDIUM]}px; font-weight: bold; }}
#SettingsCardSubtitle {{ color: {ts}; font-size: {sz[FontSize.SMALL]}px; }}
#SettingsCardBody     {{ background: transparent; padding: 14px 16px; }}
/* ═══ TOOL CARD ════════════════════════════════════════════════════════════ */
#ToolCard {{
    background: rgba(17, 34, 64, 210);
    border: 1px solid rgba(87, 199, 255, 45);
    border-radius: 10px;
}}
#ToolCardHeader {{
    background: rgba(22, 43, 77, 160);
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border-bottom: 1px solid rgba(87, 199, 255, 30);
    min-height: 50px;
}}
#ToolCardHeader:hover    {{ background: rgba(22, 43, 77, 210); }}
#ToolCardChevron         {{ color: {ap}; font-size: {sz[FontSize.SMALL]}px; }}
#ToolCardTitle           {{ color: {tp}; font-size: {sz[FontSize.MEDIUM]}px; font-weight: bold; }}
#ToolCardDescription     {{ color: {ts}; font-size: {sz[FontSize.SMALL]}px; }}
#ToolCardBody            {{ background: transparent; }}
#ToolCardTabs            {{ background: transparent; border: none; }}
#ToolCardTabs::pane      {{ background: transparent; border: none; border-top: 1px solid rgba(87, 199, 255, 25); }}
#ToolCardTabs QTabBar::tab {{
    background: transparent;
    color: {ts};
    font-size: {sz[FontSize.SMALL]}px;
    padding: 7px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 80px;
}}
#ToolCardTabs QTabBar::tab:hover    {{ color: {tp}; border-bottom: 2px solid rgba(87, 199, 255, 60); }}
#ToolCardTabs QTabBar::tab:selected {{ color: {ap}; font-weight: bold; border-bottom: 2px solid {ap}; }}
/* ═══ SECTION HEADER ═══════════════════════════════════════════════════════ */
#SectionHeader {{ color: {ap}; font-size: {sz[FontSize.SMALL]}px; font-weight: bold; }}
/* ═══ BUTTONS ══════════════════════════════════════════════════════════════ */
QPushButton {{
    background: rgba(22, 43, 77, 200);
    border: 1px solid rgba(87, 199, 255, 55);
    border-radius: 6px;
    color: {tp};
    font-size: {sz[FontSize.SMALL]}px;
    padding: 6px 18px;
    min-height: {input_h}px;
}}
QPushButton:hover    {{ background: rgba(87, 199, 255, 35);  border-color: rgba(87, 199, 255, 120); }}
QPushButton:pressed  {{ background: rgba(87, 199, 255, 55);  border-color: {ap}; }}
QPushButton:disabled {{ background: rgba(17, 34, 64, 80);    border-color: rgba(87, 199, 255, 20); color: rgba(147, 164, 195, 80); }}
QPushButton[variant="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(216, 179, 106, 200), stop:1 rgba(180, 140, 70, 220));
    border: 1px solid rgba(216, 179, 106, 160);
    color: #081120;
    font-weight: bold;
}}
QPushButton[variant="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(230, 195, 120, 220), stop:1 rgba(200, 155, 85, 240));
}}
QPushButton[variant="primary"]:pressed  {{ background: rgba(180, 140, 70, 240); }}
QPushButton[variant="secondary"] {{
    background: rgba(87, 199, 255, 35);
    border: 1px solid rgba(87, 199, 255, 140);
    color: {tp};
}}
QPushButton[variant="secondary"]:hover  {{ background: rgba(87, 199, 255, 60); border-color: rgba(87, 199, 255, 200); }}
QPushButton[variant="danger"] {{
    background: rgba(255, 107, 107, 40);
    border: 1px solid rgba(255, 107, 107, 120);
    color: {err};
}}
QPushButton[variant="danger"]:hover {{ background: rgba(255, 107, 107, 70); border-color: rgba(255, 107, 107, 200); color: {tp}; }}
QPushButton[variant="ghost"] {{ background: transparent; border-color: transparent; color: {ts}; }}
QPushButton[variant="ghost"]:hover {{ background: rgba(87, 199, 255, 18); border-color: rgba(87, 199, 255, 40); color: {ap}; }}
/* ═══ LINE EDIT ════════════════════════════════════════════════════════════ */
QLineEdit {{
    background: rgba(11, 23, 48, 200);
    border: 1px solid rgba(87, 199, 255, 45);
    border-radius: 6px;
    color: {tp};
    font-size: {sz[FontSize.SMALL]}px;
    padding: 5px 10px;
    selection-background-color: rgba(87, 199, 255, 80);
}}
QLineEdit:focus    {{ border-color: rgba(87, 199, 255, 160); background: rgba(17, 34, 64, 220); }}
QLineEdit:hover    {{ border-color: rgba(87, 199, 255, 90); }}
QLineEdit:disabled {{ color: rgba(147, 164, 195, 60); border-color: rgba(87, 199, 255, 20); }}
/* ═══ SEARCH BOX ═══════════════════════════════════════════════════════════ */
#SearchBox {{
    background: rgba(11, 23, 48, 200);
    border: 1px solid rgba(87, 199, 255, 45);
    border-radius: 6px;
}}
#SearchBoxEdit {{
    background: transparent;
    border: none;
    color: {tp};
    font-size: {sz[FontSize.SMALL]}px;
    padding: 0;
}}
#SearchBoxIcon {{
    color: {tm};
    font-size: {sz[FontSize.LARGE]}px;
    background: transparent;
}}
#SearchBoxClearBtn {{
    background: transparent;
    border: none;
    color: rgba(147, 164, 195, 120);
    font-size: {sz[FontSize.TINY]}px;
    padding: 0;
}}
#SearchBoxClearBtn:hover {{ color: {tp}; }}
/* ═══ COMBO BOX ════════════════════════════════════════════════════════════ */
QComboBox {{
    background: rgba(11, 23, 48, 200);
    border: 1px solid rgba(87, 199, 255, 45);
    border-radius: 6px;
    color: {tp};
    font-size: {sz[FontSize.SMALL]}px;
    padding: 5px 10px;
    min-height: {input_h}px;
}}
QComboBox:hover {{ border-color: rgba(87, 199, 255, 90); }}
QComboBox:focus {{ border-color: rgba(87, 199, 255, 160); }}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid rgba(87, 199, 255, 30);
    border-radius: 0px 6px 6px 0px;
}}
QComboBox::down-arrow {{ width: 0px; height: 0px; }}
QComboBox QAbstractItemView {{
    background: rgba(11, 23, 48, 245);
    border: 1px solid rgba(87, 199, 255, 80);
    border-radius: 6px;
    color: {tp};
    selection-background-color: rgba(87, 199, 255, 60);
    padding: 4px;
}}
QComboBox QAbstractItemView::item       {{ padding: 6px 10px; border-radius: 4px; min-height: 26px; }}
QComboBox QAbstractItemView::item:hover {{ background: rgba(87, 199, 255, 35); }}
/* ═══ PLAIN TEXT EDIT ══════════════════════════════════════════════════════ */
QPlainTextEdit {{
    background: rgba(8, 14, 30, 200);
    color: #B0C4DE;
    font-family: "{mono}", "Courier New", monospace;
    font-size: {sz[FontSize.SMALL]}px;
    border: 1px solid rgba(147, 164, 195, 40);
    border-radius: 4px;
    padding: 6px;
}}
/* ═══ PROGRESS BAR ═════════════════════════════════════════════════════════ */
QProgressBar {{
    background: rgba(11, 23, 48, 180);
    border: 1px solid rgba(87, 199, 255, 35);
    border-radius: 5px;
    text-align: center;
    color: {tp};
    font-size: {sz[FontSize.SMALL]}px;
    min-height: 14px;
    max-height: 14px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(87, 199, 255, 180), stop:1 rgba(87, 199, 255, 240));
    border-radius: 4px;
}}
QProgressBar[barColor="gold"]::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(216, 179, 106, 180), stop:1 rgba(216, 179, 106, 240));
}}
QProgressBar[barColor="success"]::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(120, 224, 143, 160), stop:1 rgba(120, 224, 143, 220));
}}
QProgressBar[barColor="danger"]::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255, 107, 107, 160), stop:1 rgba(255, 107, 107, 220));
}}
/* ═══ SCROLL BARS ══════════════════════════════════════════════════════════ */
QScrollBar:vertical   {{ background: rgba(8, 17, 32, 120); width:  8px; border-radius: 4px; margin: 2px; }}
QScrollBar:horizontal {{ background: rgba(8, 17, 32, 120); height: 8px; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:vertical   {{ background: rgba(87, 199, 255, 80);  border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:horizontal {{ background: rgba(87, 199, 255, 80);  border-radius: 4px; min-width:  30px; }}
QScrollBar::handle:vertical:hover   {{ background: rgba(87, 199, 255, 140); }}
QScrollBar::handle:horizontal:hover {{ background: rgba(87, 199, 255, 140); }}
QScrollBar::add-line:vertical   {{ height: 0px; }}
QScrollBar::sub-line:vertical   {{ height: 0px; }}
QScrollBar::add-line:horizontal {{ width:  0px; }}
QScrollBar::sub-line:horizontal {{ width:  0px; }}
/* ═══ SCROLL AREA ══════════════════════════════════════════════════════════ */
QScrollArea {{ background: transparent; border: none; }}
/* ═══ TABLE ════════════════════════════════════════════════════════════════ */
QTableWidget {{
    background: rgba(11, 23, 48, 160);
    border: 1px solid rgba(87, 199, 255, 35);
    border-radius: 6px;
    gridline-color: rgba(87, 199, 255, 20);
    color: {tp};
    font-size: {sz[FontSize.SMALL]}px;
}}
QTableWidget::item          {{ padding: 6px 10px; border: none; }}
QTableWidget::item:selected {{ background: rgba(87, 199, 255, 55); color: {tp}; }}
QTableWidget::item:hover    {{ background: rgba(87, 199, 255, 28); }}
QHeaderView::section {{
    background: rgba(22, 43, 77, 200);
    color: {ts};
    font-size: {sz[FontSize.SMALL]}px;
    font-weight: bold;
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid rgba(87, 199, 255, 40);
}}
QHeaderView::section:hover {{ background: rgba(87, 199, 255, 25); color: {tp}; }}
/* ═══ TOOLTIP ══════════════════════════════════════════════════════════════ */
QToolTip {{
    background: rgba(11, 23, 48, 240);
    border: 1px solid rgba(87, 199, 255, 80);
    border-radius: 6px;
    color: {tp};
    font-size: {sz[FontSize.SMALL]}px;
    padding: 5px 10px;
}}
/* ═══ LABELS ═══════════════════════════════════════════════════════════════ */
QLabel {{ background: transparent; color: {tp}; }}
/* Legacy property selectors — kept for backwards compatibility */
QLabel[secondary="true"] {{ color: {ts}; font-size: {sz[FontSize.SMALL]}px; }}
QLabel[accent="gold"]    {{ color: {aa}; }}
QLabel[accent="cyan"]    {{ color: {ap}; }}
QLabel[heading="true"]   {{ font-family: "{display}"; font-size: {sz[FontSize.XL]}px; font-weight: bold; color: {tp}; }}
/* ═══ CHECK BOX ════════════════════════════════════════════════════════════ */
QCheckBox {{ color: {tp}; font-size: {sz[FontSize.SMALL]}px; spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 1px solid rgba(87, 199, 255, 80); background: rgba(11, 23, 48, 200); }}
QCheckBox::indicator:hover   {{ border-color: rgba(87, 199, 255, 160); }}
QCheckBox::indicator:checked {{ background: rgba(87, 199, 255, 140); border-color: rgba(87, 199, 255, 200); }}
/* ═══ SLIDER ═══════════════════════════════════════════════════════════════ */
QSlider::groove:horizontal  {{ background: rgba(11, 23, 48, 200); height: 6px; border-radius: 3px; border: 1px solid rgba(87, 199, 255, 40); }}
QSlider::handle:horizontal  {{ background: {ap}; width: 16px; height: 16px; margin: -5px 0px; border-radius: 8px; border: 1px solid rgba(87, 199, 255, 160); }}
QSlider::handle:horizontal:hover {{ background: rgba(87, 199, 255, 240); }}
QSlider::sub-page:horizontal {{ background: rgba(87, 199, 255, 120); border-radius: 3px; }}
/* ═══ PAGES ════════════════════════════════════════════════════════════════ */
#PageWrapper  {{ background: transparent; }}
#PageTitle    {{ color: {tp}; font-family: "{display}"; font-size: {sz[FontSize.XL]}px; font-weight: bold; }}
#PageSubtitle {{ color: {ts}; font-size: {sz[FontSize.SMALL]}px; }}
/* ═══ ABOUT PAGE ═══════════════════════════════════════════════════════════ */
#AboutTitle {{
    font-family: "{display}";
    font-size: {sz[FontSize.HEADING]}px;
    color: {aa};
    font-weight: bold;
}}
/* ═══ OVERLAY PREVIEW ══════════════════════════════════════════════════════ */
#OverlayPreviewPanel {{
    background: rgba(8, 17, 32, 220);
    border: 1px solid rgba(87, 199, 255, 55);
    border-radius: 10px;
}}
/* ═══ OVERLAY WINDOWS ══════════════════════════════════════════════════════ */
#BaseOverlay {{
    background: rgb(8, 17, 32);
    border: 1px solid rgba(87, 199, 255, 70);
    border-radius: 8px;
}}
#OverlayHandleBar {{
    background: rgba(22, 43, 77, 180);
    border-bottom: 1px solid rgba(87, 199, 255, 40);
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-height: 24px;
    max-height: 24px;
}}
/* Badge used in overlays to highlight a count / summary */
#OverlayBadge {{
    background: rgba(216, 179, 106, 40);
    color: {aa};
    border-radius: 8px;
    padding: 3px 10px;
    font-size: {sz[FontSize.SMALL]}px;
}}
/* ═══════════════════════════════════════════════════════════════════════════
   SEMANTIC PROPERTY ROLES
   ─────────────────────────────────────────────────────────────────────────
   Widgets set Qt properties to declare visual intent; these rules resolve
   them to the current theme's concrete values.

   Usage (Python):
       label.setProperty("colorRole", ColorRole.SUCCESS.value)
       label.setProperty("fontScale", FontSize.SMALL.value)
       label.setProperty("fontRole",  FontRole.DISPLAY.value)
       _repolish(label)   # or use ThemedLabel which handles this automatically

   Never pass raw hex strings or px values to setStyleSheet.
   ═══════════════════════════════════════════════════════════════════════════ */
/* -- Colour roles -- */
QWidget[colorRole="text_primary"]   {{ color: {tp};  }}
QWidget[colorRole="text_secondary"] {{ color: {ts};  }}
QWidget[colorRole="text_muted"]     {{ color: {tm};  }}
QWidget[colorRole="accent_primary"] {{ color: {ap};  }}
QWidget[colorRole="accent_alt"]     {{ color: {aa};  }}
QWidget[colorRole="success"]        {{ color: {suc}; }}
QWidget[colorRole="warning"]        {{ color: {wrn}; }}
QWidget[colorRole="error"]          {{ color: {err}; }}
/* -- Font size roles -- */
QWidget[fontScale="tiny"]    {{ font-size: {sz[FontSize.TINY]}px;    }}
QWidget[fontScale="small"]   {{ font-size: {sz[FontSize.SMALL]}px;   }}
QWidget[fontScale="medium"]  {{ font-size: {sz[FontSize.MEDIUM]}px;  }}
QWidget[fontScale="large"]   {{ font-size: {sz[FontSize.LARGE]}px;   }}
QWidget[fontScale="xl"]      {{ font-size: {sz[FontSize.XL]}px;      }}
QWidget[fontScale="heading"] {{ font-size: {sz[FontSize.HEADING]}px; }}
/* -- Font family roles -- */
QWidget[fontRole="display"] {{ font-family: "{display}"; }}
QWidget[fontRole="mono"]    {{ font-family: "{mono}", "Courier New", monospace; }}
"""


