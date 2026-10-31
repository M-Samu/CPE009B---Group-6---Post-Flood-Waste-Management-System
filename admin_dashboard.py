from pathlib import Path
from datetime import datetime
import uuid
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QMessageBox, QComboBox, QSpinBox,
    QSplitter, QScrollArea, QDialog, QTabWidget, QAbstractItemView
)

from waste_management_models import Session
from data_store import DataStore
from data_manager import award_volunteer_points

def _load_smtp_settings():
    """
    Read SMTP_LOGIN and SMTP_PASSWORD from the process environment or a .env
    file beside this script. Credentials are never hard-coded in the source.
    Existing environment variables take precedence over .env values.
    """
    env_path = Path(__file__).resolve().with_name(".env")
    if env_path.is_file():
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("\\\"").strip("'")
                if key in ("SMTP_LOGIN", "SMTP_PASSWORD") and not os.getenv(key):
                    os.environ[key] = value
        except OSError:
            # Environment variables can still be used if .env cannot be read.
            pass

    return (
        os.getenv("SMTP_LOGIN", "").strip(),
        os.getenv("SMTP_PASSWORD", "").strip(),
    )

class EmailAnnouncementThread(QThread):
    # Send volunteer announcement emails without blocking the GUI.
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, title, body, parent=None):
        super().__init__(parent)
        self.title = title
        self.body = body

    def run(self):
        from data_manager import load_accounts
        sender_email, sender_password = _load_smtp_settings()
        if not sender_email or not sender_password:
            self.finished_signal.emit(
                False,
                "Announcement saved in the app, but email settings are missing. "
                "Create a .env file beside admin_dashboard.py with "
                "SMTP_LOGIN=your-gmail-address and SMTP_PASSWORD=your-gmail-app-password, "
                "or set those environment variables before launching the app."
            )
            return

        try:
            accounts = load_accounts()
            recipients = sorted({
                acc.email.strip() for acc in accounts
                if getattr(acc, "role", "") == "Volunteer"
                and getattr(acc, "email", "").strip()
                and "@" in acc.email
            })
            if not recipients:
                self.finished_signal.emit(
                    False, "Announcement saved in the app, but no volunteer email addresses were found."
                )
                return

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
                server.login(sender_email, sender_password)
                sent = 0
                failures = 0
                for recipient in recipients:
                    msg = MIMEMultipart()
                    msg["From"] = f"Post-Flood Waste Management <{sender_email}>"
                    msg["To"] = recipient
                    msg["Subject"] = f"Announcement: {self.title}"
                    msg.attach(MIMEText(self.body, "plain", "utf-8"))
                    try:
                        server.sendmail(sender_email, [recipient], msg.as_string())
                        sent += 1
                    except Exception:
                        failures += 1

            if failures:
                self.finished_signal.emit(
                    False, f"Announcement saved. Email sent to {sent} volunteer(s); {failures} delivery attempt(s) failed."
                )
            else:
                self.finished_signal.emit(
                    True, f"Announcement saved and email sent to {sent} volunteer(s)."
                )
        except Exception as exc:
            self.finished_signal.emit(
                False, f"Announcement saved in the app, but email delivery failed: {exc}"
            )

class AdminCreateTaskPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout_tasks = QVBoxLayout(self)

        card_tasks = QFrame()
        card_tasks.setObjectName("adminCard")
        t_layout = QVBoxLayout(card_tasks)

        t_title = QLabel("Create Volunteer Task")
        t_title.setObjectName("pageHeading")

        self.txt_task_desc = QLineEdit()
        self.txt_task_desc.setPlaceholderText(
            "e.g. Segregate plastic waste at District 2"
        )

        btn_add_task = QPushButton("Publish Task to Volunteers")
        btn_add_task.setObjectName("primaryButton")
        btn_add_task.clicked.connect(self.handle_add_task)

        t_layout.addWidget(t_title)
        t_layout.addWidget(
            QLabel("Task Description / Assignment:")
        )
        t_layout.addWidget(self.txt_task_desc)
        t_layout.addWidget(btn_add_task)
        t_layout.addStretch()

        layout_tasks.addWidget(card_tasks)

    def handle_add_task(self):
        task_text = self.txt_task_desc.text().strip()

        if not task_text:
            QMessageBox.warning(
                self, "Input Error",
                "Task description cannot be empty."
            )
            return

        DataStore.tasks.append(f"Task: {task_text}")

        try:
            DataStore.save()
        except Exception as error:
            DataStore.tasks.pop()
            QMessageBox.critical(
                self, "Save Error",
                f"Could not publish the task.\n{error}"
            )
            return

        self.txt_task_desc.clear()

        QMessageBox.information(
            self, "Success",
            "Task successfully assigned to volunteers!"
        )

