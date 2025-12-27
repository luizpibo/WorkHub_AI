"""Handoff tools for transferring conversations to human agents"""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import uuid

from app.models.conversation import Conversation, ConversationStatus, FunnelStage
from app.models.message import Message, MessageRole
from app.models.user import User
from app.models.lead import Lead, LeadStage
from app.utils.logger import logger


class RequestHandoffInput(BaseModel):
    """Input schema for request_handoff tool"""
    conversation_id: str = Field(..., description="Conversation ID")
    reason: str = Field(..., description="Motivo da transferência (ex: cliente pronto para fechar, dúvidas complexas)")
    summary: str = Field(..., description="Resumo da conversa até o momento")


async def request_handoff(
    conversation_id: str,
    reason: str,
    summary: str,
    db: AsyncSession,
) -> dict:
    """
    Solicita transferência da conversa para atendimento humano
    
    Args:
        conversation_id: Conversation UUID
        reason: Motivo da transferência
        summary: Resumo da conversa
        db: Database session
    
    Returns:
        Confirmação da transferência
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
        
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_uuid)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return {"error": "Conversation not found"}
        
        # Atualizar status para aguardando humano
        conversation.status = ConversationStatus.AWAITING_HUMAN
        conversation.handoff_reason = reason
        conversation.handoff_requested_at = datetime.utcnow()
        conversation.context_summary = summary
        
        # Salvar mensagem de sistema informando a transferência
        system_message = Message(
            conversation_id=conv_uuid,
            role=MessageRole.SYSTEM,
            content=f"🔄 Transferência solicitada para atendimento humano.\n\nMotivo: {reason}\n\nResumo: {summary}",
            metadata={
                "handoff_reason": reason,
                "handoff_time": datetime.utcnow().isoformat(),
            }
        )
        db.add(system_message)
        
        # Criar ou atualizar lead automaticamente
        lead_result = await db.execute(
            select(Lead).where(Lead.conversation_id == conv_uuid)
        )
        existing_lead = lead_result.scalar_one_or_none()
        
        # Determinar stage e score baseado no estágio do funil e motivo
        # Se está em negociação ou closed_won, é HOT ou QUALIFIED
        if conversation.funnel_stage in [FunnelStage.NEGOTIATION, FunnelStage.CLOSED_WON]:
            lead_stage = LeadStage.HOT if "pronto" in reason.lower() or "fechar" in reason.lower() else LeadStage.QUALIFIED
            score = 80 if lead_stage == LeadStage.HOT else 70
        elif conversation.funnel_stage == FunnelStage.CONSIDERATION:
            lead_stage = LeadStage.WARM
            score = 60
        else:
            lead_stage = LeadStage.WARM
            score = 50
        
        # Determinar preferred_plan_id se houver
        preferred_plan_id = conversation.interested_plan_id
        
        if existing_lead:
            # Atualizar lead existente
            old_stage = existing_lead.stage.value
            old_score = existing_lead.score
            existing_lead.stage = lead_stage
            existing_lead.score = max(existing_lead.score, score)  # Manter o maior score
            existing_lead.next_action = f"Handoff solicitado: {reason}"
            if preferred_plan_id:
                existing_lead.preferred_plan_id = preferred_plan_id
            logger.info(
                f"✅ Updated existing lead {existing_lead.id} for conversation {conversation_id}: "
                f"stage {old_stage}→{lead_stage.value}, score {old_score}→{existing_lead.score}"
            )
        else:
            # Criar novo lead
            new_lead = Lead(
                conversation_id=conv_uuid,
                user_id=conversation.user_id,
                stage=lead_stage,
                score=score,
                preferred_plan_id=preferred_plan_id,
                next_action=f"Handoff solicitado: {reason}",
            )
            db.add(new_lead)
            logger.info(
                f"✅ Created new lead automatically for conversation {conversation_id}: "
                f"lead_id={new_lead.id}, stage={lead_stage.value}, score={score}, "
                f"funnel_stage={conversation.funnel_stage.value}, reason='{reason}'"
            )
        
        await db.commit()
        await db.refresh(conversation)
        
        logger.info(f"Handoff requested for conversation {conversation_id}: {reason}")
        
        return {
            "conversation_id": conversation_id,
            "status": "awaiting_human",
            "handoff_requested": True,
            "reason": reason,
            "message": "Conversa transferida para atendimento humano. Aguarde contato de nossa equipe.",
        }
    except Exception as e:
        logger.error(f"Error requesting handoff: {e}")
        await db.rollback()
        return {"error": str(e)}


async def check_handoff_status(
    conversation_id: str,
    db: AsyncSession,
) -> dict:
    """
    Verifica se conversa está aguardando transferência
    
    Args:
        conversation_id: Conversation UUID
        db: Database session
    
    Returns:
        Status da transferência
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
        
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_uuid)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return {"error": "Conversation not found"}
        
        return {
            "conversation_id": conversation_id,
            "status": conversation.status.value,
            "awaiting_human": conversation.status == ConversationStatus.AWAITING_HUMAN,
            "handoff_reason": conversation.handoff_reason,
            "handoff_requested_at": conversation.handoff_requested_at.isoformat() if conversation.handoff_requested_at else None,
        }
    except Exception as e:
        logger.error(f"Error checking handoff status: {e}")
        return {"error": str(e)}


def create_handoff_tools(db: AsyncSession):
    """Create handoff-related tools for LangChain agents"""
    
    async def _request_handoff(
        conversation_id: str,
        reason: str,
        summary: str,
    ) -> dict:
        return await request_handoff(conversation_id, reason, summary, db)
    
    async def _check_status(conversation_id: str) -> dict:
        return await check_handoff_status(conversation_id, db)
    
    return [
        StructuredTool.from_function(
            coroutine=_request_handoff,
            name="request_handoff",
            description=(
                "Solicita transferência da conversa para atendimento humano quando identificar oportunidade de venda qualificada. "
                "Use quando: cliente demonstra forte interesse, está pronto para fechar, ou tem dúvidas complexas que requerem atenção humana. "
                "IMPORTANTE: Após usar esta tool, a conversa será bloqueada e apenas humanos poderão continuar."
            ),
            args_schema=RequestHandoffInput,
        ),
    ]

