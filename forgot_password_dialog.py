from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox
)

from password_reset_service import (
    auto_send_reset_code,
    confirm_and_update_password
)


class ForgotPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Reset Password")
        self.resize(360, 260)

        self.active_threads = []

        layout = QVBoxLayout()

        self.info_label = QLabel(
            "Enter your registered username or email:"
        )
        layout.addWidget(self.info_label)

        self.identifier_input = QLineEdit()
        self.identifier_input.setPlaceholderText(
            "Username or email address"
        )
        layout.addWidget(self.identifier_input)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText(
            "6-digit verification code"
        )
        self.code_input.hide()
        layout.addWidget(self.code_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(
            "Enter new password"
        )
        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self.password_input.hide()
        layout.addWidget(self.password_input)

        self.action_btn = QPushButton("Send Code to Email")
        self.action_btn.clicked.connect(self.handle_action)
        layout.addWidget(self.action_btn)

        self.setLayout(layout)

        self.step = 1

    def handle_action(self):
        if self.step == 1:
            identifier = self.identifier_input.text().strip()

            if not identifier:
                QMessageBox.warning(
                    self,
                    "Input Error",
                    "Please enter your username or email address."
                )
                return

            self.action_btn.setEnabled(False)
            self.action_btn.setText("Sending email...")

            success, message = auto_send_reset_code(
                identifier,
                self.active_threads,
                self.handle_email_result
            )

            if not success:
                self.action_btn.setEnabled(True)
                self.action_btn.setText("Send Code to Email")

                QMessageBox.warning(
                    self,
                    "Unable to Send Code",
                    message
                )
            else:
                self.info_label.setText(
                    "Please wait while we send your verification code."
                )

        elif self.step == 2:
            identifier = self.identifier_input.text().strip()
            code = self.code_input.text().strip()
            new_password = self.password_input.text()

            if not code or not new_password:
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    "Please enter the code and your new password."
                )
                return

            success, message = confirm_and_update_password(
                identifier,
                code,
                new_password
            )

            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    message
                )
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    "Password Reset Failed",
                    message
                )

    def handle_email_result(self, success, message):
        self.action_btn.setEnabled(True)

        if success:
            QMessageBox.information(
                self,
                "Code Sent",
                message
            )

            self.identifier_input.setReadOnly(True)

            self.info_label.setText(
                "Enter the verification code and your new password:"
            )

            self.code_input.show()
            self.password_input.show()

            self.action_btn.setText("Reset Password")
            self.step = 2

        else:
            QMessageBox.warning(
                self,
                "Email Sending Failed",
                message
            )

            self.action_btn.setText("Send Code to Email")