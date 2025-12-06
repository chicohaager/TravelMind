# Contributing to TravelMind

Thank you for your interest in contributing to TravelMind! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Please be considerate in your communications and contributions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/TravelMind.git
   cd TravelMind
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/TravelMind.git
   ```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm 9+
- Docker & Docker Compose (optional, for containerized development)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Start development server
python main.py
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Using Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Project Structure

```
TravelMind/
├── backend/                 # FastAPI backend
│   ├── main.py             # Application entry point
│   ├── routes/             # API route handlers
│   ├── models/             # SQLAlchemy models
│   ├── services/           # Business logic
│   ├── utils/              # Utility functions
│   ├── middleware/         # Custom middleware
│   └── tests/              # Backend tests
├── frontend/               # React frontend
│   ├── src/
│   │   ├── pages/         # Page components
│   │   ├── components/    # Reusable components
│   │   ├── services/      # API client
│   │   └── contexts/      # React contexts
│   ├── e2e/               # Playwright E2E tests
│   └── public/            # Static assets
└── docker-compose.yml     # Docker configuration
```

## Making Changes

### Creating a Branch

Create a descriptive branch name:

```bash
git checkout -b feature/add-trip-export
git checkout -b fix/login-validation
git checkout -b docs/update-api-docs
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/changes

### Development Workflow

1. **Keep your fork updated**:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Make your changes** following the coding standards

3. **Write/update tests** for your changes

4. **Run tests locally** before pushing

5. **Commit your changes** following commit guidelines

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests/test_trips.py

# Run in verbose mode
pytest -v
```

### Frontend Tests

```bash
cd frontend

# Unit tests
npm run test

# With coverage
npm run test:coverage

# E2E tests with Playwright
npm run test:e2e

# E2E in headed mode (see browser)
npm run test:e2e:headed

# E2E with UI
npm run test:e2e:ui
```

### Required Test Coverage

- New features should include unit tests
- Bug fixes should include regression tests
- Critical paths should have E2E tests

## Pull Request Process

1. **Update your branch** with the latest main:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-feature
   ```

3. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Description of what was changed and why
   - Link to related issue(s) if applicable
   - Screenshots for UI changes

4. **Address review feedback** promptly

5. **Squash commits** if requested by maintainers

### PR Checklist

- [ ] Code follows project coding standards
- [ ] Tests pass locally
- [ ] New code has appropriate test coverage
- [ ] Documentation updated if needed
- [ ] No unrelated changes included
- [ ] Commit messages follow guidelines

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints for function parameters and returns
- Write docstrings for public functions/classes
- Use `async/await` for database operations
- Keep functions focused and small

```python
async def get_trip_by_id(
    trip_id: int,
    db: AsyncSession
) -> Optional[Trip]:
    """
    Retrieve a trip by its ID.

    Args:
        trip_id: The unique identifier of the trip
        db: Database session

    Returns:
        The trip object if found, None otherwise
    """
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    return result.scalar_one_or_none()
```

### JavaScript/React (Frontend)

- Use functional components with hooks
- Use descriptive variable and function names
- Keep components focused and reusable
- Use proper error handling
- Follow React best practices

```jsx
function TripCard({ trip, onEdit, onDelete }) {
  const handleDelete = async () => {
    if (window.confirm('Are you sure?')) {
      await onDelete(trip.id);
    }
  };

  return (
    <div className="trip-card">
      <h3>{trip.title}</h3>
      <p>{trip.destination}</p>
      <button onClick={() => onEdit(trip)}>Edit</button>
      <button onClick={handleDelete}>Delete</button>
    </div>
  );
}
```

### General Guidelines

- Write self-documenting code
- Keep dependencies minimal
- Avoid premature optimization
- Handle errors gracefully
- Log important operations
- Never commit secrets or credentials

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(trips): add export to PDF feature

Implement PDF export functionality for trips including:
- Trip details and itinerary
- Places visited
- Budget summary

Closes #123
```

```
fix(auth): correct password validation regex

The previous regex didn't allow special characters.
Updated to accept all common special characters.

Fixes #456
```

### Guidelines

- Use imperative mood ("add" not "added")
- Keep subject line under 72 characters
- Separate subject from body with blank line
- Reference issues in footer

## Questions?

If you have questions about contributing, please:

1. Check existing issues and discussions
2. Open a new issue with the "question" label
3. Join our community discussions

Thank you for contributing to TravelMind!
