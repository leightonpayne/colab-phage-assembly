export default {
    render({ model, el }) {
        const container = document.createElement('div');
        container.style.width = '100%';
        el.appendChild(container);

        // Track collapsed state
        const collapsedCategories = new Set();
        let initialized = false;

        function renderUI() {
            container.innerHTML = '';
            const root = document.createElement('div');
            root.style.fontFamily = "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif";
            root.style.width = '100%';
            container.appendChild(root);

            const config = model.get('config') || {};
            const paramsSchema = model.get('params_schema') || {};

            // Initialize categories based on config defaults on first run
            if (!initialized && Object.keys(paramsSchema).length > 0) {
                const categoryStyles = config.category_styles || {};
                Object.keys(paramsSchema).forEach(cat => {
                    const catCfg = categoryStyles[cat] || {};
                    // If explicitly set to collapsed, or if no setting and we want a safe default
                    if (catCfg.collapsed === true) {
                        collapsedCategories.add(cat);
                    }
                });
                initialized = true;
            }
            const styles = `
                @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
                .pl-launcher { background: #ffffff; color: #1e293b; border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
                .pl-header { border-bottom: 2px solid #f1f5f9; padding-bottom: 20px; margin-bottom: 24px; }
                .pl-title { font-size: 22px; font-weight: 700; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 12px; }
                .pl-subtitle { font-size: 14px; color: #64748b; margin-top: 4px; }
                
                .cat-section { margin-bottom: 16px; border: 1px solid #f1f5f9; border-radius: 14px; overflow: hidden; transition: all 0.2s; }
                .cat-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; cursor: pointer; user-select: none; transition: background 0.2s; }
                .cat-header:hover { opacity: 0.9; }
                .cat-title-wrap { display: flex; align-items: center; gap: 10px; }
                .cat-badge { display: inline-flex; padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
                .cat-toggle { transition: transform 0.2s; color: #64748b; }
                .cat-toggle.is-collapsed { transform: rotate(-90deg); }
                
                .cat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; background: #f8fafc; padding: 20px; transition: all 0.3s ease-in-out; }
                .cat-grid.is-collapsed { display: none; }
                
                .param-item { display: flex; flex-direction: column; gap: 6px; }
                .param-label { font-size: 14px; font-weight: 600; color: #334155; }
                .param-desc { font-size: 11px; color: #64748b; line-height: 1.5; }
                .param-input { background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 12px; font-size: 13px; color: #1e293b; transition: all 0.2s; font-family: inherit; }
                .param-input:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
                .param-switch { display: flex; align-items: center; gap: 10px; cursor: pointer; }
                .param-switch input { width: 18px; height: 18px; accent-color: #6366f1; cursor: pointer; }
                .btn-action { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; padding: 8px 16px; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; transition: all 0.2s; width: fit-content; }
                .btn-action:hover { background: #e2e8f0; color: #1e293b; }
                .btn-run { background: #6366f1; color: #fff; border: none; padding: 14px 32px; border-radius: 10px; font-weight: 700; font-size: 15px; cursor: pointer; display: flex; align-items: center; gap: 10px; transition: all 0.2s; margin-top: 10px; }
                .btn-run:hover { background: #4f46e5; transform: translateY(-1px); }
                .btn-run:disabled { background: #94a3b8; cursor: not-allowed; transform: none; }
                .log-box { margin-top: 32px; background: #0f172a; border-radius: 12px; overflow: hidden; border: 1px solid #1e293b; }
                .log-header { background: #1e293b; padding: 10px 16px; font-size: 12px; font-weight: 700; color: #94a3b8; border-bottom: 1px solid #2d3748; display: flex; justify-content: space-between; }
                .log-content { padding: 16px; font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px; color: #e2e8f0; max-height: 350px; overflow-y: auto; white-space: pre-wrap; line-height: 1.6; }
                .btn-copy { 
                    appearance: none; -webkit-appearance: none; background: transparent; border: none; box-shadow: none;
                    display: flex; align-items: center; gap: 6px;
                    font-family: inherit; font-size: 11px; font-weight: 700; letter-spacing: 0px;
                    color: #64748b; /* Dimmer than header's #94a3b8 */
                    cursor: pointer; transition: color 0.15s ease;
                    padding: 0; margin: 0;
                }
                .btn-copy:hover { color: #f8fafc; }
                .btn-copy svg { width: 14px; height: 14px; stroke-width: 2.5; }
                .btn-download {
                    background: #10b981; color: white; border: none; padding: 14px 24px; border-radius: 10px;
                    font-weight: 700; font-size: 15px; cursor: pointer; display: flex; align-items: center; gap: 10px;
                    transition: all 0.2s; margin-top: 10px; margin-right: 12px;
                }
                .btn-download:hover { background: #059669; transform: translateY(-1px); }
                .spinner { animation: spin 1s linear infinite; }
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            `;

            const styleSheet = document.createElement('style');
            styleSheet.textContent = styles;
            root.appendChild(styleSheet);

            const main = document.createElement('div');
            main.className = 'pl-launcher';
            
            // Header
            const header = document.createElement('div');
            header.className = 'pl-header';
            header.innerHTML = `
                <h2 class="pl-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v20M2 12h20M5.5 5.5l13 13M18.5 5.5l-13 13"/></svg>
                    ${config.title || 'Pipeline Launcher'}
                </h2>
                <div class="pl-subtitle">${config.subtitle || 'Configure and run your pipeline'}</div>
            `;
            main.appendChild(header);

            function updateValue(name, val) {
                const vals = {...(model.get('params_values') || {})};
                vals[name] = val;
                model.set('params_values', vals);
                model.save_changes();
            }

            // Parameters
            const paramsContainer = document.createElement('div');
            Object.keys(paramsSchema).forEach(cat => {
                const isCollapsed = collapsedCategories.has(cat);
                const section = document.createElement('div');
                section.className = 'cat-section';
                
                const catStyle = (config.category_styles && config.category_styles[cat]) || { bg: '#e0e7ff', text: '#4338ca' };
                
                const catHeader = document.createElement('div');
                catHeader.className = 'cat-header';
                catHeader.style.background = isCollapsed ? '#ffffff' : catStyle.bg + '10'; // Subtle background when open
                catHeader.innerHTML = `
                    <div class="cat-title-wrap">
                        <div class="cat-badge" style="background: ${catStyle.bg}; color: ${catStyle.text}">${cat}</div>
                    </div>
                    <div class="cat-toggle ${isCollapsed ? 'is-collapsed' : ''}">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </div>
                `;
                
                catHeader.onclick = () => {
                    if (collapsedCategories.has(cat)) {
                        collapsedCategories.delete(cat);
                    } else {
                        collapsedCategories.add(cat);
                    }
                    renderUI(); // Re-render to update state
                };
                
                section.appendChild(catHeader);
                
                const grid = document.createElement('div');
                grid.className = `cat-grid ${isCollapsed ? 'is-collapsed' : ''}`;
                
                paramsSchema[cat].forEach(p => {
                    const item = document.createElement('div');
                    item.className = 'param-item';
                    
                    if (p.type === 'button') {
                        item.innerHTML = `
                            <div class="param-label">${p.label}</div>
                            <div class="param-desc">${p.desc}</div>
                            <button class="btn-action">${p.label}</button>
                        `;
                        item.querySelector('button').onclick = (e) => {
                            e.stopPropagation();
                            model.set('action_requested', p.name);
                            model.save_changes();
                        };
                    } else {
                        const currentValue = model.get('params_values')?.[p.name] ?? p.def;

                        if (p.type === 'bool' || p.type === 'switch') {
                            item.innerHTML = `
                                <label class="param-switch">
                                    <input type="checkbox" ${currentValue ? 'checked' : ''}>
                                    <span class="param-label">${p.label}</span>
                                </label>
                                <div class="param-desc" style="padding-left: 28px;">${p.desc}</div>
                            `;
                            const input = item.querySelector('input');
                            input.onclick = (e) => e.stopPropagation();
                            input.onchange = () => updateValue(p.name, input.checked);
                        } else if (p.type === 'select') {
                            const options = (p.options || []).map(opt => `<option value="${opt}" ${currentValue === opt ? 'selected' : ''}>${opt}</option>`).join('');
                            item.innerHTML = `
                                <div class="param-label">${p.label}</div>
                                <div class="param-desc">${p.desc}</div>
                                <select class="param-input">${options}</select>
                            `;
                            const select = item.querySelector('select');
                            select.onclick = (e) => e.stopPropagation();
                            select.onchange = () => updateValue(p.name, select.value);
                        } else {
                            item.innerHTML = `
                                <div class="param-label">${p.label}</div>
                                <div class="param-desc">${p.desc}</div>
                                <input class="param-input" type="${p.type === 'int' || p.type === 'float' ? 'number' : 'text'}" 
                                       value="${currentValue ?? ''}" 
                                       placeholder="${p.def ?? ''}">
                            `;
                            const input = item.querySelector('input');
                            input.onclick = (e) => e.stopPropagation();
                            input.oninput = () => {
                                let val = input.value;
                                if (p.type === 'int') val = parseInt(val);
                                if (p.type === 'float') val = parseFloat(val);
                                updateValue(p.name, val);
                            };
                        }
                    }
                    grid.appendChild(item);
                });
                section.appendChild(grid);
                paramsContainer.appendChild(section);
            });
            main.appendChild(paramsContainer);

            // Footer / Run
            const footer = document.createElement('div');
            footer.style.display = 'flex';
            footer.style.justifyContent = 'flex-end';
            
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'btn-download';
            downloadBtn.style.display = 'none'; // Hidden by default
            downloadBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                Download Results
            `;
            downloadBtn.onclick = () => {
                const dataUrl = model.get('result_file_data');
                const fileName = model.get('result_file_name');
                if (dataUrl && fileName) {
                    const a = document.createElement('a');
                    a.href = dataUrl;
                    a.download = fileName;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }
            };
            footer.appendChild(downloadBtn);

            const runBtn = document.createElement('button');
            runBtn.className = 'btn-run';
            runBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 3l14 9-14 9V3z"/></svg>
                Run Pipeline
            `;
            runBtn.onclick = () => {
                model.set('run_requested', true);
                model.save_changes();
            };
            footer.appendChild(runBtn);
            main.appendChild(footer);

            // Logs
            const logBox = document.createElement('div');
            logBox.className = 'log-box';
            logBox.innerHTML = `
                <div class="log-header">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <span>EXECUTION LOGS</span>
                        <button class="btn-copy" title="Copy to clipboard">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                            COPY LOGS
                        </button>
                    </div>
                    <span class="status-indicator">● IDLE</span>
                </div>
                <div class="log-content">${model.get('logs') || 'Ready...'}</div>
            `;
            main.appendChild(logBox);

            // Copy functionality
            const copyBtn = logBox.querySelector('.btn-copy');
            copyBtn.onclick = () => {
                const content = logBox.querySelector('.log-content').innerText;
                navigator.clipboard.writeText(content).then(() => {
                    const originalHTML = copyBtn.innerHTML;
                    copyBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> COPIED`;
                    copyBtn.style.color = '#4ade80';
                    setTimeout(() => {
                        copyBtn.innerHTML = originalHTML;
                        copyBtn.style.color = '';
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                });
            };

            root.appendChild(main);

            // Reactivity for logs and status
            const formatLog = (text) => {
                if (!text) return '';
                const parts = text.split(/(\x1b\[[\d;]*m)/);
                let html = '';
                let openSpans = 0;
                
                const colors = {
                    '30': 'color:#94a3b8', '31': 'color:#ef4444', '32': 'color:#22c55e', '33': 'color:#eab308',
                    '34': 'color:#3b82f6', '35': 'color:#a855f7', '36': 'color:#06b6d4', '37': 'color:#f8fafc',
                    '90': 'color:#64748b', '91': 'color:#f87171', '92': 'color:#4ade80', '93': 'color:#facc15',
                    '94': 'color:#60a5fa', '95': 'color:#c084fc', '96': 'color:#22d3ee', '97': 'color:#ffffff',
                };
                
                parts.forEach(part => {
                    if (part.startsWith('\x1b[')) {
                        const content = part.slice(2, -1);
                        const codes = content.split(';').map(c => c.trim()).filter(c => c.length > 0);
                        if (codes.length === 0) codes.push('0');
                        
                        codes.forEach(code => {
                            if (code === '0') {
                                html += '</span>'.repeat(openSpans);
                                openSpans = 0;
                            } else if (code === '1') {
                                html += '<span style="font-weight:700">';
                                openSpans++;
                            } else if (code === '4') {
                                html += '<span style="text-decoration:underline">';
                                openSpans++;
                            } else if (colors[code]) {
                                html += `<span style="${colors[code]}">`;
                                openSpans++;
                            }
                        });
                    } else {
                         html += part
                            .replace(/&/g, '&amp;')
                            .replace(/</g, '&lt;')
                            .replace(/>/g, '&gt;');
                    }
                });
                
                html += '</span>'.repeat(openSpans);
                return html;
            };

            const updateLogs = () => {
                const content = logBox.querySelector('.log-content');
                if (content) {
                    content.innerHTML = formatLog(model.get('logs'));
                    content.scrollTop = content.scrollHeight;
                }
            };
            model.off('change:logs'); // Avoid duplicate listeners on re-render
            model.on('change:logs', updateLogs);

            const updateStatus = () => {
                const state = model.get('status_state');
                const indicator = logBox.querySelector('.status-indicator');
                if (indicator) {
                    indicator.innerText = `● ${state.toUpperCase()}`;
                    indicator.style.color = state === 'running' ? '#327ab6' : (state === 'error' || state === 'aborted' ? '#ef4444' : '#10b981');
                }
                const isRunning = state === 'running';
                
                // When running, the button becomes a "Stop" button
                if (isRunning) {
                    runBtn.disabled = false;
                    runBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect></svg> Abort`;
                    runBtn.style.background = '#ef4444';
                    runBtn.onclick = () => {
                        runBtn.disabled = true;
                        runBtn.innerHTML = `Aborting...`;
                        model.set('terminate_requested', true);
                        model.save_changes();
                    };
                    main.querySelectorAll('.btn-action').forEach(btn => btn.disabled = true);
                } else {
                    runBtn.disabled = false;
                    runBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 3l14 9-14 9V3z"/></svg> Run`;
                    runBtn.style.background = '#6366f1';
                    runBtn.onclick = () => {
                        model.set('run_requested', true);
                        model.save_changes();
                    };
                    main.querySelectorAll('.btn-action').forEach(btn => btn.disabled = false);
                }
            };
            model.off('change:status_state'); // Avoid duplicate listeners
            model.on('change:status_state', updateStatus);

            // Watch for result file to toggle download button
            const updateDownloadButton = () => {
                const hasResult = !!model.get('result_file_data');
                downloadBtn.style.display = hasResult ? 'flex' : 'none';
            };
            model.on('change:result_file_data', updateDownloadButton);
            updateDownloadButton(); // Check initial state

            // Initial status update
            updateStatus();
        }

        model.on('change:config', renderUI);
        model.on('change:params_schema', renderUI);

        renderUI();
    }
}