class AdminNotificationsPage(QWidget):
    """Create email/dashboard announcements and manage previously sent notifications."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        send_page = QWidget()
        send_layout = QVBoxLayout(send_page)
        card = QFrame()
        card.setObjectName("adminCard")
        card_layout = QVBoxLayout(card)
        heading = QLabel("Send Notification / Announcement")
        heading.setObjectName("pageHeading")
        self.txt_n_heading = QLineEdit()
        self.txt_n_heading.setPlaceholderText("e.g. Emergency Flood Advisory")
        self.txt_n_body = QTextEdit()
        self.txt_n_body.setPlaceholderText("Enter the announcement details...")
        self.btn_send_notif = QPushButton("Send Notification to All Volunteers")
        self.btn_send_notif.setObjectName("primaryButton")
        self.btn_send_notif.clicked.connect(self.handle_send_notification)
        card_layout.addWidget(heading)
        card_layout.addWidget(QLabel("Announcement Title:"))
        card_layout.addWidget(self.txt_n_heading)
        card_layout.addWidget(QLabel("Announcement Body:"))
        card_layout.addWidget(self.txt_n_body)
        card_layout.addWidget(self.btn_send_notif)
        send_layout.addWidget(card)
        send_layout.addStretch(1)

        manage_page = QWidget()
        manage_layout = QVBoxLayout(manage_page)
        header = QHBoxLayout()
        manage_title = QLabel("My Notifications")
        manage_title.setObjectName("pageHeading")
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_my_notifications)
        header.addWidget(manage_title)
        header.addStretch()
        header.addWidget(refresh_button)
        manage_layout.addLayout(header)
        manage_layout.addWidget(QLabel(
            "Edit or delete saved dashboard notifications. Changes cannot retract emails already delivered."
        ))
        self.my_notifications_list = QListWidget()
        self.my_notifications_list.setObjectName("adminListWidget")
        manage_layout.addWidget(self.my_notifications_list, 1)

        self.tabs.addTab(send_page, "Send Notification")
        self.tabs.addTab(manage_page, "My Notifications")
        self.tabs.currentChanged.connect(
            lambda index: self.refresh_my_notifications() if index == 1 else None
        )
        layout.addWidget(self.tabs)
        self.refresh_my_notifications()

    def _current_admin_username(self):
        account = Session.current_account
        return str(getattr(account, "username", "admin")) if account else "admin"

    def handle_send_notification(self):
        title = self.txt_n_heading.text().strip()
        body = self.txt_n_body.toPlainText().strip()
        if not title or not body:
            QMessageBox.warning(self, "Input Error", "Please fill in both title and body.")
            return

        from data_manager import load_accounts
        accounts = load_accounts()
        recipients = sorted({
            str(getattr(account, "username", "")).strip()
            for account in accounts
            if getattr(account, "role", "") == "Volunteer"
            and str(getattr(account, "username", "")).strip()
        })
        if not recipients:
            QMessageBox.warning(self, "No Recipients", "No volunteer accounts were found.")
            return

        record = {
            "id": uuid.uuid4().hex,
            "title": title,
            "body": body,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "created_by": self._current_admin_username(),
            "recipients": recipients,
            "type": "admin_announcement",
        }
        DataStore.notification_records.insert(0, record)
        try:
            DataStore.save()
        except Exception as error:
            DataStore.notification_records.remove(record)
            QMessageBox.critical(self, "Save Error", f"Could not save the notification.\n{error}")
            return

        self.txt_n_heading.clear()
        self.txt_n_body.clear()
        self.btn_send_notif.setEnabled(False)
        self.btn_send_notif.setText("Sending Email...")
        self.refresh_my_notifications()
        self.email_thread = EmailAnnouncementThread(title, body, self)
        self.email_thread.finished_signal.connect(self._on_announcement_emails_sent)
        self.email_thread.start()

    def _on_announcement_emails_sent(self, success, message):
        self.btn_send_notif.setEnabled(True)
        self.btn_send_notif.setText("Send Notification to All Volunteers")
        if success:
            QMessageBox.information(self, "Email Announcement", message)
        else:
            QMessageBox.warning(
                self, "Email Announcement",
                message + "\n\nThe notification is saved in the dashboard even if email delivery failed."
            )

    def refresh_my_notifications(self):
        if not hasattr(self, "my_notifications_list"):
            return
        self.my_notifications_list.clear()
        username = self._current_admin_username()
        entries = []
        for record in DataStore.notification_records:
            if (isinstance(record, dict)
                    and record.get("type") == "admin_announcement"
                    and str(record.get("created_by", "admin")).casefold() == username.casefold()):
                entries.append(("record", record))
        # Existing releases stored notifications as tuples. Keep them manageable too.
        for old_item in DataStore.announcements:
            if isinstance(old_item, (list, tuple)) and len(old_item) >= 2:
                entries.append(("legacy", (str(old_item[0]), str(old_item[1]))))

        for entry_type, payload in entries:
            if entry_type == "record":
                title = str(payload.get("title", "Untitled notification"))
                body = str(payload.get("body", ""))
                key = payload.get("id")
                date_text = str(payload.get("created_at", ""))
            else:
                title, body = payload
                key = ("legacy", title, body)
                date_text = "Previously saved notification"

            item = QListWidgetItem()
            card = QWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)
            title_label = QLabel(title)
            title_label.setStyleSheet("font-weight: bold;")
            preview = QLabel(body[:160] + ("..." if len(body) > 160 else ""))
            preview.setWordWrap(True)
            date_label = QLabel(date_text)
            date_label.setStyleSheet("color: #64748b; font-size: 11px;")
            buttons = QHBoxLayout()
            edit_button = QPushButton("Edit")
            delete_button = QPushButton("Delete")
            edit_button.clicked.connect(lambda checked=False, k=key: self.edit_notification(k))
            delete_button.clicked.connect(lambda checked=False, k=key: self.delete_notification(k))
            buttons.addWidget(edit_button)
            buttons.addWidget(delete_button)
            buttons.addStretch()
            card_layout.addWidget(title_label)
            card_layout.addWidget(preview)
            card_layout.addWidget(date_label)
            card_layout.addLayout(buttons)
            item.setSizeHint(card.sizeHint())
            self.my_notifications_list.addItem(item)
            self.my_notifications_list.setItemWidget(item, card)

        if not entries:
            self.my_notifications_list.addItem("You have not sent any notifications yet.")

    def edit_notification(self, notification_id):
        is_legacy = isinstance(notification_id, tuple) and notification_id and notification_id[0] == "legacy"
        if is_legacy:
            old_title, old_body = notification_id[1], notification_id[2]
            record = None
        else:
            old_title = old_body = ""
            record = next(
                (item for item in DataStore.notification_records
                 if isinstance(item, dict) and item.get("id") == notification_id),
                None
            )
            if record is None:
                QMessageBox.warning(self, "Not Found", "This notification no longer exists.")
                self.refresh_my_notifications()
                return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Notification")
        dialog.resize(500, 400)
        layout = QVBoxLayout(dialog)
        title_input = QLineEdit(old_title if is_legacy else str(record.get("title", "")))
        body_input = QTextEdit()
        body_input.setPlainText(old_body if is_legacy else str(record.get("body", "")))
        layout.addWidget(QLabel("Notification title"))
        layout.addWidget(title_input)
        layout.addWidget(QLabel("Notification body"))
        layout.addWidget(body_input, 1)
        buttons = QHBoxLayout()
        save_button = QPushButton("Save Changes")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        title = title_input.text().strip()
        body = body_input.toPlainText().strip()
        if not title or not body:
            QMessageBox.warning(self, "Input Error", "Title and body cannot be empty.")
            return

        if is_legacy:
            old_pair = (old_title, old_body)
            try:
                index = DataStore.announcements.index(old_pair)
            except ValueError:
                QMessageBox.warning(self, "Not Found", "This notification no longer exists.")
                self.refresh_my_notifications()
                return
            DataStore.announcements[index] = (title, body)
            rollback = lambda: DataStore.announcements.__setitem__(index, old_pair)
        else:
            old_record = dict(record)
            record["title"], record["body"] = title, body
            record["updated_at"] = datetime.now().isoformat(timespec="seconds")
            rollback = lambda: (record.clear(), record.update(old_record))
        try:
            DataStore.save()
        except Exception as error:
            rollback()
            QMessageBox.critical(self, "Save Error", f"Could not update notification.\n{error}")
            return

        self.refresh_my_notifications()
        QMessageBox.information(
            self, "Notification Updated",
            "The dashboard notification was updated. Emails already delivered cannot be changed."
        )

    def delete_notification(self, notification_id):
        is_legacy = isinstance(notification_id, tuple) and notification_id and notification_id[0] == "legacy"
        if is_legacy:
            record = (notification_id[1], notification_id[2])
            target_list = DataStore.announcements
        else:
            record = next(
                (item for item in DataStore.notification_records
                 if isinstance(item, dict) and item.get("id") == notification_id),
                None
            )
            target_list = DataStore.notification_records
        if record is None or record not in target_list:
            self.refresh_my_notifications()
            return

        reply = QMessageBox.question(
            self, "Delete Notification",
            "Delete this notification from recipients' dashboard history? Previously delivered emails will remain in their inboxes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        index = target_list.index(record)
        target_list.remove(record)
        try:
            DataStore.save()
        except Exception as error:
            target_list.insert(index, record)
            QMessageBox.critical(self, "Save Error", f"Could not delete notification.\n{error}")
            return
        self.refresh_my_notifications()

class AdminWasteReportsPage(QWidget):
    def __init__(self, parent=None):
        self.selected_report_index = None
        super().__init__(parent)
        layout_reports = QVBoxLayout(self)

        card_reports = QFrame()
        card_reports.setObjectName("adminCard")
        r_layout = QVBoxLayout(card_reports)

        r_title = QLabel("Review Submitted Waste Reports")
        r_title.setObjectName("pageHeading")
        r_layout.addWidget(r_title)

        report_splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        self.admin_reports_list = QListWidget()
        self.admin_reports_list.setObjectName("announcementList")
        self.admin_reports_list.currentItemChanged.connect(
            self.show_selected_report
        )

        report_detail_panel = QWidget()
        report_detail_layout = QVBoxLayout(report_detail_panel)

        report_detail_title = QLabel("Report Details")
        report_detail_title.setObjectName("pageHeading")
        report_detail_layout.addWidget(report_detail_title)

        self.lbl_report_status = QLabel("Status: Not selected")
        self.lbl_report_owner = QLabel("Submitted by: Not selected")
        self.lbl_report_location = QLabel("Location: Not available")
        self.lbl_report_category = QLabel("Category: Not available")
        self.lbl_report_date = QLabel("Submitted: Not available")

        for label in (
            self.lbl_report_status,
            self.lbl_report_owner,
            self.lbl_report_location,
            self.lbl_report_category,
            self.lbl_report_date,
        ):
            label.setWordWrap(True)
            report_detail_layout.addWidget(label)

        report_detail_layout.addWidget(
            QLabel("Report Description:")
        )

        self.txt_report_details = QTextEdit()
        self.txt_report_details.setReadOnly(True)
        self.txt_report_details.setMinimumHeight(75)
        report_detail_layout.addWidget(self.txt_report_details)

        report_detail_layout.addWidget(
            QLabel("Attached Image:")
        )

        self.lbl_report_image = QLabel(
            "No image selected."
        )
        self.lbl_report_image.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.lbl_report_image.setMinimumSize(180, 130)
        self.lbl_report_image.setMaximumHeight(220)
        self.lbl_report_image.setWordWrap(True)
        report_detail_layout.addWidget(self.lbl_report_image)

        report_detail_layout.addWidget(
            QLabel("Administrator's Note:")
        )

        self.txt_report_admin_note = QTextEdit()
        self.txt_report_admin_note.setPlaceholderText(
            "Add feedback or explain the decision..."
        )
        self.txt_report_admin_note.setMaximumHeight(75)
        report_detail_layout.addWidget(
            self.txt_report_admin_note
        )

        moderation_buttons = QHBoxLayout()

        self.btn_approve_report = QPushButton(
            "Approve Report"
        )
        self.btn_approve_report.setObjectName("primaryButton")
        self.btn_approve_report.clicked.connect(
            lambda: self.handle_moderate_report("Approved")
        )

        self.btn_reject_report = QPushButton(
            "Reject Report"
        )
        self.btn_reject_report.setObjectName("secondaryButton")
        self.btn_reject_report.clicked.connect(
            lambda: self.handle_moderate_report("Rejected")
        )

        moderation_buttons.addWidget(self.btn_approve_report)
        moderation_buttons.addWidget(self.btn_reject_report)
        self.btn_award_report_points = QPushButton("Award 10 Points")
        self.btn_award_report_points.setObjectName("primaryButton")
        self.btn_award_report_points.clicked.connect(self.handle_award_report_points)
        moderation_buttons.addWidget(self.btn_award_report_points)
        report_detail_layout.addLayout(moderation_buttons)

        report_buttons = QHBoxLayout()

        btn_refresh_rep = QPushButton("Refresh Reports")
        btn_refresh_rep.setObjectName("secondaryButton")
        btn_refresh_rep.clicked.connect(
            self.refresh_admin_reports
        )

        btn_delete_rep = QPushButton("Delete Selected Report")
        btn_delete_rep.setObjectName("secondaryButton")
        btn_delete_rep.clicked.connect(
            self.handle_delete_report
        )

        report_buttons.addWidget(btn_refresh_rep)
        report_buttons.addWidget(btn_delete_rep)

        report_detail_layout.addLayout(report_buttons)

        report_splitter.addWidget(self.admin_reports_list)
        report_splitter.addWidget(report_detail_panel)
        report_splitter.setSizes([320, 650])

        r_layout.addWidget(report_splitter)
        layout_reports.addWidget(card_reports)

    def refresh_admin_reports(self):
        previous_index = self.selected_report_index

        self.admin_reports_list.clear()
        DataStore._synchronize_report_moderation()

        for index, report in enumerate(DataStore.waste_reports):
            moderation = DataStore.get_report_moderation(index)
            status = moderation.get("status", "Pending")

            item = QListWidgetItem(
                f"[{status}] {str(report)}"
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                index
            )
            self.admin_reports_list.addItem(item)

        target_row = -1

        for row in range(self.admin_reports_list.count()):
            item = self.admin_reports_list.item(row)

            if item.data(Qt.ItemDataRole.UserRole) == previous_index:
                target_row = row
                break

        if target_row >= 0:
            self.admin_reports_list.setCurrentRow(target_row)
        elif self.admin_reports_list.count() > 0:
            self.admin_reports_list.setCurrentRow(0)
        else:
            self.selected_report_index = None
            self.clear_report_details()

    def show_selected_report(self, current, _previous=None):
        if current is None:
            self.selected_report_index = None
            self.clear_report_details()
            return

        report_index = current.data(
            Qt.ItemDataRole.UserRole
        )

        if (
            not isinstance(report_index, int)
            or not 0 <= report_index < len(DataStore.waste_reports)
        ):
            self.selected_report_index = None
            self.clear_report_details()
            return

        self.selected_report_index = report_index
        report = DataStore.waste_reports[report_index]

        record = {}
        if report_index < len(DataStore.report_records):
            candidate = DataStore.report_records[report_index]
            if isinstance(candidate, dict):
                record = candidate

        moderation = DataStore.get_report_moderation(
            report_index
        ) or {}

        self.lbl_report_status.setText(
            f"Status: {moderation.get('status', 'Pending')}"
        )
        self.lbl_report_owner.setText(
            f"Submitted by: "
            f"{record.get('full_name', 'Unknown')} "
            f"({record.get('username', 'Unknown')})"
        )
        self.lbl_report_location.setText(
            f"Location: {record.get('location', 'Not available')}"
        )
        self.lbl_report_category.setText(
            f"Category: {record.get('report_type', 'Not available')}"
        )
        self.lbl_report_date.setText(
            f"Submitted: {record.get('submitted_at', 'Not available')}"
        )
        self.txt_report_details.setPlainText(
            record.get('details', '')
        )
        self.txt_report_admin_note.setPlainText(
            moderation.get('admin_note', '')
        )

        self.show_report_image(record.get('image_path', ''))

        has_selection = True
        self.btn_approve_report.setEnabled(has_selection)
        self.btn_reject_report.setEnabled(has_selection)
        self.btn_award_report_points.setEnabled(has_selection and moderation.get("status") == "Approved" and not moderation.get("points_awarded", False))

    def show_report_image(self, image_path):
        self.lbl_report_image.clear()

        if not image_path:
            self.lbl_report_image.setText(
                "No image was attached to this report."
            )
            return

        path = Path(image_path)

        if not path.is_file():
            self.lbl_report_image.setText(
                f"Image file not found:\n{image_path}"
            )
            return

        pixmap = QPixmap(str(path))

        if pixmap.isNull():
            self.lbl_report_image.setText(
                "The attached file could not be displayed."
            )
            return

        self.lbl_report_image.setPixmap(
            pixmap.scaled(
                420,
                210,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def clear_report_details(self):
        self.lbl_report_status.setText("Status: Not selected")
        self.lbl_report_owner.setText(
            "Submitted by: Not selected"
        )
        self.lbl_report_location.setText(
            "Location: Not available"
        )
        self.lbl_report_category.setText(
            "Category: Not available"
        )
        self.lbl_report_date.setText(
            "Submitted: Not available"
        )
        self.txt_report_details.clear()
        self.txt_report_admin_note.clear()
        self.lbl_report_image.setPixmap(QPixmap())
        self.lbl_report_image.setText("No image selected.")
        self.btn_approve_report.setEnabled(False)
        self.btn_reject_report.setEnabled(False)
        if hasattr(self, "btn_award_report_points"):
            self.btn_award_report_points.setEnabled(False)

    def handle_moderate_report(self, status):
        index = self.selected_report_index

        if (
            index is None
            or not 0 <= index < len(DataStore.waste_reports)
        ):
            QMessageBox.warning(
                self, "Selection Error",
                "Please select a report first."
            )
            return

        note = self.txt_report_admin_note.toPlainText().strip()

        try:
            DataStore.update_report_moderation(
                index,
                status,
                note
            )
        except Exception as error:
            QMessageBox.critical(
                self, "Update Error",
                f"Could not update the report status.\n{error}"
            )
            return

        self.refresh_admin_reports()

        QMessageBox.information(
            self,
            "Report Updated",
            f"The report has been marked as {status}."
        )

    def handle_award_report_points(self):
        index = self.selected_report_index
        if index is None or not 0 <= index < len(DataStore.waste_reports):
            QMessageBox.warning(self, "Selection Error", "Select a report first.")
            return
        moderation = DataStore.get_report_moderation(index) or {}
        if moderation.get("status") != "Approved":
            QMessageBox.warning(self, "Report Not Verified", "Approve the waste report before awarding points.")
            return
        if moderation.get("points_awarded", False):
            QMessageBox.information(self, "Already Awarded", "Points have already been awarded for this report.")
            return
        record = DataStore.report_records[index] if index < len(DataStore.report_records) else {}
        username = record.get("username", "") if isinstance(record, dict) else ""
        if not username:
            QMessageBox.warning(self, "Missing User", "The report does not identify its volunteer.")
            return
        answer = QMessageBox.question(self, "Award Points", f"Award 10 points to @{username} for this verified waste report?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        ok, message = award_volunteer_points(username, 10)
        if not ok:
            QMessageBox.warning(self, "Points Not Awarded", message)
            return
        moderation["points_awarded"] = True
        DataStore.save()
        QMessageBox.information(self, "Points Awarded", message)

    def handle_delete_report(self):
        index = self.selected_report_index

        if (
            index is None
            or not 0 <= index < len(DataStore.waste_reports)
        ):
            QMessageBox.warning(
                self, "Selection Error",
                "Please select a waste report to delete."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this waste report?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            DataStore.delete_report(index)
        except Exception as error:
            QMessageBox.critical(
                self, "Deletion Error",
                f"Could not delete the report.\n{error}"
            )
            return

        self.selected_report_index = None
        self.refresh_admin_reports()

        QMessageBox.information(
            self, "Success",
            "Waste report deleted successfully."
        )

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

        self.lbl_profile_name = QLabel(
            "Full Name: Not selected"
        )
        self.lbl_profile_username = QLabel(
            "Username: Not selected"
        )
        self.lbl_profile_role = QLabel(
            "Role: Not selected"
        )
        self.lbl_profile_email = QLabel(
            "Email: Not provided"
        )
        self.lbl_profile_phone = QLabel(
            "Phone: Not provided"
        )
        self.lbl_profile_address = QLabel(
            "Address: Not provided"
        )
        self.lbl_profile_points = QLabel("Points: 0")
        self.lbl_profile_created = QLabel(
            "Account Created: Not available"
        )

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
        self.btn_send_points.clicked.connect(
            self.handle_send_points
        )
        profile_layout.addWidget(self.btn_send_points)

        self.btn_delete_user = QPushButton(
            "Delete Volunteer Profile"
        )
        self.btn_delete_user.setObjectName("secondaryButton")
        self.btn_delete_user.clicked.connect(
            self.handle_delete_user
        )
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

        splitter.addWidget(self.volunteer_list)
        splitter.addWidget(profile_panel)
        splitter.setSizes([300, 600])

        users_layout.addWidget(splitter, 1)

        btn_refresh_users = QPushButton(
            "Refresh Volunteer List"
        )
        btn_refresh_users.setObjectName("secondaryButton")
        btn_refresh_users.clicked.connect(
            self.refresh_volunteer_list
        )
        users_layout.addWidget(btn_refresh_users)

        layout_users.addWidget(users_card)


    def get_volunteers(self):
        from data_manager import load_accounts

        return [
            account for account in load_accounts()
            if str(getattr(account, "role", "")).casefold()
            == "volunteer"
        ]

    def get_profile_picture_path(self, account):
        """
        Return the profile picture path if the account has one.

        The helper checks common attribute names because the exact
        field name depends on how the account model stores pictures.
        """
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
        search_text = (
            self.txt_search_user.text().strip().casefold()
        )
        previous_username = self.selected_username

        self.volunteer_list.clear()

        try:
            volunteers = self.get_volunteers()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Loading Error",
                f"Could not load volunteer accounts.\n{error}"
            )
            return

        selected_row = -1

        for account in volunteers:
            full_name = str(
                getattr(account, "full_name", "") or ""
            )
            username = str(
                getattr(account, "username", "") or ""
            )

            if (
                search_text
                and search_text not in full_name.casefold()
                and search_text not in username.casefold()
            ):
                continue

            item = QListWidgetItem(
                f"{full_name} ({username})"
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                username
            )

            # Show a small profile picture beside the volunteer.
            picture_path = self.get_profile_picture_path(account)

            if picture_path:
                pixmap = QPixmap(str(picture_path))

                if not pixmap.isNull():
                    thumbnail = pixmap.scaled(
                        48,
                        48,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    item.setIcon(QIcon(thumbnail))

            self.volunteer_list.addItem(item)

            if (
                previous_username
                and username.casefold()
                == previous_username.casefold()
            ):
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
                self,
                "Loading Error",
                f"Could not load this volunteer's profile.\n{error}"
            )
            return

        if account is None:
            self.selected_username = None
            self.clear_profile_details()
            return

        self.selected_username = account.username

        
        # Display the volunteer's profile picture as a circle.
        self.lbl_profile_picture.clear()
        self.lbl_profile_picture.setText("No Profile Picture")

        picture_path = self.get_profile_picture_path(account)

        if picture_path:
            pixmap = QPixmap(str(picture_path))

            if not pixmap.isNull():
                # Crop the image into a centered square first.
                size = min(pixmap.width(), pixmap.height())

                x = (pixmap.width() - size) // 2
                y = (pixmap.height() - size) // 2

                square_pixmap = pixmap.copy(
                    x, y, size, size
                )

                # Scale the square image to the label size.
                square_pixmap = square_pixmap.scaled(
                    150,
                    150,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                # Create a transparent canvas.
                circular_pixmap = QPixmap(150, 150)
                circular_pixmap.fill(Qt.GlobalColor.transparent)

                # Clip the image to a circular shape.
                painter = QPainter(circular_pixmap)
                painter.setRenderHint(
                    QPainter.RenderHint.Antialiasing
                )
                painter.setRenderHint(
                    QPainter.RenderHint.SmoothPixmapTransform
                )

                circle_path = QPainterPath()
                circle_path.addEllipse(0, 0, 150, 150)

                painter.setClipPath(circle_path)
                painter.drawPixmap(0, 0, square_pixmap)
                painter.end()

                # Display the circular image.
                self.lbl_profile_picture.setText("")
                self.lbl_profile_picture.setPixmap(
                    circular_pixmap
                )

        self.lbl_profile_name.setText(
            f"Full Name: "
            f"{getattr(account, 'full_name', 'Not provided')}"
        )

        self.lbl_profile_username.setText(
            f"Username: {account.username}"
        )

        self.lbl_profile_role.setText(
            f"Role: {getattr(account, 'role', 'Not available')}"
        )

        self.lbl_profile_email.setText(
            f"Email: "
            f"{getattr(account, 'email', '') or 'Not provided'}"
        )

        self.lbl_profile_phone.setText(
            f"Phone: "
            f"{getattr(account, 'phone', '') or 'Not provided'}"
        )

        self.lbl_profile_address.setText(
            f"Address: "
            f"{getattr(account, 'address', '') or 'Not provided'}"
        )

        self.lbl_profile_points.setText(
            f"Points: {getattr(account, 'points', 0)}"
        )

        self.lbl_profile_created.setText(
            f"Account Created: "
            f"{getattr(account, 'created_at', 'Not available')}"
        )

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
        self.lbl_profile_created.setText(
            "Account Created: Not available"
        )

    def get_selected_volunteer_records(self):
        """
        Return waste reports and clean-up drive reports submitted by the
        selected volunteer. These are the same saved records used by the
        Review Reports and Public Feed pages.
        """
        username = str(self.selected_username or "").strip()
        if not username:
            return []

        records = []

        # Waste reports use report_records, with moderation stored separately
        # by matching report index.
        waste_records = getattr(DataStore, "report_records", [])
        try:
            DataStore._synchronize_report_moderation()
        except (AttributeError, TypeError):
            pass

        for index, record in enumerate(waste_records):
            if not isinstance(record, dict):
                continue
            if str(record.get("username", "")).strip().casefold() != username.casefold():
                continue

            post = dict(record)
            post["post_type"] = "Waste Report"
            post["report_type"] = record.get("report_type", "Waste Report")
            post["_source"] = "waste"
            post["_source_index"] = index

            try:
                moderation = DataStore.get_report_moderation(index) or {}
            except (AttributeError, IndexError, TypeError):
                moderation = {}

            post["moderation_status"] = moderation.get("status", "Pending")
            post["admin_note"] = moderation.get("admin_note", "")
            records.append(post)

        # Clean-up drive reports are stored in a separate collection and have
        # their own moderation entries. Include them in the same profile view.
        cleanup_records = getattr(DataStore, "cleanup_drive_reports", [])
        try:
            DataStore._synchronize_cleanup_drive_report_moderation()
        except (AttributeError, TypeError):
            pass

        cleanup_moderation = getattr(
            DataStore, "cleanup_drive_report_moderation", []
        )

        for index, record in enumerate(cleanup_records):
            if not isinstance(record, dict):
                continue
            if str(record.get("username", "")).strip().casefold() != username.casefold():
                continue

            post = dict(record)
            post["post_type"] = "Clean-up Drive Report"
            post["report_type"] = record.get("drive_name", "Clean-up Drive Report")
            post["_source"] = "cleanup"
            post["_source_index"] = index

            moderation = (
                cleanup_moderation[index]
                if index < len(cleanup_moderation)
                and isinstance(cleanup_moderation[index], dict)
                else {}
            )
            post["moderation_status"] = moderation.get("status", "Pending")
            post["admin_note"] = moderation.get("admin_note", "")
            post.setdefault("location", record.get("location", ""))
            records.append(post)

        records.sort(
            key=lambda record: str(record.get("submitted_at", "")),
            reverse=True,
        )
        return records

    def show_selected_volunteer_gallery(self):
        if not self.selected_username:
            QMessageBox.warning(
                self,
                "No Volunteer Selected",
                "Please select a volunteer first."
            )
            return

        records = self.get_selected_volunteer_records()

        image_records = [
            record for record in records
            if record.get("image_path")
            and Path(str(record["image_path"])).is_file()
        ]

        self.open_volunteer_posts_dialog(
            "Volunteer Gallery",
            image_records,
            images_only=True
        )

    def show_selected_volunteer_recent_posts(self):
        if not self.selected_username:
            QMessageBox.warning(
                self,
                "No Volunteer Selected",
                "Please select a volunteer first."
            )
            return

        records = self.get_selected_volunteer_records()

        records.sort(
            key=lambda record: str(
                record.get("submitted_at", "")
            ),
            reverse=True
        )

        self.open_volunteer_posts_dialog(
            "Volunteer Recent Posts",
            records,
            images_only=False
        )

    def open_volunteer_posts_dialog(
        self,
        title,
        records,
        images_only=False
    ):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(600, 650)

        layout = QVBoxLayout(dialog)

        heading = QLabel(
            f"{title} — {self.selected_username}"
        )
        heading.setObjectName("pageHeading")
        layout.addWidget(heading)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        if not records:
            if images_only:
                message = "No gallery images are available."
            else:
                message = "This volunteer has no recorded posts."

            empty_label = QLabel(message)
            empty_label.setWordWrap(True)
            content_layout.addWidget(empty_label)

        for record in records:
            card = QFrame()
            card.setObjectName("adminCard")

            card_layout = QVBoxLayout(card)

            report_type = record.get(
                "report_type",
                record.get("post_type", "Waste Report")
            )

            post_heading = QLabel(str(report_type))
            post_heading.setStyleSheet(
                "font-weight: bold; font-size: 14px;"
            )
            post_heading.setWordWrap(True)
            card_layout.addWidget(post_heading)

            post_type = record.get("post_type", "Waste Report")
            if not images_only:
                type_label = QLabel(f"Post Type: {post_type}")
                type_label.setWordWrap(True)
                card_layout.addWidget(type_label)

                status = record.get("moderation_status", "")
                if status:
                    status_label = QLabel(f"Review Status: {status}")
                    status_label.setWordWrap(True)
                    card_layout.addWidget(status_label)

            location = record.get("location") or record.get("drive_location") or "Not provided"
            if record.get("drive_name") and post_type == "Clean-up Drive Report":
                location = record.get("location") or "See clean-up drive schedule"

            submitted_at = record.get(
                "submitted_at",
                "Unknown"
            )

            location_label = QLabel(
                f"Location: {location}"
            )
            location_label.setWordWrap(True)
            card_layout.addWidget(location_label)

            date_label = QLabel(
                f"Submitted: {submitted_at}"
            )
            date_label.setWordWrap(True)
            card_layout.addWidget(date_label)

            details = str(record.get("details", "") or "")

            if details and not images_only:
                details_label = QLabel(details)
                details_label.setWordWrap(True)
                card_layout.addWidget(details_label)

                likes = record.get("likes", [])
                comments = record.get("comments", [])
                if isinstance(likes, list) or isinstance(comments, list):
                    engagement_label = QLabel(
                        f"Likes: {len(likes) if isinstance(likes, list) else 0}  |  "
                        f"Comments: {len(comments) if isinstance(comments, list) else 0}"
                    )
                    card_layout.addWidget(engagement_label)

                admin_note = str(record.get("admin_note", "") or "").strip()
                if admin_note:
                    note_label = QLabel(f"Admin Note: {admin_note}")
                    note_label.setWordWrap(True)
                    card_layout.addWidget(note_label)

            image_path = record.get("image_path", "")

            if image_path:
                image_file = Path(str(image_path))

                if image_file.is_file():
                    pixmap = QPixmap(str(image_file))

                    if not pixmap.isNull():
                        image_label = QLabel()
                        image_label.setAlignment(
                            Qt.AlignmentFlag.AlignCenter
                        )
                        image_label.setPixmap(
                            pixmap.scaled(
                                460,
                                300,
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
            QMessageBox.warning(
                self, "Selection Error",
                "Please select a volunteer first."
            )
            return

        from data_manager import award_volunteer_points

        points = self.spin_points.value()

        reply = QMessageBox.question(
            self,
            "Confirm Points",
            f"Send {points} points to "
            f"{self.selected_username}?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            success, message = award_volunteer_points(
                self.selected_username,
                points
            )
        except Exception as error:
            QMessageBox.critical(
                self, "Points Error",
                f"Could not award points.\n{error}"
            )
            return

        if success:
            QMessageBox.information(
                self, "Success", message
            )
            self.show_selected_volunteer(
                self.volunteer_list.currentRow()
            )
        else:
            QMessageBox.warning(
                self, "Error", message
            )

    def handle_delete_user(self):
        if not self.selected_username:
            QMessageBox.warning(
                self, "Selection Error",
                "Please select a volunteer to delete."
            )
            return

        username = self.selected_username

        reply = QMessageBox.question(
            self,
            "Confirm Profile Deletion",
            f"Are you sure you want to delete the profile "
            f"for '{username}'?\n\n"
            "This removes the volunteer's account. "
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
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
                    account.username.casefold()
                    == username.casefold()
                    and account.role.casefold() == "volunteer"
                )
            ]

            if len(updated_accounts) == len(accounts):
                QMessageBox.warning(
                    self, "Not Found",
                    "The volunteer account was not found."
                )
                self.refresh_volunteer_list()
                return

            save_accounts(updated_accounts)

        except Exception as error:
            QMessageBox.critical(
                self, "Deletion Error",
                f"Could not delete the volunteer account.\n{error}"
            )
            return

        self.selected_username = None
        self.refresh_volunteer_list()

        QMessageBox.information(
            self, "Success",
            f"The profile for '{username}' was deleted."
        )

class AdminRewardClaimsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout_claims = QVBoxLayout(self)

        card_claims = QFrame()
        card_claims.setObjectName("adminCard")
        c_layout = QVBoxLayout(card_claims)

        c_title = QLabel(
            "Manage Reward Releases & District Pickup"
        )
        c_title.setObjectName("pageHeading")

        self.list_claims = QListWidget()
        self.list_claims.setObjectName("announcementList")
        self.list_claims.setMinimumHeight(100)
        self.list_claims.currentRowChanged.connect(
            self.on_claim_selected
        )

        self.combo_district_office = QComboBox()
        self.combo_district_office.addItems([
            "District 1 Office (Central Plaza)",
            "District 2 Branch (River Spillway Hub)",
            "District 3 Office (Main Bridge Command)",
            "Barangay 182 Hall Pickup Center"
        ])

        self.txt_pickup_notes = QLineEdit()
        self.txt_pickup_notes.setPlaceholderText(
            "e.g. Ready for pickup Mon-Fri, 9 AM - 4 PM. Present ID."
        )

        self.combo_claim_status = QComboBox()
        self.combo_claim_status.addItems([
            "Ready for Pick-up",
            "Released / Picked Up",
            "Processing Release",
            "Cancelled / Out of Stock"
        ])

        btn_update_claim = QPushButton(
            "Update Status & Notify Volunteer"
        )
        btn_update_claim.setObjectName("primaryButton")
        btn_update_claim.clicked.connect(
            self.handle_update_claim_status
        )

        btn_delete_claim = QPushButton(
            "Delete Reward Claim"
        )
        btn_delete_claim.setObjectName("secondaryButton")
        btn_delete_claim.clicked.connect(
            self.handle_delete_claim
        )

        claim_buttons = QHBoxLayout()
        claim_buttons.addWidget(btn_update_claim, 2)
        claim_buttons.addWidget(btn_delete_claim, 1)

        c_layout.addWidget(c_title)
        c_layout.addWidget(
            QLabel("Select Volunteer Reward Claim:")
        )
        c_layout.addWidget(self.list_claims)
        c_layout.addWidget(
            QLabel("Assign Nearest District Office for Pick-up:")
        )
        c_layout.addWidget(self.combo_district_office)
        c_layout.addWidget(
            QLabel("Pick-up Instructions & Schedule:")
        )
        c_layout.addWidget(self.txt_pickup_notes)
        c_layout.addWidget(QLabel("Update Release Status:"))
        c_layout.addWidget(self.combo_claim_status)
        c_layout.addLayout(claim_buttons)

        layout_claims.addWidget(card_claims)

    def refresh_reward_claims_list(self):
        previous_id = None
        current_row = self.list_claims.currentRow()
        claims = getattr(DataStore, "reward_claims", [])

        if 0 <= current_row < len(claims):
            previous_id = claims[current_row].get("id")

        self.list_claims.clear()

        if not claims:
            self.list_claims.addItem(
                "No reward claims submitted yet."
            )
            return

        selected_row = -1

        for index, claim in enumerate(claims):
            display_text = (
                f"ID #{claim.get('id', 'N/A')} | "
                f"Volunteer: {claim.get('full_name', 'Unknown')} "
                f"({claim.get('username', 'Unknown')}) | "
                f"Item: {claim.get('item_name', 'Unknown')} | "
                f"Status: {claim.get('status', 'Pending')}"
            )

            item = QListWidgetItem(display_text)
            item.setData(
                Qt.ItemDataRole.UserRole,
                claim.get("id")
            )
            self.list_claims.addItem(item)

            if (
                previous_id is not None
                and claim.get("id") == previous_id
            ):
                selected_row = index

        if selected_row >= 0:
            self.list_claims.setCurrentRow(selected_row)
        elif self.list_claims.count() > 0:
            self.list_claims.setCurrentRow(0)

    def on_claim_selected(self, row: int):
        claims = getattr(DataStore, "reward_claims", [])

        if 0 <= row < len(claims):
            claim = claims[row]

            notes = claim.get("pickup_info", "")
            self.txt_pickup_notes.setText(notes)

            status = claim.get("status", "")
            status_index = self.combo_claim_status.findText(status)

            if status_index >= 0:
                self.combo_claim_status.setCurrentIndex(
                    status_index
                )

    def handle_update_claim_status(self):
        row = self.list_claims.currentRow()
        claims = getattr(DataStore, "reward_claims", [])

        if row < 0 or row >= len(claims):
            QMessageBox.warning(
                self, "Selection Error",
                "Please select a reward claim from the list."
            )
            return

        claim = claims[row]

        district_office = self.combo_district_office.currentText()
        notes = self.txt_pickup_notes.text().strip()
        status = self.combo_claim_status.currentText()

        full_pickup_info = (
            f"{district_office}. {notes}"
            if notes else district_office
        )

        old_status = claim.get("status")
        old_pickup_info = claim.get("pickup_info")
        old_announcements = list(DataStore.announcements)

        claim["status"] = status
        claim["pickup_info"] = full_pickup_info

        full_name = claim.get("full_name", "Volunteer")
        item_name = claim.get("item_name", "reward")

        notif_title = f"Reward Update: {item_name}"
        notif_body = (
            f"Hello {full_name}! Your reward claim for "
            f"'{item_name}' is now [{status}].\n"
            f"Pickup Location: {district_office}\n"
            f"Instructions: "
            f"{notes if notes else 'Present your Volunteer ID upon pickup.'}"
        )

        DataStore.announcements.insert(
            0, (notif_title, notif_body)
        )

        try:
            DataStore.save()
        except Exception as error:
            if old_status is None:
                claim.pop("status", None)
            else:
                claim["status"] = old_status

            if old_pickup_info is None:
                claim.pop("pickup_info", None)
            else:
                claim["pickup_info"] = old_pickup_info

            DataStore.announcements = old_announcements

            QMessageBox.critical(
                self, "Save Error",
                f"Could not update the reward claim.\n{error}"
            )
            return

        self.refresh_reward_claims_list()

        QMessageBox.information(
            self,
            "Claim Updated",
            f"Updated release status to '{status}' and "
            f"created a notification for {full_name}."
        )

    def handle_delete_claim(self):
        row = self.list_claims.currentRow()
        claims = getattr(DataStore, "reward_claims", [])

        if row < 0 or row >= len(claims):
            QMessageBox.warning(
                self, "Selection Error",
                "Please select a reward claim to delete."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this reward claim?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        removed_claim = claims.pop(row)

        try:
            DataStore.save()
        except Exception as error:
            claims.insert(row, removed_claim)
            QMessageBox.critical(
                self, "Deletion Error",
                f"Could not delete the reward claim.\n{error}"
            )
            return

        self.refresh_reward_claims_list()

        QMessageBox.information(
            self, "Success",
            "Reward claim deleted successfully."
        )

class AdminVolunteerTicketsPage(QWidget):
    def __init__(self, parent=None):
        self.selected_ticket_id = None
        super().__init__(parent)
        layout_tickets = QVBoxLayout(self)

        ticket_card = QFrame()
        ticket_card.setObjectName("adminCard")
        ticket_layout = QVBoxLayout(ticket_card)

        ticket_title = QLabel("Volunteer Tickets & Complaints")
        ticket_title.setObjectName("pageHeading")
        ticket_layout.addWidget(ticket_title)

        ticket_splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        self.admin_tickets_list = QListWidget()
        self.admin_tickets_list.setObjectName("announcementList")
        self.admin_tickets_list.currentItemChanged.connect(
            self.show_selected_ticket
        )

        ticket_detail_panel = QWidget()
        ticket_detail_layout = QVBoxLayout(ticket_detail_panel)

        self.lbl_ticket_id = QLabel("Ticket: Not selected")
        self.lbl_ticket_sender = QLabel(
            "Submitted by: Not selected"
        )
        self.lbl_ticket_target = QLabel(
            "Reported profile: Not specified"
        )
        self.lbl_ticket_status = QLabel("Status: Not available")

        for label in (
            self.lbl_ticket_id,
            self.lbl_ticket_sender,
            self.lbl_ticket_target,
            self.lbl_ticket_status,
        ):
            label.setWordWrap(True)
            ticket_detail_layout.addWidget(label)

        ticket_detail_layout.addWidget(
            QLabel("Volunteer Message:")
        )

        self.txt_ticket_message = QTextEdit()
        self.txt_ticket_message.setReadOnly(True)
        ticket_detail_layout.addWidget(
            self.txt_ticket_message
        )

        ticket_detail_layout.addWidget(
            QLabel("Administrator's Response:")
        )

        self.txt_ticket_response = QTextEdit()
        self.txt_ticket_response.setPlaceholderText(
            "Write a response to the volunteer..."
        )
        ticket_detail_layout.addWidget(
            self.txt_ticket_response
        )

        self.combo_ticket_status = QComboBox()
        self.combo_ticket_status.addItems([
            "Open",
            "Responded",
            "Resolved"
        ])

        ticket_detail_layout.addWidget(
            QLabel("Update Ticket Status:")
        )
        ticket_detail_layout.addWidget(
            self.combo_ticket_status
        )

        ticket_buttons = QHBoxLayout()

        btn_respond_ticket = QPushButton(
            "Save Response"
        )
        btn_respond_ticket.setObjectName("primaryButton")
        btn_respond_ticket.clicked.connect(
            self.handle_respond_to_ticket
        )

        btn_refresh_tickets = QPushButton(
            "Refresh Tickets"
        )
        btn_refresh_tickets.setObjectName("secondaryButton")
        btn_refresh_tickets.clicked.connect(
            self.refresh_admin_tickets
        )

        ticket_buttons.addWidget(btn_respond_ticket)
        ticket_buttons.addWidget(btn_refresh_tickets)

        ticket_detail_layout.addLayout(ticket_buttons)

        ticket_splitter.addWidget(self.admin_tickets_list)
        ticket_splitter.addWidget(ticket_detail_panel)
        ticket_splitter.setSizes([320, 650])

        ticket_layout.addWidget(ticket_splitter)
        layout_tickets.addWidget(ticket_card)

    def refresh_admin_tickets(self):
        previous_id = self.selected_ticket_id

        self.admin_tickets_list.clear()

        for ticket in DataStore.report_tickets:
            ticket_id = ticket.get("id")
            username = ticket.get("username", "Unknown")
            status = ticket.get("status", "Open")
            message = ticket.get("message", "")

            # Display a short preview without changing the message.
            preview = " ".join(str(message).split())
            if len(preview) > 55:
                preview = preview[:52] + "..."

            item = QListWidgetItem(
                f"#{ticket_id} | {username} | {status}\n{preview}"
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                ticket_id
            )
            self.admin_tickets_list.addItem(item)

        target_row = -1

        for row in range(self.admin_tickets_list.count()):
            item = self.admin_tickets_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == previous_id:
                target_row = row
                break

        if target_row >= 0:
            self.admin_tickets_list.setCurrentRow(target_row)
        elif self.admin_tickets_list.count() > 0:
            self.admin_tickets_list.setCurrentRow(0)
        else:
            self.selected_ticket_id = None
            self.clear_ticket_details()

    def show_selected_ticket(self, current, _previous=None):
        if current is None:
            self.selected_ticket_id = None
            self.clear_ticket_details()
            return

        ticket_id = current.data(
            Qt.ItemDataRole.UserRole
        )

        ticket = next(
            (
                entry for entry in DataStore.report_tickets
                if entry.get("id") == ticket_id
            ),
            None
        )

        if ticket is None:
            self.selected_ticket_id = None
            self.clear_ticket_details()
            return

        self.selected_ticket_id = ticket_id

        self.lbl_ticket_id.setText(
            f"Ticket: #{ticket_id}"
        )
        self.lbl_ticket_sender.setText(
            f"Submitted by: {ticket.get('username', 'Unknown')}"
        )
        self.lbl_ticket_target.setText(
            f"Reported profile: "
            f"{ticket.get('reported_username') or 'Not specified'}"
        )
        self.lbl_ticket_status.setText(
            f"Status: {ticket.get('status', 'Open')}"
        )

        message = ticket.get("message", "")

        report_index = ticket.get("report_index")
        if report_index is not None:
            message += f"\n\nRelated report index: {report_index}"

        self.txt_ticket_message.setPlainText(message)
        self.txt_ticket_response.setPlainText(
            ticket.get("admin_response", "")
        )

        status = ticket.get("status", "Open")

        # Deleted-report tickets are a special state in the current
        # data format, so display them as Open in the status selector.
        if status not in ("Open", "Responded", "Resolved"):
            status = "Open"

        status_index = self.combo_ticket_status.findText(status)
        self.combo_ticket_status.setCurrentIndex(
            max(status_index, 0)
        )

    def clear_ticket_details(self):
        self.lbl_ticket_id.setText("Ticket: Not selected")
        self.lbl_ticket_sender.setText(
            "Submitted by: Not selected"
        )
        self.lbl_ticket_target.setText(
            "Reported profile: Not specified"
        )
        self.lbl_ticket_status.setText("Status: Not available")
        self.txt_ticket_message.clear()
        self.txt_ticket_response.clear()
        self.combo_ticket_status.setCurrentIndex(0)

    def handle_respond_to_ticket(self):
        if self.selected_ticket_id is None:
            QMessageBox.warning(
                self, "Selection Error",
                "Please select a ticket first."
            )
            return

        response = self.txt_ticket_response.toPlainText().strip()
        status = self.combo_ticket_status.currentText()

        if not response:
            QMessageBox.warning(
                self, "Input Error",
                "Please enter a response before saving."
            )
            return

        try:
            success = DataStore.respond_to_ticket(
                self.selected_ticket_id,
                response,
                status
            )
        except Exception as error:
            QMessageBox.critical(
                self, "Save Error",
                f"Could not save the ticket response.\n{error}"
            )
            return

        if not success:
            QMessageBox.warning(
                self, "Not Found",
                "The selected ticket could not be found."
            )
            self.refresh_admin_tickets()
            return

        self.refresh_admin_tickets()

        QMessageBox.information(
            self, "Response Saved",
            "The ticket response and status were saved."
        )

class AdminCleanupDrivePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout_schedules = QVBoxLayout(self)
        card_schedules = QFrame()
        card_schedules.setObjectName("adminCard")
        schedule_layout = QVBoxLayout(card_schedules)

        schedule_title = QLabel("Create Clean-up Drive Schedule")
        schedule_title.setObjectName("pageHeading")
        self.txt_drive_name = QLineEdit()
        self.txt_drive_name.setPlaceholderText("Clean-up drive name")
        self.txt_drive_datetime = QLineEdit()
        self.txt_drive_datetime.setPlaceholderText("Date and time")
        self.txt_drive_location = QLineEdit()
        self.txt_drive_location.setPlaceholderText("Location / venue")
        btn_add_schedule = QPushButton("Publish Clean-up Drive Schedule")
        btn_add_schedule.setObjectName("primaryButton")
        btn_add_schedule.clicked.connect(self.handle_add_schedule)
        self.list_schedules = QListWidget()
        self.list_schedules.setObjectName("announcementList")
        self.list_schedules.currentRowChanged.connect(self.refresh_attendance_list)
        schedule_layout.addWidget(QLabel("Volunteers who joined the selected drive:"))
        self.list_attendees = QListWidget()
        self.list_attendees.setObjectName("announcementList")
        self.list_attendees.setMaximumHeight(120)
        schedule_layout.addWidget(self.list_attendees)
        btn_delete_schedule = QPushButton("Delete Selected Clean-up Drive")
        btn_delete_schedule.setObjectName("secondaryButton")
        btn_delete_schedule.clicked.connect(self.handle_delete_schedule)

        schedule_layout.addWidget(schedule_title)
        schedule_layout.addWidget(QLabel("Clean-up Drive Name:"))
        schedule_layout.addWidget(self.txt_drive_name)
        schedule_layout.addWidget(QLabel("Date & Time:"))
        schedule_layout.addWidget(self.txt_drive_datetime)
        schedule_layout.addWidget(QLabel("Location / Venue:"))
        schedule_layout.addWidget(self.txt_drive_location)
        schedule_layout.addWidget(btn_add_schedule)
        schedule_layout.addWidget(QLabel("Existing Clean-up Drives:"))
        schedule_layout.addWidget(self.list_schedules)
        schedule_layout.addWidget(btn_delete_schedule)
        layout_schedules.addWidget(card_schedules)

    def handle_add_schedule(self):
        name = self.txt_drive_name.text().strip()
        date_time = self.txt_drive_datetime.text().strip()
        location = self.txt_drive_location.text().strip()
        if not name or not date_time or not location:
            QMessageBox.warning(self, "Input Error", "Please fill in the clean-up drive name, date/time, and location.")
            return

        ids = [
            int(item.get("id", 0)) for item in DataStore.cleanup_drives
            if isinstance(item, dict) and str(item.get("id", "")).isdigit()
        ]
        drive = {
            "id": max(ids, default=0) + 1,
            "name": name,
            "datetime": date_time,
            "location": location,
            "joined": False,
        }
        DataStore.cleanup_drives.append(drive)
        try:
            DataStore.save()
        except Exception as error:
            DataStore.cleanup_drives.remove(drive)
            QMessageBox.critical(self, "Save Error", f"Could not save clean-up drive schedule.\n{error}")
            return

        self.txt_drive_name.clear()
        self.txt_drive_datetime.clear()
        self.txt_drive_location.clear()
        self.refresh_schedules_list()
        QMessageBox.information(self, "Schedule Created", "Clean-up drive schedule published successfully.")

    def refresh_schedules_list(self):
        self.list_schedules.clear()
        for drive in DataStore.cleanup_drives:
            if not isinstance(drive, dict):
                continue
            self.list_schedules.addItem(
                f"ID #{drive.get('id', '')} | {drive.get('name', '')} | "
                f"{drive.get('datetime', '')} | {drive.get('location', '')}"
            )
        self.refresh_attendance_list(self.list_schedules.currentRow())

    def refresh_attendance_list(self, row=-1):
        if not hasattr(self, "list_attendees"):
            return
        self.list_attendees.clear()
        if row < 0 or row >= len(DataStore.cleanup_drives):
            return
        drive = DataStore.cleanup_drives[row]
        for username in drive.get("joined_by", []) if isinstance(drive, dict) else []:
            self.list_attendees.addItem(str(username))
        if self.list_attendees.count() == 0:
            self.list_attendees.addItem("No volunteers have joined this drive yet.")

    def handle_delete_schedule(self):
        row = self.list_schedules.currentRow()
        if row < 0 or row >= len(DataStore.cleanup_drives):
            QMessageBox.warning(self, "Selection Error", "Select a clean-up drive first.")
            return
        answer = QMessageBox.question(
            self, "Confirm Delete", "Delete the selected clean-up drive?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        removed = DataStore.cleanup_drives.pop(row)
        try:
            DataStore.save()
        except Exception as error:
            DataStore.cleanup_drives.insert(row, removed)
            QMessageBox.critical(self, "Save Error", f"Could not delete clean-up drive.\n{error}")
            return
        self.refresh_schedules_list()
        QMessageBox.information(self, "Schedule Deleted", "Clean-up drive deleted successfully.")

class AdminCleanupDriveReportsPage(QWidget):
    """Review volunteer clean-up drive attendance-proof submissions."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_index = None
        layout = QVBoxLayout(self)
        split = QSplitter()
        self.report_list = QListWidget()
        self.report_list.currentItemChanged.connect(self.show_selected_report)
        split.addWidget(self.report_list)
        panel = QWidget(); panel_layout = QVBoxLayout(panel)
        self.lbl_status = QLabel("Status: Not selected")
        self.lbl_owner = QLabel("Volunteer: Not selected")
        self.lbl_drive = QLabel("Clean-up Drive: Not selected")
        self.lbl_details = QLabel("Select a report to review."); self.lbl_details.setWordWrap(True)
        self.lbl_image = QLabel("No image selected."); self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lbl_image.setMinimumHeight(150)
        self.txt_note = QTextEdit(); self.txt_note.setPlaceholderText("Admin note / feedback"); self.txt_note.setMaximumHeight(75)
        panel_layout.addWidget(self.lbl_status); panel_layout.addWidget(self.lbl_owner); panel_layout.addWidget(self.lbl_drive); panel_layout.addWidget(self.lbl_details); panel_layout.addWidget(self.lbl_image, 1); panel_layout.addWidget(QLabel("Administrator's Note:")); panel_layout.addWidget(self.txt_note)
        buttons = QHBoxLayout()
        self.btn_approve = QPushButton("Verify Report"); self.btn_approve.clicked.connect(lambda: self.moderate("Approved"))
        self.btn_reject = QPushButton("Reject Report"); self.btn_reject.clicked.connect(lambda: self.moderate("Rejected"))
        self.btn_award = QPushButton("Award 10 Points"); self.btn_award.clicked.connect(self.award_points)
        for b in (self.btn_approve, self.btn_reject, self.btn_award): buttons.addWidget(b)
        panel_layout.addLayout(buttons); split.addWidget(panel); split.setSizes([300, 600]); layout.addWidget(split)

    def refresh_reports(self):
        previous = self.selected_index; self.report_list.clear(); DataStore._synchronize_cleanup_drive_report_moderation()
        for i, report in enumerate(DataStore.cleanup_drive_reports):
            mod = DataStore.cleanup_drive_report_moderation[i]
            self.report_list.addItem(f"[{mod.get('status','Pending')}] {report.get('full_name', report.get('username','Volunteer'))} — {report.get('drive_name','Clean-up Drive')}")
            self.report_list.item(self.report_list.count()-1).setData(Qt.ItemDataRole.UserRole, i)
        for row in range(self.report_list.count()):
            if self.report_list.item(row).data(Qt.ItemDataRole.UserRole) == previous:
                self.report_list.setCurrentRow(row); return
        if self.report_list.count(): self.report_list.setCurrentRow(0)
        else: self.show_selected_report(None)

    def show_selected_report(self, current, _previous=None):
        if current is None: self.selected_index = None; self.lbl_status.setText("Status: Not selected"); self.lbl_owner.setText("Volunteer: Not selected"); self.lbl_drive.setText("Clean-up Drive: Not selected"); self.lbl_details.setText("No clean-up drive reports."); self.lbl_image.setText("No image selected."); self.lbl_image.setPixmap(QPixmap()); self.txt_note.clear(); return
        i = current.data(Qt.ItemDataRole.UserRole); self.selected_index = i
        report = DataStore.cleanup_drive_reports[i]; mod = DataStore.cleanup_drive_report_moderation[i]
        self.lbl_status.setText(f"Status: {mod.get('status','Pending')}"); self.lbl_owner.setText(f"Volunteer: {report.get('full_name','')} (@{report.get('username','')})"); self.lbl_drive.setText(f"Clean-up Drive: {report.get('drive_name','')}"); self.lbl_details.setText(f"Submitted: {report.get('submitted_at','')}\n\n{report.get('details','')}"); self.txt_note.setPlainText(mod.get('admin_note',''))
        path = Path(report.get('image_path',''))
        pix = QPixmap(str(path)) if path.is_file() else QPixmap()
        if pix.isNull(): self.lbl_image.setPixmap(QPixmap()); self.lbl_image.setText("Attendance proof image unavailable.")
        else: self.lbl_image.setText(""); self.lbl_image.setPixmap(pix.scaled(440, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.btn_award.setEnabled(mod.get('status') == 'Approved' and not mod.get('points_awarded', False))

    def moderate(self, status):
        if self.selected_index is None: QMessageBox.warning(self, "Select Report", "Select a report first."); return
        try: DataStore.update_cleanup_drive_report_moderation(self.selected_index, status, self.txt_note.toPlainText())
        except Exception as error: QMessageBox.critical(self, "Update Failed", str(error)); return
        self.refresh_reports(); QMessageBox.information(self, "Report Updated", f"Clean-up drive report marked {status.lower()}.")

    def award_points(self):
        i = self.selected_index
        if i is None: return
        mod = DataStore.cleanup_drive_report_moderation[i]; report = DataStore.cleanup_drive_reports[i]
        if mod.get('status') != 'Approved': QMessageBox.warning(self, "Not Verified", "Verify the report before awarding points."); return
        if mod.get('points_awarded'): QMessageBox.information(self, "Already Awarded", "Points have already been awarded for this report."); return
        ok, message = award_volunteer_points(report.get('username',''), 10)
        if not ok: QMessageBox.warning(self, "Points Not Awarded", message); return
        mod['points_awarded'] = True; DataStore.save(); self.refresh_reports(); QMessageBox.information(self, "Points Awarded", message)

class AdminReviewReportsPage(QWidget):
    def __init__(self, waste_page, cleanup_page, parent=None):
        super().__init__(parent); layout = QVBoxLayout(self); self.tabs = QTabWidget(); self.tabs.addTab(waste_page, "Waste Report"); self.tabs.addTab(cleanup_page, "Clean-up Drive Report"); layout.addWidget(self.tabs); self.waste_page = waste_page; self.cleanup_page = cleanup_page
        self.tabs.currentChanged.connect(self._refresh_current_tab)
    def _refresh_current_tab(self, index):
        if index == 0: self.waste_page.refresh_admin_reports()
        else: self.cleanup_page.refresh_reports()
    def refresh_admin_reports(self): self.waste_page.refresh_admin_reports()
    def refresh_reports(self): self.cleanup_page.refresh_reports()

class AdminClickableFeedImageLabel(QLabel):
    """Inline image preview that opens the full-size image when clicked."""
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = str(image_path)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to view image")
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        pixmap = QPixmap(self.image_path)
        if not pixmap.isNull():
            self.setPixmap(pixmap.scaled(
                360, 240,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.setText("Image preview unavailable")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = QDialog(self)
            dialog.setWindowTitle("Public Feed Image Preview")
            dialog.resize(800, 650)
            layout = QVBoxLayout(dialog)
            image = QLabel()
            image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(self.image_path)
            if pixmap.isNull():
                image.setText("Image unavailable.")
            else:
                image.setPixmap(pixmap.scaled(
                    760, 580,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            layout.addWidget(image)
            dialog.exec()
        super().mousePressEvent(event)


class AdminPublicFeedPage(QWidget):
    """Admin view of both public feeds, with the same like/comment actions as volunteers."""
    def __init__(self, parent=None):
        super().__init__(parent); layout = QVBoxLayout(self); self.tabs = QTabWidget()
        self.waste_list = QListWidget(); self.cleanup_list = QListWidget()
        for widget in (self.waste_list, self.cleanup_list):
            widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
            widget.verticalScrollBar().setSingleStep(12)
        self.tabs.addTab(self.waste_list, "Waste Report Feed"); self.tabs.addTab(self.cleanup_list, "Clean-up Drive Feed"); layout.addWidget(self.tabs)
        refresh = QPushButton("Refresh Feed"); refresh.clicked.connect(self.refresh_feed); layout.addWidget(refresh)
        self.refresh_feed()

    def _add_interactive_post(self, target_list, index, record, cleanup=False):
        widget = QWidget(); box = QVBoxLayout(widget)
        box.addWidget(QLabel(f"{record.get('full_name',record.get('username','Volunteer'))} (@{record.get('username','')})"))
        box.addWidget(QLabel(record.get('drive_name','Clean-up Drive') if cleanup else record.get('report_type','Waste Report')))
        details = QLabel(record.get('details','')); details.setWordWrap(True); box.addWidget(details)
        image_path = record.get('image_path', '')
        if image_path and Path(str(image_path)).is_file():
            image_preview = AdminClickableFeedImageLabel(str(image_path))
            box.addWidget(image_preview)
        likes = record.get('likes', []) if isinstance(record.get('likes', []), list) else []
        like = QPushButton(f"Like ({len(likes)})")
        like.clicked.connect(lambda checked=False, i=index, c=cleanup: self._like(i,c))
        box.addWidget(like); box.addWidget(QLabel("Comments"))
        comments = record.get('comments', []) if isinstance(record.get('comments', []), list) else []
        for comment in comments:
            if isinstance(comment, dict):
                label = QLabel(f"{comment.get('full_name','Volunteer')}: {comment.get('text','')}"); label.setWordWrap(True); box.addWidget(label)
        field = QLineEdit(); field.setPlaceholderText("Write a comment..."); box.addWidget(field)
        post = QPushButton("Post Comment"); post.clicked.connect(lambda checked=False, i=index, c=cleanup, f=field: self._comment(i,c,f)); box.addWidget(post)
        item = QListWidgetItem(); item.setSizeHint(widget.sizeHint()); target_list.addItem(item); target_list.setItemWidget(item,widget)

    def refresh_feed(self):
        self.waste_list.clear(); self.cleanup_list.clear()
        for i, _text, record in DataStore.get_approved_report_records(): self._add_interactive_post(self.waste_list, i, record, False)
        for i, record in DataStore.get_approved_cleanup_drive_reports(): self._add_interactive_post(self.cleanup_list, i, record, True)
        if not self.waste_list.count(): self.waste_list.addItem("No approved waste reports yet.")
        if not self.cleanup_list.count(): self.cleanup_list.addItem("No approved clean-up drive reports yet.")

    def _show_image(self, path):
        dialog = QDialog(self); dialog.setWindowTitle("Public Feed Image"); dialog.resize(800, 650); box = QVBoxLayout(dialog)
        image = QLabel(); image.setAlignment(Qt.AlignmentFlag.AlignCenter); pix = QPixmap(path)
        if pix.isNull(): image.setText("Image unavailable.")
        else: image.setPixmap(pix.scaled(760, 580, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        box.addWidget(image); dialog.exec()

    def _like(self, index, cleanup):
        account = Session.current_account
        username = getattr(account, 'username', 'admin') if account else 'admin'
        try:
            if cleanup: DataStore.toggle_cleanup_drive_report_like(index, username)
            else: DataStore.toggle_report_like(index, username)
            self.refresh_feed()
        except Exception as error: QMessageBox.warning(self, "Like Failed", str(error))

    def _comment(self, index, cleanup, field):
        account = Session.current_account
        username = getattr(account, 'username', 'admin') if account else 'admin'
        full_name = getattr(account, 'full_name', 'Administrator') if account else 'Administrator'
        text = field.text().strip()
        if not text: QMessageBox.warning(self, "Empty Comment", "Please write a comment first."); return
        try:
            if cleanup: DataStore.add_cleanup_drive_report_comment(index, username, full_name, text)
            else: DataStore.add_report_comment(index, username, full_name, text)
            self.refresh_feed()
        except Exception as error: QMessageBox.warning(self, "Comment Failed", str(error))

class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard | Post-Flood Waste Management")
        self.resize(1100, 760)
        main_layout = QVBoxLayout(self); main_layout.setContentsMargins(20, 20, 20, 15); main_layout.setSpacing(12)
        top_bar = QHBoxLayout(); admin_badge = QLabel("ROLE: ADMINISTRATOR"); admin_badge.setObjectName("adminBadge")
        btn_logout = QPushButton("Log Out"); btn_logout.setObjectName("secondaryButton"); btn_logout.clicked.connect(self.logout)
        top_bar.addWidget(admin_badge); top_bar.addStretch(); top_bar.addWidget(btn_logout); main_layout.addLayout(top_bar)
        self.stack = QStackedWidget()
        self.page_tasks = AdminCreateTaskPage(self); self.page_notifications = AdminNotificationsPage(self)
        self.page_waste_reports = AdminWasteReportsPage(self); self.page_cleanup_reports = AdminCleanupDriveReportsPage(self)
        self.page_reports = AdminReviewReportsPage(self.page_waste_reports, self.page_cleanup_reports, self)
        self.page_schedules = AdminCleanupDrivePage(self); self.page_public_feed = AdminPublicFeedPage(self)
        self.page_users = AdminManageUsersPage(self); self.page_claims = AdminRewardClaimsPage(self); self.page_tickets = AdminVolunteerTicketsPage(self)
        self.pages = [self.page_tasks, self.page_notifications, self.page_reports, self.page_schedules, self.page_public_feed, self.page_users, self.page_claims, self.page_tickets]
        for page in self.pages: self.stack.addWidget(page)
        # Use pixel-based scrolling on the Admin lists for smoother navigation.
        for list_widget in self.findChildren(QListWidget):
            list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
            list_widget.verticalScrollBar().setSingleStep(12)
        main_layout.addWidget(self.stack, 1)
        nav_frame = QFrame(); nav_frame.setObjectName("navBarFrame"); nav_layout = QHBoxLayout(nav_frame); nav_layout.setContentsMargins(8, 6, 8, 6); nav_layout.setSpacing(5)
        labels = ["Create\nTask", "Send\nNotification", "Review\nReports", "Clean-up\nDrive", "Public\nTab", "Manage\nProfiles", "Reward\nClaims", "Manage\nTicket"]
        self.admin_nav_buttons = []
        for index, label in enumerate(labels):
            button = QPushButton(label); button.setObjectName("capsuleNavBtn"); button.setCursor(Qt.CursorShape.PointingHandCursor); button.clicked.connect(lambda checked=False, i=index: self.switch_admin_tab(i)); nav_layout.addWidget(button, 1); self.admin_nav_buttons.append((button, index))
        main_layout.addWidget(nav_frame); self.switch_admin_tab(0)

    def switch_admin_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 2:
            self.page_reports._refresh_current_tab(self.page_reports.tabs.currentIndex())
        elif index == 3: self.page_schedules.refresh_schedules_list()
        elif index == 4: self.page_public_feed.refresh_feed()
        elif index == 5: self.page_users.refresh_volunteer_list()
        elif index == 6: self.page_claims.refresh_reward_claims_list()
        elif index == 7: self.page_tickets.refresh_admin_tickets()
        for button, button_index in self.admin_nav_buttons:
            button.setProperty("active", "true" if button_index == index else "false")
            button.style().unpolish(button); button.style().polish(button)

    def logout(self):
        reply = QMessageBox.question(self, "Confirm Logout", "Are you sure you want to log out?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from login_window import LoginWindow
            self.login_window = LoginWindow(); self.login_window.show(); self.close()