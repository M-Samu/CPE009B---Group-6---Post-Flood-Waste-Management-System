from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QStackedWidget, QFrame, QListWidget, QLineEdit, QTextEdit, 
    QMessageBox
)

from waste_management_models import Session
from data_store import DataStore

# MAIN ADMIN DASHBOARD CLASS
class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard | Post-Flood Waste Management")
        self.resize(800, 620)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header Row
        top_bar = QHBoxLayout()
        admin_badge = QLabel("ROLE: ADMINISTRATOR")
        admin_badge.setObjectName("adminBadge")

        btn_logout = QPushButton("Log Out")
        btn_logout.setObjectName("secondaryButton")
        btn_logout.clicked.connect(self.logout)

        top_bar.addWidget(admin_badge)
        top_bar.addStretch()
        top_bar.addWidget(btn_logout)
        main_layout.addLayout(top_bar)

        # Stacked Admin Control Pages
        self.stack = QStackedWidget()

        # Admin Page 1: Create Task
        page_tasks = QWidget()
        layout_tasks = QVBoxLayout(page_tasks)
        card_tasks = QFrame()
        card_tasks.setObjectName("adminCard")
        t_layout = QVBoxLayout(card_tasks)

        t_title = QLabel("Create Volunteer Task")
        t_title.setObjectName("pageHeading")
        
        lbl_task_input = QLabel("Task Description / Assignment:")
        self.txt_task_desc = QLineEdit()
        self.txt_task_desc.setPlaceholderText("e.g. Segregate plastic waste at District 2")

        btn_add_task = QPushButton("Publish Task to Volunteers")
        btn_add_task.setObjectName("primaryButton")
        btn_add_task.clicked.connect(self.handle_add_task)

        t_layout.addWidget(t_title)
        t_layout.addWidget(lbl_task_input)
        t_layout.addWidget(self.txt_task_desc)
        t_layout.addWidget(btn_add_task)
        t_layout.addStretch()
        layout_tasks.addWidget(card_tasks)

        # Admin Page 2: Send Notifications
        page_notif = QWidget()
        layout_notif = QVBoxLayout(page_notif)
        card_notif = QFrame()
        card_notif.setObjectName("adminCard")
        n_layout = QVBoxLayout(card_notif)

        n_title = QLabel("Send Notification / Announcement")
        n_title.setObjectName("pageHeading")

        lbl_n_heading = QLabel("Announcement Title:")
        self.txt_n_heading = QLineEdit()
        self.txt_n_heading.setPlaceholderText("e.g. 📢 Emergency Flood Advisory")

        lbl_n_body = QLabel("Announcement Body:")
        self.txt_n_body = QTextEdit()

        btn_send_notif = QPushButton("Send Notification to All Volunteers")
        btn_send_notif.setObjectName("primaryButton")
        btn_send_notif.clicked.connect(self.handle_send_notification)

        n_layout.addWidget(n_title)
        n_layout.addWidget(lbl_n_heading)
        n_layout.addWidget(self.txt_n_heading)
        n_layout.addWidget(lbl_n_body)
        n_layout.addWidget(self.txt_n_body)
        n_layout.addWidget(btn_send_notif)
        layout_notif.addWidget(card_notif)

        # Admin Page 3: Review Waste Reports
        page_reports = QWidget()
        layout_reports = QVBoxLayout(page_reports)
        card_rep = QFrame()
        card_rep.setObjectName("adminCard")
        r_layout = QVBoxLayout(card_rep)

        r_title = QLabel("Review Submitted Waste Reports")
        r_title.setObjectName("pageHeading")
        self.admin_reports_list = QListWidget()
        self.admin_reports_list.setObjectName("announcementList")

        btn_refresh_rep = QPushButton("Refresh Reports List")
        btn_refresh_rep.setObjectName("secondaryButton")
        btn_refresh_rep.clicked.connect(self.refresh_admin_reports)

        r_layout.addWidget(r_title)
        r_layout.addWidget(self.admin_reports_list)
        r_layout.addWidget(btn_refresh_rep)
        layout_reports.addWidget(card_rep)

        self.stack.addWidget(page_tasks)    # 0
        self.stack.addWidget(page_notif)    # 1
        self.stack.addWidget(page_reports)  # 2

        main_layout.addWidget(self.stack, 1)

        # --- CIRCULAR ADMIN NAVIGATION BAR ---
        nav_frame = QFrame()
        nav_frame.setObjectName("navBarFrame")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(15, 10, 15, 10)

        self.btn_a_tasks = QPushButton("Create\nTask")
        self.btn_a_notif = QPushButton("Send\nNotif")
        self.btn_a_reports = QPushButton("Review\nReports")

        self.admin_nav_buttons = [
            (self.btn_a_tasks, 0),
            (self.btn_a_notif, 1),
            (self.btn_a_reports, 2)
        ]

        nav_layout.addStretch()
        for btn, idx in self.admin_nav_buttons:
            btn.setObjectName("navCircleButton")
            btn.setFixedSize(68, 68)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self.switch_admin_tab(i))
            nav_layout.addWidget(btn)
            nav_layout.addStretch()

        main_layout.addWidget(nav_frame)
        self.switch_admin_tab(0)

    def switch_admin_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 2:
            self.refresh_admin_reports()

        # Update QSS properties and refresh style dynamically
        for btn, idx in self.admin_nav_buttons:
            is_active = "true" if idx == index else "false"
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def handle_add_task(self):
        task_text = self.txt_task_desc.text().strip()
        if not task_text:
            QMessageBox.warning(self, "Input Error", "Task description cannot be empty.")
            return
        
        DataStore.tasks.append(f"Task: {task_text}")
        self.txt_task_desc.clear()
        QMessageBox.information(self, "Success", "Task successfully assigned to volunteers!")

    def handle_send_notification(self):
        title = self.txt_n_heading.text().strip()
        body = self.txt_n_body.toPlainText().strip()

        if not title or not body:
            QMessageBox.warning(self, "Input Error", "Please fill in both title and body for notification.")
            return

        DataStore.announcements.insert(0, (title, body))
        self.txt_n_heading.clear()
        self.txt_n_body.clear()
        QMessageBox.information(self, "Success", "Notification broadcasted to all volunteers!")

    def refresh_admin_reports(self):
        self.admin_reports_list.clear()
        for r in DataStore.waste_reports:
            self.admin_reports_list.addItem(r)

    def logout(self):
        from login_window import LoginWindow
        Session.logout()
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()