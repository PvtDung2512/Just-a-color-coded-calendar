#!/usr/bin/env python3
# floating_calendar_full_projects.py
# Requires: pip install PyQt6
#PVTDung2512
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCalendarWidget, QFileDialog, QMessageBox,
    QSystemTrayIcon, QMenu, QAction, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, QPoint, QEvent, QRect
from PyQt6.QtGui import (
    QCursor, QGuiApplication, QTextCharFormat, QColor, QIcon,
    QPixmap, QPainter, QKeySequence, QFont
)
import sys, csv

# -----------------------
# Palette for statuses / project types (you can change these hex codes)
# -----------------------
PALETTE = {
    "Fabrication":  "#3b82f6",  # blue
    "Installation": "#10b981",  # green
    "Completed":    "#22c55e",  # bright green
    "Overdue":      "#ef4444",  # red
    "Delay":        "#f97316",  # orange
    "Inspection":   "#eab308",  # yellow
    "Handover":     "#6366f1",  # indigo
    "Extra":        "#8b5cf6",  # purple
    "Tentative":    "#94a3b8",  # muted gray
    "Today":        "#38bdf8",  # cyan (special)
}

# Grey placeholder for empty cells in 3x3 grid
GRID_PLACEHOLDER = "#26303a"  # dark grey placeholder

def qcolor(hexstr):
    return QColor(hexstr)

def color_swatch_pix(hexcolor, size=14):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setPen(Qt.GlobalColor.transparent)
    p.setBrush(qcolor(hexcolor))
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.drawRoundedRect(0, 0, size-1, size-1, 3, 3)
    p.end()
    return pix

