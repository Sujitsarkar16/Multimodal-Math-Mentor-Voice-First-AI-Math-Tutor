import React from 'react';
import { Icon } from '@iconify/react';

const Sidebar = ({ activeTab, setActiveTab }) => {
    const navItems = [
        { id: 'workspace', label: 'Workspace', icon: 'lucide:layout-dashboard' },
        { id: 'knowledge', label: 'Knowledge Base', icon: 'lucide:library' },
        { id: 'history', label: 'History', icon: 'lucide:history' },
    ];

    return (
        <aside className="w-64 border-r border-neutral-800 bg-neutral-950 flex flex-col justify-between hidden md:flex">
            <div>
                <div className="h-16 flex items-center px-6 border-b border-neutral-800">
                    <div className="flex items-center gap-2 text-white">
                        <Icon icon="lucide:sigma" width={20} height={20} />
                        <span className="text-base font-semibold tracking-tight">JEE.AI</span>
                    </div>
                </div>

                <nav className="p-4 space-y-1">
                    {navItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id)}
                            className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === item.id
                                ? 'text-white bg-neutral-800/50 border border-neutral-700/50'
                                : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900 border border-transparent'
                                }`}
                        >
                            <Icon icon={item.icon} />
                            {item.label}
                        </button>
                    ))}
                </nav>
            </div>

            <div className="p-4 border-t border-neutral-800">
                <div className="flex items-center gap-3 p-2 rounded-md hover:bg-neutral-900 cursor-pointer transition-colors">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-xs text-white font-medium">A</div>
                    <div className="flex flex-col text-left">
                        <span className="text-xs font-medium text-neutral-200">Aspirant User</span>
                        <span className="text-[10px] text-neutral-500">Free Plan</span>
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
