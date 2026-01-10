import React, { useState } from 'react';
import { Icon } from '@iconify/react';
import Sidebar from './dashboard/Sidebar';
import Workspace from './dashboard/Workspace';
import KnowledgeBase from './dashboard/KnowledgeBase';
import AgentsSwarm from './dashboard/AgentsSwarm';
import History from './dashboard/History';

const Dashboard = () => {
    const [activeTab, setActiveTab] = useState('workspace');
    const [history, setHistory] = useState([]);

    const addToHistory = (entry) => {
        setHistory(prev => [entry, ...prev]);
    };

    const renderContent = () => {
        switch (activeTab) {
            case 'workspace':
                return <Workspace onSolveComplete={addToHistory} />;
            case 'knowledge':
                return <KnowledgeBase />;
            case 'agents':
                return <AgentsSwarm />;
            case 'history':
                return <History history={history} />;
            default:
                return <Workspace />;
        }
    };

    const getPageTitle = () => {
        switch (activeTab) {
            case 'workspace': return 'Problem Solver';
            case 'knowledge': return 'Knowledge Base';
            case 'agents': return 'Agents Swarm';
            default: return 'History';
        }
    }

    return (
        <div className="flex h-screen overflow-hidden antialiased selection:bg-indigo-500/30 selection:text-indigo-200 bg-neutral-950 text-neutral-200">
            <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

            <main className="flex-1 flex flex-col h-full bg-neutral-950 relative">

                {/* Top Navigation */}
                <header className="h-16 border-b border-neutral-800 flex items-center justify-between px-6 bg-neutral-950/80 backdrop-blur-md z-10 shrink-0">
                    <div className="flex items-center gap-4">
                        <span className="text-sm font-medium text-neutral-500">Dashboard</span>
                        <span className="text-neutral-700">/</span>
                        <span className="text-sm font-medium text-neutral-200">{getPageTitle()}</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <button className="relative p-2 text-neutral-400 hover:text-white transition-colors">
                            <Icon icon="lucide:bell" />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-indigo-500 rounded-full border border-neutral-950"></span>
                        </button>
                    </div>
                </header>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto p-0">
                    {renderContent()}
                </div>
            </main>
        </div>
    );
};

export default Dashboard;
