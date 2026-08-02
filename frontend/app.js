/**
 * Lenny Growth Assistant — Frontend Application
 * Handles: SSE streaming, session management, skill selection, artifact rendering
 */

const API_BASE = 'http://localhost:8000/api/v1';

// ─────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────
let state = {
  sessionId: null,
  provider: 'ollama',
  model: 'qwen2.5:7b',
  skill: null,
  isStreaming: false,
  sessions: [],
  currentArtifact: null,
  currentArtifactType: null,
};

// ─────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  loadSessions();
  checkRagStatus();
  initInput();
});

function initInput() {
  const input = document.getElementById('message-input');
  input.addEventListener('input', () => {
    const hasText = input.value.trim().length > 0;
    document.getElementById('send-btn').disabled = !hasText || state.isStreaming;
  });
}

// ─────────────────────────────────────────────────────────────
// Provider & Skill Selection
// ─────────────────────────────────────────────────────────────
function setProvider(name) {
  state.provider = name;
  document.querySelectorAll('.provider-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById(`provider-${name}`).classList.add('active');

  const modelInput = document.getElementById('model-input');
  if (name === 'anthropic') {
    modelInput.value = 'claude-3-5-haiku-20241022';
    state.model = 'claude-3-5-haiku-20241022';
  } else {
    modelInput.value = 'qwen2.5:7b';
    state.model = 'qwen2.5:7b';
  }
  showToast(`Switched to ${name === 'anthropic' ? 'Anthropic Claude' : 'Ollama (Local)'}`, 'success');
}

function setSkill(skill) {
  state.skill = skill;
  document.querySelectorAll('.skill-btn').forEach(btn => btn.classList.remove('active'));
  const btnId = skill ? `skill-${skill}` : 'skill-auto';
  document.getElementById(btnId)?.classList.add('active');

  const labels = {
    null: '🧠 Auto-detecting skill',
    'qa': '🔍 Q&A — Grounded in transcripts',
    'ship30': '✍️ Ship30for30 Essay',
    'artifact': '🎨 Artifact Generator',
  };
  document.getElementById('current-skill-label').textContent = labels[skill] || '🧠 Auto-detecting skill';
}

// ─────────────────────────────────────────────────────────────
// Sessions Management
// ─────────────────────────────────────────────────────────────
async function loadSessions() {
  try {
    const res = await fetch(`${API_BASE}/sessions/?limit=30`);
    if (!res.ok) return;
    const data = await res.json();
    state.sessions = data.sessions || [];
    renderSessions();
  } catch (e) {
    console.warn('Failed to load sessions:', e);
  }
}

function renderSessions() {
  const container = document.getElementById('sessions-list');
  const countBadge = document.getElementById('session-count-badge');
  if (countBadge) countBadge.textContent = state.sessions.length;

  if (!state.sessions.length) {
    container.innerHTML = '<div class="sessions-empty">No chats yet. Start a new conversation!</div>';
    return;
  }
  container.innerHTML = state.sessions.map(session => `
    <div class="session-item ${session.id === state.sessionId ? 'active' : ''}"
         onclick="loadSession('${session.id}')">
      <div class="session-dot"></div>
      <span class="session-title" title="${escapeHtml(session.title)}">${escapeHtml(session.title)}</span>
      <button class="session-delete" onclick="deleteSession(event, '${session.id}')" title="Delete">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
  `).join('');
}

async function loadSession(sessionId) {
  state.sessionId = sessionId;
  renderSessions();
  clearArtifact();

  try {
    const res = await fetch(`${API_BASE}/chat/${sessionId}/history`);
    if (!res.ok) return;
    const data = await res.json();

    hideWelcome();
    const messagesEl = document.getElementById('messages');
    messagesEl.innerHTML = '';

    for (const msg of data.messages) {
      if (msg.role === 'user') {
        appendUserMessage(msg.content);
      } else if (msg.role === 'assistant') {
        appendAssistantMessage(msg.content, msg.skill_used, msg.artifact_type, msg.artifact_content);
      }
    }

    // Load title
    const session = state.sessions.find(s => s.id === sessionId);
    if (session) {
      document.getElementById('chat-title').textContent = session.title;
    }

    scrollToBottom();
  } catch (e) {
    console.error('Failed to load session:', e);
  }
}

function newChat() {
  state.sessionId = null;
  document.getElementById('messages').innerHTML = '';
  document.getElementById('welcome-screen').style.display = '';
  document.getElementById('chat-title').textContent = 'Lenny Growth Assistant';
  document.getElementById('skill-badge').style.display = 'none';
  clearArtifact();
  renderSessions();
  document.getElementById('message-input').focus();
}

async function deleteSession(e, sessionId) {
  e.stopPropagation();
  try {
    await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
    if (state.sessionId === sessionId) {
      newChat();
    }
    state.sessions = state.sessions.filter(s => s.id !== sessionId);
    renderSessions();
    showToast('Chat deleted', 'success');
  } catch (e) {
    showToast('Failed to delete chat', 'error');
  }
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

// ─────────────────────────────────────────────────────────────
// Sending Messages
// ─────────────────────────────────────────────────────────────
function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!state.isStreaming) sendMessage();
  }
}

