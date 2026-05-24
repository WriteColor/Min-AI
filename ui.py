import sys
import os
import json
from pathlib import Path
from datetime import timezone, timedelta

# Professional icon library for PyQt6
try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

# Import everything from the compiled module
import ui_compiled
from ui_compiled import *

# 1. Adapt Timezone to Peru (UTC-5)
_BA_TZ = timezone(timedelta(hours=-5))
ui_compiled._BA_TZ = _BA_TZ

# Active windows tracking for theme synchronization
_active_windows = []

# Override theme application to also sync our web sphere colors
original_apply_theme_stylesheet = ui_compiled._apply_theme_stylesheet

def custom_apply_theme_stylesheet(app, name):
    original_apply_theme_stylesheet(app, name)
    for win in _active_windows:
        if hasattr(win, 'orb') and hasattr(win.orb, 'sync_theme'):
            win.orb.sync_theme()

ui_compiled._apply_theme_stylesheet = custom_apply_theme_stylesheet


# 2. Custom WebEngine-based ParticleOrb (Thread-safe signals!)
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import pyqtSlot, QUrl, Qt, QObject, pyqtSignal

class WebBridge(QObject):
    def __init__(self, orb):
        super().__init__()
        self.orb = orb

    @pyqtSlot()
    def toggle_mute(self):
        if hasattr(self.orb, 'parent_win') and self.orb.parent_win:
            self.orb.parent_win._toggle_mute()

    @pyqtSlot()
    def request_theme(self):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.orb.sync_theme)

