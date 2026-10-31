import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QStackedWidget, QFrame, QListWidget, QLineEdit, QTextEdit, 
    QMessageBox, QComboBox, QSpinBox
)

from waste_management_models import Session
from data_store import DataStore


# WORKER THREAD FOR SENDING ANNOUNCEMENT EMAILS
class EmailAnnouncementThread(QThread):
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, title, body):
        super().__init__()
        self.title = title
        self.body = body

    def run(self):
        from data_manager import load_accounts
        accounts = load_accounts()
        recipient_emails = [
            acc.email.strip() for acc in accounts
            if acc.role == "Volunteer" and acc.email and "@" in acc.email
        ]

        if not recipient_emails:
            self.finished_signal.emit(False, "Notification saved, but no volunteer email addresses were found.")
            return

        # Replace 'your-app-password-here' with your 16-character Google App Password
        sender_email = "pfwm.noreply@gmail.com"
        sender_password = "szqldlsbmojlvmor"

        try:
            msg = MIMEMultipart()
            msg["From"] = f"Post-Flood Waste Management <{sender_email}>"
            msg["To"] = ", ".join(recipient_emails)
            msg["Subject"] = f"📢 Announcement: {self.title}"
            msg.attach(MIMEText(self.body, "plain"))

            # Use SSL directly over Port 465 to prevent unexpected connection resets
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_emails, msg.as_string())

            self.finished_signal.emit(True, f"Notification broadcasted and email sent to {len(recipient_emails)} volunteer(s)!")
        except Exception as exc:
            self.finished_signal.emit(False, f"Notification saved, but failed to send email: {str(exc)}")


