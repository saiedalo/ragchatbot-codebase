// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalDokumente, dokumentTitel, newChatButton, themeToggle;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalDokumente = document.getElementById('totalDokumente');
    dokumentTitel = document.getElementById('dokumentTitel');
    newChatButton = document.getElementById('newChatButton');
    themeToggle = document.getElementById('themeToggle');

    setupEventListeners();
    initializeTheme();
    createNewSession();
    loadDokumentStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // New chat button
    newChatButton.addEventListener('click', startNewChat);

    // Theme toggle
    themeToggle.addEventListener('click', toggleTheme);

    // Keyboard shortcut for theme toggle (Ctrl/Cmd + Shift + T)
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'T') {
            e.preventDefault();
            toggleTheme();
        }
    });

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Anfrage fehlgeschlagen');

        const data = await response.json();

        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources, data.source_links);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Fehler: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, sourceLinks = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;

    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);

    let html = `<div class="message-content">${displayContent}</div>`;

    if (sources && sources.length > 0) {
        // Create sources with clickable links when available
        const sourcesHtml = sources.map((source, index) => {
            const link = sourceLinks && sourceLinks[index];
            if (link) {
                return `<a href="${link}" target="_blank" class="source-link">${source}</a>`;
            } else {
                return source;
            }
        }).join(', ');

        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Quellen</summary>
                <div class="sources-content">${sourcesHtml}</div>
            </details>
        `;
    }

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function startNewChat() {
    // Clear the current session on backend if exists
    if (currentSessionId) {
        try {
            await fetch(`${API_URL}/clear-session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: currentSessionId
                })
            });
        } catch (error) {
            console.error('Fehler beim Löschen der Sitzung:', error);
            // Continue with frontend cleanup even if backend fails
        }
    }

    // Clear frontend state and UI
    await createNewSession();
}

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    chatInput.value = '';
    chatInput.disabled = false;
    sendButton.disabled = false;
    addMessage('Willkommen beim Regulierungs-Assistenten! Ich beantworte Ihre Fragen zu deutschen Finanzregulierungen, BaFin-Vorschriften, MaRisk-Anforderungen und Compliance. Womit kann ich Ihnen helfen?', 'assistant', null, null, true);
}

// Load document statistics
function getDokumentKuerzel(titel) {
    if (/marisk/i.test(titel)) return 'MaRisk';
    if (/bait|rundschreiben 10\/2017/i.test(titel)) return 'BAIT';
    if (/gwg|geldwäsch/i.test(titel)) return 'GwG';
    if (/bundesbank|merkblatt/i.test(titel)) return 'Merkblatt';
    return titel.substring(0, 6).trim();
}

function getDokumentKurzbeschreibung(titel) {
    if (/marisk/i.test(titel)) return 'Mindestanforderungen Risikomanagement';
    if (/bait|rundschreiben 10\/2017/i.test(titel)) return 'Bankaufsichtl. Anforderungen IT';
    if (/gwg|geldwäsch/i.test(titel)) return 'Auslegungs- und Anwendungshinweise';
    if (/bundesbank/i.test(titel)) return 'Merkblatt Finanzdienstleistungen';
    return titel.length > 50 ? titel.substring(0, 50) + '…' : titel;
}

function normalizeHerausgeber(herausgeber, titel) {
    // Normalize noisy PDF-extracted publisher strings to clean group names
    if (!herausgeber || /^\.\.\//.test(herausgeber)) {
        // Fallback: infer from title
        if (/bundesbank/i.test(titel)) return 'Deutsche Bundesbank';
        return 'BaFin';
    }
    if (/bundesbank/i.test(herausgeber)) return 'Deutsche Bundesbank';
    if (/bafin|bundesanstalt|finanzdienstleistungsaufsicht/i.test(herausgeber)) return 'BaFin';
    return herausgeber;
}

function renderDokumentListe(dokumente) {
    // Normalize and group by issuer
    const gruppen = {};
    const gruppenOrder = [];
    for (const dok of dokumente) {
        const gruppe = normalizeHerausgeber(dok.herausgeber, dok.titel);
        if (!gruppen[gruppe]) {
            gruppen[gruppe] = [];
            gruppenOrder.push(gruppe);
        }
        gruppen[gruppe].push(dok);
    }

    // BaFin first, then others
    gruppenOrder.sort((a, b) => {
        if (a === 'BaFin') return -1;
        if (b === 'BaFin') return 1;
        return a.localeCompare(b, 'de');
    });

    let html = '';
    for (const gruppenName of gruppenOrder) {
        const docs = gruppen[gruppenName];
        html += `<div class="dok-gruppe">
            <div class="dok-gruppe-header">${escapeHtml(gruppenName)}</div>`;
        for (const dok of docs) {
            const kuerzel = getDokumentKuerzel(dok.titel);
            const kurzbeschreibung = getDokumentKurzbeschreibung(dok.titel);
            // Only use http/https URLs — not local file paths
            const isExternalLink = dok.dokument_quelle && /^https?:\/\//.test(dok.dokument_quelle);
            const link = isExternalLink
                ? `href="${escapeHtml(dok.dokument_quelle)}" target="_blank" rel="noopener"`
                : '';
            const tag = link ? 'a' : 'div';
            html += `<${tag} class="dok-karte${link ? ' dok-karte--link' : ''}" ${link}>
                <span class="dok-badge">${escapeHtml(kuerzel)}</span>
                <span class="dok-beschreibung">${escapeHtml(kurzbeschreibung)}</span>
            </${tag}>`;
        }
        html += '</div>';
    }
    return html;
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

async function loadDokumentStats() {
    try {
        console.log('Lade Dokumentstatistiken...');
        const response = await fetch(`${API_URL}/dokumente`);
        if (!response.ok) throw new Error('Dokumentstatistiken konnten nicht geladen werden');

        const data = await response.json();
        console.log('Dokumentdaten empfangen:', data);

        // Update stats in UI
        if (totalDokumente) {
            totalDokumente.textContent = data.gesamt_dokumente;
        }

        // Update document list
        if (dokumentTitel) {
            const dokumente = data.dokumente || [];
            if (dokumente.length > 0) {
                dokumentTitel.innerHTML = renderDokumentListe(dokumente);
            } else {
                dokumentTitel.innerHTML = '<span class="no-courses">Keine Dokumente verfügbar</span>';
            }
        }

    } catch (error) {
        console.error('Fehler beim Laden der Dokumentstatistiken:', error);
        // Set default values on error
        if (totalDokumente) {
            totalDokumente.textContent = '0';
        }
        if (dokumentTitel) {
            dokumentTitel.innerHTML = '<span class="error">Dokumente konnten nicht geladen werden</span>';
        }
    }
}

// Theme Functions
function initializeTheme() {
    // Get saved theme preference or default to dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}

function setTheme(theme) {
    if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
        themeToggle.setAttribute('aria-label', 'Zu dunklem Farbschema wechseln');
    } else {
        document.documentElement.removeAttribute('data-theme');
        themeToggle.setAttribute('aria-label', 'Zu hellem Farbschema wechseln');
    }

    // Save theme preference
    localStorage.setItem('theme', theme);
}
