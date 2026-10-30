# Import the regular expression module for checking username characters
import re

# Validate the information entered during volunteer registration
def validate_registration(full_name: str, username: str, password: str, confirm_password: str) -> tuple[bool, str]:

    # Remove extra spaces from the beginning and end of the name and username
    full_name = full_name.strip()
    username = username.strip()

    # Check whether the full name is empty
    if not full_name:
        return False, "Please enter your full name."

    # Check whether the full name contains at least 2 characters
    if len(full_name) < 2:
        return False, "Full name must contain at least 2 characters."

    # Check whether the username is empty
    if not username:
        return False, "Please enter a username."

    # Check whether the username is between 3 and 30 characters long
    if len(username) < 3 or len(username) > 30:
        return False, "Username must be 3–30 characters long."

    # Allow only letters, numbers, dots, underscores, and hyphens in usernames
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
        return False, "Username may contain letters, numbers, dots, underscores, and hyphens only."

    # Check whether a password was entered
    if not password:
        return False, "Please enter a password."

    # Check whether the password contains at least 8 characters
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    # Check whether the password and confirmation match
    if password != confirm_password:
        return False, "Passwords do not match."

    # Return success when all registration checks pass
    return True, ""


# Validate the username and password entered during login
def validate_login(username: str, password: str) -> tuple[bool, str]:

    # Check whether the username is empty or contains only spaces
    if not username.strip():
        return False, "Please enter your username."

    # Check whether a password was entered
    if not password:
        return False, "Please enter your password."

    # Return success when both login fields contain input
    return True, ""