# MAIN ADMIN DASHBOARD CLASS
class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard | Post-Flood Waste Management")
        self.resize(850, 680)

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

        self.stack = QStackedWidget()

        # Page 0: Create Task
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

        # Page 1: Send Notifications
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

        self.btn_send_notif = QPushButton("Send Notification to All Volunteers")
        self.btn_send_notif.setObjectName("primaryButton")
        self.btn_send_notif.clicked.connect(self.handle_send_notification)

        n_layout.addWidget(n_title)
        n_layout.addWidget(lbl_n_heading)
        n_layout.addWidget(self.txt_n_heading)
        n_layout.addWidget(lbl_n_body)
        n_layout.addWidget(self.txt_n_body)
        n_layout.addWidget(self.btn_send_notif)
        layout_notif.addWidget(card_notif)

        # Page 2: Review & Delete Waste Reports
        page_reports = QWidget()
        layout_reports = QVBoxLayout(page_reports)
        card_rep = QFrame()
        card_rep.setObjectName("adminCard")
        r_layout = QVBoxLayout(card_rep)

        r_title = QLabel("Review Submitted Waste Reports")
        r_title.setObjectName("pageHeading")
        self.admin_reports_list = QListWidget()
        self.admin_reports_list.setObjectName("announcementList")

        btn_row_rep = QHBoxLayout()
        btn_refresh_rep = QPushButton("Refresh Reports List")
        btn_refresh_rep.setObjectName("secondaryButton")
        btn_refresh_rep.clicked.connect(self.refresh_admin_reports)

        btn_delete_rep = QPushButton("Delete Selected Report")
        btn_delete_rep.setObjectName("secondaryButton")
        btn_delete_rep.clicked.connect(self.handle_delete_report)

        btn_row_rep.addWidget(btn_refresh_rep)
        btn_row_rep.addWidget(btn_delete_rep)

        r_layout.addWidget(r_title)
        r_layout.addWidget(self.admin_reports_list)
        r_layout.addLayout(btn_row_rep)
        layout_reports.addWidget(card_rep)

        # Page 3: Send Points to Volunteers
        page_points = QWidget()
        layout_points = QVBoxLayout(page_points)
        card_points = QFrame()
        card_points.setObjectName("adminCard")
        p_layout = QVBoxLayout(card_points)

        p_title = QLabel("Award Points to Volunteers")
        p_title.setObjectName("pageHeading")

        lbl_select_vol = QLabel("Select Volunteer:")
        self.combo_volunteers = QComboBox() 
        lbl_points_input = QLabel("Points to Award:")
        self.spin_points = QSpinBox()    
        self.spin_points.setRange(1, 10000)
        self.spin_points.setValue(50)

        btn_send_points = QPushButton("Send Points")
        btn_send_points.setObjectName("primaryButton")
        btn_send_points.clicked.connect(self.handle_send_points)

        p_layout.addWidget(p_title)
        p_layout.addWidget(lbl_select_vol)
        p_layout.addWidget(self.combo_volunteers)
        p_layout.addWidget(lbl_points_input)
        p_layout.addWidget(self.spin_points)
        p_layout.addWidget(btn_send_points)
        p_layout.addStretch()
        layout_points.addWidget(card_points)

        # Page 4: Manage & Delete Reward Release & District Pickup
        page_claims = QWidget()
        layout_claims = QVBoxLayout(page_claims)
        card_claims = QFrame()
        card_claims.setObjectName("adminCard")
        c_layout = QVBoxLayout(card_claims)

        c_title = QLabel("Manage Reward Releases & District Pickup")
        c_title.setObjectName("pageHeading")

        lbl_select_claim = QLabel("Select Volunteer Reward Claim:")
        self.list_claims = QListWidget()
        self.list_claims.setObjectName("announcementList")
        self.list_claims.setFixedHeight(120)
        self.list_claims.currentRowChanged.connect(self.on_claim_selected)

        lbl_office = QLabel("Assign Nearest District Office for Pick-up:")
        self.combo_district_office = QComboBox()
        self.combo_district_office.addItems([
            "District 1 Office (Central Plaza)",
            "District 2 Branch (River Spillway Hub)",
            "District 3 Office (Main Bridge Command)",
            "Barangay 182 Hall Pickup Center"
        ])

        lbl_pickup_notes = QLabel("Pick-up Instructions & Schedule:")
        self.txt_pickup_notes = QLineEdit()
        self.txt_pickup_notes.setPlaceholderText("e.g. Ready for pickup Mon-Fri, 9 AM - 4 PM. Present ID.")

        lbl_claim_status = QLabel("Update Release Status:")
        self.combo_claim_status = QComboBox()
        self.combo_claim_status.addItems([
            "Ready for Pick-up",
            "Released / Picked Up",
            "Processing Release",
            "Cancelled / Out of Stock"
        ])

        btn_claim_row = QHBoxLayout()
        btn_update_claim = QPushButton("Update Status & Notify Volunteer")
        btn_update_claim.setObjectName("primaryButton")
        btn_update_claim.clicked.connect(self.handle_update_claim_status)

        btn_delete_claim = QPushButton("Delete Reward Claim")
        btn_delete_claim.setObjectName("secondaryButton")
        btn_delete_claim.clicked.connect(self.handle_delete_claim)

        btn_claim_row.addWidget(btn_update_claim, 2)
        btn_claim_row.addWidget(btn_delete_claim, 1)

        c_layout.addWidget(c_title)
        c_layout.addWidget(lbl_select_claim)
        c_layout.addWidget(self.list_claims)
        c_layout.addWidget(lbl_office)
        c_layout.addWidget(self.combo_district_office)
        c_layout.addWidget(lbl_pickup_notes)
        c_layout.addWidget(self.txt_pickup_notes)
        c_layout.addWidget(lbl_claim_status)
        c_layout.addWidget(self.combo_claim_status)
        c_layout.addLayout(btn_claim_row)

        layout_claims.addWidget(card_claims)

        # Page 5: Create Cleanup Schedule
        page_schedules = QWidget()
        layout_schedules = QVBoxLayout(page_schedules)
        card_schedules = QFrame()
        card_schedules.setObjectName("adminCard")
        s_layout = QVBoxLayout(card_schedules)

        s_title = QLabel("Create Cleanup Drive Schedule")
        s_title.setObjectName("pageHeading")

        lbl_drive_name = QLabel("Cleanup Drive Name:")
        self.txt_drive_name = QLineEdit()
        self.txt_drive_name.setPlaceholderText("e.g. Barangay 182 Flood Debris Clearing")

        lbl_drive_datetime = QLabel("Date & Time:")
        self.txt_drive_datetime = QLineEdit()
        self.txt_drive_datetime.setPlaceholderText("e.g. Saturday, 8:00 AM")

        lbl_drive_location = QLabel("Location / Venue:")
        self.txt_drive_location = QLineEdit()
        self.txt_drive_location.setPlaceholderText("e.g. Central Plaza Spillway")

        btn_add_schedule = QPushButton("Publish Cleanup Drive Schedule")
        btn_add_schedule.setObjectName("primaryButton")
        btn_add_schedule.clicked.connect(self.handle_add_schedule)

        s_layout.addWidget(s_title)
        s_layout.addWidget(lbl_drive_name)
        s_layout.addWidget(self.txt_drive_name)
        s_layout.addWidget(lbl_drive_datetime)
        s_layout.addWidget(self.txt_drive_datetime)
        s_layout.addWidget(lbl_drive_location)
        s_layout.addWidget(self.txt_drive_location)
        s_layout.addWidget(btn_add_schedule)

        lbl_existing_schedules = QLabel("Existing Cleanup Schedules:")
        lbl_existing_schedules.setStyleSheet("font-weight: bold; margin-top: 10px; color: #1e293b;")
        self.list_schedules = QListWidget()
        self.list_schedules.setObjectName("announcementList")
        self.list_schedules.setFixedHeight(110)

        btn_delete_schedule = QPushButton("Delete Selected Schedule")
        btn_delete_schedule.setObjectName("secondaryButton")
        btn_delete_schedule.clicked.connect(self.handle_delete_schedule)

        s_layout.addWidget(lbl_existing_schedules)
        s_layout.addWidget(self.list_schedules)
        s_layout.addWidget(btn_delete_schedule)

        layout_schedules.addWidget(card_schedules)

        # Add pages to stack
        self.stack.addWidget(page_tasks)      # 0
        self.stack.addWidget(page_notif)      # 1
        self.stack.addWidget(page_reports)    # 2
        self.stack.addWidget(page_points)     # 3
        self.stack.addWidget(page_claims)     # 4
        self.stack.addWidget(page_schedules)  # 5

        main_layout.addWidget(self.stack, 1)

        # Capsule Admin Nav Bar
        nav_frame = QFrame()
        nav_frame.setObjectName("bottomNavFrame")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(15, 8, 15, 8)

        self.btn_a_tasks = QPushButton("Create\nTask")
        self.btn_a_notif = QPushButton("Send\nNotif")
        self.btn_a_reports = QPushButton("Review\nReports")
        self.btn_a_points = QPushButton("Send\nPoints") 
        self.btn_a_claims = QPushButton("Reward\nClaims")
        self.btn_a_schedules = QPushButton("Cleanup\nSchedules")

        self.admin_nav_buttons = [
            (self.btn_a_tasks, 0),
            (self.btn_a_notif, 1),
            (self.btn_a_reports, 2),
            (self.btn_a_points, 3),
            (self.btn_a_claims, 4),
            (self.btn_a_schedules, 5)
        ]

        nav_layout.addStretch()
        for btn, idx in self.admin_nav_buttons:
            btn.setObjectName("capsuleNavBtn")
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
        elif index == 3:
            self.refresh_volunteer_dropdown()
        elif index == 4:
            self.refresh_reward_claims_list()
        elif index == 5:
            self.refresh_schedules_list()

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
        DataStore.save()
        self.txt_task_desc.clear()
        QMessageBox.information(self, "Success", "Task successfully assigned to volunteers!")

    def handle_send_notification(self):
        title = self.txt_n_heading.text().strip()
        body = self.txt_n_body.toPlainText().strip()

        if not title or not body:
            QMessageBox.warning(self, "Input Error", "Please fill in both title and body for notification.")
            return

        DataStore.announcements.insert(0, (title, body))
        DataStore.save()

        self.btn_send_notif.setEnabled(False)
        self.btn_send_notif.setText("Sending Emails...")

        self.email_thread = EmailAnnouncementThread(title, body)
        self.email_thread.finished_signal.connect(self._on_announcement_emails_sent)
        self.email_thread.start()

    def _on_announcement_emails_sent(self, success, message):
        self.btn_send_notif.setEnabled(True)
        self.btn_send_notif.setText("Send Notification to All Volunteers")

        self.txt_n_heading.clear()
        self.txt_n_body.clear()

        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Notification Saved", message)

    def refresh_volunteer_dropdown(self):
        from data_manager import load_accounts
        self.combo_volunteers.clear()
        accounts = load_accounts()
        for acc in accounts:
            if acc.role == "Volunteer":
                self.combo_volunteers.addItem(f"{acc.full_name} ({acc.username})", acc.username)

    def handle_send_points(self):
        from data_manager import award_volunteer_points
        username = self.combo_volunteers.currentData()
        if not username:
            QMessageBox.warning(self, "Selection Error", "No volunteer selected.")
            return

        points = self.spin_points.value()
        success, message = award_volunteer_points(username, points)

        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Error", message)

    def refresh_reward_claims_list(self):
        self.list_claims.clear()
        claims = getattr(DataStore, "reward_claims", [])
        if not claims:
            self.list_claims.addItem("No reward claims submitted yet.")
            return

        for claim in claims:
            display_str = (
                f"ID #{claim['id']} | Volunteer: {claim['full_name']} ({claim['username']}) "
                f"| Item: {claim['item_name']} | Status: {claim['status']}"
            )
            self.list_claims.addItem(display_str)

    def on_claim_selected(self, row: int):
        claims = getattr(DataStore, "reward_claims", [])
        if 0 <= row < len(claims):
            selected = claims[row]
            notes = selected.get("pickup_info", "")
            if notes and "Awaiting" not in notes:
                self.txt_pickup_notes.setText(notes)

    def handle_update_claim_status(self):
        row = self.list_claims.currentRow()
        claims = getattr(DataStore, "reward_claims", [])

        if row < 0 or row >= len(claims):
            QMessageBox.warning(self, "Selection Error", "Please select a reward claim from the list.")
            return

        claim = claims[row]
        district_office = self.combo_district_office.currentText()
        notes = self.txt_pickup_notes.text().strip()
        status = self.combo_claim_status.currentText()

        full_pickup_info = f"{district_office}. {notes}" if notes else district_office

        claim["status"] = status
        claim["pickup_info"] = full_pickup_info

        notif_title = f"🎁 Reward Update: {claim['item_name']}"
        notif_body = (
            f"Hello {claim['full_name']}! Your reward claim for '{claim['item_name']}' is now [{status}].\n"
            f"Pickup Location: {district_office}\n"
            f"Instructions: {notes if notes else 'Present your Volunteer ID upon pickup.'}"
        )
        DataStore.announcements.insert(0, (notif_title, notif_body))

        DataStore.save()
        self.refresh_reward_claims_list()

        QMessageBox.information(
            self, "Claim Updated",
            f"Successfully updated release status to '{status}' and sent a notification to {claim['full_name']}!"
        )

    def handle_delete_claim(self):
        row = self.list_claims.currentRow()
        claims = getattr(DataStore, "reward_claims", [])

        if row < 0 or row >= len(claims):
            QMessageBox.warning(self, "Selection Error", "Please select a reward claim to delete.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this reward claim?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            claims.pop(row)
            DataStore.save()
            self.refresh_reward_claims_list()
            QMessageBox.information(self, "Success", "Reward claim deleted successfully.")

    def handle_delete_report(self):
        row = self.admin_reports_list.currentRow()
        if row < 0 or row >= len(DataStore.waste_reports):
            QMessageBox.warning(self, "Selection Error", "Please select a waste report to delete.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this waste report?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            del DataStore.waste_reports[row]
            if hasattr(DataStore, "report_records") and row < len(DataStore.report_records):
                del DataStore.report_records[row]
            DataStore.save()
            self.refresh_admin_reports()
            QMessageBox.information(self, "Success", "Waste report deleted successfully.")

    def handle_add_schedule(self):
        name = self.txt_drive_name.text().strip()
        dt = self.txt_drive_datetime.text().strip()
        loc = self.txt_drive_location.text().strip()

        if not name or not dt or not loc:
            QMessageBox.warning(self, "Input Error", "Please fill in all schedule details (Name, Date/Time, Location).")
            return

        new_id = len(DataStore.cleanup_drives) + 1
        DataStore.cleanup_drives.append({
            "id": new_id,
            "name": name,
            "datetime": dt,
            "location": loc,
            "joined": False
        })

        DataStore.save()
        self.txt_drive_name.clear()
        self.txt_drive_datetime.clear()
        self.txt_drive_location.clear()

        self.refresh_schedules_list()
        QMessageBox.information(self, "Success", f"Cleanup drive '{name}' scheduled and published to volunteers!")

    def refresh_schedules_list(self):
        self.list_schedules.clear()
        for drive in DataStore.cleanup_drives:
            self.list_schedules.addItem(
                f"ID #{drive.get('id', '')} | {drive.get('name', '')} | Date: {drive.get('datetime', '')} | Location: {drive.get('location', '')}"
            )

    def handle_delete_schedule(self):
        row = self.list_schedules.currentRow()
        if row < 0 or row >= len(DataStore.cleanup_drives):
            QMessageBox.warning(self, "Selection Error", "Please select a cleanup drive schedule to delete.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this cleanup drive schedule?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            DataStore.cleanup_drives.pop(row)
            DataStore.save()
            self.refresh_schedules_list()
            QMessageBox.information(self, "Success", "Cleanup drive schedule deleted successfully.")

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