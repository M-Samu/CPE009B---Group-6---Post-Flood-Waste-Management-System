from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QStackedWidget, QFrame, QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QMessageBox, QComboBox, QSpinBox,
    QSplitter, QScrollArea, QDialog
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
            if getattr(acc, "role", "") == "Volunteer" and getattr(acc, "email", "") and "@" in acc.email
        ]

        if not recipient_emails:
            self.finished_signal.emit(False, "Notification saved, but no volunteer email addresses were found.")
            return

        sender_email = "pfwm.noreply@gmail.com"
        sender_password = "szqldlsbmojlvmor"

        try:
            msg = MIMEMultipart()
            msg["From"] = f"Post-Flood Waste Management <{sender_email}>"
            msg["To"] = ", ".join(recipient_emails)
            msg["Subject"] = f"Announcement: {self.title}"
            msg.attach(MIMEText(self.body, "plain"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_emails, msg.as_string())

            self.finished_signal.emit(True, f"Notification broadcasted and email sent to {len(recipient_emails)} volunteer(s)!")
        except Exception as exc:
            self.finished_signal.emit(False, f"Notification saved, but failed to send email: {str(exc)}")


# REVIEW SUBMITTED WASTE REPORTS PAGE (WITH DETAILS & IMAGE VIEWER)
class AdminWasteReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout_reports = QVBoxLayout(self)

        card_rep = QFrame()
        card_rep.setObjectName("adminCard")
        r_layout = QVBoxLayout(card_rep)

        r_title = QLabel("Review Submitted Waste Reports")
        r_title.setObjectName("pageHeading")
        r_layout.addWidget(r_title)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.admin_reports_list = QListWidget()
        self.admin_reports_list.setObjectName("announcementList")
        self.admin_reports_list.currentRowChanged.connect(self.show_selected_report)

        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)

        detail_heading = QLabel("Report Details")
        detail_heading.setObjectName("pageHeading")
        detail_layout.addWidget(detail_heading)

        self.lbl_report_owner = QLabel("Submitted by: Not selected")
        self.lbl_report_category = QLabel("Category: Not selected")
        self.lbl_report_location = QLabel("Location: Not selected")
        self.lbl_report_date = QLabel("Submitted: Not selected")

        for lbl in (self.lbl_report_owner, self.lbl_report_category, self.lbl_report_location, self.lbl_report_date):
            lbl.setWordWrap(True)
            detail_layout.addWidget(lbl)

        detail_layout.addWidget(QLabel("Description / Details:"))
        self.txt_report_details = QTextEdit()
        self.txt_report_details.setReadOnly(True)
        self.txt_report_details.setMinimumHeight(80)
        detail_layout.addWidget(self.txt_report_details)

        detail_layout.addWidget(QLabel("Attached Image:"))
        self.lbl_report_image = QLabel("No image selected")
        self.lbl_report_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_report_image.setMinimumSize(200, 160)
        self.lbl_report_image.setStyleSheet("""
            QLabel {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background-color: #ffffff;
                color: #64748b;
                padding: 6px;
            }
        """)
        detail_layout.addWidget(self.lbl_report_image)

        detail_layout.addStretch()

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail_scroll.setWidget(detail_panel)

        splitter.addWidget(self.admin_reports_list)
        splitter.addWidget(detail_scroll)
        splitter.setSizes([320, 580])

        r_layout.addWidget(splitter, 1)

        btn_row_rep = QHBoxLayout()
        btn_refresh_rep = QPushButton("Refresh Reports List")
        btn_refresh_rep.setObjectName("secondaryButton")
        btn_refresh_rep.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh_rep.clicked.connect(self.refresh_admin_reports)

        btn_delete_rep = QPushButton("Delete Selected Report")
        btn_delete_rep.setObjectName("secondaryButton")
        btn_delete_rep.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete_rep.clicked.connect(self.handle_delete_report)

        btn_row_rep.addWidget(btn_refresh_rep)
        btn_row_rep.addWidget(btn_delete_rep)

        r_layout.addLayout(btn_row_rep)
        layout_reports.addWidget(card_rep)

    def refresh_admin_reports(self):
        current_row = self.admin_reports_list.currentRow()
        self.admin_reports_list.clear()

        for r in DataStore.waste_reports:
            self.admin_reports_list.addItem(str(r))

        if 0 <= current_row < self.admin_reports_list.count():
            self.admin_reports_list.setCurrentRow(current_row)
        elif self.admin_reports_list.count() > 0:
            self.admin_reports_list.setCurrentRow(0)
        else:
            self.clear_report_details()

    def show_selected_report(self, row: int):
        if row < 0 or row >= len(DataStore.waste_reports):
            self.clear_report_details()
            return

        records = getattr(DataStore, "report_records", [])
        if row < len(records) and isinstance(records[row], dict):
            record = records[row]
            full_name = record.get("full_name", "Unknown")
            username = record.get("username", "Unknown")
            location = record.get("location", "Not provided")
            report_type = record.get("report_type", "Not provided")
            details = record.get("details", "No description provided.")
            submitted_at = record.get("submitted_at", "Unknown date")
            image_path = record.get("image_path", "")

            self.lbl_report_owner.setText(f"Submitted by: {full_name} ({username})")
            self.lbl_report_category.setText(f"Category: {report_type}")
            self.lbl_report_location.setText(f"Location: {location}")
            self.lbl_report_date.setText(f"Submitted: {submitted_at}")
            self.txt_report_details.setPlainText(details)

            if image_path and Path(str(image_path)).is_file():
                pixmap = QPixmap(str(image_path))
                if not pixmap.isNull():
                    self.lbl_report_image.setText("")
                    self.lbl_report_image.setPixmap(
                        pixmap.scaled(
                            380, 240,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                    )
                else:
                    self.lbl_report_image.setPixmap(QPixmap())
                    self.lbl_report_image.setText("Image file corrupted or invalid.")
            else:
                self.lbl_report_image.setPixmap(QPixmap())
                self.lbl_report_image.setText("No attached image for this report.")
        else:
            summary = DataStore.waste_reports[row]
            self.lbl_report_owner.setText("Submitted by: Volunteer")
            self.lbl_report_category.setText("Category: Waste Report")
            self.lbl_report_location.setText(f"Summary: {summary}")
            self.lbl_report_date.setText("Submitted: N/A")
            self.txt_report_details.setPlainText(summary)
            self.lbl_report_image.setPixmap(QPixmap())
            self.lbl_report_image.setText("No image attached.")

    def clear_report_details(self):
        self.lbl_report_owner.setText("Submitted by: Not selected")
        self.lbl_report_category.setText("Category: Not selected")
        self.lbl_report_location.setText("Location: Not selected")
        self.lbl_report_date.setText("Submitted: Not selected")
        self.txt_report_details.clear()
        self.lbl_report_image.setPixmap(QPixmap())
        self.lbl_report_image.setText("No image selected")

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


# MANAGE VOLUNTEER PROFILES PAGE
class AdminManageUsersPage(QWidget):
    def __init__(self, parent=None):
        self.selected_username = None
        super().__init__(parent)
        layout_users = QVBoxLayout(self)

        users_card = QFrame()
        users_card.setObjectName("adminCard")
        users_layout = QVBoxLayout(users_card)

        users_title = QLabel("Manage User's Profile")
        users_title.setObjectName("pageHeading")
        users_layout.addWidget(users_title)

        self.txt_search_user = QLineEdit()
        self.txt_search_user.setPlaceholderText(
            "Search by volunteer name or username..."
        )
        self.txt_search_user.textChanged.connect(
            self.filter_volunteers
        )

        users_layout.addWidget(QLabel("Search Volunteer:"))
        users_layout.addWidget(self.txt_search_user)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.volunteer_list = QListWidget()
        self.volunteer_list.setObjectName("announcementList")
        self.volunteer_list.currentRowChanged.connect(
            self.show_selected_volunteer
        )

        profile_panel = QWidget()
        profile_layout = QVBoxLayout(profile_panel)

        profile_heading = QLabel("Volunteer Information")
        profile_heading.setObjectName("pageHeading")
        profile_layout.addWidget(profile_heading)

        self.lbl_profile_picture = QLabel("No Profile Picture")
        self.lbl_profile_picture.setFixedSize(150, 150)
        self.lbl_profile_picture.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.lbl_profile_picture.setStyleSheet("""
            QLabel {
                border: 2px solid #cccccc;
                border-radius: 75px;
                background-color: #f3f4f6;
                color: #555555;
                padding: 4px;
            }
        """)

        profile_layout.addWidget(
            self.lbl_profile_picture,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.lbl_profile_name = QLabel("Full Name: Not selected")
        self.lbl_profile_username = QLabel("Username: Not selected")
        self.lbl_profile_role = QLabel("Role: Not selected")
        self.lbl_profile_email = QLabel("Email: Not provided")
        self.lbl_profile_phone = QLabel("Phone: Not provided")
        self.lbl_profile_address = QLabel("Address: Not provided")
        self.lbl_profile_points = QLabel("Points: 0")
        self.lbl_profile_created = QLabel("Account Created: Not available")

        profile_labels = [
            self.lbl_profile_name,
            self.lbl_profile_username,
            self.lbl_profile_role,
            self.lbl_profile_email,
            self.lbl_profile_phone,
            self.lbl_profile_address,
            self.lbl_profile_points,
            self.lbl_profile_created,
        ]

        for label in profile_labels:
            label.setWordWrap(True)
            profile_layout.addWidget(label)

        profile_layout.addWidget(QLabel("Award Points:"))

        self.spin_points = QSpinBox()
        self.spin_points.setRange(1, 10000)
        self.spin_points.setValue(50)
        profile_layout.addWidget(self.spin_points)

        self.btn_send_points = QPushButton("Send Points")
        self.btn_send_points.setObjectName("primaryButton")
        self.btn_send_points.clicked.connect(self.handle_send_points)
        profile_layout.addWidget(self.btn_send_points)

        self.btn_delete_user = QPushButton("Delete Volunteer Profile")
        self.btn_delete_user.setObjectName("secondaryButton")
        self.btn_delete_user.clicked.connect(self.handle_delete_user)
        profile_layout.addWidget(self.btn_delete_user)

        self.btn_view_gallery = QPushButton("View Gallery")
        self.btn_view_gallery.setObjectName("secondaryButton")
        self.btn_view_gallery.clicked.connect(
            self.show_selected_volunteer_gallery
        )
        profile_layout.addWidget(self.btn_view_gallery)

        self.btn_view_recent_posts = QPushButton("View Recent Posts")
        self.btn_view_recent_posts.setObjectName("secondaryButton")
        self.btn_view_recent_posts.clicked.connect(
            self.show_selected_volunteer_recent_posts
        )
        profile_layout.addWidget(self.btn_view_recent_posts)

        profile_layout.addStretch()

        profile_scroll = QScrollArea()
        profile_scroll.setWidgetResizable(True)
        profile_scroll.setFrameShape(QFrame.Shape.NoFrame)
        profile_scroll.setWidget(profile_panel)

        splitter.addWidget(self.volunteer_list)
        splitter.addWidget(profile_scroll)
        splitter.setSizes([300, 600])

        users_layout.addWidget(splitter, 1)

        btn_refresh_users = QPushButton("Refresh Volunteer List")
        btn_refresh_users.setObjectName("secondaryButton")
        btn_refresh_users.clicked.connect(self.refresh_volunteer_list)
        users_layout.addWidget(btn_refresh_users)

        layout_users.addWidget(users_card)

    def get_volunteers(self):
        from data_manager import load_accounts
        return [
            account for account in load_accounts()
            if str(getattr(account, "role", "")).casefold() == "volunteer"
        ]

    def get_profile_picture_path(self, account):
        possible_fields = (
            "profile_picture",
            "profile_picture_path",
            "profile_image",
            "profile_image_path",
            "avatar",
            "avatar_path",
            "picture_path",
            "image_path",
        )
        for field in possible_fields:
            value = getattr(account, field, None)
            if not value:
                continue
            path = Path(str(value)).expanduser()
            if path.is_file():
                return path
        return None

    def refresh_volunteer_list(self):
        search_text = self.txt_search_user.text().strip().casefold()
        previous_username = self.selected_username
        self.volunteer_list.clear()

        try:
            volunteers = self.get_volunteers()
        except Exception as error:
            QMessageBox.critical(
                self, "Loading Error", f"Could not load volunteer accounts.\n{error}"
            )
            return

        selected_row = -1

        for account in volunteers:
            full_name = str(getattr(account, "full_name", "") or "")
            username = str(getattr(account, "username", "") or "")

            if (
                search_text
                and search_text not in full_name.casefold()
                and search_text not in username.casefold()
            ):
                continue

            item = QListWidgetItem(f"{full_name} ({username})")
            item.setData(Qt.ItemDataRole.UserRole, username)

            picture_path = self.get_profile_picture_path(account)
            if picture_path:
                pixmap = QPixmap(str(picture_path))
                if not pixmap.isNull():
                    thumbnail = pixmap.scaled(
                        48, 48,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    item.setIcon(QIcon(thumbnail))

            self.volunteer_list.addItem(item)

            if previous_username and username.casefold() == previous_username.casefold():
                selected_row = self.volunteer_list.count() - 1

        if selected_row >= 0:
            self.volunteer_list.setCurrentRow(selected_row)
        elif self.volunteer_list.count() > 0:
            self.volunteer_list.setCurrentRow(0)
        else:
            self.selected_username = None
            self.clear_profile_details()

    def filter_volunteers(self, _text):
        self.refresh_volunteer_list()

    def show_selected_volunteer(self, row: int):
        if row < 0:
            self.selected_username = None
            self.clear_profile_details()
            return

        item = self.volunteer_list.item(row)
        if item is None:
            return

        username = item.data(Qt.ItemDataRole.UserRole)
        if not username:
            return

        from data_manager import find_account

        try:
            account = find_account(username)
        except Exception as error:
            QMessageBox.warning(
                self, "Loading Error", f"Could not load this volunteer's profile.\n{error}"
            )
            return

        if account is None:
            self.selected_username = None
            self.clear_profile_details()
            return

        self.selected_username = account.username

        self.lbl_profile_picture.clear()
        self.lbl_profile_picture.setText("No Profile Picture")

        picture_path = self.get_profile_picture_path(account)
        if picture_path:
            pixmap = QPixmap(str(picture_path))
            if not pixmap.isNull():
                size = min(pixmap.width(), pixmap.height())
                x = (pixmap.width() - size) // 2
                y = (pixmap.height() - size) // 2
                square_pixmap = pixmap.copy(x, y, size, size)
                square_pixmap = square_pixmap.scaled(
                    150, 150,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                circular_pixmap = QPixmap(150, 150)
                circular_pixmap.fill(Qt.GlobalColor.transparent)

                painter = QPainter(circular_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

                circle_path = QPainterPath()
                circle_path.addEllipse(0, 0, 150, 150)

                painter.setClipPath(circle_path)
                painter.drawPixmap(0, 0, square_pixmap)
                painter.end()

                self.lbl_profile_picture.setText("")
                self.lbl_profile_picture.setPixmap(circular_pixmap)

        self.lbl_profile_name.setText(f"Full Name: {getattr(account, 'full_name', 'Not provided')}")
        self.lbl_profile_username.setText(f"Username: {account.username}")
        self.lbl_profile_role.setText(f"Role: {getattr(account, 'role', 'Not available')}")
        self.lbl_profile_email.setText(f"Email: {getattr(account, 'email', '') or 'Not provided'}")
        self.lbl_profile_phone.setText(f"Phone: {getattr(account, 'phone', '') or 'Not provided'}")
        self.lbl_profile_address.setText(f"Address: {getattr(account, 'address', '') or 'Not provided'}")
        self.lbl_profile_points.setText(f"Points: {getattr(account, 'points', 0)}")
        self.lbl_profile_created.setText(f"Account Created: {getattr(account, 'created_at', 'Not available')}")

    def clear_profile_details(self):
        self.lbl_profile_picture.clear()
        self.lbl_profile_picture.setText("No Profile Picture")
        self.lbl_profile_name.setText("Full Name: Not selected")
        self.lbl_profile_username.setText("Username: Not selected")
        self.lbl_profile_role.setText("Role: Not selected")
        self.lbl_profile_email.setText("Email: Not provided")
        self.lbl_profile_phone.setText("Phone: Not provided")
        self.lbl_profile_address.setText("Address: Not provided")
        self.lbl_profile_points.setText("Points: 0")
        self.lbl_profile_created.setText("Account Created: Not available")

    def get_selected_volunteer_records(self):
        username = self.selected_username
        if not username:
            return []
        records = getattr(DataStore, "report_records", [])
        return [
            record for record in records
            if isinstance(record, dict)
            and str(record.get("username", "")).casefold() == username.casefold()
        ]

    def show_selected_volunteer_gallery(self):
        if not self.selected_username:
            QMessageBox.warning(self, "No Volunteer Selected", "Please select a volunteer first.")
            return
        records = self.get_selected_volunteer_records()
        image_records = [
            record for record in records
            if record.get("image_path") and Path(str(record["image_path"])).is_file()
        ]
        self.open_volunteer_posts_dialog("Volunteer Gallery", image_records, images_only=True)

    def show_selected_volunteer_recent_posts(self):
        if not self.selected_username:
            QMessageBox.warning(self, "No Volunteer Selected", "Please select a volunteer first.")
            return
        records = self.get_selected_volunteer_records()
        records.sort(key=lambda record: str(record.get("submitted_at", "")), reverse=True)
        self.open_volunteer_posts_dialog("Volunteer Recent Posts", records, images_only=False)

    def open_volunteer_posts_dialog(self, title, records, images_only=False):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(600, 650)
        layout = QVBoxLayout(dialog)

        heading = QLabel(f"{title} — {self.selected_username}")
        heading.setObjectName("pageHeading")
        layout.addWidget(heading)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        if not records:
            message = "No gallery images are available." if images_only else "This volunteer has no recorded posts."
            empty_label = QLabel(message)
            empty_label.setWordWrap(True)
            content_layout.addWidget(empty_label)

        for record in records:
            card = QFrame()
            card.setObjectName("adminCard")
            card_layout = QVBoxLayout(card)

            post_heading = QLabel(str(record.get("report_type", "Waste Report")))
            post_heading.setStyleSheet("font-weight: bold; font-size: 14px;")
            post_heading.setWordWrap(True)
            card_layout.addWidget(post_heading)

            location_label = QLabel(f"Location: {record.get('location', 'Not provided')}")
            location_label.setWordWrap(True)
            card_layout.addWidget(location_label)

            date_label = QLabel(f"Submitted: {record.get('submitted_at', 'Unknown')}")
            date_label.setWordWrap(True)
            card_layout.addWidget(date_label)

            details = str(record.get("details", "") or "")
            if details and not images_only:
                details_label = QLabel(details)
                details_label.setWordWrap(True)
                card_layout.addWidget(details_label)

            image_path = record.get("image_path", "")
            if image_path:
                image_file = Path(str(image_path))
                if image_file.is_file():
                    pixmap = QPixmap(str(image_file))
                    if not pixmap.isNull():
                        image_label = QLabel()
                        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        image_label.setPixmap(
                            pixmap.scaled(
                                460, 300,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation
                            )
                        )
                        card_layout.addWidget(image_label)

            content_layout.addWidget(card)

        content_layout.addStretch()
        scroll_area.setWidget(content)
        layout.addWidget(scroll_area)

        close_button = QPushButton("Close")
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()

    def handle_send_points(self):
        if not self.selected_username:
            QMessageBox.warning(self, "Selection Error", "Please select a volunteer first.")
            return

        from data_manager import award_volunteer_points
        points = self.spin_points.value()

        reply = QMessageBox.question(
            self, "Confirm Points",
            f"Send {points} points to {self.selected_username}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            success, message = award_volunteer_points(self.selected_username, points)
        except Exception as error:
            QMessageBox.critical(self, "Points Error", f"Could not award points.\n{error}")
            return

        if success:
            QMessageBox.information(self, "Success", message)
            self.show_selected_volunteer(self.volunteer_list.currentRow())
        else:
            QMessageBox.warning(self, "Error", message)

    def handle_delete_user(self):
        if not self.selected_username:
            QMessageBox.warning(self, "Selection Error", "Please select a volunteer to delete.")
            return

        username = self.selected_username
        reply = QMessageBox.question(
            self, "Confirm Profile Deletion",
            f"Are you sure you want to delete the profile for '{username}'?\n\n"
            "This removes the volunteer's account. This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from data_manager import load_accounts, save_accounts

        try:
            accounts = load_accounts()
            updated_accounts = [
                account for account in accounts
                if not (
                    account.username.casefold() == username.casefold()
                    and account.role.casefold() == "volunteer"
                )
            ]
            if len(updated_accounts) == len(accounts):
                QMessageBox.warning(self, "Not Found", "The volunteer account was not found.")
                self.refresh_volunteer_list()
                return

            save_accounts(updated_accounts)
        except Exception as error:
            QMessageBox.critical(self, "Deletion Error", f"Could not delete the volunteer account.\n{error}")
            return

        self.selected_username = None
        self.refresh_volunteer_list()
        QMessageBox.information(self, "Success", f"The profile for '{username}' was deleted.")


# MAIN ADMIN DASHBOARD CLASS
class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Mcontainer")
        self.setWindowTitle("Admin Dashboard | Post-Flood Waste Management")

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
        self.txt_n_heading.setPlaceholderText("e.g. Emergency Flood Advisory")

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
        self.page_reports = AdminWasteReportsPage(self)

        # Page 3: Create Cleanup Schedule
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

        # Page 5: Manage Volunteer Profiles
        self.page_users = AdminManageUsersPage(self)

        # Add pages to stack
        self.stack.addWidget(page_tasks)          # 0
        self.stack.addWidget(page_notif)          # 1
        self.stack.addWidget(self.page_reports)   # 2
        self.stack.addWidget(page_schedules)      # 3
        self.stack.addWidget(page_claims)         # 4
        self.stack.addWidget(self.page_users)     # 5

        main_layout.addWidget(self.stack, 1)

        # Capsule Admin Nav Bar
        nav_frame = QFrame()
        nav_frame.setObjectName("bottomNavFrame")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(15, 8, 15, 8)

        self.btn_a_tasks = QPushButton("Create\nTask")
        self.btn_a_notif = QPushButton("Send\nNotifications")
        self.btn_a_reports = QPushButton("Review\nReports")
        self.btn_a_schedules = QPushButton("Cleanup\nSchedules")
        self.btn_a_claims = QPushButton("Reward\nClaims")
        self.btn_a_users = QPushButton("Manage\nProfiles") 

        self.admin_nav_buttons = [
            (self.btn_a_tasks, 0),
            (self.btn_a_notif, 1),
            (self.btn_a_reports, 2),
            (self.btn_a_schedules, 3),
            (self.btn_a_claims, 4),
            (self.btn_a_users, 5)
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
            self.page_reports.refresh_admin_reports()
        elif index == 3:
            self.refresh_schedules_list()
        elif index == 4:
            self.refresh_reward_claims_list()
        elif index == 5:
            self.page_users.refresh_volunteer_list()

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

        notif_title = f"Reward Update: {claim['item_name']}"
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

    def logout(self):
        from login_window import LoginWindow
        Session.logout()
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()