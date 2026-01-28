# Multi-Tenant Architecture Guide

Guia completo para o sistema multi-tenant do WorkHub Sales Funnel.

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Instalação e Configuração](#instalação-e-configuração)
4. [Criando um Novo Tenant](#criando-um-novo-tenant)
5. [API Reference](#api-reference)
6. [Desenvolvimento](#desenvolvimento)
7. [Troubleshooting](#troubleshooting)

---

## Visão Geral

O sistema foi transformado de uma aplicação single-tenant (específica para coworking) em uma **plataforma multi-tenant** que permite múltiplos clientes com:

- ✅ **Isolamento completo de dados** por tenant
- ✅ **Prompts e knowledge base customizáveis**
- ✅ **Produtos/planos específicos** por tenant
- ✅ **Configurações independentes** (LLM, funnel stages, etc.)
- ✅ **Autenticação via API key** por tenant
- ✅ **Backward compatibility** com modo single-tenant

---

## Arquitetura

### Modelo de Dados

#### Novas Tabelas

**`tenants`** - Cliente/Tenant
- `id` (UUID) - Primary key
- `slug` (String) - Identificador único (ex: "workhub", "techspace")
- `name` (String) - Nome de exibição
- `config` (JSONB) - Configuração customizada
- `api_key_hash` (String) - Hash bcrypt da API key
- `status` (Enum) - active, trial, suspended, cancelled
- `created_at`, `updated_at` (DateTime)

**`prompt_templates`** - Prompts por tenant
- `id` (UUID) - Primary key
- `tenant_id` (UUID) - Foreign key
- `prompt_type` (Enum) - sales_agent, admin_agent, analyst_agent
- `version` (Integer) - Versionamento
- `system_prompt` (Text) - Conteúdo do prompt
- `knowledge_base` (Text) - Base de conhecimento (opcional)
- `is_active` (Boolean) - Versão ativa

**`knowledge_documents`** - Knowledge base por tenant
- `id` (UUID) - Primary key
- `tenant_id` (UUID) - Foreign key
- `title`, `slug` (String)
- `content` (Text) - Conteúdo markdown
- `document_type` (Enum) - product, faq, objections, scripts

#### Tabelas Existentes Modificadas

Todas as tabelas existentes agora incluem:
- `tenant_id` (UUID) - Foreign key para `tenants`
- Constraints `UNIQUE(tenant_id, <field>)` para isolamento
- Índices compostos `(tenant_id, ...)` para performance

### Fluxo de Autenticação

```
1. Request → TenantMiddleware
2. Extrai X-Tenant-ID e X-API-Key dos headers
3. Valida tenant existe e está ativo
4. Verifica API key (bcrypt hash)
5. Injeta tenant no request.state
6. → Endpoint (com tenant context)
```

### Fluxo de Chat

```
1. POST /api/v1/chat (com headers X-Tenant-ID e X-API-Key)
2. TenantMiddleware valida e injeta tenant
3. TenantChatService (tenant-scoped)
4. TenantPromptService carrega prompt do DB (com cache)
5. SalesAgent com TenantToolRegistry (tools tenant-scoped)
6. Todas queries filtradas por tenant_id
7. Response isolado por tenant
```

---

## Instalação e Configuração

### 1. Configurar Variáveis de Ambiente

Adicione ao `.env`:

```bash
# Multi-Tenant Settings
MULTI_TENANT_ENABLED=false  # false = single-tenant (backward compatible)
TENANT_ID_HEADER=X-Tenant-ID
DEFAULT_TENANT_SLUG=workhub
```

### 2. Rodar Migrations

```bash
# Upgrade database para incluir multi-tenant
alembic upgrade head
```

**⚠️ IMPORTANTE:** A migration criará o tenant default "workhub" e exibirá a API key no console. **Salve essa API key!**

### 3. Ativar Multi-Tenant Mode (Opcional)

Para ativar o modo multi-tenant:

```bash
# No .env
MULTI_TENANT_ENABLED=true
```

Com `MULTI_TENANT_ENABLED=false`, o sistema:
- Usa o tenant default "workhub"
- Não requer headers X-Tenant-ID e X-API-Key
- Mantém backward compatibility total

---

## Criando um Novo Tenant

### Opção 1: Script de Onboarding (Recomendado)

```bash
# Com arquivo de configuração completo
python scripts/onboard_tenant.py --config examples/tenant_config_example.json

# Onboarding simples (apenas tenant)
python scripts/onboard_tenant.py --slug mycompany --name "My Company"
```

**Saída:**
```
================================================================================
✅ TENANT ONBOARDING COMPLETED SUCCESSFULLY
================================================================================

Tenant ID:     a1b2c3d4-...
Tenant Slug:   mycompany
Tenant Name:   My Company
Status:        active

🔑 API KEY:    my_abc123xyz...
   (Prefix:    my_abc12...)

⚠️  SAVE THIS API KEY! It will not be shown again.
```

### Opção 2: Via API

```bash
curl -X POST http://localhost:8000/api/v1/admin/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "mycompany",
    "name": "My Company",
    "config": {
      "business_type": "saas",
      "currency": "USD"
    }
  }'
```

**Response:**
```json
{
  "id": "a1b2c3d4-...",
  "slug": "mycompany",
  "name": "My Company",
  "api_key": "my_abc123xyz...",  // ⚠️ Mostrado apenas uma vez!
  "status": "active",
  ...
}
```

---

## API Reference

### Headers Obrigatórios (Multi-Tenant Mode)

```
X-Tenant-ID: <tenant-slug>
X-API-Key: <tenant-api-key>
```

### Endpoints de Chat

**POST `/api/v1/chat`** - Enviar mensagem

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: mycompany" \
  -H "X-API-Key: my_abc123xyz..." \
  -d '{
    "message": "Hello!",
    "user_key": "user123",
    "user_name": "John Doe"
  }'
```

### Endpoints de Gerenciamento de Tenant

**Platform Admin Endpoints:**

- `POST /api/v1/admin/tenants` - Criar tenant
- `GET /api/v1/admin/tenants` - Listar todos tenants
- `GET /api/v1/admin/tenants/{slug}` - Ver tenant específico
- `PUT /api/v1/admin/tenants/{slug}` - Atualizar tenant
- `DELETE /api/v1/admin/tenants/{slug}` - Desativar tenant (soft delete)

**Tenant Admin Endpoints:**

- `PUT /api/v1/tenants/prompts/{type}` - Atualizar prompt
- `GET /api/v1/tenants/prompts` - Listar prompts
- `POST /api/v1/tenants/knowledge` - Criar documento de conhecimento
- `GET /api/v1/tenants/knowledge` - Listar documentos
- `PUT /api/v1/tenants/knowledge/{slug}` - Atualizar documento
- `POST /api/v1/tenants/plans` - Criar plano/produto
- `GET /api/v1/tenants/plans` - Listar planos

### Configuração do Tenant (JSONB)

```json
{
  "business_type": "coworking|saas|retail|...",
  "currency": "BRL|USD|EUR",
  "features": {
    "enable_handoff": true,
    "enable_analytics": true,
    "max_users": 1000
  },
  "funnel_config": {
    "stages": [
      {"key": "awareness", "name": "Conscientização"},
      {"key": "interest", "name": "Interesse"},
      ...
    ]
  },
  "llm": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.7
  }
}
```

---

## Desenvolvimento

### Adicionando um Novo Tool Tenant-Aware

```python
# Em app/tools/tenant_tools.py

async def _meu_novo_tool_tenant(
    self,
    param1: str,
    db: AsyncSession,
    tenant_id: UUID
) -> dict:
    """Meu novo tool (tenant-scoped)"""
    try:
        # SEMPRE filtrar por tenant_id
        result = await db.execute(
            select(MinhaTabela).where(
                MinhaTabela.tenant_id == tenant_id,
                MinhaTabela.campo == param1
            )
        )
        # ...
        return {"success": True, ...}
    except Exception as e:
        logger.error(f"[Tenant: {tenant_id}] Error: {e}")
        return {"success": False, "error": str(e)}

# Registrar no get_all_tools():
tools.append(self._create_tenant_tool(
    self._meu_novo_tool_tenant,
    "meu_novo_tool",
    "Descrição do tool",
    MeuToolInput  # Pydantic schema
))
```

### Atualizando Prompts de um Tenant

```python
# Via API
import requests

response = requests.put(
    "http://localhost:8000/api/v1/tenants/prompts/sales_agent",
    headers={
        "X-Tenant-ID": "mycompany",
        "X-API-Key": "my_abc123xyz..."
    },
    json={
        "prompt_type": "sales_agent",
        "system_prompt": "Você é um consultor de vendas...",
        "knowledge_base": "Produto X oferece...",
        "created_by": "admin_user"
    }
)
```

### Invalidar Cache de Prompts

```python
from app.services.tenant_prompt_service import tenant_prompt_service

# Invalidar prompt específico
tenant_prompt_service.invalidate_cache(
    tenant_id=UUID("..."),
    prompt_type=PromptType.SALES_AGENT
)

# Invalidar todos prompts do tenant
tenant_prompt_service.invalidate_cache(tenant_id=UUID("..."))
```

---

## Troubleshooting

### Erro: "Tenant not found"

**Causa:** Tenant slug não existe no banco ou está desativado.

**Solução:**
```bash
# Verificar tenants existentes
curl http://localhost:8000/api/v1/admin/tenants

# Criar tenant se necessário
python scripts/onboard_tenant.py --slug mycompany --name "My Company"
```

### Erro: "Invalid API key"

**Causa:** API key incorreta ou expirada.

**Solução:** API keys são geradas apenas uma vez. Se perdida, você precisa:
1. Gerar nova API key (não implementado - TODO)
2. Ou criar novo tenant

### Erro: "Missing X-Tenant-ID header"

**Causa:** Multi-tenant mode ativado mas headers não enviados.

**Soluções:**
1. Adicionar headers `X-Tenant-ID` e `X-API-Key` na request
2. Ou desativar multi-tenant mode (`MULTI_TENANT_ENABLED=false`)

### Performance: Queries Lentas

**Verificar índices:**
```sql
-- Ver índices em tabelas
\d+ users
\d+ conversations

-- Criar índices compostos se necessário
CREATE INDEX idx_custom ON tabela(tenant_id, outro_campo);
```

**Verificar cache:**
```python
# Aumentar TTL se necessário (em seconds)
tenant_prompt_service.prompt_ttl = 1800  # 30 minutos
```

### Isolamento de Dados: Cross-Tenant Access

**Sempre verificar que queries filtram por tenant_id:**

```python
# ❌ ERRADO - sem filtro de tenant
result = await db.execute(
    select(User).where(User.user_key == user_key)
)

# ✅ CORRETO - com filtro de tenant
result = await db.execute(
    select(User).where(
        User.tenant_id == tenant_id,
        User.user_key == user_key
    )
)
```

---

## Segurança

### API Key Storage

- API keys são armazenadas com hash bcrypt (salt rounds = 12)
- Apenas o prefixo (8 chars) é armazenado em texto plano para identificação
- API keys nunca são retornadas após criação inicial

### Tenant Isolation

- Todos os modelos incluem `tenant_id` foreign key
- Constraints `UNIQUE(tenant_id, field)` previnem duplicação
- Middleware valida tenant antes de processar request
- Tools e services sempre filtram por `tenant_id`

### Rate Limiting (TODO)

- Implementar rate limiting por tenant
- Configurar limites em `tenant.config["rate_limits"]`

---

## Roadmap

### Próximas Features

- [ ] Regeneração de API keys
- [ ] Rate limiting por tenant
- [ ] Billing e usage tracking
- [ ] Tenant admin dashboard
- [ ] Custom domains (subdomain por tenant)
- [ ] Webhooks customizáveis por tenant
- [ ] Audit logs por tenant
- [ ] Export de dados por tenant
- [ ] White-label UI

### Melhorias de Performance

- [ ] Redis cache para prompts e configs
- [ ] Connection pooling por tenant
- [ ] Query optimization automática
- [ ] Lazy loading de relationships

---

## Contribuindo

Para contribuir com o sistema multi-tenant:

1. Sempre adicionar `tenant_id` em novos modelos
2. Sempre filtrar queries por `tenant_id`
3. Testar isolamento de dados entre tenants
4. Documentar novas configurações em `tenant.config`
5. Adicionar exemplos em `examples/`

---

## Suporte

Para questões ou problemas:
- Abrir issue no GitHub
- Verificar logs: `tail -f logs/app.log`
- Consultar este guia: `MULTI_TENANT_GUIDE.md`
