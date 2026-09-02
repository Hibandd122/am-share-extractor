/**
 * NEXUS ALIGHT EXTRACTOR - Studio Preview & Inspector Interactivity
 */

document.addEventListener("DOMContentLoaded", () => {
    initStudioTabs();
    initCanvasZoomPan();
    initLayerInteraction();
    initCodeViewer();
    initLayerSearch();
});

// Studio Tab Switching
function initStudioTabs() {
    const tabBtns = document.querySelectorAll(".tab-btn");
    const panels = document.querySelectorAll(".tab-panel");

    tabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");

            tabBtns.forEach((b) => b.classList.remove("active"));
            panels.forEach((p) => p.classList.remove("active"));

            btn.classList.add("active");
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) {
                targetPanel.classList.add("active");
            }
        });
    });
}

// SVG Canvas Zoom & Pan
function initCanvasZoomPan() {
    const viewport = document.getElementById("stageViewport");
    const svg = document.getElementById("amStageSvg");
    const zoomInBtn = document.getElementById("zoomInBtn");
    const zoomOutBtn = document.getElementById("zoomOutBtn");
    const resetZoomBtn = document.getElementById("resetZoomBtn");
    const toggleGridBtn = document.getElementById("toggleGridBtn");

    if (!viewport || !svg) return;

    let scale = 1.0;
    let translateX = 0;
    let translateY = 0;
    let isPanning = false;
    let startX = 0;
    let startY = 0;

    function applyTransform() {
        svg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    }

    if (zoomInBtn) {
        zoomInBtn.addEventListener("click", () => {
            scale = Math.min(scale * 1.25, 5.0);
            applyTransform();
        });
    }

    if (zoomOutBtn) {
        zoomOutBtn.addEventListener("click", () => {
            scale = Math.max(scale / 1.25, 0.2);
            applyTransform();
        });
    }

    if (resetZoomBtn) {
        resetZoomBtn.addEventListener("click", () => {
            scale = 1.0;
            translateX = 0;
            translateY = 0;
            applyTransform();
        });
    }

    if (toggleGridBtn) {
        toggleGridBtn.addEventListener("click", () => {
            const grid = svg.querySelector(".am-stage-grid");
            if (grid) {
                grid.style.display = grid.style.display === "none" ? "block" : "none";
            }
        });
    }

    // Mouse Drag Pan
    viewport.addEventListener("mousedown", (e) => {
        if (e.button !== 0) return; // Left click only
        isPanning = true;
        startX = e.clientX - translateX;
        startY = e.clientY - translateY;
    });

    window.addEventListener("mousemove", (e) => {
        if (!isPanning) return;
        translateX = e.clientX - startX;
        translateY = e.clientY - startY;
        applyTransform();
    });

    window.addEventListener("mouseup", () => {
        isPanning = false;
    });

    // Wheel Zoom
    viewport.addEventListener("wheel", (e) => {
        e.preventDefault();
        const delta = e.deltaY < 0 ? 1.15 : 0.85;
        scale = Math.max(0.2, Math.min(5.0, scale * delta));
        applyTransform();
    }, { passive: false });
}

// Layer Tree and Canvas Interaction Sync
function initLayerInteraction() {
    const treeNodes = document.querySelectorAll(".tree-node");
    const svgLayers = document.querySelectorAll(".am-layer-node");

    // Click/Hover from Tree to Canvas
    treeNodes.forEach((node) => {
        const layerId = node.getAttribute("data-layer-id");
        if (!layerId) return;

        node.addEventListener("mouseenter", () => {
            const targetSvg = document.getElementById(layerId);
            if (targetSvg) {
                targetSvg.classList.add("active-highlight");
            }
        });

        node.addEventListener("mouseleave", () => {
            const targetSvg = document.getElementById(layerId);
            if (targetSvg) {
                targetSvg.classList.remove("active-highlight");
            }
        });

        // Toggle Expand / Collapse subtree
        const toggleBtn = node.querySelector(".tree-toggle");
        if (toggleBtn) {
            toggleBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                const subtree = node.querySelector(".tree-subtree");
                if (subtree) {
                    const isHidden = subtree.style.display === "none";
                    subtree.style.display = isHidden ? "block" : "none";
                    toggleBtn.textContent = isHidden ? "▼" : "▶";
                }
            });
        }
    });

    // Click/Hover from SVG Canvas to Layer Tree
    svgLayers.forEach((layer) => {
        const layerId = layer.getAttribute("data-layer-id") || layer.id;
        if (!layerId) return;

        layer.addEventListener("mouseenter", () => {
            const targetNode = document.querySelector(`.tree-node[data-layer-id="${layerId}"]`);
            if (targetNode) {
                targetNode.classList.add("highlighted");
            }
        });

        layer.addEventListener("mouseleave", () => {
            const targetNode = document.querySelector(`.tree-node[data-layer-id="${layerId}"]`);
            if (targetNode) {
                targetNode.classList.remove("highlighted");
            }
        });

        layer.addEventListener("click", () => {
            const targetNode = document.querySelector(`.tree-node[data-layer-id="${layerId}"]`);
            if (targetNode) {
                // Switch to layers tab
                const layersTabBtn = document.querySelector('.tab-btn[data-tab="tabLayers"]');
                if (layersTabBtn) layersTabBtn.click();
                targetNode.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        });
    });
}

// Layer Search Filter
function initLayerSearch() {
    const searchInput = document.getElementById("layerSearchInput");
    const treeNodes = document.querySelectorAll(".tree-node");

    if (!searchInput) return;

    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        treeNodes.forEach((node) => {
            const title = node.querySelector(".node-title")?.textContent.toLowerCase() || "";
            const tag = node.querySelector(".node-tag")?.textContent.toLowerCase() || "";
            if (!query || title.includes(query) || tag.includes(query)) {
                node.style.display = "";
            } else {
                node.style.display = "none";
            }
        });
    });
}

// XML Code Viewer Actions
function initCodeViewer() {
    const copyBtn = document.getElementById("copyXmlBtn");
    const codePre = document.getElementById("xmlCodeBlock");

    if (copyBtn && codePre) {
        copyBtn.addEventListener("click", async () => {
            try {
                await navigator.clipboard.writeText(codePre.textContent);
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = "✓ Copied XML!";
                copyBtn.style.color = "#34d399";
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                    copyBtn.style.color = "";
                }, 2000);
            } catch (err) {
                alert("Failed to copy code to clipboard.");
            }
        });
    }
}
