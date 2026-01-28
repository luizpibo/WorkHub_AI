"""
Script para validar que todas as tabelas foram criadas corretamente após a migration.
"""
import asyncio
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect
from app.core.config import settings


async def validate_tables():
    """Valida que todas as tabelas esperadas foram criadas"""
    print("=" * 80)
    print("VALIDAÇÃO DE TABELAS APÓS MIGRATION")
    print("=" * 80)
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    # Tabelas esperadas (em ordem de criação)
    expected_tables = [
        # Tabelas da migration 001
        'users',
        'plans',
        'conversations',
        'messages',
        'leads',
        'analysis_reports',
        # Tabelas da migration 002
        'tenants',
        'prompt_templates',
        'knowledge_documents',
    ]
    
    # ENUMs esperados
    expected_enums = [
        'tenantstatus',
        'prompttype',
        'documenttype',
    ]
    
    try:
        async with engine.begin() as conn:
            # Verificar tabelas
            print("\n1. Verificando tabelas...")
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """))
            existing_tables = [row[0] for row in result.fetchall()]
            
            print(f"   Tabelas encontradas: {len(existing_tables)}")
            for table in existing_tables:
                print(f"   - {table}")
            
            # Verificar se todas as tabelas esperadas existem
            missing_tables = set(expected_tables) - set(existing_tables)
            if missing_tables:
                print(f"\n   ❌ Tabelas faltando: {missing_tables}")
                return False
            else:
                print(f"\n   ✅ Todas as {len(expected_tables)} tabelas esperadas foram criadas!")
            
            # Verificar ENUMs
            print("\n2. Verificando ENUMs...")
            result = await conn.execute(text("""
                SELECT typname 
                FROM pg_type 
                WHERE typtype = 'e'
                ORDER BY typname;
            """))
            existing_enums = [row[0] for row in result.fetchall()]
            
            print(f"   ENUMs encontrados: {len(existing_enums)}")
            for enum_name in existing_enums:
                print(f"   - {enum_name}")
            
            # Verificar valores dos ENUMs
            print("\n3. Verificando valores dos ENUMs...")
            for enum_name in expected_enums:
                result = await conn.execute(text(f"""
                    SELECT enumlabel 
                    FROM pg_enum 
                    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = '{enum_name}')
                    ORDER BY enumsortorder;
                """))
                values = [row[0] for row in result.fetchall()]
                print(f"   {enum_name}: {values}")
            
            # Verificar tenant padrão
            print("\n4. Verificando tenant padrão...")
            result = await conn.execute(text("""
                SELECT id, slug, name, status, is_active, created_at
                FROM tenants
                WHERE slug = 'workhub';
            """))
            tenant = result.fetchone()
            
            if tenant:
                print(f"   ✅ Tenant padrão encontrado:")
                print(f"      ID: {tenant[0]}")
                print(f"      Slug: {tenant[1]}")
                print(f"      Name: {tenant[2]}")
                print(f"      Status: {tenant[3]}")
                print(f"      Is Active: {tenant[4]}")
                print(f"      Created At: {tenant[5]}")
            else:
                print("   ❌ Tenant padrão não encontrado!")
                return False
            
            # Verificar colunas tenant_id nas tabelas existentes
            print("\n5. Verificando colunas tenant_id...")
            tables_with_tenant_id = [
                'users', 'plans', 'conversations', 'messages', 
                'leads', 'analysis_reports'
            ]
            
            for table_name in tables_with_tenant_id:
                result = await conn.execute(text(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    AND column_name = 'tenant_id';
                """))
                col = result.fetchone()
                if col:
                    print(f"   ✅ {table_name}.tenant_id existe (tipo: {col[1]})")
                else:
                    print(f"   ❌ {table_name}.tenant_id não encontrado!")
                    return False
            
            # Verificar índices
            print("\n6. Verificando índices importantes...")
            important_indexes = [
                'ix_tenants_slug',
                'ix_users_user_key',
                'ix_plans_slug',
            ]
            
            for index_name in important_indexes:
                result = await conn.execute(text(f"""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE indexname = '{index_name}';
                """))
                idx = result.fetchone()
                if idx:
                    print(f"   ✅ Índice {index_name} existe")
                else:
                    print(f"   ⚠️  Índice {index_name} não encontrado (pode ser normal)")
            
            print("\n" + "=" * 80)
            print("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            return True
            
    except Exception as e:
        print(f"\n❌ ERRO durante validação: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(validate_tables())
    sys.exit(0 if success else 1)