function sendStarterPrompt(text) {
  document.getElementById('message-input').value = text;
  sendMessage();
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  document.getElementById('send-btn').disabled = !el.value.trim() || state.isStreaming;
}

async function sendMessage() {
  const input = document.getElementById('message-input');
  const message = input.value.trim();
  if (!message || state.isStreaming) return;

  // Get current model from input
  const modelInput = document.getElementById('model-input');
  state.model = modelInput.value.trim() || state.model;

  // Clear input
  input.value = '';
  input.style.height = 'auto';
  document.getElementById('send-btn').disabled = true;

  // Hide welcome, show messages
  hideWelcome();

  // Append user message
  appendUserMessage(message);
  scrollToBottom();

  // Show thinking
  const thinkingId = showThinking();
  state.isStreaming = true;

  // Stream response
  try {
    await streamResponse(message, thinkingId);
  } catch (e) {
    removeElement(thinkingId);
    appendErrorMessage('Connection failed: ' + e.message);
  } finally {
    state.isStreaming = false;
    document.getElementById('send-btn').disabled = false;
  }
}

async function streamResponse(message, thinkingId) {
  const body = {
    message,
    session_id: state.sessionId || null,
    provider: state.provider,
    model: state.model,
    skill: state.skill,
    stream: true,
  };

  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let assistantEl = null;
  let fullContent = '';
  let currentSkill = 'chat';
  let currentArtifactType = null;
  let isFirstToken = true;
  let artifactContent = null;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;

        let event;
        try { event = JSON.parse(raw); } catch { continue; }

        if (event.type === 'session') {
          state.sessionId = event.session_id;
          // Refresh sessions list
          loadSessions();
        }

        else if (event.type === 'metadata') {
          currentSkill = event.skill || 'chat';
          currentArtifactType = event.artifact_type;
          updateSkillBadge(currentSkill);
        }

        else if (event.type === 'token') {
          if (isFirstToken) {
            removeElement(thinkingId);
            assistantEl = createAssistantMessageEl();
            isFirstToken = false;
          }
          fullContent += event.content;
          updateStreamingMessage(assistantEl, fullContent);
          scrollToBottom();
        }

        else if (event.type === 'artifact_ready') {
          artifactContent = event.content;
          currentArtifactType = event.artifact_type || currentArtifactType;
          showArtifact(artifactContent, currentArtifactType || 'html');
        }

        else if (event.type === 'title_update') {
          document.getElementById('chat-title').textContent = event.title;
          // Update in sessions list
          const session = state.sessions.find(s => s.id === event.session_id);
          if (session) session.title = event.title;
          renderSessions();
        }

        else if (event.type === 'error') {
          removeElement(thinkingId);
          appendErrorMessage(event.error || 'Unknown error occurred');
        }

        else if (event.type === 'done') {
          // Finalize message
          if (assistantEl) {
            finalizeMessage(assistantEl, fullContent, currentSkill, currentArtifactType, artifactContent);
          }
          if (!state.sessions.find(s => s.id === state.sessionId)) {
            loadSessions();
          }
          break;
        }
      }
    }
  } finally {
    reader.releaseLock();
    removeElement(thinkingId);
  }
}

// ─────────────────────────────────────────────────────────────
// Message Rendering
// ─────────────────────────────────────────────────────────────
function hideWelcome() {
  const welcome = document.getElementById('welcome-screen');
  welcome.style.display = 'none';
}

function appendUserMessage(content) {
  const messages = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'message user';
  div.innerHTML = `
    <div class="message-avatar">U</div>
    <div class="message-body">
      <div class="message-content">${escapeHtml(content)}</div>
    </div>
  `;
  messages.appendChild(div);
}

function appendAssistantMessage(content, skill, artifactType, artifactContent) {
  const messages = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'message assistant';

  const metaHtml = buildMetaHtml(skill, artifactType, artifactContent);

  div.innerHTML = `
    <div class="message-avatar">L</div>
    <div class="message-body">
      <div class="message-content">${renderMarkdown(content)}</div>
      <div class="message-meta">${metaHtml}</div>
    </div>
  `;
  messages.appendChild(div);

  if (artifactContent) {
    // Re-bind show artifact button
    div.querySelector('.view-artifact-btn')?.addEventListener('click', () => {
      showArtifact(artifactContent, artifactType || 'html');
    });
  }
}

