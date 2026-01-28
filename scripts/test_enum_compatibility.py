"""
Script para testar compatibilidade do ENUM TenantStatus entre Python e PostgreSQL.

Este script verifica se o SQLAlchemy consegue inserir e ler valores do enum
corretamente quando há diferença entre valores Python (minúsculos) e banco (maiúsculos).
"""
import asyncio
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.tenant import Tenant, TenantStatus
from app.core.config import settings
import uuid


async def test_enum_compatibility():
    """Testa inserção e leitura de tenant com enum"""
    print("=" * 80)
    print("TESTE DE COMPATIBILIDADE ENUM TenantStatus")
    print("=" * 80)
    
    # Criar engine e sessão
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            print("\n1. Verificando valores do enum Python:")
            print(f"   TenantStatus.ACTIVE = {TenantStatus.ACTIVE}")
            print(f"   TenantStatus.ACTIVE.value = {TenantStatus.ACTIVE.value}")
            print(f"   TenantStatus.ACTIVE.name = {TenantStatus.ACTIVE.name}")
            
            # Tentar criar um tenant de teste
            print("\n2. Tentando criar tenant de teste...")
            test_tenant = Tenant(
                id=uuid.uuid4(),
                slug=f"test-enum-{uuid.uuid4().hex[:8]}",
                name="Test Enum Compatibility",
                config={},
                status=TenantStatus.ACTIVE,  # Usando enum Python
                is_active=True
            )
            
            print(f"   Tenant criado com status={test_tenant.status}")
            print(f"   Tipo do status: {type(test_tenant.status)}")
            
            session.add(test_tenant)
            await session.commit()
            print("   ✅ Commit realizado com sucesso!")
            
            # Recarregar do banco
            await session.refresh(test_tenant)
            print(f"\n3. Tenant recarregado do banco:")
            print(f"   status={test_tenant.status}")
            print(f"   status.value={test_tenant.status.value}")
            print(f"   status.name={test_tenant.status.name}")
            
            # Verificar valor no banco diretamente
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT status, pg_typeof(status) FROM tenants WHERE id = :id"),
                {"id": test_tenant.id}
            )
            row = result.fetchone()
            print(f"\n4. Valor no banco (SQL direto):")
            print(f"   status={row[0]}")
            print(f"   tipo={row[1]}")
            
            # Limpar
            await session.delete(test_tenant)
            await session.commit()
            print("\n✅ Teste concluído com sucesso!")
            
    except Exception as e:
        print(f"\n❌ ERRO durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_enum_compatibility())
    sys.exit(0 if success else 1)
