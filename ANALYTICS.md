# 📊 Analytics e Dados de Teste

Este documento explica a lógica implementada nas funções de analytics e os dados de teste disponíveis no sistema.

## 🗄️ Dados de Teste

### Origem dos Dados

Os dados de teste são gerados automaticamente pelo script `app/core/seed_analytics.py`, que é executado quando você roda:

```bash
docker-compose exec app python -m app.core.seed
```

### O que é Criado

O script `seed_analytics.py` cria:

- **25 usuários** com nomes, emails e telefones aleatórios
- **25 conversas** distribuídas pelos diferentes estágios do funil:
  - 30% Awareness (primeiro contato)
  - 25% Interest (demonstrou interesse)
  - 20% Consideration (considerando planos)
  - 10% Negotiation (negociando condições)
  - 10% Closed Won (fechou venda)
  - 5% Closed Lost (perdeu venda)
- **50-200 mensagens** de exemplo distribuídas entre as conversas
- **15-20 leads qualificados** com diferentes estágios:
  - `cold`: Primeiro contato
  - `warm`: Demonstrou interesse
  - `hot`: Pronto para fechar
  - `qualified`: Qualificado para venda
  - `converted`: Convertido
- **Objeções comuns** associadas aos leads (ex: "preço alto", "prefere trabalhar de casa")

### Distribuição Realista

Os dados são gerados de forma a simular um cenário realista:
- Conversas têm diferentes durações e números de mensagens
- Leads têm scores variados baseados no interesse demonstrado
- Objeções são distribuídas de forma natural
- Datas de criação são distribuídas ao longo do último mês

## 🔧 Funções de Analytics

### 1. `get_funnel_metrics`

**O que faz:**
Calcula métricas do funil de vendas para um período específico.

**Lógica:**
1. Busca todas as conversas criadas no período especificado (padrão: últimos 30 dias)
2. Agrupa por estágio do funil (Awareness, Interest, Consideration, Negotiation, Closed Won)
3. Calcula taxas de conversão entre estágios consecutivos
4. Retorna contagem por estágio e taxas de conversão

**Exemplo de retorno:**
```json
{
  "period": {
    "start": "2025-11-27T00:00:00",
    "end": "2025-12-27T00:00:00"
  },
  "stages": {
    "awareness": 8,
    "interest": 6,
    "consideration": 5,
    "negotiation": 2,
    "closed_won": 2
  },
  "conversion_rates": {
    "awareness_to_interest": 75.0,
    "interest_to_consideration": 83.33,
    "consideration_to_negotiation": 40.0,
    "negotiation_to_closed_won": 100.0
  },
  "total_leads": 23
}
```

**Uso:**
- Identificar gargalos no funil
- Acompanhar performance ao longo do tempo
- Comparar períodos diferentes

### 2. `get_plan_performance`

**O que faz:**
Analisa a performance de cada plano (Day Pass, Flex, Dedicado) em termos de interesse e conversão.

**Lógica:**
1. Busca todos os planos ativos
2. Para cada plano, conta:
   - Quantas conversas demonstraram interesse (`interested_plan_id`)
   - Quantas conversas foram convertidas (`status = CONVERTED`)
3. Calcula taxa de conversão: `(conversões / interesse) * 100`

**Exemplo de retorno:**
```json
{
  "plans": [
    {
      "plan_name": "Day Pass",
      "plan_slug": "day-pass",
      "interest_count": 5,
      "conversion_count": 1,
      "conversion_rate": 20.0
    },
    {
      "plan_name": "Flex",
      "plan_slug": "flex",
      "interest_count": 12,
      "conversion_count": 4,
      "conversion_rate": 33.33
    },
    {
      "plan_name": "Dedicado",
      "plan_slug": "dedicado",
      "interest_count": 8,
      "conversion_count": 3,
      "conversion_rate": 37.5
    }
  ],
  "total_plans": 3
}
```

**Uso:**
- Identificar qual plano está vendendo mais
- Comparar taxas de conversão entre planos
- Ajustar estratégias de vendas por plano

### 3. `get_common_objections`

**O que faz:**
Identifica as objeções mais comuns apresentadas pelos leads.

**Lógica:**
1. Busca todos os leads que têm objeções registradas
2. Conta a frequência de cada objeção
3. Ordena por frequência (mais comum primeiro)
4. Retorna as top 10 objeções

**Exemplo de retorno:**
```json
{
  "total_leads_with_objections": 15,
  "objections": [
    {
      "objection": "preço alto",
      "count": 8
    },
    {
      "objection": "prefere trabalhar de casa",
      "count": 5
    },
    {
      "objection": "não usa todo dia",
      "count": 3
    }
  ]
}
```

**Uso:**
- Identificar padrões de rejeição
- Treinar equipe de vendas para superar objeções comuns
- Ajustar estratégias de comunicação

### 4. `get_conversations_by_stage`

**O que faz:**
Lista conversas filtradas por estágio específico do funil.