function createAssistantMessageEl() {
  const messages = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.innerHTML = `
    <div class="message-avatar">L</div>
    <div class="message-body">
      <div class="message-content streaming"></div>
      <div class="message-meta"></div>
    </div>
  `;
  messages.appendChild(div);
  return div;
}

function updateStreamingMessage(el, content) {
  const contentEl = el.querySelector('.message-content');
  contentEl.innerHTML = renderMarkdown(content) + '<span class="streaming-cursor"></span>';
}

function finalizeMessage(el, content, skill, artifactType, artifactContent) {
  const contentEl = el.querySelector('.message-content');
  contentEl.classList.remove('streaming');
  contentEl.innerHTML = renderMarkdown(content);

  const metaEl = el.querySelector('.message-meta');
  metaEl.innerHTML = buildMetaHtml(skill, artifactType, artifactContent);

  if (artifactContent) {
    metaEl.querySelector('.view-artifact-btn')?.addEventListener('click', () => {
      showArtifact(artifactContent, artifactType || 'html');
    });
  }
}

function buildMetaHtml(skill, artifactType, artifactContent) {
  let html = '';
  if (skill && skill !== 'chat') {
    const labels = { qa: '🔍 Q&A', ship30: '✍️ Ship30', artifact: '🎨 Artifact' };
    html += `<span class="message-skill-badge ${skill}">${labels[skill] || skill}</span>`;
  }
  if (artifactContent) {
    const icon = artifactType === 'html' ? '🌐' : '📄';
    html += `<button class="view-artifact-btn">${icon} View Artifact</button>`;
  }
  return html;
}

function appendErrorMessage(error) {
  const messages = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.innerHTML = `
    <div class="message-avatar" style="background:rgba(239,68,68,0.2)">⚠</div>
    <div class="message-body">
      <div class="message-content" style="border-color:rgba(239,68,68,0.3); color: #f87171;">
        Error: ${escapeHtml(error)}
      </div>
    </div>
  `;
  messages.appendChild(div);
  scrollToBottom();
}

