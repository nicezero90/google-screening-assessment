/**
 * Returns & Warranty Insights Chat Application
 * GPT-style interface for AI agent interactions
 */

class ChatApp {
    constructor() {
        this.messageInput = null;
        this.chatMessages = null;
        this.sendBtn = null;
        this.welcomeMessage = null;
        this.loading = false;
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    init() {
        this.bindElements();
        this.bindEvents();
        this.setupAutoResize();
        this.loadConversationHistory();
        
        console.log('Chat application initialized');
    }
    
    bindElements() {
        this.messageInput = document.getElementById('messageInput');
        this.chatMessages = document.getElementById('chatMessages');
        this.sendBtn = document.getElementById('sendBtn');
        this.welcomeMessage = document.getElementById('welcomeMessage');
        this.charCount = document.getElementById('charCount');
        this.statsBtn = document.getElementById('statsBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.chatForm = document.getElementById('chatForm');
        this.loadingOverlay = document.getElementById('loading');
    }
    
    bindEvents() {
        // Form submission
        if (this.chatForm) {
            this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        }
        
        // Input events
        if (this.messageInput) {
            this.messageInput.addEventListener('input', () => this.handleInputChange());
            this.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        }
        
        // Button events
        if (this.statsBtn) {
            this.statsBtn.addEventListener('click', () => this.showStats());
        }
        
        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => this.clearConversation());
        }
        
        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleGlobalKeyDown(e));
    }
    
    setupAutoResize() {
        if (!this.messageInput) return;
        
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        });
    }
    
    handleInputChange() {
        if (!this.messageInput || !this.charCount) return;
        
        const length = this.messageInput.value.length;
        this.charCount.textContent = `${length}/1000`;
        
        // Update send button state
        if (this.sendBtn) {
            this.sendBtn.disabled = length === 0 || this.loading;
        }
    }
    
    handleKeyDown(e) {
        // Send on Ctrl/Cmd + Enter
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            this.sendMessage();
        }
        
        // Prevent sending on just Enter if shift is held
        if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }
    
    handleGlobalKeyDown(e) {
        // Focus input on any typing (if not already focused)
        if (!this.messageInput) return;
        
        if (e.target !== this.messageInput && 
            !e.ctrlKey && !e.metaKey && !e.altKey &&
            e.key.length === 1 && 
            !document.getElementById('statsModal')?.style.display !== 'none') {
            this.messageInput.focus();
        }
    }
    
    handleSubmit(e) {
        e.preventDefault();
        this.sendMessage();
    }
    
    async sendMessage() {
        if (!this.messageInput || this.loading) return;
        
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // Hide welcome message on first message
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'none';
        }
        
        // Add user message to chat
        this.addUserMessage(message);
        
        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.handleInputChange();
        
        // Show loading
        this.setLoading(true);
        
        try {
            const response = await this.sendToAPI(message);
            this.addAgentMessage(response);
        } catch (error) {
            console.error('Error sending message:', error);
            this.addErrorMessage('Sorry, I encountered an error processing your request. Please try again.');
        } finally {
            this.setLoading(false);
            this.messageInput.focus();
        }
    }
    
    async sendToAPI(message) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    addUserMessage(message) {
        const template = document.getElementById('userMessageTemplate');
        if (!template) return;
        
        const messageElement = template.content.cloneNode(true);
        const messageText = messageElement.querySelector('.message-text');
        const messageTime = messageElement.querySelector('.message-time');
        
        messageText.textContent = message;
        messageTime.textContent = this.formatTime(new Date());
        
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }
    
    addAgentMessage(response) {
        const template = document.getElementById('agentMessageTemplate');
        if (!template) return;
        
        const messageElement = template.content.cloneNode(true);
        const agentName = messageElement.querySelector('.agent-name');
        const intentBadge = messageElement.querySelector('.intent-badge');
        const messageText = messageElement.querySelector('.message-text');
        const messageActions = messageElement.querySelector('.message-actions');
        const messageTime = messageElement.querySelector('.message-time');
        
        // Set agent name
        agentName.textContent = response.agent || 'Assistant';
        
        // Set intent badge
        if (response.intent) {
            intentBadge.textContent = response.intent.replace('_', ' ');
        } else {
            intentBadge.style.display = 'none';
        }
        
        // Set message text with markdown-like formatting
        messageText.innerHTML = this.formatMessage(response.message || 'No response');
        
        // Add download links if present
        if (response.data && response.data.filename) {
            this.addDownloadLink(messageActions, response.data.filename);
        }
        
        // Set time
        messageTime.textContent = this.formatTime(new Date());
        
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }
    
    addErrorMessage(message) {
        const response = {
            success: false,
            message: message,
            agent: 'system',
            intent: 'error'
        };
        this.addAgentMessage(response);
    }
    
    addDownloadLink(container, filename) {
        const template = document.getElementById('downloadLinkTemplate');
        if (!template) return;
        
        const linkElement = template.content.cloneNode(true);
        const downloadBtn = linkElement.querySelector('.download-btn');
        const downloadText = linkElement.querySelector('.download-text');
        
        downloadBtn.href = `/download/${filename}`;
        downloadText.textContent = `Download ${filename}`;
        
        container.appendChild(linkElement);
    }
    
    formatMessage(text) {
        // Simple markdown-like formatting
        return text
            // Bold text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Bullet points
            .replace(/^• (.+)$/gm, '<span style="margin-left: 1rem;">• $1</span>')
            // Headers
            .replace(/^## (.+)$/gm, '<h3 style="margin: 1rem 0 0.5rem 0; color: var(--primary-color);">$1</h3>')
            .replace(/^### (.+)$/gm, '<h4 style="margin: 1rem 0 0.5rem 0; color: var(--text-primary);">$1</h4>')
            // Preserve line breaks
            .replace(/\n/g, '<br>');
    }
    
    formatTime(date) {
        return date.toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
    setLoading(loading) {
        this.loading = loading;
        
        if (this.sendBtn) {
            this.sendBtn.disabled = loading || !this.messageInput?.value.trim();
        }
        
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = loading ? 'flex' : 'none';
        }
    }
    
    scrollToBottom() {
        if (this.chatMessages) {
            setTimeout(() => {
                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            }, 100);
        }
    }
    
    async loadConversationHistory() {
        try {
            const response = await fetch('/api/history');
            if (!response.ok) return;
            
            const data = await response.json();
            if (data.history && data.history.length > 0) {
                // Hide welcome message if we have history
                if (this.welcomeMessage) {
                    this.welcomeMessage.style.display = 'none';
                }
                
                // Add historical messages
                data.history.forEach(item => {
                    this.addUserMessage(item.user_message);
                    this.addAgentMessage(item.agent_response);
                });
            }
        } catch (error) {
            console.error('Error loading conversation history:', error);
        }
    }
    
    async clearConversation() {
        if (!confirm('Are you sure you want to clear the conversation?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/clear');
            if (response.ok) {
                // Clear chat messages
                if (this.chatMessages) {
                    this.chatMessages.innerHTML = '';
                }
                
                // Show welcome message
                if (this.welcomeMessage) {
                    this.welcomeMessage.style.display = 'block';
                }
                
                console.log('Conversation cleared');
            }
        } catch (error) {
            console.error('Error clearing conversation:', error);
            alert('Failed to clear conversation. Please try again.');
        }
    }
    
    async showStats() {
        const modal = document.getElementById('statsModal');
        const content = document.getElementById('statsContent');
        
        if (!modal || !content) return;
        
        // Show modal
        modal.style.display = 'flex';
        content.innerHTML = '<div class="text-center">Loading statistics...</div>';
        
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) throw new Error('Failed to load stats');
            
            const stats = await response.json();
            content.innerHTML = this.renderStats(stats);
        } catch (error) {
            console.error('Error loading stats:', error);
            content.innerHTML = '<div class="text-center text-muted">Failed to load statistics</div>';
        }
    }
    
    renderStats(stats) {
        return `
            <div class="stats-grid">
                <div class="stats-section">
                    <h3>📊 Database Statistics</h3>
                    <div class="stats-item">
                        <span class="stats-label">Total Records:</span>
                        <span class="stats-value">${stats.database?.total_records || 0}</span>
                    </div>
                    <div class="stats-item">
                        <span class="stats-label">Date Range:</span>
                        <span class="stats-value">
                            ${stats.database?.date_range?.earliest || 'N/A'} - 
                            ${stats.database?.date_range?.latest?.split(' ')[0] || 'N/A'}
                        </span>
                    </div>
                </div>
                
                <div class="stats-section">
                    <h3>📈 Recent Analytics (30 days)</h3>
                    <div class="stats-item">
                        <span class="stats-label">Returns:</span>
                        <span class="stats-value">${stats.analytics?.total_returns_30d || 0}</span>
                    </div>
                    <div class="stats-item">
                        <span class="stats-label">Total Loss:</span>
                        <span class="stats-value">$${(stats.analytics?.total_loss_30d || 0).toLocaleString()}</span>
                    </div>
                </div>
                
                ${stats.analytics?.top_products?.length ? `
                <div class="stats-section">
                    <h3>🔝 Top Returned Products</h3>
                    ${stats.analytics.top_products.slice(0, 5).map(product => `
                        <div class="stats-item">
                            <span class="stats-label">${product.product}:</span>
                            <span class="stats-value">${product.count} returns ($${product.value.toLocaleString()})</span>
                        </div>
                    `).join('')}
                </div>
                ` : ''}
                
                <div class="stats-section">
                    <h3>💬 Session Info</h3>
                    <div class="stats-item">
                        <span class="stats-label">Active Sessions:</span>
                        <span class="stats-value">${stats.system?.active_sessions || 0}</span>
                    </div>
                    <div class="stats-item">
                        <span class="stats-label">Total Conversations:</span>
                        <span class="stats-value">${stats.system?.total_conversations || 0}</span>
                    </div>
                </div>
            </div>
            
            <style>
                .stats-grid {
                    display: grid;
                    gap: 1.5rem;
                }
                .stats-section {
                    background: var(--background-secondary);
                    padding: 1rem;
                    border-radius: var(--border-radius-md);
                    border: 1px solid var(--border-color);
                }
                .stats-section h3 {
                    margin: 0 0 1rem 0;
                    color: var(--primary-color);
                    font-size: 1.1rem;
                }
                .stats-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 0.5rem 0;
                    border-bottom: 1px solid var(--border-color);
                }
                .stats-item:last-child {
                    border-bottom: none;
                }
                .stats-label {
                    color: var(--text-secondary);
                    font-weight: 500;
                }
                .stats-value {
                    color: var(--text-primary);
                    font-weight: 600;
                }
            </style>
        `;
    }
}

// Global functions for modal control
function closeStatsModal() {
    const modal = document.getElementById('statsModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('statsModal');
    if (modal && e.target === modal) {
        closeStatsModal();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeStatsModal();
    }
});

// Initialize chat app and expose for global access
window.chatApp = new ChatApp();

// Expose global functions for backwards compatibility
function initializeChat() {
    // Already initialized in constructor
    console.log('Chat already initialized');
}

function loadConversationHistory() {
    if (window.chatApp) {
        window.chatApp.loadConversationHistory();
    }
}