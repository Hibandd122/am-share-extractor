/**
 * NEXUS ALIGHT EXTRACTOR - Main Frontend Logic & Utilities
 */

const HISTORY_KEY = "nexus_am_extract_history_v1";

document.addEventListener("DOMContentLoaded", () => {
    initUrlControls();
    initModeSelection();
    initHistory();
    initQuickInspect();
});

// Toast Notifications System
function showToast(message, type = "info", duration = 3500) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    const iconMap = {
        success: "✓",
        error: "✕",
        info: "ℹ"
    };

    toast.innerHTML = `
        <span style="font-weight: bold;">${iconMap[type] || "•"}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(30px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// URL Input and Helper Controls
function initUrlControls() {
    const input = document.getElementById("urlInput");
    const pasteBtn = document.getElementById("pasteBtn");
    const clearBtn = document.getElementById("clearBtn");
    const form = document.getElementById("extractForm");
    const submitBtn = document.getElementById("submitBtn");
    const previewBtn = document.getElementById("previewBtn");

    if (pasteBtn && input) {
        pasteBtn.addEventListener("click", async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text && text.trim()) {
                    input.value = text.trim();
                    showToast("Pasted share link from clipboard!", "success");
                    validateUrl(input.value);
                }
            } catch (err) {
                showToast("Please allow clipboard permissions or paste manually.", "error");
            }
        });
    }

    if (clearBtn && input) {
        clearBtn.addEventListener("click", () => {
            input.value = "";
            input.focus();
            const drawer = document.getElementById("inspectDrawer");
            if (drawer) drawer.style.display = "none";
        });
    }

    if (previewBtn && input) {
        previewBtn.addEventListener("click", () => {
            const url = input.value.trim();
            if (!url) {
                showToast("Please enter an Alight Motion share link first.", "info");
                input.focus();
                return;
            }
            window.location.href = `/preview?url=${encodeURIComponent(url)}`;
        });
    }

    if (form && submitBtn) {
        form.addEventListener("submit", (e) => {
            const url = input.value.trim();
            if (!url) {
                e.preventDefault();
                showToast("Please provide a valid share link.", "error");
                return;
            }

            submitBtn.classList.add("loading");
            // Remove loading state after a few seconds if downloading file
            setTimeout(() => {
                submitBtn.classList.remove("loading");
            }, 3000);
        });
    }
}

// Mode Selection Highlights
function initModeSelection() {
    const modeCards = document.querySelectorAll(".mode-card");
    modeCards.forEach((card) => {
        const radio = card.querySelector("input[type='radio']");
        card.addEventListener("click", () => {
            modeCards.forEach((c) => c.classList.remove("selected"));
            card.classList.add("selected");
            if (radio) radio.checked = true;
        });
    });
}

// Quick Inspect via AJAX API
function initQuickInspect() {
    const input = document.getElementById("urlInput");
    const inspectBtn = document.getElementById("inspectBtn");
    const drawer = document.getElementById("inspectDrawer");

    if (!inspectBtn || !input || !drawer) return;

    inspectBtn.addEventListener("click", async () => {
        const url = input.value.trim();
        if (!url) {
            showToast("Enter a share link to inspect metadata.", "info");
            input.focus();
            return;
        }

        inspectBtn.classList.add("loading");
        try {
            const res = await fetch(`/api/info?url=${encodeURIComponent(url)}`);
            const data = await res.json();

            if (!res.ok || !data.success) {
                showToast(data.error || "Failed to inspect project.", "error");
                return;
            }

            // Fill inspect fields
            document.getElementById("statTitle").textContent = data.metadata.title;
            document.getElementById("statRes").textContent = data.metadata.resolution;
            document.getElementById("statFps").textContent = `${data.metadata.fps} FPS`;
            document.getElementById("statDuration").textContent = data.metadata.duration_formatted;
            document.getElementById("statLayers").textContent = data.metadata.total_layers;
            document.getElementById("statMedia").textContent = data.package.media_count;

            drawer.style.display = "block";
            showToast("Project metadata analyzed successfully!", "success");

            // Save to history
            saveToHistory({
                url: url,
                title: data.metadata.title,
                resolution: data.metadata.resolution,
                layers: data.metadata.total_layers,
                timestamp: Date.now()
            });

        } catch (err) {
            showToast("Network error or invalid link format.", "error");
        } finally {
            inspectBtn.classList.remove("loading");
        }
    });
}

// LocalStorage History
function getHistory() {
    try {
        const raw = localStorage.getItem(HISTORY_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function saveToHistory(item) {
    let list = getHistory();
    // Remove duplicates
    list = list.filter((i) => i.url !== item.url);
    list.unshift(item);
    if (list.length > 10) list.pop();
    localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
    renderHistory();
}

function initHistory() {
    const clearBtn = document.getElementById("clearHistoryBtn");
    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            localStorage.removeItem(HISTORY_KEY);
            renderHistory();
            showToast("Extraction history cleared.", "info");
        });
    }
    renderHistory();
}

function renderHistory() {
    const listEl = document.getElementById("historyList");
    const container = document.getElementById("historyContainer");
    if (!listEl || !container) return;

    const items = getHistory();
    if (items.length === 0) {
        container.style.display = "none";
        return;
    }

    container.style.display = "block";
    listEl.innerHTML = "";

    items.forEach((item) => {
        const li = document.createElement("li");
        li.className = "history-item";

        const timeStr = new Date(item.timestamp).toLocaleDateString();

        li.innerHTML = `
            <div class="history-info">
                <div class="history-title">${escapeHtml(item.title || "Alight Motion Project")}</div>
                <div class="history-url">${escapeHtml(item.url)} · ${item.resolution || "1080p"} · ${item.layers || "?"} layers</div>
            </div>
            <div class="history-actions">
                <button class="history-btn use-btn" title="Use URL">Fill</button>
                <a href="/preview?url=${encodeURIComponent(item.url)}" class="history-btn" title="Open in Studio">Studio</a>
            </div>
        `;

        li.querySelector(".use-btn").addEventListener("click", () => {
            const input = document.getElementById("urlInput");
            if (input) {
                input.value = item.url;
                input.focus();
                showToast("Loaded link from history.", "info");
            }
        });

        listEl.appendChild(li);
    });
}

function validateUrl(url) {
    return /alightcreative\.com\/am\/share\/u\//i.test(url) || /alight\.link/i.test(url);
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