**Lógica:**
1. Valida o estágio fornecido (awareness, interest, consideration, negotiation, closed_won, closed_lost)
2. Busca conversas com o estágio especificado
3. Limita a 50 conversas (mais recentes)
4. Retorna lista com informações básicas de cada conversa

**Exemplo de retorno:**
```json
{
  "stage": "negotiation",
  "count": 3,
  "conversations": [
    {
      "id": "uuid-1",
      "user_id": "uuid-user-1",
      "status": "active",
      "context_summary": "Cliente interessado no Plano Dedicado...",
      "created_at": "2025-12-20T10:00:00"
    }
  ]
}
```

**Uso:**
- Focar em leads em estágios específicos
- Analisar conversas em negociação
- Identificar oportunidades de follow-up

### 5. `get_recent_leads`

**O que faz:**
Lista os leads mais recentes cadastrados no sistema, incluindo leads explícitos e conversas qualificadas.

**Lógica:**
1. Busca leads da tabela `leads` ordenados por data de criação (mais recentes primeiro)
2. Busca conversas com status `AWAITING_HUMAN` que não têm lead explícito
3. Combina ambos os resultados
4. Para cada item, busca informações do usuário (nome, email, telefone)
5. Ordena tudo por data de criação e limita ao número solicitado

**Tipos de itens retornados:**
- **`type: "lead"`**: Lead explicitamente criado na tabela `leads`
- **`type: "qualified_conversation"`**: Conversa qualificada (handoff solicitado) sem lead explícito

**Exemplo de retorno:**
```json
{
  "total": 10,
  "leads": [
    {
      "type": "lead",
      "id": "lead-uuid",
      "conversation_id": "conv-uuid",
      "stage": "hot",
      "score": 80,
      "description": "Handoff solicitado: Cliente pronto para fechar",
      "created_at": "2025-12-27T22:41:40",
      "contact": {
        "name": "Yan Victor",
        "email": "yan@email.com",
        "phone": "619888-8888"
      },
      "objections": []
    },
    {
      "type": "qualified_conversation",
      "id": "conv-uuid-2",
      "conversation_id": "conv-uuid-2",
      "stage": "warm",
      "score": 60,
      "description": "Cliente interessado no Plano Flex",
      "created_at": "2025-12-27T22:31:12",
      "contact": {
        "name": "Luiz",
        "email": "luiz@interage.ai",
        "phone": "61983385897"
      },
      "objections": [],
      "handoff_reason": "Cliente solicitou atendimento humano"
    }
  ]
}
```

**Uso:**
- Acompanhar leads mais recentes para follow-up
- Verificar se leads estão sendo criados corretamente
- Identificar conversas qualificadas que precisam de atenção

## 🔐 Controle de Acesso

Todas as funções de analytics requerem **privilégios de administrador**. O sistema verifica se o usuário tem "ADMIN" no nome antes de permitir acesso.

**Como funciona:**
- Usuários com nome contendo "admin", "ADMIN" ou "administrador" são identificados como admins
- A verificação é feita pela função `is_admin_user()` em `app/services/auth_service.py`
- Se o usuário não for admin, as funções retornam erro de acesso negado

## 📈 Fluxo de Dados

```
Conversas → Funil de Vendas → Leads → Analytics
    ↓            ↓              ↓         ↓
Messages    Funnel Stage    Lead Stage  Métricas
```

1. **Conversas** são criadas quando usuários interagem com o Sales Agent
2. **Funil de Vendas** rastreia o progresso de cada conversa (Awareness → Interest → Consideration → Negotiation → Closed Won/Lost)
3. **Leads** são criados quando:
   - O Sales Agent explicitamente cria um lead usando `create_lead`
   - Um handoff é solicitado (lead criado automaticamente)
4. **Analytics** agrega e analisa todos esses dados para fornecer insights

## 🎯 Casos de Uso

### Para Administradores

1. **Monitorar Performance do Funil**
   - Use `get_funnel_metrics` para ver quantos leads estão em cada estágio
   - Identifique gargalos (baixas taxas de conversão)
   - Acompanhe tendências ao longo do tempo

2. **Analisar Performance de Planos**
   - Use `get_plan_performance` para ver qual plano converte melhor
   - Ajuste estratégias de vendas baseado nos dados
   - Identifique oportunidades de upsell

3. **Entender Objeções**
   - Use `get_common_objections` para identificar padrões
   - Treine equipe para superar objeções comuns
   - Ajuste comunicação e materiais de vendas

4. **Acompanhar Leads Recentes**
   - Use `get_recent_leads` para ver os leads mais recentes
   - Faça follow-up com leads qualificados
   - Verifique se o processo de criação de leads está funcionando

5. **Analisar Conversas Específicas**
   - Use `get_conversations_by_stage` para focar em estágios específicos
   - Use `get_conversation_history` para entender contexto completo

## 🔄 Atualização de Dados

Os dados de teste são estáticos (criados uma vez). Para atualizar:

```bash
# Recriar todos os dados de teste
docker-compose exec app python -m app.core.seed
```

**Nota:** Isso irá recriar todos os dados, incluindo planos e dados de analytics. Use com cuidado em produção!

