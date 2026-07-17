// ==========================================
// CTU Chatbot - Frontend Script
// ==========================================

// --- Marked.js Configuration ---
marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try { return hljs.highlight(code, { language: lang }).value; }
            catch (_) {}
        }
        return hljs.highlightAuto(code).value;
    }
});

// ==========================================
// THEME MANAGEMENT
// ==========================================
const THEME_KEY = "ctu_theme";

function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || "light";
    applyTheme(saved, false);
}

function applyTheme(theme, animate = true) {
    if (animate) {
        document.body.style.transition = "background 0.3s, color 0.3s";
        setTimeout(() => { document.body.style.transition = ""; }, 350);
    }
    if (theme === "dark") {
        document.body.classList.add("dark-mode");
    } else {
        document.body.classList.remove("dark-mode");
    }
    // Update all toggle buttons
    document.querySelectorAll(".theme-toggle-btn").forEach(btn => {
        btn.innerHTML = theme === "dark" ? ICON_SUN : ICON_MOON;
        btn.title = theme === "dark" ? "Chuyển sang Light mode" : "Chuyển sang Dark mode";
    });
    localStorage.setItem(THEME_KEY, theme);
}

function toggleTheme() {
    const isDark = document.body.classList.contains("dark-mode");
    applyTheme(isDark ? "light" : "dark");
}

const ICON_MOON = `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
const ICON_SUN  = `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;

// ==========================================
// STATE MANAGEMENT
// ==========================================
const STATE = {
    conversations: [],      // Danh sách các cuộc hội thoại
    activeId: null,         // ID cuộc hội thoại đang active
    isLoading: false,       // Đang chờ AI trả lời?
    loadingConvId: null,    // ID conv đang được xử lý (để tránh render sai khi switch)
};

// Lấy cuộc hội thoại hiện tại
function getActive() {
    return STATE.conversations.find(c => c.id === STATE.activeId) || null;
}

// ==========================================
// LOCAL STORAGE
// ==========================================
const STORAGE_KEY = "ctu_chatbot_conversations";
const ACTIVE_KEY = "ctu_chatbot_active_id";

function saveToStorage() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(STATE.conversations));
        localStorage.setItem(ACTIVE_KEY, STATE.activeId || "");
    } catch (e) {
        console.warn("LocalStorage không khả dụng:", e);
    }
}

function loadFromStorage() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) STATE.conversations = JSON.parse(raw);
        const activeId = localStorage.getItem(ACTIVE_KEY);
        if (activeId && STATE.conversations.find(c => c.id === activeId)) {
            STATE.activeId = activeId;
        }
    } catch (e) {
        console.warn("Lỗi đọc LocalStorage:", e);
        STATE.conversations = [];
    }
}

// ==========================================
// CONVERSATION MANAGEMENT
// ==========================================
function generateId() {
    return "conv_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
}

function createNewConversation() {
    const conv = {
        id: generateId(),
        title: "Cuộc hội thoại mới",
        createdAt: Date.now(),
        messages: [],
    };
    STATE.conversations.unshift(conv);
    STATE.activeId = conv.id;
    saveToStorage();
    return conv;
}

function deleteConversation(id) {
    STATE.conversations = STATE.conversations.filter(c => c.id !== id);
    if (STATE.activeId === id) {
        STATE.activeId = STATE.conversations[0]?.id || null;
    }
    saveToStorage();
    renderAll();
}

function clearAllConversations() {
    STATE.conversations = [];
    STATE.activeId = null;
    saveToStorage();
    renderAll();
}

function switchConversation(id) {
    if (STATE.activeId === id) {
        closeSidebarOnMobile();
        return;
    }
    // Nếu đang loading, chỉ update state nhưng không hủy request
    // Request cũ vẫn chạy nền và sẽ lưu vào đúng conv của nó (không update DOM)
    STATE.activeId = id;
    saveToStorage();
    renderAll();
    closeSidebarOnMobile();
}

// Auto-generate title từ tin nhắn đầu tiên của user
function autoTitle(conv) {
    const firstUser = conv.messages.find(m => m.role === "user");
    if (firstUser) {
        const text = firstUser.content.trim();
        return text.length > 40 ? text.slice(0, 40) + "…" : text;
    }
    return "Cuộc hội thoại mới";
}

// ==========================================
// DOM ELEMENTS
// ==========================================
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const menuBtn = document.getElementById("menuBtn");
const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
const newChatBtn = document.getElementById("newChatBtn");
const topbarNewBtn = document.getElementById("topbarNewBtn");
const historyList = document.getElementById("historyList");
const clearAllBtn = document.getElementById("clearAllBtn");
const welcomeScreen = document.getElementById("welcomeScreen");
const messagesContainer = document.getElementById("messagesContainer");
const chatArea = document.getElementById("chatArea");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

// ==========================================
// RENDER FUNCTIONS
// ==========================================

/** Render toàn bộ UI */
function renderAll() {
    renderHistoryList();
    renderChatArea();
}

