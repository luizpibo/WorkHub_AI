"""Chat service for orchestrating sales conversations"""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.messages import HumanMessage, AIMessage

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.agents.sales_agent import create_sales_agent
from app.agents.admin_agent import create_admin_agent
from app.services.auth_service import is_admin_user
from app.utils.logger import logger


class ChatService:
    """Service for managing chat conversations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Don't create agents immediately - create them based on user type
        self._sales_agent = None
        self._admin_agent = None
    
    def _get_agent(self, user: User):
        """
        Get the appropriate agent based on user type
        
        Args:
            user: User object
        
        Returns:
            AdminAgent if user is admin, SalesAgent otherwise
        """
        is_admin = is_admin_user(user)
        user_name_display = user.name if user.name else "Sem nome"
        
        logger.info(f"Selecting agent for user: {user.user_key} (name: '{user_name_display}')")
        logger.info(f"Admin check result: {is_admin}")
        
        if is_admin:
            logger.info("Using AdminAgent for admin user")
            if self._admin_agent is None:
                self._admin_agent = create_admin_agent(self.db, user)
            return self._admin_agent
        else:
            logger.info("Using SalesAgent for regular user")
            if self._sales_agent is None:
                self._sales_agent = create_sales_agent(self.db)
            return self._sales_agent
    
    async def get_or_create_user(self, user_key: str, user_name: Optional[str] = None) -> User:
        """
        Get existing user or create new one
        Also tries to find user by name if user_key not found and name is provided
        """
        # First try by user_key
        result = await self.db.execute(
            select(User).where(User.user_key == user_key)
        )
        user = result.scalar_one_or_none()
        
        # If not found and name provided, try to find by name
        if not user and user_name:
            logger.info(f"User not found by key {user_key}, searching by name: {user_name}")
            result = await self.db.execute(
                select(User).where(User.name.ilike(f"%{user_name}%"))
            )
            users_by_name = result.scalars().all()
            
            # If found exactly one user with matching name, use it
            if len(users_by_name) == 1:
                user = users_by_name[0]
                logger.info(f"Found existing user by name: {user.user_key} ({user.name})")
            elif len(users_by_name) > 1:
                # Multiple users with similar name - use the most recent one
                user = max(users_by_name, key=lambda u: u.created_at)
                logger.info(f"Multiple users found by name, using most recent: {user.user_key} ({user.name})")
        
        # If still not found, create new user
        if not user:
            user = User(user_key=user_key, name=user_name)
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"Created new user: {user_key} (name: {user_name})")
        else:
            # Always update name if provided (even if same, to ensure sync)
            if user_name is not None:
                old_name = user.name
                user.name = user_name
                await self.db.commit()
                await self.db.refresh(user)
                if old_name != user_name:
                    logger.info(f"Updated user name: {user_key} - '{old_name}' -> '{user_name}'")
                else:
                    logger.debug(f"User name confirmed: {user_key} - '{user_name}'")
        
        # Always refresh to ensure we have latest data
        await self.db.refresh(user)
        
        return user
    
    async def get_or_create_conversation(
        self,
        user_id: UUID,
        conversation_id: Optional[UUID] = None
    ) -> Conversation:
        """Get existing conversation or create new one"""
        if conversation_id:
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            
            if conversation:
                return conversation
        
        # Create new conversation
        conversation = Conversation(user_id=user_id)
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        logger.info(f"Created new conversation: {conversation.id}")
        
        return conversation
    
    async def get_chat_history(self, conversation_id: UUID, limit: int = 10):
        """Get recent chat history in LangChain format"""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))
        
        # Converter para formato LangChain
        langchain_messages = []
        for msg in messages:
            if msg.role.value == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role.value == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            # Ignorar mensagens de sistema no histórico
        
        return langchain_messages
    
    def _serialize_intermediate_steps(self, intermediate_steps):
        """Serialize intermediate_steps to JSON-serializable format"""
        if not intermediate_steps:
            return None
        
        import json
        
        serialized = []
        for step in intermediate_steps:
            try:
                if isinstance(step, tuple) and len(step) >= 2:
                    action, observation = step[0], step[1]
                    
                    # Serialize action
                    action_dict = {}
                    if hasattr(action, 'tool'):
                        action_dict['tool'] = str(action.tool) if action.tool else None
                    if hasattr(action, 'tool_input'):
                        # Try to serialize tool_input
                        try:
                            json.dumps(action.tool_input)
                            action_dict['tool_input'] = action.tool_input
                        except (TypeError, ValueError):
                            action_dict['tool_input'] = str(action.tool_input)
                    if hasattr(action, 'log'):
                        action_dict['log'] = str(action.log) if action.log else None
                    
                    # Serialize observation
                    observation_dict = {}
                    if isinstance(observation, dict):
                        # Try to serialize dict
                        try:
                            json.dumps(observation)
                            observation_dict = observation
                        except (TypeError, ValueError):
                            observation_dict = {'raw': str(observation)}
                    elif isinstance(observation, str):
                        observation_dict = {'value': observation}
                    else:
                        # For complex objects, convert to string
                        observation_dict = {
                            'type': type(observation).__name__,
                            'value': str(observation)
                        }
                    
                    serialized.append({
                        'action': action_dict,
                        'observation': observation_dict
                    })
                else:
                    # Fallback: convert to string representation
                    try:
                        json.dumps(step)
                        serialized.append({'step': step})
                    except (TypeError, ValueError):
                        serialized.append({'step': str(step)})
            except Exception as e:
                # If anything fails, just convert to string
                logger.warning(f"Error serializing step: {e}")
                serialized.append({'step': str(step), 'error': str(e)})
        
        return serialized if serialized else None
    
    async def save_message(
        self,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        tool_calls: Optional[dict] = None
    ) -> Message:
        """Save a message to database"""
        # Serialize tool_calls if it contains non-serializable objects
        serialized_tool_calls = None
        if tool_calls:
            import json
            # Always serialize intermediate_steps (they contain LangChain objects)
            if isinstance(tool_calls, list):
                serialized_tool_calls = self._serialize_intermediate_steps(tool_calls)
            else:
                # Try to serialize as-is
                try:
                    json.dumps(tool_calls)  # Test if serializable
                    serialized_tool_calls = tool_calls
                except (TypeError, ValueError):
                    # If not serializable, try to convert
                    if isinstance(tool_calls, dict):
                        # Try to serialize each value
                        serialized_tool_calls = {}
                        for k, v in tool_calls.items():
                            try:
                                json.dumps(v)
                                serialized_tool_calls[k] = v
                            except (TypeError, ValueError):
                                serialized_tool_calls[k] = str(v)
                    else:
                        serialized_tool_calls = str(tool_calls)
        
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=serialized_tool_calls,
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        
        return message
    
    async def process_message(
        self,
        message: str,
        user_key: str,
        conversation_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> dict:
        """
        Process a chat message through the sales agent
        
        Args:
            message: User message
            user_key: User identification key
            conversation_id: Optional existing conversation ID
        
        Returns:
            Response with agent message and metadata
        """
        try:
            # Get or create user (with name-based linking)
            user = await self.get_or_create_user(user_key, user_name)
            
            # Log user info for debugging
            logger.info(f"Processing message for user: {user.user_key}, name: '{user.name}', is_admin: {is_admin_user(user)}")
            
            # Get or create conversation
            conv_uuid = UUID(conversation_id) if conversation_id else None
            conversation = await self.get_or_create_conversation(user.id, conv_uuid)
            
            # VERIFICAR SE CONVERSA ESTÁ AGUARDANDO ATENDIMENTO HUMANO
            if conversation.status.value == "awaiting_human":
                logger.warning(f"Conversation {conversation.id} is awaiting human agent")
                
                # Salvar mensagem do usuário mesmo bloqueada
                await self.save_message(
                    conversation.id,
                    MessageRole.USER,
                    message
                )
                
                return {
                    "response": (
                        "🔒 Esta conversa foi transferida para atendimento humano.\n\n"
                        f"Motivo: {conversation.handoff_reason}\n\n"
                        "Um membro da nossa equipe entrará em contato em breve. "
                        "Sua mensagem foi registrada e será visualizada pelo atendente."
                    ),
                    "conversation_id": conversation.id,  # UUID, não string
                    "user_id": user.id,  # UUID, não string
                    "funnel_stage": conversation.funnel_stage.value,
                    "status": "awaiting_human",
                    "blocked": True,
                    "handoff_reason": conversation.handoff_reason,
                }
            
            # Save user message
            await self.save_message(
                conversation.id,
                MessageRole.USER,
                message
            )
            
            # Get chat history (excluir a mensagem atual que acabamos de salvar)
            chat_history = await self.get_chat_history(conversation.id, limit=20)
            
            # Filtrar a última mensagem do usuário (que acabamos de salvar)
            # para não duplicar no histórico
            if chat_history and len(chat_history) > 0:
                # Remover a última mensagem se for do usuário (já está sendo enviada como input)
                last_msg = chat_history[-1]
                if hasattr(last_msg, 'content') and last_msg.content == message:
                    chat_history = chat_history[:-1]
            
            # Armazenar IDs antes de chamar o agente (evita erro MissingGreenlet)
            conversation_id_uuid = conversation.id
            user_id_uuid = user.id
            funnel_stage_value = conversation.funnel_stage.value
            conversation_summary_value = conversation.context_summary
            
            # Get appropriate agent based on user type (verification happens inside _get_agent)
            # Re-verify admin status after user update to ensure we have latest data
            await self.db.refresh(user)
            is_admin = is_admin_user(user)
            logger.info(f"Final admin verification: user={user.user_key}, name='{user.name}', is_admin={is_admin}")
            
            agent = self._get_agent(user)
            agent_type_name = "AdminAgent" if is_admin else "SalesAgent"
            logger.info(f"Selected {agent_type_name} for conversation {conversation_id_uuid}")
            
            if is_admin:
                # Invoke admin agent (simpler signature)
                agent_response = await agent.invoke(
                    message=message,
                    conversation_id=str(conversation_id_uuid),
                    user_id=str(user_id_uuid),
                    user_name=user.name,
                    conversation_summary=conversation_summary_value,
                    chat_history=chat_history if chat_history else None,
                )
            else:
                # Invoke sales agent (full signature)
                agent_response = await agent.invoke(
                    message=message,
                    conversation_id=str(conversation_id_uuid),
                    user_id=str(user_id_uuid),
                    user_name=user.name,
                    work_type=user.work_type.value if user.work_type else None,
                    conversation_summary=conversation_summary_value,
                    funnel_stage=funnel_stage_value,
                    chat_history=chat_history if chat_history else None,
                )
            
            # Save agent response
            # Serialize intermediate_steps before saving
            intermediate_steps = agent_response.get("intermediate_steps")
            await self.save_message(
                conversation_id_uuid,  # Usar valor armazenado
                MessageRole.ASSISTANT,
                agent_response["output"],
                tool_calls=intermediate_steps  # Will be serialized in save_message
            )
            
            # Buscar conversation atualizada para obter status atualizado
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id_uuid)
            )
            updated_conversation = result.scalar_one_or_none()
            
            return {
                "response": agent_response["output"],
                "conversation_id": conversation_id_uuid,  # Usar valor armazenado
                "user_id": user_id_uuid,  # Usar valor armazenado
                "funnel_stage": updated_conversation.funnel_stage.value if updated_conversation else funnel_stage_value,
                "status": updated_conversation.status.value if updated_conversation else "active",
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise


async def create_chat_service(db: AsyncSession) -> ChatService:
    """Factory function to create chat service"""
    return ChatService(db)

