/**
 * Layer Workflow Editor
 * A simple but functional UI for managing Layer workflows.
 */

// =============================================================================
// Configuration
// =============================================================================

const API_BASE = '';  // Same origin
const API_KEY_STORAGE_KEY = 'layer_api_key';

// Action definitions with their parameters
const ACTION_PARAMS = {
    'open-app': [
        { name: 'app', type: 'select', label: 'Application', required: true, 
          options: ['slack', 'vscode', 'cursor', 'terminal', 'iterm', 'safari', 'chrome', 'firefox', 'notes', 'calendar', 'mail', 'messages', 'discord', 'finder', 'spotify', 'preview', 'textedit'] }
    ],
    'notify': [
        { name: 'title', type: 'text', label: 'Title', required: true },
        { name: 'message', type: 'text', label: 'Message', required: true },
        { name: 'subtitle', type: 'text', label: 'Subtitle', required: false }
    ],
    'speak': [
        { name: 'text', type: 'text', label: 'Text to speak', required: true },
        { name: 'voice', type: 'text', label: 'Voice name', required: false, placeholder: 'e.g., Samantha' },
        { name: 'rate', type: 'number', label: 'Speech rate', required: false, placeholder: '175' }
    ],
    'clipboard-get': [],
    'clipboard-set': [
        { name: 'text', type: 'text', label: 'Text to copy', required: true }
    ],
    'screenshot': [],
    'save-screenshot': [
        { name: 'filename', type: 'text', label: 'Filename (optional)', required: false, placeholder: 'e.g., bug_screenshot' }
    ],
    'create-note': [
        { name: 'title', type: 'text', label: 'Note title', required: true },
        { name: 'content', type: 'textarea', label: 'Note content', required: true }
    ],
    'open-url': [
        { name: 'url', type: 'text', label: 'URL', required: true, placeholder: 'https://...' }
    ],
    'volume': [
        { name: 'level', type: 'number', label: 'Volume level (0-100)', required: false, min: 0, max: 100 },
        { name: 'mute', type: 'checkbox', label: 'Mute', required: false }
    ],
    'sleep': [],
    'lock': [],
    'window-layout': [
        { name: 'layout', type: 'select', label: 'Layout', required: true,
          options: ['left-half', 'right-half', 'top-half', 'bottom-half', 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'first-third', 'center-third', 'last-third', 'first-two-thirds', 'last-two-thirds', 'maximize', 'almost-maximize', 'center', 'restore', 'smaller', 'larger'] },
        { name: 'app', type: 'text', label: 'App to focus first', required: false, placeholder: 'optional' }
    ],
    'run-shortcut': [
        { name: 'name', type: 'text', label: 'Shortcut name', required: true },
        { name: 'input', type: 'text', label: 'Input text', required: false }
    ],
    'pomodoro-start': [
        { name: 'work_duration', type: 'number', label: 'Work duration (min)', required: false, default: 25 },
        { name: 'break_duration', type: 'number', label: 'Break duration (min)', required: false, default: 5 },
        { name: 'focus_mode', type: 'checkbox', label: 'Enable focus mode (mute)', required: false }
    ],
    'pomodoro-stop': [],
    'pomodoro-status': [],
    'spotify-play': [
        { name: 'uri', type: 'text', label: 'Spotify URL or URI', required: false, placeholder: 'https://open.spotify.com/playlist/37i9dQZF1DX5trt9i14X7j',
          info: 'Leave empty to resume playback. Paste any Spotify link (URL) or URI. Just copy the link from Spotify\'s Share menu - both formats work!' }
    ],
    'spotify-pause': [],
    'spotify-next': [],
    'spotify-previous': [],
    'spotify-current': [],
    'spotify-volume': [
        { name: 'level', type: 'number', label: 'Volume (0-100)', required: true, min: 0, max: 100, placeholder: '50' }
    ],
    'spotify-shuffle': [
        { name: 'enabled', type: 'checkbox', label: 'Enable shuffle', required: false, default: true }
    ],
    'wallpaper': [
        { name: 'city', type: 'text', label: 'City for weather', required: false, placeholder: 'San Francisco',
          info: 'City name for weather data. Uses OpenWeatherMap.' },
        { name: 'show_weather', type: 'checkbox', label: 'Show weather', required: false, default: true },
        { name: 'show_calendar', type: 'checkbox', label: 'Show calendar events', required: false, default: true },
        { name: 'show_reminders', type: 'checkbox', label: 'Show reminders/tasks', required: false, default: true },
        { name: 'custom_message', type: 'text', label: 'Custom message', required: false, placeholder: 'Focus on what matters.',
          info: 'Optional message displayed at bottom of wallpaper' }
    ]
};

// =============================================================================
// State
// =============================================================================

let state = {
    workflows: [],
    currentWorkflow: null,
    currentWorkflowName: null,
    isNewWorkflow: false,
    editingStepIndex: null,
    apiKey: localStorage.getItem(API_KEY_STORAGE_KEY) || ''
};

