# Import Qt tools for alignment, animations, and window movement
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint

# Import widgets used to build the login interface
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
    QVBoxLayout, QHBoxLayout, QMessageBox, QFrame, QStackedWidget
)

# Import functions and classes needed for login and navigation
from data_manager import find_account
from input_validation import validate_login
from waste_management_models import Session
from registration_window import RegistrationWindow
from admin_dashboard import AdminDashboard
from volunteer_dashboard import VolunteerDashboard
from password_reset_service import (
    auto_send_reset_code,
    confirm_and_update_password
)

# Login window class
class LoginWindow(QWidget):
    # Initialize the login window
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login | Post-Flood Waste Management System")
        self.setFixedSize(440, 530)

        # Store references to other windows
        self.dashboard = None
        self.registration_window = None

        # Build the login interface
        self._build_ui()

    # Build the login interface and its layout
    def _build_ui(self):
        # Create a container stacked widget to swap views in the same window
        self.stacked_widget = QStackedWidget(self)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stacked_widget)

        # ---------------------------------------------------------
        # PAGE 1: LOGIN VIEW
        # ---------------------------------------------------------
        self.login_page = QWidget()
        login_layout = QVBoxLayout(self.login_page)
        login_layout.setContentsMargins(36, 30, 36, 30)
        login_layout.setSpacing(13)

        # Create the application title
        title = QLabel("POST-FLOOD WASTE")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the application subtitle
        subtitle = QLabel("MANAGEMENT SYSTEM")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the welcome heading
        heading = QLabel("Welcome back")
        heading.setObjectName("pageHeading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create a short instruction below the heading
        hint = QLabel("Log in to continue")
        hint.setObjectName("mutedText")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the username input field
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setClearButtonEnabled(True)

        # Create the password input field
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        # Allow the Enter key to trigger login
        self.password.returnPressed.connect(self.login)

        # Create options row (Show password checkbox & Forgot password button)
        options_row = QHBoxLayout()

        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(self.toggle_password)

        self.forgot_password_button = QPushButton("Forgot password?")
        self.forgot_password_button.setObjectName("linkButton")
        self.forgot_password_button.clicked.connect(self.show_reset_page)

        options_row.addWidget(self.show_password)
        options_row.addStretch()
        options_row.addWidget(self.forgot_password_button)

        # Create the status label for login messages
        self.status = QLabel("")
        self.status.setObjectName("statusLabel")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the login button
        self.login_button = QPushButton("Log In")
        self.login_button.setObjectName("primaryButton")
        self.login_button.clicked.connect(self.login)

        # Create the registration navigation button
        self.register_button = QPushButton("Create Volunteer Account")
        self.register_button.setObjectName("linkButton")
        self.register_button.clicked.connect(self.open_registration)

        # Arrange the clear and login buttons in one row
        button_row = QHBoxLayout()
        button_row.addWidget(self.login_button, 2)

        # Add the widgets to the login layout
        login_layout.addWidget(title)
        login_layout.addWidget(subtitle)
        login_layout.addSpacing(12)
        login_layout.addWidget(heading)
        login_layout.addWidget(hint)
        login_layout.addSpacing(8)
        login_layout.addWidget(self.username)
        login_layout.addWidget(self.password)
        login_layout.addLayout(options_row)
        login_layout.addWidget(self.status)
        login_layout.addLayout(button_row)
        login_layout.addWidget(self.register_button)
        login_layout.addStretch()

        # Add the footnote at the bottom of the window
        footnote = QLabel("Community cleanup starts with you.")
        footnote.setObjectName("mutedText")
        footnote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(footnote)

        # ---------------------------------------------------------
        # PAGE 2: RESET PASSWORD VIEW (Same Window)
        # ---------------------------------------------------------
        self.reset_page = QWidget()
        reset_layout = QVBoxLayout(self.reset_page)
        reset_layout.setContentsMargins(36, 30, 36, 30)
        reset_layout.setSpacing(11)

        reset_title = QLabel("RESET PASSWORD")
        reset_title.setObjectName("appTitle")
        reset_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.reset_info = QLabel("Enter your registered username or email:")
        self.reset_info.setObjectName("mutedText")
        self.reset_info.setWordWrap(True)
        self.reset_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.reset_identifier = QLineEdit()
        self.reset_identifier.setPlaceholderText("Username or email address")
        self.reset_identifier.setClearButtonEnabled(True)

        self.reset_code = QLineEdit()
        self.reset_code.setPlaceholderText("6-digit verification code")
        self.reset_code.hide()

        self.reset_new_password = QLineEdit()
        self.reset_new_password.setPlaceholderText("Enter new password")
        self.reset_new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reset_new_password.hide()

        self.reset_status = QLabel("")
        self.reset_status.setObjectName("statusLabel")
        self.reset_status.setWordWrap(True)
        self.reset_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.reset_action_btn = QPushButton("Send Code to Email")
        self.reset_action_btn.setObjectName("primaryButton")
        self.reset_action_btn.clicked.connect(self.handle_reset_action)

        self.reset_back_btn = QPushButton("Back to Login")
        self.reset_back_btn.setObjectName("linkButton")
        self.reset_back_btn.clicked.connect(self.show_login_page)

        reset_layout.addWidget(reset_title)
        reset_layout.addSpacing(10)
        reset_layout.addWidget(self.reset_info)
        reset_layout.addSpacing(10)
        reset_layout.addWidget(self.reset_identifier)
        reset_layout.addWidget(self.reset_code)
        reset_layout.addWidget(self.reset_new_password)
        reset_layout.addWidget(self.reset_status)
        reset_layout.addWidget(self.reset_action_btn)
        reset_layout.addWidget(self.reset_back_btn)
        reset_layout.addStretch()

        # Add both pages to the stack
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.reset_page)

        # Track reset state and thread references
        self.reset_step = 1
        self.active_threads = []

    # Show or hide the password text
    def toggle_password(self, checked: bool):
        self.password.setEchoMode(
            QLineEdit.EchoMode.Normal
            if checked else QLineEdit.EchoMode.Password
        )

    # Validate the login details and open the correct dashboard
    def login(self):
        username = self.username.text().strip()
        password = self.password.text()

        valid, message = validate_login(username, password)

        if not valid:
            self.status.setText(message)
            self.status.setProperty("state", "error")
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self._shake()
            return

        try:
            account = find_account(username)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Data Error", str(exc))
            return

        if account is None or not account.verify_password(password):
            self.status.setText("Incorrect username or password.")
            self.status.setProperty("state", "error")
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self.password.clear()
            self._shake()
            return

        Session.login(account)

        if account.role == "Admin":
            self.dashboard = AdminDashboard()
        else:
            self.dashboard = VolunteerDashboard()

        self.dashboard.show()
        self.close()

    # Open the volunteer registration window
    def open_registration(self):
        self.registration_window = RegistrationWindow()
        self.registration_window.registration_successful.connect(
            self._registration_completed
        )
        self.registration_window.show()
        self.hide()

    # Switch view to password reset inside the same window
    def show_reset_page(self):
        self.reset_step = 1
        self.reset_identifier.clear()
        self.reset_identifier.setReadOnly(False)
        self.reset_code.clear()
        self.reset_code.hide()
        self.reset_new_password.clear()
        self.reset_new_password.hide()
        self.reset_info.setText("Enter your registered username or email:")
        self.reset_action_btn.setText("Send Code to Email")
        self.reset_action_btn.setEnabled(True)
        self.reset_status.setText("")
        self.stacked_widget.setCurrentWidget(self.reset_page)

    # Switch back to login page
    def show_login_page(self):
        self.status.setText("")
        self.stacked_widget.setCurrentWidget(self.login_page)

    # Handle sending reset code and resetting password
    def handle_reset_action(self):
        if self.reset_step == 1:
            identifier = self.reset_identifier.text().strip()
            if not identifier:
                self.reset_status.setText("Please enter your username or email address.")
                return

            self.reset_action_btn.setEnabled(False)
            self.reset_action_btn.setText("Sending email...")

            success, message = auto_send_reset_code(
                identifier,
                self.active_threads,
                self.handle_reset_email_result
            )

            if not success:
                self.reset_action_btn.setEnabled(True)
                self.reset_action_btn.setText("Send Code to Email")
                self.reset_status.setText(message)
            else:
                self.reset_info.setText("Please wait while we send your verification code.")

        elif self.reset_step == 2:
            identifier = self.reset_identifier.text().strip()
            code = self.reset_code.text().strip()
            new_password = self.reset_new_password.text()

            if not code or not new_password:
                self.reset_status.setText("Please enter the code and your new password.")
                return

            success, message = confirm_and_update_password(
                identifier,
                code,
                new_password
            )

            if success:
                QMessageBox.information(self, "Success", message)
                self.show_login_page()
            else:
                self.reset_status.setText(message)

    # Callback when email thread completes
    def handle_reset_email_result(self, success, message):
        self.reset_action_btn.setEnabled(True)

        if success:
            QMessageBox.information(self, "Code Sent", message)
            self.reset_identifier.setReadOnly(True)
            self.reset_info.setText("Enter the verification code and your new password:")
            self.reset_code.show()
            self.reset_new_password.show()
            self.reset_action_btn.setText("Reset Password")
            self.reset_status.setText("")
            self.reset_step = 2
        else:
            self.reset_status.setText(message)
            self.reset_action_btn.setText("Send Code to Email")

    # Return to login after successful registration
    def _registration_completed(self, username: str):
        self.username.setText(username)
        self.password.clear()
        self.show()
        self.raise_()
        self.activateWindow()

    # Shake animation for validation errors
    def _shake(self):
        start_pos = self.pos()
        animation = QPropertyAnimation(self, b"pos", self)
        animation.setDuration(280)

        animation.setKeyValueAt(0, start_pos)
        animation.setKeyValueAt(0.25, start_pos + QPoint(-8, 0))
        animation.setKeyValueAt(0.5, start_pos + QPoint(8, 0))
        animation.setKeyValueAt(0.75, start_pos + QPoint(-5, 0))
        animation.setKeyValueAt(1, start_pos)

        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._shake_animation = animation
        animation.start()