# -----------------------
# Custom calendar which paints multiple project colors inside each day cell
# -----------------------
class CustomCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Mapping: 'YYYY-MM-DD' -> list of project-type strings (ordered)
        self.project_map = {}
        # allow keyboard focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # make sure grid not shown; we custom paint
        self.setGridVisible(False)

    def set_project_map(self, project_map):
        """project_map: dict 'YYYY-MM-DD' -> list of project type names (strings)"""
        self.project_map = project_map or {}
        self.viewport().update()  # repaint

    def paintCell(self, painter: QPainter, rect: QRect, date: QDate):
        """Override to paint our multi-project visuals"""
        painter.save()

        # fill base background (transparent-ish)
        # call default background (we'll draw date number ourselves later)
        painter.setPen(Qt.GlobalColor.transparent)
        painter.setBrush(qcolor("#0f172a"))  # matches window background
        painter.drawRect(rect)

        key = date.toString("yyyy-MM-dd")
        projects = self.project_map.get(key, [])
        count = len(projects)

        # if has projects, draw according to rules
        if count > 0:
            if count <= 4:
                # horizontal strips: split rect.height into count slices
                slice_h = rect.height() / count
                for i, proj in enumerate(projects[:4]):  # cap to 4 (but rule allows 4)
                    y = rect.top() + int(i * slice_h)
                    h = int(slice_h) + (1 if i == count-1 else 0)  # fix rounding on last
                    r = QRect(rect.left()+2, y+2, rect.width()-4, h-4)  # small inner padding
                    color_hex = PALETTE.get(proj, PALETTE.get("Extra"))
                    painter.setBrush(qcolor(color_hex))
                    painter.setPen(Qt.GlobalColor.transparent)
                    painter.drawRect(r)
                # If there are more than 4 but <=4 branch won't happen; counted above
            else:
                # 5..9 -> 3x3 grid
                # compute cell size with small padding
                pad = 4
                grid_w = rect.width() - pad*2
                grid_h = rect.height() - pad*2
                cell_w = grid_w // 3
                cell_h = grid_h // 3
                # fill each grid cell
                for idx in range(9):
                    row = idx // 3
                    col = idx % 3
                    cx = rect.left() + pad + col * cell_w
                    cy = rect.top() + pad + row * cell_h
                    cw = cell_w - 2
                    ch = cell_h - 2
                    cell_rect = QRect(cx+1, cy+1, cw, ch)
                    if idx < min(count, 9):
                        proj = projects[idx]
                        color_hex = PALETTE.get(proj, PALETTE.get("Extra"))
                        painter.setBrush(qcolor(color_hex))
                    else:
                        painter.setBrush(qcolor(GRID_PLACEHOLDER))  # placeholder
                    painter.setPen(Qt.GlobalColor.transparent)
                    painter.drawRect(cell_rect)

                # if more than 9 -> badge will be drawn below
        else:
            # no projects -> draw nothing special (keeps base background)
            pass

        # Draw selection highlight (start / end / inrange) if needed
        # We will let caller/or parent draw selection; but to keep visual, draw a faint outline if date is selected
        # Parent selection logic will set attribute on widget: self.selected_start/self.selected_end handled externally

        # Draw the day number on top-right-ish
        painter.setPen(qcolor("#cfe8ff"))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        day_text = str(date.day())
        # position in top-left with a little padding
        painter.drawText(rect.adjusted(6, 4, -6, -4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, day_text)

        # If there are >9 projects, draw +N badge bottom-right
        if count > 9:
            extra = count - 9
            badge_text = f"+{extra}"
            # badge rect
            badge_w = 28
            badge_h = 16
            bx = rect.right() - badge_w - 6
            by = rect.bottom() - badge_h - 6
            badge_rect = QRect(bx, by, badge_w, badge_h)
            painter.setBrush(qcolor("#0f172a"))
            painter.setPen(qcolor("#cfe8ff"))
            painter.drawRoundedRect(badge_rect, 6, 6)
            font2 = QFont()
            font2.setPointSize(8)
            painter.setFont(font2)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        # If date is today, draw a subtle outline or mark
        if date == QDate.currentDate():
            pen = painter.pen()
            pen.setColor(qcolor("#38bdf8"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(1,1,-1,-1))

        painter.restore()

# -----------------------
# Main Floating Calendar (keeps prior functionality)
# -----------------------
class FloatingCalendar(QWidget):
    SNAP_MARGIN = 24  # snapping threshold

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Floating Calendar")
        # Always on top and frameless
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowOpacity(0.96)  # Option A
        self._drag_active = False
        self._drag_pos = QPoint(0,0)
        self._last_geom = None

        self.start_date = None
        self.end_date = None

        # Tray
        self.tray = None
        self.always_on_top = True

        self._build_ui()
        self._apply_styles()
        self._connect_signals()

        # sample project_map to demo (today with multiple)
        demo_map = {
            QDate.currentDate().addDays(-1).toString("yyyy-MM-dd"): ["Fabrication"],
            QDate.currentDate().toString("yyyy-MM-dd"): ["Fabrication", "Installation", "Inspection", "Extra"],
            QDate.currentDate().addDays(2).toString("yyyy-MM-dd"): ["Installation","Completed","Delay","Handover","Extra","Inspection"],
            QDate.currentDate().addDays(5).toString("yyyy-MM-dd"): ["Fabrication","Installation","Completed","Overdue","Delay","Inspection","Handover","Extra","Tentative","Extra"],
        }
        # apply demo
        self.calendar.set_project_map(demo_map)

        # position and tray
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geo.right() - self.width() - 24, screen_geo.bottom() - self.height() - 24)
        self._create_tray_icon()

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(8,8,8,8)
        root.setSpacing(8)
        self.setLayout(root)

        # Header (draggable)
        self.header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(6,6,6,6)
        header_layout.setSpacing(8)
        self.header_widget.setLayout(header_layout)
        self.lbl_title = QLabel("  ⬤ Floating Calendar")
        self.lbl_title.setObjectName("title")
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()

        # Quick buttons
        self.btn_today = QPushButton("Today")
        self.btn_week = QPushButton("This Week")
        self.btn_month = QPushButton("This Month")
        self.btn_min = QPushButton("—")
        self.btn_close = QPushButton("✕")
        for b in (self.btn_today, self.btn_week, self.btn_month, self.btn_min, self.btn_close):
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setFixedHeight(28)

        header_layout.addWidget(self.btn_today)
        header_layout.addWidget(self.btn_week)
        header_layout.addWidget(self.btn_month)
        header_layout.addWidget(self.btn_min)
        header_layout.addWidget(self.btn_close)
        root.addWidget(self.header_widget)

        # Custom calendar
        self.calendar = CustomCalendar()
        root.addWidget(self.calendar)

        # Footer: info + legend + actions
        footer = QHBoxLayout()
        self.lbl_info = QLabel("No dates selected")
        footer.addWidget(self.lbl_info)
        footer.addStretch()

        # Legend small subset
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(6)
        items = [("Fabrication","Fabrication"),("Overdue","Overdue"),("Completed","Completed"),("Inspection","Inspection")]
        for label_text, key in items:
            lbl = QLabel(label_text)
            lbl.setPixmap(color_swatch_pix(PALETTE.get(key, PALETTE["Extra"]), size=12))
            lbl.setContentsMargins(6,0,6,0)
            lbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            legend_layout.addWidget(lbl)
        footer.addLayout(legend_layout)

        footer.addStretch()
        self.btn_copy = QPushButton("Copy")
        self.btn_export = QPushButton("Export (CSV)")
        for b in (self.btn_copy, self.btn_export):
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setFixedHeight(30)
        footer.addWidget(self.btn_copy)
        footer.addWidget(self.btn_export)
        root.addLayout(footer)

        # Mini bar
        self.mini_bar = MiniBar(self)

        # Dragging via header event filter
        self.header_widget.installEventFilter(self)

        # connect calendar click to selection logic and show projects dialog
        self.calendar.clicked.connect(self._on_date_clicked)

    def _apply_styles(self):
        style = """
        QWidget {
            background: #0f172a;
            color: #e6eef8;
            border-radius: 10px;
            font-family: Inter, "Segoe UI", Roboto, Arial;
        }
        #title { font-weight: 700; color: #dff1ff; }
        QPushButton {
            background: rgba(255,255,255,0.02);
            border: 0;
            padding: 6px 8px;
            border-radius: 8px;
            color: #cfe8ff;
        }
        QPushButton:hover { background: rgba(255,255,255,0.04); color: #60a5fa; }
        QLabel { color: #cfe8ff; }
        """
        self.setStyleSheet(style)
        self.resize(380, 460)

    def _connect_signals(self):
        self.btn_today.clicked.connect(self._go_today)
        self.btn_week.clicked.connect(self._go_week)
        self.btn_month.clicked.connect(self._go_month)
        self.btn_min.clicked.connect(self._minimize_to_bar)
        self.btn_close.clicked.connect(self._close_app)
        self.btn_copy.clicked.connect(self._copy_selection)
        self.btn_export.clicked.connect(self._export_csv)

    # Dragging via header eventFilter
    def eventFilter(self, obj, event):
        if obj is self.header_widget:
            if event.type() == QEvent.Type.MouseButtonPress:
                me = event
                if me.button() == Qt.MouseButton.LeftButton:
                    self._drag_active = True
                    self._drag_pos = me.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if self._drag_active:
                    gp = event.globalPosition().toPoint()
                    self.move(gp - self._drag_pos)
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self._drag_active:
                    self._drag_active = False
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    self._snap_to_edge_if_close()
                    return True
        return super().eventFilter(obj, event)

    def _snap_to_edge_if_close(self):
        screen_geo = QApplication.primaryScreen().availableGeometry()
        g = self.geometry()
        left = g.left(); right = g.right(); top = g.top(); bottom = g.bottom()
        moved = False
        nx, ny = g.left(), g.top()
        if abs(left - screen_geo.left()) <= self.SNAP_MARGIN:
            nx = screen_geo.left() + 8; moved = True
        elif abs(screen_geo.right() - right) <= self.SNAP_MARGIN:
            nx = screen_geo.right() - g.width() - 8; moved = True
        if abs(top - screen_geo.top()) <= self.SNAP_MARGIN:
            ny = screen_geo.top() + 8; moved = True
        elif abs(screen_geo.bottom() - bottom) <= self.SNAP_MARGIN:
            ny = screen_geo.bottom() - g.height() - 8; moved = True
        if moved:
            self.move(nx, ny)

    # Date click behavior -> selection logic + show project list tooltip dialog
    def _on_date_clicked(self, qdate: QDate):
        # selection logic same as before
        if self.start_date is None:
            self.start_date = QDate(qdate)
            self.end_date = None
        elif self.start_date is not None and self.end_date is None:
            if qdate == self.start_date:
                self.start_date = None
                self.end_date = None
            elif qdate < self.start_date:
                self.end_date = QDate(self.start_date)
                self.start_date = QDate(qdate)
            else:
                self.end_date = QDate(qdate)
        else:
            self.start_date = QDate(qdate)
            self.end_date = None

        # update info label
        self._refresh_info_label()
        # refresh calendar (we didn't override selection visuals, but we redraw)
        self.calendar.viewport().update()

        # show a small dialog with project list for that date (if any)
        key = qdate.toString("yyyy-MM-dd")
        projects = self.calendar.project_map.get(key, [])
        if projects:
            # Build message
            msg = "\n".join(f"{i+1}. {p}" for i,p in enumerate(projects[:20]))
            if len(projects) > 20:
                msg += f"\n... and {len(projects)-20} more"
            QMessageBox.information(self, f"Projects on {key}", msg)

    def _refresh_info_label(self):
        if not self.start_date:
            self.lbl_info.setText("No dates selected")
        elif self.start_date and not self.end_date:
            self.lbl_info.setText(f"Start: {self.start_date.toString('yyyy-MM-dd')}")
        else:
            s = self.start_date; e = self.end_date
            if s > e: s,e = e,s
            self.lbl_info.setText(f"Range: {s.toString('yyyy-MM-dd')} → {e.toString('yyyy-MM-dd')}")

    # Quick-jump helpers
    def _go_today(self):
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.showSelectedDate()
        self.start_date = None; self.end_date = None
        self._refresh_info_label()

    def _go_week(self):
        d = QDate.currentDate()
        start = d.addDays(-(d.dayOfWeek()-1))
        end = start.addDays(6)
        self.start_date = QDate(start); self.end_date = QDate(end)
        self._refresh_info_label()
        self.calendar.viewport().update()

    def _go_month(self):
        d = QDate.currentDate()
        start = QDate(d.year(), d.month(), 1)
        end = start.addMonths(1).addDays(-1)
        self.start_date = QDate(start); self.end_date = QDate(end)
        self._refresh_info_label()
        self.calendar.viewport().update()

    # Minimize / restore / close
    def _minimize_to_bar(self):
        self._last_geom = self.geometry()
        screen_geo = QApplication.primaryScreen().availableGeometry()
        mb_geo = self.mini_bar.geometry()
        mb_x = screen_geo.right() - mb_geo.width() - 24
        mb_y = screen_geo.bottom() - mb_geo.height() - 24
        self.mini_bar.move(mb_x, mb_y)
        self.hide()
        self.mini_bar.show()

    def _restore_from_bar(self):
        if self._last_geom:
            self.setGeometry(self._last_geom)
        else:
            screen_geo = QApplication.primaryScreen().availableGeometry()
            self.move(screen_geo.right() - self.width() - 24, screen_geo.bottom() - self.height() - 24)
        self.show()
        self.mini_bar.hide()

    def _close_app(self):
        if self.tray:
            self.tray.hide()
        self.mini_bar.close()
        self.close()

    # Copy & Export (range inclusive)
    def _copy_selection(self):
        if not self.start_date:
            QMessageBox.information(self, "No selection", "No dates selected.")
            return
        if self.start_date and not self.end_date:
            txt = self.start_date.toString("yyyy-MM-dd")
        else:
            s = self.start_date; e = self.end_date
            if s > e: s,e = e,s
            txt = ",".join((s.addDays(i).toString("yyyy-MM-dd") for i in range(s.daysTo(e)+1)))
        QGuiApplication.clipboard().setText(txt)
        QMessageBox.information(self, "Copied", f"Copied: {txt}")

    def _export_csv(self):
        if not self.start_date:
            QMessageBox.information(self, "No selection", "No dates selected.")
            return
        if self.start_date and not self.end_date:
            rows = [(self.start_date.toString("yyyy-MM-dd"),)]
        else:
            s = self.start_date; e = self.end_date
            if s > e: s,e = e,s
            rows = []
            for i in range(s.daysTo(e)+1):
                d = s.addDays(i)
                rows.append((d.toString("yyyy-MM-dd"),))
        fn, _ = QFileDialog.getSaveFileName(self, "Save CSV", "dates.csv", "CSV Files (*.csv);;All Files (*)")
        if not fn:
            return
        try:
            with open(fn, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            QMessageBox.information(self, "Saved", f"Saved {len(rows)} rows to {fn}")
        except Exception as ex:
            QMessageBox.critical(self, "Error", f"Could not save file: {ex}")

    # Keyboard events (shortcuts)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.start_date = None; self.end_date = None; self._refresh_info_label(); self.calendar.viewport().update()
        elif event.key() == Qt.Key.Key_T:
            self._go_today()
        elif event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and event.key() == Qt.Key.Key_C:
            self._copy_selection()
        elif event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and event.key() == Qt.Key.Key_E:
            self._export_csv()
        else:
            super().keyPressEvent(event)

    # System tray
    def _create_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = QIcon(self._make_tray_pixmap())
        self.tray = QSystemTrayIcon(icon)
        menu = QMenu()
        show_action = QAction("Show")
        hide_action = QAction("Hide")
        toggle_top = QAction("Toggle Always On Top")
        quit_action = QAction("Quit")
        show_action.triggered.connect(lambda: (self.show(), self.mini_bar.hide()))
        hide_action.triggered.connect(lambda: (self.hide(), self.mini_bar.show()))
        toggle_top.triggered.connect(self._toggle_always_on_top)
        quit_action.triggered.connect(self._close_app)
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addAction(toggle_top)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Floating Calendar")
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _make_tray_pixmap(self):
        pix = QPixmap(32,32)
        pix.fill(qcolor("#0f172a"))
        p = QPainter(pix)
        p.setBrush(qcolor("#3b82f6")); p.setPen(Qt.GlobalColor.transparent)
        p.drawRoundedRect(4,4,24,24,4,4)
        p.end()
        return pix

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
                self.mini_bar.show()
            else:
                self.show()
                self.mini_bar.hide()

    def _toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.always_on_top)
        self.setWindowFlags(self.windowFlags())
        self.show()

# -----------------------
# MiniBar widget
# -----------------------
class MiniBar(QWidget):
    def __init__(self, parent: FloatingCalendar):
        super().__init__(None)
        self.parent = parent
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowOpacity(0.96)
        self._build_ui()
        self._apply_styles()
        self._connect_signals()
        self.hide()

    def _build_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8,8,8,8)
        self.setLayout(layout)
        self.lbl = QLabel("Calendar")
        self.btn_restore = QPushButton("⤢")
        self.btn_quit = QPushButton("✕")
        for b in (self.btn_restore, self.btn_quit):
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setFixedHeight(28)
        layout.addWidget(self.lbl)
        layout.addStretch()
        layout.addWidget(self.btn_restore)
        layout.addWidget(self.btn_quit)
        self.resize(180, 44)

    def _apply_styles(self):
        style = """
        QWidget { background: #0f172a; color: #dff1ff; border-radius: 999px; }
        QPushButton { background: rgba(255,255,255,0.02); border: 0; padding: 6px 8px; border-radius: 8px; color: #cfe8ff; }
        QPushButton:hover { color: #60a5fa; background: rgba(255,255,255,0.04); }
        QLabel { font-weight: 700; padding-left: 6px; }
        """
        self.setStyleSheet(style)

    def _connect_signals(self):
        self.btn_restore.clicked.connect(self._restore_parent)
        self.btn_quit.clicked.connect(self._quit_app)

    def _restore_parent(self):
        self.hide()
        self.parent._restore_from_bar()

    def _quit_app(self):
        self.parent._close_app()

# -----------------------
# Helper to apply project_map programmatically
# project_map: dict 'YYYY-MM-DD' -> list of project type strings
# Example:
# { '2025-11-14': ['Fabrication','Installation'] }
# -----------------------
def apply_project_map_to_widget(widget_calendar, project_map):
    widget_calendar.set_project_map(project_map)

# -----------------------
# Run
# -----------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("Floating Calendar")
    win = FloatingCalendar()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

