import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { abortCurrentRequest } from '../services/api';

const WorkspaceContext = createContext();

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within WorkspaceProvider');
  }
  return context;
};

export const WorkspaceProvider = ({ children }) => {
  // Persistent state that survives component unmounting
  const [viewState, setViewState] = useState(() => {
    // Try to restore from sessionStorage
    const saved = sessionStorage.getItem('workspace_viewState');
    // Don't restore 'processing' state - there's no active request after refresh
    // Only restore 'review' or 'solution' states
    if (saved === 'review' || saved === 'solution') {
      return saved;
    }
    // Default to 'input' for any other state (including 'processing')
    return 'input';
  });

  const [pipelineStep, setPipelineStep] = useState(() => {
    const saved = sessionStorage.getItem('workspace_pipelineStep');
    return saved ? parseInt(saved, 10) : 0;
  });

  const [activeAgents, setActiveAgents] = useState(() => {
    const saved = sessionStorage.getItem('workspace_activeAgents');
    return saved ? JSON.parse(saved) : [];
  });

  const [agentOutputs, setAgentOutputs] = useState(() => {
    const saved = sessionStorage.getItem('workspace_agentOutputs');
    return saved ? JSON.parse(saved) : {};
  });

  const [agentTrace, setAgentTrace] = useState(() => {
    const saved = sessionStorage.getItem('workspace_agentTrace');
    return saved ? JSON.parse(saved) : [];
  });

  const [solutionData, setSolutionData] = useState(() => {
    const saved = sessionStorage.getItem('workspace_solutionData');
    return saved ? JSON.parse(saved) : null;
  });

  const [error, setError] = useState(null);
  const [processingProblem, setProcessingProblem] = useState(null);

  // Clear stale 'processing' state on mount (in case of browser crash or hard refresh)
  useEffect(() => {
    const savedState = sessionStorage.getItem('workspace_viewState');
    if (savedState === 'processing') {
      // Clear stale processing state
      sessionStorage.removeItem('workspace_viewState');
      sessionStorage.removeItem('workspace_pipelineStep');
      sessionStorage.removeItem('workspace_activeAgents');
    }
  }, []); // Run only on mount

  // Persist state to sessionStorage whenever it changes
  // Don't persist 'processing' state - it can't be resumed after refresh
  useEffect(() => {
    if (viewState !== 'processing') {
      sessionStorage.setItem('workspace_viewState', viewState);
    }
  }, [viewState]);

  useEffect(() => {
    sessionStorage.setItem('workspace_pipelineStep', pipelineStep.toString());
  }, [pipelineStep]);

  useEffect(() => {
    sessionStorage.setItem('workspace_activeAgents', JSON.stringify(activeAgents));
  }, [activeAgents]);

  useEffect(() => {
    sessionStorage.setItem('workspace_agentOutputs', JSON.stringify(agentOutputs));
  }, [agentOutputs]);

  useEffect(() => {
    sessionStorage.setItem('workspace_agentTrace', JSON.stringify(agentTrace));
  }, [agentTrace]);

  useEffect(() => {
    if (solutionData) {
      sessionStorage.setItem('workspace_solutionData', JSON.stringify(solutionData));
    } else {
      sessionStorage.removeItem('workspace_solutionData');
    }
  }, [solutionData]);

  const resetWorkspace = useCallback(() => {
    // Abort any ongoing streaming request
    abortCurrentRequest();

    setViewState('input');
    setPipelineStep(0);
    setActiveAgents([]);
    setAgentOutputs({});
    setAgentTrace([]);
    setSolutionData(null);
    setError(null);
    setProcessingProblem(null);

    // Clear sessionStorage
    sessionStorage.removeItem('workspace_viewState');
    sessionStorage.removeItem('workspace_pipelineStep');
    sessionStorage.removeItem('workspace_activeAgents');
    sessionStorage.removeItem('workspace_agentOutputs');
    sessionStorage.removeItem('workspace_agentTrace');
    sessionStorage.removeItem('workspace_solutionData');
  }, []);

  const updateAgentProgress = useCallback((update) => {
    const { agent, status, data } = update;

    // Update active agents list
    if (status === 'started') {
      setActiveAgents(prev => {
        if (!prev.includes(agent)) {
          return [...prev, agent];
        }
        return prev;
      });
    } else if (status === 'completed') {
      setActiveAgents(prev => prev.filter(a => a !== agent));

      // Store agent output for display
      setAgentOutputs(prev => ({
        ...prev,
        [agent]: {
          status: 'completed',
          input: data.input,
          output: data.output,
          time_ms: data.time_ms,
          success: data.success
        }
      }));
    } else if (status === 'failed') {
      setActiveAgents(prev => prev.filter(a => a !== agent));

      setAgentOutputs(prev => ({
        ...prev,
        [agent]: {
          status: 'failed',
          error: data.error,
          time_ms: data.time_ms
        }
      }));
    }
  }, []);

  const value = {
    // State
    viewState,
    pipelineStep,
    activeAgents,
    agentOutputs,
    agentTrace,
    solutionData,
    error,
    processingProblem,

    // Setters
    setViewState,
    setPipelineStep,
    setActiveAgents,
    setAgentOutputs,
    setAgentTrace,
    setSolutionData,
    setError,
    setProcessingProblem,

    // Actions
    resetWorkspace,
    updateAgentProgress,

    // Check if processing
    isProcessing: viewState === 'processing' || activeAgents.length > 0
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
};
