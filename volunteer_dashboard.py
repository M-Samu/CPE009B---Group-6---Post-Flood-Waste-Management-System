# Import Qt tools for alignment
from PyQt6.QtCore import Qt

# Import widgets used to build the volunteer dashboard
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout

# Import the session class to access the logged-in account
from waste_management_models import Session

# Volunteer dashboard class
class VolunteerDashboard(QWidget):

    # Initialize the volunteer dashboard
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Volunteer Dashboard | Post-Flood Waste Management"
        )
        self.setMinimumSize(560, 400)

        # Create the main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)

        # Create the dashboard title
        title = QLabel("Volunteer Dashboard")
        title.setObjectName("pageHeading")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Get the currently logged-in account
        account = Session.current_account

        # Display a welcome message using the account's full name
        welcome = QLabel(
            f"Welcome, {account.full_name if account else 'Volunteer'}!"
        )
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Display information about planned volunteer features
        info = QLabel(
            "Your volunteer account is ready.\n\n"
            "Next features to add:\n"
            "• View and join cleanup drives\n"
            "• Check announcements and notifications\n"
            "• Submit waste reports"
        )
        info.setObjectName("dashboardInfo")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the logout button
        logout = QPushButton("Log Out")
        logout.setObjectName("primaryButton")
        logout.clicked.connect(self.logout)

        # Add the widgets to the dashboard layout
        layout.addWidget(title)
        layout.addWidget(welcome)
        layout.addWidget(info, 1)
        layout.addWidget(logout)

    # Log out the volunteer and return to the login window
    def logout(self):
        # Import the login window when logout is requested
        from login_window import LoginWindow

        # Clear the current user session
        Session.logout()

        # Create and display a new login window
        self.login_window = LoginWindow()
        self.login_window.show()

        # Close the volunteer dashboard
        self.close()