/** Render danh sách lịch sử */
function renderHistoryList() {
    historyList.innerHTML = "";
    if (STATE.conversations.length === 0) {
        historyList.innerHTML = `<div class="history-empty">Chưa có hội thoại nào</div>`;
        return;
    }
    STATE.conversations.forEach(conv => {
        const item = document.createElement("div");
        item.className = "history-item" + (conv.id === STATE.activeId ? " active" : "");
        item.innerHTML = `
            <span class="history-item-title">${escapeHtml(conv.title)}</span>
            <button class="history-item-delete" aria-label="Xóa hội thoại này">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        `;
        item.addEventListener("click", () => switchConversation(conv.id));
        item.querySelector(".history-item-delete").addEventListener("click", (e) => {
            e.stopPropagation();
            deleteConversation(conv.id);
        });
        historyList.appendChild(item);
    });
}

/** Render khu vực chat — FIX: luôn clear DOM sạch trước khi render */
function renderChatArea() {
    // Xóa typing indicator nếu đang hiển thị cho conv khác
    const existingIndicator = document.getElementById("typingIndicator");
    if (existingIndicator && STATE.loadingConvId !== STATE.activeId) {
        existingIndicator.remove();
    }

    const conv = getActive();
    if (!conv || conv.messages.length === 0) {
        welcomeScreen.style.display = "flex";
        messagesContainer.style.display = "none";
        messagesContainer.innerHTML = ""; // Xóa sạch messages cũ
        return;
    }
    welcomeScreen.style.display = "none";
    messagesContainer.style.display = "flex";
    messagesContainer.innerHTML = ""; // Luôn clear trước khi render lại

    conv.messages.forEach(msg => {
        appendMessageToDOM(msg.role, msg.content, false);
    });

    scrollToBottom(false);
}

/** Thêm một message vào DOM — chỉ render nếu conv này đang active */
function appendMessageToDOM(role, content, animate = true, targetConvId = null) {
    // Nếu có targetConvId và không phải conv đang active -> không render DOM
    if (targetConvId && targetConvId !== STATE.activeId) return;

    const time = new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    const row = document.createElement("div");
    row.className = `message-row ${role}${animate ? "" : " no-animate"}`;


    let bubbleContent = "";
    if (role === "assistant") {
        bubbleContent = marked.parse(content || "");
    } else {
        bubbleContent = escapeHtml(content);
    }

    const bubbleClass = role === "assistant" ? "message-bubble assistant-content" : "message-bubble";

    row.innerHTML = `
        <div class="message-meta">
            <span class="message-time">${time}</span>
        </div>
        <div class="${bubbleClass}">${bubbleContent}</div>
        ${role === "assistant" ? `
        <div class="message-actions">
            <button class="action-btn copy-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                </svg>
                Sao chép
            </button>
        </div>` : ""}
    `;

    // Highlight code blocks
    row.querySelectorAll("pre code").forEach(el => hljs.highlightElement(el));

    // Copy button
    const copyBtn = row.querySelector(".copy-btn");
    if (copyBtn) {
        copyBtn.addEventListener("click", () => copyText(content, copyBtn));
    }

    messagesContainer.appendChild(row);
    return row;
}

/** Thêm typing indicator */
function showTypingIndicator(convId) {
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.id = "typingIndicator";
    indicator.dataset.convId = convId;
    indicator.innerHTML = `
        <div class="typing-bubble">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    messagesContainer.appendChild(indicator);
    scrollToBottom(true);
    return indicator;
}

function removeTypingIndicator(convId = null) {
    const el = document.getElementById("typingIndicator");
    if (!el) return;
    // Chỉ xóa nếu đúng conv hoặc không quan tâm conv
    if (!convId || el.dataset.convId === convId) {
        el.remove();
    }
}

function scrollToBottom(smooth = true) {
    chatArea.scrollTo({
        top: chatArea.scrollHeight,
        behavior: smooth ? "smooth" : "auto",
    });
}

// ==========================================
// SEND MESSAGE
// ==========================================
async function sendMessage() {
    if (STATE.isLoading) return;
    const text = userInput.value.trim();
    if (!text) return;

    // Nếu chưa có cuộc hội thoại, tạo mới
    if (!STATE.activeId) {
        createNewConversation();
        renderAll();
    }

    const conv = getActive();
    const convId = conv.id; // Ghi lại ID để tránh race condition khi switch conv

    // Ẩn welcome screen, hiện messages
    welcomeScreen.style.display = "none";
    messagesContainer.style.display = "flex";

    // Lấy history TRƯỚC khi thêm message mới
    const historyForAPI = [...conv.messages];

    // Thêm message của user vào state
    conv.messages.push({ role: "user", content: text });
    conv.title = autoTitle(conv);
    saveToStorage();
    renderHistoryList();
    appendMessageToDOM("user", text, true, convId);

    userInput.value = "";
    autoResizeInput();
    sendBtn.disabled = true;
    STATE.isLoading = true;
    STATE.loadingConvId = convId;

    // Hiển thị typing indicator (chỉ nếu conv này đang active)
    if (STATE.activeId === convId) {
        showTypingIndicator(convId);
    }

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, history: historyForAPI }),
        });

        // Xóa typing indicator của conv này
        removeTypingIndicator(convId);

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${response.status}`);
        }

        const data = await response.json();
        const answer = data.answer || "(Không có câu trả lời)";

        // Lưu vào đúng conv (dù user đã switch sang conv khác)
        conv.messages.push({ role: "assistant", content: answer });
        saveToStorage();

        // CHỈ render vào DOM nếu conv này vẫn đang active
        if (STATE.activeId === convId) {
            appendMessageToDOM("assistant", answer, true, convId);
            scrollToBottom(true);
        }
        // Nếu user đã switch sang conv khác -> cập nhật title trong sidebar (không render chat)
        renderHistoryList();

    } catch (err) {
        removeTypingIndicator(convId);
        if (STATE.activeId === convId) {
            const errRow = document.createElement("div");
            errRow.className = "message-row assistant";
            errRow.style.animation = "message-appear 0.3s ease forwards";
            errRow.innerHTML = `
                <div class="error-bubble">
                    <span>⚠️</span>
                    <span>Lỗi: ${escapeHtml(err.message)}</span>
                </div>
            `;
            messagesContainer.appendChild(errRow);
            scrollToBottom(true);
        }
    } finally {
        STATE.isLoading = false;
        STATE.loadingConvId = null;
        updateSendBtn();
    }
}

