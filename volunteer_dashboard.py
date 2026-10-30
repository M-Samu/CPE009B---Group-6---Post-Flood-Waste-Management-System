from datetime import datetime
from pathlib import Path
import re
import shutil
import time

from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QListWidget,
    QListWidgetItem, QDialog, QLineEdit, QTextEdit, QComboBox,
    QMessageBox, QScrollArea, QFileDialog, QFormLayout,
    QDateEdit, QDialogButtonBox, QGroupBox, QInputDialog, QApplication
)

from waste_management_models import Session, hash_password
from app_utils import current_datetime
from data_manager import load_accounts, save_accounts, find_account
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

        # Build task items with green checkmarks
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

        self.report_image_path = ""

    def choose_report_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Waste Report Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if not file_path:
            return

        source = Path(file_path)
        target_dir = Path("data") / "report_images"
        target_dir.mkdir(parents=True, exist_ok=True)

        account = Session.current_account
        username = account.username if account else "unknown"
        safe_username = re.sub(r"[^A-Za-z0-9_-]", "_", username)

        target = target_dir / (
            f"{safe_username}_{time.time_ns()}{source.suffix.lower()}"
        )

        try:
            shutil.copy2(source, target)
            self.report_image_path = str(target.resolve())

            QMessageBox.information(
                self,
                "Image Selected",
                "The report image has been uploaded."
            )

        except OSError as error:
            QMessageBox.critical(
                self,
                "Upload Failed",
                f"Unable to save the image:\n{error}"
            )

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
            details = txt_details.toPlainText().strip()
            report_type = cmb_type.currentText()

            if not loc:
                QMessageBox.warning(
                    dialog,
                    "Input Error",
                    "Please enter a location."
                )
                return

            account = Session.current_account

            if account is None:
                QMessageBox.warning(
                    dialog,
                    "Login Required",
                    "Please log in before submitting a report."
                )
                return

            submitted_at = current_datetime()

            report_entry = (
                f" {loc} - {report_type} "
                f"(Submitted: {submitted_at})"
            )

            DataStore.waste_reports.append(report_entry)

            if not hasattr(DataStore, "report_records"):
                DataStore.report_records = []

            DataStore.report_records.append({
                "username": account.username,
                "full_name": account.full_name,
                "location": loc,
                "report_type": report_type,
                "details": details,
                "image_path": self.report_image_path,
                "submitted_at": submitted_at,
            })

            self.refresh_data()

            QMessageBox.information(
                dialog,
                "Success",
                "Waste report submitted successfully!"
            )

            self.report_image_path = ""
            dialog.accept()

        btn_submit.clicked.connect(handle_submit)

        d_layout.addWidget(lbl_location)
        d_layout.addWidget(txt_location)
        d_layout.addWidget(lbl_type)
        d_layout.addWidget(cmb_type)
        d_layout.addWidget(lbl_details)
        d_layout.addWidget(txt_details)
        d_layout.addWidget(btn_submit)

        btn_upload_image = QPushButton("Upload Report Image")
        btn_upload_image.clicked.connect(self.choose_report_image)
        d_layout.addWidget(btn_upload_image)

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
                    account = Session.current_account

                    if (
                        account is None
                        or not account.valid_id_path
                        or not Path(account.valid_id_path).is_file()
                    ):
                        QMessageBox.warning(
                            self,
                            "Valid ID Required",
                            "Please upload a valid ID in your profile "
                            "before joining a cleanup drive."
                        )
                        return

                    d["joined"] = True

                    QMessageBox.information(
                        self,
                        "Cleanup Drive",
                        f"You joined '{d['name']}'!"
                    )

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
        
        # Single main layout for the page
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 1. Available Points Display Label at the top
        self.lbl_user_points = QLabel(self)
        self.lbl_user_points.setObjectName("pageHeading")
        self.lbl_user_points.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_user_points)

        # 2. Rewards Card Container
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

        # Load initial points
        self.refresh_user_points()

    def refresh_user_points(self):
        """Fetches the latest points from storage and updates the label."""
        if Session.current_account:
            updated_account = find_account(Session.current_account.username)
            if updated_account:
                Session.current_account = updated_account
            
            points_val = Session.current_account.points
            self.lbl_user_points.setText(f"⭐ Available Points: {points_val}")
        else:
            self.lbl_user_points.setText("⭐ Available Points: 0")

    def showEvent(self, event):
        """Automatically refreshes points every time you open the rewards page."""
        super().showEvent(event)
        self.refresh_user_points()

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
# Screen 6: Volunteer Profile (View Profile / Edit Profile)
# ==============================================================================
class VolunteerProfilePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(12)

        card = QFrame()
        card.setObjectName("volCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 22)
        card_layout.setSpacing(14)

        # Profile heading and Edit Profile button
        header = QHBoxLayout()

        title_column = QVBoxLayout()

        title = QLabel("My Profile")
        title.setObjectName("cardHeading")

        subtitle = QLabel(
            "View and manage your volunteer information"
        )
        subtitle.setWordWrap(True)

        title_column.addWidget(title)
        title_column.addWidget(subtitle)

        header.addLayout(title_column)
        header.addStretch()

        self.btn_edit = QPushButton("Edit Profile")
        self.btn_edit.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.btn_edit.clicked.connect(self.open_edit_dialog)

        header.addWidget(self.btn_edit)
        card_layout.addLayout(header)

        # Profile picture and basic account information
        identity = QHBoxLayout()

        self.avatar = QLabel("Add photo")
        self.avatar.setFixedSize(132, 132)
        self.avatar.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.avatar.setStyleSheet(
            "background-color: #dbeafe;"
            "color: #1d4ed8;"
            "border: 3px solid #bfdbfe;"
            "border-radius: 66px;"
            "font-weight: bold;"
        )

        identity.addWidget(
            self.avatar,
            0,
            Qt.AlignmentFlag.AlignTop
        )

        identity_text = QVBoxLayout()

        self.name_label = QLabel("Volunteer Name")
        self.name_label.setStyleSheet(
            "font-size: 22px;"
            "font-weight: bold;"
            "color: #1e293b;"
        )

        self.role_label = QLabel("Volunteer")
        self.username_label = QLabel("Username: —")
        self.member_since_label = QLabel("Member since: —")

        identity_text.addWidget(self.name_label)
        identity_text.addWidget(self.role_label)
        identity_text.addWidget(self.username_label)
        identity_text.addWidget(self.member_since_label)
        identity_text.addStretch()

        identity.addLayout(identity_text, 1)
        card_layout.addLayout(identity)

        # Personal information section
        details_group = QGroupBox("Personal Information")
        details = QFormLayout(details_group)
        details.setVerticalSpacing(10)
        details.setHorizontalSpacing(18)

        self.email_value = self._make_value_label()
        self.phone_value = self._make_value_label()
        self.dob_value = self._make_value_label()
        self.gender_value = self._make_value_label()
        self.address_value = self._make_value_label()
        self.emergency_name_value = self._make_value_label()
        self.emergency_phone_value = self._make_value_label()

        details.addRow("Email address:", self.email_value)
        details.addRow("Phone number:", self.phone_value)
        details.addRow("Date of birth:", self.dob_value)
        details.addRow("Gender:", self.gender_value)
        details.addRow("Home address:", self.address_value)
        details.addRow(
            "Emergency contact:",
            self.emergency_name_value
        )
        details.addRow(
            "Emergency phone:",
            self.emergency_phone_value
        )

        card_layout.addWidget(details_group)

        self.lbl_valid_id_status = QLabel("Valid ID: Not uploaded")
        card_layout.addWidget(self.lbl_valid_id_status)

        # Additional profile features
        self.btn_valid_id = QPushButton("Upload Valid ID")
        self.btn_gallery = QPushButton("Gallery")
        self.btn_recent_posts = QPushButton("Recent Posts")
        self.btn_achievements = QPushButton("Achievements")
        self.btn_change_password = QPushButton("Change Password")
        self.btn_delete_account = QPushButton("Delete Account")

        # Connect buttons to their functions
        self.btn_valid_id.clicked.connect(self.upload_valid_id)
        self.btn_gallery.clicked.connect(self.show_gallery)
        self.btn_recent_posts.clicked.connect(self.show_recent_posts)
        self.btn_achievements.clicked.connect(self.show_achievements)
        self.btn_change_password.clicked.connect(self.change_password)
        self.btn_delete_account.clicked.connect(self.delete_account)

        # Add buttons to the profile card
        card_layout.addWidget(self.btn_valid_id)
        card_layout.addWidget(self.btn_gallery)
        card_layout.addWidget(self.btn_recent_posts)
        card_layout.addWidget(self.btn_achievements)
        card_layout.addWidget(self.btn_change_password)
        card_layout.addWidget(self.btn_delete_account)

        card_layout.addStretch()

        # Scroll area keeps the profile usable in smaller windows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(card)

        outer.addWidget(scroll)

        self.refresh_data()

    @staticmethod
    def _make_value_label():
        label = QLabel("Not provided")
        label.setWordWrap(True)
        return label

    def refresh_data(self):
        account = Session.current_account

        if account is None:
            self.name_label.setText("No active account")
            return

        self.name_label.setText(
            account.full_name or "Volunteer"
        )
        self.role_label.setText(
            account.role or "Volunteer"
        )
        self.username_label.setText(
            f"Username: {account.username}"
        )
        self.member_since_label.setText(
            f"Member since: {account.created_at or 'Not available'}"
        )

        self.email_value.setText(
            getattr(account, "email", "") or "Not provided"
        )
        self.phone_value.setText(
            getattr(account, "phone", "") or "Not provided"
        )
        self.dob_value.setText(
            getattr(account, "date_of_birth", "") or "Not provided"
        )
        self.gender_value.setText(
            getattr(account, "gender", "") or "Not provided"
        )
        self.address_value.setText(
            getattr(account, "address", "") or "Not provided"
        )
        self.emergency_name_value.setText(
            getattr(account, "emergency_contact_name", "")
            or "Not provided"
        )
        self.emergency_phone_value.setText(
            getattr(account, "emergency_contact_phone", "")
            or "Not provided"
        )

        self.update_avatar()

        if (
            account.valid_id_path
            and Path(account.valid_id_path).is_file()
        ):
            self.lbl_valid_id_status.setText(
                "Valid ID: Uploaded — Pending Verification"
            )
        else:
            self.lbl_valid_id_status.setText(
                "Valid ID: Not Uploaded"
            )

    def upload_valid_id(self):
        account = Session.current_account

        if account is None:
            QMessageBox.warning(self, "Error", "No active account found.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Upload Valid ID",
            "",
            "ID Documents (*.png *.jpg *.jpeg *.pdf)"
        )

        if not file_path:
            return

        source = Path(file_path)
        target_dir = Path("data") / "valid_ids"
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_username = re.sub(r"[^A-Za-z0-9_-]", "_", account.username)
        target = target_dir / f"{safe_username}_valid_id{source.suffix.lower()}"

        try:
            shutil.copy2(source, target)
            account.valid_id_path = str(target.resolve())

            accounts = load_accounts()

            for index, saved_account in enumerate(accounts):
                if saved_account.username == account.username:
                    accounts[index] = account
                    break
            else:
                accounts.append(account)

            save_accounts(accounts)

            QMessageBox.information(
                self,
                "Upload Successful",
                "Your valid ID has been uploaded successfully."
            )

            self.refresh_data()

        except OSError as error:
            QMessageBox.critical(
                self,
                "Upload Failed",
                f"Unable to save the ID:\n{error}"
            )

    def update_avatar(self):
        account = Session.current_account

        self.avatar.clear()
        self.avatar.setText("Add photo")

        if account is None:
            return

        saved_path = getattr(
            account, "profile_picture", ""
        ) or ""

        if not saved_path:
            return

        project_dir = Path(__file__).resolve().parent
        picture_path = Path(saved_path)

        if not picture_path.is_absolute():
            picture_path = project_dir / picture_path

        pixmap = QPixmap(str(picture_path))

        if pixmap.isNull():
            return

        self.avatar.setText("")
        self.avatar.setPixmap(
            pixmap.scaled(
                132,
                132,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def open_edit_dialog(self):
        account = Session.current_account

        if account is None:
            QMessageBox.warning(
                self,
                "Profile",
                "No active account was found."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Profile")
        dialog.resize(520, 650)

        layout = QVBoxLayout(dialog)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        photo_row = QHBoxLayout()

        preview = QLabel("No profile picture")
        preview.setFixedSize(100, 100)
        preview.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        preview.setStyleSheet(
            "background-color: #dbeafe;"
            "border: 2px solid #bfdbfe;"
            "border-radius: 50px;"
        )

        current_picture = getattr(
            account, "profile_picture", ""
        ) or ""

        if current_picture:
            picture_path = Path(current_picture)

            if not picture_path.is_absolute():
                picture_path = (
                    Path(__file__).resolve().parent
                    / picture_path
                )

            pixmap = QPixmap(str(picture_path))

            if not pixmap.isNull():
                preview.setText("")
                preview.setPixmap(
                    pixmap.scaled(
                        100,
                        100,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

        selected_picture = {"path": ""}

        def choose_picture():
            file_path, _ = QFileDialog.getOpenFileName(
                dialog,
                "Choose Profile Picture",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
            )

            if not file_path:
                return

            pixmap = QPixmap(file_path)

            if pixmap.isNull():
                QMessageBox.warning(
                    dialog,
                    "Invalid Image",
                    "Please choose a valid image."
                )
                return

            selected_picture["path"] = file_path
            preview.setText("")
            preview.setPixmap(
                pixmap.scaled(
                    100,
                    100,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        photo_column = QVBoxLayout()
        photo_column.addWidget(QLabel("Profile picture"))

        upload_button = QPushButton("Upload Photo")
        upload_button.clicked.connect(choose_picture)
        photo_column.addWidget(upload_button)
        photo_column.addStretch()

        photo_row.addWidget(preview)
        photo_row.addLayout(photo_column, 1)
        content_layout.addLayout(photo_row)

        form = QFormLayout()
        form.setVerticalSpacing(10)

        txt_name = QLineEdit(account.full_name)
        txt_email = QLineEdit(
            getattr(account, "email", "") or ""
        )
        txt_phone = QLineEdit(
            getattr(account, "phone", "") or ""
        )
        txt_dob = QLineEdit(
            getattr(account, "date_of_birth", "") or ""
        )
        txt_dob.setPlaceholderText("YYYY-MM-DD (optional)")

        cmb_gender = QComboBox()
        cmb_gender.addItems([
            "Prefer not to say",
            "Female",
            "Male",
            "Non-binary",
            "Other",
        ])

        saved_gender = getattr(account, "gender", "") or ""
        if saved_gender and cmb_gender.findText(saved_gender) < 0:
            cmb_gender.addItem(saved_gender)

        cmb_gender.setCurrentText(
            saved_gender or "Prefer not to say"
        )

        txt_address = QTextEdit()
        txt_address.setFixedHeight(75)
        txt_address.setPlainText(
            getattr(account, "address", "") or ""
        )

        txt_emergency_name = QLineEdit(
            getattr(account, "emergency_contact_name", "") or ""
        )
        txt_emergency_phone = QLineEdit(
            getattr(account, "emergency_contact_phone", "") or ""
        )

        form.addRow("Full name *", txt_name)
        form.addRow(
            "Username:",
            QLabel(f"{account.username} (cannot be changed)")
        )
        form.addRow(
            "Role:",
            QLabel(f"{account.role} (assigned by the system)")
        )
        form.addRow("Email address:", txt_email)
        form.addRow("Phone number:", txt_phone)
        form.addRow("Date of birth:", txt_dob)
        form.addRow("Gender:", cmb_gender)
        form.addRow("Home address:", txt_address)
        form.addRow("Emergency contact name:", txt_emergency_name)
        form.addRow("Emergency contact phone:", txt_emergency_phone)

        content_layout.addLayout(form)
        content_layout.addWidget(
            QLabel(
                "Username and role cannot be edited here. "
                "Only provide personal details you are comfortable sharing."
            )
        )

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        full_name = txt_name.text().strip()
        email = txt_email.text().strip()
        phone = txt_phone.text().strip()
        dob = txt_dob.text().strip()
        gender = cmb_gender.currentText()
        address = txt_address.toPlainText().strip()
        emergency_name = txt_emergency_name.text().strip()
        emergency_phone = txt_emergency_phone.text().strip()

        if len(full_name) < 2:
            QMessageBox.warning(
                self,
                "Invalid Profile",
                "Enter a full name with at least 2 characters."
            )
            return

        if email and not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email
        ):
            QMessageBox.warning(
                self,
                "Invalid Profile",
                "Enter a valid email address."
            )
            return

        if dob:
            try:
                datetime.strptime(dob, "%Y-%m-%d")
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Invalid Profile",
                    "Date of birth must use YYYY-MM-DD."
                )
                return

        profile_picture = getattr(
            account, "profile_picture", ""
        ) or ""

        if selected_picture["path"]:
            source = Path(selected_picture["path"])
            project_dir = Path(__file__).resolve().parent
            picture_dir = project_dir / "data" / "profile_pictures"
            picture_dir.mkdir(parents=True, exist_ok=True)

            safe_username = re.sub(
                r"[^A-Za-z0-9_.-]",
                "_",
                account.username
            )

            target = picture_dir / (
                f"{safe_username}_{int(time.time())}"
                f"{source.suffix.lower()}"
            )

            shutil.copy2(source, target)
            profile_picture = str(
                target.relative_to(project_dir)
            )

        account.full_name = full_name
        account.email = email
        account.phone = phone
        account.date_of_birth = dob
        account.gender = (
            "" if gender == "Prefer not to say" else gender
        )
        account.address = address
        account.emergency_contact_name = emergency_name
        account.emergency_contact_phone = emergency_phone
        account.profile_picture = profile_picture

        accounts = load_accounts()
        saved_account = next(
            (
                item for item in accounts
                if item.username.casefold()
                == account.username.casefold()
            ),
            None
        )

        if saved_account is None:
            QMessageBox.warning(
                self,
                "Save Failed",
                "The account could not be found in saved records."
            )
            return

        saved_account.full_name = account.full_name
        saved_account.email = account.email
        saved_account.phone = account.phone
        saved_account.date_of_birth = account.date_of_birth
        saved_account.gender = account.gender
        saved_account.address = account.address
        saved_account.emergency_contact_name = (
            account.emergency_contact_name
        )
        saved_account.emergency_contact_phone = (
            account.emergency_contact_phone
        )
        saved_account.profile_picture = account.profile_picture

        save_accounts(accounts)
        Session.login(saved_account)
        self.refresh_data()

        QMessageBox.information(
            self,
            "Profile Updated",
            "Your profile changes have been saved."
        )

    def show_gallery(self):
        account = Session.current_account
        if account is None:
            return

        records = getattr(DataStore, "report_records", [])
        records = [
            record for record in records
            if record.get("username") == account.username
            and record.get("image_path")
            and Path(record["image_path"]).is_file()
        ]

        self._show_post_window("My Gallery", records, images_only=True)

    def show_recent_posts(self):
        account = Session.current_account
        if account is None:
            return

        records = getattr(DataStore, "report_records", [])
        records = [
            record for record in records
            if record.get("username") == account.username
        ]

        records.sort(
            key=lambda record: record.get("submitted_at", ""),
            reverse=True
        )

        self._show_post_window("My Recent Posts", records)

    def _show_post_window(self, title, records, images_only=False):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(560, 620)

        outer_layout = QVBoxLayout(dialog)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        if not records:
            content_layout.addWidget(
                QLabel("No posts or images to display yet.")
            )

        for record in records:
            card = QWidget()
            card_layout = QVBoxLayout(card)

            card_layout.addWidget(
                QLabel(
                    f"<b>{record.get('report_type', 'Waste Report')}</b>"
                )
            )

            card_layout.addWidget(
                QLabel(f"Location: {record.get('location', 'Not provided')}")
            )

            card_layout.addWidget(
                QLabel(f"Date: {record.get('submitted_at', 'Unknown')}")
            )

            details = record.get("details", "")
            if details and not images_only:
                description = QLabel(details)
                description.setWordWrap(True)
                card_layout.addWidget(description)

            image_path = record.get("image_path", "")

            if image_path and Path(image_path).is_file():
                pixmap = QPixmap(image_path)

                if not pixmap.isNull():
                    image_label = QLabel()
                    image_label.setPixmap(
                        pixmap.scaled(
                            420,
                            280,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                    )
                    card_layout.addWidget(image_label)

            content_layout.addWidget(card)

            separator = QLabel("—" * 40)
            content_layout.addWidget(separator)

        content_layout.addStretch()
        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        outer_layout.addWidget(close_button)

        dialog.exec()

    def change_password(self):
        account = Session.current_account

        if account is None:
            QMessageBox.warning(self, "Error", "No active account found.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Change Password")
        dialog.setMinimumWidth(350)

        layout = QFormLayout(dialog)

        current_input = QLineEdit()
        current_input.setEchoMode(QLineEdit.EchoMode.Password)

        new_input = QLineEdit()
        new_input.setEchoMode(QLineEdit.EchoMode.Password)

        confirm_input = QLineEdit()
        confirm_input.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addRow("Current Password:", current_input)
        layout.addRow("New Password:", new_input)
        layout.addRow("Confirm New Password:", confirm_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        current_password = current_input.text()
        new_password = new_input.text()
        confirm_password = confirm_input.text()

        if not account.verify_password(current_password):
            QMessageBox.warning(
                self, "Invalid Password",
                "Your current password is incorrect."
            )
            return

        if len(new_password) < 8:
            QMessageBox.warning(
                self, "Invalid Password",
                "The new password must contain at least 8 characters."
            )
            return

        if new_password != confirm_password:
            QMessageBox.warning(
                self, "Password Mismatch",
                "The new passwords do not match."
            )
            return

        account.password_hash, account.salt = hash_password(new_password)

        accounts = load_accounts()

        for index, saved_account in enumerate(accounts):
            if saved_account.username == account.username:
                accounts[index] = account
                break
        else:
            accounts.append(account)

        try:
            save_accounts(accounts)
        except (OSError, ValueError) as error:
            QMessageBox.critical(
                self, "Save Failed",
                f"Unable to save your new password:\n{error}"
            )
            return

        QMessageBox.information(
            self, "Password Changed",
            "Your password has been changed successfully."
        )

    def delete_account(self):
        account = Session.current_account

        if account is None:
            QMessageBox.warning(self, "Error", "No active account found.")
            return

        password, ok = QInputDialog.getText(
            self,
            "Confirm Account Deletion",
            "Enter your current password:",
            QLineEdit.EchoMode.Password
        )

        if not ok:
            return

        if not account.verify_password(password):
            QMessageBox.warning(
                self, "Incorrect Password",
                "Your password is incorrect. The account was not deleted."
            )
            return

        confirmation = QMessageBox.question(
            self,
            "Permanently Delete Account",
            "Are you sure you want to permanently delete your account?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            accounts = load_accounts()
            remaining_accounts = [
                saved_account
                for saved_account in accounts
                if saved_account.username != account.username
            ]

            if len(remaining_accounts) == len(accounts):
                QMessageBox.warning(
                    self, "Account Not Found",
                    "The account could not be found in saved records."
                )
                return

            save_accounts(remaining_accounts)

        except (OSError, ValueError) as error:
            QMessageBox.critical(
                self, "Deletion Failed",
                f"Unable to delete the account:\n{error}"
            )
            return

        for stored_path in (
            account.profile_picture,
            account.valid_id_path,
        ):
            if stored_path:
                try:
                    Path(stored_path).unlink(missing_ok=True)
                except OSError:
                    pass

        Session.logout()

        QMessageBox.information(
            self,
            "Account Deleted",
            "Your account has been deleted. The application will now close."
        )

        QApplication.instance().quit()

    def show_achievements(self):
        QMessageBox.information(
            self,
            "Achievements",
            "Volunteer Achievements\n\n"
            "Your achievements and points will appear here in a future update.\n\n"
            "Planned features:\n"
            "- Volunteer points\n"
            "- Waste reports submitted\n"
            "- Cleanup drives attended\n"
            "- Achievement badges"
        )

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

        # --- HEADER BAR ---
        top_bar = QHBoxLayout()
        
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
        self.page_profile = VolunteerProfilePage()

        self.stack.addWidget(self.page_overview)          # Index 0
        self.stack.addWidget(self.page_waste_reports)     # Index 1
        self.stack.addWidget(self.page_scheduled_drives)  # Index 2
        self.stack.addWidget(self.page_rewards)           # Index 3
        self.stack.addWidget(self.page_announcements)     # Index 4
        self.stack.addWidget(self.page_profile)           # Index 5

        main_layout.addWidget(self.stack, 1)

        # --- CAPSULE PILL BOTTOM NAVIGATION BAR ---
        nav_frame = QFrame()
        nav_frame.setObjectName("bottomNavFrame")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(15, 8, 15, 8)

        self.btn_nav_home = QPushButton("    Home  ")
        self.btn_nav_reports = QPushButton(" Waste\nReports")
        self.btn_nav_drives = QPushButton(" Cleanup\nDrives")
        self.btn_nav_rewards = QPushButton(" Rewards")
        self.btn_nav_announcements = QPushButton(" Notifications")
        self.btn_nav_profile = QPushButton(" View\nProfile")

        self.nav_buttons = [
            (self.btn_nav_home, 0),
            (self.btn_nav_reports, 1),
            (self.btn_nav_drives, 2),
            (self.btn_nav_rewards, 3),
            (self.btn_nav_announcements, 4),
            (self.btn_nav_profile, 5),
        ]

        nav_layout.addStretch()
        for btn, index in self.nav_buttons:
            btn.setObjectName("capsuleNavBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=index: self.switch_tab(idx))
            nav_layout.addWidget(btn)
            nav_layout.addStretch()

        main_layout.addWidget(nav_frame)

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