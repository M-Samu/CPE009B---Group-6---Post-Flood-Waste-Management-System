from datetime import datetime
from pathlib import Path
import re
import shutil
import time

from PyQt6.QtCore import Qt, QRectF, QUrl
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QDesktopServices 
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QListWidget,
    QListWidgetItem, QDialog, QLineEdit, QTextEdit, QComboBox,
    QMessageBox, QScrollArea, QFileDialog, QFormLayout,
    QDialogButtonBox, QGroupBox, QInputDialog, QApplication, 
    QPlainTextEdit, QTabWidget, QAbstractItemView
)

from waste_management_models import Session, hash_password
from app_utils import current_datetime
from data_manager import load_accounts, save_accounts, find_account
from data_store import DataStore

def apply_smooth_scrolling(widget):
    if isinstance(widget, QAbstractItemView):
        widget.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        widget.verticalScrollBar().setSingleStep(12)

    elif isinstance(widget, QScrollArea):
        widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        widget.verticalScrollBar().setSingleStep(12)

# ==============================================================================
# Custom Blue Progress Gauge
# ==============================================================================
class CircularProgressWidget(QWidget):
    def __init__(self, value=0, max_value=100, parent=None):
        super().__init__(parent)
        self.value = value
        self.max_value = max_value if max_value > 0 else 1
        self.setMinimumSize(170, 170)

    def set_value(self, value, max_value=100):
        self.value = value
        self.max_value = max_value if max_value > 0 else 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        size = min(width, height) - 24
        rect = QRectF((width - size) / 2, (height - size) / 2, size, size)

        bg_pen = QPen(QColor("#dbeafe"), 14)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        progress_pen = QPen(QColor("#3b82f6"), 14)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)

        ratio = min(max(self.value / self.max_value, 0.0), 1.0)
        angle = int(360 * ratio * 16)
        painter.drawArc(rect, 90 * 16, -angle)

        painter.setPen(QColor("#1e293b"))
        font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(font)
        pct = int(ratio * 100)
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            f"{pct}%\nCompleted\n({self.value}/{self.max_value})"
        )


class VolunteerOverviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(14)

        self.welcome_label = QLabel("Welcome, Volunteer")
        self.welcome_label.setObjectName("welcomeTitle")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.welcome_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        self.task_card = QFrame()
        self.task_card.setObjectName("volCard")
        task_layout = QVBoxLayout(self.task_card)
        task_layout.setContentsMargins(20, 20, 20, 20)

        # Header Row with Date and "Clear Completed Task" Button
        task_header_layout = QHBoxLayout()
        today_str = datetime.now().strftime("%B %d, %Y")
        date_label = QLabel(today_str)
        date_label.setObjectName("cardDateLabel")

        btn_clear_completed = QPushButton("Clear Completed Task")
        btn_clear_completed.setObjectName("secondaryButton")
        btn_clear_completed.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_completed.clicked.connect(self.clear_completed_tasks)

        task_header_layout.addWidget(date_label)
        task_header_layout.addStretch()
        task_header_layout.addWidget(btn_clear_completed)

        task_layout.addLayout(task_header_layout)

        self.tasks_container = QVBoxLayout()
        self.tasks_container.setSpacing(10)
        task_layout.addLayout(self.tasks_container)
        task_layout.addStretch()

        content_layout.addWidget(self.task_card, 1)

        graphic_card = QFrame()
        graphic_card.setObjectName("volCard")
        graphic_layout = QVBoxLayout(graphic_card)
        graphic_layout.setContentsMargins(20, 20, 20, 20)

        self.ring_chart = CircularProgressWidget(0, 100)
        graphic_layout.addWidget(self.ring_chart, 0, Qt.AlignmentFlag.AlignCenter)

        tint_box = QFrame()
        tint_box.setObjectName("tintedInfoBox")
        tint_layout = QVBoxLayout(tint_box)

        impact_desc = QLabel("Completed Task Progress")
        impact_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        impact_desc.setObjectName("tintedBoxText")
        tint_layout.addWidget(impact_desc)

        graphic_layout.addWidget(tint_box)
        content_layout.addWidget(graphic_card, 1)

        self.main_layout.addLayout(content_layout)

    def refresh_data(self):
        account = Session.current_account
        username = account.username if account else ""
        user_name = account.full_name if account else "Volunteer"
        self.welcome_label.setText(f"Welcome, {user_name}")

        while self.tasks_container.count():
            item = self.tasks_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not hasattr(DataStore, "user_joined_tasks"):
            DataStore.user_joined_tasks = []

        if not hasattr(DataStore, "cleared_tasks"):
            DataStore.cleared_tasks = {}

        user_cleared_list = DataStore.cleared_tasks.get(username, [])

        visible_tasks = [
            (idx, task_text) for idx, task_text in enumerate(DataStore.tasks)
            if task_text not in user_cleared_list
        ]

        total_tasks = len(visible_tasks)
        completed_count = 0

        for idx, task_text in visible_tasks:
            t_row = QHBoxLayout()

            t_text = QLabel(task_text)
            t_text.setObjectName("taskItemText")
            t_text.setWordWrap(True)

            joined_record = next(
                (
                    j for j in DataStore.user_joined_tasks
                    if j.get("username") == username and (j.get("task_title") == task_text or j.get("task_id") == idx)
                ),
                None
            )

            t_row.addWidget(t_text, 1)

            if joined_record is None:
                btn_action = QPushButton("Join Task")
                btn_action.setObjectName("primaryButton")
                btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_action.clicked.connect(lambda _, task_idx=idx, t_title=task_text: self.join_task(task_idx, t_title))
                t_row.addWidget(btn_action)

            elif not joined_record.get("completed", False):
                btn_action = QPushButton("Mark as Done")
                btn_action.setObjectName("primaryButton")
                btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_action.clicked.connect(lambda _, record=joined_record: self.mark_task_completed(record))
                t_row.addWidget(btn_action)

            else:
                completed_count += 1
                lbl_done = QLabel("Completed")
                lbl_done.setStyleSheet("color: #16a34a; font-weight: bold; font-size: 13px;")
                t_row.addWidget(lbl_done)

            row_widget = QWidget()
            row_widget.setLayout(t_row)
            self.tasks_container.addWidget(row_widget)

        self.ring_chart.set_value(completed_count, max_value=max(total_tasks, 1))

    def join_task(self, task_idx: int, task_title: str):
        account = Session.current_account
        if not account:
            QMessageBox.warning(self, "Login Required", "Please log in to join tasks.")
            return

        if not hasattr(DataStore, "user_joined_tasks"):
            DataStore.user_joined_tasks = []

        DataStore.user_joined_tasks.append({
            "username": account.username,
            "task_id": task_idx,
            "task_title": task_title,
            "joined_at": current_datetime(),
            "completed": False
        })

        try:
            DataStore.save()
            QMessageBox.information(
                self, "Task Joined",
                "You joined this task! Mark it as done once you finish to update your progress."
            )
        except Exception as error:
            QMessageBox.critical(self, "Save Error", f"Could not join task:\n{error}")

        self.refresh_data()

    def mark_task_completed(self, record: dict):
        reply = QMessageBox.question(
            self,
            "Confirm Completion",
            "Have you finished working on this task?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        record["completed"] = True
        record["completed_at"] = current_datetime()

        try:
            DataStore.save()
            QMessageBox.information(self, "Task Completed", "Great job! Task marked as done.")
        except Exception as error:
            record["completed"] = False
            QMessageBox.critical(self, "Save Error", f"Could not update task status:\n{error}")

        self.refresh_data()

    def clear_completed_tasks(self):
        """Clears completed tasks for the current logged-in volunteer (hides them for this account only)."""
        account = Session.current_account
        if not account:
            return

        username = account.username
        if not hasattr(DataStore, "user_joined_tasks"):
            DataStore.user_joined_tasks = []

        if not hasattr(DataStore, "cleared_tasks"):
            DataStore.cleared_tasks = {}

        # Find task titles completed by current user
        completed_task_titles = []
        for record in DataStore.user_joined_tasks:
            if record.get("username") == username and record.get("completed", False):
                title = record.get("task_title")
                if not title and 0 <= record.get("task_id", -1) < len(DataStore.tasks):
                    title = DataStore.tasks[record["task_id"]]
                if title and title not in completed_task_titles:
                    completed_task_titles.append(title)

        if not completed_task_titles:
            QMessageBox.information(self, "Clear Tasks", "There are no completed tasks to clear.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Clear",
            "Are you sure you want to clear your completed tasks from your view?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if username not in DataStore.cleared_tasks:
            DataStore.cleared_tasks[username] = []

        for title in completed_task_titles:
            if title not in DataStore.cleared_tasks[username]:
                DataStore.cleared_tasks[username].append(title)

        try:
            DataStore.save()
            QMessageBox.information(self, "Success", "Completed tasks cleared from your account!")
        except Exception as error:
            QMessageBox.critical(self, "Save Error", f"Could not clear completed tasks:\n{error}")

        self.refresh_data()


class VolunteerWasteReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.report_image_path = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("volCard")
        card_layout = QVBoxLayout(card)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Create Reports")
        title.setObjectName("cardHeading")

        btn_create = QPushButton("Create Report")
        btn_create.setObjectName("primaryButton")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.clicked.connect(self.open_create_report_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_create)
        card_layout.addLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget()

        # My Reports tab
        my_reports_page = QWidget()
        my_reports_layout = QVBoxLayout(my_reports_page)

        self.reports_list = QListWidget()
        self.reports_list.setObjectName("volListWidget")
        apply_smooth_scrolling(self.reports_list)

        my_reports_layout.addWidget(self.reports_list)

        self.tabs.addTab(my_reports_page, "My Reports")

        card_layout.addWidget(self.tabs)
        layout.addWidget(card)

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
        target_dir = Path(__file__).resolve().parent / "data" / "report_images"
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
        """Refresh the logged-in volunteer's own reports."""
        self.reports_list.clear()

        account = Session.current_account
        if account is None:
            return

        records = getattr(DataStore, "report_records", [])

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue

            if record.get("username") != account.username:
                continue

            if index >= len(DataStore.waste_reports):
                continue

            report = DataStore.waste_reports[index]
            moderation = DataStore.get_report_moderation(index) or {}
            status = moderation.get("status", "Pending")

            self.reports_list.addItem(
                QListWidgetItem(f"{report}\nStatus: {status}")
            )

        if self.reports_list.count() == 0:
            self.reports_list.addItem(
                "You have not submitted any waste reports yet."
            )

    def refresh_public_feed(self):
        """Show only approved reports in the public feed."""
        self.public_feed_list.clear()

        account = Session.current_account
        if account is None:
            self.public_feed_list.addItem("Please log in to view the public feed.")
            return

        try:
            approved_reports = DataStore.get_approved_report_records()
        except (AttributeError, TypeError, ValueError) as error:
            QMessageBox.warning(
                self,
                "Feed Error",
                f"Unable to load the public feed:\n{error}"
            )
            return

        if not approved_reports:
            self.public_feed_list.addItem(
                "No approved waste reports are available yet."
            )
            return

        for report_index, report_text, record in approved_reports:
            self._add_public_report_item(
                report_index,
                report_text,
                record,
                account
            )

    def _add_public_report_item(
        self,
        report_index,
        report_text,
        record,
        account
    ):
        """Create one public-feed entry with likes and comments."""
        author_name = record.get("full_name") or record.get("username", "Volunteer")
        username = record.get("username", "unknown")
        location = record.get("location", "Not specified")
        category = record.get("report_type", "General")
        details = record.get("details", "")
        submitted_at = record.get("submitted_at", "")
        image_path = record.get("image_path", "")

        item_widget = QWidget()
        item_layout = QVBoxLayout(item_widget)
        item_layout.setContentsMargins(10, 10, 10, 10)

        # Report author
        author_button = QPushButton(f"{author_name}  (@{username})")
        author_button.setFlat(True)
        author_button.setCursor(Qt.CursorShape.PointingHandCursor)
        author_button.clicked.connect(
            lambda checked=False, user=username:
                self.open_public_volunteer_profile(user)
        )
        item_layout.addWidget(author_button)

        # Report details
        item_layout.addWidget(QLabel(f"Location: {location}"))
        item_layout.addWidget(QLabel(f"Category: {category}"))

        if submitted_at:
            item_layout.addWidget(QLabel(f"Submitted: {submitted_at}"))

        details_label = QLabel(details or report_text)
        details_label.setWordWrap(True)
        item_layout.addWidget(details_label)

        # Report image
        if image_path and Path(image_path).is_file():
            image_label = QLabel()
            pixmap = QPixmap(image_path)

            if not pixmap.isNull():
                image_label.setPixmap(
                    pixmap.scaled(
                        360,
                        240,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
                item_layout.addWidget(image_label)

        # Likes
        likes = record.get("likes", [])
        if not isinstance(likes, list):
            likes = []

        already_liked = any(
            isinstance(name, str)
            and name.casefold() == account.username.casefold()
            for name in likes
        )

        btn_like = QPushButton(
            f"{'Unlike' if already_liked else 'Like'} ({len(likes)})"
        )
        btn_like.clicked.connect(
            lambda checked=False, idx=report_index:
                self.handle_like_report(idx)
        )
        item_layout.addWidget(btn_like)

        # Existing comments
        comments_label = QLabel("Comments")
        comments_label.setStyleSheet("font-weight: bold;")
        item_layout.addWidget(comments_label)

        comments = record.get("comments", [])
        if not isinstance(comments, list):
            comments = []

        if comments:
            for comment in comments:
                if not isinstance(comment, dict):
                    continue

                comment_name = comment.get("full_name", "Volunteer")
                comment_text = comment.get("text", "")
                comment_date = comment.get("submitted_at", "")

                comment_label = QLabel(
                    f"{comment_name}: {comment_text}"
                    + (f"\n{comment_date}" if comment_date else "")
                )
                comment_label.setWordWrap(True)
                item_layout.addWidget(comment_label)
        else:
            item_layout.addWidget(QLabel("No comments yet."))

        # Add a comment
        comment_input = QLineEdit()
        comment_input.setPlaceholderText("Write a comment...")

        btn_comment = QPushButton("Post Comment")
        btn_comment.clicked.connect(
            lambda checked=False,
                   idx=report_index,
                   field=comment_input:
                self.handle_add_comment(idx, field)
        )

        item_layout.addWidget(comment_input)
        item_layout.addWidget(btn_comment)

        # Put each report inside a list item.
        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())

        self.public_feed_list.addItem(list_item)
        self.public_feed_list.setItemWidget(list_item, item_widget)

    def handle_like_report(self, report_index):
        account = Session.current_account
        if account is None:
            QMessageBox.warning(self, "Login Required", "Please log in first.")
            return

        try:
            DataStore.toggle_report_like(report_index, account.username)
            self.refresh_public_feed()

        except (AttributeError, IndexError, ValueError, OSError) as error:
            QMessageBox.warning(
                self,
                "Like Failed",
                f"Unable to update the like:\n{error}"
            )

    def handle_add_comment(self, report_index, comment_input):
        account = Session.current_account
        if account is None:
            QMessageBox.warning(self, "Login Required", "Please log in first.")
            return

        comment_text = comment_input.text().strip()

        if not comment_text:
            QMessageBox.warning(
                self,
                "Empty Comment",
                "Please write a comment before posting."
            )
            return

        try:
            DataStore.add_report_comment(
                report_index,
                account.username,
                account.full_name,
                comment_text
            )
            self.refresh_public_feed()

        except (AttributeError, IndexError, ValueError, OSError) as error:
            QMessageBox.warning(
                self,
                "Comment Failed",
                f"Unable to post the comment:\n{error}"
            )

    def open_public_volunteer_profile(self, username):
        """Display basic public information only."""
        record = next(
            (
                item for item in getattr(DataStore, "report_records", [])
                if isinstance(item, dict)
                and item.get("username", "").casefold() == username.casefold()
            ),
            None
        )

        account = find_account(username)

        dialog = QDialog(self)
        dialog.setWindowTitle("Volunteer Profile")
        dialog.setMinimumWidth(300)

        profile_layout = QVBoxLayout(dialog)

        full_name = (
            record.get("full_name")
            if record else None
        ) or (account.full_name if account else "Volunteer")

        name_label = QLabel(full_name)
        name_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        profile_layout.addWidget(name_label)

        profile_layout.addWidget(QLabel(f"Username: @{username}"))

        # Display a profile picture only if the account has one.
        picture_path = (
            getattr(account, "profile_picture", "") or ""
        ) if account else ""

        if picture_path:
            picture_file = Path(picture_path)

            if not picture_file.is_absolute():
                picture_file = (
                    Path(__file__).resolve().parent / picture_file
                )

            if picture_file.is_file():
                picture_label = QLabel()
                pixmap = QPixmap(str(picture_file))

                if not pixmap.isNull():
                    picture_label.setPixmap(
                        pixmap.scaled(
                            120,
                            120,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                    )
                    profile_layout.addWidget(picture_label)

        profile_layout.addWidget(
            QLabel("Volunteer in the Post-Flood Waste Management System")
        )

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dialog.accept)
        profile_layout.addWidget(btn_close)

        dialog.exec()

    def open_create_report_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Waste Report")
        dialog.setFixedSize(380, 320)

        d_layout = QVBoxLayout(dialog)

        lbl_location = QLabel("Location / Area:")
        txt_location = QLineEdit()

        lbl_type = QLabel("Waste Category:")
        cmb_type = QComboBox()
        cmb_type.addItems([
            "Plastic & Bottles",
            "Flood Mud / Organic",
            "Hazardous / E-Waste",
            "Heavy Debris"
        ])

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
                    dialog, "Input Error", "Please enter a location."
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
                f"📍 {loc} - {report_type} (Submitted: {submitted_at})"
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
                "likes": [],
                "comments": [],
            })

            try:
                DataStore.save()
            except (OSError, TypeError, ValueError) as error:
                # Remove the report entries added by this submission.
                if DataStore.waste_reports and DataStore.waste_reports[-1] == report_entry:
                    DataStore.waste_reports.pop()

                if (
                    DataStore.report_records
                    and DataStore.report_records[-1].get("username") == account.username
                    and DataStore.report_records[-1].get("submitted_at") == submitted_at
                ):
                    DataStore.report_records.pop()

                QMessageBox.critical(
                    dialog,
                    "Save Failed",
                    f"Unable to save the report:\n{error}"
                )
                return

            self.refresh_data()

            if hasattr(self, "public_feed_list"):
                self.refresh_public_feed()

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

        btn_upload_image = QPushButton("Upload Report Image")
        btn_upload_image.clicked.connect(self.choose_report_image)
        d_layout.addWidget(btn_upload_image)

        d_layout.addWidget(btn_submit)
        dialog.exec()

# ==============================================================================
# Screen 3: PublicFeedPage
# ==============================================================================

class VolunteerPublicFeedPage(VolunteerWasteReportsPage):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("volCard")
        card_layout = QVBoxLayout(card)

        header = QHBoxLayout()

        title = QLabel("Public Feed")
        title.setObjectName("cardHeading")

        btn_refresh = QPushButton("Refresh Feed")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_public_feed)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_refresh)

        card_layout.addLayout(header)

        self.public_feed_list = QListWidget()
        self.public_feed_list.setObjectName("volListWidget")
        self.public_feed_list.setSpacing(8)

        # Apply consistent scrolling settings
        apply_smooth_scrolling(self.public_feed_list)

        card_layout.addWidget(self.public_feed_list)

        layout.addWidget(card)

        self.refresh_public_feed()

