# TravelMind Test Suite

## Overview

This directory contains the test suite for the TravelMind backend API. Tests are written using pytest and cover authentication, authorization, CRUD operations, and security features.

## Running Tests

### Run all tests:
```bash
cd backend
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_auth.py -v
pytest tests/test_trips.py -v
```

### Run with coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

### Run specific test:
```bash
pytest tests/test_auth.py::test_register_success -v
```

## Test Structure

### conftest.py
Contains pytest fixtures and configuration:
- `db_session`: Fresh database session for each test (in-memory SQLite)
- `client`: Async HTTP test client with database override
- `test_user`: Fixture that creates a test user
- `auth_token`: Fixture that provides an authentication token
- `auth_headers`: Fixture that provides authorization headers

### test_auth.py
Tests for authentication endpoints (`/api/auth/*`):
- User registration (success, duplicate username/email, weak password)
- User login (success, wrong password, non-existent user)
- Getting current user info (with/without auth)
- Token refresh

**Total:** 13 tests

### test_trips.py
Tests for trip endpoints (`/api/trips/*`):
- Creating trips (with auth, without auth, demo mode)
- Pagination (skip/limit parameters)
- Getting trips (own trips, other user's trips)
- Authorization checks (ownership verification)
- Updating trips (authorized, unauthorized, no auth)
- Deleting trips (authorized, unauthorized, no auth)
- Trip summary endpoint

**Total:** 16 tests

## Test Database

Tests use an in-memory SQLite database that is:
- Created fresh for each test
- Automatically cleaned up after each test
- Fast (no disk I/O)
- Isolated (no interference between tests)

## Writing New Tests

### Example test structure:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_something(client: AsyncClient, auth_headers: dict):
    """Test description"""
    response = await client.get("/api/endpoint", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

### Available fixtures:
- `client`: Async HTTP client
- `db_session`: Database session
- `test_user`: Pre-created test user
- `auth_token`: Authentication token for test user
- `auth_headers`: Headers with Bearer token
- `test_trip`: Pre-created test trip (in test_trips.py)
- `other_user`: Another test user (in test_trips.py)
- `other_auth_headers`: Headers for other user (in test_trips.py)

## Test Coverage Goals

Current coverage focuses on:
- ✅ Authentication flows
- ✅ Authorization and ownership checks
- ✅ CRUD operations
- ✅ Pagination
- ✅ Security vulnerabilities

Future coverage should include:
- ⏳ Places endpoints
- ⏳ Diary endpoints
- ⏳ Budget/expense endpoints
- ⏳ AI assistant endpoints
- ⏳ File upload edge cases
- ⏳ Rate limiting tests

## CI/CD Integration

### GitHub Actions example:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v --cov
```

## Debugging Tests

### Run tests with print statements:
```bash
pytest tests/ -v -s
```

### Run tests with debugger:
```bash
pytest tests/ --pdb
```

### Show test duration:
```bash
pytest tests/ -v --durations=10
```

## Performance

Typical test run time:
- **Full suite:** ~2-5 seconds
- **Single test file:** ~1-2 seconds
- **Single test:** ~0.1-0.5 seconds

Fast execution is achieved through:
- In-memory database
- Async operations
- Minimal test setup

## Troubleshooting

### Import errors:
Make sure you're running pytest from the `backend` directory:
```bash
cd backend
pytest tests/
```

### Database errors:
Tests create a fresh database each time. If you see database errors:
1. Check that models are imported in `models/database.py`
2. Verify SQLAlchemy relationships are correct
3. Ensure `Base.metadata.create_all()` is called in fixtures

### Async errors:
All test functions must be marked with `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_something():
    ...
```

## Contributing

When adding new features:
1. Write tests first (TDD approach recommended)
2. Ensure tests cover success and error cases
3. Test authorization/ownership checks for protected endpoints
4. Add fixtures to `conftest.py` if needed by multiple tests
5. Run full test suite before committing

---

**Last Updated:** 2025-10-31
**Test Framework:** pytest + pytest-asyncio
**HTTP Client:** httpx
**Database:** SQLite (in-memory)
