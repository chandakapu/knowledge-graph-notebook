document.getElementById('workspaceSearchInput').addEventListener('keydown', async e => {
  if (e.key === 'Enter') {
    e.preventDefault();
    const query = e.target.value.trim();
    if (!query) return;

    // Collect all current nodes to send as context for semantic search
    const nodes = [];
    globalNodes.forEach(n => {
      nodes.push({
        id: n.id,
        name: n.label,
        type: n.nodeType,
        description: n.description
      });
    });

    if (nodes.length === 0) return;

    try {
      const resp = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, nodes })
      });
      const data = await resp.json();
      const matches = data.matched_nodes || [];

      if (matches.length > 0) {
        const matchName = matches[0];
        // Find vis.js node ID by label (which is the node name)
        let targetNodeId = null;
        globalNodes.forEach(n => {
          if (n.label && n.label.toLowerCase() === matchName.toLowerCase()) {
            targetNodeId = n.id;
          }
        });

        if (targetNodeId && networkInstance) {
          if (networkInstance.isClustered(targetNodeId)) {
            const clusterId = networkInstance.findNode(targetNodeId)[0];
            networkInstance.openCluster(clusterId);
            updateStats();
          }
          networkInstance.focus(targetNodeId, {
            scale: 1.3,
            animation: {
              duration: 1000,
              easingFunction: 'easeInOutQuad'
            }
          });
          networkInstance.selectNodes([targetNodeId]);
          openInspector(globalNodes.get(targetNodeId));
          
          // Temporary flash border or show visual search feedback
          e.target.classList.add('ring-2', 'ring-green-500');
          setTimeout(() => {
            e.target.classList.remove('ring-2', 'ring-green-500');
          }, 1500);
        } else {
          alert(`Concept found: "${matchName}", but it could not be located in the current graph view.`);
        }
      } else {
        e.target.classList.add('ring-2', 'ring-red-500');
        setTimeout(() => {
          e.target.classList.remove('ring-2', 'ring-red-500');
        }, 1500);
        console.log("No semantic matches found for search query.");
      }
    } catch (err) {
      console.error("Semantic search error:", err);
    }
  }
});
