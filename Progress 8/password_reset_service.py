import random
import smtplib
import os
from email.message import EmailMessage
from PyQt6.QtCore import QThread, pyqtSignal
from data_manager import load_accounts, save_accounts
from waste_management_models import hash_password

# SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_LOGIN = os.getenv("SMTP_LOGIN", "pfwm.noreply@gmail.com").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "szqldlsbmojlvmor").strip()

RESET_CODES = {}
LOGIN_VERIFICATION_CODES = {}


class VerificationEmailThread(QThread):
    """Sends verification emails in the background without freezing the UI."""

    email_result = pyqtSignal(bool, str)

    def __init__(self, recipient_email: str, code: str, purpose: str = "Password Reset"):
        super().__init__()
        self.recipient_email = recipient_email
        self.code = code
        self.purpose = purpose

    def run(self):
        try:
            if not SMTP_LOGIN or not SMTP_PASSWORD:
                raise ValueError(
                    "Email configuration is missing. Please configure SMTP_LOGIN "
                    "and SMTP_PASSWORD."
                )

            msg = EmailMessage()
            msg["Subject"] = f"Your Verification Code - {self.purpose}"
            msg["From"] = SMTP_LOGIN
            msg["To"] = self.recipient_email

            msg.set_content(
                f"Hello,\n\n"
                f"Your 6-digit verification code for {self.purpose} is: {self.code}\n\n"
                f"If you did not request this, please ignore this email."
            )

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_LOGIN, SMTP_PASSWORD)
                server.send_message(msg)

            print(f"   EMAIL SENT SUCCESSFULLY TO: {self.recipient_email}")

            self.email_result.emit(
                True,
                f"Verification code sent to {self.recipient_email}!"
            )

        except Exception as e:
            print(f"   FAILED TO SEND EMAIL VIA SMTP: {e}")
            self.email_result.emit(False, f"Unable to send email: {e}")


def auto_send_reset_code(
    identifier: str,
    thread_holder: list,
    result_callback=None
) -> tuple[bool, str]:
    """Finds a registered account, prints code to terminal, and emails it."""

    key = identifier.strip().casefold()

    if not key:
        return False, "Please enter your username or email address."

    accounts = load_accounts()
    target_account = None

    for acc in accounts:
        acc_username = getattr(acc, "username", "").strip().casefold()
        acc_email = getattr(acc, "email", "").strip().casefold()

        if key == acc_username or key == acc_email:
            target_account = acc
            break

    if target_account is None:
        return False, "No account found with that username or email address."

    target_email = getattr(target_account, "email", "").strip()
    target_username = getattr(target_account, "username", "").strip()

    if not target_email or "@" not in target_email:
        return False, "This account does not have a valid registered email address."

    # Generate 6-digit verification code
    code = f"{random.randint(100000, 999999)}"

    # PRINT CODE TO VS CODE TERMINAL FOR DEBUGGING/TESTING
    print("\n" + "=" * 50)
    print(f"   [PASSWORD RESET CODE GENERATED]")
    print(f"   Target User  : {target_username}")
    print(f"   Target Email : {target_email}")
    print(f"   VERIFICATION CODE : {code}")
    print("=" * 50 + "\n")

    RESET_CODES[target_username.casefold()] = code
    RESET_CODES[target_email.casefold()] = code

    email_thread = VerificationEmailThread(
        target_email,
        code,
        purpose="Password Reset"
    )

    if result_callback:
        email_thread.email_result.connect(result_callback)

    thread_holder.append(email_thread)
    email_thread.start()

    return True, f"Sending verification code to {target_email}..."


def send_login_verification_code(
    username_or_email: str,
    recipient_email: str,
    thread_holder: list
) -> tuple[bool, str]:
    """Sends a login verification code to the supplied email address."""

    if not recipient_email or "@" not in recipient_email:
        return False, "Invalid target email address."

    code = f"{random.randint(100000, 999999)}"
    key = username_or_email.strip().casefold()

    # PRINT CODE TO TERMINAL
    print("\n" + "=" * 50)
    print(f"   [LOGIN 2FA CODE GENERATED]")
    print(f"   Target Email : {recipient_email}")
    print(f"   VERIFICATION CODE : {code}")
    print("=" * 50 + "\n")

    LOGIN_VERIFICATION_CODES[key] = code

    email_thread = VerificationEmailThread(
        recipient_email.strip(),
        code,
        purpose="Login Verification"
    )

    thread_holder.append(email_thread)
    email_thread.start()

    return True, f"Sending login verification code to {recipient_email}..."


def verify_login_code(username_or_email: str, input_code: str) -> bool:
    """Verifies the login verification code."""

    key = username_or_email.strip().casefold()
    saved_code = LOGIN_VERIFICATION_CODES.get(key)

    if saved_code and input_code.strip() == saved_code:
        LOGIN_VERIFICATION_CODES.pop(key, None)
        return True

    return False


def confirm_and_update_password(
    identifier: str,
    input_code: str,
    new_password: str
) -> tuple[bool, str]:
    """Validates the reset code and updates the account password."""

    key = identifier.strip().casefold()
    saved_code = RESET_CODES.get(key)

    if not saved_code or input_code.strip() != saved_code:
        return False, "Invalid or expired verification code."

    accounts = load_accounts()
    target_account = None

    for acc in accounts:
        acc_username = getattr(acc, "username", "").strip().casefold()
        acc_email = getattr(acc, "email", "").strip().casefold()

        if key == acc_username or key == acc_email:
            target_account = acc
            break

    if target_account is None:
        return False, "Account record not found."

    if hasattr(target_account, "set_password"):
        target_account.set_password(new_password)
    else:
        target_account.password_hash, target_account.salt = hash_password(new_password)

    save_accounts(accounts)

    RESET_CODES.pop(target_account.username.casefold(), None)

    target_email = getattr(target_account, "email", "").strip().casefold()
    if target_email:
        RESET_CODES.pop(target_email, None)

    return True, "Password reset successfully!"