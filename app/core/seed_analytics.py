"""Analytics seed script for test data"""
import asyncio
from datetime import datetime, timedelta
from random import choice, randint, sample
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User, WorkType
from app.models.conversation import Conversation, ConversationStatus, FunnelStage
from app.models.message import Message, MessageRole
from app.models.lead import Lead, LeadStage
from app.models.plan import Plan, BillingCycle
from app.utils.logger import logger
from decimal import Decimal


# Dados de exemplo para gerar conversas realistas
USER_NAMES = [
    "João Silva", "Maria Santos", "Pedro Oliveira", "Ana Costa",
    "Carlos Souza", "Julia Ferreira", "Lucas Almeida", "Fernanda Lima",
    "Rafael Martins", "Beatriz Gomes", "Thiago Rodrigues", "Camila Ribeiro",
    "Gabriel Pereira", "Isabela Carvalho", "Bruno Araújo", "Larissa Barbosa",
    "Felipe Dias", "Mariana Rocha", "Rodrigo Castro", "Amanda Monteiro",
    "Gustavo Cardoso", "Patricia Moura", "André Teixeira", "Renata Freitas",
    "Diego Nunes", "Vanessa Campos", "Marcelo Azevedo", "Tatiana Duarte"
]

WORK_TYPES = [WorkType.FREELANCER, WorkType.STARTUP, WorkType.COMPANY, WorkType.OTHER]

MESSAGES_TEMPLATES = {
    "awareness": [
        "Olá, quero saber sobre coworking",
        "Oi, vocês têm espaços de trabalho?",
        "Bom dia, gostaria de informações sobre os planos",
        "Olá, trabalho de casa e quero conhecer o espaço"
    ],
    "interest": [
        "Quanto custa o plano Flex?",
        "Qual a diferença entre os planos?",
        "Preciso de um espaço para trabalhar 3x por semana",
        "Vocês têm salas de reunião disponíveis?"
    ],
    "consideration": [
        "Posso fazer um teste antes de assinar?",
        "Quais são os horários de funcionamento?",
        "Tem estacionamento disponível?",
        "Como funciona o acesso 24/7?"
    ],
    "negotiation": [
        "Tem desconto para pagamento anual?",
        "Posso cancelar a qualquer momento?",
        "Quero agendar uma visita",
        "Preciso de endereço fiscal, vocês oferecem?"
    ],
    "closed_won": [
        "Perfeito, quero contratar o plano Dedicado",
        "Vou fechar o plano Flex",
        "Quero começar hoje mesmo",
        "Como faço para assinar?"
    ],
    "closed_lost": [
        "Acho que está muito caro para mim",
        "Vou pensar melhor e retorno depois",
        "Não é o que estou procurando",
        "Vou trabalhar de casa mesmo"
    ]
}

AGENT_RESPONSES = {
    "awareness": [
        "Olá! Que bom que você se interessou pelo WorkHub. Temos 3 planos flexíveis...",
        "Bem-vindo! O WorkHub oferece espaços de coworking modernos...",
        "Oi! Fico feliz em ajudar. Temos opções para diferentes necessidades..."
    ],
    "interest": [
        "O plano Flex custa R$ 497/mês e oferece 10 dias de acesso...",
        "Temos 3 planos principais: Day Pass, Flex e Dedicado...",
        "Para trabalhar 3x por semana, recomendo o plano Flex..."
    ],
    "consideration": [
        "Sim, oferecemos tour gratuito! Posso agendar para você?",
        "Funcionamos 24/7 no plano Dedicado, e 8h-18h nos outros...",
        "Temos estacionamento sim, e também acesso por transporte público..."
    ],
    "negotiation": [
        "Temos condições especiais para pagamento anual!",
        "Sim, pode cancelar a qualquer momento sem multa...",
        "Perfeito! Vou preparar a proposta para você..."
    ],
    "closed_won": [
        "Excelente escolha! Vou preparar tudo para você...",
        "Ótimo! Vou processar sua contratação agora...",
        "Perfeito! Bem-vindo ao WorkHub!"
    ],
    "closed_lost": [
        "Entendo. Se mudar de ideia, estaremos aqui!",
        "Sem problemas. Qualquer dúvida, pode retornar!",
        "Tudo bem. Obrigado pelo interesse!"
    ]
}

