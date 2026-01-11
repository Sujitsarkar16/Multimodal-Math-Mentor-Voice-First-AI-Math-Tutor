import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Icon } from '@iconify/react';
import { ingestImage, ingestAudio, solveProblemStreaming, submitFeedback, hitlApprove, abortCurrentRequest } from "../../services/api";
import { useWorkspace } from "../../context/WorkspaceContext";


const processLatexContent = (content) => {
    if (!content || typeof content !== 'string') return content || '';

    let processed = content;

    // Replace inline LaTeX \( ... \) with $ ... $
    processed = processed.replace(/\\\(([^)]+)\\\)/g, '$$$1$$');

    // Replace display LaTeX \[ ... \] with $$ ... $$
    processed = processed.replace(/\\\[([^\]]+)\\\]/g, '$$$$$$1$$$$');

    // Handle unescaped LaTeX commands that should be wrapped
    // Match patterns like f(x) = \frac{...} that aren't already in $ delimiters
    const latexCommands = ['\\frac', '\\sqrt', '\\int', '\\sum', '\\prod', '\\lim', '\\arctan', '\\sin', '\\cos', '\\tan', '\\log', '\\ln', '\\exp'];

    // Check if content has LaTeX commands but no $ delimiters
    const hasLatexCommands = latexCommands.some(cmd => processed.includes(cmd));
    const hasDollarSigns = processed.includes('$');

    if (hasLatexCommands && !hasDollarSigns) {
        // Wrap the entire content in $$ if it looks like a single expression
        if (!processed.includes('\n') && processed.length < 500) {
            processed = `$$${processed}$$`;
        }
    }

    return processed;
};

/**
 * Format step-by-step solution for better display
 */
const formatStepByStep = (steps) => {
    if (!steps || !Array.isArray(steps) || steps.length === 0) return null;

    return steps.map((step, index) => {
        // Process each step for LaTeX
        const processedStep = processLatexContent(String(step));
        return processedStep;
    });
};

// Error boundary component for Markdown rendering
class MarkdownErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error('Markdown rendering error:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
                    <p className="text-red-200 text-sm mb-2">Error rendering content. Showing raw text:</p>
                    <pre className="text-xs text-red-300 whitespace-pre-wrap font-mono bg-neutral-900 p-2 rounded">
                        {this.props.fallbackText || 'Content could not be rendered'}
                    </pre>
                </div>
            );
        }

        return this.props.children;
    }
}

// Reusable Helper Component for Agent Step
const AgentStep = ({ label, desc, status }) => {
    let icon = 'lucide:circle';
    let iconClass = 'text-neutral-600';
    let containerClass = 'bg-neutral-900 border-neutral-800';
    let opacity = 'opacity-100';
    let textColor = 'text-neutral-300';

    if (status === 'done') {
        icon = 'lucide:check';
        iconClass = 'text-emerald-400';
        containerClass = 'bg-neutral-900 border-emerald-700/30';
        textColor = 'text-emerald-300';
    } else if (status === 'active') {
        icon = 'lucide:loader-2';
        iconClass = 'text-indigo-400 animate-spin';
        containerClass = 'bg-indigo-500/20 border-indigo-500/50 shadow-[0_0_10px_rgba(99,102,241,0.3)]';
        textColor = 'text-white';
    } else if (status === 'failed') {
        icon = 'lucide:x';
        iconClass = 'text-red-400';
        containerClass = 'bg-red-900/20 border-red-500/50';
        textColor = 'text-red-300';
    } else {
        // Pending
        opacity = 'opacity-50';
    }

    return (
        <div className={`relative flex gap-3 items-start ${opacity}`}>
            <div className={`w-6 h-6 rounded-full border flex items-center justify-center z-10 ${containerClass}`}>
                {status === 'pending' ? (
                    <div className="w-1.5 h-1.5 rounded-full bg-neutral-600"></div>
                ) : (
                    <Icon icon={icon} className={iconClass} width={12} />
                )}
            </div>
            <div className="flex-1 min-w-0">
                <p className={`text-xs font-medium ${textColor}`}>{label}</p>
                <p className="text-[10px] text-neutral-500 mt-0.5 break-words">{desc}</p>
            </div>
        </div>
    );
};


