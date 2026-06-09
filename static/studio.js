/**
 * langextract HCI Extraction Studio - Client Controller
 * Reactive state management, Visual Traceability, HITL Engine,
 * Undo/Redo System, Toast Notifications, and Keyboard Shortcuts.
 */

// Application State
let state = {
    templates: {},
    currentTemplateKey: "",
    classes: [], // Active list of extraction classes
    documentId: "",
    rawText: "",
    extractions: [], // Array of active extractions
    examples: [], // Few-shot examples from current template
    isVisualizing: false,
    selectedSpan: null // Temporary holder for text selections {text, start, end}
};

// Undo/Redo State
const MAX_HISTORY = 50;
let undoStack = []; // { description, snapshotBefore, snapshotAfter }
let redoStack = [];

// DOM Elements
const selectTemplate = document.getElementById("select-template");
const selectModel = document.getElementById("select-model");
const inputApiKey = document.getElementById("input-api-key");
const textareaPrompt = document.getElementById("textarea-prompt");
const schemaClassesList = document.getElementById("schema-classes-list");
const inputNewClass = document.getElementById("input-new-class");
const btnAddClass = document.getElementById("btn-add-class");
const btnRun = document.getElementById("btn-run");
const btnSave = document.getElementById("btn-save");
const btnClearExtractions = document.getElementById("btn-clear-extractions");
const textareaDocInput = document.getElementById("textarea-doc-input");
const textViewer = document.getElementById("text-viewer");
const extractionsContainer = document.getElementById("extractions-container");
const extractionsEmpty = document.getElementById("extractions-empty");
const extractionStats = document.getElementById("extraction-stats");
const loadingOverlay = document.getElementById("loading-overlay");
const loadingText = document.getElementById("loading-text");
const selectionPopover = document.getElementById("selection-popover");
const spanHoverCard = document.getElementById("span-hover-card");
const docIdBadge = document.getElementById("doc-id-badge");
const toastContainer = document.getElementById("toast-container");

// Modal Elements
const modalOverlay = document.getElementById("modal-overlay");
const modalTitle = document.getElementById("modal-title");
const modalEntityText = document.getElementById("modal-entity-text");
const modalEntityClass = document.getElementById("modal-entity-class");
const modalAttributesList = document.getElementById("modal-attributes-list");
const modalAddAttribute = document.getElementById("modal-add-attribute");
const modalCancel = document.getElementById("modal-cancel");
const modalSave = document.getElementById("modal-save");
const modalClose = document.getElementById("modal-close");

// Undo/Redo Buttons (Header + Sidebar)
const btnUndo = document.getElementById("btn-undo");
const btnRedo = document.getElementById("btn-redo");
const btnUndoSidebar = document.getElementById("btn-undo-sidebar");
const btnRedoSidebar = document.getElementById("btn-redo-sidebar");
const historyList = document.getElementById("history-list");

// Target Edit Entity index
let editingEntityIndex = null;

// Initialize Web Studio
document.addEventListener("DOMContentLoaded", async () => {
    // 1. Fetch available templates
    await fetchTemplates();
    
    // 2. Load API Key from Session Storage if available
    const savedKey = sessionStorage.getItem("langextract_api_key");
    if (savedKey) {
        inputApiKey.value = savedKey;
    }
    
    // 3. Setup Listeners
    setupEventListeners();
    
    // 4. Default to first template to reduce cognitive load on cold-start
    if (selectTemplate.options.length > 1) {
        selectTemplate.selectedIndex = 1;
        applyTemplate(selectTemplate.value);
    }
});