COMMON_OBJECTIONS = [
    "Está muito caro",
    "Trabalho de casa mesmo",
    "Não uso todo dia",
    "Preciso pensar melhor",
    "Não tenho orçamento agora",
    "Já tenho escritório",
    "Prefiro trabalhar de casa"
]


async def seed_analytics_data(session: AsyncSession):
    """Cria dados de teste para analytics"""
    logger.info("Starting analytics seed...")
    
    # Buscar planos existentes
    result = await session.execute(select(Plan))
    plans = result.scalars().all()
    
    # Se não houver planos, criar os básicos
    if not plans:
        logger.warning("No plans found! Creating basic plans...")
        
        plans_data = [
            {
                "name": "Day Pass",
                "slug": "day-pass",
                "price": Decimal("49.00"),
                "billing_cycle": BillingCycle.DAILY,
                "description": "Acesso por 1 dia útil (8h às 18h)",
                "features": ["Acesso por 1 dia útil", "Estação compartilhada", "Wi-Fi", "Café"],
                "is_active": True
            },
            {
                "name": "Flex",
                "slug": "flex",
                "price": Decimal("497.00"),
                "billing_cycle": BillingCycle.MONTHLY,
                "description": "10 dias de acesso por mês",
                "features": ["10 dias/mês", "Estação compartilhada", "Wi-Fi", "Café e snacks"],
                "is_active": True
            },
            {
                "name": "Dedicado",
                "slug": "dedicado",
                "price": Decimal("897.00"),
                "billing_cycle": BillingCycle.MONTHLY,
                "description": "Acesso ilimitado (24/7)",
                "features": ["Acesso ilimitado", "Mesa fixa", "Wi-Fi", "Endereço fiscal"],
                "is_active": True
            }
        ]
        
        for plan_data in plans_data:
            plan = Plan(**plan_data)
            session.add(plan)
        
        await session.flush()
        
        # Buscar novamente
        result = await session.execute(select(Plan))
        plans = result.scalars().all()
        logger.info(f"Created {len(plans)} plans")
    
    day_pass = next((p for p in plans if p.slug == "day-pass"), None)
    flex = next((p for p in plans if p.slug == "flex"), None)
    dedicado = next((p for p in plans if p.slug == "dedicado"), None)
    
    users_created = []
    conversations_created = []
    leads_created = []
    messages_created = []
    
    # Criar 25 usuários com conversas
    for i in range(25):
        user_key = f"test_user_{i+1:03d}"
        work_type = choice(WORK_TYPES)
        
        user = User(
            user_key=user_key,
            name=USER_NAMES[i % len(USER_NAMES)],
            email=f"user{i+1}@example.com",
            phone=f"+5511999{i+1:05d}",
            work_type=work_type,
            company=f"Company {i+1}" if work_type == WorkType.COMPANY else None
        )
        session.add(user)
        await session.flush()
        users_created.append(user)
        
        # Distribuir estágios do funil de forma realista
        # 30% awareness, 25% interest, 20% consideration, 10% negotiation, 10% closed_won, 5% closed_lost
        stage_weights = {
            FunnelStage.AWARENESS: 0.30,
            FunnelStage.INTEREST: 0.25,
            FunnelStage.CONSIDERATION: 0.20,
            FunnelStage.NEGOTIATION: 0.10,
            FunnelStage.CLOSED_WON: 0.10,
            FunnelStage.CLOSED_LOST: 0.05
        }
        
        rand = randint(1, 100)
        if rand <= 30:
            funnel_stage = FunnelStage.AWARENESS
            status = ConversationStatus.ACTIVE
            interested_plan = None
        elif rand <= 55:
            funnel_stage = FunnelStage.INTEREST
            status = ConversationStatus.ACTIVE
            interested_plan = choice([flex, dedicado])
        elif rand <= 75:
            funnel_stage = FunnelStage.CONSIDERATION
            status = ConversationStatus.ACTIVE
            interested_plan = choice([flex, dedicado])
        elif rand <= 85:
            funnel_stage = FunnelStage.NEGOTIATION
            status = ConversationStatus.ACTIVE
            interested_plan = dedicado
        elif rand <= 95:
            funnel_stage = FunnelStage.CLOSED_WON
            status = ConversationStatus.CONVERTED
            interested_plan = choice([flex, dedicado])
        else:
            funnel_stage = FunnelStage.CLOSED_LOST
            status = ConversationStatus.LOST
            interested_plan = None
        
        # Criar conversa
        conversation = Conversation(
            user_id=user.id,
            status=status,
            funnel_stage=funnel_stage,
            interested_plan_id=interested_plan.id if interested_plan else None,
            context_summary=f"Lead interessado em {interested_plan.name if interested_plan else 'informações gerais'}. Estágio: {funnel_stage.value}",
            created_at=datetime.utcnow() - timedelta(days=randint(1, 30))
        )
        session.add(conversation)
        await session.flush()
        conversations_created.append(conversation)
        
        # Criar mensagens (3-10 mensagens por conversa)
        num_messages = randint(3, 10)
        user_messages = MESSAGES_TEMPLATES.get(funnel_stage.value, MESSAGES_TEMPLATES["awareness"])
        agent_responses = AGENT_RESPONSES.get(funnel_stage.value, AGENT_RESPONSES["awareness"])
        
        for msg_idx in range(num_messages):
            # Mensagem do usuário
            user_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=choice(user_messages) if msg_idx == 0 else f"Mensagem {msg_idx + 1} do usuário sobre o plano",
                created_at=conversation.created_at + timedelta(minutes=msg_idx * 5)
            )
            session.add(user_msg)
            messages_created.append(user_msg)
            
            # Resposta do agente
            agent_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=choice(agent_responses) if msg_idx == 0 else f"Resposta {msg_idx + 1} do agente explicando os benefícios",
                created_at=conversation.created_at + timedelta(minutes=msg_idx * 5 + 2)
            )
            session.add(agent_msg)
            messages_created.append(agent_msg)
        
        # Criar lead se não for awareness ou closed_lost
        if funnel_stage not in [FunnelStage.AWARENESS, FunnelStage.CLOSED_LOST]:
            # Score baseado no estágio
            score_map = {
                FunnelStage.INTEREST: randint(20, 40),
                FunnelStage.CONSIDERATION: randint(40, 70),
                FunnelStage.NEGOTIATION: randint(70, 90),
                FunnelStage.CLOSED_WON: 100
            }
            score = score_map.get(funnel_stage, 30)
            
            # Stage do lead
            lead_stage_map = {
                FunnelStage.INTEREST: LeadStage.WARM,
                FunnelStage.CONSIDERATION: LeadStage.HOT,
                FunnelStage.NEGOTIATION: LeadStage.QUALIFIED,
                FunnelStage.CLOSED_WON: LeadStage.CONVERTED
            }
            lead_stage = lead_stage_map.get(funnel_stage, LeadStage.WARM)
            
            # Objeções (30% dos leads têm objeções)
            objections = []
            if randint(1, 100) <= 30 and funnel_stage != FunnelStage.CLOSED_WON:
                objections = sample(COMMON_OBJECTIONS, randint(1, 2))
            
            lead = Lead(
                conversation_id=conversation.id,
                user_id=user.id,
                stage=lead_stage,
                score=score,
                objections=objections,
                preferred_plan_id=interested_plan.id if interested_plan else None,
                next_action="Follow-up em 3 dias" if funnel_stage == FunnelStage.INTEREST else "Agendar visita" if funnel_stage == FunnelStage.CONSIDERATION else None
            )
            session.add(lead)
            leads_created.append(lead)
    
    await session.commit()
    
    logger.info(f"✅ Analytics seed completed!")
    logger.info(f"   - Users created: {len(users_created)}")
    logger.info(f"   - Conversations created: {len(conversations_created)}")
    logger.info(f"   - Leads created: {len(leads_created)}")
    logger.info(f"   - Messages created: {len(messages_created)}")


async def run_seed_analytics():
    """Run analytics seed"""
    async with AsyncSessionLocal() as session:
        try:
            await seed_analytics_data(session)
        except Exception as e:
            logger.error(f"Error during analytics seed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(run_seed_analytics())

