from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import os

def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return a PBKDF2 password hash and its salt for local account storage."""
    salt_bytes = bytes.fromhex(salt) if salt else os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        310_000
    ).hex()
    return password_hash, salt_bytes.hex()

@dataclass
class Account:
    username: str
    full_name: str
    password_hash: str
    salt: str
    role: str = "Volunteer"
    created_at: str = ""

    # Profile information
    email: str = ""
    phone: str = ""
    date_of_birth: str = ""
    gender: str = ""
    address: str = ""
    emergency_contact_name: str = ""
    emergency_contact_phone: str = ""
    profile_picture: str = ""
    valid_id_path: str = ""
    points: int = 0

    @classmethod
    def create(
        cls,
        username: str,
        full_name: str,
        password: str,
        role: str = "Volunteer",
        email: str = ""
    ):
        password_hash, salt = hash_password(password)

        return cls(
            username=username.strip(),
            full_name=full_name.strip(),
            password_hash=password_hash,
            salt=salt,
            role=role,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            email=email.strip(),
        )

    def verify_password(self, password: str) -> bool:
        candidate_hash, _ = hash_password(password, self.salt)
        return hmac.compare_digest(
            candidate_hash,
            self.password_hash
        )

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "full_name": self.full_name,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "role": self.role,
            "created_at": self.created_at,
            "email": self.email,
            "phone": self.phone,
            "date_of_birth": self.date_of_birth,
            "gender": self.gender,
            "address": self.address,
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "profile_picture": self.profile_picture,
            "valid_id_path": self.valid_id_path,
            "points": self.points,  
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            username=data.get("username", ""),
            full_name=data.get("full_name", ""),
            password_hash=data.get("password_hash", ""),
            salt=data.get("salt", ""),
            role=data.get("role", "Volunteer"),
            created_at=data.get("created_at", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            date_of_birth=data.get("date_of_birth", ""),
            gender=data.get("gender", ""),
            address=data.get("address", ""),
            emergency_contact_name=data.get(
                "emergency_contact_name", ""
            ),
            emergency_contact_phone=data.get(
                "emergency_contact_phone", ""
            ),
            profile_picture=data.get("profile_picture", ""),
            valid_id_path=data.get("valid_id_path", ""),
            points=data.get("points", 0)
        )

class Session:
    """Stores the account currently signed in."""

    current_account: Account | None = None

    @classmethod
    def login(cls, account: Account):
        cls.current_account = account

    @classmethod
    def logout(cls):
        cls.current_account = None