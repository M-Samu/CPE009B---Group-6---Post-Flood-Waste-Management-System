# Import JSON for reading and writing account data
import json

# Import Path for handling file and directory paths
from pathlib import Path

# Import the Account class for creating and loading user accounts
from waste_management_models import Account

# Define the main project directory
BASE_DIR = Path(__file__).resolve().parent

# Define the folder where application data will be stored
DATA_DIR = BASE_DIR / "data"

# Define the JSON file used to store account information
ACCOUNTS_FILE = DATA_DIR / "accounts.json"

# Initialize the storage folder and account data file
def initialize_storage():
    # Create the data directory if it does not exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create an empty account list if the JSON file does not exist
    if not ACCOUNTS_FILE.exists():
        ACCOUNTS_FILE.write_text("[]", encoding="utf-8")

    # Load the existing accounts from the JSON file
    accounts = load_accounts()

    # Demo account for initial testing only. Change its password after first use.
    # Create the default administrator account if one does not already exist
    if not any(account.username.casefold() == "admin" for account in accounts):
        accounts.append(
            Account.create(
                "admin", "System Administrator", "admin123", "Admin", email="pfwm.noreply@gmail.com"
            )
        )

        # Save the updated account list
        save_accounts(accounts)

# Load account information from the JSON file
def load_accounts() -> list[Account]:
    # Make sure the data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Return an empty list if the account file does not exist
    if not ACCOUNTS_FILE.exists():
        return []

    # Read and convert the stored JSON data into Account objects
    try:
        raw_data = json.loads(
            ACCOUNTS_FILE.read_text(encoding="utf-8")
        )
        return [Account.from_dict(item) for item in raw_data]

    # Raise an error if the account data cannot be read or converted
    except (json.JSONDecodeError, TypeError, ValueError):
        raise RuntimeError(
            f"Could not read {ACCOUNTS_FILE}. The account data file may be damaged."
        )

# Save account information to the JSON file
def save_accounts(accounts: list[Account]) -> None:
    # Make sure the data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create a temporary file before replacing the account file
    temp_file = ACCOUNTS_FILE.with_suffix(".tmp")

    # Convert Account objects into dictionaries and save them as JSON
    temp_file.write_text(
        json.dumps([account.to_dict() for account in accounts], indent=4),
        encoding="utf-8",
    )

    # Replace the old account file with the updated temporary file
    temp_file.replace(ACCOUNTS_FILE)

# Find an account using its username
def find_account(username: str) -> Account | None:
    # Remove surrounding spaces and ignore differences in letter case
    username_key = username.strip().casefold()

    # Return the matching account or None if no match is found
    return next(
        (account for account in load_accounts()
         if account.username.casefold() == username_key),
        None,
    )

# Register a new volunteer account
def register_volunteer(full_name: str, email: str, username: str, password: str) -> tuple[bool, str]:
    # Load the existing account list
    accounts = load_accounts()

    # Prepare keys for case-insensitive comparison
    username_key = username.strip().casefold()
    email_key = email.strip().casefold()

    # Prevent registration if username or email is already in use
    if any(account.username.casefold() == username_key for account in accounts):
        return False, "That username is already registered."

    if any(account.email.casefold() == email_key for account in accounts):
        return False, "That email address is already registered."

    # Create and add the new volunteer account
    accounts.append(Account.create(username, full_name, password, "Volunteer", email=email))

    # Save the updated account list
    save_accounts(accounts)

    # Return a success message after registration
    return True, "Registration successful. You can now log in."

def award_volunteer_points(username: str, points_to_add: int) -> tuple[bool, str]:
    accounts = load_accounts()
    target_account = next(
        (acc for acc in accounts if acc.username.casefold() == username.strip().casefold()),
        None
    )

    if not target_account:
        return False, "Volunteer account not found."

    if target_account.role != "Volunteer":
        return False, "Can only award points to Volunteer accounts."

    target_account.points += points_to_add
    save_accounts(accounts)
    return True, f"Successfully awarded {points_to_add} points to {target_account.full_name}!"