class CustomParticleOrb(QWidget):
    # PyQt signals MUST be defined as class attributes for thread-safe cross-thread calls!
    audio_signal = pyqtSignal(float)
    state_signal = pyqtSignal(str)
    theme_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_win = parent
        
        # Link references
        if self.parent_win:
            self.parent_win.orb = self
            
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.web_view = QWebEngineView(self)
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        # Optimize QWebEngineView settings to aggressively save RAM (up to 150MB+ memory reduction)
        try:
            from PyQt6.QtWebEngineCore import QWebEngineSettings
            settings = self.web_view.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, False)  # Canvas is 2D, WebGL is unused
            settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)  # Disable Flash/PDF plugins
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, False)  # No local storage needed
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, False)
            print("[JARVIS] QWebEngineView memory optimizations successfully applied.")
        except Exception as e:
            print(f"[JARVIS] Failed to apply WebEngine memory optimizations: {e}")
        
        # Setup QWebChannel
        self.channel = QWebChannel()
        self.bridge = WebBridge(self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        
        # Load local assets/sphere.html
        sphere_path = Path(__file__).parent / "assets" / "sphere.html"
        self.web_view.setUrl(QUrl.fromLocalFile(str(sphere_path.absolute())))
        
        layout.addWidget(self.web_view)
        self.setLayout(layout)
        
        # Connect signals to thread-safe slots executing on the main GUI thread
        self.audio_signal.connect(self._safe_set_audio)
        self.state_signal.connect(self._safe_set_state)
        self.theme_signal.connect(self._safe_sync_theme)
        
        self.web_view.loadFinished.connect(self._on_load_finished)
        
    def _on_load_finished(self, ok):
        if ok:
            self.sync_theme()
            if self.parent_win:
                self.set_state('MUTED' if self.parent_win._muted else 'LISTENING')

    # Thread-safe triggers called from any secondary thread (like the sounddevice thread)
    def sync_theme(self):
        self.theme_signal.emit()

    def set_audio(self, level: float):
        self.audio_signal.emit(level)
        
    def set_state(self, state: str):
        self.state_signal.emit(state)

    # Slots that run safely inside the main GUI thread
    def _safe_sync_theme(self):
        colors = {
            'PRI': ui_compiled.C.PRI,
            'PRI_DIM': ui_compiled.C.PRI_DIM,
            'TEXT': ui_compiled.C.TEXT,
            'BG': ui_compiled.C.BG
        }
        js_code = f"if (window.setThemeColors) window.setThemeColors({json.dumps(colors)});"
        self.web_view.page().runJavaScript(js_code)

    def _safe_set_audio(self, level: float):
        js_code = f"if (window.updateVolume) window.updateVolume({level});"
        self.web_view.page().runJavaScript(js_code)

    def _safe_set_state(self, state: str):
        js_code = f"if (window.updateState) window.updateState('{state}');"
        self.web_view.page().runJavaScript(js_code)


# 3. Custom MainWindow subclass
class CustomMainWindow(ui_compiled.MainWindow):
    def __init__(self, face_path):
        super().__init__(face_path)
        _active_windows.append(self)
        
        # Define a consistent medium size on startup and prevent squishing
        self.resize(1050, 760)
        self.setMinimumSize(1000, 750)
        
        # Make the window frameless (no native OS borders) and translucent
        from PyQt6.QtCore import Qt
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Set a gorgeous dark-gold glassmorphic background with rounded corners and glowing border
        self.setStyleSheet("""
            QMainWindow {
                background: transparent;
            }
        """)
        
        # ID-specific styling for the central widget to avoid polluting child widgets with borders!
        if self.centralWidget():
            self.centralWidget().setObjectName("myCentralWidget")
            self.centralWidget().setStyleSheet("""
                QWidget#myCentralWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(28, 21, 6, 0.88), stop:1 rgba(10, 7, 2, 0.88));
                    border: 2px solid rgba(245, 158, 11, 0.45);
                    border-radius: 20px;
                }
            """)
            
        # Premium elegant typography for the 'JARVIS' title label
        from PyQt6.QtWidgets import QWidget, QPushButton, QLabel
        from PyQt6.QtGui import QFont, QIcon
        from PyQt6.QtCore import QSize
        for child in self.findChildren(QWidget):
            if hasattr(child, 'text') and child.text():
                txt = child.text()
                # Find the J-A-R-V-I-S label
                if 'J' in txt and 'R' in txt and len(txt) < 25:
                    font = QFont("Century Gothic", 16)
                    font.setBold(True)
                    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 8.0)
                    child.setFont(font)
                    child.setStyleSheet("color: #f59e0b; font-weight: bold; background: transparent;")

        # ──────────────────────────────────────────────────────────────
        # FIX: Restyle the top header bar and bottom input bar from
        # blue-ish (#030a10) to a warm dark-gold tone matching the
        # overall glassmorphic palette
        # ──────────────────────────────────────────────────────────────
        _HEADER_BG  = "#0f0a02"  # Warm near-black gold base
        _BORDER_DIM = "rgba(120, 53, 15, 0.45)"  # Subtle amber separator
        _BTN_DIM    = "#b45309"  # Amber-700 for dim buttons
        _BTN_BRIGHT = "#f59e0b"  # Amber-500 for hover/active

        for child in self.centralWidget().children():
            if isinstance(child, QWidget):
                ss = child.styleSheet()
                # Top header bar
                if 'background:#030a10' in ss and 'border-bottom' in ss:
                    child.setStyleSheet(f"background:{_HEADER_BG}; border-bottom:1px solid {_BORDER_DIM};")
                    # Restyle all buttons inside the top bar
                    for btn in child.findChildren(QPushButton):
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background: transparent; color: {_BTN_DIM};
                                border: 1px solid rgba(120,53,15,0.35); border-radius: 12px;
                            }}
                            QPushButton:hover {{ color: {_BTN_BRIGHT}; border-color: {_BTN_BRIGHT}; background: rgba(245,158,11,0.08); }}
                        """)
                # Bottom input bar
                elif 'background:#030a10' in ss and 'border-top' in ss:
                    child.setStyleSheet(f"background:{_HEADER_BG}; border-top:1px solid {_BORDER_DIM};")
                    for btn in child.findChildren(QPushButton):
                        old_ss = btn.styleSheet()
                        # Keep the green mic button green, restyle other bottom buttons
                        if '#00ff88' not in old_ss and '#ff3355' not in old_ss:
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    background: rgba(245,158,11,0.08); color: {_BTN_DIM};
                                    border: 1px solid rgba(120,53,15,0.35); border-radius: 15px;
                                }}
                                QPushButton:hover {{ color: {_BTN_BRIGHT}; border-color: {_BTN_BRIGHT}; }}
                            """)

        # ──────────────────────────────────────────────────────────────
        # PROFESSIONAL ICONS with qtawesome (Font Awesome 6)
        # Replaces generic Unicode emojis with crisp vector icons
        # ──────────────────────────────────────────────────────────────
        if HAS_QTA:
            self._apply_professional_icons()

        # Style individual bento card widgets with a premium translucent glowing golden background
        for w in [self._spotify_w, self._system_w, self._todo_w, self._notes_w, self._files_panel]:
            name = w.objectName() or f"bento_{id(w)}"
            w.setObjectName(name)
            w.setStyleSheet(f"""
                QWidget#{name} {{
                    background: rgba(35, 28, 10, 0.65);
                    border: 1.5px solid rgba(245, 158, 11, 0.4);
                    border-radius: 12px;
                }}
            """)
        
        # Hide the GridCanvas (the HUD grid frame around the orb)
        for child in self.findChildren(QWidget):
            if child.__class__.__name__ == 'GridCanvas':
                child.hide()
                
        # Ensure the orb area container has absolutely no borders or outlines
        self._orb_area.setObjectName("myOrbArea")
        self._orb_area.setStyleSheet("QWidget#myOrbArea { border: none; background: transparent; }")
        
        # Remove orb from parent layout so its geometry is fully custom and resizable
        if hasattr(self, 'orb') and self.orb:
            layout = self._orb_area.layout()
            if layout:
                layout.removeWidget(self.orb)
            self.orb.setParent(self._orb_area)
            self.orb.show()
        
        # Create bento container for aligned widgets using QGridLayout
        from PyQt6.QtWidgets import QGridLayout
        
        self._bento_container = QWidget(self._orb_area)
        self._bento_container.setStyleSheet("background: transparent;")
        
        self._bento_layout = QGridLayout(self._bento_container)
        self._bento_layout.setContentsMargins(0, 0, 0, 0)
        self._bento_layout.setSpacing(15)
        
        # Set equal stretch for all three columns so they never squeeze or squish Spotify!
        self._bento_layout.setColumnStretch(0, 1)
        self._bento_layout.setColumnStretch(1, 1)
        self._bento_layout.setColumnStretch(2, 1)
        
        # Aligned dashboard bento layout mapping (Spotify spans 2 columns, Weather removed)
        self._bento_layout.addWidget(self._spotify_w, 0, 0, 1, 2)
        self._bento_layout.addWidget(self._system_w, 0, 2, 1, 1)
        self._bento_layout.addWidget(self._todo_w, 1, 0, 1, 1)
        self._bento_layout.addWidget(self._notes_w, 1, 1, 1, 1)
        self._bento_layout.addWidget(self._files_panel, 1, 2, 1, 1)
        
        # Populate bento dashboard on startup (Weather is hidden)
        self._spotify_w.show()
        self._weather_w.hide()
        self._system_w.show()
        self._todo_w.show()
        self._notes_w.show()
        self._files_panel.show()

    # ──────────────────────────────────────────────────────────────────────
    # Professional icon injection using qtawesome (Font Awesome 6)
    # ──────────────────────────────────────────────────────────────────────
    def _apply_professional_icons(self):
        from PyQt6.QtWidgets import QPushButton, QLabel
        from PyQt6.QtGui import QFont, QIcon
        from PyQt6.QtCore import QSize

        _HEADER_BG = '#0f0a02'
        GOLD       = '#f59e0b'
        GOLD_DIM   = '#b45309'
        GREEN      = '#1DB954'  # Spotify brand green
        WHITE      = '#fde68a'
        RED        = '#ff3355'
        ICO_SZ     = QSize(16, 16)
        ICO_MD     = QSize(20, 20)
        ICO_LG     = QSize(26, 26)

        # Helper: set a qta icon on a QPushButton by matching its current text
        def _set_btn_icon(card, text_match, icon_name, color=GOLD, size=ICO_MD):
            for btn in card.findChildren(QPushButton):
                try:
                    if btn.text().strip() == text_match:
                        btn.setIcon(qta.icon(icon_name, color=color))
                        btn.setIconSize(size)
                        btn.setText('')
                        return btn
                except Exception:
                    pass
            return None

        # Helper: set a qta icon on a QLabel by matching its current text
        def _set_lbl_icon(card, text_match, icon_name, color=GOLD, size=ICO_SZ):
            for lbl in card.findChildren(QLabel):
                try:
                    if lbl.text().strip() == text_match:
                        lbl.setPixmap(qta.icon(icon_name, color=color).pixmap(size))
                        return lbl
                except Exception:
                    pass
            return None

        # ─── SPOTIFY CARD ────────────────────────────────────────────
        sp = self._spotify_w
        _set_lbl_icon(sp, '\u266b', 'fa5b.spotify',  color=GREEN, size=ICO_MD)  # ♫ header icon → Spotify logo
        _set_lbl_icon(sp, '\u266a', 'fa5b.spotify',  color=GREEN, size=ICO_SZ)  # ♪ → Spotify
        _set_lbl_icon(sp, '\U0001f50a', 'fa5s.volume-up', color=GOLD_DIM, size=ICO_SZ)  # 🔊 → volume icon
        _set_btn_icon(sp, '\U0001f500', 'fa5s.random',    color=GOLD_DIM, size=ICO_SZ)  # 🔀 → shuffle
        _set_btn_icon(sp, '\u23ee',     'fa5s.step-backward', color=WHITE, size=ICO_MD)  # ⏮ → prev
        _set_btn_icon(sp, '\u23f8',     'fa5s.pause',     color=WHITE, size=ICO_LG)      # ⏸ → pause
        _set_btn_icon(sp, '\u23ed',     'fa5s.step-forward', color=WHITE, size=ICO_MD)   # ⏭ → next
        _set_btn_icon(sp, '\u2661',     'fa5s.heart',     color=RED,   size=ICO_MD)      # ♡ → heart
        _set_btn_icon(sp, '\u2581',     'fa5s.volume-off',  color=GOLD_DIM, size=ICO_SZ) # ▁ vol 1
        _set_btn_icon(sp, '\u2583',     'fa5s.volume-down', color=GOLD_DIM, size=ICO_SZ) # ▃ vol 2
        _set_btn_icon(sp, '\u2585',     'fa5s.volume-down', color=GOLD,     size=ICO_SZ) # ▅ vol 3
        _set_btn_icon(sp, '\u2587',     'fa5s.volume-up',   color=GOLD,     size=ICO_SZ) # ▇ vol 4

        # ─── SYSTEM CARD ─────────────────────────────────────────────
        sy = self._system_w
        _set_lbl_icon(sy, '\u26a1', 'fa5s.bolt',  color=GOLD, size=ICO_MD)   # ⚡ → bolt

        # ─── TODO CARD ───────────────────────────────────────────────
        td = self._todo_w
        _set_lbl_icon(td, '\u2713', 'fa5s.check-circle', color=GREEN, size=ICO_MD)  # ✓ → checkmark
        _set_btn_icon(td, '+',      'fa5s.plus-circle',  color=GOLD,  size=ICO_MD)  # + → plus

        # ─── NOTES CARD ──────────────────────────────────────────────
        nt = self._notes_w
        _set_lbl_icon(nt, '\U0001f4dd', 'fa5s.sticky-note', color=GOLD, size=ICO_MD)  # 📝 → note

        # ─── FILES PANEL ─────────────────────────────────────────────
        fp = self._files_panel
        _set_lbl_icon(fp, '\U0001f4c1', 'fa5s.folder-open', color=GOLD, size=ICO_MD)  # 📁 → folder

        # ─── CLOSE (✕) BUTTONS on all cards → fa5s.times ─────────
        for card in [sp, sy, td, nt, fp]:
            _set_btn_icon(card, '\u2715', 'fa5s.times', color='#78350f', size=ICO_SZ)

        # ─── DRAG HANDLE (⠿) LABELS on bento cards → fa5s.grip-vertical ─
        for card in [sp, sy, td, nt]:
            _set_lbl_icon(card, '\u283f', 'fa5s.grip-vertical', color='#78350f', size=ICO_SZ)

        # ─── STATUS DOT (●) LABELS → fa5s.circle ────────────────
        for card in [sp, sy, td, nt]:
            _set_lbl_icon(card, '\u25cf', 'fa5s.circle', color=GREEN, size=QSize(8, 8))

        # ─── TOP BAR BUTTONS ─────────────────────────────────────
        # Settings ⚙, Play ▸, Folder 📁
        for child in self.centralWidget().children():
            if isinstance(child, QWidget):
                ss = child.styleSheet()
                if 'border-bottom' in ss and (_HEADER_BG in ss or '#030a10' in ss or '#0f0a02' in ss):
                    for btn in child.findChildren(QPushButton):
                        t = btn.text().strip()
                        if t == '\u2699':       # ⚙ settings
                            btn.setIcon(qta.icon('fa5s.cog', color=GOLD_DIM))
                            btn.setIconSize(ICO_MD)
                            btn.setText('')
                        elif t == '\u25b8':     # ▸ play
                            btn.setIcon(qta.icon('fa5s.play', color=GOLD_DIM))
                            btn.setIconSize(ICO_MD)
                            btn.setText('')
                        elif t == '\U0001f4c1': # 📁 folder
                            btn.setIcon(qta.icon('fa5s.folder', color=GOLD_DIM))
                            btn.setIconSize(ICO_MD)
                            btn.setText('')
                    break
        
    def closeEvent(self, event):
        if self in _active_windows:
            _active_windows.remove(self)
        super().closeEvent(event)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._layout_orb_area)

    def mousePressEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        
    def _build_input_strip(self):
        outer = super()._build_input_strip()
        outer.hide()
        return outer

    def _layout_orb_area(self):
        super()._layout_orb_area()
        if hasattr(self, 'orb') and self.orb:
            W = self._orb_area.width()
            H = self._orb_area.height()
            if getattr(self, '_orb_mini', False):
                # Mini layout: place at bottom-left
                mx = 18
                my = H - 110 - 210 - 18
                self.orb.setGeometry(mx, my, 210, 210)
            else:
                # Full size: cover the entire central widget (core + bottom transcript space)
                # This positions the HTML capsule exactly at the bottom of the window
                self.orb.setGeometry(0, 0, W, H)

            # Bento grid container geometry: fits closer to the edges (no margins)
            if hasattr(self, '_bento_container') and self._bento_container:
                bh = H // 2 - 20 # Height of the bento grid area
                by = H // 2 - 10 # Position it starting from the middle
                bw = W - 30 # Leave tiny margin on the sides (15px each side)
                bx = 15
                self._bento_container.setGeometry(bx, by, bw, bh)
                
                # Z-order stacking adjustments:
                self.orb.lower() # Push the 3D sphere to the background!
                self._bento_container.raise_() # Bring the interactive Bento Grid to the front!

    def _build_beta_banner(self):
        # Prevent the "Beta" or "Pasate a pro" banner from ever being created!
        from PyQt6.QtWidgets import QWidget
        widget = QWidget(self)
        widget.hide()
        return widget

    def _style_mic(self, muted):
        super()._style_mic(muted)
        if hasattr(self, 'orb') and self.orb:
            self.orb.set_state('MUTED' if muted else 'LISTENING')

    def _show_widget(self, widget, make_orb_mini=False):
        # Allow the widgets to remain in the locked Bento Grid layout stably
        widget.show()
        widget.raise_()


# 4. Inject overridden classes into compiled module namespace
ui_compiled.ParticleOrb = CustomParticleOrb
ui_compiled.MainWindow = CustomMainWindow

# Expose overridden classes in the public namespace of ui.py
ParticleOrb = CustomParticleOrb
MainWindow = CustomMainWindow
