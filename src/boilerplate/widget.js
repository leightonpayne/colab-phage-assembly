export default {
    render({ model, el }) {
        const container = document.createElement('div');
        container.style.width = '100%';
        el.appendChild(container);

        let initialized = false;
        let logOffset = 0;
        let pollInterval = null;
        const collapsedCategories = new Set();

        // 1. UTILITIES
        const formatLog = (text) => {
            if (!text) return '';
            
            // HTML Escape
            let html = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            // ANSI to HTML
            const colors = {
                '1': 'font-weight:bold',
                '31': 'color:#f87171', // Red
                '32': 'color:#4ade80', // Green
                '33': 'color:#fbbf24', // Yellow
                '34': 'color:#60a5fa', // Blue
                '35': 'color:#c084fc', // Magenta
                '36': 'color:#22d3ee', // Cyan
                '90': 'color:#94a3b8'  // Gray
            };

            // Simplified ANSI parser
            html = html.replace(/\u001b\[([0-9;]+)m/g, (match, p1) => {
                const codes = p1.split(';');
                if (codes.includes('0')) return '</span>'.repeat(10); 
                const styles = codes.map(c => colors[c]).filter(Boolean);
                if (styles.length > 0) return `<span style="${styles.join(';')}">`;
                return '';
            });

            return html.replace(/\n/g, '<br>');
        };

        const clearUI = () => {
            const content = container.querySelector('.log-content');
            if (content) {
                content.innerHTML = '<div class="ready-placeholder">Ready...</div>';
            }
            logOffset = 0;
        };

        const appendLogs = (text, totalLength) => {
            if (!text || text.length === 0) return;
            const content = container.querySelector('.log-content');
            if (!content) return;

            // Clear placeholder on first real content
            if (content.querySelector('.ready-placeholder')) {
                content.innerHTML = '';
            }

            content.insertAdjacentHTML('beforeend', formatLog(text));
            content.scrollTop = content.scrollHeight;
            
            if (totalLength !== undefined) {
                logOffset = totalLength;
            } else {
                logOffset += text.length;
            }
        };

        const clearPolling = () => {
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
        };

        // 2. PRIMARY SYNC HANDLERS (MESSAGE BASED)
        const startPolling = () => {
            // We ALWAYS poll. This ensures reliability in any network condition.
            if (pollInterval) return; // Already running
            
            const scheduleNext = () => {
                pollInterval = setTimeout(() => {
                    const state = model.get('status_state');
                    if (state === 'running') {
                        model.send({ type: 'poll', offset: logOffset });
                        scheduleNext();
                    } else {
                        // One final poll to catch race conditions at the end of a run
                        model.send({ type: 'poll', offset: logOffset });
                        pollInterval = null;
                    }
                }, 250);
            };
            scheduleNext();
        };

        const handleCustomMessage = (msg) => {
            if (msg.type === 'log_batch') {
                // VERY IMPORTANT: Only process logs beyond our current offset to avoid repetition
                // from multiple widget instances or stale poll responses.
                if (msg.new_offset !== undefined && msg.new_offset > logOffset) {
                    const content = msg.content || '';
                    const msgStartOffset = msg.new_offset - content.length;
                    
                    if (msgStartOffset >= logOffset) {
                        // Perfect match or gap (append all)
                        appendLogs(content, msg.new_offset);
                    } else {
                        // Overlap (append only the new part)
                        const overlap = logOffset - msgStartOffset;
                        if (overlap < content.length) {
                            appendLogs(content.substring(overlap), msg.new_offset);
                        }
                    }
                }
                
                // Status sync from message (very high priority source of truth)
                if (msg.status && msg.status !== model.get('status_state')) {
                    model.set('status_state', msg.status);
                    updateStatus();
                }
            } else if (msg.type === 'result_ready') {
                // Priority sync for heavy result data via message
                if (msg.data) {
                    model.set('result_file_data', msg.data);
                    model.set('result_file_name', msg.name);
                    updateDownloadButton();
                }
            } else if (msg.type === 'run_finished') {
                // Ensure everything is synced before stopping
                if (msg.status) model.set('status_state', msg.status);
                
                // Sync result metadata if provided
                if (msg.result_file_data) {
                    model.set('result_file_data', msg.result_file_data);
                    model.set('result_file_name', msg.result_file_name);
                }
                
                // Catch any remaining logs in the final signal, using same deduplication
                if (msg.logs && msg.logs.length > logOffset) {
                    appendLogs(msg.logs.substring(logOffset), msg.logs.length);
                }
                
                clearPolling();
                updateStatus();
                updateDownloadButton();
            }
        };

        // 3. UI STATE UPDATERS
        const updateStatus = () => {
            const state = model.get('status_state');
            const indicator = container.querySelector('.status-indicator');
            if (indicator) {
                indicator.innerText = `● ${state.toUpperCase()}`;
                indicator.style.color = state === 'running' ? '#327ab6' : (state === 'error' || state === 'aborted' ? '#ef4444' : '#10b981');
            }
            
            const runBtn = container.querySelector('.btn-run');
            if (!runBtn) return;

            const isRunning = state === 'running';
            if (isRunning) {
                if (!pollInterval) startPolling();
                runBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect></svg> Abort`;
                runBtn.style.background = '#ef4444';
                runBtn.onclick = () => {
                    model.set('terminate_requested', true);
                    model.save_changes();
                };
                container.querySelectorAll('.btn-action').forEach(btn => btn.disabled = true);
            } else {
                clearPolling();
                runBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 3l14 9-14 9V3z"/></svg> Run Pipeline`;
                runBtn.style.background = '#6366f1';
                runBtn.onclick = () => {
                    clearUI();
                    model.set('run_requested', true);
                    model.save_changes();
                };
                container.querySelectorAll('.btn-action').forEach(btn => btn.disabled = false);
            }
        };

        const updateDownloadButton = () => {
            const btn = container.querySelector('.btn-download');
            if (btn) {
                const hasData = !!model.get('result_file_data');
                btn.style.display = hasData ? 'flex' : 'none';
            }
        };

        // 4. MAIN RENDERER
        function renderUI() {
            // Check if we need to initialize the main skeleton
            if (!container.querySelector('.pl-launcher')) {
                const config = model.get('config') || {};
                container.innerHTML = `
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
                        .pl-launcher { background: #ffffff; color: #1e293b; border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); font-family: 'Plus Jakarta Sans', system-ui, sans-serif; }
                        .pl-header { border-bottom: 2px solid #f1f5f9; padding-bottom: 20px; margin-bottom: 24px; }
                        .pl-title { font-size: 22px; font-weight: 700; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 12px; }
                        .pl-subtitle { font-size: 14px; color: #64748b; margin-top: 4px; }
                        .cat-section { margin-bottom: 16px; border: 1px solid #f1f5f9; border-radius: 14px; overflow: hidden; }
                        .cat-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; cursor: pointer; user-select: none; }
                        .cat-badge { display: inline-flex; padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
                        .cat-toggle { transition: transform 0.2s; color: #64748b; }
                        .cat-toggle.is-collapsed { transform: rotate(-90deg); }
                        .cat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; background: #f8fafc; padding: 20px; }
                        .cat-grid.is-collapsed { display: none; }
                        .param-item { display: flex; flex-direction: column; gap: 6px; }
                        .param-label { font-size: 14px; font-weight: 600; color: #334155; }
                        .param-desc { font-size: 11px; color: #64748b; line-height: 1.5; }
                        .param-input { background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 12px; font-size: 13px; color: #1e293b; font-family: inherit; }
                        .param-switch { display: flex; align-items: center; gap: 10px; cursor: pointer; }
                        .btn-action { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; padding: 8px 16px; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; }
                        .btn-action:disabled { opacity: 0.5; cursor: not-allowed; }
                        .btn-run { color: #fff; border: none; padding: 14px 32px; border-radius: 10px; font-weight: 700; font-size: 15px; cursor: pointer; display: flex; align-items: center; gap: 10px; }
                        .btn-download { background: #10b981; color: white; border: none; padding: 14px 24px; border-radius: 10px; font-weight: 700; font-size: 15px; cursor: pointer; display: flex; align-items: center; gap: 10px; margin-right: 12px; }
                        .log-box { margin-top: 32px; background: #0f172a; border-radius: 12px; overflow: hidden; border: 1px solid #1e293b; }
                        .log-header { background: #1e293b; padding: 10px 16px; font-size: 12px; font-weight: 700; color: #94a3b8; display: flex; justify-content: space-between; }
                        .log-content { padding: 16px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #e2e8f0; max-height: 350px; overflow-y: auto; white-space: pre-wrap; line-height: 1.6; }
                        .btn-copy { background: transparent; border: none; font-size: 11px; font-weight: 700; color: #64748b; cursor: pointer; display: flex; align-items: center; gap: 6px; }
                        .ready-placeholder { color: #475569; font-style: italic; }
                    </style>
                    <div class="pl-launcher">
                        <div class="pl-header">
                            <h2 class="pl-title">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v20M2 12h20M5.5 5.5l13 13M18.5 5.5l-13 13"/></svg>
                                ${config.title || 'Pipeline Launcher'}
                            </h2>
                            <div class="pl-subtitle">${config.subtitle || 'Configure and run your pipeline'}</div>
                        </div>
                        <div class="params-container"></div>
                        <div class="footer" style="display: flex; justify-content: flex-end; margin-top: 20px;">
                            <button class="btn-download" style="display: none;">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg> Download Results
                            </button>
                            <button class="btn-run"></button>
                        </div>
                        <div class="log-box">
                            <div class="log-header">
                                <div style="display: flex; align-items: center; gap: 16px;">
                                    <span>EXECUTION LOGS</span>
                                    <button class="btn-copy">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> COPY LOGS
                                    </button>
                                </div>
                                <span class="status-indicator">● IDLE</span>
                            </div>
                            <div class="log-content">Ready...</div>
                        </div>
                    </div>
                `;

                container.querySelector('.btn-copy').onclick = () => {
                    navigator.clipboard.writeText(container.querySelector('.log-content').innerText);
                };
                container.querySelector('.btn-download').onclick = () => {
                    const a = document.createElement('a'); a.href = model.get('result_file_data'); a.download = model.get('result_file_name'); a.click();
                };
            }

            renderParams();
            updateStatus();
            updateDownloadButton();
        }

        function renderParams() {
            const config = model.get('config') || {};
            const paramsSchema = model.get('params_schema') || {};

            if (!initialized && Object.keys(paramsSchema).length > 0) {
                const categoryStyles = config.category_styles || {};
                Object.keys(paramsSchema).forEach(cat => {
                    if (categoryStyles[cat]?.collapsed === true) collapsedCategories.add(cat);
                });
                initialized = true;
            }

            const paramsContainer = container.querySelector('.params-container');
            if (!paramsContainer) return;

            paramsContainer.innerHTML = ''; // Only clear the params, not the whole widget
            Object.keys(paramsSchema).forEach(cat => {
                const isCollapsed = collapsedCategories.has(cat);
                const section = document.createElement('div');
                section.className = 'cat-section';
                const catStyle = config.category_styles?.[cat] || { bg: '#e0e7ff', text: '#4338ca' };
                
                section.innerHTML = `
                    <div class="cat-header" style="background: ${isCollapsed ? '#fff' : catStyle.bg + '10'}">
                        <div class="cat-title-wrap"><div class="cat-badge" style="background: ${catStyle.bg}; color: ${catStyle.text}">${cat}</div></div>
                        <div class="cat-toggle ${isCollapsed ? 'is-collapsed' : ''}">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                        </div>
                    </div>
                    <div class="cat-grid ${isCollapsed ? 'is-collapsed' : ''}"></div>
                `;
                section.querySelector('.cat-header').onclick = () => {
                    if (collapsedCategories.has(cat)) collapsedCategories.delete(cat);
                    else collapsedCategories.add(cat);
                    renderParams();
                };

                const grid = section.querySelector('.cat-grid');
                paramsSchema[cat].forEach(p => {
                    const item = document.createElement('div');
                    item.className = 'param-item';
                    const currentValue = model.get('params_values')?.[p.name] ?? p.def;

                    if (p.type === 'button') {
                        item.innerHTML = `<div class="param-label">${p.label}</div><div class="param-desc">${p.desc}</div><button class="btn-action">${p.label}</button>`;
                        item.querySelector('button').onclick = () => { clearUI(); model.set('action_requested', p.name); model.save_changes(); };
                    } else if (p.type === 'bool' || p.type === 'switch') {
                        item.innerHTML = `<label class="param-switch"><input type="checkbox" ${currentValue ? 'checked' : ''}><span class="param-label">${p.label}</span></label><div class="param-desc" style="padding-left: 28px;">${p.desc}</div>`;
                        item.querySelector('input').onchange = (e) => {
                            const vals = {...model.get('params_values')}; vals[p.name] = e.target.checked;
                            model.set('params_values', vals); model.save_changes();
                        };
                    } else if (p.type === 'select') {
                        const opts = (p.options || []).map(opt => `<option value="${opt}" ${currentValue === opt ? 'selected' : ''}>${opt}</option>`).join('');
                        item.innerHTML = `<div class="param-label">${p.label}</div><div class="param-desc">${p.desc}</div><select class="param-input">${opts}</select>`;
                        item.querySelector('select').onchange = (e) => {
                            const vals = {...model.get('params_values')}; vals[p.name] = e.target.value;
                            model.set('params_values', vals); model.save_changes();
                        };
                    } else {
                        item.innerHTML = `<div class="param-label">${p.label}</div><div class="param-desc">${p.desc}</div><input class="param-input" type="${p.type === 'int' || p.type === 'float' ? 'number' : 'text'}" value="${currentValue ?? ''}" placeholder="${p.def ?? ''}">`;
                        item.querySelector('input').oninput = (e) => {
                            let val = e.target.value;
                            if (p.type === 'int') val = parseInt(val);
                            if (p.type === 'float') val = parseFloat(val);
                            const vals = {...model.get('params_values')}; vals[p.name] = val;
                            model.set('params_values', vals); model.save_changes();
                        };
                    }
                    grid.appendChild(item);
                });
                paramsContainer.appendChild(section);
            });
        }

        // 5. EVENT HANDLERS (Registered ONCE)
        model.on('msg:custom', handleCustomMessage);
        
        model.on('change:status_state', updateStatus);
        
        // We still listen for config changes to allow UI updates
        model.on('change:config', renderUI);
        model.on('change:params_schema', renderUI);
        model.on('change:result_file_data', updateDownloadButton);

        renderUI();

        return () => {
            clearPolling();
            model.off('msg:custom', handleCustomMessage);
            model.off('change:config', renderUI);
            model.off('change:params_schema', renderUI);
        };
    }
}
