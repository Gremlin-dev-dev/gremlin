let currentConversationId = null;

function scrollBottom() {
    const chatBox = document.getElementById("chat-box");
    chatBox.scrollTop = chatBox.scrollHeight;
}

function escapeText(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

async function typeReply(element, text) {
    let output = "";
    const words = text.split(" ");

    for (const word of words) {
        output += word + " ";

        element.innerHTML = marked.parse(output);

        document.querySelectorAll("pre code").forEach(block => {
            hljs.highlightElement(block);
        });

        if (window.MathJax) {
            await MathJax.typesetPromise();
        }

        scrollBottom();

        await new Promise(r => setTimeout(r, 25));
    }
}

function attachImageModal(img) {
    img.onclick = () => {
        const modal = document.getElementById("image-modal");
        const modalImg = document.getElementById("modal-image");

        if (modal && modalImg) {
            modalImg.src = img.src;
            modal.style.display = "flex";
        }
    };
}

async function sendMessage() {

    const input = document.getElementById("message");
    const imageInput = document.getElementById("image");
    const chatBox = document.getElementById("chat-box");
    const attachBtn = document.querySelector(".attach-btn");

    const message = input.value.trim();

    if (!message && imageInput.files.length === 0) {
        return;
    }

    const userMessage = document.createElement("div");
    userMessage.className = "user-msg";

    userMessage.innerHTML = `
        <span class="msg-label">You</span>
        <div class="msg-content">${escapeText(message)}</div>
    `;

    if (imageInput.files.length) {
        const file = imageInput.files[0];

        const img = document.createElement("img");
        img.className = "uploaded-image";
        img.src = URL.createObjectURL(file);
        attachImageModal(img);

        userMessage.querySelector(".msg-content").appendChild(img);
    }

    chatBox.appendChild(userMessage);

    input.value = "";
    autoResizeMessageInput();

    const thinking = document.createElement("div");

    thinking.className = "bot-msg";
    thinking.id = "thinking";

    thinking.innerHTML = `
        <span class="msg-label">GREMLIN</span>
        <div class="typing">
            GREMLIN is conquering
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
    `;

    chatBox.appendChild(thinking);

    scrollBottom();

    try {

        const formData = new FormData();

        formData.append("message", message);

        if (currentConversationId) {
            formData.append("conversation_id", currentConversationId);
        }

        if (imageInput.files.length) {
            formData.append("image", imageInput.files[0]);
        }

        const response = await fetch("/chat", {
            method: "POST",
            body: formData
        });

        if (response.status === 401) {
            window.location.href = "/auth/login";
            return;
        }

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `Request failed (${response.status})`);
        }

        const data = await response.json();

        const isNewConversation = !currentConversationId;
        currentConversationId = data.conversation_id;

        thinking.remove();

        const bot = document.createElement("div");

        bot.className = "bot-msg";

        bot.innerHTML = `
            <span class="msg-label">GREMLIN</span>
            <div class="reply"></div>
        `;

        chatBox.appendChild(bot);

        await typeReply(
            bot.querySelector(".reply"),
            data.reply
        );

        enhanceCodeBlocks();

        speakText(data.reply);

        input.value = "";
        autoResizeMessageInput();

        if (imageInput) {
            imageInput.value = "";
        }

        if (attachBtn) {
            attachBtn.classList.remove("has-file");
        }

        scrollBottom();

        loadConversations(currentConversationId);

    } catch (err) {

        console.error(err);

        thinking.remove();

        chatBox.innerHTML += `
            <div class="bot-msg">
                <span class="msg-label">GREMLIN</span>
                <div class="msg-content">⚠️ ${escapeText(err.message)}</div>
            </div>
        `;

        scrollBottom();

    }

}


// ===========================
// Press Enter to Send
// ===========================

const messageInput = document.getElementById("message");

function autoResizeMessageInput() {
    if (!messageInput) return;
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + "px";
}

if (messageInput) {

    messageInput.addEventListener("keydown", (e) => {

        if (e.key === "Enter" && !e.shiftKey) {

            e.preventDefault();
            sendMessage();

        }

    });

    messageInput.addEventListener("input", autoResizeMessageInput);

}

// ===========================
// New Chat
// ===========================

