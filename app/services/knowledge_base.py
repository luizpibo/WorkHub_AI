"""Knowledge base service for product information"""
from typing import List, Dict, Any
from decimal import Decimal


class KnowledgeBase:
    """Service for accessing product knowledge"""
    
    @staticmethod
    def get_plans_summary() -> str:
        """Get formatted summary of all plans"""
        return """
PLANOS WORKHUB:

1. DAY PASS - R$ 49/dia
   - Acesso por 1 dia útil (8h-18h)
   - Estação compartilhada
   - Wi-Fi 1Gbps + Café à vontade
   - 2h sala de reunião
   - Ideal: Freelancers, teste do espaço

2. FLEX - R$ 497/mês
   - 10 dias de acesso/mês
   - Estação compartilhada
   - Wi-Fi 1Gbps + Café e snacks
   - 4h sala de reunião/mês
   - Armário compartilhado
   - Eventos e comunidade
   - Ideal: Profissionais híbridos (2-3x/semana)

3. DEDICADO - R$ 897/mês
   - Acesso ilimitado 24/7
   - Mesa fixa personalizada
   - Wi-Fi 1Gbps + Café e snacks
   - 10h sala de reunião/mês
   - Armário privativo
   - Endereço fiscal
   - Suporte administrativo
   - Ideal: Startups, pequenas empresas
"""
    
    @staticmethod
    def get_plan_comparison(plan_slugs: List[str]) -> Dict[str, Any]:
        """
        Compare multiple plans
        
        Args:
            plan_slugs: List of plan slugs to compare
        
        Returns:
            Comparison dictionary
        """
        plans_data = {
            "day-pass": {
                "name": "Day Pass",
                "price": Decimal("49.00"),
                "billing": "diário",
                "access": "1 dia útil (8h-18h)",
                "workspace": "Compartilhada",
                "meeting_room": "2h (disponibilidade)",
                "storage": "Não",
                "fiscal_address": "Não",
                "events": "Não",
                "best_for": "Teste, reuniões pontuais"
            },
            "flex": {
                "name": "Flex",
                "price": Decimal("497.00"),
                "billing": "mensal",
                "access": "10 dias/mês",
                "workspace": "Compartilhada",
                "meeting_room": "4h/mês",
                "storage": "Armário compartilhado",
                "fiscal_address": "Não",
                "events": "Sim",
                "best_for": "Híbrido (2-3x/semana)"
            },
            "dedicado": {
                "name": "Dedicado",
                "price": Decimal("897.00"),
                "billing": "mensal",
                "access": "Ilimitado 24/7",
                "workspace": "Mesa fixa",
                "meeting_room": "10h/mês",
                "storage": "Armário privativo",
                "fiscal_address": "Sim",
                "events": "Sim (prioritário)",
                "best_for": "Startups, empresas"
            }
        }
        
        comparison = {
            "plans": [plans_data.get(slug) for slug in plan_slugs if slug in plans_data],
            "comparison_points": [
                "Preço",
                "Acesso",
                "Tipo de Estação",
                "Salas de Reunião",
                "Armazenamento",
                "Endereço Fiscal",
                "Eventos"
            ]
        }
        
        return comparison
    
    @staticmethod
    def get_objection_handlers() -> Dict[str, str]:
        """Get common objections and how to handle them"""
        return {
            "muito_caro": (
                "Entendo sua preocupação com o investimento. Vamos fazer um cálculo: "
                "se você trabalha em cafés, gasta em média R$30/dia (café + lanche). "
                "Em 10 dias = R$300. O Flex custa R$497, mas você tem internet 1Gbps, "
                "sala de reunião, café ilimitado e networking. A diferença de R$197 "
                "traz produtividade e oportunidades que podem gerar muito mais retorno."
            ),
            "trabalho_de_casa": (
                "Trabalhar de casa tem suas vantagens, mas muitos profissionais "
                "relatam dificuldade em separar vida pessoal e profissional. "
                "Na WorkHub, você tem um ambiente dedicado ao trabalho, o que "
                "aumenta a produtividade em até 40% segundo nossos membros. "
                "Além disso, o networking pode gerar novas oportunidades de negócio."
            ),
            "nao_uso_todo_dia": (
                "Perfeito! É exatamente por isso que criamos o Plano Flex. "
                "Você tem 10 dias de acesso por mês, ideal para quem trabalha "
                "2-3 vezes por semana fora de casa. Comparando: 10 Day Pass = R$490, "
                "enquanto o Flex custa R$497 e inclui salas de reunião, armário "
                "e eventos. Muito mais vantajoso!"
            ),
            "preciso_mais_salas": (
                "As horas de sala de reunião incluídas são para uso regular. "
                "Caso precise de mais, você pode agendar horas extras: "
                "R$40/hora no Flex ou R$30/hora no Dedicado (30% de desconto). "
                "Muitos membros acham que as horas incluídas são suficientes "
                "para suas necessidades mensais."
            )
        }
    
    @staticmethod
    def calculate_roi(plan_slug: str, days_per_week: int = 3) -> Dict[str, Any]:
        """
        Calculate ROI for a plan based on usage
        
        Args:
            plan_slug: Plan slug
            days_per_week: Expected days of use per week
        
        Returns:
            ROI calculation
        """
        days_per_month = days_per_week * 4
        
        calculations = {
            "day-pass": {
                "plan_cost": Decimal("49.00") * days_per_month,
                "alternative_cost": Decimal("30.00") * days_per_month,  # Café
                "savings": Decimal("0"),
                "benefits": ["Flexibilidade total", "Sem compromisso"]
            },
            "flex": {
                "plan_cost": Decimal("497.00"),
                "alternative_cost": Decimal("49.00") * min(days_per_month, 10),
                "savings": Decimal("49.00") * min(days_per_month, 10) - Decimal("497.00"),
                "benefits": ["Economia vs Day Pass", "Salas de reunião", "Eventos", "Armário"]
            },
            "dedicado": {
                "plan_cost": Decimal("897.00"),
                "alternative_cost": Decimal("1500.00"),  # Aluguel escritório pequeno
                "savings": Decimal("603.00"),
                "benefits": ["Economia vs aluguel", "Sem IPTU/condomínio", "Endereço fiscal", "Flexibilidade"]
            }
        }
        
        return calculations.get(plan_slug, {})


# Singleton instance
knowledge_base = KnowledgeBase()

