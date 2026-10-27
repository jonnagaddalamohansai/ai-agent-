/* Agent Desk uses same-origin APIs and stores conversation history in this browser. */
(() => {
  'use strict';

  const STORAGE_KEY = 'agent-desk.chats.v1';
  const MAX_CHATS = 40;
  const $ = (id) => document.getElementById(id);
  const elements = Object.fromEntries([
    'history', 'history-count', 'welcome', 'messages', 'prompt', 'chat-form',
    'send-button', 'stop-button', 'mode-badge', 'mode-label', 'mode-notice',
    'error-notice', 'error-text', 'retry-button', 'dismiss-error',
    'conversation-title', 'chat-scroll', 'sidebar', 'sidebar-backdrop', 'menu-button',
  ].map((id) => [id, $(id)]));

  let chats = loadChats();
  let activeId = null;
  let config = null;
  let currentRequest = null;
  let pendingMessage = null;
  let retryAction = null;
  let storageWarningShown = false;
  const mobileLayout = window.matchMedia('(max-width: 760px)');

  function makeId() {
    return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }

  function loadChats() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      if (!Array.isArray(parsed)) return [];
      return parsed.filter((chat) => chat && typeof chat.id === 'string' && Array.isArray(chat.messages))
        .slice(0, MAX_CHATS).map((chat) => ({
          id: chat.id,
          title: typeof chat.title === 'string' ? chat.title.slice(0, 80) : 'Conversation',
          updatedAt: typeof chat.updatedAt === 'number' ? chat.updatedAt : 0,
          messages: chat.messages.filter((message) => message && ['user', 'assistant'].includes(message.role) && typeof message.content === 'string')
            .slice(-100).map((message) => ({
              role: message.role,
              content: message.content.slice(0, 30000),
              mode: message.mode === 'live' ? 'live' : 'demo',
              tool_calls: Array.isArray(message.tool_calls) ? message.tool_calls.filter((tool) => tool && typeof tool.name === 'string' && typeof tool.result === 'string').slice(0, 12) : [],
            })),
        }));
    } catch {
      return [];
    }
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(chats.slice(0, MAX_CHATS)));
    } catch {
      if (!storageWarningShown) {
        storageWarningShown = true;
        showError('Your browser could not save this conversation. You can keep chatting, but this history may disappear when you leave.');
      }
    }
  }

  function currentChat() {
    return chats.find((chat) => chat.id === activeId);
  }

  function showError(message, retry = null) {
    elements['error-text'].textContent = message;
    elements['error-notice'].hidden = false;
    retryAction = retry;
    elements['retry-button'].hidden = !retry;
  }

  function hideError() {
    elements['error-notice'].hidden = true;
    retryAction = null;
  }

  function setSidebar(open) {
    open = open && mobileLayout.matches;
    elements.sidebar.classList.toggle('open', open);
    elements['sidebar-backdrop'].hidden = !open;
    elements['menu-button'].setAttribute('aria-expanded', String(open));
    elements.sidebar.inert = mobileLayout.matches && !open;
    document.querySelector('.workspace').inert = open;
    if (open) $('new-chat').focus();
  }

  function cancelRequest() {
    if (currentRequest) currentRequest.abort();
    currentRequest = null;
    pendingMessage = null;
    updateComposer();
  }

  function openChat(id = null) {
    cancelRequest();
    activeId = id;
    hideError();
    elements.prompt.value = '';
    resizePrompt();
    setSidebar(false);
    render();
    elements.prompt.focus();
  }

  function renderHistory() {
    elements.history.replaceChildren();
    elements['history-count'].textContent = String(chats.length);
    if (!chats.length) {
      const empty = document.createElement('p');
      empty.className = 'history-empty';
      empty.textContent = 'Your next good idea starts here. Start a conversation to save it.';
      elements.history.append(empty);
      return;
    }
    for (const chat of chats) {
      const row = document.createElement('div');
      row.className = `history-item${chat.id === activeId ? ' active' : ''}`;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'history-open';
      button.textContent = chat.title;
      button.title = chat.title;
      if (chat.id === activeId) button.setAttribute('aria-current', 'page');
      button.addEventListener('click', () => openChat(chat.id));
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'history-delete';
      remove.textContent = '×';
      remove.setAttribute('aria-label', `Delete conversation: ${chat.title}`);
      remove.addEventListener('click', () => {
        const wasActive = chat.id === activeId;
        if (wasActive) cancelRequest();
        chats = chats.filter((item) => item.id !== chat.id);
        persist();
        if (wasActive) openChat();
        else renderHistory();
      });
      row.append(button, remove);
      elements.history.append(row);
    }
  }

  function appendText(container, content) {
    // Fenced code gets a readable block; all content stays inert text.
    const segments = content.split(/(```[\s\S]*?```)/g);
    for (const segment of segments) {
      if (!segment) continue;
      if (segment.startsWith('```') && segment.endsWith('```')) {
        const pre = document.createElement('pre');
        const code = document.createElement('code');
        code.textContent = segment.slice(3, -3).replace(/^[a-z0-9_+-]*\n/i, '').replace(/\n$/, '');
        pre.append(code);
        container.append(pre);
      } else {
        const text = document.createElement('span');
        text.textContent = segment;
        container.append(text);
      }
    }
  }

  function messageElement(message, pending = false) {
    const article = document.createElement('article');
    article.className = `message ${message.role}`;
    const avatar = document.createElement('span');
    avatar.className = 'message-avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.textContent = message.role === 'user' ? 'YOU' : '✳';
    const body = document.createElement('div');
    body.className = 'message-body';
    const label = document.createElement('div');
    label.className = 'message-label';
    label.textContent = message.role === 'user' ? 'You' : 'Agent Desk';
    if (message.role === 'assistant' && message.mode === 'demo') {
      const demo = document.createElement('span');
      demo.className = 'demo-tag';
      demo.textContent = 'DEMO';
      label.append(demo);
    }
    body.append(label);
    if (pending) {
      const thinking = document.createElement('div');
      thinking.className = 'thinking';
      thinking.setAttribute('role', 'status');
      thinking.setAttribute('aria-label', 'Agent Desk is thinking');
      for (let index = 0; index < 3; index += 1) thinking.append(document.createElement('span'));
      body.append(thinking);
    } else {
      const text = document.createElement('div');
      text.className = 'message-text';
      appendText(text, message.content);
      body.append(text);
      if (message.tool_calls?.length) {
        const details = document.createElement('details');
        details.className = 'tool-details';
        const summary = document.createElement('summary');
        summary.textContent = `${message.tool_calls.length} tool ${message.tool_calls.length === 1 ? 'used' : 'calls'} · View results`;
        details.append(summary);
        for (const tool of message.tool_calls) {
          const entry = document.createElement('div');
          entry.className = 'tool-entry';
          const name = document.createElement('span');
          name.className = 'tool-name';
          name.textContent = tool.name;
          const result = document.createElement('span');
          result.textContent = tool.result;
          entry.append(name, result);
          details.append(entry);
        }
        body.append(details);
      }
    }
    article.append(avatar, body);
    return article;
  }

  function renderMessages() {
    const chat = currentChat();
    const messages = chat?.messages || [];
    elements.welcome.hidden = messages.length > 0;
    elements.messages.hidden = messages.length === 0;
    elements.messages.replaceChildren(...messages.map((message) => messageElement(message)));
    if (pendingMessage && currentRequest) elements.messages.append(messageElement({ role: 'assistant', mode: config?.mode }, true));
    elements['conversation-title'].textContent = chat?.title || 'New conversation';
    requestAnimationFrame(() => {
      elements['chat-scroll'].scrollTop = elements['chat-scroll'].scrollHeight;
    });
  }

  function updateComposer() {
    const busy = Boolean(currentRequest);
    elements['send-button'].hidden = busy;
    elements['stop-button'].hidden = !busy;
    elements['send-button'].disabled = busy || !config || !elements.prompt.value.trim();
    elements.prompt.readOnly = busy;
    elements['chat-form'].setAttribute('aria-busy', String(busy));
  }

  function render() {
    renderHistory();
    renderMessages();
    updateComposer();
  }

  function resizePrompt() {
    elements.prompt.style.height = 'auto';
    elements.prompt.style.height = `${Math.min(elements.prompt.scrollHeight, 180)}px`;
    updateComposer();
  }

  function requestMessages(chat) {
    const selected = [];
    let characters = 0;
    for (let index = chat.messages.length - 1; index >= 0 && selected.length < 30; index -= 1) {
      const message = chat.messages[index];
      const content = message.content.slice(0, 12000);
      if (characters + content.length > 60000) break;
      selected.unshift({ role: message.role, content });
      characters += content.length;
    }
    return selected;
  }

  async function sendChat(chat) {
    if (currentRequest || !chat || activeId !== chat.id) return;
    hideError();
    const controller = new AbortController();
    currentRequest = controller;
    pendingMessage = chat.id;
    render();
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: requestMessages(chat) }),
        signal: controller.signal,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : `The request failed (${response.status}). Please try again.`);
      if (typeof payload.reply !== 'string' || !payload.reply.trim()) throw new Error('The assistant returned an empty response. Please try again.');
      if (controller.signal.aborted || currentRequest !== controller || activeId !== chat.id) return;
      chat.messages.push({ role: 'assistant', content: payload.reply, mode: payload.mode, tool_calls: payload.tool_calls || [] });
      chat.updatedAt = Date.now();
      persist();
    } catch (error) {
      if (error.name !== 'AbortError' && currentRequest === controller && activeId === chat.id) {
        showError(error.message === 'Failed to fetch' ? 'Could not reach the server. Check your connection and try again.' : error.message, () => sendChat(chat));
      }
    } finally {
      if (currentRequest === controller) {
        currentRequest = null;
        pendingMessage = null;
        render();
        elements.prompt.focus();
      }
    }
  }

  function submitMessage(event) {
    event.preventDefault();
    const content = elements.prompt.value.trim();
    if (!content || currentRequest || !config) return;
    let chat = currentChat();
    if (!chat) {
      chat = { id: makeId(), title: content.replace(/\s+/g, ' ').slice(0, 60), updatedAt: Date.now(), messages: [] };
      chats.unshift(chat);
      chats = chats.slice(0, MAX_CHATS);
      activeId = chat.id;
    } else {
      chats = [chat, ...chats.filter((item) => item.id !== chat.id)];
    }
    chat.messages.push({ role: 'user', content });
    chat.updatedAt = Date.now();
    elements.prompt.value = '';
    resizePrompt();
    persist();
    sendChat(chat);
  }

  async function loadConfig() {
    elements['mode-label'].textContent = 'Connecting…';
    try {
      const response = await fetch('/api/config');
      if (!response.ok) throw new Error('The server is not ready yet. Please try again.');
      const data = await response.json();
      if (!['demo', 'live'].includes(data.mode)) throw new Error('The server returned an invalid configuration.');
      config = data;
      elements['mode-badge'].className = `mode-badge ${data.mode}`;
      elements['mode-label'].textContent = data.mode === 'live' ? 'Live AI mode' : 'Local demo';
      elements['mode-notice'].textContent = data.mode === 'live'
        ? `Using ${data.model}. Your messages are sent to the configured AI provider.`
        : 'Demo mode · Local sample replies and built-in tools. Configure a server API key to enable AI conversation.';
      hideError();
    } catch (error) {
      config = null;
      elements['mode-badge'].className = 'mode-badge offline';
      elements['mode-label'].textContent = 'Disconnected';
      elements['mode-notice'].textContent = 'Your assistant is temporarily unavailable. Saved conversations are still here.';
      showError(error.message === 'Failed to fetch' ? 'Could not connect to the server.' : error.message, loadConfig);
    }
    updateComposer();
  }

  elements['chat-form'].addEventListener('submit', submitMessage);
  elements.prompt.addEventListener('input', resizePrompt);
  elements.prompt.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      submitMessage(event);
    }
  });
  $('new-chat').addEventListener('click', () => openChat());
  elements['stop-button'].addEventListener('click', () => {
    cancelRequest();
    renderMessages();
    elements.prompt.focus();
  });
  elements['dismiss-error'].addEventListener('click', hideError);
  elements['retry-button'].addEventListener('click', () => retryAction?.());
  elements['menu-button'].addEventListener('click', () => setSidebar(!elements.sidebar.classList.contains('open')));
  elements['sidebar-backdrop'].addEventListener('click', () => {
    setSidebar(false);
    elements['menu-button'].focus();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && elements.sidebar.classList.contains('open')) {
      setSidebar(false);
      elements['menu-button'].focus();
    }
    if (event.key === 'Tab' && elements.sidebar.classList.contains('open')) {
      const focusable = elements.sidebar.querySelectorAll('a[href], button');
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
  mobileLayout.addEventListener('change', () => setSidebar(false));
  document.querySelectorAll('[data-prompt]').forEach((button) => {
    button.addEventListener('click', () => {
      if (currentRequest) return;
      elements.prompt.value = button.dataset.prompt;
      resizePrompt();
      elements.prompt.focus();
    });
  });

  setSidebar(false);
  render();
  loadConfig();
})();
