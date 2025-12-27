// WorkHub AI Sales Chat Frontend
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Estado da aplicação
let conversationId = null;
let userKey = 'test_user_frontend';
let userName = '';

// Configurar Marked.js
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,  // Quebras de linha viram <br>
        gfm: true,     // GitHub Flavored Markdown
    });
}

// Função para renderizar Markdown com sanitização
function renderMarkdown(markdownText) {
    if (!markdownText) return '';
    
    try {
        // Verificar se as bibliotecas estão disponíveis
        if (typeof marked === 'undefined') {
            console.warn('Marked.js não está disponível, retornando texto original');
            return markdownText;
        }
        
        // Converter markdown para HTML
        const html = marked.parse(markdownText);
        
        // Sanitizar HTML com DOMPurify (se disponível)
        if (typeof DOMPurify !== 'undefined') {
            return DOMPurify.sanitize(html, {
                ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'a', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
                ALLOWED_ATTR: ['href', 'title', 'target', 'rel'],
                ALLOW_DATA_ATTR: false
            });
        }
        
        // Se DOMPurify não estiver disponível, retornar HTML sem sanitização (não recomendado em produção)
        console.warn('DOMPurify não está disponível, HTML não será sanitizado');
        return html;
    } catch (error) {
        console.error('Erro ao renderizar markdown:', error);
        // Em caso de erro, retornar texto original
        return markdownText;
    }
}

// Elementos DOM
const messagesContainer = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const userKeyInput = document.getElementById('userKeyInput');
const userNameInput = document.getElementById('userNameInput');
const clearChatBtn = document.getElementById('clearChatBtn');
const typingIndicator = document.getElementById('typingIndicator');
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    // Carregar user_key do localStorage
    const savedUserKey = localStorage.getItem('workhub_user_key');
    if (savedUserKey) {
        userKey = savedUserKey;
        userKeyInput.value = savedUserKey;
    }
    
    // Carregar user_name do localStorage
    const savedUserName = localStorage.getItem('workhub_user_name');
    if (savedUserName) {
        userName = savedUserName;
        userNameInput.value = savedUserName;
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    userKeyInput.addEventListener('change', (e) => {
        userKey = e.target.value || 'test_user_frontend';
        localStorage.setItem('workhub_user_key', userKey);
        conversationId = null; // Reset conversation when user changes
        addSystemMessage('User key alterado. Nova conversa iniciada.');
    });
    
    userNameInput.addEventListener('change', (e) => {
        userName = e.target.value || '';
        localStorage.setItem('workhub_user_name', userName);
        conversationId = null; // Reset conversation when name changes
        if (userName) {
            addSystemMessage(`Nome atualizado: ${userName}. Nova conversa iniciada.`);
        }
    });
    
    clearChatBtn.addEventListener('click', clearChat);
    
    // Verificar status da API
    checkAPIStatus();
});

// Verificar status da API
async function checkAPIStatus() {
    try {
        const response = await fetch('http://localhost:8000/health');
        if (response.ok) {
            updateStatus('connected', 'Conectado');
        } else {
            updateStatus('error', 'Erro na API');
        }
    } catch (error) {
        updateStatus('error', 'Desconectado');
    }
}

// Atualizar indicador de status
function updateStatus(status, text) {
    statusText.textContent = text;
    statusIndicator.className = 'status-indicator';
    
    if (status === 'connected') {
        statusIndicator.style.color = '#4ade80';
    } else if (status === 'sending') {
        statusIndicator.style.color = '#fbbf24';
    } else {
        statusIndicator.style.color = '#ef4444';
    }
}

// Enviar mensagem
async function sendMessage() {
    const message = messageInput.value.trim();
    
    if (!message) {
        return;
    }
    
    if (!userKey || userKey === '') {
        addErrorMessage('Por favor, defina um User Key antes de enviar mensagens.');
        return;
    }
    
    // Desabilitar input
    messageInput.disabled = true;
    sendButton.disabled = true;
    updateStatus('sending', 'Enviando...');
    
    // Adicionar mensagem do usuário
    addMessage('user', message);
    messageInput.value = '';
    
    // Mostrar indicador de digitação
    showTypingIndicator();
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                user_key: userKey,
                user_name: userName || null,
                conversation_id: conversationId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Atualizar conversation_id
        if (data.conversation_id) {
            conversationId = data.conversation_id;
        }
        
        // Adicionar resposta do agente
        hideTypingIndicator();
        addMessage('assistant', data.response);
        
        // Atualizar status
        updateStatus('connected', 'Conectado');
        
    } catch (error) {
        hideTypingIndicator();
        console.error('Error sending message:', error);
        addErrorMessage(`Erro ao enviar mensagem: ${error.message}`);
        updateStatus('error', 'Erro');
    } finally {
        // Reabilitar input
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

// Adicionar mensagem ao chat
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Aplicar markdown apenas para mensagens do assistente
    if (role === 'assistant') {
        // Renderizar markdown e inserir como HTML
        const renderedHtml = renderMarkdown(content);
        contentDiv.innerHTML = renderedHtml;
    } else {
        // Para mensagens do usuário, manter texto simples
        // Se o conteúdo tiver múltiplas linhas, criar parágrafos
        const lines = content.split('\n').filter(line => line.trim());
        if (lines.length > 0) {
            lines.forEach(line => {
                const p = document.createElement('p');
                p.textContent = line;
                contentDiv.appendChild(p);
            });
        } else {
            // Se não houver linhas, adicionar conteúdo direto
            const p = document.createElement('p');
            p.textContent = content;
            contentDiv.appendChild(p);
        }
    }
    
    // Adicionar timestamp
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString('pt-BR', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    contentDiv.appendChild(timeDiv);
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    // Scroll para o final
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Adicionar mensagem de sistema
function addSystemMessage(content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const p = document.createElement('p');
    p.textContent = content;
    contentDiv.appendChild(p);
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Adicionar mensagem de erro
function addErrorMessage(content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message error';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const p = document.createElement('p');
    p.textContent = `❌ ${content}`;
    contentDiv.appendChild(p);
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Mostrar indicador de digitação
function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Esconder indicador de digitação
function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

// Limpar chat
function clearChat() {
    if (confirm('Tem certeza que deseja limpar o chat? Isso iniciará uma nova conversa.')) {
        messagesContainer.innerHTML = '';
        conversationId = null;
        addSystemMessage('Chat limpo. Nova conversa iniciada.');
    }
}

