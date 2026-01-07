"""
Unit tests for security utilities (JWT, password hashing, encryption).
"""
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt as jose_jwt

from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    create_token_pair,
    generate_api_key,
    generate_secure_password,
    encrypt_api_key,
    decrypt_api_key,
    TokenData,
    TokenResponse,
)
from app.core.exceptions import AuthenticationError
from app.config import settings


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_creates_different_hashes(self):
        """Test that hashing the same password twice creates different hashes."""
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert hash1 != password
        assert hash2 != password

    def test_verify_password_with_correct_password(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_with_incorrect_password(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword456"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_password_with_empty_string(self):
        """Test hashing an empty password."""
        hashed = hash_password("")
        assert hashed is not None
        assert verify_password("", hashed) is True

    def test_hash_password_with_special_characters(self):
        """Test hashing password with special characters."""
        password = "p@ssw0rd!#$%^&*()"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_hash_password_with_unicode(self):
        """Test hashing password with unicode characters."""
        password = "пароль密码🔒"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_access_token(self, mock_settings):
        """Test access token creation."""
        user_id = "user_123"
        token = create_access_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self, mock_settings):
        """Test access token with custom expiration time."""
        user_id = "user_123"
        expires_delta = timedelta(minutes=15)
        token = create_access_token(user_id, expires_delta=expires_delta)

        # Decode without verification to check expiry
        payload = jose_jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        current_time = datetime.now(timezone.utc)

        time_diff = (exp_time - current_time).total_seconds()
        assert 14 * 60 < time_diff < 16 * 60  # ~15 minutes

    def test_create_access_token_with_additional_data(self, mock_settings):
        """Test access token with additional data."""
        user_id = "user_123"
        additional_data = {"session_id": "session_456", "role": "admin"}
        token = create_access_token(user_id, additional_data=additional_data)

        payload = jose_jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert payload["sub"] == user_id
        assert payload["session_id"] == "session_456"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_create_refresh_token(self, mock_settings):
        """Test refresh token creation."""
        user_id = "user_123"
        token = create_refresh_token(user_id)

        assert token is not None
        assert isinstance(token, str)

        payload = jose_jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["type"] == "refresh"
        assert payload["sub"] == user_id

    def test_create_refresh_token_with_custom_expiry(self, mock_settings):
        """Test refresh token with custom expiration."""
        user_id = "user_123"
        expires_delta = timedelta(days=30)
        token = create_refresh_token(user_id, expires_delta=expires_delta)

        payload = jose_jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        current_time = datetime.now(timezone.utc)

        time_diff = (exp_time - current_time).total_seconds()
        assert 29 * 24 * 3600 < time_diff < 31 * 24 * 3600  # ~30 days

    def test_decode_valid_token(self, mock_settings):
        """Test decoding a valid token."""
        user_id = "user_123"
        token = create_access_token(user_id)

        token_data = decode_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.sub == user_id
        assert token_data.type == "access"
        assert isinstance(token_data.exp, datetime)
        assert isinstance(token_data.iat, datetime)

    def test_decode_invalid_token(self, mock_settings):
        """Test decoding an invalid token."""
        invalid_token = "invalid.token.here"

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(invalid_token)

        assert "Invalid token" in str(exc_info.value)

    def test_decode_expired_token(self, mock_settings):
        """Test decoding an expired token."""
        user_id = "user_123"
        # Create token that expires immediately
        token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(token)

        assert "expired" in str(exc_info.value).lower()

    def test_decode_token_with_wrong_secret(self, mock_settings):
        """Test decoding token with wrong secret key."""
        user_id = "user_123"
        # Create token with different secret
        wrong_token = jose_jwt.encode(
            {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key",
            algorithm="HS256",
        )

        with pytest.raises(AuthenticationError):
            decode_token(wrong_token)

    def test_create_token_pair(self, mock_settings):
        """Test creating both access and refresh tokens."""
        user_id = "user_123"
        tokens = create_token_pair(user_id)

        assert isinstance(tokens, TokenResponse)
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        assert tokens.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_create_token_pair_with_session_id(self, mock_settings):
        """Test creating token pair with session ID."""
        user_id = "user_123"
        session_id = "session_456"
        tokens = create_token_pair(user_id, session_id=session_id)

        # Verify access token contains session ID
        payload = jose_jwt.decode(
            tokens.access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["session_id"] == session_id

    def test_token_contains_required_fields(self, mock_settings):
        """Test that tokens contain all required fields."""
        user_id = "user_123"
        token = create_access_token(user_id)

        payload = jose_jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload


@pytest.mark.unit
class TestApiKeyGeneration:
    """Test API key generation utilities."""

    def test_generate_api_key_default_prefix(self):
        """Test generating API key with default prefix."""
        key = generate_api_key()

        assert key.startswith("pk_")
        assert len(key) > 10

    def test_generate_api_key_custom_prefix(self):
        """Test generating API key with custom prefix."""
        key = generate_api_key(prefix="sk")

        assert key.startswith("sk_")
        assert len(key) > 10

    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        keys = [generate_api_key() for _ in range(100)]

        assert len(keys) == len(set(keys))  # All unique

    def test_generate_api_key_format(self):
        """Test API key format."""
        key = generate_api_key()

        # Should be prefix + underscore + base64 string
        assert "_" in key
        prefix, rest = key.split("_", 1)
        assert len(rest) > 30  # URL-safe base64 encoded 32 bytes

    def test_generate_secure_password_default_length(self):
        """Test generating secure password with default length."""
        password = generate_secure_password()

        assert len(password) == 16
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)

    def test_generate_secure_password_custom_length(self):
        """Test generating secure password with custom length."""
        password = generate_secure_password(length=24)

        assert len(password) == 24

    def test_generate_secure_password_uniqueness(self):
        """Test that generated passwords are unique."""
        passwords = [generate_secure_password() for _ in range(100)]

        assert len(passwords) == len(set(passwords))  # All unique


@pytest.mark.unit
class TestEncryption:
    """Test API key encryption/decryption."""

    def test_encrypt_decrypt_api_key(self):
        """Test encrypting and decrypting an API key."""
        api_key = "sk-test-api-key-123456"
        user_key = "user-master-key-123"

        encrypted, salt = encrypt_api_key(api_key, user_key)
        assert encrypted != api_key
        assert len(encrypted) > len(api_key)
        assert salt is not None

        decrypted = decrypt_api_key(encrypted, user_key, salt)
        assert decrypted == api_key

    def test_encrypt_with_different_keys(self):
        """Test that different user keys produce different encrypted values."""
        api_key = "sk-test-api-key-123456"
        user_key1 = "user-master-key-1"
        user_key2 = "user-master-key-2"

        encrypted1, _ = encrypt_api_key(api_key, user_key1)
        encrypted2, _ = encrypt_api_key(api_key, user_key2)

        assert encrypted1 != encrypted2

    def test_decrypt_with_wrong_key_fails(self):
        """Test that decrypting with wrong key fails."""
        api_key = "sk-test-api-key-123456"
        user_key = "user-master-key-123"
        wrong_key = "wrong-master-key-456"

        encrypted, salt = encrypt_api_key(api_key, user_key)

        with pytest.raises(Exception):  # Fernet raises InvalidToken
            decrypt_api_key(encrypted, wrong_key, salt)

    def test_encrypt_empty_string(self):
        """Test encrypting an empty string."""
        api_key = ""
        user_key = "user-master-key-123"

        encrypted, salt = encrypt_api_key(api_key, user_key)
        decrypted = decrypt_api_key(encrypted, user_key, salt)

        assert decrypted == api_key

    def test_encrypt_long_string(self):
        """Test encrypting a long string."""
        api_key = "sk-" + "x" * 1000
        user_key = "user-master-key-123"

        encrypted, salt = encrypt_api_key(api_key, user_key)
        decrypted = decrypt_api_key(encrypted, user_key, salt)

        assert decrypted == api_key

    def test_encrypt_special_characters(self):
        """Test encrypting string with special characters."""
        api_key = "sk-!@#$%^&*()_+-={}[]|:;<>?,./"
        user_key = "user-master-key-123"

        encrypted, salt = encrypt_api_key(api_key, user_key)
        decrypted = decrypt_api_key(encrypted, user_key, salt)

        assert decrypted == api_key


@pytest.mark.unit
class TestTokenDataModel:
    """Test TokenData Pydantic model."""

    def test_token_data_creation(self):
        """Test creating TokenData instance."""
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)

        token_data = TokenData(
            sub="user_123",
            exp=exp,
            iat=now,
            type="access",
            session_id="session_456",
        )

        assert token_data.sub == "user_123"
        assert token_data.exp == exp
        assert token_data.iat == now
        assert token_data.type == "access"
        assert token_data.session_id == "session_456"

    def test_token_data_without_session_id(self):
        """Test TokenData without optional session_id."""
        now = datetime.now(timezone.utc)

        token_data = TokenData(
            sub="user_123",
            exp=now + timedelta(hours=1),
            iat=now,
            type="refresh",
        )

        assert token_data.session_id is None


@pytest.mark.unit
class TestTokenResponseModel:
    """Test TokenResponse Pydantic model."""

    def test_token_response_creation(self):
        """Test creating TokenResponse instance."""
        response = TokenResponse(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            token_type="bearer",
            expires_in=3600,
        )

        assert response.access_token == "access_token_123"
        assert response.refresh_token == "refresh_token_456"
        assert response.token_type == "bearer"
        assert response.expires_in == 3600

    def test_token_response_default_type(self):
        """Test TokenResponse with default token_type."""
        response = TokenResponse(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
        )

        assert response.token_type == "bearer"
