from datetime import datetime
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QListWidget,
    QListWidgetItem, QDialog, QLineEdit, QTextEdit, QComboBox,
    QMessageBox, QScrollArea
)

from waste_management_models import Session
from app_utils import current_datetime
from data_store import DataStore


# ==============================================================================
# Custom Blue Progress Gauge (Matches 1VOLdashboarddesign.jpg)
# ==============================================================================
class CircularProgressWidget(QWidget):
    def __init__(self, value=75, max_value=100, parent=None):
        super().__init__(parent)
        self.value = value
        self.max_value = max_value
        self.setMinimumSize(170, 170)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        size = min(width, height) - 24
        rect = QRectF((width - size) / 2, (height - size) / 2, size, size)

        # Soft background track ring
        bg_pen = QPen(QColor("#dbeafe"), 14)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        # Active blue progress arc
        progress_pen = QPen(QColor("#3b82f6"), 14)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)

        angle = int(360 * (self.value / self.max_value) * 16)
        painter.drawArc(rect, 90 * 16, -angle)

        # Inner text ("75% / Target Met")
        painter.setPen(QColor("#1e293b"))
        font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}%\nTarget Met")


# ==============================================================================
# Screen 1: Overview
# ==============================================================================
class VolunteerOverviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(14)

        # Welcome Heading
        self.welcome_label = QLabel("Welcome, Samuel Ramos")
        self.welcome_label.setObjectName("welcomeTitle")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.welcome_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # --- LEFT CARD: Date & Tasks List ---
        self.task_card = QFrame()
        self.task_card.setObjectName("volCard")
        task_layout = QVBoxLayout(self.task_card)
        task_layout.setContentsMargins(20, 20, 20, 20)

        # Dynamic Date Header
        today_str = datetime.now().strftime("%B %d, %Y")
        date_label = QLabel(today_str)
        date_label.setObjectName("cardDateLabel")
        task_layout.addWidget(date_label)

        # Container for task check items
        self.tasks_container = QVBoxLayout()
        self.tasks_container.setSpacing(10)
        task_layout.addLayout(self.tasks_container)
        task_layout.addStretch()

        content_layout.addWidget(self.task_card, 1)

        # --- RIGHT CARD: Blue Progress Gauge & Community Target Tint Box ---
        graphic_card = QFrame()
        graphic_card.setObjectName("volCard")
        graphic_layout = QVBoxLayout(graphic_card)
        graphic_layout.setContentsMargins(20, 20, 20, 20)

        self.ring_chart = CircularProgressWidget(75, 100)
        graphic_layout.addWidget(self.ring_chart, 0, Qt.AlignmentFlag.AlignCenter)

        # Bottom Tinted Soft Container Box
        tint_box = QFrame()
        tint_box.setObjectName("tintedInfoBox")
        tint_layout = QVBoxLayout(tint_box)

        impact_desc = QLabel("Community Target\nPost-Flood Cleanup")
        impact_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        impact_desc.setObjectName("tintedBoxText")
        tint_layout.addWidget(impact_desc)

        graphic_layout.addWidget(tint_box)
        content_layout.addWidget(graphic_card, 1)

        self.main_layout.addLayout(content_layout)

    def refresh_data(self):
        account = Session.current_account
        user_name = account.full_name if account else "Samuel Ramos"
        self.welcome_label.setText(f"Welcome, {user_name}")

        # Clear existing task widgets
        while self.tasks_container.count():
            item = self.tasks_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Build task items with green checkmarks (matching 1VOLdashboarddesign.jpg)
        for task in DataStore.tasks:
            t_row = QHBoxLayout()
            check_icon = QLabel("✔")
            check_icon.setObjectName("taskCheckBadge")

            t_text = QLabel(task)
            t_text.setObjectName("taskItemText")
            t_text.setWordWrap(True)

            t_row.addWidget(check_icon)
            t_row.addWidget(t_text, 1)
            
            row_widget = QWidget()
            row_widget.setLayout(t_row)
            self.tasks_container.addWidget(row_widget)


