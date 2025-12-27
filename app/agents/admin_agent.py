"""Admin Agent implementation"""
from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage
from openai import RateLimitError, APIError, APITimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import get_llm
from app.tools import create_admin_tools
from app.models.user import User
from app.services.prompt_service import prompt_service
from app.services.auth_service import require_admin
from app.utils.logger import logger


class AdminAgent:
    """Admin Agent for administrative tasks and analytics"""
    
    def __init__(self, db: AsyncSession, user: Optional[User] = None):
        self.db = db
        self.user = user
        # Verify admin access
        require_admin(user)
        self.llm = get_llm(temperature=0.3)  # Lower temperature for more factual responses
        self.tools = create_admin_tools(db, user)
        self.agent_executor = None
    
    def _create_prompt(
        self,
        conversation_id: str = None,
    ) -> ChatPromptTemplate:
        """
        Create prompt template for admin agent
        
        Args:
            conversation_id: Current conversation ID
        
        Returns:
            ChatPromptTemplate
        """
        # Get system prompt with injected variables
        system_prompt = prompt_service.get_admin_prompt(
            conversation_id=conversation_id,
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        return prompt
    
    async def invoke(
        self,
        message: str,
        conversation_id: str,
        user_id: str,
        user_name: str = None,
        conversation_summary: str = None,
        chat_history: Optional[List[BaseMessage]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke admin agent with a message
        
        Args:
            message: User message
            conversation_id: Conversation ID
            user_id: User ID
            user_name: User's name
            conversation_summary: Conversation summary
            chat_history: Previous messages
        
        Returns:
            Agent response
        """
        try:
            # Create prompt with current context
            prompt = self._create_prompt(
                conversation_id=conversation_id,
            )
            
            # Create agent
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt,
            )
            
            # Create executor with optimized configuration
            from app.core.config import settings
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=settings.APP_ENV == "development",  # Verbose apenas em desenvolvimento
                max_iterations=15,  # Aumentar limite de iterações
                max_execution_time=120,  # Timeout de 2 minutos
                early_stopping_method="generate",  # Parar graciosamente
                handle_parsing_errors=True,  # Tratar erros de parsing automaticamente
                return_intermediate_steps=True,
            )
            
            # Prepare input
            agent_input = {
                "input": message,
                "chat_history": chat_history or [],
            }
            
            # Invoke agent
            logger.info(f"Invoking admin agent for conversation {conversation_id}")
            result = await agent_executor.ainvoke(agent_input)
            
            logger.info(f"Admin agent response generated for conversation {conversation_id}")
            
            return {
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        
        except OutputParserException as e:
            logger.error(f"Output parsing error in admin agent: {e}")
            return {
                "output": "Desculpe, tive dificuldade em processar a resposta. Pode reformular sua pergunta?",
                "error": f"OutputParserException: {str(e)}"
            }
        
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded in admin agent: {e}")
            return {
                "output": "Estamos com muitas requisições no momento. Por favor, aguarde alguns segundos e tente novamente.",
                "error": f"RateLimitError: {str(e)}"
            }
        
        except APITimeoutError as e:
            logger.error(f"API timeout in admin agent: {e}")
            return {
                "output": "A requisição demorou muito para processar. Por favor, tente novamente.",
                "error": f"APITimeoutError: {str(e)}"
            }
        
        except APIError as e:
            logger.error(f"API error in admin agent: {e}")
            return {
                "output": "Ocorreu um erro temporário com nosso serviço de IA. Por favor, tente novamente em alguns instantes.",
                "error": f"APIError: {str(e)}"
            }
        
        except PermissionError as e:
            logger.error(f"Permission error in admin agent: {e}")
            return {
                "output": "Acesso negado. Você precisa ter privilégios de administrador para usar este agente.",
                "error": str(e)
            }
            
        except Exception as e:
            logger.error(f"Unexpected error invoking admin agent: {e}", exc_info=True)
            return {
                "output": "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
                "error": str(e)
            }


def create_admin_agent(db: AsyncSession, user: Optional[User] = None) -> AdminAgent:
    """
    Factory function to create admin agent
    
    Args:
        db: Database session
        user: User making the request (must be admin)
    
    Returns:
        AdminAgent instance
    
    Raises:
        PermissionError: If user is not admin
    """
    return AdminAgent(db, user)