// Event Listeners Configuration
function setupEventListeners() {
    // Template loading
    selectTemplate.addEventListener("change", (e) => {
        applyTemplate(e.target.value);
    });
    
    // Save API key locally in session
    inputApiKey.addEventListener("input", (e) => {
        sessionStorage.setItem("langextract_api_key", e.target.value);
    });
    
    // Schema Builder Actions
    btnAddClass.addEventListener("click", addCustomClass);
    inputNewClass.addEventListener("keypress", (e) => {
        if (e.key === "Enter") addCustomClass();
    });
    
    // Run & Save actions
    btnRun.addEventListener("click", executeExtraction);
    btnSave.addEventListener("click", saveAnnotationsToFile);
    btnClearExtractions.addEventListener("click", resetToRawTextState);
    
    // Undo/Redo buttons (header)
    if (btnUndo) btnUndo.addEventListener("click", undo);
    if (btnRedo) btnRedo.addEventListener("click", redo);
    
    // Undo/Redo buttons (sidebar)
    if (btnUndoSidebar) btnUndoSidebar.addEventListener("click", undo);
    if (btnRedoSidebar) btnRedoSidebar.addEventListener("click", redo);
    
    // Text Selection Event for HITL Span Labeling
    textViewer.addEventListener("mouseup", handleTextSelection);
    
    // Close Selection Popover if clicking elsewhere
    document.addEventListener("mousedown", (e) => {
        if (!selectionPopover.contains(e.target) && e.target !== textViewer) {
            hideSelectionPopover();
        }
        if (!spanHoverCard.contains(e.target) && !e.target.classList.contains("grounded-span")) {
            hideHoverCard();
        }
    });
    
    // Modal controls
    modalClose.addEventListener("click", closeModal);
    modalCancel.addEventListener("click", closeModal);
    modalSave.addEventListener("click", applyModalChanges);
    modalAddAttribute.addEventListener("click", () => addAttributeRow());
    
    // Keyboard Shortcuts
    document.addEventListener("keydown", handleKeyboardShortcuts);
}

// ----------------------------------------------------
// Keyboard Shortcuts
// ----------------------------------------------------
function handleKeyboardShortcuts(e) {
    // Ctrl+Z → Undo
    if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
        return;
    }
    
    // Ctrl+Shift+Z or Ctrl+Y → Redo
    if ((e.ctrlKey || e.metaKey) && (e.key === "Z" || e.key === "y")) {
        e.preventDefault();
        redo();
        return;
    }
    
    // Ctrl+S → Save/Export
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        saveAnnotationsToFile();
        return;
    }
    
    // Escape → Close modal, popover, hovercard
    if (e.key === "Escape") {
        if (modalOverlay.classList.contains("active")) {
            closeModal();
        }
        hideSelectionPopover();
        hideHoverCard();
        return;
    }
}

