"""
Pytest configuration and fixtures for Paraclete backend tests.
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.database import Base, get_session
from app.db.models import User, Session as DBSession, SessionStatus
from app.core.security import hash_password, create_token_pair
from app.config import settings


# Test database URL (using port 5433 as per docker-compose.yml)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/paraclete_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session_maker(test_engine):
    """Create a test session maker."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture(scope="function")
async def db_session(test_session_maker) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with database session override."""

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True  # Follow 307 redirects for trailing slash
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user."""
    tokens = create_token_pair(str(test_user.id))
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_user: User) -> dict:
    """Create authentication headers for admin user."""
    tokens = create_token_pair(str(admin_user.id))
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def test_session(db_session: AsyncSession, test_user: User) -> DBSession:
    """Create a test coding session."""
    session = DBSession(
        user_id=test_user.id,
        status=SessionStatus.ACTIVE,
        repo_url="https://github.com/test/repo",
        branch_name="main",
        project_name="test-repo",
        description="Test session",
        agent_statuses={},
        files_changed=[],
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture(autouse=True)
def mock_api_keys(monkeypatch):
    """Provide mock API keys for all tests."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-anthropic-1234567890")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-openai-1234567890")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-google-1234567890")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key-deepgram-1234567890")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key-elevenlabs-1234567890")


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock application settings for testing."""
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key-min-32-chars-long")
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    monkeypatch.setattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)
    return settings


# Sample test data
@pytest.fixture
def sample_session_data():
    """Sample data for creating sessions."""
    return {
        "repo_url": "https://github.com/test/repo",
        "branch_name": "feature/test",
        "project_name": "Test Project",
        "description": "Test session description",
    }


@pytest.fixture
def sample_user_data():
    """Sample data for creating users."""
    return {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "full_name": "New User",
    }


@pytest.fixture
def sample_message_data():
    """Sample data for creating messages."""
    return {
        "role": "user",
        "content": "Test message content",
        "voice_transcript": "Test voice transcript",
    }


# Markers for different test types
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as requiring authentication"
    )