# ==============================================================================
# Screen 4: Scheduled Cleanup Drives
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

            account = Session.current_account
            joined_by = drive.setdefault("joined_by", [])

            already_joined = (
                account is not None
                and any(
                    isinstance(saved_username, str)
                    and saved_username.casefold()
                    == account.username.casefold()
                    for saved_username in joined_by
                )
            )

            btn_join = QPushButton(
                "Joined" if already_joined else "Join Drive"
            )
            btn_join.setEnabled(
                account is not None and not already_joined
            )

            btn_join.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_join.setObjectName("primaryButton")
             
            def make_join_handler(d=drive):
                def handler():
                    account = Session.current_account
                    if account is None or not account.valid_id_path or not Path(account.valid_id_path).is_file():
                        QMessageBox.warning(
                            self, "Valid ID Required",
                            "Please upload a valid ID in your profile before joining a cleanup drive."
                        )
                        return

                    username = account.username

                    joined_by = d.setdefault("joined_by", [])

                    if not any(
                        isinstance(saved_username, str)
                        and saved_username.casefold() == username.casefold()
                        for saved_username in joined_by
                    ):
                        joined_by.append(username)

                    DataStore.save()
                    self.refresh_data()

                return handler

            btn_join.clicked.connect(make_join_handler())

            i_layout.addLayout(info_v)
            i_layout.addStretch()
            i_layout.addWidget(btn_join)

            self.drives_container.addWidget(drive_box)


