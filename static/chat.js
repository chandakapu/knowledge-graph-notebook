function switchPanelTab(tab) {
  const chatBtn    = document.getElementById('panelTabChatBtn');
  const uploadBtn  = document.getElementById('panelTabUploadBtn');
  const chatPanel  = document.getElementById('panelChat');
  const uploadPanel= document.getElementById('panelUpload');

  const activeClass   = 'flex-1 h-14 flex items-center justify-center gap-1.5 border-b-2 border-primary text-primary font-label-md text-label-md font-bold transition-all text-[13px]';
  const inactiveClass = 'flex-1 h-14 flex items-center justify-center gap-1.5 border-b-2 border-transparent text-on-surface-variant hover:text-primary font-label-md text-label-md font-semibold transition-all text-[13px]';

  if (tab === 'chat') {
    chatBtn.className    = activeClass;
    uploadBtn.className  = inactiveClass;
    chatPanel.style.display  = '';
    uploadPanel.style.display = 'none';
  } else {
    uploadBtn.className  = activeClass;
    chatBtn.className    = inactiveClass;
    chatPanel.style.display  = 'none';
    uploadPanel.style.display = '';
  }
}

async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const question = (input.value || '').trim();
  if (!question) return;

  input.value = '';
  const history = document.getElementById('chatHistory');

  // User bubble
  const userHtml = `
    <div class="flex flex-col items-end gap-1">
      <span class="text-[10px] text-on-surface-variant mr-1">Just now</span>
      <div class="bg-primary text-white px-4 py-3 rounded-2xl rounded-tr-none text-[13px] shadow-md shadow-primary/10 max-w-[90%] leading-relaxed">
        ${escapeHtml(question)}
      </div>
    </div>`;
  history.insertAdjacentHTML('beforeend', userHtml);
  history.scrollTop = history.scrollHeight;

  // Thinking bubble
  const thinkId = 'think-' + Date.now();
  const thinkHtml = `
    <div class="flex gap-3" id="${thinkId}">
      <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-electric-purple flex items-center justify-center flex-shrink-0 shadow shadow-primary/20">
        <span class="material-symbols-outlined text-white text-sm animate-pulse" style="font-variation-settings:'FILL' 1">smart_toy</span>
      </div>
      <div class="bg-surface-container-low border border-surface-container px-4 py-3 rounded-2xl rounded-tl-none text-[13px] text-on-surface-variant shadow-sm flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"></span>
        <span class="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style="animation-delay:0.15s"></span>
        <span class="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style="animation-delay:0.3s"></span>
      </div>
    </div>`;
  history.insertAdjacentHTML('beforeend', thinkHtml);
  history.scrollTop = history.scrollHeight;

  document.getElementById('chatSpinner').style.display = 'block';
  document.getElementById('chatSendBtn').disabled = true;
  document.getElementById('chatInput').disabled = true;

  // Collect graph context
  const nodes = [];
  globalNodes.forEach(n => nodes.push({ name: n.label, type: n.nodeType, description: n.description }));
  const edges = [];
  globalEdges.forEach(e => {
    const s = globalNodes.get(e.from);
    const t = globalNodes.get(e.to);
    edges.push({ source: s ? s.label : e.from, relation: e.label, target: t ? t.label : e.to });
  });

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, nodes, edges })
    });
    const data = await resp.json();

    // Remove thinking bubble
    document.getElementById(thinkId)?.remove();

    const answer = data.answer || 'Sorry, I could not generate a response.';
    const relatedNodes = data.related_nodes || [];

    // Format markdown-ish bold (**text**) — escape HTML first to prevent XSS
    const escaped = escapeHtml(answer);
    const formatted = escaped
      .replace(/\*\*(.+?)\*\*/g, '<span class="font-bold text-primary">$1</span>')
      .replace(/\n/g, '<br>');

    // Related nodes chips
    const chipsHtml = relatedNodes.length
      ? `<div class="flex flex-wrap gap-1 mt-2 pt-2 border-t border-surface-container">
          ${relatedNodes.slice(0,5).map(n => `<span class="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-bold rounded-full">${escapeHtml(n)}</span>`).join('')}
         </div>`
      : '';

    const answerHtml = `
      <div class="flex gap-3">
        <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-electric-purple flex items-center justify-center flex-shrink-0 shadow shadow-primary/20">
          <span class="material-symbols-outlined text-white text-sm" style="font-variation-settings:'FILL' 1">smart_toy</span>
        </div>
        <div class="bg-surface-container-low border border-surface-container p-4 rounded-2xl rounded-tl-none text-[13px] shadow-sm text-on-surface flex-grow">
          <p class="text-primary font-bold mb-2 text-[11px] uppercase tracking-wider">langextract AI</p>
          <p class="leading-relaxed">${formatted}</p>
          ${chipsHtml}
        </div>
      </div>`;
    history.insertAdjacentHTML('beforeend', answerHtml);

  } catch (err) {
    document.getElementById(thinkId)?.remove();
    console.error('[chat]', err);
    history.insertAdjacentHTML('beforeend', `
      <div class="flex gap-3">
        <div class="w-8 h-8 rounded-xl bg-error/10 flex items-center justify-center flex-shrink-0">
          <span class="material-symbols-outlined text-error text-sm">error</span>
        </div>
        <div class="bg-error/5 border border-error/20 px-4 py-3 rounded-2xl text-[13px] text-error">
          Failed to get a response. Check your connection.
        </div>
      </div>`);
  } finally {
    document.getElementById('chatSpinner').style.display = 'none';
    document.getElementById('chatSendBtn').disabled = false;
    document.getElementById('chatInput').disabled = false;
    document.getElementById('chatInput').focus();
    history.scrollTop = history.scrollHeight;
  }
}
