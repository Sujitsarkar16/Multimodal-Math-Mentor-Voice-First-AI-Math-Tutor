import React from 'react';

const AgentsSwarm = () => {
    const agents = [
        { id: 'ocr', name: 'OCR Processor', status: 'active', role: 'Visual Perception', tasks: 124 },
        { id: 'math', name: 'Math Solver', status: 'idle', role: 'Logical Reasoning', tasks: 89 },
        { id: 'verifier', name: 'Solution Verifier', status: 'idle', role: 'Quality Assurance', tasks: 89 },
        { id: 'rag', name: 'Context Retriever', status: 'active', role: 'Memory Access', tasks: 450 },
    ];

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <div className="mb-6">
                <h2 className="text-2xl font-semibold text-white">Agent Swarm Status</h2>
                <p className="text-neutral-400 text-sm mt-1">Monitor real-time status of the multi-agent system.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                {agents.map(agent => (
                    <div key={agent.id} className="bg-neutral-900/60 backdrop-blur-xl border border-neutral-800 rounded-lg p-6">
                        <div className="flex justify-between items-start mb-4">
                            <div className="w-10 h-10 rounded-lg bg-neutral-800 flex items-center justify-center">
                                <Icon icon="lucide:bot" className="text-white" width={20} />
                            </div>
                            <span className={`text-[10px] px-2 py-1 rounded-full border ${
                                agent.status === 'active' 
                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                                    : 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20'
                            }`}>
                                {agent.status === 'active' ? '● Online' : '○ Idle'}
                            </span>
                        </div>
                        <h3 className="text-white font-semibold text-base">{agent.name}</h3>
                        <p className="text-neutral-500 text-xs mt-1">{agent.role}</p>

                        <div className="mt-6 pt-4 border-t border-neutral-800 flex justify-between items-center">
                            <span className="text-neutral-400 text-xs">Tasks Processed</span>
                            <span className="text-white text-sm font-mono">{agent.tasks}</span>
                        </div>
                    </div>
                ))}
            </div>

            <div className="bg-neutral-900/60 backdrop-blur-xl border border-dashed border-neutral-800 rounded-lg p-6 h-[300px] flex items-center justify-center">
                <p className="text-neutral-600">Real-time usage graph placeholder</p>
            </div>
        </div>
    );
};

export default AgentsSwarm;