// ----------------------------------------------------
// Toast Notification System
// ----------------------------------------------------
function showToast(message, type = "info", duration = 4000) {
    const icons = {
        success: "✓",
        error: "✕",
        warning: "⚠",
        info: "ℹ"
    };
    
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-body">${escapeHtml(message)}</span>
        <button class="toast-close" aria-label="Dismiss notification">&times;</button>
    `;
    
    // Close button handler
    const closeBtn = toast.querySelector(".toast-close");
    closeBtn.addEventListener("click", () => dismissToast(toast));
    
    toastContainer.appendChild(toast);
    
    // Auto-dismiss
    const timer = setTimeout(() => dismissToast(toast), duration);
    toast._timer = timer;
}

function dismissToast(toast) {
    if (toast._dismissed) return;
    toast._dismissed = true;
    clearTimeout(toast._timer);
    toast.classList.add("toast-exiting");
    toast.addEventListener("animationend", () => {
        toast.remove();
    });
}

// ----------------------------------------------------
// Undo/Redo System
// ----------------------------------------------------
function snapshotExtractions() {
    return JSON.parse(JSON.stringify(state.extractions));
}

function pushUndoAction(description, snapshotBefore, snapshotAfter) {
    undoStack.push({ description, snapshotBefore, snapshotAfter });
    if (undoStack.length > MAX_HISTORY) {
        undoStack.shift();
    }
    redoStack = [];
    updateUndoRedoUI();
}

function undo() {
    if (undoStack.length === 0) return;
    
    const action = undoStack.pop();
    redoStack.push(action);
    
    state.extractions = JSON.parse(JSON.stringify(action.snapshotBefore));
    
    renderInteractiveSpans();
    renderExtractionsPanel();
    renderExtractionStats();
    updateUndoRedoUI();
    
    showToast(`Undone: ${action.description}`, "info", 2500);
}

function redo() {
    if (redoStack.length === 0) return;
    
    const action = redoStack.pop();
    undoStack.push(action);
    
    state.extractions = JSON.parse(JSON.stringify(action.snapshotAfter));
    
    renderInteractiveSpans();
    renderExtractionsPanel();
    renderExtractionStats();
    updateUndoRedoUI();
    
    showToast(`Redone: ${action.description}`, "info", 2500);
}

function updateUndoRedoUI() {
    const canUndo = undoStack.length > 0;
    const canRedo = redoStack.length > 0;
    
    if (btnUndo) btnUndo.disabled = !canUndo;
    if (btnRedo) btnRedo.disabled = !canRedo;
    if (btnUndoSidebar) btnUndoSidebar.disabled = !canUndo;
    if (btnRedoSidebar) btnRedoSidebar.disabled = !canRedo;
    
    renderHistoryPanel();
}

function renderHistoryPanel() {
    if (!historyList) return;
    historyList.innerHTML = "";
    
    if (undoStack.length === 0 && redoStack.length === 0) {
        historyList.innerHTML = `<div class="history-empty">No actions recorded yet</div>`;
        return;
    }
    
    // Show redo items (greyed out, at top)
    for (let i = redoStack.length - 1; i >= 0; i--) {
        const item = document.createElement("div");
        item.className = "history-item";
        item.style.opacity = "0.45";
        item.innerHTML = `
            <span class="history-item-icon">↻</span>
            <span class="history-item-desc">${escapeHtml(redoStack[i].description)}</span>
        `;
        historyList.appendChild(item);
    }
    
    // Show undo items
    for (let i = undoStack.length - 1; i >= 0; i--) {
        const iconMap = {
            "Added": "＋",
            "Edited": "✎",
            "Deleted": "✕",
            "Cleared": "⌧",
            "Ran": "▶"
        };
        const firstWord = undoStack[i].description.split(" ")[0];
        const icon = iconMap[firstWord] || "●";
        
        const item = document.createElement("div");
        item.className = "history-item";
        item.innerHTML = `
            <span class="history-item-icon">${icon}</span>
            <span class="history-item-desc">${escapeHtml(undoStack[i].description)}</span>
        `;
        historyList.appendChild(item);
    }
}

// ----------------------------------------------------
// Templates & State Setups
// ----------------------------------------------------
async function fetchTemplates() {
    showLoading("Loading templates...");
    try {
        const response = await fetch("/api/templates");
        if (!response.ok) throw new Error("Failed to load templates.");
        state.templates = await response.json();
        
        selectTemplate.innerHTML = '<option value="">-- Choose Template --</option>';
        Object.keys(state.templates).forEach(key => {
            const opt = document.createElement("option");
            opt.value = key;
            opt.textContent = state.templates[key].name;
            selectTemplate.appendChild(opt);
        });
    } catch (err) {
        console.error(err);
        showToast("Server communication error. Make sure Flask server is running.", "error", 6000);
    } finally {
        hideLoading();
    }
}

function applyTemplate(key) {
    if (!key || !state.templates[key]) {
        state.currentTemplateKey = "";
        return;
    }
    
    const t = state.templates[key];
    state.currentTemplateKey = key;
    
    textareaPrompt.value = t.prompt;
    textareaDocInput.value = t.input_text;
    state.examples = t.examples;
    
    state.classes = Object.keys(t.schema);
    renderSchemaClasses();
    
    resetToRawTextState();
}

function renderSchemaClasses() {
    schemaClassesList.innerHTML = "";
    state.classes.forEach((className, idx) => {
        const classColorIdx = (idx % 4) + 1; // map 1-4
        
        const tag = document.createElement("div");
        tag.className = `schema-tag class-${classColorIdx}`;
        tag.innerHTML = `
            <span>${className}</span>
            <button class="remove-btn" onclick="removeSchemaClass('${className}')">&times;</button>
        `;
        schemaClassesList.appendChild(tag);
    });
}

window.removeSchemaClass = function(name) {
    state.classes = state.classes.filter(c => c !== name);
    renderSchemaClasses();
};

function addCustomClass() {
    const val = inputNewClass.value.trim().toLowerCase();
    if (!val) return;
    if (state.classes.includes(val)) {
        showToast("Class already exists!", "warning");
        return;
    }
    state.classes.push(val);
    renderSchemaClasses();
    inputNewClass.value = "";
}

function resetToRawTextState() {
    if (state.extractions.length > 0) {
        const before = snapshotExtractions();
        state.extractions = [];
        pushUndoAction(`Cleared all extractions`, before, []);
    } else {
        state.extractions = [];
    }
    
    state.documentId = "";
    state.isVisualizing = false;
    
    textareaDocInput.style.display = "block";
    textViewer.style.display = "none";
    textViewer.innerHTML = "";
    
    extractionsContainer.style.display = "none";
    extractionsEmpty.style.display = "flex";
    btnClearExtractions.style.display = "none";
    docIdBadge.textContent = "";
    extractionStats.style.display = "none";
}

// ----------------------------------------------------
// Traceability Rendering Engine (XAI Visuals)
// ----------------------------------------------------
function renderInteractiveSpans() {
    const raw = state.rawText;
    
    const grounded = state.extractions
        .filter(ext => ext.char_interval && ext.char_interval.start_pos !== null && ext.char_interval.end_pos !== null)
        .sort((a, b) => a.char_interval.start_pos - b.char_interval.start_pos);
        
    let outputHTML = "";
    let currentIndex = 0;
    
    for (let i = 0; i < grounded.length; i++) {
        const ext = grounded[i];
        const { start_pos, end_pos } = ext.char_interval;
        
        if (start_pos < currentIndex) {
            continue; 
        }
        
        outputHTML += escapeHtml(raw.substring(currentIndex, start_pos));
        const classColorIdx = (state.classes.indexOf(ext.extraction_class) % 4) + 1 || "unknown";
        outputHTML += `<span class="grounded-span class-${classColorIdx}" data-index="${ext.extraction_index}" tabindex="0" role="button" aria-label="${escapeHtml(ext.extraction_text)} (${ext.extraction_class})">${escapeHtml(raw.substring(start_pos, end_pos))}</span>`;
        
        currentIndex = end_pos;
    }
    
    outputHTML += escapeHtml(raw.substring(currentIndex));
    
    textViewer.innerHTML = outputHTML;
    textViewer.style.display = "block";
    textareaDocInput.style.display = "none";
    
    setupSpanEventListeners();
}

function setupSpanEventListeners() {
    const spans = textViewer.querySelectorAll(".grounded-span");
    spans.forEach(span => {
        const index = parseInt(span.getAttribute("data-index"));
        
        span.addEventListener("mouseenter", (e) => {
            highlightEntityCard(index, true);
            showHoverCard(index, e);
        });
        
        span.addEventListener("mouseleave", () => {
            highlightEntityCard(index, false);
        });
        
        span.addEventListener("click", (e) => {
            e.stopPropagation();
            openEditModal(index);
        });
        
        span.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openEditModal(index);
            }
        });
    });
}

function renderExtractionsPanel() {
    if (state.extractions.length === 0) {
        extractionsContainer.style.display = "none";
        extractionsEmpty.style.display = "flex";
        btnClearExtractions.style.display = "none";
        extractionStats.style.display = "none";
        return;
    }
    
    extractionsEmpty.style.display = "none";
    extractionsContainer.style.display = "flex";
    extractionsContainer.innerHTML = "";
    btnClearExtractions.style.display = "block";
    
    const groups = {};
    state.classes.forEach(cls => groups[cls] = []);
    groups["unclassified"] = [];
    
    state.extractions.forEach(ext => {
        if (groups[ext.extraction_class]) {
            groups[ext.extraction_class].push(ext);
        } else {
            groups["unclassified"].push(ext);
        }
    });
    
    Object.keys(groups).forEach(cls => {
        const list = groups[cls];
        if (list.length === 0) return;
        
        const groupColorIdx = (state.classes.indexOf(cls) % 4) + 1 || "unknown";
        
        const groupEl = document.createElement("div");
        groupEl.className = "extraction-group";
        groupEl.innerHTML = `
            <div class="extraction-group-title">${cls.toUpperCase()}</div>
            <div class="entity-list"></div>
        `;
        
        const listEl = groupEl.querySelector(".entity-list");
        
        list.forEach(ext => {
            const card = document.createElement("div");
            card.className = `entity-card`;
            card.setAttribute("id", `entity-card-${ext.extraction_index}`);
            
            const alignmentBadge = getAlignmentBadgeHTML(ext.alignment_status);
            
            let attributesHTML = "";
            if (ext.attributes && Object.keys(ext.attributes).length > 0) {
                attributesHTML = `<div class="entity-attributes">`;
                Object.entries(ext.attributes).forEach(([key, val]) => {
                    attributesHTML += `
                        <div class="attribute-key">${key}:</div>
                        <div class="attribute-val">${escapeHtml(String(val))}</div>
                    `;
                });
                attributesHTML += `</div>`;
            }
            
            card.innerHTML = `
                <div class="entity-card-header">
                    <div class="entity-name">${escapeHtml(ext.extraction_text)}</div>
                    <div style="display:flex; align-items:center; gap:0.35rem;">
                        ${alignmentBadge}
                        <span class="entity-badge class-${groupColorIdx}">${ext.extraction_class}</span>
                    </div>
                </div>
                ${attributesHTML}
                <div class="entity-actions">
                    <button class="btn-workbench btn-workbench-sm" onclick="event.stopPropagation(); openEditModal(${ext.extraction_index})">Edit</button>
                    <button class="btn-workbench btn-workbench-sm btn-workbench-danger" onclick="event.stopPropagation(); deleteExtraction(${ext.extraction_index})">Delete</button>
                </div>
            `;
            
            card.addEventListener("mouseenter", () => {
                highlightDocumentSpan(ext.extraction_index, true);
            });
            card.addEventListener("mouseleave", () => {
                highlightDocumentSpan(ext.extraction_index, false);
            });
            card.addEventListener("click", () => {
                highlightDocumentSpan(ext.extraction_index, true);
                scrollToSpan(ext.extraction_index);
            });
            
            listEl.appendChild(card);
        });
        
        extractionsContainer.appendChild(groupEl);
    });
    
    renderExtractionStats();
}

function getAlignmentBadgeHTML(status) {
    if (!status) {
        return `<span class="alignment-badge alignment-neutral" title="Alignment status unknown">🔘</span>`;
    }
    
    const map = {
        "match_exact": { icon: "✅", cls: "alignment-exact", label: "Exact match: Text grounding precisely aligned" },
        "match_approximate": { icon: "⚠️", cls: "alignment-approx", label: "Approximate match: Text found with slight offset" },
        "no_match": { icon: "❌", cls: "alignment-none", label: "No match: Could not ground text in document" }
    };
    
    const info = map[status] || { icon: "🔘", cls: "alignment-neutral", label: status };
    return `<span class="alignment-badge ${info.cls}" title="${info.label}">${info.icon}</span>`;
}

function renderExtractionStats() {
    if (state.extractions.length === 0) {
        extractionStats.style.display = "none";
        return;
    }
    
    extractionStats.style.display = "flex";
    
    const classCounts = {};
    state.classes.forEach(cls => classCounts[cls] = 0);
    const alignCounts = { exact: 0, approx: 0, none: 0, unknown: 0 };
    
    state.extractions.forEach(ext => {
        if (classCounts[ext.extraction_class] !== undefined) {
            classCounts[ext.extraction_class]++;
        }
        
        if (ext.alignment_status === "match_exact") alignCounts.exact++;
        else if (ext.alignment_status === "match_approximate") alignCounts.approx++;
        else if (ext.alignment_status === "no_match") alignCounts.none++;
        else alignCounts.unknown++;
    });
    
    let html = `<span class="stat-total">Total: ${state.extractions.length}</span>`;
    html += `<span class="stat-divider"></span>`;
    
    state.classes.forEach((cls, idx) => {
        const count = classCounts[cls];
        if (count === 0) return;
        const colorIdx = (idx % 4) + 1;
        html += `<span class="stat-pill class-${colorIdx}">${cls}: ${count}</span>`;
    });
    
    html += `<span class="stat-divider"></span>`;
    
    if (alignCounts.exact > 0) {
        html += `<span class="stat-alignment"><span class="stat-alignment-icon">✅</span> ${alignCounts.exact}</span>`;
    }
    if (alignCounts.approx > 0) {
        html += `<span class="stat-alignment"><span class="stat-alignment-icon">⚠️</span> ${alignCounts.approx}</span>`;
    }
    if (alignCounts.none > 0) {
        html += `<span class="stat-alignment"><span class="stat-alignment-icon">❌</span> ${alignCounts.none}</span>`;
    }
    
    extractionStats.innerHTML = html;
}

// Hover sync and card helpers
function highlightEntityCard(index, active) {
    const card = document.getElementById(`entity-card-${index}`);
    if (!card) return;
    if (active) {
        card.classList.add("active");
        card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
        card.classList.remove("active");
    }
}

function highlightDocumentSpan(index, active) {
    const span = textViewer.querySelector(`.grounded-span[data-index="${index}"]`);
    if (!span) return;
    if (active) {
        span.classList.add("highlight-active");
    } else {
        span.classList.remove("highlight-active");
    }
}

function scrollToSpan(index) {
    const span = textViewer.querySelector(`.grounded-span[data-index="${index}"]`);
    if (span) {
        span.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function showHoverCard(index, event) {
    const ext = state.extractions.find(e => e.extraction_index === index);
    if (!ext) return;
    
    let attrs = "";
    if (ext.attributes) {
        Object.entries(ext.attributes).forEach(([k, v]) => {
            attrs += `<div><strong>${k}:</strong> ${escapeHtml(String(v))}</div>`;
        });
    }
    
    const alignmentBadge = getAlignmentBadgeHTML(ext.alignment_status);
    
    spanHoverCard.innerHTML = `
        <h4>${escapeHtml(ext.extraction_text)}</h4>
        <div style="font-size:0.75rem; color:var(--text-secondary); margin-bottom:0.25rem; display:flex; align-items:center; gap:0.35rem;">
            Class: <span style="font-weight:600;">${ext.extraction_class}</span>
            ${alignmentBadge}
        </div>
        <div style="font-size:0.7rem; font-family:var(--font-mono); margin-bottom:0.4rem;">
            Offset: [${ext.char_interval.start_pos}, ${ext.char_interval.end_pos}]
        </div>
        <div style="border-top:1px dashed var(--border-color); padding-top:0.4rem; font-size:0.75rem;">
            ${attrs || "<em>No attributes defined</em>"}
        </div>
        <div style="margin-top:0.5rem; display:flex; justify-content:flex-end; gap:0.25rem;">
            <button class="btn-workbench btn-workbench-sm" style="font-size:0.7rem; padding:0.15rem 0.35rem;" onclick="openEditModal(${index})">Edit</button>
            <button class="btn-workbench btn-workbench-sm btn-workbench-danger" style="font-size:0.7rem; padding:0.15rem 0.35rem;" onclick="deleteExtraction(${index})">Delete</button>
        </div>
    `;
    
    const contentRect = textViewer.parentElement.getBoundingClientRect();
    const x = event.clientX - contentRect.left + textViewer.parentElement.scrollLeft;
    const y = event.clientY - contentRect.top + textViewer.parentElement.scrollTop - 100;
    
    spanHoverCard.style.left = `${x}px`;
    spanHoverCard.style.top = `${y}px`;
    spanHoverCard.style.display = "flex";
}

window.hideHoverCard = function() {
    spanHoverCard.style.display = "none";
};

// HITL Text Selection
function handleTextSelection(e) {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) return;
    
    const selectedText = sel.toString().trim();
    if (!selectedText) return;
    
    const range = sel.getRangeAt(0);
    const container = textViewer;
    const preSelectionRange = range.cloneRange();
    preSelectionRange.selectNodeContents(container);
    preSelectionRange.setEnd(range.startContainer, range.startOffset);
    
    const start = preSelectionRange.toString().length;
    const end = start + selectedText.length;
    
    state.selectedSpan = {
        text: selectedText,
        start_pos: start,
        end_pos: end
    };
    
    renderSelectionPopover(e.clientX, e.clientY);
}

function renderSelectionPopover(clientX, clientY) {
    selectionPopover.innerHTML = "";
    
    state.classes.forEach((cls, idx) => {
        const btn = document.createElement("button");
        btn.textContent = `+ ${cls}`;
        btn.addEventListener("click", () => {
            hideSelectionPopover();
            openAddModal(cls);
        });
        selectionPopover.appendChild(btn);
    });
    
    const customBtn = document.createElement("button");
    customBtn.textContent = "+ custom...";
    customBtn.style.fontStyle = "italic";
    customBtn.addEventListener("click", () => {
        hideSelectionPopover();
        const customClass = prompt("Enter custom class name:");
        if (customClass) {
            const normalizedClass = customClass.trim().toLowerCase();
            if (normalizedClass) {
                if (!state.classes.includes(normalizedClass)) {
                    state.classes.push(normalizedClass);
                    renderSchemaClasses();
                }
                openAddModal(normalizedClass);
            }
        }
    });
    selectionPopover.appendChild(customBtn);
    
    const contentRect = textViewer.parentElement.getBoundingClientRect();
    const x = clientX - contentRect.left + textViewer.parentElement.scrollLeft;
    const y = clientY - contentRect.top + textViewer.parentElement.scrollTop - 40;
    
    selectionPopover.style.left = `${x}px`;
    selectionPopover.style.top = `${y}px`;
    selectionPopover.style.display = "flex";
}

function hideSelectionPopover() {
    selectionPopover.style.display = "none";
}

// Modal handling
function openAddModal(className) {
    editingEntityIndex = null;
    modalTitle.textContent = "Add Custom Extraction";
    modalEntityText.value = state.selectedSpan.text;
    
    modalEntityClass.innerHTML = "";
    state.classes.forEach(cls => {
        const opt = document.createElement("option");
        opt.value = cls;
        opt.textContent = cls;
        if (cls === className) opt.selected = true;
        modalEntityClass.appendChild(opt);
    });
    
    modalAttributesList.innerHTML = "";
    const activeTemplate = state.templates[state.currentTemplateKey];
    if (activeTemplate && activeTemplate.schema[className]) {
        Object.keys(activeTemplate.schema[className]).forEach(attrKey => {
            addAttributeRow(attrKey, "");
        });
    } else {
        addAttributeRow("", "");
    }
    
    openModal();
}

window.openEditModal = function(index) {
    const ext = state.extractions.find(e => e.extraction_index === index);
    if (!ext) return;
    
    editingEntityIndex = index;
    modalTitle.textContent = "Edit Extraction Attributes";
    modalEntityText.value = ext.extraction_text;
    
    modalEntityClass.innerHTML = "";
    state.classes.forEach(cls => {
        const opt = document.createElement("option");
        opt.value = cls;
        opt.textContent = cls;
        if (cls === ext.extraction_class) opt.selected = true;
        modalEntityClass.appendChild(opt);
    });
    
    modalAttributesList.innerHTML = "";
    
    if (ext.attributes && Object.keys(ext.attributes).length > 0) {
        Object.entries(ext.attributes).forEach(([k, v]) => {
            addAttributeRow(k, v);
        });
    } else {
        addAttributeRow("", "");
    }
    
    window.hideHoverCard();
    openModal();
};

function addAttributeRow(key = "", val = "") {
    const row = document.createElement("div");
    row.className = "attribute-input-row";
    row.innerHTML = `
        <input type="text" placeholder="Key" class="attr-key studio-input" value="${escapeHtml(key)}" style="width:30%;">
        <input type="text" placeholder="Value" class="attr-val studio-input" value="${escapeHtml(String(val))}">
        <button onclick="this.parentElement.remove()" class="text-text-muted hover:text-accent font-bold" aria-label="Remove attribute">&times;</button>
    `;
    modalAttributesList.appendChild(row);
}

function openModal() {
    modalOverlay.classList.add("active");
}

function closeModal() {
    modalOverlay.classList.remove("active");
    window.getSelection().removeAllRanges();
}

window.deleteExtraction = function(index) {
    const ext = state.extractions.find(e => e.extraction_index === index);
    const description = ext ? `Deleted '${ext.extraction_text}' (${ext.extraction_class})` : `Deleted extraction #${index}`;
    
    const before = snapshotExtractions();
    state.extractions = state.extractions.filter(e => e.extraction_index !== index);
    const after = snapshotExtractions();
    
    pushUndoAction(description, before, after);
    window.hideHoverCard();
    
    renderInteractiveSpans();
    renderExtractionsPanel();
    
    showToast(description, "info", 3000);
};