const Workspace = ({ onSolveComplete }) => {
    // Use global workspace context for persistent state
    const {
        viewState, setViewState,
        pipelineStep, setPipelineStep,
        activeAgents, setActiveAgents,
        agentOutputs, setAgentOutputs,
        agentTrace, setAgentTrace,
        solutionData, setSolutionData,
        error, setError,
        resetWorkspace,
        updateAgentProgress,
        isProcessing
    } = useWorkspace();

    // Local state (doesn't need persistence)
    const [inputMethod, setInputMethod] = useState(null);
    const [parsedText, setParsedText] = useState('');
    const [parsedConfidence, setParsedConfidence] = useState(null);
    const [feedbackSubmitted, setFeedbackSubmitted] = useState(null); // 'correct' | 'incorrect' | null
    const [inputValue, setInputValue] = useState('');
    const [filePreview, setFilePreview] = useState(null);

    const [showRestoredNotice, setShowRestoredNotice] = useState(false);
    const [isRecording, setIsRecording] = useState(false);

    const fileInputRef = useRef(null);
    const audioInputRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    // Check if state was restored on mount
    useEffect(() => {
        const wasRestored = sessionStorage.getItem('workspace_viewState');
        if (wasRestored && wasRestored !== 'input') {
            setShowRestoredNotice(true);
            setTimeout(() => setShowRestoredNotice(false), 5000); // Hide after 5s
        }
    }, []);

    // Warn user before leaving/refreshing during processing
    useEffect(() => {
        const handleBeforeUnload = (e) => {
            if (isProcessing) {
                e.preventDefault();
                e.returnValue = 'Problem solving is in progress. Are you sure you want to leave?';
                return e.returnValue;
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    }, [isProcessing]);

    // --- RECORDING HANDLERS ---
    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
                const audioFile = new File([audioBlob], "recording.wav", { type: 'audio/wav' });
                processAudioFile(audioFile);

                // Stop all tracks to release microphone
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);
        } catch (err) {
            console.error("Error accessing microphone:", err);
            setError("Could not access microphone. Please ensure permissions are granted.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const toggleRecording = (e) => {
        e.stopPropagation(); // Prevent bubbling if needed
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    // --- LOGIC HANDLERS (Same as before, simplified for this display) ---
    const handleImageUpload = async (event) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setInputMethod('image');
        setFilePreview(URL.createObjectURL(file)); // Show preview
        setViewState('processing');
        setError(null);
        setPipelineStep(1);

        try {
            setPipelineStep(2); // OCR
            const result = await ingestImage(file);
            const rawText = String(result?.raw_text || result?.text || '').trim();
            setParsedText(rawText);
            setParsedConfidence(result?.confidence ?? 1.0);
            setPipelineStep(3);

            // Always show review state for image uploads so user can see OCR content
            if (rawText) {
                setViewState('review');
            } else {
                setError('No text extracted from image. Please try a clearer image.');
                setViewState('input');
                setParsedText('');
                setParsedConfidence(null);
            }
        } catch (err) {
            setError(err?.message || 'Failed to process image');
            setViewState('input');
            setParsedText('');
            setParsedConfidence(null);
        }
    };

    const processAudioFile = async (file) => {
        if (!file) return;

        setInputMethod('audio');
        setViewState('processing');
        setError(null);
        setPipelineStep(1);

        try {
            setPipelineStep(2); // ASR
            const result = await ingestAudio(file);
            const normalizedText = result.normalized_text || result.raw_text || result.text || '';
            setParsedText(normalizedText);
            setParsedConfidence(result.confidence || 1.0);
            setPipelineStep(3);

            setViewState('review');
            // Remove auto-solve to allow user to verify transcript first
            // if (result.confidence < 0.75 || result.needs_confirmation) {
            //    setViewState('review');
            // } else {
            //    await handleSolve(normalizedText);
            // }
        } catch (err) {
            setError(err.message || 'Failed to process audio');
            setViewState('input');
            setParsedText('');
            setParsedConfidence(null);
        }
    };

    const handleAudioUpload = async (event) => {
        const file = event.target.files?.[0];
        if (file) await processAudioFile(file);
    };

    const handleTextSubmit = async () => {
        if (!inputValue.trim()) return;
        setInputMethod('text');
        setParsedText(inputValue);
        setViewState('processing');
        setPipelineStep(1);
        await handleSolve(inputValue);
    };

    const handleSolve = async (text) => {
        try {
            // Reset agent tracking
            setActiveAgents([]);
            setAgentOutputs({});
            setPipelineStep(1);

            // Define agent name mapping and order
            const agentSteps = {
                'guardrail': 0,
                'parser': 1,
                'intent_router': 2,
                'solver': 3,
                'verifier': 4,
                'explainer': 5
            };

            // Handle progress updates from streaming (use context updater)
            const handleProgress = (update) => {
                const { agent, status, data } = update;

                // Update using context
                updateAgentProgress(update);

                // Update pipeline step based on agent
                const step = agentSteps[agent] || 0;
                if (status === 'started') {
                    setPipelineStep(step);
                } else if (status === 'completed') {
                    setPipelineStep(step + 1);
                }
            };

            // Use streaming API with progress callback
            const result = await solveProblemStreaming(text, {}, handleProgress);

            setPipelineStep(6); // Done
            setAgentTrace(result.agent_trace || []);

            // Update agent outputs from final trace to ensure UI shows completion
            // (fallback in case streaming updates didn't reach the UI)
            if (result.agent_trace && result.agent_trace.length > 0) {
                const finalOutputs = {};
                result.agent_trace.forEach(trace => {
                    finalOutputs[trace.agent] = {
                        status: trace.success ? 'completed' : 'failed',
                        output: trace.output,
                        time_ms: trace.time_ms,
                        success: trace.success,
                        error: trace.error,
                        metadata: trace.metadata || {}
                    };
                });
                setAgentOutputs(finalOutputs);
            }

            // Clear active agents since all are done
            setActiveAgents([]);

            const confidencePercent = Math.round(result.confidence * 100);
            const needsHITL = confidencePercent < 75 || result.requires_human_review;

            setSolutionData({
                memoryId: result.memory_id,
                answer: result.final_answer,
                confidence: confidencePercent,
                explanation: result.explanation,
                requiresReview: needsHITL,
                retrievalUsed: result.retrieval_used || false,
                retrievalFailed: result.retrieval_failed || false,
                sources: result.sources || [],
                retrievedContext: result.retrieved_context || [],
                metadata: result.metadata
            });
            setViewState('solution');

            if (onSolveComplete) {
                onSolveComplete({
                    id: result.memory_id || `#${Date.now()}`,
                    input: inputMethod,
                    topic: result.metadata?.topic || 'General',
                    status: result.requires_human_review ? 'Review' : 'Solved',
                    date: new Date().toLocaleDateString()
                });
            }
        } catch (err) {
            // Handle abort errors gracefully - don't show error message for user-initiated cancellation
            if (err.name === 'AbortError') {
                console.log('Request was cancelled by user');
                // State is already reset by handleResetWorkspace
                return;
            }
            setError(err.message);
            setViewState('input');
            setPipelineStep(0);
            setActiveAgents([]);
        }
    };

    const handleResetWorkspace = () => {
        // First, abort any ongoing request
        abortCurrentRequest();

        resetWorkspace(); // From context
        // Reset local state
        setInputMethod(null);
        setInputValue('');
        setParsedText('');
        setParsedConfidence(null);
        setFilePreview(null);
        setFeedbackSubmitted(null); // Reset feedback state for new problem
    };

    const handleFeedback = async (isCorrect) => {
        if (!solutionData?.memoryId) {
            setError('Cannot submit feedback: Solution was not stored in memory. This may happen if memory storage failed.');
            return;
        }

        // Prevent double submission
        if (feedbackSubmitted) {
            return;
        }

        try {
            setFeedbackSubmitted(isCorrect ? 'correct' : 'incorrect');
            await submitFeedback(solutionData.memoryId, isCorrect);
            console.log(`Feedback submitted: ${isCorrect ? 'correct' : 'incorrect'}`);
        } catch (err) {
            setFeedbackSubmitted(null); // Reset on error
            setError(`Failed to submit feedback: ${err.message}`);
        }
    };

    // --- RENDER ---

    return (
        <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8">

            {/* State Restored Notice */}
            {showRestoredNotice && (
                <div className="bg-indigo-900/20 border border-indigo-500/50 text-indigo-200 p-4 rounded-lg flex items-center gap-3">
                    <Icon icon="lucide:info" className="text-indigo-400" />
                    <span className="flex-1">Progress restored! Your previous session state has been recovered.</span>
                    <button onClick={() => setShowRestoredNotice(false)} className="hover:text-white">✕</button>
                </div>
            )}

            {/* Error Banner */}
            {error && (
                <div className="bg-red-900/20 border border-red-500/50 text-red-200 p-4 rounded-lg flex justify-between items-center">
                    <span>{error}</span>
                    <button onClick={() => setError(null)} className="hover:text-white">✕</button>
                </div>
            )}

            {/* Section 1: Multimodal Input (Only show when in input mode or for context) */}
            {viewState === 'input' && (
                <section>
                    <h2 className="text-lg font-semibold tracking-tight text-white mb-4">Input Method</h2>

                    {/* HIDDEN INPUTS */}
                    <input type="file" ref={fileInputRef} accept="image/*" className="hidden" onChange={handleImageUpload} />
                    <input type="file" ref={audioInputRef} accept="audio/*" className="hidden" onChange={handleAudioUpload} />

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Image Upload */}
                        <div onClick={() => fileInputRef.current?.click()} className="group relative flex flex-col items-center justify-center p-8 border border-neutral-800 border-dashed rounded-lg bg-neutral-900/20 hover:bg-neutral-900/40 hover:border-neutral-600 transition-all cursor-pointer">
                            <div className="w-12 h-12 rounded-full bg-neutral-800 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                <Icon icon="lucide:camera" className="text-neutral-400 group-hover:text-indigo-400" width={24} />
                            </div>
                            <span className="text-sm font-medium text-neutral-300">Upload Question</span>
                            <span className="text-xs text-neutral-500 mt-1">JPG, PNG, PDF</span>
                        </div>

                        {/* Audio Input */}
                        {/* Audio Input / Dictation */}
                        <div onClick={toggleRecording} className={`group relative flex flex-col items-center justify-center p-8 border border-dashed rounded-lg transition-all cursor-pointer ${isRecording
                            ? 'bg-red-900/20 border-red-500/50 hover:bg-red-900/30'
                            : 'border-neutral-800 bg-neutral-900/20 hover:bg-neutral-900/40 hover:border-neutral-600'}`}>

                            <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-4 transition-transform ${isRecording
                                ? 'bg-red-500/20 animate-pulse scale-110'
                                : 'bg-neutral-800 group-hover:scale-110'}`}>
                                <Icon icon={isRecording ? "lucide:mic-off" : "lucide:mic"} className={isRecording ? "text-red-400" : "text-neutral-400 group-hover:text-emerald-400"} width={24} />
                            </div>
                            <span className={`text-sm font-medium ${isRecording ? 'text-red-300' : 'text-neutral-300'}`}>
                                {isRecording ? 'Stop Recording' : 'Voice Dictation'}
                            </span>
                            <span className="text-xs text-neutral-500 mt-1">
                                {isRecording ? 'Listening...' : 'Whisper ASR Model'}
                            </span>
                        </div>

                        {/* Text Input Toggle */}
                        <div onClick={() => setInputMethod('text_manual')} className="group relative flex flex-col items-center justify-center p-8 border border-neutral-800 border-dashed rounded-lg bg-neutral-900/20 hover:bg-neutral-900/40 hover:border-neutral-600 transition-all cursor-pointer">
                            <div className="w-12 h-12 rounded-full bg-neutral-800 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                <Icon icon="lucide:keyboard" className="text-neutral-400 group-hover:text-amber-400" width={24} />
                            </div>
                            <span className="text-sm font-medium text-neutral-300">Paste Text / LaTeX</span>
                            <span className="text-xs text-neutral-500 mt-1">Direct input</span>
                        </div>
                    </div>

                    {/* Manual Text Input Area */}
                    {inputMethod === 'text_manual' && (
                        <div className="mt-6 bg-neutral-900/60 backdrop-blur-xl border border-neutral-800 p-6 rounded-lg">
                            <textarea
                                className="w-full bg-neutral-900 border border-neutral-800 rounded p-4 text-neutral-200 outline-none focus:border-indigo-500/50 min-h-[150px]"
                                placeholder="Enter your math problem here..."
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                            />
                            <div className="flex justify-end gap-3 mt-4">
                                <button onClick={() => setInputMethod(null)} className="px-4 py-2 text-sm text-neutral-400 hover:text-white">Cancel</button>
                                <button onClick={handleTextSubmit} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-sm font-medium">Solve Problem</button>
                            </div>
                        </div>
                    )}
                </section>
            )}

            {/* Section 2: Agent Swarm & Processing Pipeline (Visible when processing, reviewing, or solved) */}
            {viewState !== 'input' && (
                <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                    {/* Left: Agent Logs / Pipeline Visualization */}
                    <div className="lg:col-span-1 bg-neutral-900/60 backdrop-blur-xl border border-neutral-800 rounded-lg p-5 flex flex-col h-full min-h-[400px] max-h-[600px]">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-medium text-white flex items-center gap-2">
                                <Icon icon="lucide:cpu" className="text-indigo-400" />
                                Agent Swarm Activity
                            </h3>
                            {viewState === 'processing' && activeAgents.length > 0 && (
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded border border-indigo-500/20 animate-pulse">
                                        {activeAgents.length} Active
                                    </span>
                                    <Icon icon="lucide:wifi" className="text-emerald-500" title="Progress is preserved" />
                                </div>
                            )}
                        </div>

                        <div className="flex-1 overflow-y-auto space-y-3 relative pr-2">
                            {/* Vertical line connector */}
                            <div className="absolute left-3 top-2 bottom-2 w-px bg-neutral-800"></div>

                            {/* Real-time agent activity display */}
                            {['parser', 'intent_router', 'solver', 'verifier', 'explainer'].map((agentName) => {
                                const agentOutput = agentOutputs[agentName];
                                const isActive = activeAgents.includes(agentName);
                                const isDone = agentOutput && agentOutput.status === 'completed';
                                const isFailed = agentOutput && agentOutput.status === 'failed';

                                // Determine status
                                let status = 'pending';
                                if (isActive) status = 'active';
                                else if (isDone) status = 'done';
                                else if (isFailed) status = 'failed';

                                // Agent labels
                                const agentLabels = {
                                    'parser': { label: 'Parser Agent', desc: 'Structuring problem...' },
                                    'intent_router': { label: 'Router Agent', desc: 'Classifying problem type...' },
                                    'solver': { label: 'Solver Agent', desc: 'Computing solution...' },
                                    'verifier': { label: 'Verifier Agent', desc: 'Validating correctness...' },
                                    'explainer': { label: 'Explainer Agent', desc: 'Generating explanation...' }
                                };

                                const agentInfo = agentLabels[agentName] || { label: agentName, desc: '' };

                                return (
                                    <div key={agentName} className="relative">
                                        <AgentStep
                                            label={agentInfo.label}
                                            desc={agentOutput ? agentOutput.output : agentInfo.desc}
                                            status={status}
                                        />
                                        {agentOutput && agentOutput.time_ms && (
                                            <div className="ml-9 mt-1 text-[9px] text-neutral-600">
                                                {Math.round(agentOutput.time_ms)}ms
                                            </div>
                                        )}
                                        {agentOutput && agentOutput.error && (
                                            <div className="ml-9 mt-1 text-[10px] text-red-400">
                                                Error: {agentOutput.error}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}

                            {/* Show trace if available */}
                            {agentTrace.length > 0 && viewState === 'solution' && (
                                <div className="mt-6 pt-4 border-t border-neutral-800">
                                    <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-2">Execution Summary</p>
                                    <div className="space-y-1">
                                        {agentTrace.map((trace, idx) => (
                                            <div key={idx} className="text-[10px] text-neutral-400 flex items-center gap-2">
                                                <span className={trace.success ? 'text-emerald-500' : 'text-red-500'}>
                                                    {trace.success ? '✓' : '✗'}
                                                </span>
                                                <span className="flex-1">{trace.agent}</span>
                                                <span className="text-neutral-600">{Math.round(trace.time_ms)}ms</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right: HITL Interface / Solution Display */}
                    <div className="lg:col-span-2 bg-neutral-900/60 backdrop-blur-xl border border-neutral-700/30 rounded-lg flex flex-col overflow-hidden">

                        {/* REVIEW STATE */}
                        {viewState === 'review' && (
                            <>
                                <div className="bg-amber-500/10 px-5 py-3 border-b border-amber-500/20 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Icon icon="lucide:alert-circle" className="text-amber-400" />
                                        <span className="text-xs font-medium text-amber-200 uppercase tracking-wide">Review Required</span>
                                    </div>
                                    <span className="text-xs text-neutral-400">Please verify extracted text</span>
                                </div>

                                <div className="flex-1 p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {/* Source */}
                                    <div className="space-y-2">
                                        <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Source</span>
                                        <div className="h-48 bg-neutral-900 rounded border border-neutral-800 flex items-center justify-center overflow-hidden relative">
                                            {filePreview ? (
                                                <img src={filePreview} alt="Source" className="max-h-full max-w-full object-contain" />
                                            ) : (
                                                <div className="text-neutral-600 text-xs">No preview</div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Parsed Output */}
                                    <div className="space-y-2 flex flex-col">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Parsed Transcript</span>
                                            {parsedConfidence !== null && (
                                                <span className={`text-xs font-medium px-2 py-1 rounded ${parsedConfidence < 0.75
                                                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                                    : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                                    }`}>
                                                    Confidence: {Math.round(parsedConfidence * 100)}%
                                                </span>
                                            )}
                                        </div>

                                        {/* Editable textarea for corrections */}
                                        <textarea
                                            className="w-full h-32 bg-neutral-950 border border-neutral-800 rounded p-4 text-sm text-neutral-200 font-mono resize-none focus:outline-none focus:border-indigo-500/50 mb-4"
                                            value={parsedText}
                                            onChange={(e) => setParsedText(e.target.value)}
                                            placeholder="Edit parsed text if needed..."
                                        />

                                        {/* Rendered preview with Markdown and LaTeX */}
                                        <div className="flex-1 bg-neutral-950 border border-neutral-800 rounded p-4 overflow-y-auto min-h-[200px]">
                                            <div className="prose prose-invert prose-sm max-w-none text-neutral-200">
                                                {parsedText && parsedText.trim() ? (
                                                    <MarkdownErrorBoundary fallbackText={parsedText}>
                                                        <ReactMarkdown
                                                            remarkPlugins={[remarkMath]}
                                                            rehypePlugins={[rehypeKatex]}
                                                        >
                                                            {String(parsedText)}
                                                        </ReactMarkdown>
                                                    </MarkdownErrorBoundary>
                                                ) : (
                                                    <p className="text-neutral-500 italic">No text to display. Parsed content will appear here.</p>
                                                )}
                                            </div>
                                        </div>

                                        {parsedConfidence !== null && parsedConfidence < 0.75 && (
                                            <div className="mt-2 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                                                <div className="flex items-start gap-2">
                                                    <Icon icon="lucide:alert-triangle" className="text-amber-400 mt-0.5" />
                                                    <div className="flex-1">
                                                        <p className="text-xs font-medium text-amber-200 mb-1">Human-in-the-Loop Review Recommended</p>
                                                        <p className="text-xs text-amber-300/80">
                                                            Confidence is below 75%. Please review and correct the parsed text before proceeding.
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="p-4 bg-neutral-900/50 border-t border-neutral-800 flex justify-end gap-3 transition-colors">
                                    <button onClick={handleResetWorkspace} className="px-4 py-1.5 rounded text-neutral-400 hover:text-white text-xs font-medium">Cancel</button>
                                    <button onClick={() => { setViewState('processing'); handleSolve(parsedText); }} className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-white text-black hover:bg-neutral-200 border border-transparent text-xs font-semibold transition-colors">
                                        Confirm & Solve
                                    </button>
                                </div>
                            </>
                        )}

                        {/* SOLUTION STATE */}
                        {viewState === 'solution' && solutionData && (
                            <>
                                <div className={`px-5 py-3 border-b flex items-center justify-between ${solutionData.requiresReview ? 'bg-amber-500/10 border-amber-500/20' : 'bg-emerald-500/10 border-emerald-500/20'}`}>
                                    <div className="flex items-center gap-2">
                                        <Icon icon={solutionData.requiresReview ? 'lucide:alert-circle' : 'lucide:sparkles'} className={solutionData.requiresReview ? 'text-amber-400' : 'text-emerald-400'} />
                                        <span className={`text-xs font-medium uppercase tracking-wide ${solutionData.requiresReview ? 'text-amber-200' : 'text-emerald-200'}`}>
                                            {solutionData.requiresReview ? 'Review Recommended' : 'Solution Complete'}
                                        </span>
                                    </div>
                                    <span className="text-xs text-neutral-400">Confidence: <span className="font-medium text-white">{solutionData.confidence}%</span></span>
                                </div>

                                {/* HITL Reasons Banner */}
                                {solutionData.requiresReview && solutionData.metadata?.hitl_reasons && solutionData.metadata.hitl_reasons.length > 0 && (
                                    <div className="px-5 py-3 bg-amber-500/5 border-b border-amber-500/10">
                                        <div className="flex items-start gap-2">
                                            <Icon icon="lucide:info" className="text-amber-400 mt-0.5" width={14} />
                                            <div className="flex-1">
                                                <p className="text-xs font-medium text-amber-200 mb-1">Why Review is Recommended:</p>
                                                <ul className="text-xs text-amber-300/80 space-y-1">
                                                    {solutionData.metadata.hitl_reasons.map((reason, idx) => (
                                                        <li key={idx} className="flex items-center gap-1.5">
                                                            <span className="w-1 h-1 rounded-full bg-amber-400"></span>
                                                            {reason === 'parser_ambiguity' && 'Problem statement contains ambiguities'}
                                                            {reason === 'verifier_low_confidence' && `Verifier confidence below threshold (${solutionData.confidence}%)`}
                                                            {reason === 'ocr_low_confidence' && 'OCR extraction confidence was low'}
                                                            {reason === 'asr_low_confidence' && 'Audio transcription confidence was low'}
                                                            {!['parser_ambiguity', 'verifier_low_confidence', 'ocr_low_confidence', 'asr_low_confidence'].includes(reason) && reason}
                                                        </li>
                                                    ))}
                                                </ul>
                                                {/* Show parser ambiguities if any */}
                                                {solutionData.metadata.parser_ambiguities && solutionData.metadata.parser_ambiguities.length > 0 && (
                                                    <div className="mt-2 p-2 bg-amber-900/20 rounded border border-amber-500/20">
                                                        <p className="text-[10px] text-amber-300/60 uppercase tracking-wider mb-1">Ambiguities Detected:</p>
                                                        {solutionData.metadata.parser_ambiguities.map((amb, idx) => (
                                                            <p key={idx} className="text-xs text-amber-200/80">• {amb}</p>
                                                        ))}
                                                    </div>
                                                )}
                                                {/* Show verifier issues if any */}
                                                {solutionData.metadata.verifier_issues && solutionData.metadata.verifier_issues.length > 0 && (
                                                    <div className="mt-2 p-2 bg-amber-900/20 rounded border border-amber-500/20">
                                                        <p className="text-[10px] text-amber-300/60 uppercase tracking-wider mb-1">Verifier Concerns:</p>
                                                        {solutionData.metadata.verifier_issues.map((issue, idx) => (
                                                            <p key={idx} className="text-xs text-amber-200/80">• {issue}</p>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div className="flex-1 p-6 overflow-y-auto space-y-6">
                                    {/* Final Answer Section */}
                                    <div className="space-y-2">
                                        <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Final Answer</span>
                                        <div className="p-6 bg-neutral-950 border border-emerald-500/30 rounded-lg">
                                            <div className="prose prose-invert prose-lg max-w-none text-white">
                                                {solutionData.answer && String(solutionData.answer).trim() ? (
                                                    <MarkdownErrorBoundary fallbackText={solutionData.answer}>
                                                        <ReactMarkdown
                                                            remarkPlugins={[remarkMath]}
                                                            rehypePlugins={[rehypeKatex]}
                                                        >
                                                            {processLatexContent(String(solutionData.answer))}
                                                        </ReactMarkdown>
                                                    </MarkdownErrorBoundary>
                                                ) : (
                                                    <p className="text-neutral-500 italic">No answer available</p>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Step-by-Step Solution Section */}
                                    {solutionData.metadata?.step_by_step && Array.isArray(solutionData.metadata.step_by_step) && solutionData.metadata.step_by_step.length > 0 && (
                                        <div className="space-y-3">
                                            <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider flex items-center gap-2">
                                                <Icon icon="lucide:list-ordered" className="text-indigo-400" width={14} />
                                                Step-by-Step Solution
                                            </span>
                                            <div className="space-y-3">
                                                {solutionData.metadata.step_by_step.map((step, idx) => (
                                                    <div key={idx} className="p-4 bg-neutral-950 border border-neutral-800 rounded-lg relative">
                                                        <div className="absolute -left-3 top-4 w-6 h-6 rounded-full bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center">
                                                            <span className="text-xs font-bold text-indigo-400">{idx + 1}</span>
                                                        </div>
                                                        <div className="pl-4 prose prose-invert prose-sm max-w-none text-neutral-300">
                                                            <MarkdownErrorBoundary fallbackText={step}>
                                                                <ReactMarkdown
                                                                    remarkPlugins={[remarkMath]}
                                                                    rehypePlugins={[rehypeKatex]}
                                                                >
                                                                    {processLatexContent(String(step))}
                                                                </ReactMarkdown>
                                                            </MarkdownErrorBoundary>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Explanation Section */}
                                    <div className="space-y-2">
                                        <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider flex items-center gap-2">
                                            <Icon icon="lucide:book-open" className="text-amber-400" width={14} />
                                            Detailed Explanation
                                        </span>
                                        <div className="p-5 bg-gradient-to-br from-neutral-950 to-neutral-900/80 border border-neutral-800 rounded-lg">
                                            <div className="prose prose-invert prose-sm max-w-none text-neutral-300 leading-relaxed [&>p]:mb-4 [&>h1]:text-emerald-300 [&>h2]:text-emerald-300 [&>h3]:text-emerald-300 [&>strong]:text-white [&>ul]:space-y-2 [&>ol]:space-y-2">
                                                {solutionData.explanation && String(solutionData.explanation).trim() ? (
                                                    <MarkdownErrorBoundary fallbackText={solutionData.explanation}>
                                                        <ReactMarkdown
                                                            remarkPlugins={[remarkMath]}
                                                            rehypePlugins={[rehypeKatex]}
                                                        >
                                                            {processLatexContent(String(solutionData.explanation))}
                                                        </ReactMarkdown>
                                                    </MarkdownErrorBoundary>
                                                ) : (
                                                    <p className="text-neutral-500 italic">No explanation available</p>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Key Concepts (if available) */}
                                    {solutionData.metadata?.key_concepts && Array.isArray(solutionData.metadata.key_concepts) && solutionData.metadata.key_concepts.length > 0 && (
                                        <div className="space-y-2">
                                            <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider flex items-center gap-2">
                                                <Icon icon="lucide:lightbulb" className="text-yellow-400" width={14} />
                                                Key Concepts
                                            </span>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                {solutionData.metadata.key_concepts.map((concept, idx) => (
                                                    <div key={idx} className="p-3 bg-yellow-500/5 border border-yellow-500/20 rounded-lg">
                                                        <div className="prose prose-invert prose-sm max-w-none text-yellow-200/90">
                                                            <MarkdownErrorBoundary fallbackText={concept}>
                                                                <ReactMarkdown
                                                                    remarkPlugins={[remarkMath]}
                                                                    rehypePlugins={[rehypeKatex]}
                                                                >
                                                                    {processLatexContent(String(concept))}
                                                                </ReactMarkdown>
                                                            </MarkdownErrorBoundary>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Common Mistakes (if available) */}
                                    {solutionData.metadata?.common_mistakes && Array.isArray(solutionData.metadata.common_mistakes) && solutionData.metadata.common_mistakes.length > 0 && (
                                        <div className="space-y-2">
                                            <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider flex items-center gap-2">
                                                <Icon icon="lucide:alert-triangle" className="text-orange-400" width={14} />
                                                Common Mistakes to Avoid
                                            </span>
                                            <div className="space-y-2">
                                                {solutionData.metadata.common_mistakes.map((mistake, idx) => (
                                                    <div key={idx} className="p-3 bg-orange-500/5 border border-orange-500/20 rounded-lg">
                                                        <div className="prose prose-invert prose-sm max-w-none text-orange-200/90">
                                                            <MarkdownErrorBoundary fallbackText={mistake}>
                                                                <ReactMarkdown
                                                                    remarkPlugins={[remarkMath]}
                                                                    rehypePlugins={[rehypeKatex]}
                                                                >
                                                                    {processLatexContent(String(mistake))}
                                                                </ReactMarkdown>
                                                            </MarkdownErrorBoundary>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    {/* Sources / Retrieved Context (only show if retrieval was used and not failed) */}
                                    {solutionData.retrievalUsed && !solutionData.retrievalFailed && solutionData.sources && solutionData.sources.length > 0 && (
                                        <div className="space-y-2">
                                            <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider flex items-center gap-2">
                                                <Icon icon="lucide:database" className="text-cyan-400" width={14} />
                                                Sources Used
                                                <span className="text-[10px] bg-cyan-500/20 text-cyan-400 px-1.5 py-0.5 rounded border border-cyan-500/30">
                                                    {solutionData.sources.length} source{solutionData.sources.length !== 1 ? 's' : ''}
                                                </span>
                                            </span>
                                            <div className="space-y-2">
                                                {solutionData.sources.map((source, idx) => (
                                                    <div key={idx} className={`p-3 rounded-lg border ${source.source_type === 'memory'
                                                        ? 'bg-indigo-500/5 border-indigo-500/20'
                                                        : 'bg-cyan-500/5 border-cyan-500/20'
                                                        }`}>
                                                        <div className="flex items-start gap-2 mb-2">
                                                            <Icon
                                                                icon={source.source_type === 'memory' ? 'lucide:brain' : 'lucide:book-open'}
                                                                className={source.source_type === 'memory' ? 'text-indigo-400' : 'text-cyan-400'}
                                                                width={14}
                                                            />
                                                            <span className={`text-[10px] uppercase tracking-wider font-medium ${source.source_type === 'memory' ? 'text-indigo-400' : 'text-cyan-400'
                                                                }`}>
                                                                {source.source_type === 'memory' ? 'Learned Pattern' : 'Knowledge Base'}
                                                            </span>
                                                            {source.similarity_score && (
                                                                <span className="text-[9px] text-neutral-500 ml-auto">
                                                                    {Math.round(source.similarity_score * 100)}% match
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div className="prose prose-invert prose-sm max-w-none text-neutral-300/90 text-xs line-clamp-3">
                                                            <MarkdownErrorBoundary fallbackText={source.content}>
                                                                <ReactMarkdown
                                                                    remarkPlugins={[remarkMath]}
                                                                    rehypePlugins={[rehypeKatex]}
                                                                >
                                                                    {processLatexContent(String(source.content).slice(0, 300) + (source.content.length > 300 ? '...' : ''))}
                                                                </ReactMarkdown>
                                                            </MarkdownErrorBoundary>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Retrieval Failed Warning */}
                                    {solutionData.retrievalFailed && (
                                        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                                            <div className="flex items-start gap-3">
                                                <Icon icon="lucide:database-off" className="text-amber-400 mt-0.5" width={18} />
                                                <div className="flex-1">
                                                    <p className="text-sm font-medium text-amber-200 mb-1">Knowledge Retrieval Unavailable</p>
                                                    <p className="text-xs text-amber-300/80">
                                                        The system was unable to retrieve relevant context from the knowledge base.
                                                        The solution was generated without citations from the curated knowledge base or learned patterns.
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* No Sources Available Notice (when retrieval was attempted and succeeded but found nothing) */}
                                    {solutionData.retrievalUsed && !solutionData.retrievalFailed && (!solutionData.sources || solutionData.sources.length === 0) && (
                                        <div className="p-3 bg-neutral-800/50 border border-neutral-700/50 rounded-lg">
                                            <div className="flex items-center gap-2">
                                                <Icon icon="lucide:search-x" className="text-neutral-500" width={14} />
                                                <p className="text-xs text-neutral-400">
                                                    No relevant sources found in the knowledge base for this problem.
                                                </p>
                                            </div>
                                        </div>
                                    )}

                                    {solutionData.confidence < 75 && (
                                        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                                            <div className="flex items-start gap-3">
                                                <Icon icon="lucide:alert-circle" className="text-amber-400 mt-0.5" />
                                                <div className="flex-1">
                                                    <p className="text-sm font-medium text-amber-200 mb-1">Human-in-the-Loop Review Required</p>
                                                    <p className="text-xs text-amber-300/80">
                                                        The solution confidence ({solutionData.confidence}%) is below the 75% threshold.
                                                        Please review the solution carefully before accepting it.
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Footer with Feedback Buttons */}
                                <div className="p-4 bg-neutral-900/50 border-t border-neutral-800 flex justify-between items-center">
                                    <button onClick={handleResetWorkspace} className="text-xs text-indigo-400 hover:text-indigo-300">Start New Problem</button>

                                    {/* Feedback Section */}
                                    <div className="flex items-center gap-3">
                                        {feedbackSubmitted && (
                                            <span className={`text-xs font-medium px-3 py-1 rounded-full ${feedbackSubmitted === 'correct'
                                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                                : 'bg-red-500/20 text-red-400 border border-red-500/30'
                                                }`}>
                                                <Icon icon="lucide:check" className="inline mr-1" width={12} />
                                                Feedback Submitted
                                            </span>
                                        )}

                                        {!feedbackSubmitted && (
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => handleFeedback(true)}
                                                    disabled={!solutionData?.memoryId || feedbackSubmitted}
                                                    className={`px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1.5 ${solutionData?.memoryId
                                                        ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500/50 hover:shadow-lg hover:shadow-emerald-500/10'
                                                        : 'bg-neutral-800 border border-neutral-700 opacity-50 cursor-not-allowed text-neutral-500'
                                                        }`}
                                                    title={!solutionData?.memoryId ? 'Feedback unavailable: Solution not stored in memory' : 'Mark as correct'}
                                                >
                                                    <Icon icon="lucide:check-circle" width={14} />
                                                    Correct
                                                </button>
                                                <button
                                                    onClick={() => handleFeedback(false)}
                                                    disabled={!solutionData?.memoryId || feedbackSubmitted}
                                                    className={`px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1.5 ${solutionData?.memoryId
                                                        ? 'bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 hover:border-red-500/50 hover:shadow-lg hover:shadow-red-500/10'
                                                        : 'bg-neutral-800 border border-neutral-700 opacity-50 cursor-not-allowed text-neutral-500'
                                                        }`}
                                                    title={!solutionData?.memoryId ? 'Feedback unavailable: Solution not stored in memory' : 'Mark as incorrect'}
                                                >
                                                    <Icon icon="lucide:x-circle" width={14} />
                                                    Incorrect
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </>
                        )}

                        {/* LOADING STATE - Placeholder for the right panel */}
                        {viewState === 'processing' && (
                            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                                <Icon icon="lucide:loader-2" className="text-indigo-500 animate-spin mb-4" width={48} />
                                <h3 className="text-neutral-300 font-medium text-lg">Processing Your Problem...</h3>
                                <p className="text-neutral-500 text-sm mt-2 mb-6">Agents are analyzing the input and computing the solution.</p>

                                {/* Stop & Start New Button */}
                                <button
                                    onClick={handleResetWorkspace}
                                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 hover:border-red-500/50 hover:text-red-300 transition-all duration-200 group"
                                >
                                    <Icon icon="lucide:square" className="group-hover:scale-110 transition-transform" width={16} />
                                    <span className="text-sm font-medium">Stop & Start New</span>
                                </button>
                            </div>
                        )}

                    </div>
                </section>
            )}

            {/* Section 3: Agent Thinking Process - Visual Cards */}
            {viewState !== 'input' && (
                <section>
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-sm font-medium text-neutral-400 flex items-center gap-2">
                            <Icon icon="lucide:brain" className="text-indigo-400" />
                            Agent Thinking Process
                        </h2>
                        <div className="flex items-center gap-3">
                            {viewState === 'processing' && (
                                <>
                                    <span className="text-[10px] bg-indigo-500/10 text-indigo-400 px-3 py-1 rounded-full border border-indigo-500/20 animate-pulse flex items-center gap-1.5">
                                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping"></span>
                                        Agents Working...
                                    </span>
                                    <button
                                        onClick={handleResetWorkspace}
                                        className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 hover:text-red-300 transition-all text-xs font-medium"
                                    >
                                        <Icon icon="lucide:x" width={12} />
                                        Stop
                                    </button>
                                </>
                            )}
                            {viewState === 'solution' && (
                                <button
                                    onClick={handleResetWorkspace}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/20 hover:text-indigo-300 transition-all text-xs font-medium"
                                >
                                    <Icon icon="lucide:plus" width={12} />
                                    New Problem
                                </button>
                            )}
                        </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                        {/* Agent Cards */}
                        {[
                            {
                                name: 'parser',
                                label: 'Parser Agent',
                                icon: 'lucide:scan-text',
                                desc: 'Analyzing problem structure...',
                                color: 'blue'
                            },
                            {
                                name: 'intent_router',
                                label: 'Router Agent',
                                icon: 'lucide:route',
                                desc: 'Classifying problem type...',
                                color: 'violet'
                            },
                            {
                                name: 'solver',
                                label: 'Solver Agent',
                                icon: 'lucide:calculator',
                                desc: 'Computing solution...',
                                color: 'amber'
                            },
                            {
                                name: 'verifier',
                                label: 'Verifier Agent',
                                icon: 'lucide:shield-check',
                                desc: 'Validating correctness...',
                                color: 'emerald'
                            },
                            {
                                name: 'explainer',
                                label: 'Explainer Agent',
                                icon: 'lucide:graduation-cap',
                                desc: 'Generating explanation...',
                                color: 'rose'
                            }
                        ].map((agent, idx) => {
                            const agentOutput = agentOutputs[agent.name];
                            const isActive = activeAgents.includes(agent.name);
                            const isDone = agentOutput && agentOutput.status === 'completed';
                            const isFailed = agentOutput && agentOutput.status === 'failed';

                            // Determine status
                            let status = 'pending';
                            if (isActive) status = 'active';
                            else if (isDone) status = 'done';
                            else if (isFailed) status = 'failed';

                            // Color mappings
                            const colorMap = {
                                blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', glow: 'shadow-blue-500/20' },
                                violet: { bg: 'bg-violet-500/10', border: 'border-violet-500/30', text: 'text-violet-400', glow: 'shadow-violet-500/20' },
                                amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', glow: 'shadow-amber-500/20' },
                                emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', glow: 'shadow-emerald-500/20' },
                                rose: { bg: 'bg-rose-500/10', border: 'border-rose-500/30', text: 'text-rose-400', glow: 'shadow-rose-500/20' }
                            };
                            const colors = colorMap[agent.color];

                            return (
                                <div
                                    key={agent.name}
                                    className={`relative rounded-xl border p-4 transition-all duration-300 ${status === 'active'
                                        ? `${colors.bg} ${colors.border} shadow-lg ${colors.glow}`
                                        : status === 'done'
                                            ? 'bg-neutral-900/80 border-emerald-500/40'
                                            : status === 'failed'
                                                ? 'bg-red-900/20 border-red-500/40'
                                                : 'bg-neutral-900/40 border-neutral-800 opacity-50'
                                        }`}
                                >
                                    {/* Status indicator */}
                                    <div className="absolute top-3 right-3">
                                        {status === 'active' && (
                                            <Icon icon="lucide:loader-2" className={`${colors.text} animate-spin`} width={14} />
                                        )}
                                        {status === 'done' && (
                                            <Icon icon="lucide:check-circle" className="text-emerald-400" width={14} />
                                        )}
                                        {status === 'failed' && (
                                            <Icon icon="lucide:x-circle" className="text-red-400" width={14} />
                                        )}
                                        {status === 'pending' && (
                                            <Icon icon="lucide:circle-dashed" className="text-neutral-600" width={14} />
                                        )}
                                    </div>

                                    {/* Agent icon */}
                                    <div className={`w-10 h-10 rounded-lg ${status === 'done' ? 'bg-emerald-500/20' : colors.bg} flex items-center justify-center mb-3`}>
                                        <Icon icon="agent.icon" className={`${status === 'done' ? 'text-emerald-400' : colors.text}`} width={20} />
                                    </div>

                                    {/* Agent name */}
                                    <h3 className={`text-sm font-semibold mb-1 ${status === 'done' ? 'text-emerald-300' : status === 'active' ? 'text-white' : 'text-neutral-400'}`}>
                                        {agent.label}
                                    </h3>

                                    {/* Status/Output */}
                                    <div className="text-[11px] text-neutral-500 min-h-[40px]">
                                        {status === 'pending' && <span className="italic">Waiting...</span>}
                                        {status === 'active' && <span className="text-neutral-300">{agent.desc}</span>}
                                        {status === 'done' && agentOutput && (
                                            <span className="text-emerald-300/80 line-clamp-2">
                                                {agentOutput.output || 'Completed successfully'}
                                            </span>
                                        )}
                                        {status === 'failed' && agentOutput && (
                                            <span className="text-red-400">
                                                {agentOutput.error || 'Failed'}
                                            </span>
                                        )}
                                    </div>

                                    {/* Execution time */}
                                    {agentOutput && agentOutput.time_ms && (
                                        <div className="mt-2 text-[9px] text-neutral-600 flex items-center gap-1">
                                            <Icon icon="lucide:clock" width={10} />
                                            {Math.round(agentOutput.time_ms)}ms
                                        </div>
                                    )}

                                    {/* Self-learning indicator for solver agent */}
                                    {agent.name === 'solver' && agentOutput && agentOutput.metadata?.self_learning_active && (
                                        <div className="mt-2 flex items-center gap-1 text-[9px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-500/30 w-fit">
                                            <Icon icon="lucide:brain" width={10} />
                                            <span>Learning from {agentOutput.metadata.memory_patterns_count} patterns</span>
                                        </div>
                                    )}

                                    {/* Progress bar for active agent */}
                                    {status === 'active' && (
                                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-neutral-800 overflow-hidden rounded-b-xl">
                                            <div className={`h-full ${colors.text.replace('text-', 'bg-')} animate-pulse`} style={{ width: '60%' }}></div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </section>
            )}
        </div>
    );
};

export default Workspace;