function newChat() {
    currentConversationId = null;
    document.getElementById("chat-box").innerHTML = "";

    document.querySelectorAll(".chat-item").forEach(item => {
        item.classList.remove("active");
    });

    if (messageInput) {
        messageInput.focus();
    }
}

const newChatBtn = document.getElementById("new-chat");

if (newChatBtn) {
    newChatBtn.addEventListener("click", newChat);
}

// ===========================
// Conversations (sidebar + restore)
// ===========================

function renderConversationMessage(msg) {
    const chatBox = document.getElementById("chat-box");

    if (msg.role === "user") {
        const el = document.createElement("div");
        el.className = "user-msg";

        el.innerHTML = `
            <span class="msg-label">You</span>
            <div class="msg-content">${escapeText(msg.text)}</div>
        `;

        if (msg.image_path) {
            const img = document.createElement("img");
            img.className = "uploaded-image";
            img.src = msg.image_path;
            attachImageModal(img);
            el.querySelector(".msg-content").appendChild(img);
        }

        chatBox.appendChild(el);

    } else {
        const el = document.createElement("div");
        el.className = "bot-msg";

        el.innerHTML = `
            <span class="msg-label">GREMLIN</span>
            <div class="reply">${marked.parse(msg.text || "")}</div>
        `;

        chatBox.appendChild(el);
    }
}

async function loadConversation(id) {
    try {
        const response = await fetch(`/api/conversations/${id}`);

        if (response.status === 401) {
            window.location.href = "/auth/login";
            return;
        }

        if (!response.ok) return;

        const data = await response.json();

        currentConversationId = data.id;

        const chatBox = document.getElementById("chat-box");
        chatBox.innerHTML = "";

        data.messages.forEach(renderConversationMessage);

        document.querySelectorAll("pre code").forEach(block => {
            hljs.highlightElement(block);
        });

        enhanceCodeBlocks();

        if (window.MathJax) {
            await MathJax.typesetPromise();
        }

        document.querySelectorAll(".chat-item").forEach(item => {
            item.classList.toggle("active", Number(item.dataset.id) === id);
        });

        scrollBottom();

    } catch (err) {
        console.error(err);
    }
}

function closeAllChatDropdowns() {
    document.querySelectorAll(".chat-item-dropdown.open").forEach(d => d.classList.remove("open"));
    document.querySelectorAll(".chat-item-menu-btn.open").forEach(b => b.classList.remove("open"));
}

