#!/usr/bin/env python3
"""
Script para verificar configuração do sistema
Execute: docker-compose exec app python check_config.py
"""
import os
from app.core.config import settings

def check_config():
    """Verifica configurações importantes"""
    print("\n" + "="*60)
    print("🔍 VERIFICAÇÃO DE CONFIGURAÇÃO")
    print("="*60)
    
    issues = []
    
    # Verificar API Key
    print("\n✓ Verificando OpenAI API Key...")
    if not settings.OPENAI_API_KEY:
        issues.append("❌ OPENAI_API_KEY não configurada")
        print("   ❌ OPENAI_API_KEY não configurada")
    elif len(settings.OPENAI_API_KEY) < 20:
        issues.append("❌ OPENAI_API_KEY parece inválida (muito curta)")
        print(f"   ⚠️  OPENAI_API_KEY muito curta: {len(settings.OPENAI_API_KEY)} caracteres")
    elif not settings.OPENAI_API_KEY.startswith("sk-"):
        issues.append("⚠️  OPENAI_API_KEY não começa com 'sk-'")
        print(f"   ⚠️  OPENAI_API_KEY não começa com 'sk-': {settings.OPENAI_API_KEY[:7]}...")
    else:
        # Não exibir partes da chave por segurança
        print(f"   ✅ OPENAI_API_KEY configurada (oculta por segurança)")
    
    # Verificar Modelo
    print("\n✓ Verificando modelo OpenAI...")
    print(f"   ✅ Modelo: {settings.OPENAI_MODEL}")
    
    # Verificar Database URL
    print("\n✓ Verificando Database URL...")
    if "localhost" in settings.DATABASE_URL and "db:" not in settings.DATABASE_URL:
        print("   ⚠️  DATABASE_URL aponta para localhost (pode não funcionar no Docker)")
        print(f"      Atual: {settings.DATABASE_URL}")
        print("      Esperado: postgresql+asyncpg://workhub:workhub123@db:5432/workhub_db")
    else:
        print(f"   ✅ DATABASE_URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'OK'}")
    
    # Verificar Ambiente
    print("\n✓ Verificando ambiente...")
    print(f"   ✅ APP_ENV: {settings.APP_ENV}")
    print(f"   ✅ LOG_LEVEL: {settings.LOG_LEVEL}")
    
    # Resumo
    print("\n" + "="*60)
    if issues:
        print("⚠️  PROBLEMAS ENCONTRADOS:")
        for issue in issues:
            print(f"   {issue}")
        print("\n💡 SOLUÇÃO:")
        print("   1. Verifique o arquivo .env na raiz do projeto")
        print("   2. Certifique-se de que OPENAI_API_KEY está configurada")
        print("   3. Reinicie os containers: docker-compose restart")
        return False
    else:
        print("✅ Todas as configurações estão corretas!")
        return True
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        check_config()
    except Exception as e:
        print(f"\n❌ Erro ao verificar configuração: {e}")
        import traceback
        traceback.print_exc()

