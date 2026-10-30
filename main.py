import sys
from PyQt6.QtWidgets import QApplication
from pathlib import Path

from data_manager import initialize_storage
from login_window import LoginWindow


def main():
    # 1. Initialize data directory & default admin account
    initialize_storage()

    # 2. Create Qt Application instance
    app = QApplication(sys.argv)

    # 3. Apply QSS Stylesheet if present
    style_path = Path(__file__).resolve().parent / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))

    # 4. Launch the initial Login Window
    login = LoginWindow()
    login.show()

    # 5. Start main event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()