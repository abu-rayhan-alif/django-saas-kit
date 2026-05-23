# Service Layer Architecture

**Story:** SAAS-102 | **Layer:** L1 MVP

## Purpose

Business logic lives in `services/`, not in views, serializers, or models.
Views are thin **HTTP adapters** that validate input, call a service, and map
results or errors to HTTP responses.

```
Client → View (DRF) → Service (use-case) → Model / DB
              ↑ no business rules here
```

## Principles

| Rule | Rationale |
|------|-----------|
| **No HTTP in services** | Services must not import `request`, `Response`, or DRF |
| **One use-case per method** | e.g. `UserService.create_user()` |
| **Explicit inputs** | Dataclasses or typed kwargs (`CreateUserInput`) |
| **Domain exceptions** | `ValidationServiceError`, `ConflictServiceError` — views map to status codes |
| **Test without HTTP** | Unit-test services with pytest + DB, no `APIClient` required |

## Folder structure

```
services/
├── __init__.py           # public exports
├── exceptions.py         # ServiceError hierarchy
├── users/
│   ├── user_service.py   # UserService
│   └── ...
├── auth/
│   └── auth_service.py
└── tenants/
    └── tenant_service.py
```

Add a new domain → new subpackage under `services/`, not logic in `apps/*/views.py`.

## Example: create user

### Service (business logic)

```python
# services/users/user_service.py
@dataclass(frozen=True)
class CreateUserInput:
    email: str
    username: str
    password: str

class UserService:
    @staticmethod
    def create_user(data: CreateUserInput) -> User:
        # validate, check conflicts, save — no request object
        ...
```

### View (HTTP only)

```python
# apps/users/views.py
class UserCreateView(APIView):
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = UserService.create_user(CreateUserInput(**serializer.validated_data))
        except ValidationServiceError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(UserSerializer(user).data, status=201)
```

### Unit test (no HTTP)

```python
# tests/unit/services/test_user_service.py
@pytest.mark.django_db
def test_create_user():
    user = UserService.create_user(
        CreateUserInput(email="a@b.com", username="alice", password="SecurePass123!")
    )
    assert user.email == "a@b.com"
```

## Exception → HTTP mapping (views)

| Service exception | HTTP status |
|-------------------|-------------|
| `ValidationServiceError` | 400 Bad Request |
| `ConflictServiceError` | 409 Conflict |
| `ServiceError` (other) | 500 / 400 (case by case) |

Keep mapping in views only; services stay transport-agnostic.

## What belongs where

| Layer | Responsibility |
|-------|----------------|
| **Model** | Schema, constraints, simple properties (`BaseModel` in `apps/common/models.py`) |
| **Service** | Workflows, validation, orchestration, side effects |
| **Serializer** | Input/output shape for API |
| **View** | Auth, HTTP status, call service |

## Related

- [Event-driven flow](event-driven.md) — Event → Celery → Notification → Email/WebSocket
- [ADR index](../adr/README.md)
- API docs: `/api/docs/` (user create: `POST /api/users/`)
