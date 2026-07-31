// ==========================================
// CTU Chatbot - Frontend Script (Auth + DB version)
// ==========================================

const renderer = new marked.Renderer();
const linkRenderer = renderer.link;
renderer.link = (href, title, text) => {
    const html = linkRenderer.call(renderer, href, title, text);
    return html.replace(/^<a /, '<a target="_blank" rel="noopener noreferrer" ');
};

marked.setOptions({
    renderer: renderer,
    breaks: true,
    gfm: true,
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try { return hljs.highlight(code, { language: lang }).value; }
            catch (_) { }
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
// STATE MANAGEMENT (server-backed)
// ==========================================
const STATE = {
    conversations: [],      // [{id, title, updated_at}] — từ server
    activeId: null,         // ID conversation đang active (số nguyên từ DB)
    activeMessages: [],     // Messages của conversation hiện tại
    isLoading: false,
    loadingConvId: null,
};

function getActive() {
    return STATE.conversations.find(c => c.id === STATE.activeId) || null;
}

// ==========================================
// SERVER API HELPERS
// ==========================================

async function apiGet(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function apiPost(url, body) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
}

async function apiDelete(url) {
    const res = await fetch(url, { method: "DELETE" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function apiPatch(url, body) {
    const res = await fetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

// ==========================================
// CONVERSATION MANAGEMENT (server-backed)
// ==========================================

/** Tải danh sách conversations từ server */
async function loadConversationsFromServer() {
    try {
        const convs = await apiGet("/api/conversations");
        STATE.conversations = convs;
        // Khôi phục active conversation từ localStorage
        const savedActiveId = parseInt(localStorage.getItem("ctu_active_conv_id") || "0");
        if (savedActiveId && STATE.conversations.find(c => c.id === savedActiveId)) {
            STATE.activeId = savedActiveId;
            await loadMessagesForConversation(savedActiveId);
        } else if (STATE.conversations.length > 0) {
            // Không có active cụ thể → không chọn gì (hiện welcome screen)
            STATE.activeId = null;
        }
        renderAll();
    } catch (e) {
        console.error("Lỗi tải conversations:", e);
    }
}

/** Tải messages cho một conversation */
async function loadMessagesForConversation(convId) {
    try {
        const msgs = await apiGet(`/api/conversations/${convId}/messages`);
        STATE.activeMessages = msgs; // [{role, content, ...}]
    } catch (e) {
        console.error("Lỗi tải messages:", e);
        STATE.activeMessages = [];
    }
}

/** Tạo conversation mới — trả về conv object hoặc null */
async function createConversationOnServer(title = "Cuộc hội thoại mới") {
    try {
        const conv = await apiPost("/api/conversations", { title });
        STATE.conversations.unshift(conv);
        return conv;
    } catch (e) {
        console.error("Lỗi tạo conversation:", e);
        return null;
    }
}

/** Xóa một conversation */
async function deleteConversation(id) {
    try {
        await apiDelete(`/api/conversations/${id}`);
        STATE.conversations = STATE.conversations.filter(c => c.id !== id);
        if (STATE.activeId === id) {
            STATE.activeId = null;
            STATE.activeMessages = [];
            localStorage.removeItem("ctu_active_conv_id");
        }
        renderAll();
    } catch (e) {
        console.error("Lỗi xóa conversation:", e);
    }
}

/** Xóa tất cả conversations */
async function clearAllConversations() {
    try {
        await apiDelete("/api/conversations/all");
        STATE.conversations = [];
        STATE.activeId = null;
        STATE.activeMessages = [];
        localStorage.removeItem("ctu_active_conv_id");
        renderAll();
    } catch (e) {
        console.error("Lỗi xóa tất cả:", e);
    }
}

/** Chuyển sang conversation khác */
async function switchConversation(id) {
    if (STATE.activeId === id) {
        closeSidebarOnMobile();
        return;
    }
    STATE.activeId = id;
    STATE.activeMessages = [];
    localStorage.setItem("ctu_active_conv_id", id);
    renderHistoryList();

    // Hiển thị loading skeleton
    showLoadingMessages();

    await loadMessagesForConversation(id);
    renderChatArea();
    closeSidebarOnMobile();
}

/** Auto-generate title từ tin nhắn đầu tiên */
function autoTitle(text) {
    return text.length > 55 ? text.slice(0, 55) + "…" : text;
}

// ==========================================
// DOM ELEMENTS
// ==========================================
const sidebar           = document.getElementById("sidebar");
const sidebarOverlay    = document.getElementById("sidebarOverlay");
const menuBtn           = document.getElementById("menuBtn");
const sidebarToggleBtn  = document.getElementById("sidebarToggleBtn");
const sidebarCollapseBtn = document.getElementById("sidebarCollapseBtn");
const sidebarExpandBtn  = document.getElementById("sidebarExpandBtn");
const newChatBtn        = document.getElementById("newChatBtn");
const topbarNewBtn      = document.getElementById("topbarNewBtn");
const historyList       = document.getElementById("historyList");
const clearAllBtn       = document.getElementById("clearAllBtn");
const welcomeScreen     = document.getElementById("welcomeScreen");
const messagesContainer = document.getElementById("messagesContainer");
const chatArea          = document.getElementById("chatArea");
const userInput         = document.getElementById("userInput");
const sendBtn           = document.getElementById("sendBtn");
const statusDot         = document.getElementById("statusDot");
const statusText        = document.getElementById("statusText");
const userAvatar        = document.getElementById("userAvatar");

// ==========================================
// USER AVATAR INIT
// ==========================================
function initUserAvatar() {
    const fullname = document.body.dataset.fullname || "";
    const username = document.body.dataset.username || "?";
    const letter = (fullname || username).charAt(0).toUpperCase();
    if (userAvatar) {
        userAvatar.textContent = letter;
    }
}

// ==========================================
// RENDER FUNCTIONS
// ==========================================
function renderAll() {
    renderHistoryList();
    renderChatArea();
}

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

/** Hiển thị loading skeleton khi đang tải messages */
function showLoadingMessages() {
    welcomeScreen.style.display = "none";
    messagesContainer.style.display = "flex";
    messagesContainer.innerHTML = `
        <div class="msg-skeleton-wrap">
            <div class="msg-skeleton user"></div>
            <div class="msg-skeleton assistant"></div>
            <div class="msg-skeleton user short"></div>
            <div class="msg-skeleton assistant"></div>
        </div>
    `;
}

function renderChatArea() {
    const existingIndicator = document.getElementById("typingIndicator");
    if (existingIndicator && STATE.loadingConvId !== STATE.activeId) {
        existingIndicator.remove();
    }

    const conv = getActive();
    if (!conv || STATE.activeMessages.length === 0) {
        welcomeScreen.style.display = "flex";
        messagesContainer.style.display = "none";
        messagesContainer.innerHTML = "";
        return;
    }
    welcomeScreen.style.display = "none";
    messagesContainer.style.display = "flex";
    messagesContainer.innerHTML = "";

    STATE.activeMessages.forEach(msg => {
        appendMessageToDOM(msg.role, msg.content, false);
    });

    scrollToBottom(false);
}

function appendMessageToDOM(role, content, animate = true, targetConvId = null) {
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

    row.querySelectorAll("pre code").forEach(el => hljs.highlightElement(el));

    const copyBtn = row.querySelector(".copy-btn");
    if (copyBtn) {
        copyBtn.addEventListener("click", () => copyText(content, copyBtn));
    }

    messagesContainer.appendChild(row);
    return row;
}

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
    if (!convId || el.dataset.convId == convId) {
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
// SEND MESSAGE (server-backed)
// ==========================================
async function sendMessage() {
    if (STATE.isLoading) return;
    const text = userInput.value.trim();
    if (!text) return;

    // Nếu chưa có active conversation, server sẽ tự tạo
    let convId = STATE.activeId;

    // Ẩn welcome screen
    welcomeScreen.style.display = "none";
    messagesContainer.style.display = "flex";

    // Thêm message user vào DOM ngay
    appendMessageToDOM("user", text, true, convId);

    userInput.value = "";
    autoResizeInput();
    sendBtn.disabled = true;
    STATE.isLoading = true;
    STATE.loadingConvId = convId;

    if (STATE.activeId === convId || convId === null) {
        showTypingIndicator(convId || "new");
    }

    try {
        const data = await apiPost("/api/chat", {
            message: text,
            conversation_id: convId || null,
        });

        const answer = data.answer || "(Không có câu trả lời)";
        const returnedConvId = data.conversation_id;

        removeTypingIndicator(convId || "new");

        // Nếu server tạo conversation mới → cập nhật state
        if (!convId || convId !== returnedConvId) {
            convId = returnedConvId;
            STATE.activeId = convId;
            STATE.loadingConvId = convId;
            localStorage.setItem("ctu_active_conv_id", convId);
            // Tải lại danh sách conversations
            const convs = await apiGet("/api/conversations");
            STATE.conversations = convs;
            renderHistoryList();
        } else {
            // Cập nhật updated_at trong danh sách local (để sort)
            const convInList = STATE.conversations.find(c => c.id === convId);
            if (convInList) {
                convInList.updated_at = new Date().toISOString();
                // Re-sort
                STATE.conversations.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
                renderHistoryList();
            }
        }

        // Thêm vào activeMessages (đồng bộ local state)
        STATE.activeMessages.push({ role: "user", content: text });
        STATE.activeMessages.push({ role: "assistant", content: answer });

        // Render vào DOM
        if (STATE.activeId === convId) {
            appendMessageToDOM("assistant", answer, true, convId);
            scrollToBottom(true);
        }

    } catch (err) {
        removeTypingIndicator(convId || "new");
        if (STATE.activeId === convId || convId === null) {
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
    // New chat — chỉ reset UI, không tạo conv ngay (server sẽ tạo khi gửi tin đầu)
    newChatBtn.addEventListener("click", () => {
        STATE.activeId = null;
        STATE.activeMessages = [];
        localStorage.removeItem("ctu_active_conv_id");
        renderAll();
        userInput.focus();
        closeSidebarOnMobile();
    });

    topbarNewBtn.addEventListener("click", () => {
        STATE.activeId = null;
        STATE.activeMessages = [];
        localStorage.removeItem("ctu_active_conv_id");
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

    // Sidebar toggle (mobile)
    menuBtn.addEventListener("click", openSidebar);
    sidebarToggleBtn.addEventListener("click", closeSidebar);
    sidebarOverlay.addEventListener("click", closeSidebar);

    // Sidebar collapse/expand (desktop)
    sidebarCollapseBtn.addEventListener("click", collapseSidebar);
    sidebarExpandBtn.addEventListener("click", expandSidebar);

    // Theme toggle
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
// SIDEBAR COLLAPSE (Desktop)
// ==========================================
const SIDEBAR_COLLAPSED_KEY = "ctu_sidebar_collapsed";

function collapseSidebar() {
    document.body.classList.add("sidebar-collapsed");
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, "1");
}

function expandSidebar() {
    document.body.classList.remove("sidebar-collapsed");
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, "0");
}

function initSidebarCollapse() {
    if (window.innerWidth <= 768) return;
    const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    if (saved === "1") {
        document.body.classList.add("sidebar-collapsed");
    }
}

// ==========================================
// SPEECH-TO-TEXT (Web Speech API)
// ==========================================
const micBtn  = document.getElementById("micBtn");
const micToast = document.getElementById("micToast");

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition    = null;
let isRecording    = false;
let toastTimer     = null;
let interimBuffer  = "";
let preMicText     = "";

function showMicToast(message, type = "info", duration = 0) {
    if (toastTimer) clearTimeout(toastTimer);
    micToast.className = "mic-toast";
    if (type === "error") micToast.classList.add("error");

    if (type === "recording") {
        micToast.innerHTML = `<span class="mic-toast-dot"></span>${message}`;
    } else {
        micToast.innerHTML = message;
    }

    micToast.offsetHeight;
    micToast.classList.add("visible");

    if (duration > 0) {
        toastTimer = setTimeout(() => hideMicToast(), duration);
    }
}

function hideMicToast() {
    if (toastTimer) { clearTimeout(toastTimer); toastTimer = null; }
    micToast.classList.remove("visible");
}

function initSpeechRecognition() {
    if (!SpeechRecognition) return null;

    const rec = new SpeechRecognition();
    rec.lang = "vi-VN";
    rec.continuous = true;
    rec.interimResults = true;

    rec.onstart = () => {
        isRecording = true;
        interimBuffer = "";
        preMicText = userInput.value;
        micBtn.classList.add("recording");
        showMicToast("Đang lắng nghe...", "recording");
    };

    rec.onresult = (event) => {
        let finalText = "";
        interimBuffer = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalText += transcript;
            } else {
                interimBuffer += transcript;
            }
        }

        if (finalText) {
            const base = preMicText.trim();
            const current = userInput.value;
            const recognized = current.slice(base.length).trim();
            userInput.value = base ? base + " " + recognized + finalText : recognized + finalText;
            preMicText = userInput.value;
            interimBuffer = "";
        } else if (interimBuffer) {
            const base = preMicText.trim();
            userInput.value = base ? base + " " + interimBuffer : interimBuffer;
        }

        autoResizeInput();
        updateSendBtn();
    };

    rec.onerror = (event) => {
        isRecording = false;
        micBtn.classList.remove("recording");

        let errorMsg = "Lỗi nhận dạng giọng nói.";
        switch (event.error) {
            case "not-allowed":
            case "permission-denied":
                errorMsg = "❌ Bạn chưa cấp quyền microphone. Vui lòng kiểm tra cài đặt trình duyệt.";
                break;
            case "no-speech":
                errorMsg = "Không nghe thấy giọng nói. Hãy thử lại!";
                break;
            case "network":
                errorMsg = "❌ Lỗi kết nối mạng. Nhận dạng giọng nói cần internet.";
                break;
            case "audio-capture":
                errorMsg = "❌ Không tìm thấy microphone. Hãy kiểm tra thiết bị.";
                break;
            case "aborted":
                hideMicToast();
                return;
        }
        showMicToast(errorMsg, "error", 3500);
    };

    rec.onend = () => {
        if (isRecording) {
            isRecording = false;
            micBtn.classList.remove("recording");
            hideMicToast();
        }
    };

    return rec;
}

function toggleMic() {
    if (!SpeechRecognition) {
        showMicToast("❌ Trình duyệt không hỗ trợ nhận dạng giọng nói. Hãy dùng Chrome hoặc Edge.", "error", 4000);
        return;
    }

    if (isRecording) {
        isRecording = false;
        recognition.stop();
        micBtn.classList.remove("recording");
        hideMicToast();

        const finalizedText = preMicText.trim();
        userInput.value = finalizedText;
        autoResizeInput();
        updateSendBtn();
        userInput.focus();
    } else {
        recognition = initSpeechRecognition();
        if (!recognition) return;
        try {
            recognition.start();
        } catch (e) {
            showMicToast("❌ Không thể khởi động microphone. Thử lại!", "error", 3000);
        }
    }
}

function initMicButton() {
    if (!SpeechRecognition) {
        micBtn.classList.add("unsupported");
        micBtn.title = "Trình duyệt không hỗ trợ nhận dạng giọng nói";
    }
    micBtn.addEventListener("click", toggleMic);
}

// ==========================================
// INIT
// ==========================================
async function init() {
    initTheme();
    initSidebarCollapse();
    initUserAvatar();

    // Hiện loading state ban đầu
    historyList.innerHTML = `<div class="history-empty">Đang tải...</div>`;

    // Tải conversations từ server
    await loadConversationsFromServer();

    initEventListeners();
    initMicButton();
    checkStatus();

    setTimeout(() => userInput.focus(), 100);
}

document.addEventListener("DOMContentLoaded", init);
