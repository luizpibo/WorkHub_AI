#!/usr/bin/env python3
"""
Script de teste para validar o fluxo completo dos agentes
Execute: docker-compose exec app python test_agent_flow.py
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.agents.sales_agent import create_sales_agent
from app.agents.analyst_agent import create_analyst_agent
from app.models.user import User
from app.models.conversation import Conversation
from app.core.database import Base


async def test_sales_agent():
    """Testa o Sales Agent"""
    print("\n" + "="*60)
    print("🧪 TESTE 1: Sales Agent")
    print("="*60)
    
    try:
        # Criar engine e sessão
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Criar agente
            print("✓ Criando Sales Agent...")
            agent = create_sales_agent(db)
            
            # Testar invocação
            print("✓ Testando invocação do agente...")
            result = await agent.invoke(
                message="Olá, quero saber sobre os planos de coworking",
                conversation_id="00000000-0000-0000-0000-000000000001",
                user_id="00000000-0000-0000-0000-000000000001",
                user_name="Teste",
                work_type="freelancer",
                conversation_summary="Primeira interação",
                funnel_stage="awareness",
                chat_history=[]
            )
            
            # Verificar resultado
            if "output" in result:
                print("✅ Sales Agent funcionando corretamente!")
                print(f"   Resposta: {result['output'][:100]}...")
                return True
            elif "error" in result:
                print(f"❌ Erro no Sales Agent: {result['error']}")
                return False
            else:
                print("⚠️  Resposta inesperada do Sales Agent")
                return False
                
    except Exception as e:
        print(f"❌ Exceção no teste do Sales Agent: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_analyst_agent():
    """Testa o Analyst Agent"""
    print("\n" + "="*60)
    print("🧪 TESTE 2: Analyst Agent")
    print("="*60)
    
    try:
        # Criar engine e sessão
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Criar agente
            print("✓ Criando Analyst Agent...")
            agent = create_analyst_agent(db)
            
            # Testar análise de funil
            print("✓ Testando análise de funil...")
            result = await agent.get_funnel_analysis()
            
            # Verificar resultado
            if "analysis" in result:
                print("✅ Analyst Agent funcionando corretamente!")
                print(f"   Análise: {result['analysis'][:100]}...")
                return True
            elif "error" in result:
                print(f"❌ Erro no Analyst Agent: {result['error']}")
                return False
            else:
                print("⚠️  Resposta inesperada do Analyst Agent")
                return False
                
    except Exception as e:
        print(f"❌ Exceção no teste do Analyst Agent: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling():
    """Testa tratamento de erros"""
    print("\n" + "="*60)
    print("🧪 TESTE 3: Tratamento de Erros")
    print("="*60)
    
    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            agent = create_sales_agent(db)
            
            # Testar com entrada inválida
            print("✓ Testando com entrada inválida...")
            result = await agent.invoke(
                message="",  # Mensagem vazia
                conversation_id="invalid-uuid",  # UUID inválido
                user_id="invalid-uuid",
                user_name=None,
                work_type=None,
                conversation_summary=None,
                funnel_stage="awareness",
                chat_history=[]
            )
            
            # Deve retornar erro mas não crashar
            if "error" in result or "output" in result:
                print("✅ Tratamento de erros funcionando!")
                return True
            else:
                print("⚠️  Comportamento inesperado com entrada inválida")
                return False
                
    except Exception as e:
        print(f"❌ Exceção no teste de erro: {e}")
        return False


async def test_configuration():
    """Testa configurações"""
    print("\n" + "="*60)
    print("🧪 TESTE 4: Configurações")
    print("="*60)
    
    try:
        from app.agents.base import get_llm
        from app.core.config import settings
        
        print("✓ Verificando configuração do LLM...")
        llm = get_llm()
        
        # Verificar apenas atributos suportados por ambos providers
        # max_retries: ✓ (ambos)
        # request_timeout: ✗ (Gemini não suporta da mesma forma)
        # max_tokens: ✗ (Gemini não suporta)
        
        provider = settings.LLM_PROVIDER.lower()
        
        checks = {
            "max_retries": getattr(llm, 'max_retries', None) == 3,
        }
        
        # Adicionar checks específicos por provider
        if provider == "openai":
            checks["request_timeout"] = getattr(llm, 'request_timeout', None) == 60
            checks["max_tokens"] = getattr(llm, 'max_tokens', None) == 2000
        else:
            # Para Gemini, verificar apenas atributos básicos
            checks["temperature"] = hasattr(llm, 'temperature')
            checks["model"] = hasattr(llm, 'model')
        
        all_ok = all(checks.values())
        
        if all_ok:
            print("✅ Configurações corretas!")
            for key, value in checks.items():
                print(f"   {key}: {'✓' if value else '✗'}")
            return True
        else:
            print("⚠️  Algumas configurações incorretas:")
            for key, value in checks.items():
                print(f"   {key}: {'✓' if value else '✗'}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar configurações: {e}")
        return False


async def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("🚀 INICIANDO TESTES DO SISTEMA MULTI-AGENTE")
    print("="*60)
    
    results = []
    
    # Teste 1: Sales Agent
    results.append(("Sales Agent", await test_sales_agent()))
    
    # Teste 2: Analyst Agent
    results.append(("Analyst Agent", await test_analyst_agent()))
    
    # Teste 3: Tratamento de Erros
    results.append(("Tratamento de Erros", await test_error_handling()))
    
    # Teste 4: Configurações
    results.append(("Configurações", await test_configuration()))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status}: {name}")
    
    print(f"\n{'='*60}")
    print(f"Total: {passed}/{total} testes passaram")
    print(f"{'='*60}\n")
    
    # Retornar código de saída
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())