// =============================================================================
// DOM Elements
// =============================================================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const elements = {
    workflowList: $('#workflow-list'),
    emptyState: $('#empty-state'),
    editor: $('#editor'),
    workflowName: $('#workflow-name'),
    workflowDescription: $('#workflow-description'),
    inputsContainer: $('#inputs-container'),
    noInputs: $('#no-inputs'),
    stepsContainer: $('#steps-container'),
    noSteps: $('#no-steps'),
    runOutputSection: $('#run-output-section'),
    runOutput: $('#run-output'),
    stepModal: $('#step-modal'),
    stepModalTitle: $('#step-modal-title'),
    stepAction: $('#step-action'),
    stepParamsContainer: $('#step-params-container'),
    stepDelay: $('#step-delay'),
    stepTimeAfter: $('#step-time-after'),
    stepTimeBefore: $('#step-time-before'),
    stepDays: $('#step-days'),
    variablesHint: $('#variables-hint'),
    deleteModal: $('#delete-modal'),
    deleteWorkflowName: $('#delete-workflow-name'),
    runModal: $('#run-modal'),
    runInputsContainer: $('#run-inputs-container'),
    noRunInputs: $('#no-run-inputs'),
    toast: $('#toast'),
    toastIcon: $('#toast-icon'),
    toastMessage: $('#toast-message'),
    connectionStatus: $('#connection-status')
};

// =============================================================================
// API Functions
// =============================================================================

async function apiRequest(method, path, body = null) {
    const headers = {
        'X-API-Key': state.apiKey,
        'Content-Type': 'application/json'
    };
    
    const options = { method, headers };
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch(`${API_BASE}${path}`, options);
    const data = await response.json();
    
    if (data.status === 'error') {
        throw new Error(data.message);
    }
    
    return data.data;
}

async function loadWorkflows() {
    try {
        const data = await apiRequest('GET', '/workflows');
        state.workflows = data.workflows || [];
        renderWorkflowList();
        updateConnectionStatus(true);
    } catch (error) {
        console.error('Failed to load workflows:', error);
        updateConnectionStatus(false);
        showToast('Failed to connect to API', 'error');
    }
}

async function loadWorkflow(name) {
    try {
        const data = await apiRequest('GET', `/workflows/${name}`);
        state.currentWorkflow = data;
        state.currentWorkflowName = name;
        state.isNewWorkflow = false;
        renderEditor();
    } catch (error) {
        showToast(`Failed to load workflow: ${error.message}`, 'error');
    }
}

async function saveWorkflow() {
    const name = elements.workflowName.value.trim().toLowerCase().replace(/\s+/g, '-');
    const description = elements.workflowDescription.value.trim();
    
    if (!name) {
        showToast('Workflow name is required', 'error');
        return;
    }
    
    const workflow = {
        description,
        inputs: state.currentWorkflow.inputs || [],
        steps: state.currentWorkflow.steps || []
    };
    
    try {
        await apiRequest('PUT', `/workflows/${name}`, workflow);
        
        // Update state
        if (state.isNewWorkflow || name !== state.currentWorkflowName) {
            state.currentWorkflowName = name;
            state.isNewWorkflow = false;
        }
        
        showToast('Workflow saved', 'success');
        await loadWorkflows();
        selectWorkflow(name);
    } catch (error) {
        showToast(`Failed to save: ${error.message}`, 'error');
    }
}

async function deleteWorkflow() {
    if (!state.currentWorkflowName) return;
    
    try {
        await apiRequest('DELETE', `/workflows/${state.currentWorkflowName}`);
        showToast('Workflow deleted', 'success');
        state.currentWorkflow = null;
        state.currentWorkflowName = null;
        hideEditor();
        await loadWorkflows();
    } catch (error) {
        showToast(`Failed to delete: ${error.message}`, 'error');
    }
    
    hideModal(elements.deleteModal);
}

async function runWorkflow(inputs = {}) {
    if (!state.currentWorkflowName) return;
    
    hideModal(elements.runModal);
    elements.runOutputSection.classList.remove('hidden');
    elements.runOutput.innerHTML = '<div class="text-night-400">Running...</div>';
    
    try {
        const data = await apiRequest('POST', `/run/${state.currentWorkflowName}`, inputs);
        renderRunOutput(data);
        showToast(`Workflow completed in ${data.duration_ms}ms`, 'success');
    } catch (error) {
        elements.runOutput.innerHTML = `<div class="text-red-400">Error: ${error.message}</div>`;
        showToast(`Run failed: ${error.message}`, 'error');
    }
}

// =============================================================================
// Render Functions
// =============================================================================

