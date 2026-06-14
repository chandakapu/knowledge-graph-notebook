let pendingFileText = "";
let pendingFileName = "";
let pendingFileSize = "";

function addNoteHistoryEntry(filename, size, timestamp, newNodes, newEdges) {
  const empty = document.getElementById('noteHistoryEmpty');
  if (empty) empty.style.display = 'none';

  const container = document.getElementById('noteHistory');
  const entryHtml = `
    <div class="bg-surface-container-low border border-surface-container rounded-2xl p-3 space-y-2">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-primary text-[16px]">${filename.endsWith('.pdf') ? 'picture_as_pdf' : 'description'}</span>
        <div class="flex-grow min-w-0">
          <p class="text-[12px] font-bold text-void-black truncate">${escapeHtml(filename)}</p>
          <p class="text-[10px] text-on-surface-variant">${timestamp} · ${size}</p>
        </div>
      </div>
      <div class="flex gap-2 flex-wrap">
        <span class="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-bold rounded-full">+${newNodes} nodes</span>
        <span class="px-2 py-0.5 bg-secondary-container/20 text-secondary-container text-[10px] font-bold rounded-full">+${newEdges} edges</span>
        <span class="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded-full">Analyzed ✓</span>
      </div>
    </div>`;
  container.insertAdjacentHTML('beforeend', entryHtml);
  container.scrollTop = container.scrollHeight;
}

function renderHighlights(text, highlights) {
  if (!highlights || highlights.length === 0) return escapeHtml(text);
  const sorted = [...highlights].sort((a, b) => a.start - b.start);
  let html = '';
  let cursor = 0;
  for (const h of sorted) {
    if (h.start < cursor) continue;
    html += escapeHtml(text.slice(cursor, h.start));
    const spanText = escapeHtml(text.slice(h.start, h.end));
    const clsName = h.cls || 'KeyConcept';
    html += `<span class="${clsName}" title="${clsName}">${spanText}</span>`;
    cursor = h.end;
  }
  html += escapeHtml(text.slice(cursor));
  return html;
}

async function handleFileSelected(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  event.target.value = '';
  
  document.getElementById('spinner').style.display = 'block';
  document.getElementById('noteInput').disabled = true;
  document.getElementById('sendBtn').disabled = true;
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const resp = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await resp.json();
    if (resp.status !== 200 || !data || data.error) {
      alert(data ? data.error : "Failed to upload and parse file.");
      return;
    }
    
    pendingFileText = data.text;
    pendingFileName = data.filename;
    
    const bytes = file.size;
    if (bytes < 1024) pendingFileSize = bytes + ' B';
    else if (bytes < 1048576) pendingFileSize = (bytes / 1024).toFixed(1) + ' KB';
    else pendingFileSize = (bytes / 1048576).toFixed(1) + ' MB';
    
    document.getElementById('attachedFileName').innerText = pendingFileName;
    document.getElementById('attachedFileSize').innerText = `(${pendingFileSize})`;
    document.getElementById('fileAttachmentContainer').classList.remove('hidden');
    
    document.getElementById('noteInput').focus();
  } catch (err) {
    console.error(err);
    alert("An error occurred during file upload.");
  } finally {
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('noteInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
  }
}

function removeAttachment() {
  pendingFileText = "";
  pendingFileName = "";
  pendingFileSize = "";
  document.getElementById('fileAttachmentContainer').classList.add('hidden');
}

