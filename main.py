import os
import re
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt, QPointF, QSettings
from qgis.PyQt.QtGui import QColor, QFont, QPolygonF, QIcon
from qgis.PyQt.QtWidgets import QAction, QComboBox, QToolBar
from qgis.core import (
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes,
    QgsLayoutItemHtml, QgsLayoutFrame, QgsLayoutItemPolyline,
    QgsLayoutItemLabel, QgsLineSymbol
)

PLUGIN_DIR = os.path.dirname(__file__)

CALLOUT_CSS = """:root {
  --line-length: 36px;
  --line-width: 2px;
  --icon-size: 16px;

  --bg-color: rgba(15, 23, 42, 0.56);
  --border-color: rgba(148, 163, 184, 0.60);
  --accent-color: #94a3b8;
  --text-color: #f8fafc;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 6px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 12px;
  line-height: 1.38;
  background: transparent;
}

.variant-brand   { --border-color: rgba(96, 165, 250, 0.65); --accent-color: #60a5fa; }
.variant-info    { --border-color: rgba(34, 211, 238, 0.65); --accent-color: #22d3ee; }
.variant-success { --border-color: rgba(74, 222, 128, 0.65); --accent-color: #4ade80; }
.variant-warning { --border-color: rgba(251, 191, 36, 0.65); --accent-color: #fbbf24; }
.variant-danger  { --border-color: rgba(248, 113, 113, 0.65); --accent-color: #f87171; }

.wa-callout {
  width: fit-content;
  max-width: 100%;
  padding: 7px 11px;
  border-radius: 6px;
  background-color: var(--bg-color);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid var(--border-color);
  border-left: 3.5px solid var(--accent-color);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.18);
  color: var(--text-color);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
}

.wa-callout strong {
  color: #ffffff;
}
"""

VARIANTS = {
    "brand": {
        "icon": "\u25C9",
        "hex": "#60a5fa",
        "title_pt": "Ponto de Referência:",
        "body_pt": "Edite este texto nas propriedades da moldura HTML.",
        "title_en": "Reference Point:",
        "body_en": "Edit this text in the HTML frame properties."
    },
    "info": {
        "icon": "\u24D8",
        "hex": "#22d3ee",
        "title_pt": "Nota Técnica:",
        "body_pt": "Edite este texto nas propriedades da moldura HTML.",
        "title_en": "Technical Note:",
        "body_en": "Edit this text in the HTML frame properties."
    },
    "success": {
        "icon": "\u2714",
        "hex": "#4ade80",
        "title_pt": "Área Regularizada:",
        "body_pt": "Edite este texto nas propriedades da moldura HTML.",
        "title_en": "Validated Area:",
        "body_en": "Edit this text in the HTML frame properties."
    },
    "warning": {
        "icon": "\u26A0",
        "hex": "#fbbf24",
        "title_pt": "Atenção Ambiental:",
        "body_pt": "Edite este texto nas propriedades da moldura HTML.",
        "title_en": "Environmental Alert:",
        "body_en": "Edit this text in the HTML frame properties."
    },
    "danger": {
        "icon": "\u2716",
        "hex": "#f87171",
        "title_pt": "Zona de Risco:",
        "body_pt": "Edite este texto nas propriedades da moldura HTML.",
        "title_en": "Hazard Zone:",
        "body_en": "Edit this text in the HTML frame properties."
    },
}


def is_pt_br():
    locale = str(QSettings().value("locale/userLocale", "en_US"))
    return locale.lower().startswith("pt")


class ModernCalloutPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.designer_bars = {}

    def initGui(self):
        self.iface.layoutDesignerOpened.connect(self._on_designer_opened)
        for designer in self.iface.openLayoutDesigners():
            self._on_designer_opened(designer)

    def unload(self):
        try:
            self.iface.layoutDesignerOpened.disconnect(self._on_designer_opened)
        except Exception:
            pass

        for designer, bar in list(self.designer_bars.items()):
            try:
                if bar is not None and not sip.isdeleted(bar):
                    if designer is not None and not sip.isdeleted(designer):
                        win = designer.window()
                        if win is not None and not sip.isdeleted(win):
                            win.removeToolBar(bar)
                    bar.deleteLater()
            except Exception:
                pass
        self.designer_bars.clear()

    def _on_designer_opened(self, designer):
        if designer is None or sip.isdeleted(designer):
            return
        if designer in self.designer_bars:
            return

        win = designer.window()
        if win is None or sip.isdeleted(win):
            return

        pt = is_pt_br()
        bar = QToolBar("Modern Callout", win)
        bar.setObjectName("ModernCalloutToolBar")

        icon_path = os.path.join(PLUGIN_DIR, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        combo = QComboBox(bar)
        combo.setToolTip(
            "Escolha a variante do Modern Callout" if pt else "Select Modern Callout variant"
        )
        combo.setMinimumWidth(145)
        for key, data in VARIANTS.items():
            combo.addItem(f"{data['icon']}  variant-{key}", key)

        act_add = QAction(icon, "Adicionar Callout" if pt else "Add Callout", bar)
        act_add.setToolTip(
            "Inserir Moldura HTML, Polilinha e Ícone nativos no Layout"
            if pt else "Insert native HTML Frame, Polyline and Marker Icon into Layout"
        )
        act_add.triggered.connect(lambda _checked=False, d=designer, c=combo: self._add_callout(d, c))

        bar.addAction(act_add)
        bar.addWidget(combo)
        win.addToolBar(Qt.TopToolBarArea, bar)
        bar.show()

        self.designer_bars[designer] = bar

    def _next_index(self, layout):
        used = set()
        pattern = re.compile(r"^(?:modern-callout|polilinha|icone texto)\s+(\d+)$", re.IGNORECASE)
        for item in layout.items():
            try:
                iid = item.id().strip()
                m = pattern.match(iid)
                if m:
                    used.add(int(m.group(1)))
            except Exception:
                pass
        idx = 1
        while idx in used:
            idx += 1
        return idx

    def _add_callout(self, designer, combo):
        if designer is None or sip.isdeleted(designer):
            return
        layout = designer.layout()
        if not layout:
            return

        pt = is_pt_br()
        variant_key = combo.currentData() if combo.currentData() in VARIANTS else "brand"
        vdata = VARIANTS[variant_key]
        idx = self._next_index(layout)

        offset = (idx - 1) * 6.0
        icon_x = 30.0 + offset
        icon_y = 45.0 + offset
        line_start_x = icon_x + 7.5
        line_mid_y = icon_y + 4.0
        box_x = line_start_x + 14.0
        box_y = icon_y - 4.0

        # 1. Ícone Marcador Nativo (QgsLayoutItemLabel)
        label = QgsLayoutItemLabel(layout)
        label.setId(f"icone texto {idx}")
        label.setText(vdata["icon"])
        label.setFont(QFont("Sans Serif", 14, QFont.Bold))
        label.setFontColor(QColor(vdata["hex"]))
        label.setHAlign(Qt.AlignHCenter)
        label.setVAlign(Qt.AlignVCenter)
        label.setBackgroundEnabled(False)
        label.setFrameEnabled(False)
        label.attemptMove(QgsLayoutPoint(icon_x, icon_y, QgsUnitTypes.LayoutMillimeters))
        label.attemptResize(QgsLayoutSize(8.0, 8.0, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(label)

        # 2. Linha Conectora Nativa (QgsLayoutItemPolyline)
        poly_points = QPolygonF([
            QPointF(line_start_x, line_mid_y),
            QPointF(box_x, line_mid_y)
        ])
        polyline = QgsLayoutItemPolyline(poly_points, layout)
        polyline.setId(f"polilinha {idx}")
        line_symbol = QgsLineSymbol.createSimple({
            "color": vdata["hex"],
            "width": "0.55",
            "width_unit": "MM",
            "capstyle": "round"
        })
        polyline.setSymbol(line_symbol)
        layout.addLayoutItem(polyline)

        # 3. Moldura HTML Nativa (QgsLayoutItemHtml + QgsLayoutFrame)
        title_str = vdata["title_pt"] if pt else vdata["title_en"]
        body_str = vdata["body_pt"] if pt else vdata["body_en"]

        html_item = QgsLayoutItemHtml(layout)
        html_item.setContentMode(QgsLayoutItemHtml.ManualHtml)
        html_item.setHtml(
            f'<div class="wa-callout variant-{variant_key}">\n'
            f'  <strong>{title_str}</strong> {body_str}\n'
            f'</div>'
        )
        html_item.setUserStylesheet(CALLOUT_CSS)
        html_item.setUserStylesheetEnabled(True)

        frame = QgsLayoutFrame(layout, html_item)
        frame.setId(f"modern-callout {idx}")
        frame.setBackgroundEnabled(False)
        frame.setFrameEnabled(False)
        frame.attemptMove(QgsLayoutPoint(box_x, box_y, QgsUnitTypes.LayoutMillimeters))
        frame.attemptResize(QgsLayoutSize(68.0, 18.0, QgsUnitTypes.LayoutMillimeters))

        html_item.addFrame(frame)
        layout.addMultiFrame(html_item)
        layout.addLayoutItem(frame)
        html_item.loadHtml()

        layout.deselectAll()
        frame.setSelected(True)
