// API Base URL Configuration
// In production, VITE_API_URL should be set in Vercel environment variables to your backend URL
const getApiBase = () => {
    const envUrl = import.meta.env.VITE_API_URL;

    // If VITE_API_URL is set, use it
    if (envUrl) {
        // Ensure it ends with /api/v1
        return envUrl.endsWith('/api/v1') ? envUrl : `${envUrl}/api/v1`;
    }

    // Default to localhost for development
    return 'http://localhost:8000/api/v1';
};

const API_BASE = getApiBase();

// Request state management using WeakMap for memory efficiency
const activeRequests = new Map();
let currentAbortController = null;

/**
 * Generic API request handler with retry and timeout support
 * @param {string} endpoint - API endpoint
 * @param {Object} options - Fetch options
 * @param {Object} config - Additional config (retries, timeout)
 * @returns {Promise<any>}
 */
async function apiRequest(endpoint, options = {}, config = {}) {
    const { retries = 0, timeout = 30000 } = config;
    const url = `${API_BASE}${endpoint}`;
    const isFormData = options.body instanceof FormData;

    const fetchOptions = {
        ...options,
        headers: isFormData
            ? options.headers
            : { 'Content-Type': 'application/json', ...options.headers },
    };

    // Add timeout using AbortController
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    fetchOptions.signal = options.signal || controller.signal;

    try {
        const response = await fetch(url, fetchOptions);
        clearTimeout(timeoutId);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
            throw new Error(error.detail || error.error || `HTTP ${response.status}`);
        }

        return response.json();
    } catch (error) {
        clearTimeout(timeoutId);

        // Retry on network errors
        if (retries > 0 && error.name !== 'AbortError') {
            await new Promise(r => setTimeout(r, 1000));
            return apiRequest(endpoint, options, { ...config, retries: retries - 1 });
        }

        console.error(`API Error [${endpoint}]:`, error.message);
        throw error;
    }
}

// ============================================================================
// Ingest API
// ============================================================================

/**
 * Ingest input (text, image, or audio)
 * @param {'text'|'image'|'audio'} inputType
 * @param {string|null} textValue
 * @param {File|null} file
 */
export async function ingestInput(inputType, textValue = null, file = null) {
    const formData = new FormData();
    formData.append('input_type', inputType);

    if (inputType === 'text' && textValue) {
        formData.append('text', textValue);
    } else if (file) {
        formData.append('file', file);
    }

    return apiRequest('/ingest', { method: 'POST', body: formData });
}

export const ingestImage = (file) => ingestInput('image', null, file);
export const ingestAudio = (file) => ingestInput('audio', null, file);

// ============================================================================
// Solve API
// ============================================================================

/**
 * Solve problem (async endpoint)
 */
export async function solveProblem(text, options = {}) {
    return apiRequest('/solve/async', {
        method: 'POST',
        body: JSON.stringify({
            text,
            context: options.context ?? null,
            enable_guardrails: options.enableGuardrails !== false,
        }),
    });
}

/**
 * Abort current streaming request
 * @returns {boolean}
 */
export function abortCurrentRequest() {
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
        return true;
    }
    return false;
}

/**
 * Check if streaming is in progress
 */
export const isStreamingInProgress = () => currentAbortController !== null;

/**
 * Solve with streaming updates (SSE)
 * @param {string} text - Problem text
 * @param {Object} options - Solve options
 * @param {Function} onProgress - Progress callback
 * @param {AbortSignal} signal - External abort signal
 */
export async function solveProblemStreaming(text, options = {}, onProgress = null, signal = null) {
    currentAbortController = new AbortController();
    const abortSignal = signal || currentAbortController.signal;
    let reader = null;

    try {
        const response = await fetch(`${API_BASE}/solve/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                context: options.context ?? null,
                enable_guardrails: options.enableGuardrails !== false,
            }),
            signal: abortSignal,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Stream failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;

        while (true) {
            if (abortSignal.aborted) {
                throw new DOMException('Request aborted', 'AbortError');
            }

            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE messages - O(n) where n = buffer length
            const messages = buffer.split('\n\n');
            buffer = messages.pop() || '';

            for (const msg of messages) {
                if (!msg.startsWith('data: ')) continue;

                try {
                    const data = JSON.parse(msg.slice(6));

                    switch (data.type) {
                        case 'final_result':
                            finalResult = data.data;
                            break;
                        case 'agent_update':
                            onProgress?.(data);
                            break;
                        case 'error':
                            throw new Error(data.error);
                    }
                } catch (e) {
                    if (e.name === 'AbortError') throw e;
                    console.warn('SSE parse error:', e.message);
                }
            }
        }

        if (!finalResult) throw new Error('No final result from stream');
        return finalResult;

    } finally {
        reader?.cancel().catch(() => { });
        currentAbortController = null;
    }
}

// ============================================================================
// Feedback API
// ============================================================================

/**
 * Submit solution feedback
 */
export async function submitFeedback(entryId, isCorrect, comment = null) {
    if (!entryId) throw new Error('entry_id is required');

    return apiRequest(isCorrect ? '/feedback/correct' : '/feedback/incorrect', {
        method: 'POST',
        body: JSON.stringify({ entry_id: entryId, is_correct: isCorrect, comment }),
    });
}

/**
 * HITL approval
 */
export async function hitlApprove(entryId, editedText = null) {
    return apiRequest('/feedback/hitl/approve', {
        method: 'POST',
        body: JSON.stringify({ entry_id: entryId, edited_text: editedText }),
    });
}

/**
 * HITL rejection
 */
export async function hitlReject(entryId, reason) {
    return apiRequest('/feedback/hitl/reject', {
        method: 'POST',
        body: JSON.stringify({ entry_id: entryId, reason }),
    });
}

// ============================================================================
// History & Stats API  
// ============================================================================

export const getHistory = (limit = 20) => apiRequest(`/feedback/history?limit=${limit}`);
export const getEntry = (entryId) => apiRequest(`/feedback/entry/${entryId}`);
export const getPipelineStats = () => apiRequest('/solve/stats');
export const healthCheck = () => apiRequest('/solve/health');

// ============================================================================
// Knowledge Base API
// ============================================================================

/**
 * Get knowledge base entries with optional filters
 * @param {Object} filters - { topic, type, difficulty, search }
 */
export async function getKnowledgeBase(filters = {}) {
    const params = new URLSearchParams();
    if (filters.topic) params.set('topic', filters.topic);
    if (filters.type) params.set('type', filters.type);
    if (filters.difficulty) params.set('difficulty', filters.difficulty);
    if (filters.search) params.set('search', filters.search);
    params.set('include_stats', 'true');

    return apiRequest(`/knowledge?${params}`);
}

export const getKnowledgeTopics = () => apiRequest('/knowledge/topics');
export const getKnowledgeEntry = (id) => apiRequest(`/knowledge/${id}`);

/**
 * Create new knowledge entry
 */
export async function createKnowledgeEntry(entry) {
    return apiRequest('/knowledge', {
        method: 'POST',
        body: JSON.stringify(entry),
    });
}

/**
 * Update knowledge entry
 */
export async function updateKnowledgeEntry(id, updates) {
    return apiRequest(`/knowledge/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
    });
}

/**
 * Delete knowledge entry
 */
export async function deleteKnowledgeEntry(id) {
    return apiRequest(`/knowledge/${id}`, { method: 'DELETE' });
}
