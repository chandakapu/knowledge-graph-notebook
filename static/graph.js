const TYPE_COLORS = {
  Concept:     { bg: '#8127cf', border: '#6900b3', font: '#ffffff', icon: 'lightbulb' },
  Algorithm:   { bg: '#346bf1', border: '#0050d7', font: '#ffffff', icon: 'functions' },
  Method:      { bg: '#fabc4e', border: '#7b5500', font: '#181c22', icon: 'build' },
  Theory:      { bg: '#ba1a1a', border: '#93000a', font: '#ffffff', icon: 'menu_book' },
  default:     { bg: '#e0e2eb', border: '#7e7385', font: '#181c22', icon: 'radio_button_unchecked' },
};

function getNodeStyle(type) {
  return TYPE_COLORS[type] || TYPE_COLORS.default;
}

function initGraph() {
  const container = document.getElementById('graphCanvas');
  const data = { nodes: globalNodes, edges: globalEdges };
  const options = {
    interaction: { hover: true },
    physics: {
      barnesHut: { 
        gravitationalConstant: -5000, 
        centralGravity: 0.15, 
        springLength: 200,
        springConstant: 0.04,
        damping: 0.3
      },
      stabilization: { iterations: 300 },
    },
    nodes: {
      shape: 'dot',
      font: { color: '#181c22', face: 'Inter', size: 12 },
      borderWidth: 2
    },
    edges: {
      font: { color: '#4d4354', size: 10, align: 'middle' },
      arrows: { to: { enabled: true, scaleFactor: 0.5 } },
      color: { color: 'rgba(129, 39, 207, 0.25)', highlight: '#8127cf' },
      smooth: { type: 'continuous' }
    }
  };
  networkInstance = new vis.Network(container, data, options);
  
  networkInstance.on('click', params => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      if (networkInstance.isCluster(nodeId)) {
        networkInstance.openCluster(nodeId);
        updateStats();
        return;
      }
      const nodeData = globalNodes.get(nodeId);
      openInspector(nodeData);
    } else {
      closeInspector();
    }
  });
}

function openInspector(nodeData) {
  document.getElementById('nodeInspector').style.display = 'block';
  document.getElementById('inspectorTitle').innerText = nodeData.label || nodeData.id;
  document.getElementById('inspectorType').innerText = nodeData.nodeType || 'Entity';
  document.getElementById('inspectorDesc').innerText = nodeData.description || 'No description available.';
  const style = getNodeStyle(nodeData.nodeType);
  document.getElementById('inspectorIcon').innerText = style.icon;
}

function closeInspector() {
  document.getElementById('nodeInspector').style.display = 'none';
}

function updateNodeSizesByDegree() {
  const degrees = {};
  globalNodes.forEach(n => {
    degrees[n.id] = 0;
  });
  globalEdges.forEach(e => {
    if (degrees[e.from] !== undefined) degrees[e.from]++;
    if (degrees[e.to] !== undefined) degrees[e.to]++;
  });
  
  const updates = [];
  globalNodes.forEach(n => {
    const deg = degrees[n.id] || 0;
    const newSize = Math.min(40, 20 + deg * 4);
    if (n.size !== newSize) {
      updates.push({ id: n.id, size: newSize });
    }
  });
  
  if (updates.length > 0) {
    globalNodes.update(updates);
  }
}

function clusterNodesByType(type) {
  const style = getNodeStyle(type);
  const clusterOptions = {
    joinCondition: function(nodeOptions) {
      return nodeOptions.nodeType === type;
    },
    clusterNodeProperties: {
      id: 'cluster_' + type.toLowerCase(),
      label: type + 's',
      nodeType: type,
      isCluster: true,
      shape: 'database',
      size: 30,
      color: {
        background: style.bg,
        border: style.border,
        highlight: { background: style.bg, border: style.border },
        hover: { background: style.bg, border: style.border }
      },
      font: { color: style.font || '#ffffff', face: 'Inter', size: 14, bold: true }
    }
  };
  networkInstance.cluster(clusterOptions);
}

function toggleClustering() {
  if (!networkInstance) return;
  if (isClustered) {
    // Open all clusters
    for (const type of Object.keys(TYPE_COLORS)) {
      const clusterId = 'cluster_' + type.toLowerCase();
      if (networkInstance.body.nodes[clusterId]) {
        networkInstance.openCluster(clusterId);
      }
    }
    isClustered = false;
    document.getElementById('clusterToggleBtn').innerHTML = `
      <span class="material-symbols-outlined text-[16px]">bubble_chart</span>
      <span>Cluster by Type</span>
    `;
  } else {
    // Cluster by type
    const typesInGraph = new Set();
    globalNodes.forEach(n => {
      if (n.nodeType) typesInGraph.add(n.nodeType);
    });
    typesInGraph.forEach(type => {
      clusterNodesByType(type);
    });
    isClustered = true;
    document.getElementById('clusterToggleBtn').innerHTML = `
      <span class="material-symbols-outlined text-[16px]">unfold_more</span>
      <span>Expand All</span>
    `;
  }
  updateStats();
}

function updateStats() {
  updateNodeSizesByDegree();
  const n = globalNodes.length;
  document.getElementById('statNodes').innerText = n;
  document.getElementById('statEdges').innerText = globalEdges.length;
  // Keep chat context badge up-to-date
  const badge = document.getElementById('chatContextCount');
  if (badge) badge.innerText = n;
}
