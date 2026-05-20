const API_BASE = 'http://localhost:8000';
const state = {
    accessToken: localStorage.getItem('accessToken'),
    refreshToken: localStorage.getItem('refreshToken'),
    currentChatId: null,
    chats: [],
    isStreaming: false
};

async function apiRequest(endpoint, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (state.accessToken) {
        headers['Authorization'] = `Bearer ${state.accessToken}`;
    }
    
    let response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    
    if (response.status === 401 && state.refreshToken) {
        const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: state.refreshToken })
        });
        
        if (refreshResponse.ok) {
            const tokens = await refreshResponse.json();
            state.accessToken = tokens.access_token;
            state.refreshToken = tokens.refresh_token;
            localStorage.setItem('accessToken', tokens.access_token);
            localStorage.setItem('refreshToken', tokens.refresh_token);
            headers['Authorization'] = `Bearer ${state.accessToken}`;
            response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        } else {
            logout();
        }
    }
    
    if (!response.ok && response.status !== 401) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || 'Request failed');
    }
    
    return response;
}



// Add this function for dev testing
async function devLogin() {
    try {
        const response = await fetch(`${API_BASE}/api/auth/dev/login?username=testuser&user_id=1`, {
            method: 'POST'
        });
        const tokens = await response.json();
        
        localStorage.setItem('accessToken', tokens.access_token);
        localStorage.setItem('refreshToken', tokens.refresh_token);
        state.accessToken = tokens.access_token;
        state.refreshToken = tokens.refresh_token;
        
        document.getElementById('auth-screen').classList.add('hidden');
        document.getElementById('chat-screen').classList.remove('hidden');
        loadChats();
    } catch (error) {
        console.error('Dev login failed:', error);
    }
}

async function loadChats() {
    try {
        const response = await apiRequest('/api/chats');
        state.chats = await response.json();
        renderChatList();
    } catch (error) {
        console.error('Failed to load chats:', error);
    }
}

function renderChatList() {
    const chatList = document.getElementById('chat-list');
    chatList.innerHTML = state.chats.map(chat => `
        <div class="chat-item ${chat.id === state.currentChatId ? 'active' : ''}" data-id="${chat.id}">
            <span class="chat-item-title">${chat.title}</span>
            <button class="chat-item-delete" data-id="${chat.id}">
                <i class="ri-delete-bin-line"></i>
            </button>
        </div>
    `).join('');
    
    document.querySelectorAll('.chat-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.chat-item-delete')) {
                selectChat(parseInt(item.dataset.id));
            }
        });
    });
    
    document.querySelectorAll('.chat-item-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteChat(parseInt(btn.dataset.id));
        });
    });
}

async function selectChat(chatId) {
    state.currentChatId = chatId;
    renderChatList();
    await loadMessages(chatId);
}

async function loadMessages(chatId) {
    const container = document.getElementById('messages-container');
    container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Loading messages...</p>';
    
    try {
        const response = await apiRequest(`/api/chats/${chatId}/messages`);
        const messages = await response.json();
        container.innerHTML = messages.map(msg => `
            <div class="message ${msg.role}">
                <div class="message-role">${msg.role}</div>
                <div class="message-content">${escapeHtml(msg.content)}</div>
            </div>
        `).join('');
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        container.innerHTML = `<p style="color: var(--error);">Failed to load messages</p>`;
    }
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    if (!message || !state.currentChatId || state.isStreaming) return;
    
    input.value = '';
    state.isStreaming = true;
    document.getElementById('send-btn').disabled = true;
    
    const container = document.getElementById('messages-container');
    container.innerHTML += `
        <div class="message user">
            <div class="message-role">You</div>
            <div class="message-content">${escapeHtml(message)}</div>
        </div>
    `;
    
    const assistantMsg = document.createElement('div');
    assistantMsg.className = 'message assistant';
    assistantMsg.innerHTML = `
        <div class="message-role">Assistant</div>
        <div class="message-content"><span class="typing-indicator"></span></div>
    `;
    container.appendChild(assistantMsg);
    container.scrollTop = container.scrollHeight;
    
    try {
        const response = await apiRequest(`/api/chats/${state.currentChatId}/chat/stream`, {
            method: 'POST',
            body: JSON.stringify({ message })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        let buffer = '';
        
        assistantMsg.querySelector('.message-content').innerHTML = '';
        const contentDiv = assistantMsg.querySelector('.message-content');
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.token) {
                            fullResponse += data.token;
                            contentDiv.textContent = fullResponse;
                            container.scrollTop = container.scrollHeight;
                        }
                        if (data.done) {
                            state.isStreaming = false;
                            document.getElementById('send-btn').disabled = false;
                        }
                    } catch (e) { }
                }
            }
        }
        
        if (fullResponse.trim()) {
            await apiRequest(`/api/chats/${state.currentChatId}/messages`, {
                method: 'POST',
                body: JSON.stringify({ content: fullResponse })
            });
        }
    } catch (error) {
        contentDiv.innerHTML = `<span style="color: var(--error);">Error: ${error.message}</span>`;
        state.isStreaming = false;
        document.getElementById('send-btn').disabled = false;
    }
}

