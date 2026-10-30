# Import Qt alignment options and required PyQt6 widgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QMessageBox

# Import Session to access the currently logged-in account
from waste_management_models import Session

# Create the Admin Dashboard window
class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()

        # Set the window title and minimum size
        self.setWindowTitle("Admin Dashboard | Post-Flood Waste Management")
        self.setMinimumSize(560, 400)

        # Create the main vertical layout and set its margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)

        # Create and format the dashboard title
        title = QLabel("Admin Dashboard")
        title.setObjectName("pageHeading")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Get the currently logged-in account
        account = Session.current_account

        # Display the account's full name or use "Administrator" if no account is available
        welcome = QLabel(f"Welcome, {account.full_name if account else 'Administrator'}!")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Display the current system status and planned features
        info = QLabel(
            "The login system is connected.\n\n"
            "Next features to add:\n"
            "• Manage cleanup schedules\n"
            "• Review waste reports\n"
            "• Post announcements"
        )
        info.setObjectName("dashboardInfo")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the Log Out button and connect it to the logout function
        logout = QPushButton("Log Out")
        logout.setObjectName("primaryButton")
        logout.clicked.connect(self.logout)

        # Add the widgets to the main layout
        layout.addWidget(title)
        layout.addWidget(welcome)
        layout.addWidget(info, 1)
        layout.addWidget(logout)

    # Log out the current account and return to the login window
    def logout(self):
        # Import LoginWindow when the logout function is called
        from login_window import LoginWindow

        # Clear the current login session
        Session.logout()

        # Create and display a new login window
        self.login_window = LoginWindow()
        self.login_window.show()

        # Close the admin dashboard
        self.close()