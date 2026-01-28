# Multi-Tenant Testing Guide

Guia para atualizar e criar testes no sistema multi-tenant.

## 📋 Visão Geral

Com a implementação multi-tenant, os testes precisam ser atualizados para:
1. Incluir autenticação por tenant (headers)
2. Testar isolamento de dados
3. Suportar ambos os modos (single-tenant e multi-tenant)

---

## 🔧 Atualizando Testes Existentes

### 1. Adicionar Fixtures de Tenant

Adicione ao seu `conftest.py`:

```python
import pytest
import bcrypt
import uuid
from app.models import Tenant, TenantStatus

@pytest.fixture
async def test_tenant(db_session):
    """Create test tenant"""
    api_key = f"test_{uuid.uuid4().hex[:32]}"
    api_key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    tenant = Tenant(
        id=uuid.uuid4(),
        slug="test-tenant",
        name="Test Tenant",
        config={"business_type": "test"},
        api_key_hash=api_key_hash,
        api_key_prefix=api_key[:8],
        status=TenantStatus.ACTIVE
    )

    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    return {"tenant": tenant, "api_key": api_key}
```

### 2. Atualizar Requests HTTP

**Antes:**
```python
response = await client.post(
    "/api/v1/chat",
    json={"message": "Hello", "user_key": "test"}
)
```

**Depois:**
```python
response = await client.post(
    "/api/v1/chat",
    headers={
        "X-Tenant-ID": test_tenant["tenant"].slug,
        "X-API-Key": test_tenant["api_key"]
    },
    json={"message": "Hello", "user_key": "test"}
)
```

### 3. Atualizar Queries de Banco

**Antes:**
```python
result = await db.execute(
    select(User).where(User.user_key == "test")
)
```

**Depois:**
```python
result = await db.execute(
    select(User).where(
        User.tenant_id == tenant_id,
        User.user_key == "test"
    )
)
```

### 4. Atualizar Fixtures de Dados

**Antes:**
```python
@pytest.fixture
async def test_user(db_session):
    user = User(
        id=uuid.uuid4(),
        user_key="test_user",
        name="Test User"
    )
    db_session.add(user)
    await db_session.commit()
    return user
```

**Depois:**
```python
@pytest.fixture
async def test_user(db_session, test_tenant):
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant["tenant"].id,  # ← Adicionar tenant_id
        user_key="test_user",
        name="Test User"
    )
    db_session.add(user)
    await db_session.commit()
    return user
```

---

## ✅ Checklist de Atualização

Para cada arquivo de teste:

- [ ] Importar fixtures de tenant (`test_tenant`)
- [ ] Adicionar `tenant_id` em fixtures que criam dados
- [ ] Adicionar headers `X-Tenant-ID` e `X-API-Key` em requests HTTP
- [ ] Adicionar filtro `tenant_id` em queries de banco
- [ ] Testar com `MULTI_TENANT_ENABLED=True` e `False`

---

## 🧪 Tipos de Testes Multi-Tenant

### 1. Testes de Autenticação

```python
@pytest.mark.asyncio
async def test_valid_authentication(test_tenant):
    """Test successful tenant authentication"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": test_tenant["tenant"].slug,
                "X-API-Key": test_tenant["api_key"]
            },
            json={"message": "Hello", "user_key": "test"}
        )
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_invalid_api_key(test_tenant):
    """Test authentication fails with invalid API key"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": test_tenant["tenant"].slug,
                "X-API-Key": "invalid_key"
            },
            json={"message": "Hello", "user_key": "test"}
        )
        assert response.status_code == 401
```

### 2. Testes de Isolamento de Dados

```python
@pytest.mark.asyncio
async def test_data_isolation(test_tenant_a, test_tenant_b):
    """Test that tenants cannot access each other's data"""
    # Create user in tenant A
    user_a = User(
        tenant_id=test_tenant_a["tenant"].id,
        user_key="shared_key",
        name="User A"
    )
    db.add(user_a)
    await db.commit()

    # Create user with same key in tenant B
    user_b = User(
        tenant_id=test_tenant_b["tenant"].id,
        user_key="shared_key",
        name="User B"
    )
    db.add(user_b)
    await db.commit()

    # Query as tenant A - should only see user A
    result = await db.execute(
        select(User).where(
            User.tenant_id == test_tenant_a["tenant"].id,
            User.user_key == "shared_key"
        )
    )
    user = result.scalar_one()
    assert user.name == "User A"
    assert user.id == user_a.id
```

### 3. Testes de Backward Compatibility

```python
@pytest.mark.asyncio
async def test_single_tenant_mode():
    """Test that single-tenant mode works without headers"""
    # Set MULTI_TENANT_ENABLED=False
    import os
    os.environ["MULTI_TENANT_ENABLED"] = "false"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            # No headers needed in single-tenant mode
            json={"message": "Hello", "user_key": "test"}
        )
        assert response.status_code == 200
```

### 4. Testes de Cross-Tenant Access

```python
@pytest.mark.asyncio
async def test_cross_tenant_access_denied(test_tenant_a, test_tenant_b):
    """Test that tenant B cannot access tenant A's conversations"""
    # Create conversation in tenant A
    async with AsyncClient(app=app, base_url="http://test") as client:
        response_a = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": test_tenant_a["tenant"].slug,
                "X-API-Key": test_tenant_a["api_key"]
            },
            json={"message": "Hello", "user_key": "user_a"}
        )
        conversation_id = response_a.json()["conversation_id"]

        # Try to access as tenant B
        response_b = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": test_tenant_b["tenant"].slug,
                "X-API-Key": test_tenant_b["api_key"]
            },
            json={
                "message": "Trying to access A's conversation",
                "user_key": "user_a",
                "conversation_id": conversation_id
            }
        )

        # Should NOT access tenant A's conversation
        assert response_b.json()["conversation_id"] != conversation_id
```