function applyModalChanges() {
    const targetClass = modalEntityClass.value;
    const targetText = modalEntityText.value;
    
    const attributes = {};
    const rows = modalAttributesList.querySelectorAll(".attribute-input-row");
    rows.forEach(row => {
        const k = row.querySelector(".attr-key").value.trim();
        const v = row.querySelector(".attr-val").value.trim();
        if (k && v) {
            attributes[k] = v;
        }
    });
    
    const before = snapshotExtractions();
    
    if (editingEntityIndex !== null) {
        const ext = state.extractions.find(e => e.extraction_index === editingEntityIndex);
        if (ext) {
            ext.extraction_class = targetClass;
            ext.attributes = attributes;
            
            const after = snapshotExtractions();
            pushUndoAction(`Edited '${ext.extraction_text}' → ${targetClass}`, before, after);
            showToast(`Updated extraction: ${ext.extraction_text}`, "success", 3000);
        }
    } else {
        const nextIndex = state.extractions.reduce((max, ext) => Math.max(max, ext.extraction_index), -1) + 1;
        
        state.extractions.push({
            extraction_class: targetClass,
            extraction_text: targetText,
            char_interval: {
                start_pos: state.selectedSpan.start_pos,
                end_pos: state.selectedSpan.end_pos
            },
            attributes: attributes,
            alignment_status: "match_exact",
            extraction_index: nextIndex
        });
        
        const after = snapshotExtractions();
        pushUndoAction(`Added '${targetText}' as ${targetClass}`, before, after);
        showToast(`Added extraction: ${targetText} (${targetClass})`, "success", 3000);
    }
    
    closeModal();
    renderInteractiveSpans();
    renderExtractionsPanel();
}

