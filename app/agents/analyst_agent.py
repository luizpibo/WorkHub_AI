"""Analyst Agent implementation"""
from typing import Dict, Any, Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.exceptions import OutputParserException
from openai import RateLimitError, APIError, APITimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import get_llm
from app.tools import create_analyst_tools
from app.models.user import User
from app.services.auth_service import require_admin
from app.services.prompt_service import PromptService
from app.utils.logger import logger


class AnalystAgent:
    """Analyst Agent for sales analytics"""
    
    def __init__(self, db: AsyncSession, user: Optional[User] = None):
        self.db = db
        self.user = user
        # Verify admin access before creating tools
        require_admin(user)
        self.llm = get_llm(temperature=0.3)  # Lower temperature for more factual analysis
        self.tools = create_analyst_tools(db, user)
        self.agent_executor = None
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """
        Create prompt template for analyst agent
        
        Returns:
            ChatPromptTemplate
        """
        prompt_service = PromptService()
        system_prompt = prompt_service.get_analyst_prompt()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        return prompt
    
    async def analyze_conversation(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Analyze a specific conversation
        
        Args:
            conversation_id: Conversation ID to analyze
        
        Returns:
            Analysis results
        """
        try:
            prompt = self._create_prompt()
            
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
            
            # Prepare analysis request
            analysis_request = f"""
Analise a conversa com ID {conversation_id}.

Forneça:
1. Resumo da conversa
2. Estágio atual do funil
3. Objeções identificadas
4. Próximas ações recomendadas
5. Probabilidade de conversão (alta/média/baixa)
6. Insights sobre o comportamento do lead

Retorne a análise em formato JSON estruturado.
"""
            
            # Invoke agent
            logger.info(f"Analyzing conversation {conversation_id}")
            result = await agent_executor.ainvoke({"input": analysis_request})
            
            logger.info(f"Analysis completed for conversation {conversation_id}")
            
            return {
                "conversation_id": conversation_id,
                "analysis": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        
        except OutputParserException as e:
            logger.error(f"Output parsing error in analyst agent: {e}")
            return {
                "conversation_id": conversation_id,
                "error": f"Erro ao processar análise: {str(e)}"
            }
        
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded in analyst agent: {e}")
            return {
                "conversation_id": conversation_id,
                "error": "Limite de requisições excedido. Tente novamente em alguns instantes."
            }
        
        except APITimeoutError as e:
            logger.error(f"API timeout in analyst agent: {e}")
            return {
                "conversation_id": conversation_id,
                "error": "Timeout ao processar análise. Tente novamente."
            }
        
        except APIError as e:
            logger.error(f"OpenAI API error in analyst agent: {e}")
            return {
                "conversation_id": conversation_id,
                "error": f"Erro na API OpenAI: {str(e)}"
            }
            
        except Exception as e:
            logger.error(f"Unexpected error analyzing conversation: {e}", exc_info=True)
            return {
                "conversation_id": conversation_id,
                "error": str(e)
            }
    
    async def get_funnel_analysis(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        Analyze funnel metrics
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Funnel analysis
        """
        try:
            prompt = self._create_prompt()
            
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
            )
            
            # Prepare analysis request
            date_filter = ""
            if start_date and end_date:
                date_filter = f" entre {start_date} e {end_date}"
            
            analysis_request = f"""
Analise as métricas do funil de vendas{date_filter}.

Forneça:
1. Número de leads em cada estágio
2. Taxas de conversão entre estágios
3. Gargalos identificados
4. Recomendações para melhorar conversão
5. Comparação de performance entre planos

Use as tools disponíveis para obter os dados necessários.
Retorne a análise em formato estruturado.
"""
            
            # Invoke agent
            logger.info("Analyzing funnel metrics")
            result = await agent_executor.ainvoke({"input": analysis_request})
            
            logger.info("Funnel analysis completed")
            
            return {
                "analysis": result.get("output", ""),
                "period": {"start": start_date, "end": end_date}
            }
        
        except OutputParserException as e:
            logger.error(f"Output parsing error in funnel analysis: {e}")
            return {"error": f"Erro ao processar análise do funil: {str(e)}"}
        
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded in funnel analysis: {e}")
            return {"error": "Limite de requisições excedido. Tente novamente em alguns instantes."}
        
        except APITimeoutError as e:
            logger.error(f"API timeout in funnel analysis: {e}")
            return {"error": "Timeout ao processar análise do funil. Tente novamente."}
        
        except APIError as e:
            logger.error(f"OpenAI API error in funnel analysis: {e}")
            return {"error": f"Erro na API OpenAI: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Unexpected error analyzing funnel: {e}", exc_info=True)
            return {"error": str(e)}