function renderWorkflowList() {
    elements.workflowList.innerHTML = state.workflows.map(w => `
        <div class="workflow-item px-3 py-2.5 rounded-lg cursor-pointer ${state.currentWorkflowName === w.name ? 'active' : ''}" 
             data-name="${w.name}">
            <div class="font-medium text-sm">${w.name}</div>
            <div class="text-xs text-night-500 truncate">${w.description || 'No description'}</div>
        </div>
    `).join('');
    
    // Attach click handlers
    $$('.workflow-item').forEach(el => {
        el.addEventListener('click', () => selectWorkflow(el.dataset.name));
    });
}

function renderEditor() {
    const wf = state.currentWorkflow;
    if (!wf) return;
    
    elements.emptyState.classList.add('hidden');
    elements.editor.classList.remove('hidden');
    
    elements.workflowName.value = wf.name || '';
    elements.workflowDescription.value = wf.description || '';
    
    renderInputs();
    renderSteps();
    elements.runOutputSection.classList.add('hidden');
}

function renderInputs() {
    const inputs = state.currentWorkflow.inputs || [];
    
    if (inputs.length === 0) {
        elements.inputsContainer.innerHTML = '';
        elements.noInputs.classList.remove('hidden');
        return;
    }
    
    elements.noInputs.classList.add('hidden');
    elements.inputsContainer.innerHTML = inputs.map((inp, i) => {
        const name = typeof inp === 'string' ? inp : inp.name;
        const defaultVal = typeof inp === 'object' ? inp.default || '' : '';
        
        return `
            <div class="flex items-center gap-2 bg-night-900 rounded-lg p-3 border border-night-800">
                <input type="text" value="${name}" placeholder="name" 
                    class="flex-1 bg-night-800 border border-night-700 rounded px-2 py-1.5 text-sm focus:border-accent focus:outline-none"
                    data-input-index="${i}" data-field="name">
                <span class="text-night-500 text-sm">default:</span>
                <input type="text" value="${defaultVal}" placeholder="optional" 
                    class="flex-1 bg-night-800 border border-night-700 rounded px-2 py-1.5 text-sm focus:border-accent focus:outline-none"
                    data-input-index="${i}" data-field="default">
                <button class="text-night-500 hover:text-red-400 p-1" data-remove-input="${i}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
    }).join('');
    
    // Attach handlers
    $$('[data-input-index]').forEach(el => {
        el.addEventListener('input', (e) => {
            const index = parseInt(e.target.dataset.inputIndex);
            const field = e.target.dataset.field;
            updateInput(index, field, e.target.value);
        });
    });
    
    $$('[data-remove-input]').forEach(el => {
        el.addEventListener('click', (e) => {
            const index = parseInt(e.target.closest('[data-remove-input]').dataset.removeInput);
            removeInput(index);
        });
    });
}

function renderSteps() {
    const steps = state.currentWorkflow.steps || [];
    
    if (steps.length === 0) {
        elements.stepsContainer.innerHTML = '';
        elements.noSteps.classList.remove('hidden');
        return;
    }
    
    elements.noSteps.classList.add('hidden');
    elements.stepsContainer.innerHTML = steps.map((step, i) => {
        const params = step.params || {};
        const paramSummary = Object.entries(params)
            .map(([k, v]) => `<span class="text-night-400">${k}:</span> <span class="text-accent">${truncate(String(v), 30)}</span>`)
            .join(', ');
        
        const isFirst = i === 0;
        const isLast = i === steps.length - 1;
        
        return `
            <div class="step-card bg-night-900 rounded-lg border border-night-800 overflow-hidden" data-step-index="${i}">
                <div class="flex items-center gap-3 p-3">
                    <!-- Reorder buttons -->
                    <div class="flex flex-col gap-0.5">
                        <button class="p-1 text-night-500 hover:text-white rounded hover:bg-night-800 ${isFirst ? 'opacity-30 cursor-not-allowed' : ''}" 
                            data-move-up="${i}" title="Move up" ${isFirst ? 'disabled' : ''}>
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"></path>
                            </svg>
                        </button>
                        <button class="p-1 text-night-500 hover:text-white rounded hover:bg-night-800 ${isLast ? 'opacity-30 cursor-not-allowed' : ''}" 
                            data-move-down="${i}" title="Move down" ${isLast ? 'disabled' : ''}>
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                        </button>
                    </div>
                    <div class="flex items-center justify-center w-6 h-6 bg-night-800 rounded text-xs font-mono text-night-400">${i + 1}</div>
                    <div class="flex-1 min-w-0">
                        <div class="font-medium text-sm flex items-center gap-2 flex-wrap">
                            <span class="text-accent">${step.action}</span>
                            ${step.delay ? `<span class="text-xs bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded">⏱ ${step.delay}s</span>` : ''}
                            ${step.time_after ? `<span class="text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">after ${step.time_after}</span>` : ''}
                            ${step.time_before ? `<span class="text-xs bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded">before ${step.time_before}</span>` : ''}
                            ${step.days?.length ? `<span class="text-xs bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded">${step.days.join(', ')}</span>` : ''}
                        </div>
                        ${paramSummary ? `<div class="text-xs text-night-400 mt-0.5 truncate font-mono">${paramSummary}</div>` : ''}
                    </div>
                    <div class="flex items-center gap-1">
                        <button class="p-1.5 text-night-400 hover:text-white rounded hover:bg-night-800" data-edit-step="${i}" title="Edit">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                            </svg>
                        </button>
                        <button class="p-1.5 text-night-400 hover:text-red-400 rounded hover:bg-night-800" data-remove-step="${i}" title="Delete">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Attach handlers
    $$('[data-edit-step]').forEach(el => {
        el.addEventListener('click', (e) => {
            const index = parseInt(e.target.closest('[data-edit-step]').dataset.editStep);
            openEditStep(index);
        });
    });
    
    $$('[data-remove-step]').forEach(el => {
        el.addEventListener('click', (e) => {
            const index = parseInt(e.target.closest('[data-remove-step]').dataset.removeStep);
            removeStep(index);
        });
    });
    
    // Move up handlers
    $$('[data-move-up]').forEach(el => {
        el.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-move-up]');
            if (btn.disabled) return;
            const index = parseInt(btn.dataset.moveUp);
            moveStep(index, index - 1);
        });
    });
    
    // Move down handlers
    $$('[data-move-down]').forEach(el => {
        el.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-move-down]');
            if (btn.disabled) return;
            const index = parseInt(btn.dataset.moveDown);
            moveStep(index, index + 1);
        });
    });
}

