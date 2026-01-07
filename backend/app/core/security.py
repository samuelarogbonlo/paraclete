"""
Security utilities for authentication and encryption.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import secrets
import string

from app.config import settings
from app.core.exceptions import AuthenticationError


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token payload data."""

    sub: str  # Subject (user_id)
    exp: datetime
    iat: datetime
    type: str  # "access" or "refresh"
    session_id: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject of the token (usually user_id)
        expires_delta: Optional custom expiration time
        additional_data: Additional data to include in the token

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    if additional_data:
        to_encode.update(additional_data)

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject of the token (usually user_id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        TokenData object containing the token payload

    Raises:
        AuthenticationError: If the token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Extract token data
        token_data = TokenData(
            sub=payload.get("sub"),
            exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
            iat=datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc),
            type=payload.get("type", "access"),
            session_id=payload.get("session_id"),
        )

        # Verify token hasn't expired (JWT library also checks this)
        if token_data.exp < datetime.now(timezone.utc):
            raise AuthenticationError("Token has expired")

        return token_data

    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


def create_token_pair(
    user_id: str, session_id: Optional[str] = None
) -> TokenResponse:
    """
    Create both access and refresh tokens for a user.

    Args:
        user_id: The user's ID
        session_id: Optional session ID to include in tokens

    Returns:
        TokenResponse with both tokens
    """
    additional_data = {"session_id": session_id} if session_id else None

    access_token = create_access_token(
        subject=user_id, additional_data=additional_data
    )
    refresh_token = create_refresh_token(subject=user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
    )


def generate_api_key(prefix: str = "pk") -> str:
    """
    Generate a secure API key.

    Args:
        prefix: Prefix for the API key (e.g., "pk" for public key)

    Returns:
        A secure random API key
    """
    # Generate 32 random bytes and encode as URL-safe base64
    random_bytes = secrets.token_urlsafe(32)
    return f"{prefix}_{random_bytes}"


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a secure random password.

    Args:
        length: Length of the password

    Returns:
        A secure random password
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def encrypt_api_key(api_key: str, user_id: str) -> tuple[str, str]:
    """
    Encrypt an API key using user-specific salt and OWASP-recommended PBKDF2 iterations.

    Args:
        api_key: The API key to encrypt
        user_id: The user's ID (used with app secret for key derivation)

    Returns:
        Tuple of (encrypted_key, salt_b64) where salt_b64 is Base64-encoded salt
    """
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64

    # Generate unique salt for this user (32 bytes = 256 bits)
    salt = secrets.token_bytes(32)

    # Derive encryption key using PBKDF2 with 600,000 iterations (OWASP 2023 recommendation)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,  # Increased from 100,000 to 600,000
    )
    key_material = f"{user_id}:{settings.SECRET_KEY}".encode()
    key = base64.urlsafe_b64encode(kdf.derive(key_material))

    # Encrypt the API key using Fernet (AES-128-CBC with HMAC)
    f = Fernet(key)
    encrypted = f.encrypt(api_key.encode())

    # Return encrypted key and base64-encoded salt
    salt_b64 = base64.b64encode(salt).decode()
    return encrypted.decode(), salt_b64


def decrypt_api_key(encrypted_key: str, user_id: str, salt_b64: str) -> str:
    """
    Decrypt an API key using user-specific salt.

    Args:
        encrypted_key: The encrypted API key
        user_id: The user's ID (used with app secret for key derivation)
        salt_b64: Base64-encoded salt used during encryption

    Returns:
        Decrypted API key
    """
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64

    # Decode the salt
    salt = base64.b64decode(salt_b64)

    # Derive the same encryption key using the stored salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,  # Must match encryption iterations
    )
    key_material = f"{user_id}:{settings.SECRET_KEY}".encode()
    key = base64.urlsafe_b64encode(kdf.derive(key_material))

    # Decrypt the API key
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_key.encode())
    return decrypted.decode()