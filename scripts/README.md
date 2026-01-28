# Tenant Onboarding Scripts

Scripts para gerenciar tenants na plataforma multi-tenant.

## onboard_tenant.py

Script para criar e configurar novos tenants automaticamente.

### Uso Básico

**Modo 1: Com arquivo de configuração (recomendado)**

```bash
python scripts/onboard_tenant.py --config examples/tenant_config_example.json
```

**Modo 2: Onboarding simples (apenas tenant)**

```bash
python scripts/onboard_tenant.py --slug mycompany --name "My Company"
```

### Formato do Arquivo de Configuração

```json
{
  "slug": "techspace",
  "name": "TechSpace Coworking",
  "status": "active",
  "config": {
    "business_type": "coworking",
    "currency": "USD",
    "features": {
      "enable_handoff": true,
      "enable_analytics": true
    },
    "funnel_config": {
      "stages": [
        {"key": "awareness", "name": "Awareness"},
        {"key": "interest", "name": "Interest"}
      ]
    },
    "llm": {
      "provider": "openai",
      "model": "gpt-4o-mini"
    }
  },
  "plans": [
    {
      "name": "Basic Plan",
      "slug": "basic",
      "price": 99.00,
      "billing_cycle": "monthly",
      "features": ["Feature 1", "Feature 2"],
      "description": "Basic plan description"
    }
  ],
  "prompts": {
    "sales_agent": "Your custom sales agent prompt...",
    "admin_agent": "Your custom admin agent prompt..."
  },
  "knowledge_documents": [
    {
      "title": "Product Knowledge",
      "slug": "product-knowledge",
      "content": "Your product knowledge content...",
      "document_type": "product"
    }
  ]
}
```

### Campos Obrigatórios

- `slug`: Identificador único do tenant (apenas letras minúsculas, números e hífens)
- `name`: Nome de exibição do tenant

### Campos Opcionais

- `status`: Status do tenant (active, trial, suspended, cancelled) - padrão: "active"
- `config`: Configurações customizadas do tenant
- `plans`: Lista de planos/produtos
- `prompts`: Prompts customizados por tipo
- `knowledge_documents`: Documentos da base de conhecimento

### Saída do Script

O script irá:
1. Criar o tenant no banco de dados
2. Gerar uma API key única
3. Criar planos (se fornecidos)
4. Criar prompts customizados (se fornecidos)
5. Criar documentos de conhecimento (se fornecidos)
6. Exibir um resumo com as credenciais

**⚠️ IMPORTANTE:** A API key é mostrada **apenas uma vez**. Salve-a imediatamente!

### Exemplo de Saída

```
================================================================================
✅ TENANT ONBOARDING COMPLETED SUCCESSFULLY
================================================================================

Tenant ID:     a1b2c3d4-e5f6-7890-abcd-ef1234567890
Tenant Slug:   techspace
Tenant Name:   TechSpace Coworking
Status:        active

🔑 API KEY:    te_abc123xyz789def456ghi012jkl345mno
   (Prefix:    te_abc12...)

⚠️  SAVE THIS API KEY! It will not be shown again.

--------------------------------------------------------------------------------
TEST CURL COMMAND:
--------------------------------------------------------------------------------

curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: techspace" \
  -H "X-API-Key: te_abc123xyz789def456ghi012jkl345mno" \
  -d '{
    "message": "Olá!",
    "user_key": "test_user_1",
    "user_name": "Test User"
  }'

================================================================================
```

### Testando o Tenant

Após o onboarding, teste o tenant usando o comando curl fornecido ou através da API:

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/chat",
    headers={
        "X-Tenant-ID": "techspace",
        "X-API-Key": "te_abc123xyz789def456ghi012jkl345mno"
    },
    json={
        "message": "Hello!",
        "user_key": "user123",
        "user_name": "John Doe"
    }
)

print(response.json())
```

### Troubleshooting

**Erro: "Tenant already exists"**
- O slug já está em uso. Escolha outro slug único.

**Erro: "Missing required field"**
- Verifique se o arquivo JSON contém os campos `slug` e `name`.

**Erro: "Invalid slug format"**
- O slug deve conter apenas letras minúsculas, números e hífens.

**Erro: Database connection failed**
- Verifique se o banco de dados está rodando e as configurações em `.env` estão corretas.

### Exemplos

Ver arquivo `examples/tenant_config_example.json` para um exemplo completo de configuração.