function renderStepParams(action) {
    const params = ACTION_PARAMS[action] || [];
    
    if (params.length === 0) {
        elements.stepParamsContainer.innerHTML = '<div class="text-night-500 text-sm">This action has no parameters.</div>';
        return;
    }
    
    // Helper to render info button
    const infoButton = (info) => info ? `
        <div class="relative inline-block ml-1 group">
            <button type="button" class="w-4 h-4 rounded-full bg-night-700 text-night-400 hover:bg-accent hover:text-white text-xs font-bold inline-flex items-center justify-center">?</button>
            <div class="absolute left-0 bottom-full mb-2 w-72 p-3 bg-night-800 border border-night-600 rounded-lg shadow-xl text-xs text-night-300 hidden group-hover:block z-50">
                ${info}
                <div class="absolute left-3 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-night-600"></div>
            </div>
        </div>
    ` : '';
    
    elements.stepParamsContainer.innerHTML = params.map(param => {
        const id = `param-${param.name}`;
        
        if (param.type === 'select') {
            return `
                <div>
                    <label for="${id}" class="text-sm font-medium text-night-300 mb-1.5 flex items-center">
                        ${param.label} ${param.required ? '' : '<span class="text-night-500 font-normal ml-1">(optional)</span>'}
                        ${infoButton(param.info)}
                    </label>
                    <select id="${id}" class="action-select w-full bg-night-800 border border-night-700 rounded-lg px-3 py-2 text-white appearance-none cursor-pointer focus:border-accent focus:outline-none">
                        <option value="">Select...</option>
                        ${param.options.map(opt => `<option value="${opt}">${opt}</option>`).join('')}
                    </select>
                </div>
            `;
        } else if (param.type === 'checkbox') {
            return `
                <div class="flex items-center gap-2">
                    <input type="checkbox" id="${id}" ${param.default ? 'checked' : ''} 
                        class="w-4 h-4 bg-night-800 border-night-700 rounded text-accent focus:ring-accent focus:ring-offset-night-900">
                    <label for="${id}" class="text-sm text-night-300 flex items-center">${param.label}${infoButton(param.info)}</label>
                </div>
            `;
        } else if (param.type === 'textarea') {
            return `
                <div>
                    <label for="${id}" class="text-sm font-medium text-night-300 mb-1.5 flex items-center">
                        ${param.label} ${param.required ? '' : '<span class="text-night-500 font-normal ml-1">(optional)</span>'}
                        ${infoButton(param.info)}
                    </label>
                    <textarea id="${id}" rows="3" placeholder="${param.placeholder || ''}"
                        class="w-full bg-night-800 border border-night-700 rounded-lg px-3 py-2 text-white placeholder-night-500 focus:border-accent focus:outline-none resize-none"></textarea>
                </div>
            `;
        } else {
            return `
                <div>
                    <label for="${id}" class="text-sm font-medium text-night-300 mb-1.5 flex items-center">
                        ${param.label} ${param.required ? '' : '<span class="text-night-500 font-normal ml-1">(optional)</span>'}
                        ${infoButton(param.info)}
                    </label>
                    <input type="${param.type}" id="${id}" placeholder="${param.placeholder || ''}"
                        ${param.min !== undefined ? `min="${param.min}"` : ''}
                        ${param.max !== undefined ? `max="${param.max}"` : ''}
                        class="w-full bg-night-800 border border-night-700 rounded-lg px-3 py-2 text-white placeholder-night-500 focus:border-accent focus:outline-none">
                </div>
            `;
        }
    }).join('');
}

