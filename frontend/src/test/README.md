# Frontend Testing Guide

This directory contains the test setup and utilities for the TravelMind frontend.

## Running Tests

```bash
# Run tests in watch mode (development)
npm test

# Run tests once (CI/CD)
npm run test:run

# Run tests with coverage report
npm run test:coverage

# Run tests with UI (interactive mode)
npm run test:ui
```

## Test Structure

```
src/
├── test/
│   ├── setup.js      # Global test setup (runs before each test)
│   ├── utils.jsx     # Test utilities and custom render
│   └── README.md     # This file
├── components/
│   └── *.test.jsx    # Component tests (co-located)
├── services/
│   └── *.test.js     # Service tests (co-located)
└── pages/
    └── *.test.jsx    # Page tests (co-located)
```

## Writing Tests

### Basic Component Test

```jsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/utils'
import MyComponent from './MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Hello" />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

### Testing with User Events

```jsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import Button from './Button'

describe('Button', () => {
  it('calls onClick when clicked', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()

    render(<Button onClick={handleClick}>Click me</Button>)

    await user.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledOnce()
  })
})
```

### Testing Async Operations

```jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@/test/utils'
import DataComponent from './DataComponent'

// Mock the API
vi.mock('@/services/api', () => ({
  tripsService: {
    getAll: vi.fn().mockResolvedValue({
      data: [{ id: 1, title: 'Trip 1' }]
    })
  }
}))

describe('DataComponent', () => {
  it('loads and displays data', async () => {
    render(<DataComponent />)

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Trip 1')).toBeInTheDocument()
    })
  })
})
```

## Test Utilities

### Custom Render

The custom `render` function from `@/test/utils` wraps components with all necessary providers:

- React Query (QueryClientProvider)
- React Router (BrowserRouter)
- Auth Context (AuthProvider)

```jsx
import { render } from '@/test/utils'

render(<MyComponent />) // Automatically wrapped with all providers
```

### Mock Factories

```jsx
import { createMockUser, createMockTrip, createMockDiaryEntry } from '@/test/utils'

const user = createMockUser({ username: 'custom' })
const trip = createMockTrip({ destination: 'Paris' })
const entry = createMockDiaryEntry({ mood: 'excited' })
```

## Mocking

### Mocking Modules

```jsx
import { vi } from 'vitest'

vi.mock('@/services/api', () => ({
  tripsService: {
    getAll: vi.fn()
  }
}))
```

### Mocking Hooks

```jsx
import { vi } from 'vitest'

vi.mock('@/hooks/useTrips', () => ({
  useTrips: () => ({
    trips: [{ id: 1, title: 'Test' }],
    isLoading: false,
    error: null
  })
}))
```

## Coverage

Coverage reports are generated in the `coverage/` directory:

- `coverage/index.html` - Interactive HTML report
- `coverage/lcov.info` - LCOV format for CI tools

## Best Practices

1. **Co-locate tests** with the code they test
2. **Use meaningful descriptions** in `describe` and `it` blocks
3. **Test behavior, not implementation**
4. **Use data-testid sparingly** - prefer accessible queries
5. **Mock external dependencies** (API, localStorage, etc.)
6. **Clean up after tests** (handled automatically by setup.js)

## Query Priority

Use queries in this order of priority:

1. `getByRole` - Most accessible
2. `getByLabelText` - For form elements
3. `getByPlaceholderText` - For inputs
4. `getByText` - For visible text
5. `getByTestId` - Last resort

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Library Cheatsheet](https://testing-library.com/docs/react-testing-library/cheatsheet/)
