# Import dataclass for automatically creating class methods
from dataclasses import dataclass

# Import datetime to record account creation dates and times
from datetime import datetime

# Import libraries for password hashing and secure comparison
import hashlib
import hmac
import os

# Convert a password into a secure hash using a salt
def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return a PBKDF2 password hash and its salt for local account storage."""

    # Use the existing salt or generate a new random 16-byte salt
    salt_bytes = bytes.fromhex(salt) if salt else os.urandom(16)

    # Generate a password hash using PBKDF2 and SHA-256
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_bytes, 310_000
    ).hex()

    # Return the password hash and salt as hexadecimal strings
    return password_hash, salt_bytes.hex()

# Account class for storing user account information
@dataclass
class Account:
    username: str
    full_name: str
    password_hash: str
    salt: str
    role: str = "Volunteer"
    created_at: str = ""

    # Create a new account with a hashed password
    @classmethod
    def create(cls, username: str, full_name: str, password: str, role: str = "Volunteer"):

        # Generate the password hash and salt
        password_hash, salt = hash_password(password)

        # Return an Account object with the supplied details
        return cls(
            username=username.strip(),
            full_name=full_name.strip(),
            password_hash=password_hash,
            salt=salt,
            role=role,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    # Check whether the entered password matches the stored password hash
    def verify_password(self, password: str) -> bool:
        candidate_hash, _ = hash_password(password, self.salt)

        # Compare the hashes securely and return the result
        return hmac.compare_digest(candidate_hash, self.password_hash)

    # Convert account information into a dictionary for storage
    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "full_name": self.full_name,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "role": self.role,
            "created_at": self.created_at,
        }

    # Create an Account object from stored dictionary data
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            username=data.get("username", ""),
            full_name=data.get("full_name", ""),
            password_hash=data.get("password_hash", ""),
            salt=data.get("salt", ""),
            role=data.get("role", "Volunteer"),
            created_at=data.get("created_at", ""),
        )

# Session class for managing the currently logged-in account
class Session:
    """Small holder for the account currently signed in."""

    # Store the current account or None when nobody is logged in
    current_account: Account | None = None

    # Set the current account after a successful login
    @classmethod
    def login(cls, account: Account):
        cls.current_account = account

    # Clear the current account when logging out
    @classmethod
    def logout(cls):
        cls.current_account = None