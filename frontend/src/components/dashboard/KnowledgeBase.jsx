import React from 'react';
import { Icon } from '@iconify/react';

const KnowledgeBase = () => {
    return (
        <div className="p-6 max-w-7xl mx-auto">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-semibold text-white">Knowledge Base</h2>
                    <p className="text-neutral-400 text-sm mt-1">Manage textbooks, formula sheets, and reference materials.</p>
                </div>
                <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-md text-sm font-medium transition-colors">
                    <Icon icon="lucide:upload" width={14} />
                    Upload Resource
                </button>
            </div>

            {/* Empty State */}
            <div className="bg-neutral-900/60 backdrop-blur-xl border border-dashed border-neutral-800 rounded-lg p-16 flex flex-col items-center justify-center">
                <div className="w-16 h-16 rounded-full bg-neutral-800 flex items-center justify-center mb-6">
                    <Icon icon="lucide:library" className="text-neutral-500" width={32} />
                </div>
                <h3 className="text-neutral-200 font-medium mb-2">No documents uploaded</h3>
                <p className="text-neutral-500 text-sm text-center max-w-[300px]">
                    Upload JEE mathematics textbooks or PDF notes to enhance the RAG retrieval system.
                </p>
            </div>
        </div>
    );
};

export default KnowledgeBase;
