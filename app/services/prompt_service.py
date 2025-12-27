"""Prompt service for loading and injecting templates"""
from pathlib import Path
from typing import Dict, Any
from app.utils.logger import logger


class PromptService:
    """Service for managing prompt templates"""
    
    def __init__(self):
        self.prompts_dir = Path("prompts")
        self.knowledge_dir = self.prompts_dir / "knowledge"
    
    def load_template(self, template_name: str) -> str:
        """
        Load a prompt template from file
        
        Args:
            template_name: Name of the template file (e.g., 'sales_agent.txt')
        
        Returns:
            Template content as string
        """
        template_path = self.prompts_dir / template_name
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Loaded template: {template_name}")
            return content
        except FileNotFoundError:
            logger.error(f"Template not found: {template_name}")
            raise
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            raise
    
    def load_knowledge(self, knowledge_file: str) -> str:
        """
        Load knowledge base from file
        
        Args:
            knowledge_file: Name of the knowledge file (e.g., 'workhub_product.txt')
        
        Returns:
            Knowledge content as string
        """
        knowledge_path = self.knowledge_dir / knowledge_file
        
        try:
            with open(knowledge_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Loaded knowledge: {knowledge_file}")
            return content
        except FileNotFoundError:
            logger.error(f"Knowledge file not found: {knowledge_file}")
            raise
        except Exception as e:
            logger.error(f"Error loading knowledge {knowledge_file}: {e}")
            raise
    
    def inject_variables(self, template: str, **kwargs: Any) -> str:
        """
        Inject variables into template
        
        Args:
            template: Template string with {variable} placeholders
            **kwargs: Variables to inject
        
        Returns:
            Template with variables replaced
        """
        try:
            # Replace None values with empty string or default
            safe_kwargs = {}
            for key, value in kwargs.items():
                if value is None:
                    safe_kwargs[key] = "Não informado"
                elif isinstance(value, list):
                    safe_kwargs[key] = "\n".join(f"- {item}" for item in value)
                else:
                    safe_kwargs[key] = str(value)
            
            result = template.format(**safe_kwargs)
            logger.debug(f"Injected variables into template")
            return result
        except KeyError as e:
            logger.error(f"Missing variable in template: {e}")
            raise
        except Exception as e:
            logger.error(f"Error injecting variables: {e}")
            raise
    
    def get_sales_prompt(
        self,
        user_name: str = None,
        work_type: str = None,
        conversation_summary: str = None,
        funnel_stage: str = "awareness",
        available_plans: str = None,
        conversation_id: str = None,
    ) -> str:
        """
        Get complete sales agent prompt with injected variables
        
        Args:
            user_name: User's name
            work_type: Type of work (freelancer, startup, etc.)
            conversation_summary: Summary of conversation so far
            funnel_stage: Current funnel stage
            available_plans: Formatted list of available plans
        
        Returns:
            Complete prompt ready for LLM
        """
        template = self.load_template("sales_agent.txt")
        product_knowledge = self.load_knowledge("workhub_product.txt")
        
        return self.inject_variables(
            template,
            product_knowledge=product_knowledge,
            user_name=user_name or "Cliente",
            work_type=work_type or "Não informado",
            conversation_summary=conversation_summary or "Primeira interação",
            funnel_stage=funnel_stage,
            available_plans=available_plans or "Carregando planos...",
            conversation_id=conversation_id or "N/A",
        )
    
    def get_analyst_prompt(self) -> str:
        """
        Get analyst agent prompt
        
        Returns:
            Analyst prompt ready for LLM
        """
        return self.load_template("analyst_agent.txt")
    
    def get_admin_prompt(
        self,
        conversation_id: str = None,
    ) -> str:
        """
        Get admin agent prompt with injected variables
        
        Args:
            conversation_id: Current conversation ID
        
        Returns:
            Complete admin prompt ready for LLM
        """
        template = self.load_template("admin_agent.txt")
        
        return self.inject_variables(
            template,
            conversation_id=conversation_id or "N/A",
        )


# Singleton instance
prompt_service = PromptService()

