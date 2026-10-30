# Import modules for system arguments and file path handling
import sys
from pathlib import Path

# Import PyQt6 application class
from PyQt6.QtWidgets import QApplication

# Import the login window and storage initialization function
from login_window import LoginWindow
from data_manager import initialize_storage

# Load the application's QSS stylesheet
def load_stylesheet(app):
    # Get the path of style.qss in the same folder as this file
    stylesheet_path = Path(__file__).resolve().parent / "style.qss"

    # Apply the stylesheet if the file exists
    if stylesheet_path.exists():
        app.setStyleSheet(stylesheet_path.read_text(encoding="utf-8"))

# Start the Post-Flood Waste Management System
def main():
    # Initialize the storage used by the application
    initialize_storage()

    # Create the PyQt6 application
    app = QApplication(sys.argv)

    # Set the application's name
    app.setApplicationName("Post-Flood Waste Management System")

    # Load the application's visual style
    load_stylesheet(app)

    # Create and display the login window
    window = LoginWindow()
    window.show()

    # Start the application's event loop
    sys.exit(app.exec())

# Run the main function when this file is executed directly
if __name__ == "__main__":
    main()