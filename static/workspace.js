let networkInstance = null;
let globalNodes = new vis.DataSet();
let globalEdges = new vis.DataSet();
let nodeNames = new Set();
let edgeSignatures = new Set();

let uploadedDocs = [];
let activeDocId = null;
let isClustered = false;

// Handle tab switching
function switchTab(tab) {
  const tabGraphBtn = document.getElementById('tabGraphBtn');
  const tabDocBtn = document.getElementById('tabDocBtn');
  const graphTabContent = document.getElementById('graphTabContent');
  const docTabContent = document.getElementById('docTabContent');
  
  if (tab === 'graph') {
    tabGraphBtn.className = 'h-full border-b-2 border-primary text-primary px-1 font-label-md text-label-md flex items-center gap-2 transition-all font-semibold';
    tabDocBtn.className = 'h-full border-b-2 border-transparent text-on-surface-variant hover:text-primary px-1 font-label-md text-label-md flex items-center gap-2 transition-all font-semibold';
    graphTabContent.style.display = '';
    docTabContent.style.display = 'none';
    if (networkInstance) {
      setTimeout(() => { networkInstance.redraw(); networkInstance.fit(); }, 50);
    }
  } else {
    tabGraphBtn.className = 'h-full border-b-2 border-transparent text-on-surface-variant hover:text-primary px-1 font-label-md text-label-md flex items-center gap-2 transition-all font-semibold';
    tabDocBtn.className = 'h-full border-b-2 border-primary text-primary px-1 font-label-md text-label-md flex items-center gap-2 transition-all font-semibold';
    graphTabContent.style.display = 'none';
    docTabContent.style.display = 'flex';
  }
}

// Document List Rendering & Selection
function renderDocList() {
  const container = document.getElementById('docListContainer');
  if (uploadedDocs.length === 0) {
    container.innerHTML = '<div class="text-center py-8 text-xs text-on-surface-variant/60">No documents analyzed yet.</div>';
    return;
  }
  
  container.innerHTML = '';
  uploadedDocs.forEach((doc) => {
    const isActive = activeDocId === doc.id;
    const activeClass = isActive 
      ? 'bg-primary/10 text-primary border-primary/20 font-semibold' 
      : 'text-on-surface-variant hover:bg-surface-container-high';
    container.innerHTML += `
      <button onclick="selectDoc('${doc.id}')" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left text-xs transition-all ${activeClass}">
        <span class="material-symbols-outlined text-[18px]">${doc.filename.endsWith('.pdf') ? 'picture_as_pdf' : 'description'}</span>
        <div class="flex-grow min-w-0">
          <div class="truncate font-bold">${escapeHtml(doc.filename)}</div>
          <div class="text-[10px] opacity-60">${doc.timestamp} • ${doc.size}</div>
        </div>
      </button>
    `;
  });
}

function selectDoc(docId) {
  activeDocId = docId;
  renderDocList();
  
  const doc = uploadedDocs.find(d => d.id === docId);
  if (!doc) return;
  
  const viewer = document.getElementById('docContentViewer');
  
  const highlightedHtml = renderHighlights(doc.text, doc.highlights);
  const paragraphsHtml = highlightedHtml.split('\n\n').map(p => {
    return `<p class="mb-4 leading-relaxed text-on-surface text-body-md">${p.replace(/\n/g, '<br>')}</p>`;
  }).join('');
  
  viewer.innerHTML = `
    <div class="mb-6 pb-4 border-b border-surface-container-high">
      <div class="flex items-center justify-between mb-1">
        <h2 class="text-headline-md font-bold text-void-black text-[22px]">${escapeHtml(doc.filename)}</h2>
        <span class="text-xs px-2.5 py-1 bg-surface-container-high rounded-full font-bold text-on-surface-variant">${doc.size}</span>
      </div>
      <p class="text-xs text-on-surface-variant">Analyzed at ${doc.timestamp}</p>
    </div>
    <article class="prose max-w-none text-on-surface">
      ${paragraphsHtml}
    </article>
  `;
}

// Handle enter key on note input
document.getElementById('noteInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendNote();
  }
});

// Handle enter key on chat input
document.getElementById('chatInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage();
  }
});

async function exportSummaryPdf() {
  const btn = document.getElementById('exportPdfBtn');
  const icon = document.getElementById('exportPdfIcon');
  const label = document.getElementById('exportPdfLabel');

  // Set loading state
  if (btn) btn.disabled = true;
  if (icon) icon.textContent = 'hourglass_top';
  if (label) label.textContent = 'Generating…';
  const nodes = [];
  globalNodes.forEach(n => {
    nodes.push({
      name: n.label,
      type: n.nodeType,
      description: n.description
    });
  });

  const edges = [];
  globalEdges.forEach(e => {
    const srcNode = globalNodes.get(e.from);
    const tgtNode = globalNodes.get(e.to);
    edges.push({
      source: srcNode ? srcNode.label : e.from,
      target: tgtNode ? tgtNode.label : e.to,
      relation: e.label,
      confidence: e.title ? (e.title.match(/[\d\.]+/) ? parseFloat(e.title.match(/[\d\.]+/)[0]) : 0.5) : 0.5
    });
  });

  const docs = uploadedDocs.map(d => ({
    filename: d.filename,
    timestamp: d.timestamp,
    size: d.size
  }));

  const resetBtn = () => {
    if (btn) btn.disabled = false;
    if (icon) icon.textContent = 'picture_as_pdf';
    if (label) label.textContent = 'Export PDF';
  };

  if (nodes.length === 0) {
    resetBtn();
    alert("No concepts in the workspace to export. Add some notes or upload documents first!");
    return;
  }

  try {
    const resp = await fetch('/api/export-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nodes, edges, documents: docs })
    });

    if (!resp.ok) {
      let errMsg = `Server error (${resp.status})`;
      try {
        const errData = await resp.json();
        errMsg = errData.error || errMsg;
      } catch (_) {
        const errText = await resp.text().catch(() => '');
        if (errText) errMsg += ': ' + errText.substring(0, 300);
      }
      console.error('[exportSummaryPdf] Server error:', errMsg);
      alert('PDF Export failed: ' + errMsg);
      return;
    }

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'langextract_Summary.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error('[exportSummaryPdf] Fetch/generation error:', err);
    alert('An error occurred during PDF generation: ' + (err.message || err));
  } finally {
    resetBtn();
  }
}

window.onload = () => {
  initGraph();
};
