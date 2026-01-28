# Comandos para Reset e Teste da Migration

## Etapa 1: Reset Completo do Banco de Dados

Execute os seguintes comandos na ordem:

```bash
# 1. Parar todos os containers
docker compose down

# 2. Remover volumes (ZERA banco completamente - apaga TODOS os dados)
docker compose down -v

# 3. Verificar que volumes foram removidos (opcional)
docker volume ls | grep postgres

# 4. Recriar containers do zero
docker compose up --build
```

**⚠️ ATENÇÃO**: O comando `docker compose down -v` apaga TODOS os dados do banco. Use apenas em desenvolvimento.

## Etapa 2: Monitorar Logs da Migration

Após subir os containers, monitore os logs:

```bash
# Ver logs em tempo real
docker compose logs -f app

# Ou ver apenas os últimos logs
docker compose logs --tail=100 app
```

## Etapa 3: Verificar Migration Executada

Após os containers subirem, verifique se a migration executou corretamente:

```bash
# Verificar versão atual da migration
docker compose exec app alembic current

# Deve mostrar: 002 (head)
```

## Etapa 4: Validar Tabelas Criadas

Verifique se todas as tabelas foram criadas:

```bash
# Listar todas as tabelas
docker compose exec db psql -U workhub -d workhub_db -c "\dt"

# Verificar tenant criado
docker compose exec db psql -U workhub -d workhub_db -c "SELECT id, slug, name, status FROM tenants;"

# Verificar tipo do status no banco
docker compose exec db psql -U workhub -d workhub_db -c "SELECT status, pg_typeof(status) FROM tenants;"
```

## Etapa 5: Testar Compatibilidade ENUM Python/Banco

Execute o script de teste:

```bash
# Executar script de teste de compatibilidade
docker compose exec app python scripts/test_enum_compatibility.py
```

Este script vai:
1. Criar um tenant de teste usando o enum Python (`TenantStatus.ACTIVE`)
2. Inserir no banco
3. Ler de volta e verificar se os valores estão corretos
4. Verificar valor direto no banco via SQL

## Checklist de Validação

Após executar os comandos acima, verifique:

- [ ] Migration 001 executou sem erros
- [ ] Migration 002 executou sem erros
- [ ] ENUMs foram criados corretamente (`tenantstatus`, `prompttype`, `documenttype`)
- [ ] Tabela `tenants` foi criada
- [ ] INSERT do tenant padrão funcionou (com cast de ENUM)
- [ ] Todas as outras tabelas foram criadas (`prompt_templates`, `knowledge_documents`, etc.)
- [ ] UPDATEs executaram corretamente (backfill de `tenant_id`)
- [ ] Seed executou e populou dados (se `AUTO_SEED=true`)
- [ ] API está funcionando corretamente
- [ ] Script de teste de compatibilidade ENUM passou

## Possíveis Problemas e Soluções

### Erro: "column status is of type tenantstatus but expression is of type character varying"

**Causa**: Cast de ENUM não está sendo aplicado corretamente na migration.

**Solução**: Verificar se a linha 182 da migration tem `CAST(:status AS tenantstatus)`.

### Erro: "relation 'plans' does not exist"

**Causa**: Migration não completou, seed tentou executar antes das tabelas serem criadas.

**Solução**: Verificar logs da migration para encontrar o erro específico.

### Erro: Enum values mismatch entre Python e banco

**Causa**: SQLAlchemy pode estar usando valores do enum Python ("active") em vez de nomes ("ACTIVE").

**Solução**: Se o teste de compatibilidade falhar, pode ser necessário ajustar o modelo para usar `values_callable` ou alinhar os valores.

## Próximos Passos

Após validar que tudo está funcionando:

1. Testar inserção de tenant via API (`POST /admin/tenants`)
2. Verificar se queries filtram por `tenant_id` corretamente
3. Testar middleware de autenticação por tenant
4. Validar isolamento de dados entre tenants
