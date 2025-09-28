from rating_popup import generate_rating_popup

def generate_widget_js(company_name: str, company_display_name: str, greeting: str, api_key: str, primary_color: str) -> str:
    """
    Δημιουργεί τον JavaScript/CSS κώδικα για το chat widget
    Ταιριάζει με το design του web app chatbot
    """
    # Καθαρισμός του company_name για έγκυρα CSS class names
    clean_name = company_name.replace(' ', '_').replace('-', '_').replace('.', '_')
    rating = generate_rating_popup(clean_name, primary_color, api_key)
    
    return f"""
(function() {{
    // Δημιουργία chat widget container
    const widgetContainer = document.createElement('div');
    widgetContainer.id = 'chatbot-widget-{clean_name}';
    widgetContainer.innerHTML = `
        <!-- Chat Button -->
        <div id="chat-button-{clean_name}" class="chat-button-{clean_name}">
            💬
        </div>
        
        <!-- Chat Popup -->
        <div id="chat-popup-{clean_name}" class="chat-popup-{clean_name}" style="display: none;">
            <div class="chat-header-{clean_name}">
                <div class="header-info-{clean_name}">
                    <div class="bot-avatar-header-{clean_name}">
                        <svg class="chip-icon-{clean_name}" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                        </svg>
                    </div>
                    <span class="bot-name-{clean_name}">{company_display_name}</span>
                </div>
                <div class="status-info-{clean_name}">
                    <div class="status-dot-{clean_name}"></div>
                    <span class="status-text-{clean_name}">Συνδεδεμένος</span>
                </div>
                <button id="close-chat-{clean_name}" class="close-btn-{clean_name}">×</button>
            </div>
            <div id="chat-messages-{clean_name}" class="chat-messages-{clean_name}">
                <div class="message-wrapper-{clean_name} bot-wrapper-{clean_name}">
                    <div class="bot-avatar-{clean_name}">
                        <svg class="chip-icon-{clean_name}" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                        </svg>
                    </div>
                    <div class="bot-message-{clean_name}">{greeting}</div>
                </div>
            </div>
            <div class="chat-input-container-{clean_name}">
                <input type="text" id="chat-input-{clean_name}" placeholder="Γράψτε το μήνυμά σας..." />
                <button id="send-btn-{clean_name}" class="send-btn-{clean_name}">
                    <svg class="send-icon-{clean_name}" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z"/>
                    </svg>
                </button>
            </div>
        </div>
    `;
    
    // Προσθήκη στο DOM
    document.body.appendChild(widgetContainer);
    
    // CSS Styles που ταιριάζουν με το screenshot
    const styles = `
        /* Chat Button */
        .chat-button-{clean_name} {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 60px;
            height: 60px;
            background: {primary_color};
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 24px;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
            z-index: 1000;
            transition: all 0.3s ease;
            border: none;
        }}

        .chat-button-{clean_name}:hover {{
            transform: scale(1.1);
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.5);
        }}

        /* Chat Popup */
        .chat-popup-{clean_name} {{
            position: fixed;
            bottom: 90px;
            right: 20px;
            width: 350px;
            height: 500px;
            background: #fafafa;
            border-radius: 12px;
            border: 1px solid rgba(139, 92, 246, 0.2);
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
            z-index: 1001;
            display: flex;
            flex-direction: column;
            font-family: system-ui, -apple-system, sans-serif;
            overflow: hidden;
        }}

        /* Header */
        .chat-header-{clean_name} {{
            background: {primary_color};
            padding: 16px;
            border-bottom: 1px solid rgba(139, 92, 246, 0.2);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .header-info-{clean_name} {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .bot-avatar-header-{clean_name} {{
            width: 32px;
            height: 32px;
            background: {primary_color};
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .chip-icon-{clean_name} {{
            width: 20px;
            height: 20px;
            color: white;
        }}

        .bot-name-{clean_name} {{
            color: #a78bfa;
            font-size: 18px;
            font-weight: bold;
        }}

        .status-info-{clean_name} {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .status-dot-{clean_name} {{
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
        }}

        .status-text-{clean_name} {{
            color: #10b981;
            font-size: 12px;
        }}

        .close-btn-{clean_name} {{
            position: absolute;
            top: 16px;
            right: 16px;
            background: none;
            border: none;
            color: #94a3b8;
            font-size: 20px;
            cursor: pointer;
            padding: 4px;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            transition: all 0.2s ease;
        }}

        .close-btn-{clean_name}:hover {{
            background: rgba(139, 92, 246, 0.2);
            color: white;
        }}

        /* Messages */
        .chat-messages-{clean_name} {{
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .message-wrapper-{clean_name} {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }}

        .user-wrapper-{clean_name} {{
            flex-direction: row-reverse;
        }}

        .bot-avatar-{clean_name}, .user-avatar-{clean_name} {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}

        .bot-avatar-{clean_name} {{
            background: {primary_color};
        }}

        .user-avatar-{clean_name} {{
            background: #475569;
        }}

        .bot-message-{clean_name}, .user-message-{clean_name} {{
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 240px;
            word-wrap: break-word;
            line-height: 1.4;
        }}

        .bot-message-{clean_name} {{
            background: #f1f5f9; 
            color: #1e293b;
            border-radius: 12px 12px 12px 4px;
        }}

        .user-message-{clean_name} {{
            background: {primary_color};
            color: white;
            border-radius: 12px 12px 4px 12px;
        }}

        /* Typing Indicator */
        .typing-indicator-{clean_name} {{
            display: none;
            padding: 12px 16px;
            background: #374151;
            color: #9ca3af;
            border-radius: 12px 12px 12px 4px;
            max-width: 240px;
            font-style: italic;
        }}

        /* Input Area */
        .chat-input-container-{clean_name} {{
            padding: 16px;
            border-top: 1px solid #e5e7eb;
            background: #ffffff;
            display: flex;
            gap: 12px;
            align-items: center;
        }}

        #chat-input-{clean_name} {{
            flex: 1;
            background: #ffffff;
            color: #111111;
            border: 1px solid #e5e7eb;
            border-radius: 20px;
            padding: 12px 16px;
            outline: none;
            transition: all 0.2s ease;
            font-family: inherit;
        }}

        #chat-input-{clean_name}:focus {{
            background: #ffffff;
            box-shadow: 0 0 0 2px rgba(59,130,246,0.25);
        }}

        #chat-input-{clean_name}::placeholder {{
            color: #9ca3af;
        }}

        .send-btn-{clean_name} {{
            width: 44px;
            height: 44px;
            background: {primary_color};
            border: none;
            border-radius: 50%;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            flex-shrink: 0;
        }}

        .send-btn-{clean_name}:hover:not(:disabled) {{
            opacity: 0.9;
            transform: scale(1.05);
        }}

        .send-btn-{clean_name}:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        .send-icon-{clean_name} {{
            width: 20px;
            height: 20px;
        }}

        /* Scrollbar */
        .chat-messages-{clean_name}::-webkit-scrollbar {{
            width: 6px;
        }}

        .chat-messages-{clean_name}::-webkit-scrollbar-track {{
            background: transparent;
        }}

        .chat-messages-{clean_name}::-webkit-scrollbar-thumb {{
            background: rgba(139, 92, 246, 0.3);
            border-radius: 3px;
        }}

        .chat-messages-{clean_name}::-webkit-scrollbar-thumb:hover {{
            background: rgba(139, 92, 246, 0.5);
        }}

        /* Mobile Responsive */
        @media (max-width: 480px) {{
            .chat-popup-{clean_name} {{
                width: 90%;
                height: 70%;
                right: 5%;
                bottom: 90px;
            }}
        }}
    `;
    
    // Προσθήκη CSS στο DOM
    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
    
    // JavaScript Functionality
    const apiKey = '{api_key}';
    const chatButton = document.getElementById('chat-button-{clean_name}');
    const chatPopup = document.getElementById('chat-popup-{clean_name}');
    const closeChat = document.getElementById('close-chat-{clean_name}');
    const chatInput = document.getElementById('chat-input-{clean_name}');
    const sendBtn = document.getElementById('send-btn-{clean_name}');
    const messagesContainer = document.getElementById('chat-messages-{clean_name}');

    let sessionId = localStorage.getItem('chatbot_session_' + apiKey) || null;
    let isOpen = false;
    let messageHistory = [];
    let isLoading = false;
    
    // Δημιουργία typing indicator
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'message-wrapper-{clean_name} bot-wrapper-{clean_name}';
    typingIndicator.style.display = 'none';
    typingIndicator.innerHTML = `
        <div class="bot-avatar-{clean_name}">
            <svg class="chip-icon-{clean_name}" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
            </svg>
        </div>
        <div class="typing-indicator-{clean_name}" style="display: block;">Γράφει...</div>
    `;
    
    // Toggle chat popup
    chatButton.addEventListener('click', function() {{
        isOpen = !isOpen;
        chatPopup.style.display = isOpen ? 'flex' : 'none';
        if (isOpen) chatInput.focus();
    }});
    
    // Close chat
    closeChat.addEventListener('click', function() {{
        isOpen = false;
        chatPopup.style.display = 'none';
    }});
    
    // Send message on Enter key
    chatInput.addEventListener('keypress', function(e) {{
        if (e.key === 'Enter' && !isLoading) {{
            sendMessage();
        }}
    }});
    
    // Send message on button click
    sendBtn.addEventListener('click', function() {{
        if (!isLoading) {{
            sendMessage();
        }}
    }});
    
    function getRecentHistory() {{
        if (messageHistory.length === 0) {{
            return [];
        }}
        return messageHistory.slice(-6).map(msg => {{
            return {{ role: msg.role, content: msg.content }};
        }});
    }}
    
    function addMessage(content, isUser = false) {{
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `message-wrapper-{clean_name} ${{isUser ? 'user-wrapper-{clean_name}' : 'bot-wrapper-{clean_name}'}}`;
        
        if (isUser) {{
            messageWrapper.innerHTML = `
                <div class="user-avatar-{clean_name}">
                    <svg class="chip-icon-{clean_name}" fill="currentColor" viewBox="0 0 24 24">
                        <path fill-rule="evenodd" d="M7.5 6a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM3.751 20.105a8.25 8.25 0 0116.498 0 .75.75 0 01-.437.695A18.683 18.683 0 0112 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 01-.437-.695z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <div class="user-message-{clean_name}">${{content}}</div>
            `;
        }} else {{
            messageWrapper.innerHTML = `
                <div class="bot-avatar-{clean_name}">
                    <svg class="chip-icon-{clean_name}" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                    </svg>
                </div>
                <div class="bot-message-{clean_name}">${{content}}</div>
            `;
        }}
        
        messagesContainer.appendChild(messageWrapper);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        messageHistory.push({{ role: isUser ? 'user' : 'assistant', content: content }});
    }}
    
    function showTypingIndicator() {{
        messagesContainer.appendChild(typingIndicator);
        typingIndicator.style.display = 'flex';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }}
    
    function hideTypingIndicator() {{
        if (typingIndicator.parentNode) {{
            typingIndicator.parentNode.removeChild(typingIndicator);
        }}
        typingIndicator.style.display = 'none';
    }}
    
    async function sendMessage() {{
        const message = chatInput.value.trim();
        if (!message || isLoading) return;
        
        addMessage(message, true);
        chatInput.value = '';
        
        isLoading = true;
        chatInput.disabled = true;
        sendBtn.disabled = true;
        
        showTypingIndicator();
        
        try {{
            const currentScript = document.currentScript || 
                Array.from(document.getElementsByTagName('script')).find(s => 
                    s.src && s.src.includes('widget.js')
                );
            
            let apiBase = 'http://127.0.0.1:8000';
            
            if (currentScript && currentScript.src) {{
                const url = new URL(currentScript.src);
                apiBase = url.origin;
            }}
            
            const response = await fetch(`${{apiBase}}/widget-chat?api_key={api_key}`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    message: message,
                    history: getRecentHistory(),
                    session_id: sessionId
                }})
            }});
            
            if (!response.ok) {{
                throw new Error(`HTTP error! status: {{response.status}}`);
            }}
            
            hideTypingIndicator();
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let botResponse = '';
            
            const botMessageWrapper = document.createElement('div');
            botMessageWrapper.className = 'message-wrapper-{clean_name} bot-wrapper-{clean_name}';
            botMessageWrapper.innerHTML = `
                <div class="bot-avatar-{clean_name}">
                    <svg class="chip-icon-{clean_name}" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                    </svg>
                </div>
                <div class="bot-message-{clean_name}"></div>
            `;
            messagesContainer.appendChild(botMessageWrapper);
            const botMessageDiv = botMessageWrapper.querySelector('.bot-message-{clean_name}');
            
            while (true) {{
                const {{ done, value }} = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                const lines = chunk.split('\\n');
                for (const line of lines) {{
                    if (line.startsWith('data: ')) {{
                        const data = line.slice(6);
                        if (data === '[DONE]') {{
                            break;
                        }}
                        try {{
                            const parsed = JSON.parse(data);
                            if (parsed.response) {{
                                botResponse += parsed.response;
                                botMessageDiv.textContent = botResponse;
                                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                            }}
                            if (parsed.session_id) {{
                                sessionId = parsed.session_id;
                                localStorage.setItem('chatbot_session_' + apiKey, sessionId);
                                console.log('Session ID received and stored:', sessionId);
                            }}
                            if (parsed.error) {{
                                throw new Error(parsed.error);
                            }}
                        }} catch (e) {{
                            console.warn('Failed to parse chunk:', data);
                        }}
                    }}
                }}
            }}
            
            if (botResponse) {{
                messageHistory.push({{ role: 'assistant', content: botResponse }});
            }}
        }} catch (error) {{
            console.error('Chat error:', error);
            hideTypingIndicator();
            addMessage('Συγγνώμη, προέκυψε ένα σφάλμα. Παρακαλώ δοκιμάστε ξανά.', false);
        }} finally {{
            isLoading = false;
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }}
    }}
    
    console.log('Chat widget loaded for {company_name}');
    console.log('Widget is connected to API endpoint: /widget-chat?api_key={api_key}');
}})();
"""
