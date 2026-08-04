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

        input.value = "";

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

if (messageInput) {

    messageInput.addEventListener("keydown", (e) => {

        if (e.key === "Enter" && !e.shiftKey) {

            e.preventDefault();
            sendMessage();

        }

    });

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

            item.textContent = conv.title || "New chat";

            item.addEventListener("click", () => loadConversation(conv.id));

            chatList.appendChild(item);
        });

        return conversations;

    } catch (err) {
        console.error(err);
        return [];
    }
}

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
// Init — restore chats on load
// ===========================

(async function init() {
    enhanceCodeBlocks();

    const conversations = await loadConversations(null);

    if (conversations && conversations.length > 0) {
        await loadConversation(conversations[0].id);
    }
})();
