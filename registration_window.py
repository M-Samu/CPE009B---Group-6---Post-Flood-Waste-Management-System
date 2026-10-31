# Import Qt tools for alignment and custom signals
from PyQt6.QtCore import Qt, pyqtSignal

# Import widgets used to build the registration interface
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
    QVBoxLayout, QHBoxLayout, QMessageBox
)

# Import registration and input validation functions
from data_manager import register_volunteer
from input_validation import validate_registration

# Registration window class
class RegistrationWindow(QWidget):

    # Signal emitted when registration is completed or the window is closed
    registration_successful = pyqtSignal(str)

    # Initialize the registration window
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Volunteer Registration")
        self.setFixedSize(440, 610)

        # Track whether registration was completed successfully
        self._registered = False

        # Build the registration interface
        self._build_ui()

    # Build the registration interface and layout
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(12)

        # Create the application title
        title = QLabel("JOIN THE COMMUNITY")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the registration heading
        heading = QLabel("Create an account")
        heading.setObjectName("pageHeading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the registration subtitle
        subtitle = QLabel("Register as a cleanup volunteer")
        subtitle.setObjectName("mutedText")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the full name input field
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Full name")

        # Create the email address input field
        self.email = QLineEdit()
        self.email.setPlaceholderText("Email address")

        # Create the username input field
        self.username = QLineEdit()
        self.username.setPlaceholderText("Create username")

        # Create the password input field
        self.password = QLineEdit()
        self.password.setPlaceholderText(
            "Create password (at least 8 characters)"
        )
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        # Create the password confirmation field
        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Confirm password")
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)

        # Create the checkbox for showing or hiding passwords
        self.show_password = QCheckBox("Show passwords")
        self.show_password.toggled.connect(self.toggle_passwords)

        # Create the status label for registration messages
        self.status = QLabel("")
        self.status.setObjectName("statusLabel")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the registration button
        self.register_button = QPushButton("Register")
        self.register_button.setObjectName("primaryButton")
        self.register_button.clicked.connect(self.register)

        # Create the button for returning to the login window
        self.back_button = QPushButton("Back to Login")
        self.back_button.setObjectName("secondaryButton")
        self.back_button.clicked.connect(self.close)

        # Add the widgets to the registration layout
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.full_name)
        layout.addWidget(self.email)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.confirm_password)
        layout.addWidget(self.show_password)
        layout.addWidget(self.status)
        layout.addWidget(self.register_button)
        layout.addWidget(self.back_button)
        layout.addStretch()

    # Show or hide both password fields
    def toggle_passwords(self, checked: bool):
        mode = (
            QLineEdit.EchoMode.Normal
            if checked else QLineEdit.EchoMode.Password
        )
        self.password.setEchoMode(mode)
        self.confirm_password.setEchoMode(mode)

    # Validate the registration details and create an account
    def register(self):
        # Get the registration details entered by the user
        full_name = self.full_name.text().strip()
        email = self.email.text().strip()
        username = self.username.text().strip()
        password = self.password.text()
        confirm_password = self.confirm_password.text()

        # Validate the registration input
        valid, message = validate_registration(
            full_name, username, password, confirm_password
        )

        # Additional quick email check
        if valid and ("@" not in email or "." not in email):
            valid = False
            message = "Please enter a valid email address."

        # Display an error if the input is invalid
        if not valid:
            self._show_status(message, "error")
            return

        # Save the new volunteer account with email
        try:
            success, message = register_volunteer(
                full_name, email, username, password
            )
        except (OSError, RuntimeError) as exc:
            # Display an error if the account cannot be saved
            QMessageBox.critical(
                self,
                "Save Error",
                f"Could not save the account:\n{exc}"
            )
            return

        # Display a message when registration succeeds
        if success:
            QMessageBox.information(
                self, "Registration Complete", message
            )

            # Mark registration as completed
            self._registered = True

            # Notify the login window of the new username
            self.registration_successful.emit(username)

            # Close the registration window
            self.close()
        else:
            # Display an error if registration fails
            self._show_status(message, "error")

    # Display a status message and set its state
    def _show_status(self, message: str, state: str):
        self.status.setText(message)
        self.status.setProperty("state", state)

        # Refresh the stylesheet to apply the status color
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    # Handle the registration window closing event
    def closeEvent(self, event):
        # If registration was not completed, notify the login window
        if not self._registered:
            self.registration_successful.emit("")

        # Continue with the normal window closing process
        super().closeEvent(event)