async function createNewChat() {
    try {
        const response = await apiRequest('/api/chats', {
            method: 'POST',
            body: JSON.stringify({ title: `Chat ${state.chats.length + 1}` })
        });
        const chat = await response.json();
        await loadChats();
        await selectChat(chat.id);
    } catch (error) {
        alert('Failed to create chat');
    }
}

async function deleteChat(chatId) {
    if (!confirm('Delete this chat?')) return;
    try {
        await apiRequest(`/api/chats/${chatId}`, { method: 'DELETE' });
        if (state.currentChatId === chatId) {
            state.currentChatId = null;
            document.getElementById('messages-container').innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Select or create a chat</p>';
        }
        await loadChats();
    } catch (error) {
        alert('Failed to delete chat');
    }
}

function logout() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    state.accessToken = null;
    state.refreshToken = null;
    state.currentChatId = null;
    state.chats = [];
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('chat-screen').classList.add('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function init() {
    const urlParams = new URLSearchParams(window.location.search);
    const accessToken = urlParams.get('access_token');
    const refreshToken = urlParams.get('refresh_token');
    
    if (accessToken && refreshToken) {
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
        state.accessToken = accessToken;
        state.refreshToken = refreshToken;
        window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    if (state.accessToken) {
        document.getElementById('auth-screen').classList.add('hidden');
        document.getElementById('chat-screen').classList.remove('hidden');
        loadChats();
    }
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`${btn.dataset.tab}-form`).classList.add('active');
        });
    });
    
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const response = await fetch(`${API_BASE}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: document.getElementById('login-username').value,
                    password: document.getElementById('login-password').value
                })
            });
            const data = await response.json();
            if (response.ok) {
                localStorage.setItem('accessToken', data.access_token);
                localStorage.setItem('refreshToken', data.refresh_token);
                state.accessToken = data.access_token;
                state.refreshToken = data.refresh_token;
                document.getElementById('auth-screen').classList.add('hidden');
                document.getElementById('chat-screen').classList.remove('hidden');
                loadChats();
            } else {
                alert(data.detail || 'Login failed');
            }
        } catch (error) {
            alert('Connection error');
        }
    });
    
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const response = await fetch(`${API_BASE}/api/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: document.getElementById('reg-username').value,
                    email: document.getElementById('reg-email').value,
                    password: document.getElementById('reg-password').value
                })
            });
            const data = await response.json();
            if (response.ok) {
                alert('Registration successful! Please login.');
                document.querySelector('[data-tab="login"]').click();
            } else {
                alert(data.detail || 'Registration failed');
            }
        } catch (error) {
            alert('Connection error');
        }
    });
    
    document.getElementById('github-login-btn').addEventListener('click', () => {
        window.location.href = `${API_BASE}/api/auth/github`;
    });
    
    document.getElementById('new-chat-btn').addEventListener('click', createNewChat);
    document.getElementById('logout-btn').addEventListener('click', logout);
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    document.getElementById('message-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

document.addEventListener('DOMContentLoaded', init);