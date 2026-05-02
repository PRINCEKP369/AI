(function () {
  let selectedModel = localStorage.getItem("localai_selected_model") || "model1";
  let usageState = { used: 0 };

  const api = {
    async get(path) {
      const res = await fetch(path, { credentials: "same-origin" });
      if (!res.ok) throw new Error(`http_${res.status}`);
      return res.json();
    },
    async post(path, body = {}) {
      const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`http_${res.status}`);
      return res.status === 204 ? null : res.json();
    },
    async del(path) {
      const res = await fetch(path, { method: "DELETE", credentials: "same-origin" });
      if (!res.ok) throw new Error(`http_${res.status}`);
    },
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function estimateTokens(text) {
    if (!text) return 0;
    return Math.max(1, Math.ceil(String(text).length / 4));
  }

  function formatTokenCount(value) {
    if (value >= 1000) return `${Math.round(value / 1000)}k`;
    return String(value);
  }

  function setUsageDisplay(usage) {
    usageState = { ...usageState, ...usage };
    const text = document.getElementById("usage-text");
    if (text) text.textContent = `${formatTokenCount(usageState.used)} tokens used`;
  }

  async function refreshUsage() {
    try {
      setUsageDisplay(await api.get("/api/usage"));
    } catch (_) {}
  }

  saveToStorage = window.saveToStorage = function saveToStorage() {
    // Server-backed mode: history is persisted through API calls.
  };

  loadFromStorage = window.loadFromStorage = function loadFromStorage() {
    return false;
  };

  renderHistory = window.renderHistory = function renderHistory() {
    const container = document.getElementById("chat-history");
    container.innerHTML = "";
    Object.entries(conversations).forEach(([id, conv]) => {
      const item = document.createElement("div");
      item.className = "history-item" + (id == currentId ? " active" : "");

      const title = document.createElement("span");
      title.className = "history-title";
      title.textContent = conv.title || "New conversation";

      const del = document.createElement("button");
      del.className = "history-del";
      del.title = "Delete";
      del.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>';
      del.addEventListener("click", (event) => deleteChat(event, id));

      item.append(title, del);
      item.addEventListener("click", () => {
        currentId = id;
        renderHistory();
        renderMessages();
      });
      container.appendChild(item);
    });
  };

  newChat = window.newChat = async function newChat() {
    try {
      const conv = await api.post("/api/conversations", { title: "New conversation" });
      conversations = { [conv.id]: conv, ...conversations };
      currentId = conv.id;
      renderHistory();
      renderMessages();
    } catch (error) {
      showError("Could not create a new conversation.");
    }
  };

  clearChat = window.clearChat = async function clearChat() {
    if (!currentId) return;
    try {
      await api.post(`/api/conversations/${currentId}/clear`);
      conversations[currentId].messages = [];
      renderMessages();
    } catch (error) {
      showError("Could not clear this conversation.");
    }
  };

  deleteChat = window.deleteChat = async function deleteChat(event, id) {
    event.stopPropagation();
    try {
      await api.del(`/api/conversations/${id}`);
      delete conversations[id];
      if (String(currentId) === String(id)) currentId = Object.keys(conversations)[0] || null;
      if (!currentId) {
        await newChat();
        return;
      }
      renderHistory();
      renderMessages();
    } catch (error) {
      showError("Could not delete this conversation.");
    }
  };

  sendMessage = window.sendMessage = async function sendMessage() {
    const text = textarea.value.trim();
    const attachments = [...pendingFiles];
    if (!text && attachments.length === 0) return;
    if (isGenerating) return;

    pendingFiles = [];
    renderFilePreviews();

    if (!currentId) {
      const conv = await api.post("/api/conversations", {
        title: (text || attachments[0]?.name || "Attachment").slice(0, 40),
      });
      conversations = { [conv.id]: conv, ...conversations };
      currentId = conv.id;
      renderHistory();
    }

    const conv = conversations[currentId];
    const apiContent = buildApiContent(text, attachments);
    const storedContent = buildStoredUserContent(text, apiContent, attachments);
    conv.messages.push({ role: "user", content: storedContent });
    if (conv.messages.length === 1) conv.title = (text || attachments[0]?.name || "Attachment").slice(0, 40) + "...";

    const { bubbleEl: userBubble } = appendMessageDOM("user", "");
    userBubble.innerHTML = renderAttachments(attachments) + (text ? `<span>${escapeHtml(text)}</span>` : "");
    scrollToBottom(true);

    textarea.value = "";
    textarea.style.height = "auto";
    isGenerating = true;
    setStopMode();

    const msgContainer = document.getElementById("messages");
    const typingRow = document.createElement("div");
    typingRow.className = "message-row ai";
    typingRow.id = "typing-indicator";
    typingRow.innerHTML = '<div class="msg-avatar ai">AI</div><div class="msg-content"><div class="msg-name">Local Model</div><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>';
    msgContainer.appendChild(typingRow);
    scrollToBottom(true);

    abortController = new AbortController();
    let typingRowRemoved = false;

    try {
      const apiMessages = conv.messages.map((m) => ({ role: m.role, content: contentToString(m.content) }));
      const liveUsageBase = usageState.used;
      const liveInputTokens = estimateTokens(JSON.stringify(apiMessages));
      setUsageDisplay({ used: liveUsageBase + liveInputTokens });
      const res = await fetch("/api/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        signal: abortController.signal,
        body: JSON.stringify({
          conversation_id: currentId,
          model: selectedModel,
          user_content: storedContent,
          messages: apiMessages,
        }),
      });
      if (!res.ok) {
        let message = `Server returned error ${res.status}.`;
        try {
          const data = await res.json();
          if (data.error) message = data.error;
        } catch (_) {}
        throw new Error(message);
      }

      typingRow.remove();
      typingRowRemoved = true;
      const { bubbleEl } = appendMessageDOM("assistant", "");
      scrollToBottom(true);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullReply = "";
      let buffer = "";

      outer: while (true) {
        let done;
        let value;
        try {
          ({ done, value } = await reader.read());
        } catch (error) {
          break;
        }
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data:")) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (jsonStr === "[DONE]") break outer;
          try {
            const chunk = JSON.parse(jsonStr);
            if (chunk.error) throw new Error(chunk.error);
            const delta = chunk.choices?.[0]?.delta?.content;
            if (delta) {
              fullReply += delta;
              setUsageDisplay({ used: liveUsageBase + liveInputTokens + estimateTokens(fullReply) });
              bubbleEl.innerHTML = formatMessage(fullReply);
              scrollToBottom();
            }
          } catch (error) {
            if (error.message) throw error;
          }
        }
      }

      if (fullReply) {
        conv.messages.push({ role: "assistant", content: fullReply });
        renderHistory();
      }
      await refreshUsage();
    } catch (err) {
      if (err.name !== "AbortError") {
        if (!typingRowRemoved) typingRow.remove();
        await refreshUsage();
        showError(err.message || "Could not reach llama.cpp through Flask. Check both servers.");
        conv.messages.pop();
      } else if (!typingRowRemoved) {
        typingRow.remove();
      }
    }

    isGenerating = false;
    abortController = null;
    setSendMode();
  };

  async function bootServerBackedChat() {
    try {
      const user = await api.get("/api/me");
      const modelData = await api.get("/api/models");
      await refreshUsage();
      const select = document.getElementById("model-select");
      if (select) {
        select.innerHTML = "";
        modelData.models.forEach((model) => {
          const option = document.createElement("option");
          option.value = model.id;
          option.textContent = model.name;
          select.appendChild(option);
        });
        if (!modelData.models.some((model) => model.id === selectedModel)) {
          selectedModel = modelData.default || modelData.models[0]?.id || "model1";
        }
        select.value = selectedModel;
        select.addEventListener("change", () => {
          selectedModel = select.value;
          localStorage.setItem("localai_selected_model", selectedModel);
        });
      }
      const avatar = document.querySelector(".avatar");
      const footerName = document.querySelector(".footer-name");
      if (avatar) avatar.textContent = user.username.slice(0, 1).toUpperCase();
      if (footerName) footerName.textContent = user.username;

      const data = await api.get("/api/conversations");
      conversations = {};
      data.conversations.forEach((conv) => {
        conversations[conv.id] = {
          title: conv.title,
          messages: conv.messages.map((message) => ({
            role: message.role,
            content: message.content,
          })),
        };
      });
      currentId = Object.keys(conversations)[0] || null;
      if (!currentId) {
        await newChat();
        return;
      }
      renderHistory();
      renderMessages();
    } catch (error) {
      showError("Could not load your saved chats.");
    }
  }

  bootServerBackedChat();
})();
