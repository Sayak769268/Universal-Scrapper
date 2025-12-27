document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('urlInput');
    const scrapeBtn = document.getElementById('scrapeBtn');
    const clearBtn = document.getElementById('clearBtn');
    const loadingDiv = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const errorDiv = document.getElementById('error');
    
    // Clear / Reset action
    clearBtn.addEventListener('click', () => {
        urlInput.value = '';
        scrapeBtn.disabled = true;
        urlInput.focus();
        resultsDiv.classList.add('hidden');
        errorDiv.classList.add('hidden');
        // Optional: clear interactions/meta if needed
    });
    
    // Enable scrape button check
    urlInput.addEventListener('input', () => {
        scrapeBtn.disabled = !urlInput.value;
    });
    const metaInfoDiv = document.getElementById('metaInfo');
    const sectionsListDiv = document.getElementById('sectionsList');
    const interactionsInfoDiv = document.getElementById('interactionsInfo');
    const downloadBtn = document.getElementById('downloadBtn');

    let currentResult = null;

    scrapeBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) return;

        // Reset UI
        resultsDiv.classList.add('hidden');
        errorDiv.classList.add('hidden');
        loadingDiv.classList.remove('hidden');
        scrapeBtn.disabled = true;
        scrapeBtn.textContent = 'Scraping...';

        try {
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url })
            });

            const data = await response.json();
            
            if (!response.ok) {
                 throw new Error(data.detail || 'Failed to scrape URL');
            }

            currentResult = data.result;
            
            // Check for explicit scraper errors even if 200 OK
            if (currentResult.errors && currentResult.errors.length > 0) {
                 // We can display a warning, but still show partial results
                 renderErrorWarning(currentResult.errors);
            }

            renderResults(currentResult);
        } catch (err) {
            errorDiv.innerHTML = `<strong>Error:</strong> ${err.message}`;
            errorDiv.classList.remove('hidden');
        } finally {
            loadingDiv.classList.add('hidden');
            scrapeBtn.disabled = false;
            scrapeBtn.textContent = 'Scrape URL';
        }
    });

    downloadBtn.addEventListener('click', () => {
        if (!currentResult) return;
        const blob = new Blob([JSON.stringify({ result: currentResult }, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'scrape-result.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    function renderErrorWarning(errors) {
        // Just show the first error as a warning for now
        const msg = errors.map(e => `[${e.phase}] ${e.message}`).join('<br>');
        errorDiv.innerHTML = `<strong>Warning (Partial Result):</strong><br>${msg}`;
        errorDiv.classList.remove('hidden');
    }

    function renderResults(result) {
        // Render Meta
        metaInfoDiv.innerHTML = `
            <div class="meta-card">
                <h2>${escapeHtml(result.meta.title || "No Title Detected")}</h2>
                <div class="meta-grid">
                    <div class="meta-item">
                        <label>URL</label>
                        <span><a href="${result.url}" target="_blank">${escapeHtml(result.url)}</a></span>
                    </div>
                    <div class="meta-item">
                        <label>Description</label>
                        <span>${escapeHtml(result.meta.description || "N/A")}</span>
                    </div>
                    <div class="meta-item">
                        <label>Language</label>
                        <span>${escapeHtml(result.meta.language || "N/A")}</span>
                    </div>
                    <div class="meta-item">
                        <label>Scraped At</label>
                        <span>${formatDate(result.scrapedAt)}</span>
                    </div>
                </div>
            </div>
        `;

        // Render Sections
        sectionsListDiv.innerHTML = '';
        if (result.sections.length === 0) {
                const blockedError = result.errors.find(e => e.phase === 'analysis_tip');
                if (blockedError) {
                    sectionsListDiv.innerHTML = `
                        <div class="section-card" style="padding: 2rem; border-left: 5px solid #ff4444; background: #fff5f5;">
                            <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                                <span style="font-size: 2rem;">🛡️</span>
                                <div>
                                    <h3 style="margin: 0; color: #cc0000; font-size: 1.25rem;">Access Restricted</h3>
                                    <p style="margin: 0.25rem 0 0 0; color: #b91c1c;">The target website blocked the scraper.</p>
                                </div>
                            </div>
                            <div style="background: white; padding: 1rem; border-radius: 0.5rem; border: 1px solid #fed7d7;">
                                <strong style="display: block; margin-bottom: 0.5rem; color: #991b1b; font-size: 0.9rem;">REASON / TIP:</strong>
                                <p style="margin: 0; color: #7f1d1d; font-size: 0.95rem; line-height: 1.5;">${escapeHtml(blockedError.message)}</p>
                            </div>
                        </div>
                    `;
                } else {
                    sectionsListDiv.innerHTML = `
                        <div class="section-card" style="padding: 2rem; text-align: center; color: var(--text-secondary);">
                            <p>No sections were detected. The page might be empty, or handled strictly by unknown scripts.</p>
                        </div>
                    `;
                }
        } else {
            result.sections.forEach(section => {
                const card = document.createElement('div');
                card.className = 'section-card';
                card.innerHTML = `
                    <div class="section-header">
                        <div class="section-title-group">
                            <span class="badge">${section.type}</span>
                            <h3>${escapeHtml(section.label)}</h3>
                        </div>
                        <span class="chevron">▼</span>
                    </div>
                    <div class="section-content">
                        <pre>${escapeHtml(JSON.stringify(section, null, 2))}</pre>
                    </div>
                `;
                
                const header = card.querySelector('.section-header');
                const content = card.querySelector('.section-content');
                const chevron = card.querySelector('.chevron');
                
                header.addEventListener('click', () => {
                   const isOpen = content.classList.contains('open');
                   content.classList.toggle('open');
                   chevron.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
                });

                sectionsListDiv.appendChild(card);
                
                // Add copy functionality
                const copyBtn = document.createElement('button');
                copyBtn.className = 'copy-btn';
                copyBtn.textContent = 'Copy JSON';
                copyBtn.onclick = (e) => {
                    e.stopPropagation();
                    navigator.clipboard.writeText(JSON.stringify(section, null, 2));
                    const originalText = copyBtn.textContent;
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => copyBtn.textContent = originalText, 2000);
                };
                
                // Insert copy button into content area header or top right
                // Let's put it inside the content div, top right
                content.style.position = 'relative';
                content.prepend(copyBtn);
            });
        }

        // Render Interactions
        const interactions = result.interactions;
        const hasInteractions = interactions.scrolls > 0 || interactions.pages.length > 0 || interactions.clicks.length > 0;

        if (hasInteractions) {
            interactionsInfoDiv.classList.remove('hidden');
            interactionsInfoDiv.innerHTML = `
                <h2>Interaction Details</h2>
                <div class="interaction-grid">
                    <div class="interaction-stat">
                        <label>Scrolls</label>
                        <span>${interactions.scrolls}</span>
                    </div>
                    <div class="interaction-stat">
                        <label>Pages</label>
                        <span>${interactions.pages.length}</span>
                    </div>
                    <div class="interaction-stat">
                        <label>Clicks</label>
                        <span>${interactions.clicks.length}</span>
                    </div>
                </div>
                ${interactions.clicks.length > 0 ? 
                    `<div style="margin-top: 1rem;">
                        <strong>Clicked Elements:</strong>
                        <ul style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.5rem; list-style-position: inside;">
                            ${interactions.clicks.map(c => `<li>${c}</li>`).join('')}
                        </ul>
                    </div>` : ''}
            `;
        } else {
            interactionsInfoDiv.classList.add('hidden');
            interactionsInfoDiv.innerHTML = '';
        }


        resultsDiv.classList.remove('hidden');
    }

    function formatDate(isoString) {
        if (!isoString) return "N/A";
        try {
            return new Date(isoString).toLocaleString();
        } catch (e) {
            return isoString;
        }
    }

    function escapeHtml(text) {
        if (!text) return "";
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