// API Requests
async function executeExtraction() {
    const text = textareaDocInput.value.trim();
    const promptDescription = textareaPrompt.value.trim();
    
    if (!text) {
        showToast("Please enter a target document first!", "warning");
        return;
    }
    if (!promptDescription) {
        showToast("Extraction instructions cannot be empty!", "warning");
        return;
    }
    
    const modelId = selectModel.value;
    const apiKey = inputApiKey.value.trim();
    
    const requestExamples = [];
    if (state.examples && state.examples.length > 0) {
        state.examples.forEach(ex => {
            requestExamples.push({
                text: ex.text,
                extractions: ex.extractions.map(ext => ({
                    extraction_class: ext.extraction_class,
                    extraction_text: ext.extraction_text,
                    attributes: ext.attributes || {}
                }))
            });
        });
    }
    
    showLoading(`Executing standard schema constraints with ${modelId}...`);
    
    try {
        const response = await fetch("/api/extract", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: text,
                prompt_description: promptDescription,
                examples: requestExamples,
                model_id: modelId,
                api_key: apiKey || null
            })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Error communicating with server.");
        }
        
        const before = snapshotExtractions();
        
        state.rawText = data.text;
        state.documentId = data.document_id;
        state.extractions = data.extractions;
        state.isVisualizing = true;
        
        const after = snapshotExtractions();
        pushUndoAction(`Ran extraction (${data.extractions.length} results)`, before, after);
        
        docIdBadge.textContent = state.documentId;
        
        renderInteractiveSpans();
        renderExtractionsPanel();
        
        showToast(`Extraction complete: ${data.extractions.length} entities found.`, "success");
        
    } catch (err) {
        showToast(`Extraction Failed: ${err.message}`, "error", 6000);
        console.error(err);
    } finally {
        hideLoading();
    }
}

async function saveAnnotationsToFile() {
    if (state.extractions.length === 0) {
        showToast("There are no extractions to save!", "warning");
        return;
    }
    
    const filename = prompt("Enter file name for saving (e.g. custom_extraction.jsonl):", "annotated_spans.jsonl");
    if (!filename) return;
    
    showLoading("Saving annotated JSONL output...");
    
    try {
        const response = await fetch("/api/save", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: state.rawText,
                document_id: state.documentId,
                extractions: state.extractions,
                filename: filename
            })
        });
        
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || "Failed to save file.");
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename.endsWith(".jsonl") ? filename : (filename + ".jsonl");
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        showToast("Annotations exported successfully!", "success", 5000);
        
    } catch (err) {
        showToast(`Export failed: ${err.message}`, "error", 5000);
        console.error(err);
    } finally {
        hideLoading();
    }
}

// Helpers
function showLoading(msg) {
    loadingText.textContent = msg;
    loadingOverlay.classList.add("active");
}

function hideLoading() {
    loadingOverlay.classList.remove("active");
}