// ==========================================
// SIDEBAR TOGGLE (Mobile)
// ==========================================
function openSidebar() {
    sidebar.classList.add("open");
    sidebarOverlay.classList.add("visible");
    document.body.style.overflow = "hidden";
}

function closeSidebar() {
    sidebar.classList.remove("open");
    sidebarOverlay.classList.remove("visible");
    document.body.style.overflow = "";
}

function closeSidebarOnMobile() {
    if (window.innerWidth <= 768) closeSidebar();
}

// ==========================================
// INPUT HELPERS
// ==========================================
function autoResizeInput() {
    userInput.style.height = "auto";
    const maxH = 160;
    userInput.style.height = Math.min(userInput.scrollHeight, maxH) + "px";
}

function updateSendBtn() {
    sendBtn.disabled = STATE.isLoading || !userInput.value.trim();
}

function copyText(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        const original = btn.innerHTML;
        btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Đã sao chép`;
        btn.classList.add("copied");
        setTimeout(() => { btn.innerHTML = original; btn.classList.remove("copied"); }, 2000);
    }).catch(() => alert("Không thể sao chép. Vui lòng chọn thủ công."));
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// ==========================================
// STATUS CHECK
// ==========================================
async function checkStatus() {
    try {
        const res = await fetch("/api/status");
        if (res.ok) {
            const data = await res.json();
            statusDot.className = "status-dot online";
            statusText.textContent = `Sẵn sàng (${data.nganh_count || 0} ngành)`;
        } else {
            throw new Error();
        }
    } catch {
        statusDot.className = "status-dot error";
        statusText.textContent = "Lỗi kết nối";
    }
}

// ==========================================
// EVENT LISTENERS
// ==========================================
function initEventListeners() {
    // New chat
    newChatBtn.addEventListener("click", () => {
        createNewConversation();
        renderAll();
        userInput.focus();
        closeSidebarOnMobile();
    });

    topbarNewBtn.addEventListener("click", () => {
        createNewConversation();
        renderAll();
        userInput.focus();
    });

    // Send message
    sendBtn.addEventListener("click", sendMessage);

    userInput.addEventListener("input", () => {
        autoResizeInput();
        updateSendBtn();
    });

    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Suggestion chips
    document.querySelectorAll(".suggestion-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const question = chip.dataset.question;
            if (question) {
                userInput.value = question;
                autoResizeInput();
                updateSendBtn();
                sendMessage();
            }
        });
    });

    // Sidebar toggle
    menuBtn.addEventListener("click", openSidebar);
    sidebarToggleBtn.addEventListener("click", closeSidebar);
    sidebarOverlay.addEventListener("click", closeSidebar);

    // Theme toggle — bind tất cả buttons có class .theme-toggle-btn
    document.querySelectorAll(".theme-toggle-btn").forEach(btn => {
        btn.addEventListener("click", toggleTheme);
    });

    // Clear all
    clearAllBtn.addEventListener("click", () => {
        if (STATE.conversations.length === 0) return;
        if (confirm("Bạn có chắc muốn xóa tất cả lịch sử hội thoại không?")) {
            clearAllConversations();
        }
    });

    // Close sidebar on resize
    window.addEventListener("resize", () => {
        if (window.innerWidth > 768) closeSidebar();
    });
}

// ==========================================
// INIT
// ==========================================
function init() {
    initTheme();
    loadFromStorage();

    if (STATE.conversations.length === 0 || !STATE.activeId) {
        STATE.activeId = null;
    }

    renderAll();
    initEventListeners();
    checkStatus();

    setTimeout(() => userInput.focus(), 100);
}

document.addEventListener("DOMContentLoaded", init);