# ==============================================================================
# Screen 5: Rewards Page (With Live Pickup Tracker)
# ==============================================================================
class VolunteerRewardsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.lbl_user_points = QLabel(self)
        self.lbl_user_points.setObjectName("pageHeading")
        self.lbl_user_points.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_user_points)

        card = QFrame()
        card.setObjectName("volCard")
        card_layout = QVBoxLayout(card)

        title = QLabel("Claim Your Rewards")
        title.setObjectName("cardHeading")
        card_layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        apply_smooth_scrolling(scroll)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)

        reward_items = [
            "Eco Bag (2 points)", "Water Bottle (1 point)", "Gloves Kit (3 points)", "1KG Rice (5 points)"
        ]
        item_price = [2, 1, 3, 5]

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
                    btn_claim.clicked.connect(
                        lambda _, n=item_name, p=item_price[idx]: self.claim_reward(n, p)
                    )

                    b_layout.addWidget(lbl)
                    b_layout.addWidget(btn_claim)
                    grid.addWidget(r_box, row, col)
                    idx += 1

        scroll.setWidget(grid_widget)
        card_layout.addWidget(scroll)

        claims_group = QGroupBox("My Claimed Items & Pickup Status")
        claims_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; font-size: 13px; }")
        claims_layout = QVBoxLayout(claims_group)

        self.user_claims_list = QListWidget()
        apply_smooth_scrolling(self.user_claims_list)
        self.user_claims_list.setFixedHeight(120)
        self.user_claims_list.setStyleSheet("QListWidget { border: 1px solid #cbd5e1; border-radius: 8px; font-size: 12px; }")
        claims_layout.addWidget(self.user_claims_list)

        card_layout.addWidget(claims_group)
        layout.addWidget(card)

        self.refresh_user_points()

    def refresh_user_points(self):
        if Session.current_account:
            updated_account = find_account(Session.current_account.username)
            if updated_account:
                Session.current_account = updated_account
            
            points_val = Session.current_account.points
            self.lbl_user_points.setText(f"Available Points: {points_val}")
        else:
            self.lbl_user_points.setText("Available Points: 0")

        self.refresh_claim_status()

    def refresh_claim_status(self):
        self.user_claims_list.clear()
        account = Session.current_account
        if not account:
            return

        user_claims = [c for c in getattr(DataStore, "reward_claims", []) if c.get("username") == account.username]
        if not user_claims:
            self.user_claims_list.addItem("No reward claims submitted yet.")
            return

        for claim in reversed(user_claims):
            status_text = (
                f" {claim['item_name']} | Status: [{claim['status']}]\n"
                f"   Pickup Location & Info: {claim['pickup_info']}"
            )
            self.user_claims_list.addItem(status_text)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_user_points()

    def claim_reward(self, item_name, item_cost):
        account = Session.current_account

        if account is None:
            QMessageBox.warning(
                self, "Login Required",
                "Please log in to claim a reward."
            )
            return

        try:
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
                    self, "Account Not Found",
                    "Your saved account could not be found."
                )
                return

            old_points = saved_account.points

            if old_points < item_cost:
                QMessageBox.warning(
                    self, "Insufficient Points",
                    "You don't have enough points to claim this reward."
                )
                return

            old_claims = list(
                getattr(DataStore, "reward_claims", [])
            )

            saved_account.points = old_points - item_cost

            claim_record = {
                "id": max(
                    (
                        claim.get("id", 0)
                        for claim in old_claims
                        if isinstance(claim, dict)
                        and isinstance(claim.get("id"), int)
                    ),
                    default=0
                ) + 1,
                "username": saved_account.username,
                "full_name": saved_account.full_name,
                "item_name": item_name,
                "points_spent": item_cost,
                "status": "Pending Admin Release",
                "pickup_info": (
                    "Awaiting confirmation from Admin on "
                    "nearest district office release."
                ),
                "claimed_at": current_datetime()
            }

            DataStore.reward_claims = old_claims + [claim_record]

            save_accounts(accounts)
            DataStore.save()

            Session.current_account = saved_account
            self.refresh_user_points()

        except Exception as error:
            # Restore in-memory claim data and points.
            if "old_claims" in locals():
                DataStore.reward_claims = old_claims

            if "old_points" in locals():
                try:
                    rollback_accounts = load_accounts()
                    rollback_account = next(
                        (
                            item for item in rollback_accounts
                            if item.username.casefold()
                            == account.username.casefold()
                        ),
                        None
                    )
                    if rollback_account is not None:
                        rollback_account.points = old_points
                        save_accounts(rollback_accounts)
                        Session.current_account = rollback_account
                except Exception:
                    pass

            self.refresh_user_points()
            QMessageBox.critical(
                self, "Reward Claim Failed",
                "Unable to save your reward claim. "
                "Please check your points and claim status before "
                f"trying again.\n\nDetails: {error}"
            )
            return

        QMessageBox.information(
            self, "Reward Claimed",
            f"You claimed '{item_name}'!\n\n"
            "The Admin has been notified. Check the status box "
            "below for item release details."
        )

