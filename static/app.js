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
          options: ['slack', 'vscode', 'terminal', 'safari', 'chrome', 'firefox', 'notes', 'calendar', 'mail', 'messages', 'discord', 'finder', 'spotify', 'preview', 'textedit'] }
    ],
    'notify': [
        { name: 'title', type: 'text', label: 'Title', required: true },
        { name: 'message', type: 'text', label: 'Message', required: true },
        { name: 'subtitle', type: 'text', label: 'Subtitle', required: false },
        { name: 'sound', type: 'checkbox', label: 'Play sound', required: false, default: true }
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
    'pomodoro-status': []
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
    stepCondition: $('#step-condition'),
    conditionEnabled: $('#condition-enabled'),
    conditionBuilder: $('#condition-builder'),
    conditionSource: $('#condition-source'),
    conditionField: $('#condition-field'),
    conditionOperator: $('#condition-operator'),
    conditionValue: $('#condition-value'),
    conditionPreview: $('#condition-preview'),
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
                        <div class="font-medium text-sm flex items-center gap-2">
                            <span class="text-accent">${step.action}</span>
                            ${step.if ? `<span class="text-xs bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded">if</span>` : ''}
                        </div>
                        ${paramSummary ? `<div class="text-xs text-night-400 mt-0.5 truncate font-mono">${paramSummary}</div>` : ''}
                        ${step.if ? `<div class="text-xs text-night-500 mt-1 font-mono">if: ${truncate(step.if, 40)}</div>` : ''}
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
    
    elements.stepParamsContainer.innerHTML = params.map(param => {
        const id = `param-${param.name}`;
        
        if (param.type === 'select') {
            return `
                <div>
                    <label for="${id}" class="block text-sm font-medium text-night-300 mb-1.5">
                        ${param.label} ${param.required ? '' : '<span class="text-night-500 font-normal">(optional)</span>'}
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
                    <label for="${id}" class="text-sm text-night-300">${param.label}</label>
                </div>
            `;
        } else if (param.type === 'textarea') {
            return `
                <div>
                    <label for="${id}" class="block text-sm font-medium text-night-300 mb-1.5">
                        ${param.label} ${param.required ? '' : '<span class="text-night-500 font-normal">(optional)</span>'}
                    </label>
                    <textarea id="${id}" rows="3" placeholder="${param.placeholder || ''}"
                        class="w-full bg-night-800 border border-night-700 rounded-lg px-3 py-2 text-white placeholder-night-500 focus:border-accent focus:outline-none resize-none"></textarea>
                </div>
            `;
        } else {
            return `
                <div>
                    <label for="${id}" class="block text-sm font-medium text-night-300 mb-1.5">
                        ${param.label} ${param.required ? '' : '<span class="text-night-500 font-normal">(optional)</span>'}
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
        <div class="space-y-2">
            ${results.map(r => {
                const statusIcon = r.status === 'ok' 
                    ? '<span class="text-green-400">✓</span>'
                    : r.status === 'skipped' 
                        ? '<span class="text-yellow-400">○</span>'
                        : '<span class="text-red-400">✗</span>';
                const message = r.output?.message || r.reason || '';
                
                return `
                    <div class="flex items-start gap-2 text-sm">
                        <span class="w-5 text-center">${statusIcon}</span>
                        <span class="text-night-300">Step ${r.step + 1}</span>
                        <span class="text-accent">${r.action}</span>
                        ${message ? `<span class="text-night-500">— ${truncate(message, 50)}</span>` : ''}
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

function openAddStep() {
    state.editingStepIndex = null;
    elements.stepModalTitle.textContent = 'Add Step';
    elements.stepAction.value = '';
    elements.stepCondition.value = '';
    elements.stepParamsContainer.innerHTML = '<div class="text-night-500 text-sm">Select an action to see its parameters.</div>';
    
    // Reset condition builder
    resetConditionBuilder();
    
    showModal(elements.stepModal);
}

function openEditStep(index) {
    const step = state.currentWorkflow.steps[index];
    state.editingStepIndex = index;
    elements.stepModalTitle.textContent = 'Edit Step';
    elements.stepAction.value = step.action;
    elements.stepCondition.value = step.if || '';
    renderStepParams(step.action);
    
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
    
    // Populate condition builder
    if (step.if) {
        parseConditionToBuilder(step.if);
    } else {
        resetConditionBuilder();
    }
    
    showModal(elements.stepModal);
}

function saveStep() {
    const action = elements.stepAction.value;
    if (!action) {
        showToast('Please select an action', 'error');
        return;
    }
    
    const step = { action };
    const condition = elements.stepCondition.value.trim();
    if (condition) {
        step.if = condition;
    }
    
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

function openRunModal() {
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

function resetConditionBuilder() {
    elements.conditionEnabled.checked = false;
    elements.conditionBuilder.classList.add('hidden');
    elements.conditionSource.value = '';
    elements.conditionField.value = '';
    elements.conditionOperator.value = '!=';
    elements.conditionValue.value = '';
    elements.conditionPreview.textContent = '';
    elements.stepCondition.value = '';
}

function parseConditionToBuilder(conditionStr) {
    // Try to parse a condition string like "steps[0].text != ''"
    const patterns = [
        /^(steps\[\d+\])\.(\w+)\s*(!=|==|>=|<=|>|<)\s*(.+)$/,
        /^(input)\.(\w+)\s*(!=|==|>=|<=|>|<)\s*(.+)$/
    ];
    
    for (const pattern of patterns) {
        const match = conditionStr.match(pattern);
        if (match) {
            elements.conditionEnabled.checked = true;
            elements.conditionBuilder.classList.remove('hidden');
            elements.conditionSource.value = match[1];
            elements.conditionField.value = match[2];
            elements.conditionOperator.value = match[3];
            elements.conditionValue.value = match[4];
            updateConditionPreview();
            return;
        }
    }
    
    // Couldn't parse - show builder but leave empty, keep original value
    elements.conditionEnabled.checked = true;
    elements.conditionBuilder.classList.remove('hidden');
    elements.stepCondition.value = conditionStr;
    elements.conditionPreview.textContent = conditionStr + ' (custom)';
}

function updateConditionPreview() {
    const source = elements.conditionSource.value;
    const field = elements.conditionField.value.trim();
    const operator = elements.conditionOperator.value;
    const value = elements.conditionValue.value.trim();
    
    if (!source || !field) {
        elements.conditionPreview.textContent = '';
        elements.stepCondition.value = '';
        return;
    }
    
    const condition = `${source}.${field} ${operator} ${value || "''"}`;
    elements.conditionPreview.textContent = condition;
    elements.stepCondition.value = condition;
}

function toggleConditionBuilder() {
    if (elements.conditionEnabled.checked) {
        elements.conditionBuilder.classList.remove('hidden');
        updateConditionPreview();
    } else {
        elements.conditionBuilder.classList.add('hidden');
        elements.stepCondition.value = '';
    }
}

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
    
    // Condition builder
    elements.conditionEnabled.addEventListener('change', toggleConditionBuilder);
    elements.conditionSource.addEventListener('change', updateConditionPreview);
    elements.conditionField.addEventListener('input', updateConditionPreview);
    elements.conditionOperator.addEventListener('change', updateConditionPreview);
    elements.conditionValue.addEventListener('input', updateConditionPreview);
    
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