function renderRunOutput(data) {
    const results = data.results || [];
    
    elements.runOutput.innerHTML = `
        <div class="flex items-center justify-between mb-3 pb-3 border-b border-night-700">
            <span class="text-night-400">Completed in ${data.duration_ms}ms</span>
            <span class="text-sm">
                <span class="text-green-400">${data.steps_executed} executed</span>
                ${data.steps_skipped > 0 ? `<span class="text-yellow-400 ml-2">${data.steps_skipped} skipped</span>` : ''}
            </span>
        </div>
        <div class="space-y-3">
            ${results.map(r => {
                const statusIcon = r.status === 'ok' 
                    ? '<span class="text-green-400">✓</span>'
                    : r.status === 'skipped' 
                        ? '<span class="text-yellow-400">○</span>'
                        : '<span class="text-red-400">✗</span>';
                
                // Format output nicely
                let outputHtml = '';
                if (r.output) {
                    // Check for image (base64)
                    if (r.output.image) {
                        const imgId = `img-${r.step}`;
                        outputHtml = `
                            <div class="mt-2 ml-7">
                                <img id="${imgId}" src="data:image/png;base64,${r.output.image}" 
                                     data-base64="${r.output.image}"
                                     class="max-w-md rounded border border-night-700 cursor-pointer hover:opacity-80 transition-all"
                                     onclick="downloadImage('${imgId}')"
                                     title="Click to download">
                                <div class="flex items-center gap-3 mt-1.5 text-xs">
                                    <span class="text-night-500">Click image to download</span>
                                    <button onclick="copyBase64('${imgId}')" class="text-accent hover:text-accent/80">Copy base64</button>
                                </div>
                            </div>`;
                    } else {
                        // Show other output fields
                        const fields = Object.entries(r.output)
                            .filter(([k, v]) => k !== 'success' && v !== undefined && v !== null && v !== '')
                            .map(([k, v]) => `<span class="text-night-500">${k}:</span> <span class="text-night-300">${truncate(String(v), 60)}</span>`)
                            .join(', ');
                        if (fields) {
                            outputHtml = `<div class="mt-1 ml-7 text-xs font-mono">${fields}</div>`;
                        }
                    }
                }
                
                if (r.reason) {
                    outputHtml = `<div class="mt-1 ml-7 text-xs text-yellow-400">${r.reason}</div>`;
                }
                
                return `
                    <div>
                        <div class="flex items-start gap-2 text-sm">
                            <span class="w-5 text-center">${statusIcon}</span>
                            <span class="text-night-300">Step ${r.step + 1}</span>
                            <span class="text-accent">${r.action}</span>
                        </div>
                        ${outputHtml}
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

// =============================================================================
// Action Handlers
// =============================================================================

function selectWorkflow(name) {
    state.currentWorkflowName = name;
    renderWorkflowList();
    loadWorkflow(name);
}

function createNewWorkflow() {
    state.currentWorkflow = {
        name: '',
        description: '',
        inputs: [],
        steps: []
    };
    state.currentWorkflowName = null;
    state.isNewWorkflow = true;
    renderWorkflowList();
    renderEditor();
    elements.workflowName.focus();
}

function hideEditor() {
    elements.editor.classList.add('hidden');
    elements.emptyState.classList.remove('hidden');
}

function addInput() {
    if (!state.currentWorkflow.inputs) {
        state.currentWorkflow.inputs = [];
    }
    state.currentWorkflow.inputs.push({ name: '', default: '' });
    renderInputs();
}

function updateInput(index, field, value) {
    const input = state.currentWorkflow.inputs[index];
    if (typeof input === 'string') {
        state.currentWorkflow.inputs[index] = { name: input, default: '' };
    }
    state.currentWorkflow.inputs[index][field] = value;
}

function removeInput(index) {
    state.currentWorkflow.inputs.splice(index, 1);
    renderInputs();
}

// What each action returns (for variable hints)
// Useful outputs from each action (excludes 'success' since it's just a boolean)
const ACTION_OUTPUTS = {
    'open-app': [],
    'notify': [],
    'speak': [],
    'screenshot': ['image'],
    'save-screenshot': ['path', 'filename'],
    'clipboard-get': ['text'],
    'clipboard-set': [],
    'create-note': [],
    'open-url': [],
    'volume': ['level', 'muted'],
    'sleep': [],
    'lock': [],
    'window-layout': [],
    'run-shortcut': ['result'],
    'pomodoro-start': ['state'],
    'pomodoro-stop': [],
    'pomodoro-status': ['state', 'remaining', 'phase'],
    'spotify-play': ['playing', 'track', 'artist'],
    'spotify-pause': [],
    'spotify-next': ['track', 'artist'],
    'spotify-previous': ['track', 'artist'],
    'spotify-volume': ['volume'],
    'spotify-shuffle': [],
    'spotify-current': ['track', 'artist', 'album'],
    'wallpaper': ['path', 'resolution'],
};

// Track last focused param input for variable insertion
let lastFocusedParamInput = null;

function updateVariablesHint(currentStepIndex) {
    const variables = [];
    
    // Add workflow inputs
    const inputs = state.currentWorkflow?.inputs || [];
    inputs.forEach(inp => {
        const name = typeof inp === 'string' ? inp : inp.name;
        variables.push({ var: `{{ input.${name} }}`, label: `input.${name}`, type: 'input' });
    });
    
    // Add previous step outputs (only if they have useful output)
    const steps = state.currentWorkflow?.steps || [];
    const maxIndex = currentStepIndex !== null ? currentStepIndex : steps.length;
    
    for (let i = 0; i < maxIndex; i++) {
        const step = steps[i];
        const outputs = ACTION_OUTPUTS[step.action] || [];
        outputs.forEach(field => {
            variables.push({ var: `{{ steps[${i}].${field} }}`, label: `step${i + 1}.${field}`, type: 'step' });
        });
    }
    
    // Add built-in variables
    variables.push({ var: '{{ timestamp }}', label: 'timestamp', type: 'builtin' });
    variables.push({ var: '{{ date }}', label: 'date', type: 'builtin' });
    variables.push({ var: '{{ time }}', label: 'time', type: 'builtin' });
    
    // Render as clickable chips
    const typeColors = {
        input: 'bg-green-500/20 text-green-400 border-green-500/30',
        step: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        builtin: 'bg-purple-500/20 text-purple-400 border-purple-500/30'
    };
    
    elements.variablesHint.innerHTML = variables.map(v => 
        `<button type="button" class="var-chip px-1.5 py-0.5 rounded border text-xs font-mono cursor-pointer hover:brightness-125 ${typeColors[v.type]}" data-var="${v.var}" title="Click to insert">${v.label}</button>`
    ).join(' ');
    
    // Add click handlers
    elements.variablesHint.querySelectorAll('.var-chip').forEach(chip => {
        chip.addEventListener('click', () => insertVariable(chip.dataset.var));
    });
}

function insertVariable(variable) {
    // Find the last focused param input, or the first text input in params
    let target = lastFocusedParamInput;
    if (!target || !document.body.contains(target)) {
        target = elements.stepParamsContainer.querySelector('input[type="text"], textarea');
    }
    
    if (target) {
        const start = target.selectionStart || target.value.length;
        const end = target.selectionEnd || target.value.length;
        const before = target.value.substring(0, start);
        const after = target.value.substring(end);
        target.value = before + variable + after;
        target.focus();
        target.selectionStart = target.selectionEnd = start + variable.length;
        
        // Flash effect
        target.classList.add('ring-2', 'ring-accent');
        setTimeout(() => target.classList.remove('ring-2', 'ring-accent'), 300);
    } else {
        showToast('Click on a parameter field first', 'error');
    }
}

function openAddStep() {
    state.editingStepIndex = null;
    elements.stepModalTitle.textContent = 'Add Step';
    elements.stepAction.value = '';
    elements.stepDelay.value = '';
    elements.stepTimeAfter.value = '';
    elements.stepTimeBefore.value = '';
    resetDayButtons();
    elements.stepParamsContainer.innerHTML = '<div class="text-night-500 text-sm">Select an action to see its parameters.</div>';
    updateVariablesHint(null);  // Show all previous steps
    
    showModal(elements.stepModal);
}

function resetDayButtons() {
    $$('.day-btn').forEach(btn => {
        btn.classList.remove('bg-accent', 'border-accent', 'text-white');
        btn.classList.add('border-night-700', 'text-night-400');
    });
}

function setSelectedDays(days) {
    resetDayButtons();
    if (!days || days.length === 0) return;
    
    days.forEach(day => {
        const btn = $(`.day-btn[data-day="${day}"]`);
        if (btn) {
            btn.classList.remove('border-night-700', 'text-night-400');
            btn.classList.add('bg-accent', 'border-accent', 'text-white');
        }
    });
}

function getSelectedDays() {
    const days = [];
    $$('.day-btn').forEach(btn => {
        if (btn.classList.contains('bg-accent')) {
            days.push(btn.dataset.day);
        }
    });
    return days;
}

function openEditStep(index) {
    const step = state.currentWorkflow.steps[index];
    state.editingStepIndex = index;
    elements.stepModalTitle.textContent = 'Edit Step';
    elements.stepAction.value = step.action;
    elements.stepDelay.value = step.delay || '';
    elements.stepTimeAfter.value = step.time_after || '';
    elements.stepTimeBefore.value = step.time_before || '';
    setSelectedDays(step.days || []);
    renderStepParams(step.action);
    updateVariablesHint(index);  // Only show steps before this one
    
    // Fill in current values
    const params = ACTION_PARAMS[step.action] || [];
    params.forEach(param => {
        const el = $(`#param-${param.name}`);
        if (el && step.params) {
            if (param.type === 'checkbox') {
                el.checked = step.params[param.name] ?? param.default ?? false;
            } else {
                el.value = step.params[param.name] ?? '';
            }
        }
    });
    
    showModal(elements.stepModal);
}

function saveStep() {
    const action = elements.stepAction.value;
    if (!action) {
        showToast('Please select an action', 'error');
        return;
    }
    
    const step = { action };
    const delay = parseFloat(elements.stepDelay.value);
    if (delay && delay > 0) {
        step.delay = delay;
    }
    
    // Time conditions
    const timeAfter = elements.stepTimeAfter.value;
    const timeBefore = elements.stepTimeBefore.value;
    const days = getSelectedDays();
    
    if (timeAfter) step.time_after = timeAfter;
    if (timeBefore) step.time_before = timeBefore;
    if (days.length > 0) step.days = days;
    
    // Collect params
    const paramDefs = ACTION_PARAMS[action] || [];
    const params = {};
    
    paramDefs.forEach(param => {
        const el = $(`#param-${param.name}`);
        if (el) {
            let value;
            if (param.type === 'checkbox') {
                value = el.checked;
            } else if (param.type === 'number') {
                value = el.value ? parseInt(el.value) : undefined;
            } else {
                value = el.value.trim();
            }
            
            if (value !== undefined && value !== '' && value !== false) {
                params[param.name] = value;
            }
        }
    });
    
    if (Object.keys(params).length > 0) {
        step.params = params;
    }
    
    // Validate required params
    for (const param of paramDefs) {
        if (param.required && !params[param.name]) {
            showToast(`${param.label} is required`, 'error');
            return;
        }
    }
    
    if (state.editingStepIndex !== null) {
        state.currentWorkflow.steps[state.editingStepIndex] = step;
    } else {
        if (!state.currentWorkflow.steps) {
            state.currentWorkflow.steps = [];
        }
        state.currentWorkflow.steps.push(step);
    }
    
    hideModal(elements.stepModal);
    renderSteps();
}

function removeStep(index) {
    state.currentWorkflow.steps.splice(index, 1);
    renderSteps();
}

function moveStep(fromIndex, toIndex) {
    const steps = state.currentWorkflow.steps;
    if (toIndex < 0 || toIndex >= steps.length) return;
    
    const [step] = steps.splice(fromIndex, 1);
    steps.splice(toIndex, 0, step);
    renderSteps();
}

async function openRunModal() {
    // Auto-save before running
    const name = elements.workflowName.value.trim().toLowerCase().replace(/\s+/g, '-');
    if (!name) {
        showToast('Enter a workflow name first', 'error');
        return;
    }
    
    // Save the workflow first
    const workflow = {
        description: elements.workflowDescription.value.trim(),
        inputs: state.currentWorkflow.inputs || [],
        steps: state.currentWorkflow.steps || []
    };
    
    if (workflow.steps.length === 0) {
        showToast('Add at least one step before running', 'error');
        return;
    }
    
    try {
        await apiRequest('PUT', `/workflows/${name}`, workflow);
        state.currentWorkflowName = name;
        state.isNewWorkflow = false;
        await loadWorkflows();
    } catch (error) {
        showToast(`Failed to save before run: ${error.message}`, 'error');
        return;
    }
    
    // Now show the run modal
    const inputs = state.currentWorkflow.inputs || [];
    
    if (inputs.length === 0) {
        elements.runInputsContainer.innerHTML = '';
        elements.noRunInputs.classList.remove('hidden');
    } else {
        elements.noRunInputs.classList.add('hidden');
        elements.runInputsContainer.innerHTML = inputs.map((inp, i) => {
            const name = typeof inp === 'string' ? inp : inp.name;
            const defaultVal = typeof inp === 'object' ? inp.default || '' : '';
            
            return `
                <div>
                    <label class="block text-sm font-medium text-night-300 mb-1.5">${name}</label>
                    <input type="text" id="run-input-${i}" value="${defaultVal}" placeholder="${defaultVal || 'Enter value...'}"
                        data-input-name="${name}"
                        class="w-full bg-night-800 border border-night-700 rounded-lg px-3 py-2 text-white placeholder-night-500 focus:border-accent focus:outline-none">
                </div>
            `;
        }).join('');
    }
    
    showModal(elements.runModal);
}

function confirmRun() {
    const inputs = {};
    $$('[data-input-name]').forEach(el => {
        const name = el.dataset.inputName;
        const value = el.value.trim();
        if (value) {
            inputs[name] = value;
        }
    });
    
    runWorkflow(inputs);
}

function openDeleteModal() {
    elements.deleteWorkflowName.textContent = state.currentWorkflowName;
    showModal(elements.deleteModal);
}

// =============================================================================
// Condition Builder Helpers
// =============================================================================


// =============================================================================
// UI Helpers
// =============================================================================

function showModal(modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function hideModal(modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

function downloadImage(imgId) {
    const img = document.getElementById(imgId);
    if (!img) return;
    
    // Create download link
    const link = document.createElement('a');
    link.href = img.src;
    link.download = `screenshot_${new Date().toISOString().slice(0,19).replace(/[:-]/g, '')}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('Screenshot downloaded!', 'success');
    
    // Flash effect
    img.classList.add('ring-2', 'ring-green-400');
    setTimeout(() => img.classList.remove('ring-2', 'ring-green-400'), 500);
}

function copyBase64(imgId) {
    const img = document.getElementById(imgId);
    if (!img) return;
    
    const base64 = img.dataset.base64;
    navigator.clipboard.writeText(base64).then(() => {
        showToast('Base64 copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy', 'error');
    });
}

function showToast(message, type = 'info') {
    const icons = {
        success: '<svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>',
        error: '<svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>',
        info: '<svg class="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
    };
    
    elements.toastIcon.innerHTML = icons[type] || icons.info;
    elements.toastMessage.textContent = message;
    elements.toast.classList.remove('translate-y-20', 'opacity-0');
    
    setTimeout(() => {
        elements.toast.classList.add('translate-y-20', 'opacity-0');
    }, 3000);
}

function updateConnectionStatus(connected) {
    const dot = elements.connectionStatus.querySelector('span:first-child');
    const text = elements.connectionStatus.querySelector('span:last-child');
    
    if (connected) {
        dot.classList.remove('bg-red-500');
        dot.classList.add('bg-green-500');
        text.textContent = 'Connected';
    } else {
        dot.classList.remove('bg-green-500');
        dot.classList.add('bg-red-500');
        text.textContent = 'Disconnected';
    }
}

function truncate(str, len) {
    if (str.length <= len) return str;
    return str.substring(0, len) + '...';
}

// =============================================================================
// API Key Prompt
// =============================================================================

function promptForApiKey() {
    const key = prompt('Enter your Layer API key:');
    if (key) {
        state.apiKey = key.trim();
        localStorage.setItem(API_KEY_STORAGE_KEY, state.apiKey);
        loadWorkflows();
    }
}

// =============================================================================
// Event Listeners
// =============================================================================

function setupEventListeners() {
    // New workflow
    $('#btn-new-workflow').addEventListener('click', createNewWorkflow);
    
    // Save
    $('#btn-save').addEventListener('click', saveWorkflow);
    
    // Run
    $('#btn-run').addEventListener('click', openRunModal);
    $('#btn-cancel-run').addEventListener('click', () => hideModal(elements.runModal));
    $('#btn-confirm-run').addEventListener('click', confirmRun);
    
    // Delete
    $('#btn-delete').addEventListener('click', openDeleteModal);
    $('#btn-cancel-delete').addEventListener('click', () => hideModal(elements.deleteModal));
    $('#btn-confirm-delete').addEventListener('click', deleteWorkflow);
    
    // Inputs
    $('#btn-add-input').addEventListener('click', addInput);
    
    // Steps
    $('#btn-add-step').addEventListener('click', openAddStep);
    $('#btn-close-modal').addEventListener('click', () => hideModal(elements.stepModal));
    $('#btn-cancel-step').addEventListener('click', () => hideModal(elements.stepModal));
    $('#btn-save-step').addEventListener('click', saveStep);
    
    // Action change
    elements.stepAction.addEventListener('change', (e) => {
        renderStepParams(e.target.value);
    });
    
    // Track last focused param input for variable insertion
    elements.stepParamsContainer.addEventListener('focusin', (e) => {
        if (e.target.matches('input[type="text"], textarea')) {
            lastFocusedParamInput = e.target;
        }
    });
    
    // Day buttons toggle
    $$('.day-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.classList.toggle('bg-accent');
            btn.classList.toggle('border-accent');
            btn.classList.toggle('text-white');
            btn.classList.toggle('border-night-700');
            btn.classList.toggle('text-night-400');
        });
    });
    
    // Close modals on backdrop click
    [elements.stepModal, elements.deleteModal, elements.runModal].forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                hideModal(modal);
            }
        });
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideModal(elements.stepModal);
            hideModal(elements.deleteModal);
            hideModal(elements.runModal);
        }
        if ((e.metaKey || e.ctrlKey) && e.key === 's') {
            e.preventDefault();
            if (state.currentWorkflow) {
                saveWorkflow();
            }
        }
    });
}

// =============================================================================
// Initialize
// =============================================================================

async function init() {
    setupEventListeners();
    
    if (!state.apiKey) {
        promptForApiKey();
    } else {
        await loadWorkflows();
    }
}

// Start the app
init();