function showThinking() {
  const messages = document.getElementById('messages');
  const id = 'thinking-' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'message assistant';
  div.innerHTML = `
    <div class="message-avatar">L</div>
    <div class="message-body">
      <div class="thinking-dots">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
  messages.appendChild(div);
  scrollToBottom();
  return id;
}

function updateSkillBadge(skill) {
  const badge = document.getElementById('skill-badge');
  const labels = { qa: '🔍 Q&A', ship30: '✍️ Ship30', artifact: '🎨 Artifact', chat: '💬 Chat' };
  if (skill && skill !== 'chat') {
    badge.className = `skill-badge ${skill}`;
    badge.textContent = labels[skill] || skill;
    badge.style.display = '';
  } else {
    badge.style.display = 'none';
  }
}

// ─────────────────────────────────────────────────────────────
// Artifact Panel
// ─────────────────────────────────────────────────────────────
function showArtifact(content, type) {
  state.currentArtifact = content;
  state.currentArtifactType = type;

  const panel = document.getElementById('artifact-panel');
  panel.style.display = 'flex';
  document.getElementById('clear-artifact-btn').style.display = '';

  // Update header
  const icon = type === 'html' ? '🌐' : '📄';
  document.getElementById('artifact-icon').textContent = icon;
  document.getElementById('artifact-label').textContent = type === 'html' ? 'HTML Artifact' : 'Markdown Document';

  // Show/hide open in tab button
  document.getElementById('open-tab-btn').style.display = type === 'html' ? '' : 'none';

  // Render preview (default tab)
  switchArtifactTab('preview');
  document.getElementById('artifact-code').textContent = content;
}

function switchArtifactTab(tab) {
  const iframe = document.getElementById('artifact-iframe');
  const markdown = document.getElementById('artifact-markdown');
  const source = document.getElementById('artifact-source');

  document.querySelectorAll('.artifact-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`tab-${tab}`).classList.add('active');

  if (tab === 'preview') {
    if (state.currentArtifactType === 'html') {
      iframe.style.display = '';
      markdown.style.display = 'none';
      source.style.display = 'none';
      // Write HTML to iframe
      const doc = iframe.contentDocument || iframe.contentWindow.document;
      doc.open();
      doc.write(state.currentArtifact || '');
      doc.close();
    } else {
      // Markdown preview
      iframe.style.display = 'none';
      markdown.style.display = '';
      source.style.display = 'none';
      markdown.innerHTML = renderMarkdown(state.currentArtifact || '');
    }
  } else {
    // Source
    iframe.style.display = 'none';
    markdown.style.display = 'none';
    source.style.display = '';
  }
}

function clearArtifact() {
  state.currentArtifact = null;
  state.currentArtifactType = null;
  document.getElementById('artifact-panel').style.display = 'none';
  document.getElementById('clear-artifact-btn').style.display = 'none';

  // Clear iframe
  const iframe = document.getElementById('artifact-iframe');
  const doc = iframe.contentDocument || iframe.contentWindow.document;
  doc.open(); doc.write(''); doc.close();
}

function copyArtifact() {
  if (!state.currentArtifact) return;
  navigator.clipboard.writeText(state.currentArtifact)
    .then(() => showToast('Copied to clipboard!', 'success'))
    .catch(() => showToast('Copy failed', 'error'));
}

function downloadArtifact() {
  if (!state.currentArtifact) return;
  const ext = state.currentArtifactType === 'html' ? 'html' : 'md';
  const blob = new Blob([state.currentArtifact], { type: ext === 'html' ? 'text/html' : 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `lenny-growth-artifact.${ext}`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Artifact downloaded', 'success');
}

function openInNewTab() {
  if (!state.currentArtifact) return;
  const blob = new Blob([state.currentArtifact], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
}

// ─────────────────────────────────────────────────────────────
// RAG Status
// ─────────────────────────────────────────────────────────────
async function checkRagStatus() {
  try {
    const res = await fetch(`${API_BASE}/rag-status`);
    const data = await res.json();
    const statusEl = document.getElementById('rag-status');
    if (data.loaded && data.chunk_count > 0) {
      statusEl.innerHTML = `
        <div class="status-dot online"></div>
        <span>RAG: ${data.chunk_count.toLocaleString()} chunks</span>
      `;
    } else {
      statusEl.innerHTML = `
        <div class="status-dot" style="background: var(--warning)"></div>
        <span>RAG: Indexing...</span>
      `;
    }
  } catch {
    document.getElementById('rag-status').innerHTML = `
      <div class="status-dot error"></div>
      <span>Backend offline</span>
    `;
  }
}

// ─────────────────────────────────────────────────────────────
// Markdown Renderer
// ─────────────────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return '';
  let html = escapeHtml(text);

  // Code blocks with Header & Copy button
  html = html.replace(/```(\w+)?\n?([\s\S]*?)```/g, (_, lang, code) => {
    const language = lang || 'code';
    return `<div class="code-block-wrapper">
      <div class="code-header">
        <span>${language}</span>
        <button class="code-copy-btn" onclick="copyCodeSnippet(this)">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
        </button>
      </div>
      <pre><code>${code.trim()}</code></pre>
    </div>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold + italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr>');

  // Blockquote
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

  // Unordered list
  html = html.replace(/^[-*•] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]+?<\/li>)/g, '<ul>$1</ul>');
  html = html.replace(/<\/ul>\s*<ul>/g, '');

  // Ordered list
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

  // Paragraphs (double newline)
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';

  // Single newlines inside paragraphs
  html = html.replace(/(?<!>)\n(?![<])/g, '<br>');

  // Clean up empty paragraphs
  html = html.replace(/<p>\s*<\/p>/g, '');
  html = html.replace(/<p>(<div class="code-block-wrapper">)/g, '$1');
  html = html.replace(/(<\/div>)<\/p>/g, '$1');
  html = html.replace(/<p>(<h[1-6]>)/g, '$1');
  html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
  html = html.replace(/<p>(<ul>)/g, '$1');
  html = html.replace(/(<\/ul>)<\/p>/g, '$1');
  html = html.replace(/<p>(<blockquote>)/g, '$1');
  html = html.replace(/(<\/blockquote>)<\/p>/g, '$1');
  html = html.replace(/<p>(<hr>)<\/p>/g, '$1');

  return html;
}

function copyCodeSnippet(btn) {
  const wrapper = btn.closest('.code-block-wrapper');
  const code = wrapper ? wrapper.querySelector('code').textContent : '';
  if (!code) return;
  navigator.clipboard.writeText(code).then(() => {
    btn.innerHTML = `✓ Copied`;
    setTimeout(() => {
      btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy`;
    }, 2000);
  });
}

// ─────────────────────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────────────────────
function scrollToBottom() {
  const container = document.getElementById('messages-container');
  container.scrollTop = container.scrollHeight;
}

function removeElement(id) {
  document.getElementById(id)?.remove();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showToast(message, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}