# ==============================================================================
# Screen 2: Waste Reports
# ==============================================================================
class VolunteerWasteReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("volCard")
        card_layout = QVBoxLayout(card)

        header_layout = QHBoxLayout()
        title = QLabel("Waste Reports")
        title.setObjectName("cardHeading")

        btn_create = QPushButton("Create Report")
        btn_create.setObjectName("primaryButton")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.clicked.connect(self.open_create_report_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_create)
        card_layout.addLayout(header_layout)

        self.reports_list = QListWidget()
        self.reports_list.setObjectName("volListWidget")
        card_layout.addWidget(self.reports_list)

        layout.addWidget(card)

    def refresh_data(self):
        self.reports_list.clear()
        for report in DataStore.waste_reports:
            self.reports_list.addItem(QListWidgetItem(report))

    def open_create_report_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Waste Report")
        dialog.setFixedSize(380, 320)

        d_layout = QVBoxLayout(dialog)

        lbl_location = QLabel("Location / Area:")
        txt_location = QLineEdit()

        lbl_type = QLabel("Waste Category:")
        cmb_type = QComboBox()
        cmb_type.addItems(["Plastic & Bottles", "Flood Mud / Organic", "Hazardous / E-Waste", "Heavy Debris"])

        lbl_details = QLabel("Description:")
        txt_details = QTextEdit()

        btn_submit = QPushButton("Submit Waste Report")
        btn_submit.setObjectName("primaryButton")

        def handle_submit():
            loc = txt_location.text().strip()
            if not loc:
                QMessageBox.warning(dialog, "Input Error", "Please enter a location.")
                return
            
            report_entry = f"📍 {loc} - {cmb_type.currentText()} (Submitted: {current_datetime()})"
            DataStore.waste_reports.append(report_entry)
            self.refresh_data()
            QMessageBox.information(dialog, "Success", "Waste report submitted!")
            dialog.accept()

        btn_submit.clicked.connect(handle_submit)

        d_layout.addWidget(lbl_location)
        d_layout.addWidget(txt_location)
        d_layout.addWidget(lbl_type)
        d_layout.addWidget(cmb_type)
        d_layout.addWidget(lbl_details)
        d_layout.addWidget(txt_details)
        d_layout.addWidget(btn_submit)

        dialog.exec()


# ==============================================================================
# Screen 3: Scheduled Cleanup Drives
# ==============================================================================
class VolunteerScheduledDrivesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.card = QFrame()
        self.card.setObjectName("volCard")
        self.card_layout = QVBoxLayout(self.card)

        title = QLabel("Scheduled Cleanup Drives")
        title.setObjectName("cardHeading")
        self.card_layout.addWidget(title)

        self.drives_container = QVBoxLayout()
        self.card_layout.addLayout(self.drives_container)
        self.card_layout.addStretch()

        layout.addWidget(self.card)

    def refresh_data(self):
        while self.drives_container.count():
            item = self.drives_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for drive in DataStore.cleanup_drives:
            drive_box = QFrame()
            drive_box.setObjectName("driveItemBox")
            i_layout = QHBoxLayout(drive_box)

            info_v = QVBoxLayout()
            lbl_name = QLabel(drive["name"])
            lbl_name.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
            lbl_meta = QLabel(f"Date: {drive['datetime']} | Location: {drive['location']}")
            lbl_meta.setStyleSheet("color: #64748b; font-size: 12px; border: none;")
            info_v.addWidget(lbl_name)
            info_v.addWidget(lbl_meta)

            btn_join = QPushButton("Joined" if drive["joined"] else "Join Drive")
            btn_join.setEnabled(not drive["joined"])
            btn_join.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_join.setObjectName("primaryButton")
            
            def make_join_handler(d=drive):
                def handler():
                    d["joined"] = True
                    QMessageBox.information(self, "Cleanup Drive", f"You joined '{d['name']}'!")
                    self.refresh_data()
                return handler

            btn_join.clicked.connect(make_join_handler())

            i_layout.addLayout(info_v)
            i_layout.addStretch()
            i_layout.addWidget(btn_join)

            self.drives_container.addWidget(drive_box)


# ==============================================================================
# Screen 4: Rewards Page
# ==============================================================================
class VolunteerRewardsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("volCard")
        card_layout = QVBoxLayout(card)

        title = QLabel("Claim Your Rewards")
        title.setObjectName("cardHeading")
        card_layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)

        reward_items = [
            "Eco Bag", "Water Bottle", "Gloves Kit", "Meal Pass", "Cert Badge",
            "Cap / Hat", "T-Shirt", "Hydration Tumbler", "Snack Pack", "VIP Badge"
        ]

        idx = 0
        for row in range(2):
            for col in range(5):
                if idx < len(reward_items):
                    item_name = reward_items[idx]
                    r_box = QFrame()
                    r_box.setObjectName("rewardGridCard")
                    b_layout = QVBoxLayout(r_box)

                    lbl = QLabel(item_name)
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl.setStyleSheet("font-weight: bold; font-size: 12px; border: none;")

                    btn_claim = QPushButton("Claim")
                    btn_claim.setObjectName("secondaryButton")
                    btn_claim.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_claim.clicked.connect(lambda _, n=item_name: QMessageBox.information(self, "Rewards", f"Claim request for '{n}' received!"))

                    b_layout.addWidget(lbl)
                    b_layout.addWidget(btn_claim)
                    grid.addWidget(r_box, row, col)
                    idx += 1

        scroll.setWidget(grid_widget)
        card_layout.addWidget(scroll)

        layout.addWidget(card)