---

## 🎯 Exemplos Completos

### Teste de Chat com Multi-Tenant

```python
@pytest.mark.asyncio
async def test_chat_with_multi_tenant(test_tenant, test_user):
    """Complete chat test with multi-tenant"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Send message
        response = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": test_tenant["tenant"].slug,
                "X-API-Key": test_tenant["api_key"]
            },
            json={
                "message": "I want to know about your plans",
                "user_key": test_user.user_key,
                "user_name": test_user.name
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert data["conversation_id"] is not None
        assert data["user_id"] == str(test_user.id)

        # Verify conversation was created with correct tenant_id
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == data["conversation_id"],
                Conversation.tenant_id == test_tenant["tenant"].id
            )
        )
        conversation = result.scalar_one()
        assert conversation is not None
        assert conversation.tenant_id == test_tenant["tenant"].id
```

---

## 🛠️ Helpers Úteis

### Helper para Headers

```python
def create_tenant_headers(tenant_slug: str, api_key: str) -> dict:
    """Create authentication headers for tenant"""
    return {
        "X-Tenant-ID": tenant_slug,
        "X-API-Key": api_key
    }

# Uso:
headers = create_tenant_headers(
    test_tenant["tenant"].slug,
    test_tenant["api_key"]
)
```

### Helper para Criar Tenant de Teste

```python
async def create_test_tenant(db, slug: str = None) -> dict:
    """Create a test tenant with random data"""
    if slug is None:
        slug = f"test-{uuid.uuid4().hex[:8]}"

    api_key = f"{slug[:2]}_{uuid.uuid4().hex[:32]}"
    api_key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    tenant = Tenant(
        id=uuid.uuid4(),
        slug=slug,
        name=f"Test Tenant {slug}",
        config={},
        api_key_hash=api_key_hash,
        api_key_prefix=api_key[:8],
        status=TenantStatus.ACTIVE
    )

    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    return {"tenant": tenant, "api_key": api_key}
```

---

## 🔍 Debugging Testes

### Ver Logs de Tenant

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs incluirão [Tenant: <tenant_id>] prefix
```

### Verificar Isolamento de Dados

```python
# Query manual para verificar tenant_id
async def verify_isolation(db, tenant_id):
    """Verify all data has correct tenant_id"""
    models_to_check = [User, Conversation, Message, Lead, Plan]

    for model in models_to_check:
        result = await db.execute(
            select(model).where(model.tenant_id != tenant_id)
        )
        leaked_data = result.scalars().all()

        assert len(leaked_data) == 0, f"Found {len(leaked_data)} leaked records in {model.__name__}"
```

---

## 📊 Cobertura de Testes

Certifique-se de testar:

- [x] Autenticação válida
- [x] Autenticação inválida (API key errada)
- [x] Tenant não encontrado
- [x] Headers faltando
- [x] Isolamento de dados entre tenants
- [x] Cross-tenant access bloqueado
- [x] Backward compatibility (single-tenant mode)
- [x] CRUD operations com tenant_id
- [x] Tools tenant-scoped
- [x] Prompts tenant-specific

---

## 🚀 Rodando Testes

```bash
# Todos os testes
pytest

# Apenas testes multi-tenant
pytest tests/test_multi_tenant.py

# Com coverage
pytest --cov=app --cov-report=html

# Verbose output
pytest -v -s

# Específico
pytest tests/test_multi_tenant.py::test_data_isolation -v
```

---

## ⚠️ Problemas Comuns

### 1. Teste falha com "Tenant not found"

**Causa:** Tenant não foi criado antes do teste.

**Solução:** Adicionar fixture `test_tenant` ou criar tenant no setup.

### 2. Teste falha com "Invalid API key"

**Causa:** API key não está sendo passada ou está incorreta.

**Solução:** Verificar que headers estão sendo enviados e que `api_key` da fixture está sendo usado.

### 3. Dados "vazam" entre tenants

**Causa:** Query não está filtrando por `tenant_id`.

**Solução:** Sempre incluir `Model.tenant_id == tenant_id` em queries.

### 4. Testes passam mas isolamento não funciona

**Causa:** Testes não estão verificando isolamento adequadamente.

**Solução:** Adicionar testes específicos de cross-tenant access e verificar que são bloqueados.

---

## 📝 Template de Teste

```python
@pytest.mark.asyncio
async def test_minha_funcionalidade(test_tenant, db_session):
    """Test description"""
    # Setup - criar dados
    # ...

    # Action - fazer request
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/endpoint",
            headers={
                "X-Tenant-ID": test_tenant["tenant"].slug,
                "X-API-Key": test_tenant["api_key"]
            },
            json={...}
        )

    # Assert - verificar resultado
    assert response.status_code == 200

    # Verify - verificar banco de dados
    result = await db_session.execute(
        select(Model).where(
            Model.tenant_id == test_tenant["tenant"].id,
            # ...
        )
    )
    # ...
```

---

## 📚 Referências

- Arquivo de exemplo: `tests/test_multi_tenant.py`
- Guia multi-tenant: `MULTI_TENANT_GUIDE.md`
- Fixtures: `tests/conftest.py`
