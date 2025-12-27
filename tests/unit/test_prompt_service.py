"""Unit tests for prompt service"""
import pytest
from pathlib import Path
from app.services.prompt_service import PromptService


@pytest.fixture
def prompt_service():
    """Create PromptService instance"""
    return PromptService()


@pytest.mark.asyncio
async def test_load_template_success(prompt_service):
    """Test load_template with existing template"""
    template = prompt_service.load_template("sales_agent.txt")
    
    assert isinstance(template, str)
    assert len(template) > 0
    assert "Consultor de Vendas" in template or "vendas" in template.lower()


@pytest.mark.asyncio
async def test_load_template_not_found(prompt_service):
    """Test load_template with non-existent template"""
    with pytest.raises(FileNotFoundError):
        prompt_service.load_template("nonexistent_template.txt")


@pytest.mark.asyncio
async def test_load_knowledge_success(prompt_service):
    """Test load_knowledge with existing knowledge file"""
    knowledge = prompt_service.load_knowledge("workhub_product.txt")
    
    assert isinstance(knowledge, str)
    assert len(knowledge) > 0
    assert "WorkHub" in knowledge or "coworking" in knowledge.lower()


@pytest.mark.asyncio
async def test_load_knowledge_not_found(prompt_service):
    """Test load_knowledge with non-existent knowledge file"""
    with pytest.raises(FileNotFoundError):
        prompt_service.load_knowledge("nonexistent_knowledge.txt")


@pytest.mark.asyncio
async def test_inject_variables_simple(prompt_service):
    """Test inject_variables with simple variables"""
    template = "Hello {name}, welcome to {place}!"
    result = prompt_service.inject_variables(template, name="John", place="WorkHub")
    
    assert result == "Hello John, welcome to WorkHub!"


@pytest.mark.asyncio
async def test_inject_variables_with_none(prompt_service):
    """Test inject_variables with None values"""
    template = "Name: {name}, Email: {email}"
    result = prompt_service.inject_variables(template, name="John", email=None)
    
    assert "Name: John" in result
    assert "Email: Não informado" in result


@pytest.mark.asyncio
async def test_inject_variables_with_list(prompt_service):
    """Test inject_variables with list values"""
    template = "Features:\n{features}"
    features = ["Wi-Fi", "Café", "Sala de reunião"]
    result = prompt_service.inject_variables(template, features=features)
    
    assert "- Wi-Fi" in result
    assert "- Café" in result
    assert "- Sala de reunião" in result


@pytest.mark.asyncio
async def test_inject_variables_missing_variable(prompt_service):
    """Test inject_variables with missing variable raises KeyError"""
    template = "Hello {name}, welcome to {place}!"
    
    with pytest.raises(KeyError):
        prompt_service.inject_variables(template, name="John")


@pytest.mark.asyncio
async def test_get_sales_prompt_complete(prompt_service):
    """Test get_sales_prompt generates complete prompt"""
    prompt = prompt_service.get_sales_prompt(
        user_name="João",
        work_type="freelancer",
        conversation_summary="Primeira conversa",
        funnel_stage="interest",
        available_plans="Day Pass, Flex",
        conversation_id="123e4567-e89b-12d3-a456-426614174000"
    )
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "João" in prompt or "Cliente" in prompt
    assert "freelancer" in prompt.lower() or "Não informado" in prompt


@pytest.mark.asyncio
async def test_get_sales_prompt_with_defaults(prompt_service):
    """Test get_sales_prompt with default values"""
    prompt = prompt_service.get_sales_prompt()
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "Cliente" in prompt  # Default user_name


@pytest.mark.asyncio
async def test_get_analyst_prompt(prompt_service):
    """Test get_analyst_prompt loads template"""
    prompt = prompt_service.get_analyst_prompt()
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.asyncio
async def test_get_admin_prompt(prompt_service):
    """Test get_admin_prompt with conversation_id"""
    conversation_id = "123e4567-e89b-12d3-a456-426614174000"
    prompt = prompt_service.get_admin_prompt(conversation_id=conversation_id)
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert conversation_id in prompt


@pytest.mark.asyncio
async def test_get_admin_prompt_with_default(prompt_service):
    """Test get_admin_prompt with default conversation_id"""
    prompt = prompt_service.get_admin_prompt()
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "N/A" in prompt  # Default conversation_id