# ==============================================================================
# Screen 5: Notifications Feed
# ==============================================================================
class VolunteerAnnouncementsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("volCard")
        self.card_layout = QVBoxLayout(card)

        title = QLabel("Notification and Announcement")
        title.setObjectName("cardHeading")
        self.card_layout.addWidget(title)

        self.feed_container = QVBoxLayout()
        self.card_layout.addLayout(self.feed_container)
        self.card_layout.addStretch()

        layout.addWidget(card)

    def refresh_data(self):
        while self.feed_container.count():
            item = self.feed_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for heading, body in DataStore.announcements:
            box = QFrame()
            box.setObjectName("driveItemBox")
            b_layout = QVBoxLayout(box)

            h_lbl = QLabel(heading)
            h_lbl.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")
            b_lbl = QLabel(body)
            b_lbl.setStyleSheet("color: #475569; font-size: 12px; border: none;")
            b_lbl.setWordWrap(True)

            b_layout.addWidget(h_lbl)
            b_layout.addWidget(b_lbl)

            self.feed_container.addWidget(box)


# ==============================================================================
# MAIN VOLUNTEER DASHBOARD CLASS
# ==============================================================================
class VolunteerDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Volunteer Dashboard | Post-Flood Waste Management")
        self.resize(880, 680)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 15)
        main_layout.setSpacing(12)

        # --- HEADER BAR (Matches Capsule Pill Layout in 1VOLdashboarddesign.jpg) ---
        top_bar = QHBoxLayout()
        
        # Left Badge Pill
        badge_pill = QLabel("Volunteer Dashboard")
        badge_pill.setObjectName("headerBadgePill")

        subtitle = QLabel("Post-Flood Waste Management")
        subtitle.setObjectName("headerSubtitle")

        btn_logout = QPushButton("Log Out")
        btn_logout.setObjectName("logoutPillButton")
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.clicked.connect(self.logout)

        top_bar.addWidget(badge_pill)
        top_bar.addWidget(subtitle)
        top_bar.addStretch()
        top_bar.addWidget(btn_logout)
        main_layout.addLayout(top_bar)

        # --- STACKED PAGES CONTAINER ---
        self.stack = QStackedWidget()
        self.page_overview = VolunteerOverviewPage()
        self.page_waste_reports = VolunteerWasteReportsPage()
        self.page_scheduled_drives = VolunteerScheduledDrivesPage()
        self.page_rewards = VolunteerRewardsPage()
        self.page_announcements = VolunteerAnnouncementsPage()

        self.stack.addWidget(self.page_overview)          # Index 0
        self.stack.addWidget(self.page_waste_reports)     # Index 1
        self.stack.addWidget(self.page_scheduled_drives) # Index 2
        self.stack.addWidget(self.page_rewards)          # Index 3
        self.stack.addWidget(self.page_announcements)   # Index 4

        main_layout.addWidget(self.stack, 1)

        # --- CAPSULE PILL BOTTOM NAVIGATION BAR ---
        nav_frame = QFrame()
        nav_frame.setObjectName("bottomNavFrame")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(15, 8, 15, 8)

        # Capsule nav buttons matching exact labels/icons from design
        self.btn_nav_home = QPushButton("    Home  ")
        self.btn_nav_reports = QPushButton(" Waste\nReports")
        self.btn_nav_drives = QPushButton(" Cleanup\nDrives")
        self.btn_nav_rewards = QPushButton(" Rewards")
        self.btn_nav_announcements = QPushButton(" Notifications")

        self.nav_buttons = [
            (self.btn_nav_home, 0),
            (self.btn_nav_reports, 1),
            (self.btn_nav_drives, 2),
            (self.btn_nav_rewards, 3),
            (self.btn_nav_announcements, 4)
        ]

        nav_layout.addStretch()
        for btn, index in self.nav_buttons:
            btn.setObjectName("capsuleNavBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=index: self.switch_tab(idx))
            nav_layout.addWidget(btn)
            nav_layout.addStretch()

        main_layout.addWidget(nav_frame)

        # Footer version label
        version_label = QLabel("In Development")
        version_label.setObjectName("versionLabel")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(version_label)

        self.switch_tab(0)

    def switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)

        current_widget = self.stack.currentWidget()
        if hasattr(current_widget, "refresh_data"): 
            current_widget.refresh_data()

        # Update QSS properties for active capsule pill style
        for btn, idx in self.nav_buttons:
            is_active = "true" if idx == index else "false"
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def logout(self):
        from login_window import LoginWindow
        Session.logout()
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()