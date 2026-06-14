# Testing

## Backend Tests

```bash
cd packages/backend
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html  # with coverage
```

Tests are in `packages/backend/tests/`. The CI enforces ≥80% coverage.

## CLI Tests

```bash
cd packages/cli
npm test
```

## SDK Tests

```bash
cd packages/sdk
npm test
```

## End-to-End

For full integration testing, start the stack with Docker:

```bash
docker compose up -d
cd packages/backend && pytest tests/integration/ -v
```

## Writing Tests

### Python
Follow the existing pattern in `packages/backend/tests/`. Use `pytest` fixtures:

```python
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
```

### TypeScript
Use Vitest or Jest:

```typescript
import { describe, it, expect } from "vitest";
import { myFunction } from "../src/myModule.js";

describe("myFunction", () => {
  it("returns expected value", () => {
    expect(myFunction("input")).toBe("expected");
  });
});
```
