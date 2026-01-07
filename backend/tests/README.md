# Paraclete Backend Tests

Comprehensive test suite for the Paraclete FastAPI backend.

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html --cov-report=term
```

### Run specific test type
```bash
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest -m "not slow"              # Exclude slow tests
```

### Run specific test file
```bash
pytest tests/unit/test_security.py
pytest tests/integration/test_sessions_api.py
```

### Run with verbose output
```bash
pytest -v -s
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (no database/network)
│   ├── test_security.py     # Security utilities tests
│   └── test_session_service.py  # Session service logic tests
└── integration/             # Integration tests (with database)
    ├── test_sessions_api.py     # Session API endpoints
    └── test_websocket.py        # WebSocket connection tests
```

## Prerequisites

### Database Setup
Create test database:
```bash
createdb paraclete_test
```

Or using Docker:
```bash
docker run -d \
  --name paraclete-test-db \
  -e POSTGRES_DB=paraclete_test \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15
```

### Environment Variables
```bash
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/paraclete_test"
export SECRET_KEY="test-secret-key-min-32-chars-long"
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **Security**: Password hashing, JWT tokens, encryption
- **Services**: Business logic without external dependencies
- **Models**: Pydantic model validation

**Coverage Goal**: >90%

### Integration Tests (`@pytest.mark.integration`)
- **API Endpoints**: Full request/response cycle
- **Database**: Real database operations
- **Authentication**: End-to-end auth flow

**Coverage Goal**: >80%

## Key Test Files

### Unit Tests
- `test_security.py` - 150+ tests for auth, encryption, JWT
- `test_session_service.py` - 80+ tests for session management logic

### Integration Tests
- `test_sessions_api.py` - 50+ tests for all session endpoints
- `test_websocket.py` - WebSocket connection and messaging (planned)

## Test Fixtures

### Database Fixtures
```python
@pytest_asyncio.fixture
async def db_session(test_engine):
    """Provides clean database session for each test."""
    async with test_session_maker() as session:
        yield session
        await session.rollback()  # Cleanup
```

### User Fixtures
```python
@pytest_asyncio.fixture
async def test_user(db_session):
    """Creates a test user."""
    # Returns User instance
```

### Authentication Fixtures
```python
@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Provides auth headers for API requests."""
    # Returns {"Authorization": "Bearer <token>"}
```

## Writing New Tests

### Unit Test Example
```python
@pytest.mark.unit
class TestMyFeature:
    def test_something(self):
        # Arrange
        input_data = "test"

        # Act
        result = my_function(input_data)

        # Assert
        assert result == expected_value
```

### Integration Test Example
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_endpoint(test_client, auth_headers):
    # Arrange
    payload = {"key": "value"}

    # Act
    response = await test_client.post(
        "/v1/endpoint",
        json=payload,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["key"] == "value"
```

## Coverage Reports

### Generate HTML coverage report
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Check coverage threshold
```bash
pytest --cov=app --cov-fail-under=80
```

## Test Markers

- `@pytest.mark.unit` - Unit test (fast, no I/O)
- `@pytest.mark.integration` - Integration test (database, API)
- `@pytest.mark.slow` - Slow running test
- `@pytest.mark.auth` - Requires authentication

## Continuous Integration

### GitHub Actions
```yaml
- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Database connection errors
- Ensure PostgreSQL is running
- Check DATABASE_URL environment variable
- Verify test database exists

### Async warnings
- Use `@pytest.mark.asyncio` for async tests
- Ensure pytest-asyncio is installed

### Fixture not found
- Check conftest.py is in correct location
- Verify fixture scope (session/module/function)

### Tests hanging
- Check for infinite loops in async code
- Verify database connections are properly closed
- Use pytest timeout: `pytest --timeout=60`

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Use fixtures to ensure cleanup
3. **Clear names**: Use descriptive test names
4. **AAA pattern**: Arrange, Act, Assert
5. **Fast tests**: Mock external services
6. **Data factories**: Use fixtures for test data
7. **Edge cases**: Test boundary conditions
8. **Error cases**: Test failure scenarios