async function sendNote() {
  const input = document.getElementById('noteInput');
  const userMessage = input.value.trim();
  
  if (!userMessage && !pendingFileText) return;
  
  input.value = '';
  
  let textToAnalyze = "";
  let displayMessage = "";
  
  if (pendingFileText) {
    textToAnalyze = (userMessage ? userMessage + "\n\n" : "") + pendingFileText;
    displayMessage = `📎 <span class="font-semibold text-white underline">${escapeHtml(pendingFileName)}</span> (${pendingFileSize})` + 
                     (userMessage ? `<br><br>${escapeHtml(userMessage)}` : "");
  } else {
    textToAnalyze = userMessage;
    displayMessage = escapeHtml(userMessage);
  }
  
  const hasAttachment = !!pendingFileText;
  const attachmentName = pendingFileName;
  const attachmentSize = pendingFileSize;
  removeAttachment();
  
  const history = document.getElementById('chatHistory');
  const userBubbleId = 'user-msg-' + Date.now();
  const userHtml = `
    <div class="flex flex-col items-end gap-2">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-[10px] text-on-surface-variant">Just now</span>
        <span class="font-label-sm text-label-sm font-bold text-primary">Me</span>
      </div>
      <div class="bg-primary text-white p-4 rounded-2xl rounded-tr-none text-body-md text-[14px] shadow-md shadow-primary/10 max-w-[90%]" id="${userBubbleId}">
        ${displayMessage}
      </div>
    </div>
  `;
  history.insertAdjacentHTML('beforeend', userHtml);
  history.scrollTop = history.scrollHeight;
  
  document.getElementById('spinner').style.display = 'block';
  
  try {
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: textToAnalyze })
    });
    const data = await resp.json();
    
    if (!hasAttachment) {
      const highlightedText = renderHighlights(userMessage, data.highlights);
      document.getElementById(userBubbleId).innerHTML = highlightedText;
    } else {
      const userMsgHighlights = (data.highlights || []).filter(h => h.end <= userMessage.length);
      const highlightedUserMsg = renderHighlights(userMessage, userMsgHighlights);
      let newDisplay = `📎 <span class="font-semibold text-white underline">${escapeHtml(attachmentName)}</span> (${attachmentSize})`;
      if (userMessage) {
        newDisplay += `<br><br>${highlightedUserMsg}`;
      }
      document.getElementById(userBubbleId).innerHTML = newDisplay;
    }
    
    // Process Graph
    let newNodesCount = 0;
    let newEdgesCount = 0;
    let sysNodesHtml = '';
    
    if (data.graph && data.graph.nodes) {
      data.graph.nodes.forEach(n => {
        const nodeId = n.name.toLowerCase();
        if (!nodeNames.has(nodeId)) {
          const style = getNodeStyle(n.type);
          globalNodes.add({
            id: nodeId,
            label: n.name,
            nodeType: n.type,
            description: n.description,
            size: 20,
            color: { 
              background: style.bg, 
              border: style.border, 
              highlight: { background: style.bg, border: style.border }, 
              hover: { background: style.bg, border: style.border } 
            },
            font: { color: '#181c22' }
          });
          nodeNames.add(nodeId);
          newNodesCount++;
          sysNodesHtml += `<li>Added Node: <span class="text-primary font-semibold">${escapeHtml(n.name)}</span> (${escapeHtml(n.type)})</li>`;
        }
      });
    }
    
    if (data.graph && data.graph.edges) {
      data.graph.edges.forEach((e) => {
        const sourceId = e.source.toLowerCase();
        const targetId = e.target.toLowerCase();
        
        if (!nodeNames.has(sourceId)) {
          const style = getNodeStyle('default');
          globalNodes.add({
            id: sourceId,
            label: e.source,
            nodeType: 'Concept',
            description: 'Automatically created from relationship.',
            size: 20,
            color: { 
              background: style.bg, 
              border: style.border, 
              highlight: { background: style.bg, border: style.border }, 
              hover: { background: style.bg, border: style.border } 
            },
            font: { color: '#181c22' }
          });
          nodeNames.add(sourceId);
          newNodesCount++;
          sysNodesHtml += `<li>Added Node: <span class="text-primary font-semibold">${escapeHtml(e.source)}</span> (Concept)</li>`;
        }
        
        if (!nodeNames.has(targetId)) {
          const style = getNodeStyle('default');
          globalNodes.add({
            id: targetId,
            label: e.target,
            nodeType: 'Concept',
            description: 'Automatically created from relationship.',
            size: 20,
            color: { 
              background: style.bg, 
              border: style.border, 
              highlight: { background: style.bg, border: style.border }, 
              hover: { background: style.bg, border: style.border } 
            },
            font: { color: '#181c22' }
          });
          nodeNames.add(targetId);
          newNodesCount++;
          sysNodesHtml += `<li>Added Node: <span class="text-primary font-semibold">${escapeHtml(e.target)}</span> (Concept)</li>`;
        }
        
        const sig = sourceId + '->' + targetId + ':' + e.relation;
        if (!edgeSignatures.has(sig)) {
          globalEdges.add({
            from: sourceId,
            to: targetId,
            label: e.relation,
            title: e.relation + ' (' + e.confidence + ')'
          });
          edgeSignatures.add(sig);
          newEdgesCount++;
          sysNodesHtml += `<li>Added Edge: <span class="italic font-semibold">${escapeHtml(e.relation)}</span></li>`;
        }
      });
    }
    
    updateStats();
    
    if (isClustered) {
      isClustered = false;
      toggleClustering();
    } else if (globalNodes.length >= 8) {
      toggleClustering();
    }
    
    // Save to document list archive
    const docId = 'doc-' + Date.now();
    const newDocObj = {
      id: docId,
      filename: hasAttachment ? attachmentName : `Note - ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      size: hasAttachment ? attachmentSize : (textToAnalyze.length + ' chars'),
      text: textToAnalyze,
      highlights: data.highlights || [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    uploadedDocs.push(newDocObj);
    activeDocId = docId;
    renderDocList();
    selectDoc(docId);

    // Record in Upload Notes panel history
    addNoteHistoryEntry(newDocObj.filename, newDocObj.size, newDocObj.timestamp, newNodesCount, newEdgesCount);
    
    // Add system response bubble
    if (newNodesCount > 0 || newEdgesCount > 0) {
      const sysHtml = `
        <div class="flex gap-3">
          <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <span class="material-symbols-outlined text-primary text-sm">auto_awesome</span>
          </div>
          <div class="bg-electric-purple/5 border border-electric-purple/20 border-l-4 border-l-primary p-4 rounded-2xl text-body-md text-[14px] shadow-sm text-on-surface flex-grow">
            <p class="text-primary font-bold mb-1">Extracted Elements</p>
            <ul class="list-disc ml-4 space-y-1 text-on-surface-variant text-xs">
              ${sysNodesHtml}
            </ul>
          </div>
        </div>
      `;
      history.insertAdjacentHTML('beforeend', sysHtml);
    } else {
      const sysHtml = `
        <div class="flex gap-3">
          <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <span class="material-symbols-outlined text-primary text-sm">auto_awesome</span>
          </div>
          <div class="bg-surface-container-low p-4 rounded-2xl text-body-md text-[14px] text-on-surface-variant shadow-sm flex-grow">
            No new distinct entities or relationships found in this note.
          </div>
        </div>
      `;
      history.insertAdjacentHTML('beforeend', sysHtml);
    }
    history.scrollTop = history.scrollHeight;
    
    if (networkInstance) {
        networkInstance.fit({ animation: true });
    }
    
  } catch (err) {
    console.error(err);
  } finally {
    document.getElementById('spinner').style.display = 'none';
  }
}