async function renameConversationRequest(id, title) {
    try {
        const response = await fetch(`/api/conversations/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title })
        });

        if (response.status === 401) {
            window.location.href = "/auth/login";
            return null;
        }

        if (!response.ok) return null;

        return await response.json();

    } catch (err) {
        console.error(err);
        return null;
    }
}

async function deleteConversationRequest(id) {
    try {
        const response = await fetch(`/api/conversations/${id}`, {
            method: "DELETE"
        });

        if (response.status === 401) {
            window.location.href = "/auth/login";
            return false;
        }

        return response.ok;

    } catch (err) {
        console.error(err);
        return false;
    }
}

function startRenameInline(item, titleSpan, conv) {
    closeAllChatDropdowns();

    const input = document.createElement("input");
    input.type = "text";
    input.className = "chat-item-rename-input";
    input.value = conv.title || "New chat";

    titleSpan.replaceWith(input);
    input.focus();
    input.select();

    const finish = async (save) => {
        const newTitle = input.value.trim();

        if (save && newTitle && newTitle !== conv.title) {
            const updated = await renameConversationRequest(conv.id, newTitle);
            if (updated) conv.title = updated.title;
        }

        const span = document.createElement("span");
        span.className = "chat-item-title";
        span.textContent = conv.title || "New chat";
        input.replaceWith(span);
    };

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            finish(true);
        } else if (e.key === "Escape") {
            e.preventDefault();
            finish(false);
        }
    });

    input.addEventListener("blur", () => finish(true));
}

async function loadConversations(activeId) {
    try {
        const response = await fetch("/api/conversations");

        if (response.status === 401) {
            window.location.href = "/auth/login";
            return;
        }

        if (!response.ok) return;

        const conversations = await response.json();

        const chatList = document.getElementById("chat-list");
        chatList.innerHTML = "";

        conversations.forEach(conv => {
            const item = document.createElement("div");
            item.className = "chat-item";
            item.dataset.id = conv.id;

            if (activeId && Number(activeId) === conv.id) {
                item.classList.add("active");
            }

            const titleSpan = document.createElement("span");
            titleSpan.className = "chat-item-title";
            titleSpan.textContent = conv.title || "New chat";

            const menuBtn = document.createElement("button");
            menuBtn.className = "chat-item-menu-btn";
            menuBtn.setAttribute("aria-label", "Chat options");
            menuBtn.innerHTML = `
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>
            `;

            const dropdown = document.createElement("div");
            dropdown.className = "chat-item-dropdown";
            dropdown.innerHTML = `
                <button type="button" class="rename-action">Rename</button>
                <button type="button" class="danger delete-action">Delete</button>
            `;

            menuBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                const isOpen = dropdown.classList.contains("open");
                closeAllChatDropdowns();
                if (!isOpen) {
                    dropdown.classList.add("open");
                    menuBtn.classList.add("open");
                }
            });

            dropdown.querySelector(".rename-action").addEventListener("click", (e) => {
                e.stopPropagation();
                closeAllChatDropdowns();
                startRenameInline(item, titleSpan, conv);
            });

            dropdown.querySelector(".delete-action").addEventListener("click", async (e) => {
                e.stopPropagation();
                closeAllChatDropdowns();

                const confirmed = window.confirm("Delete this conversation? This can't be undone.");
                if (!confirmed) return;

                const success = await deleteConversationRequest(conv.id);

                if (success) {
                    item.remove();

                    if (currentConversationId === conv.id) {
                        newChat();
                    }
                }
            });

            item.addEventListener("click", () => loadConversation(conv.id));

            item.appendChild(titleSpan);
            item.appendChild(menuBtn);
            item.appendChild(dropdown);

            chatList.appendChild(item);
        });

        return conversations;

    } catch (err) {
        console.error(err);
        return [];
    }
}

document.addEventListener("click", () => {
    closeAllChatDropdowns();
});

// ===========================
// Image Modal
// ===========================

const imageModal = document.getElementById("image-modal");

if (imageModal) {

    imageModal.addEventListener("click", () => {

        imageModal.style.display = "none";

    });

}

// ===========================
// Attachment Button
// ===========================

const imageInput = document.getElementById("image");
const attachBtn = document.querySelector(".attach-btn");

if (imageInput && attachBtn) {

    imageInput.addEventListener("change", () => {

        attachBtn.classList.toggle("has-file", imageInput.files.length > 0);

    });

}

// ===========================
// Logout
// ===========================

const logoutBtn = document.getElementById("logout-btn");

if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
        try {
            const response = await fetch("/auth/logout", { method: "POST" });
            const data = await response.json().catch(() => ({}));
            window.location.href = data.redirect || "/auth/login";
        } catch (err) {
            window.location.href = "/auth/login";
        }
    });
}

// ===========================
// Code Highlight + Copy Buttons
// ===========================

function enhanceCodeBlocks() {

    document.querySelectorAll("pre code").forEach(block => {

        hljs.highlightElement(block);

        const pre = block.parentElement;

        // already wrapped
        if (pre.parentElement.classList.contains("code-block")) return;

        const langMatch = block.className.match(/language-(\w+)/);
        const lang = langMatch ? langMatch[1] : "text";

        const wrapper = document.createElement("div");
        wrapper.className = "code-block";

        const header = document.createElement("div");
        header.className = "code-block-header";

        const langLabel = document.createElement("span");
        langLabel.className = "code-lang";
        langLabel.textContent = lang;

        const button = document.createElement("button");
        button.className = "copy-btn";
        button.textContent = "Copy";

        button.onclick = async () => {

            try {

                await navigator.clipboard.writeText(block.innerText);

                button.textContent = "Copied ✓";

                setTimeout(() => {

                    button.textContent = "Copy";

                }, 2000);

            } catch {

                button.textContent = "Failed";

            }

        };

        header.appendChild(langLabel);
        header.appendChild(button);

        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(header);
        wrapper.appendChild(pre);

    });

}

// ===========================
// Voice Input (speech-to-text)
// ===========================

(function initVoiceInput() {
    const micBtn = document.getElementById("mic-btn");
    const voiceInput = document.getElementById("message");

    if (!micBtn || !voiceInput) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        micBtn.classList.add("unsupported");
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    let listening = false;
    let baseText = "";

    micBtn.addEventListener("click", () => {
        if (listening) {
            recognition.stop();
            return;
        }

        baseText = voiceInput.value ? voiceInput.value + " " : "";

        try {
            recognition.start();
        } catch (err) {
            console.error(err);
        }
    });

    recognition.addEventListener("start", () => {
        listening = true;
        micBtn.classList.add("listening");
    });

    recognition.addEventListener("end", () => {
        listening = false;
        micBtn.classList.remove("listening");
    });

    recognition.addEventListener("error", () => {
        listening = false;
        micBtn.classList.remove("listening");
    });

    recognition.addEventListener("result", (event) => {
        let transcript = "";

        for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }

        voiceInput.value = baseText + transcript;
    });

})();

// ===========================
// Voice Output (text-to-speech)
// ===========================

let voiceOutputEnabled = false;

(function initVoiceOutput() {
    const voiceToggle = document.getElementById("voice-toggle");

    if (!voiceToggle) return;

    if (!("speechSynthesis" in window)) {
        voiceToggle.style.display = "none";
        return;
    }

    voiceOutputEnabled = localStorage.getItem("gremlin_voice_output") === "true";
    voiceToggle.classList.toggle("active", voiceOutputEnabled);

    voiceToggle.addEventListener("click", () => {
        voiceOutputEnabled = !voiceOutputEnabled;
        voiceToggle.classList.toggle("active", voiceOutputEnabled);
        localStorage.setItem("gremlin_voice_output", voiceOutputEnabled);

        if (!voiceOutputEnabled) {
            window.speechSynthesis.cancel();
        }
    });

})();

let cachedMaleVoice = null;

function pickMaleVoice() {
    if (!("speechSynthesis" in window)) return null;

    const voices = window.speechSynthesis.getVoices();
    if (!voices.length) return null;

    const deepMaleNamePatterns = [
        /\bdaniel\b/i,
        /\bgordon\b/i,
        /\barthur\b/i,
        /\bthomas\b/i,
        /\beric\b/i,
        /\bguy\b/i
    ];

    const maleNamePatterns = [
        /\bmale\b/i,
        /\bdavid\b/i,
        /\bmark\b/i,
        /\balex\b/i,
        /\bfred\b/i,
        /\baaron\b/i,
        /\bjames\b/i,
        /\bnathan\b/i
    ];

    let match = voices.find(v =>
        /en/i.test(v.lang) && deepMaleNamePatterns.some(p => p.test(v.name))
    );

    if (!match) {
        match = voices.find(v => deepMaleNamePatterns.some(p => p.test(v.name)));
    }

    if (!match) {
        match = voices.find(v =>
            /en/i.test(v.lang) && maleNamePatterns.some(p => p.test(v.name))
        );
    }

    if (!match) {
        match = voices.find(v => maleNamePatterns.some(p => p.test(v.name)));
    }

    if (!match) {
        match = voices.find(v => /en/i.test(v.lang) && !/female|woman|zira|samantha|susan|karen|victoria|moira|tessa/i.test(v.name));
    }

    return match || null;
}

if ("speechSynthesis" in window) {
    window.speechSynthesis.onvoiceschanged = () => {
        cachedMaleVoice = pickMaleVoice();
    };
    cachedMaleVoice = pickMaleVoice();
}

function speakText(text) {
    if (!voiceOutputEnabled || !("speechSynthesis" in window)) return;

    const clean = text
        .replace(/```[\s\S]*?```/g, "")
        .replace(/`[^`]*`/g, "")
        .replace(/\$\$[\s\S]*?\$\$/g, "")
        .replace(/\$[^$]*\$/g, "")
        .replace(/[*_#>]/g, "")
        .trim();

    if (!clean) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = 0.95;
    utterance.pitch = 0.75;

    const voice = cachedMaleVoice || pickMaleVoice();
    if (voice) {
        utterance.voice = voice;
    }

    window.speechSynthesis.speak(utterance);
}

// ===========================
// Init — restore chats on load
// ===========================

(async function init() {
    enhanceCodeBlocks();

    const conversations = await loadConversations(null);

    if (conversations && conversations.length > 0) {
        await loadConversation(conversations[0].id);
    }
})();
