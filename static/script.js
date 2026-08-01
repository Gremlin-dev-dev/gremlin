let history = [];

function scrollBottom() {
    const chatBox = document.getElementById("chat-box");
    chatBox.scrollTop = chatBox.scrollHeight;
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

async function sendMessage() {

    const input = document.getElementById("message");
    const imageInput = document.getElementById("image");
    const chatBox = document.getElementById("chat-box");
    const attachBtn = document.querySelector(".attach-btn");

    const message = input.value.trim();

    if (!message && imageInput.files.length === 0) {
        return;
    }

    history.push({
        role: "user",
        text: message
    });

    const userMessage = document.createElement("div");
    userMessage.className = "user-msg";

    const safe = document.createElement("div");
    safe.textContent = message;

    userMessage.innerHTML = `
        <span class="msg-label">You</span>
        <div class="msg-content">${safe.innerHTML}</div>
    `;

    if (imageInput.files.length) {

        const file = imageInput.files[0];

        const img = document.createElement("img");
        img.className = "uploaded-image";
        img.src = URL.createObjectURL(file);

        img.onclick = () => {

            const modal = document.getElementById("image-modal");
            const modalImg = document.getElementById("modal-image");

            if (modal && modalImg) {
                modalImg.src = img.src;
                modal.style.display = "flex";
            }

        };

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

        formData.append(
            "history",
            JSON.stringify(history)
        );

        if (imageInput.files.length) {
            formData.append(
                "image",
                imageInput.files[0]
            );
        }

        const response = await fetch("/chat", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(response.status);
        }

        const data = await response.json();

        history.push({
            role: "assistant",
            text: data.reply
        });

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

    } catch (err) {

        console.error(err);

        thinking.remove();

        chatBox.innerHTML += `
            <div class="bot-msg">
                <span class="msg-label">GREMLIN</span>
                <div class="msg-content">⚠️ ${err.message}</div>
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

const newChatBtn = document.getElementById("new-chat");

if (newChatBtn) {

    newChatBtn.addEventListener("click", () => {

        if (history.length) {

            const firstUser = history.find(m => m.role === "user");

            if (firstUser) {

                const item = document.createElement("div");

                item.className = "chat-item";

                item.textContent =
                    firstUser.text.length > 30
                        ? firstUser.text.substring(0, 30) + "..."
                        : firstUser.text;

                document.getElementById("chat-list").prepend(item);

            }

        }

        history = [];

        document.getElementById("chat-box").innerHTML = "";

        messageInput.focus();

    });

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

// Run once on page load
enhanceCodeBlocks();
