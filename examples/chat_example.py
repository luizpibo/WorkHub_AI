"""
Exemplo de uso da API de Chat
"""
import requests
import json
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"


class WorkHubClient:
    """Cliente Python para a API do WorkHub"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def chat(
        self,
        message: str,
        user_key: str,
        conversation_id: Optional[str] = None
    ) -> dict:
        """
        Envia mensagem ao agente de vendas
        
        Args:
            message: Mensagem do usuário
            user_key: Chave de identificação do usuário
            conversation_id: ID da conversa (opcional)
        
        Returns:
            Resposta do agente
        """
        payload = {
            "message": message,
            "user_key": user_key,
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        response = self.session.post(
            f"{self.base_url}/chat",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_plans(self) -> list:
        """Obtém lista de planos disponíveis"""
        response = self.session.get(f"{self.base_url}/plans")
        response.raise_for_status()
        return response.json()
    
    def analyze_conversation(self, conversation_id: str) -> dict:
        """Analisa uma conversa específica"""
        response = self.session.post(
            f"{self.base_url}/analytics/analyze",
            json={"conversation_id": conversation_id}
        )
        response.raise_for_status()
        return response.json()
    
    def get_funnel_metrics(self) -> dict:
        """Obtém métricas do funil"""
        response = self.session.get(f"{self.base_url}/analytics/funnel")
        response.raise_for_status()
        return response.json()


def exemplo_conversa_completa():
    """Exemplo de conversa completa de vendas"""
    client = WorkHubClient()
    user_key = "exemplo_usuario_123"
    
    print("=" * 60)
    print("EXEMPLO: Conversa Completa de Vendas")
    print("=" * 60)
    
    # Mensagem 1: Interesse inicial
    print("\n[USER] Oi, queria saber sobre coworking")
    response = client.chat(
        message="Oi, queria saber sobre coworking",
        user_key=user_key
    )
    print(f"[AGENT] {response['response']}")
    print(f"[FUNIL] {response['funnel_stage']}")
    
    conversation_id = response['conversation_id']
    
    # Mensagem 2: Perfil do cliente
    print("\n[USER] Sou desenvolvedor freelancer, trabalho 2-3 dias por semana fora de casa")
    response = client.chat(
        message="Sou desenvolvedor freelancer, trabalho 2-3 dias por semana fora de casa",
        user_key=user_key,
        conversation_id=conversation_id
    )
    print(f"[AGENT] {response['response']}")
    print(f"[FUNIL] {response['funnel_stage']}")
    
    # Mensagem 3: Pergunta sobre preço
    print("\n[USER] Quanto custa o plano Flex?")
    response = client.chat(
        message="Quanto custa o plano Flex?",
        user_key=user_key,
        conversation_id=conversation_id
    )
    print(f"[AGENT] {response['response']}")
    print(f"[FUNIL] {response['funnel_stage']}")
    
    # Mensagem 4: Objeção
    print("\n[USER] Está um pouco caro ainda")
    response = client.chat(
        message="Está um pouco caro ainda",
        user_key=user_key,
        conversation_id=conversation_id
    )
    print(f"[AGENT] {response['response']}")
    print(f"[FUNIL] {response['funnel_stage']}")
    
    print("\n" + "=" * 60)
    print(f"Conversa ID: {conversation_id}")
    print("=" * 60)
    
    return conversation_id


def exemplo_listar_planos():
    """Exemplo de listagem de planos"""
    client = WorkHubClient()
    
    print("\n" + "=" * 60)
    print("EXEMPLO: Listar Planos Disponíveis")
    print("=" * 60)
    
    plans = client.get_plans()
    
    for plan in plans:
        print(f"\n📋 {plan['name']} - R$ {plan['price']}/{plan['billing_cycle']}")
        print(f"   Slug: {plan['slug']}")
        print(f"   Features:")
        for feature in plan['features']:
            print(f"   • {feature}")


def exemplo_analytics(conversation_id: str):
    """Exemplo de análise de conversa"""
    client = WorkHubClient()
    
    print("\n" + "=" * 60)
    print("EXEMPLO: Análise de Conversa com IA")
    print("=" * 60)
    
    analysis = client.analyze_conversation(conversation_id)
    
    print(f"\nConversa ID: {analysis['conversation_id']}")
    print(f"\nAnálise:")
    print(analysis['analysis'])


def exemplo_metricas_funil():
    """Exemplo de métricas do funil"""
    client = WorkHubClient()
    
    print("\n" + "=" * 60)
    print("EXEMPLO: Métricas do Funil de Vendas")
    print("=" * 60)
    
    metrics = client.get_funnel_metrics()
    
    print("\n📊 Métricas:")
    print(json.dumps(metrics['metrics'], indent=2, ensure_ascii=False))
    
    print("\n🤖 Análise da IA:")
    print(metrics['ai_analysis']['analysis'])


if __name__ == "__main__":
    # Exemplo 1: Listar planos
    exemplo_listar_planos()
    
    # Exemplo 2: Conversa completa
    conversation_id = exemplo_conversa_completa()
    
    # Exemplo 3: Análise da conversa
    # exemplo_analytics(conversation_id)
    
    # Exemplo 4: Métricas do funil
    # exemplo_metricas_funil()
    
    print("\n✅ Exemplos executados com sucesso!")
    print("\nPara executar análises, descomente as linhas no final do arquivo.")

