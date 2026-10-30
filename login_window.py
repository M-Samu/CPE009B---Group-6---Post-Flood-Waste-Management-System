# Import Qt tools for alignment, animations, and window movement
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint

# Import widgets used to build the login interface
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
    QVBoxLayout, QHBoxLayout, QMessageBox, QFrame
)

# Import functions and classes needed for login and navigation
from data_manager import find_account
from input_validation import validate_login
from waste_management_models import Session
from registration_window import RegistrationWindow
from admin_dashboard import AdminDashboard
from volunteer_dashboard import VolunteerDashboard

# Login window class
class LoginWindow(QWidget):
    # Initialize the login window
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login | Post-Flood Waste Management System")
        self.setFixedSize(440, 510)

        # Store references to other windows
        self.dashboard = None
        self.registration_window = None

        # Build the login interface
        self._build_ui()

    # Build the login interface and its layout
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(13)

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

        # Create the show-password checkbox
        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(self.toggle_password)

        # Create the status label for login messages
        self.status = QLabel("")
        self.status.setObjectName("statusLabel")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the login button
        self.login_button = QPushButton("Log In")
        self.login_button.setObjectName("primaryButton")
        self.login_button.clicked.connect(self.login)

        # Create the clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("secondaryButton")
        self.clear_button.clicked.connect(self.clear_fields)

        # Create the registration navigation button
        self.register_button = QPushButton("Create Volunteer Account")
        self.register_button.setObjectName("linkButton")
        self.register_button.clicked.connect(self.open_registration)

        # Arrange the clear and login buttons in one row
        button_row = QHBoxLayout()
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.login_button, 2)

        # Add the widgets to the main layout
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(hint)
        layout.addSpacing(8)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.show_password)
        layout.addWidget(self.status)
        layout.addLayout(button_row)
        layout.addWidget(self.register_button)
        layout.addStretch()

        # Add the footnote at the bottom of the window
        footnote = QLabel("Community cleanup starts with you.")
        footnote.setObjectName("mutedText")
        footnote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footnote)

    # Show or hide the password text
    def toggle_password(self, checked: bool):
        self.password.setEchoMode(
            QLineEdit.EchoMode.Normal
            if checked else QLineEdit.EchoMode.Password
        )

    # Clear the username, password, and status message
    def clear_fields(self):
        self.username.clear()
        self.password.clear()
        self.status.clear()
        self.username.setFocus()

    # Validate the login details and open the correct dashboard
    def login(self):
        # Get the username and password entered by the user
        username = self.username.text().strip()
        password = self.password.text()

        # Check whether the login fields contain valid input
        valid, message = validate_login(username, password)

        # Display an error if the input is invalid
        if not valid:
            self.status.setText(message)
            self.status.setProperty("state", "error")
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self._shake()
            return

        # Search for the account in the stored account data
        try:
            account = find_account(username)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Data Error", str(exc))
            return

        # Check whether the account exists and the password is correct
        if account is None or not account.verify_password(password):
            self.status.setText("Incorrect username or password.")
            self.status.setProperty("state", "error")
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self.password.clear()
            self._shake()
            return

        # Save the logged-in account in the current session
        Session.login(account)

        # Open the dashboard based on the account's role
        if account.role == "Admin":
            self.dashboard = AdminDashboard()
        else:
            self.dashboard = VolunteerDashboard()

        # Display the dashboard and close the login window
        self.dashboard.show()
        self.close()

    # Open the volunteer registration window
    def open_registration(self):
        self.registration_window = RegistrationWindow()

        # Listen for successful registration
        self.registration_window.registration_successful.connect(
            self._registration_completed
        )

        # Display registration and hide the login window
        self.registration_window.show()
        self.hide()

    # Return to login after successful registration
    def _registration_completed(self, username: str):
        self.username.setText(username)
        self.password.clear()
        self.show()
        self.raise_()
        self.activateWindow()

    # Shake the login window when login validation fails
    def _shake(self):
        # Get the window's current position
        start_pos = self.pos()

        # Create an animation for the window movement
        animation = QPropertyAnimation(self, b"pos", self)
        animation.setDuration(280)

        # Set the movement points for the shaking effect
        animation.setKeyValueAt(0, start_pos)
        animation.setKeyValueAt(0.25, start_pos + QPoint(-8, 0))
        animation.setKeyValueAt(0.5, start_pos + QPoint(8, 0))
        animation.setKeyValueAt(0.75, start_pos + QPoint(-5, 0))
        animation.setKeyValueAt(1, start_pos)

        # Set the animation easing and keep a reference to it
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._shake_animation = animation

        # Start the shaking animation
        animation.start()