# ==============================================================================
# Screen 6: Notifications Feed (User-Specific Clear Functionality)
# ==============================================================================
class VolunteerAnnouncementsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("volCard")
        self.card_layout = QVBoxLayout(card)

        # Header with Title and Clear All button
        header_layout = QHBoxLayout()
        title = QLabel("Notifications & Announcements")
        title.setObjectName("cardHeading")

        self.btn_clear_all = QPushButton("Clear All")
        self.btn_clear_all.setObjectName("secondaryButton")
        self.btn_clear_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_all.clicked.connect(self.clear_all_announcements)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_clear_all)
        self.card_layout.addLayout(header_layout)

        # Scrollable Notifications Feed Container
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        apply_smooth_scrolling(scroll)

        self.feed_widget = QWidget()
        self.feed_container = QVBoxLayout(self.feed_widget)
        self.feed_container.setSpacing(10)

        scroll.setWidget(self.feed_widget)
        self.card_layout.addWidget(scroll)

        layout.addWidget(card)

    def _get_announcement_key(self, heading, body):
        return f"{heading}|||{body}"

    def refresh_data(self):
        while self.feed_container.count():
            item = self.feed_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        account = Session.current_account
        username = account.username if account else ""
        
        # Retrieve user-specific cleared notifications
        cleared_keys = DataStore.cleared_announcements.get(username, [])

        visible_announcements = []
        for heading, body in DataStore.announcements:
            key = self._get_announcement_key(heading, body)
            if key not in cleared_keys:
                visible_announcements.append((heading, body, key))

        if not visible_announcements:
            empty_lbl = QLabel("No notifications or announcements.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748b; font-size: 13px; font-style: italic; padding: 20px;")
            self.feed_container.addWidget(empty_lbl)
            self.btn_clear_all.setEnabled(False)
            return

        self.btn_clear_all.setEnabled(True)

        for heading, body, key in visible_announcements:
            box = QFrame()
            box.setObjectName("driveItemBox")
            box.setCursor(Qt.CursorShape.PointingHandCursor)
            
            b_layout = QHBoxLayout(box)

            text_v = QVBoxLayout()
            h_lbl = QLabel(heading)
            h_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #1e3a8a; border: none;")

            preview_body = body[:90] + "..." if len(body) > 90 else body
            b_lbl = QLabel(preview_body)
            b_lbl.setStyleSheet("color: #475569; font-size: 12px; border: none;")
            b_lbl.setWordWrap(True)

            text_v.addWidget(h_lbl)
            text_v.addWidget(b_lbl)

            btn_clear = QPushButton("Clear")
            btn_clear.setObjectName("secondaryButton")
            btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)

            def make_clear_handler(k=key):
                return lambda: self.clear_single_announcement(k)

            btn_clear.clicked.connect(make_clear_handler(key))

            b_layout.addLayout(text_v, 1)
            b_layout.addWidget(btn_clear, 0, Qt.AlignmentFlag.AlignVCenter)

            def make_click_handler(h=heading, b=body):
                return lambda event: self.show_announcement_details(h, b)

            box.mousePressEvent = make_click_handler(heading, body)

            self.feed_container.addWidget(box)

        self.feed_container.addStretch()

    def show_announcement_details(self, heading, body):
        dialog = QDialog(self)
        dialog.setWindowTitle("Notification Details")
        dialog.setFixedWidth(420)

        d_layout = QVBoxLayout(dialog)
        d_layout.setSpacing(12)

        h_lbl = QLabel(heading)
        h_lbl.setStyleSheet("font-weight: bold; font-size: 16px; color: #1e3a8a;")
        h_lbl.setWordWrap(True)

        b_lbl = QTextEdit()
        b_lbl.setReadOnly(True)
        b_lbl.setPlainText(body)
        b_lbl.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; padding: 10px;")

        btn_close = QPushButton("Close")
        btn_close.setObjectName("primaryButton")
        btn_close.clicked.connect(dialog.accept)

        d_layout.addWidget(h_lbl)
        d_layout.addWidget(b_lbl)
        d_layout.addWidget(btn_close)

        dialog.exec()

    def clear_single_announcement(self, key):
        account = Session.current_account
        if not account:
            return
        
        username = account.username
        if username not in DataStore.cleared_announcements:
            DataStore.cleared_announcements[username] = []

        if key not in DataStore.cleared_announcements[username]:
            DataStore.cleared_announcements[username].append(key)
            DataStore.save()

        self.refresh_data()

    def clear_all_announcements(self):
        account = Session.current_account
        if not account:
            return

        reply = QMessageBox.question(
            self, "Clear All Notifications",
            "Are you sure you want to clear all notifications for your account?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            username = account.username
            if username not in DataStore.cleared_announcements:
                DataStore.cleared_announcements[username] = []

            for heading, body in DataStore.announcements:
                key = self._get_announcement_key(heading, body)
                if key not in DataStore.cleared_announcements[username]:
                    DataStore.cleared_announcements[username].append(key)

            DataStore.save()
            self.refresh_data()


# ==============================================================================
# Screen 7: Volunteer Profile
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

        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title = QLabel("My Profile")
        title.setObjectName("cardHeading")
        subtitle = QLabel("View and manage your volunteer information")
        subtitle.setWordWrap(True)

        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header.addLayout(title_column)
        header.addStretch()

        self.btn_edit = QPushButton("Edit Profile")
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.clicked.connect(self.open_edit_dialog)

        header.addWidget(self.btn_edit)
        card_layout.addLayout(header)

        identity = QHBoxLayout()
        self.avatar = QLabel("Add photo")
        self.avatar.setFixedSize(132, 132)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setStyleSheet(
            "background-color: #dbeafe; color: #1d4ed8; border: 3px solid #bfdbfe; border-radius: 66px; font-weight: bold;"
        )

        identity.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignTop)

        identity_text = QVBoxLayout()
        self.name_label = QLabel("Volunteer Name")
        self.name_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #1e293b;")
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
        details.addRow("Emergency contact:", self.emergency_name_value)
        details.addRow("Emergency phone:", self.emergency_phone_value)

        card_layout.addWidget(details_group)

        self.lbl_valid_id_status = QLabel("Valid ID: Not uploaded")
        card_layout.addWidget(self.lbl_valid_id_status)

        self.btn_valid_id = QPushButton("Upload Valid ID")
        self.btn_gallery = QPushButton("Gallery")
        self.btn_recent_posts = QPushButton("Recent Posts")
        self.btn_achievements = QPushButton("Achievements")
        self.btn_change_password = QPushButton("Change Password")
        self.btn_delete_account = QPushButton("Delete Account")

        self.btn_valid_id.clicked.connect(self.upload_valid_id)
        self.btn_gallery.clicked.connect(self.show_gallery)
        self.btn_recent_posts.clicked.connect(self.show_recent_posts)
        self.btn_achievements.clicked.connect(self.show_achievements)
        self.btn_change_password.clicked.connect(self.change_password)
        self.btn_delete_account.clicked.connect(self.delete_account)

        card_layout.addWidget(self.btn_valid_id)
        card_layout.addWidget(self.btn_gallery)
        card_layout.addWidget(self.btn_recent_posts)
        card_layout.addWidget(self.btn_achievements)
        card_layout.addWidget(self.btn_change_password)
        card_layout.addWidget(self.btn_delete_account)

        card_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(card)
        apply_smooth_scrolling(scroll)

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

        self.name_label.setText(account.full_name or "Volunteer")
        self.role_label.setText(account.role or "Volunteer")
        self.username_label.setText(f"Username: {account.username}")
        self.member_since_label.setText(f"Member since: {account.created_at or 'Not available'}")

        self.email_value.setText(getattr(account, "email", "") or "Not provided")
        self.phone_value.setText(getattr(account, "phone", "") or "Not provided")
        self.dob_value.setText(getattr(account, "date_of_birth", "") or "Not provided")
        self.gender_value.setText(getattr(account, "gender", "") or "Not provided")
        self.address_value.setText(getattr(account, "address", "") or "Not provided")
        self.emergency_name_value.setText(getattr(account, "emergency_contact_name", "") or "Not provided")
        self.emergency_phone_value.setText(getattr(account, "emergency_contact_phone", "") or "Not provided")

        self.update_avatar()
        if account.valid_id_path and Path(account.valid_id_path).is_file():
            self.lbl_valid_id_status.setText("Valid ID: Uploaded — Pending Verification")
        else:
            self.lbl_valid_id_status.setText("Valid ID: Not Uploaded")

    
    def upload_valid_id(self):
        account = Session.current_account

        if account is None:
            QMessageBox.warning(
                self, "Error", "No active account found."
            )
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
        project_dir = Path(__file__).resolve().parent
        target_dir = project_dir / "data" / "valid_ids"
        target = None
        old_valid_id_path = getattr(account, "valid_id_path", "")

        try:
            target_dir.mkdir(parents=True, exist_ok=True)

            safe_username = re.sub(
                r"[^A-Za-z0-9_-]", "_", account.username
            )
            target = target_dir / (
                f"{safe_username}_valid_id_{time.time_ns()}"
                f"{source.suffix.lower()}"
            )

            shutil.copy2(source, target)

            # Store a relative path for portability.
            new_valid_id_path = str(target.relative_to(project_dir))

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
                target.unlink(missing_ok=True)
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    "The account could not be found in saved records."
                )
                return

            previous_saved_path = getattr(
                saved_account, "valid_id_path", ""
            )

            saved_account.valid_id_path = new_valid_id_path

            try:
                save_accounts(accounts)
            except Exception:
                saved_account.valid_id_path = previous_saved_path
                account.valid_id_path = old_valid_id_path
                target.unlink(missing_ok=True)
                raise

            # Update the active account after a successful save.
            account.valid_id_path = new_valid_id_path
            Session.login(saved_account)

            self.refresh_data()

            QMessageBox.information(
                self,
                "Upload Successful",
                "Your valid ID has been uploaded successfully."
            )

        except (OSError, ValueError, TypeError, AttributeError) as error:
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

        saved_path = getattr(account, "profile_picture", "") or ""
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
            pixmap.scaled(132, 132, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        )

    def open_edit_dialog(self):
        account = Session.current_account
        if account is None:
            QMessageBox.warning(self, "Profile", "No active account was found.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Profile")
        dialog.resize(520, 650)

        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        apply_smooth_scrolling(scroll)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        photo_row = QHBoxLayout()

        preview = QLabel("No profile picture")
        preview.setFixedSize(100, 100)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setStyleSheet("background-color: #dbeafe; border: 2px solid #bfdbfe; border-radius: 50px;")

        current_picture = getattr(account, "profile_picture", "") or ""
        if current_picture:
            picture_path = Path(current_picture)
            if not picture_path.is_absolute():
                picture_path = Path(__file__).resolve().parent / picture_path
            pixmap = QPixmap(str(picture_path))
            if not pixmap.isNull():
                preview.setText("")
                preview.setPixmap(
                    pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                )

        selected_picture = {"path": ""}

        def choose_picture():
            file_path, _ = QFileDialog.getOpenFileName(dialog, "Choose Profile Picture", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
            if not file_path:
                return

            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                QMessageBox.warning(dialog, "Invalid Image", "Please choose a valid image.")
                return

            selected_picture["path"] = file_path
            preview.setText("")
            preview.setPixmap(
                pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
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
        txt_email = QLineEdit(getattr(account, "email", "") or "")
        txt_phone = QLineEdit(getattr(account, "phone", "") or "")
        txt_dob = QLineEdit(getattr(account, "date_of_birth", "") or "")
        txt_dob.setPlaceholderText("YYYY-MM-DD (optional)")

        cmb_gender = QComboBox()
        cmb_gender.addItems(["Prefer not to say", "Female", "Male", "Non-binary", "Other"])

        saved_gender = getattr(account, "gender", "") or ""
        if saved_gender and cmb_gender.findText(saved_gender) < 0:
            cmb_gender.addItem(saved_gender)
        cmb_gender.setCurrentText(saved_gender or "Prefer not to say")

        txt_address = QTextEdit()
        txt_address.setFixedHeight(75)
        txt_address.setPlainText(getattr(account, "address", "") or "")

        txt_emergency_name = QLineEdit(getattr(account, "emergency_contact_name", "") or "")
        txt_emergency_phone = QLineEdit(getattr(account, "emergency_contact_phone", "") or "")

        form.addRow("Full name *", txt_name)
        form.addRow("Username:", QLabel(f"{account.username} (cannot be changed)"))
        form.addRow("Role:", QLabel(f"{account.role} (assigned by the system)"))
        form.addRow("Email address:", txt_email)
        form.addRow("Phone number:", txt_phone)
        form.addRow("Date of birth:", txt_dob)
        form.addRow("Gender:", cmb_gender)
        form.addRow("Home address:", txt_address)
        form.addRow("Emergency contact name:", txt_emergency_name)
        form.addRow("Emergency contact phone:", txt_emergency_phone)

        content_layout.addLayout(form)
        content_layout.addWidget(QLabel("Username and role cannot be edited here. Only provide personal details you are comfortable sharing."))

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
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
            QMessageBox.warning(self, "Invalid Profile", "Enter a full name with at least 2 characters.")
            return

        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            QMessageBox.warning(self, "Invalid Profile", "Enter a valid email address.")
            return

        if dob:
            try:
                datetime.strptime(dob, "%Y-%m-%d")
            except ValueError:
                QMessageBox.warning(self, "Invalid Profile", "Date of birth must use YYYY-MM-DD.")
                return

        profile_picture = getattr(account, "profile_picture", "") or ""

        if selected_picture["path"]:
            source = Path(selected_picture["path"])
            project_dir = Path(__file__).resolve().parent
            picture_dir = project_dir / "data" / "profile_pictures"
            picture_dir.mkdir(parents=True, exist_ok=True)

            safe_username = re.sub(r"[^A-Za-z0-9_.-]", "_", account.username)
            target = picture_dir / f"{safe_username}_{int(time.time())}{source.suffix.lower()}"

            shutil.copy2(source, target)
            profile_picture = str(target.relative_to(project_dir))

        account.full_name = full_name
        account.email = email
        account.phone = phone
        account.date_of_birth = dob
        account.gender = "" if gender == "Prefer not to say" else gender
        account.address = address
        account.emergency_contact_name = emergency_name
        account.emergency_contact_phone = emergency_phone
        account.profile_picture = profile_picture

        accounts = load_accounts()
        saved_account = next((item for item in accounts if item.username.casefold() == account.username.casefold()), None)

        if saved_account is None:
            QMessageBox.warning(self, "Save Failed", "The account could not be found in saved records.")
            return

        saved_account.full_name = account.full_name
        saved_account.email = account.email
        saved_account.phone = account.phone
        saved_account.date_of_birth = account.date_of_birth
        saved_account.gender = account.gender
        saved_account.address = account.address
        saved_account.emergency_contact_name = account.emergency_contact_name
        saved_account.emergency_contact_phone = account.emergency_contact_phone
        saved_account.profile_picture = account.profile_picture

        save_accounts(accounts)
        Session.login(saved_account)
        self.refresh_data()

        QMessageBox.information(self, "Profile Updated", "Your profile changes have been saved.")

    def show_gallery(self):
        account = Session.current_account
        if account is None:
            return

        records = getattr(DataStore, "report_records", [])
        records = [
            record for record in records
            if record.get("username") == account.username and record.get("image_path") and Path(record["image_path"]).is_file()
        ]
        self._show_post_window("My Gallery", records, images_only=True)

    def show_recent_posts(self):
        account = Session.current_account
        if account is None:
            return

        records = getattr(DataStore, "report_records", [])
        records = [record for record in records if record.get("username") == account.username]
        records.sort(key=lambda record: record.get("submitted_at", ""), reverse=True)
        self._show_post_window("My Recent Posts", records)

    def _show_post_window(self, title, records, images_only=False):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(560, 620)

        outer_layout = QVBoxLayout(dialog)
        scroll_area = QScrollArea()
        apply_smooth_scrolling(scroll_area)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        if not records:
            content_layout.addWidget(QLabel("No posts or images to display yet."))

        for record in records:
            card = QWidget()
            card_layout = QVBoxLayout(card)

            card_layout.addWidget(QLabel(f"<b>{record.get('report_type', 'Waste Report')}</b>"))
            card_layout.addWidget(QLabel(f"Location: {record.get('location', 'Not provided')}"))
            card_layout.addWidget(QLabel(f"Date: {record.get('submitted_at', 'Unknown')}"))

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
                        pixmap.scaled(420, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        current_password = current_input.text()
        new_password = new_input.text()
        confirm_password = confirm_input.text()

        if not account.verify_password(current_password):
            QMessageBox.warning(self, "Invalid Password", "Your current password is incorrect.")
            return

        if len(new_password) < 8:
            QMessageBox.warning(self, "Invalid Password", "The new password must contain at least 8 characters.")
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "Password Mismatch", "The new passwords do not match.")
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
            QMessageBox.critical(self, "Save Failed", f"Unable to save your new password:\n{error}")
            return

        QMessageBox.information(self, "Password Changed", "Your password has been changed successfully.")

    def delete_account(self):
        account = Session.current_account
        if account is None:
            QMessageBox.warning(self, "Error", "No active account found.")
            return

        password, ok = QInputDialog.getText(
            self, "Confirm Account Deletion", "Enter your current password:", QLineEdit.EchoMode.Password
        )
        if not ok:
            return

        if not account.verify_password(password):
            QMessageBox.warning(self, "Incorrect Password", "Your password is incorrect. The account was not deleted.")
            return

        confirmation = QMessageBox.question(
            self, "Permanently Delete Account",
            "Are you sure you want to permanently delete your account?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            accounts = load_accounts()
            remaining_accounts = [s for s in accounts if s.username != account.username]
            if len(remaining_accounts) == len(accounts):
                QMessageBox.warning(self, "Account Not Found", "The account could not be found in saved records.")
                return
            save_accounts(remaining_accounts)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Deletion Failed", f"Unable to delete the account:\n{error}")
            return

        for stored_path in (account.profile_picture, account.valid_id_path):
            if stored_path:
                try:
                    Path(stored_path).unlink(missing_ok=True)
                except OSError:
                    pass

        Session.logout()
        QMessageBox.information(self, "Account Deleted", "Your account has been deleted. The application will now close.")
        QApplication.instance().quit()

    def show_achievements(self):
        QMessageBox.information(
            self, "Achievements",
            "Volunteer Achievements\n\nYour achievements and points appear here.\n\n"
            "Features:\n- Volunteer points tracking\n- Waste reports submitted\n- Cleanup drives attended"
        )


# ==============================================================================
# Screen 8: Volunteer Tickets and Admin Responses
# ==============================================================================
class VolunteerTicketsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("volCard")
        card_layout = QVBoxLayout(card)

        header = QHBoxLayout()

        title = QLabel("Submit Tickets")
        title.setObjectName("cardHeading")

        btn_create = QPushButton("Submit Ticket")
        btn_create.setObjectName("primaryButton")
        btn_create.clicked.connect(self.open_ticket_dialog)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_create)
        card_layout.addLayout(header)

        self.tickets_list = QListWidget()
        self.tickets_list.setObjectName("volListWidget")
        apply_smooth_scrolling(self.tickets_list)

        card_layout.addWidget(self.tickets_list)
        layout.addWidget(card)

    def refresh_data(self):
        self.tickets_list.clear()

        account = Session.current_account
        if account is None:
            return

        tickets = DataStore.get_tickets_for_user(account.username)

        if not tickets:
            self.tickets_list.addItem("You have not submitted any tickets yet.")
            return

        for ticket in reversed(tickets):
            target = ticket.get("reported_username") or "General Complaint"
            response = ticket.get("admin_response") or "No admin response yet."

            item_text = (
                f"Ticket #{ticket.get('id', '?')}\n"
                f"About: {target}\n"
                f"Message: {ticket.get('message', '')}\n"
                f"Status: {ticket.get('status', 'Open')}\n"
                f"Admin Response: {response}"
            )

            self.tickets_list.addItem(item_text)

    def open_ticket_dialog(self):
        account = Session.current_account
        if account is None:
            QMessageBox.warning(
                self, "Login Required",
                "Please log in before submitting a ticket."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Submit a Ticket")
        dialog.resize(420, 300)

        form = QFormLayout(dialog)

        txt_reported_user = QLineEdit()
        txt_reported_user.setPlaceholderText(
            "Optional: enter the volunteer's username"
        )

        txt_message = QTextEdit()
        txt_message.setPlaceholderText(
            "Explain your concern or complaint..."
        )

        form.addRow("Volunteer Username (optional):", txt_reported_user)
        form.addRow("Message:", txt_message)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )

        submit_button = buttons.addButton(
            "Submit",
            QDialogButtonBox.ButtonRole.AcceptRole
        )

        submit_button.clicked.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        form.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        message = txt_message.toPlainText().strip()
        reported_username = txt_reported_user.text().strip()

        if not message:
            QMessageBox.warning(
                self, "Missing Message",
                "Please explain your concern before submitting."
            )
            return

        if reported_username.casefold() == account.username.casefold():
            QMessageBox.warning(
                self, "Invalid Username",
                "You cannot submit a ticket about your own profile."
            )
            return

        try:
            DataStore.create_report_ticket(
                username=account.username,
                message=message,
                reported_username=reported_username or None
            )
            DataStore.save()

        except Exception as error:
            QMessageBox.critical(
                self, "Ticket Submission Failed",
                f"Unable to submit your ticket:\n{error}"
            )
            return

        QMessageBox.information(
            self, "Ticket Submitted",
            "Your ticket has been submitted to the Admin."
        )

        self.refresh_data()

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

        self.stack = QStackedWidget()
        self.page_overview = VolunteerOverviewPage()
        self.page_waste_reports = VolunteerWasteReportsPage()
        self.page_public_feed = VolunteerPublicFeedPage()
        self.page_scheduled_drives = VolunteerScheduledDrivesPage()
        self.page_rewards = VolunteerRewardsPage()
        self.page_announcements = VolunteerAnnouncementsPage()
        self.page_profile = VolunteerProfilePage()
        self.page_tickets = VolunteerTicketsPage()

        self.stack.addWidget(self.page_overview)          # 0
        self.stack.addWidget(self.page_waste_reports)     # 1
        self.stack.addWidget(self.page_public_feed)       # 2
        self.stack.addWidget(self.page_scheduled_drives)  # 3
        self.stack.addWidget(self.page_rewards)           # 4
        self.stack.addWidget(self.page_announcements)     # 5
        self.stack.addWidget(self.page_profile)           # 6
        self.stack.addWidget(self.page_tickets)           # 7

        main_layout.addWidget(self.stack, 1)

        nav_frame = QFrame()
        nav_frame.setObjectName("bottomNavFrame")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(15, 8, 15, 8)

        self.btn_nav_home = QPushButton("    Home  ")
        self.btn_nav_reports = QPushButton(" Waste\nReports")
        self.btn_nav_feed = QPushButton(" Public\nFeed")
        self.btn_nav_drives = QPushButton(" Cleanup\nDrives")
        self.btn_nav_rewards = QPushButton(" Rewards")
        self.btn_nav_announcements = QPushButton(" Notifications")
        self.btn_nav_profile = QPushButton(" View\nProfile")
        self.btn_nav_tickets = QPushButton(" My\nTickets")

        self.nav_buttons = [
            (self.btn_nav_home, 0),
            (self.btn_nav_reports, 1),
             (self.btn_nav_feed, 2),
            (self.btn_nav_drives, 3),
            (self.btn_nav_rewards, 4),
            (self.btn_nav_announcements, 5),
            (self.btn_nav_profile, 6),
            (self.btn_nav_tickets, 7),
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

        # Refresh the selected page
        if current_widget == self.page_public_feed:
            current_widget.refresh_public_feed()
        elif hasattr(current_widget, "refresh_data"):
            current_widget.refresh_data()

        # Update the active navigation button
        for btn, idx in self.nav_buttons:
            is_active = "true" if idx == index else "false"
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def logout(self):
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            from login_window import LoginWindow

            Session.logout()
            self.login_window = LoginWindow()
            self.login_window.show()
            self.close()