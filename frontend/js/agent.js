/**
 * OnboardAI - Agentic Copilot Chat, Tool Dispatch & Interactive Action Cards.
 */
let liveChatContext = {};

function renderAIChatUI(role, user) {
    liveChatContext = { role: role, email: user.email, name: user.name };
    const chatHeaderRole = document.getElementById('chat-header-role');
    if (chatHeaderRole) {
        chatHeaderRole.innerText = role === "manager" ? "Manager Operations Copilot" : "Day 1 Onboarding Buddy";
    }
    const chipsContainer = document.getElementById('quick-prompt-chips');
    if (chipsContainer) {
        const chips = role === "manager" 
            ? ["Approve all pending requests", "Show team bottlenecks", "Send training reminders"]
            : ["What is my next step?", "Request AWS Dev Sandbox", "Show my trainings", "Who is my manager?"];
        chipsContainer.innerHTML = chips.map(c => `
            <button onclick="sendChatMessage('${c}')" class="px-2.5 py-1 text-[11px] font-semibold bg-slate-100 hover:bg-blue-50 text-slate-600 hover:text-blue-700 rounded-lg border border-slate-200 transition shrink-0 cursor-pointer">
                ${c}
            </button>
        `).join('');
    }
}

async function sendChatMessage(customText = null) {
    const input = document.getElementById('chat-input-field');
    const text = customText || (input ? input.value.trim() : "");
    if (!text) return;
    if (input && !customText) input.value = "";

    appendChatMessage("user", text);

    // Typing indicator
    const typingId = appendTypingIndicator();

    try {
        const res = await fetch(`${BACKEND_BASE_URL}/api/agent/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, context: liveChatContext, role: liveChatContext.role })
        });
        const data = await res.json();
        removeTypingIndicator(typingId);

        if (data && data.success) {
            appendChatMessage("agent", data.reply, data.action_cards, data.tool_executed);
            // If tool was executed in chat, refresh the views
            if (data.tool_executed) {
                if (liveChatContext.role === "manager") loadManagerSession(liveChatContext.email);
                else loadEmployeeSession(liveChatContext.email);
            }
        } else {
            appendChatMessage("agent", "I ran into a temporary error. Please try again.");
        }
    } catch (e) {
        removeTypingIndicator(typingId);
        appendChatMessage("agent", "Connection notice: Server offline or unreachable.");
    }
}

function appendChatMessage(sender, text, actionCards = [], toolExecuted = null) {
    const box = document.getElementById('chat-messages-box');
    if (!box) return;

    const div = document.createElement('div');
    const isUser = sender === "user";
    div.className = `flex gap-2.5 mb-3.5 ${isUser ? 'justify-end' : 'justify-start'}`;

    let toolBadge = toolExecuted ? `
        <div class="mb-1.5 inline-flex items-center gap-1 px-2 py-0.5 bg-indigo-50 border border-indigo-200 rounded-md text-[10px] font-extrabold text-indigo-700">
            <span>⚡ Executed: ${toolExecuted}</span>
        </div>
    ` : '';

    let cardsHtml = "";
    if (actionCards && actionCards.length > 0) {
        cardsHtml = `
            <div class="mt-2.5 pt-2 border-t border-slate-100 flex flex-col gap-2">
                ${actionCards.map(c => `
                    <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-left">
                        <div class="text-xs font-bold text-slate-800">${c.title}</div>
                        ${c.desc ? `<div class="text-[11px] text-slate-500 mb-1.5">${c.desc}</div>` : ''}
                        <button onclick='executeAgentToolFromChat("${c.action}", ${JSON.stringify(c.payload || {})})' class="w-full px-3 py-1.5 bg-${c.color || 'blue'}-600 hover:bg-${c.color || 'blue'}-700 text-white font-bold text-xs rounded-lg shadow-2xs transition cursor-pointer">
                            ${c.btn_text || 'Execute Tool'}
                        </button>
                    </div>
                `).join('')}
            </div>
        `;
    }

    const formattedText = text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    div.innerHTML = `
        ${!isUser ? `<div class="w-7 h-7 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white font-bold flex items-center justify-center text-xs shrink-0">🤖</div>` : ''}
        <div class="max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs ${isUser ? 'bg-blue-600 text-white rounded-tr-xs' : 'bg-white border border-slate-200 text-slate-800 shadow-2xs rounded-tl-xs'}">
            ${toolBadge}
            <div class="leading-relaxed">${formattedText}</div>
            ${cardsHtml}
        </div>
        ${isUser ? `<div class="w-7 h-7 rounded-xl bg-slate-200 text-slate-700 font-bold flex items-center justify-center text-xs shrink-0">👤</div>` : ''}
    `;

    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

async function executeAgentToolFromChat(toolName, params) {
    try {
        appendChatMessage("user", `Execute tool: ${toolName}`);
        const res = await fetch(`${BACKEND_BASE_URL}/api/agent/execute_tool`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool_name: toolName, params: params })
        });
        const data = await res.json();
        if (data && data.success) {
            appendChatMessage("agent", `🤖 **Action Completed:** ${data.message}`);
            showToast("Agent Action Completed", data.message, "success");
            if (liveChatContext.role === "manager") loadManagerSession(liveChatContext.email);
            else loadEmployeeSession(liveChatContext.email);
        } else {
            appendChatMessage("agent", `❌ Action failed: ${data.message || 'Unknown error'}`);
        }
    } catch (e) {
        appendChatMessage("agent", "Error communicating with tool executor.");
    }
}

function appendTypingIndicator() {
    const box = document.getElementById('chat-messages-box');
    const id = "typing-" + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = "flex gap-2.5 mb-3.5 justify-start";
    div.innerHTML = `
        <div class="w-7 h-7 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white font-bold flex items-center justify-center text-xs shrink-0">🤖</div>
        <div class="bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 text-xs text-slate-400 flex items-center gap-1 shadow-2xs">
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"></span>
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0.2s]"></span>
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0.4s]"></span>
        </div>
    `;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
