/**
 * API Service - Connects frontend to Math Mentor backend
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * Helper to make API requests with error handling
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    try {
        // Don't set Content-Type for FormData - browser will set it with boundary
        const isFormData = options.body instanceof FormData;
        const headers = isFormData
            ? { ...options.headers }
            : {
                'Content-Type': 'application/json',
                ...options.headers,
            };

        const response = await fetch(url, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

/**
 * Ingest text, image, or audio input
 */
export async function ingestInput(inputType, textValue = null, file = null) {
    const formData = new FormData();
    formData.append('input_type', inputType);

    if (inputType === 'text') {
        formData.append('text', textValue);
    } else if (file) {
        formData.append('file', file);
    }

    const url = `${API_BASE}/ingest`;
    const response = await fetch(url, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Ingest failed' }));
        throw new Error(error.error || error.detail || 'Ingest failed');
    }

    return await response.json();
}

/**
 * Ingest image for OCR
 */
export async function ingestImage(file) {
    return ingestInput('image', null, file);
}

/**
 * Ingest audio for ASR transcription
 */
export async function ingestAudio(file) {
    return ingestInput('audio', null, file);
}

/**
 * Solve a problem using the multi-agent system (faster with parallel execution)
 */
export async function solveProblem(text, options = {}) {
    return apiRequest('/solve/async', {
        method: 'POST',
        body: JSON.stringify({
            text,
            context: options.context || null,
            enable_guardrails: options.enableGuardrails !== false,
        }),
    });
}

// Global abort controller for current streaming request
let currentAbortController = null;

/**
 * Abort the current streaming request if one is in progress
 * @returns {boolean} - True if a request was aborted
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
 * Check if a streaming request is currently in progress
 * @returns {boolean}
 */
export function isStreamingInProgress() {
    return currentAbortController !== null;
}

/**
 * Solve a problem with streaming updates from agents
 * @param {string} text - Problem text
 * @param {object} options - Options
 * @param {function} onProgress - Callback for agent progress updates
 * @param {AbortSignal} signal - Optional external abort signal
 * @returns {Promise} - Resolves with final result
 */
export async function solveProblemStreaming(text, options = {}, onProgress = null, signal = null) {
    const url = `${API_BASE}/solve/stream`;

    // Create abort controller for this request
    currentAbortController = new AbortController();
    const abortSignal = signal || currentAbortController.signal;

    let reader = null;

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text,
                context: options.context || null,
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
            // Check if aborted
            if (abortSignal.aborted) {
                throw new DOMException('Request aborted', 'AbortError');
            }

            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // Keep incomplete message in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === 'final_result') {
                            finalResult = data.data;
                        } else if (data.type === 'agent_update' && onProgress) {
                            // Use setTimeout to avoid blocking the main thread
                            setTimeout(() => onProgress(data), 0);
                        } else if (data.type === 'error') {
                            throw new Error(data.error);
                        }
                    } catch (e) {
                        if (e.name === 'AbortError') throw e;
                        console.error('Error parsing SSE data:', e);
                    }
                }
            }
        }

        if (!finalResult) {
            throw new Error('No final result received from stream');
        }

        return finalResult;
    } catch (error) {
        // Re-throw abort errors as-is
        if (error.name === 'AbortError') {
            console.log('Streaming request was aborted');
            throw error;
        }
        throw error;
    } finally {
        // Clean up reader if it exists
        if (reader) {
            try {
                await reader.cancel();
            } catch (e) {
                // Ignore cancel errors
            }
        }
        // Clear the global abort controller
        currentAbortController = null;
    }
}

/**
 * Submit feedback for a solution
 */
export async function submitFeedback(entryId, isCorrect, comment = null) {
    if (!entryId) {
        throw new Error('entry_id is required. The solution was not stored in memory.');
    }

    const endpoint = isCorrect ? '/feedback/correct' : '/feedback/incorrect';
    return apiRequest(endpoint, {
        method: 'POST',
        body: JSON.stringify({
            entry_id: entryId,
            is_correct: isCorrect,
            comment: comment || null,
        }),
    });
}

/**
 * HITL - Approve parsed/solved result
 */
export async function hitlApprove(entryId, editedText = null) {
    return apiRequest('/feedback/hitl/approve', {
        method: 'POST',
        body: JSON.stringify({
            entry_id: entryId,
            edited_text: editedText,
        }),
    });
}

/**
 * HITL - Reject parsed/solved result
 */
export async function hitlReject(entryId, reason) {
    return apiRequest('/feedback/hitl/reject', {
        method: 'POST',
        body: JSON.stringify({
            entry_id: entryId,
            reason,
        }),
    });
}

/**
 * Get problem-solving history
 */
export async function getHistory(limit = 20) {
    return apiRequest(`/feedback/history?limit=${limit}`);
}

/**
 * Get details of a specific entry
 */
export async function getEntry(entryId) {
    return apiRequest(`/feedback/entry/${entryId}`);
}

/**
 * Get pipeline statistics
 */
export async function getPipelineStats() {
    return apiRequest('/solve/stats');
}

/**
 * Health check
 */
export async function healthCheck() {
    return apiRequest('/solve/health');
}
