import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Icon } from '@iconify/react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { getKnowledgeBase, createKnowledgeEntry, deleteKnowledgeEntry } from '../../services/api';

// ============================================================================
// Configuration Constants
// ============================================================================

const TOPIC_CONFIG = {
    algebra: { icon: 'lucide:variable', color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/30' },
    calculus: { icon: 'lucide:trending-up', color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
    probability: { icon: 'lucide:dice-5', color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/30' },
    linear_algebra: { icon: 'lucide:grid-3x3', color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
    trigonometry: { icon: 'lucide:triangle', color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/30' },
    geometry: { icon: 'lucide:hexagon', color: 'text-pink-400', bg: 'bg-pink-500/10', border: 'border-pink-500/30' },
    common_mistakes: { icon: 'lucide:alert-triangle', color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
    verification: { icon: 'lucide:check-circle', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
};

const TYPE_CONFIG = {
    formula: { label: 'Formula', color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' },
    technique: { label: 'Technique', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
    template: { label: 'Template', color: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
    pitfall: { label: 'Common Mistake', color: 'bg-red-500/20 text-red-300 border-red-500/30' },
    constraint: { label: 'Constraint', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' },
};

const DIFFICULTY_CONFIG = {
    easy: { label: 'Easy', color: 'text-green-400', bgColor: 'bg-green-400', dots: 1 },
    medium: { label: 'Medium', color: 'text-amber-400', bgColor: 'bg-amber-400', dots: 2 },
    hard: { label: 'Hard', color: 'text-red-400', bgColor: 'bg-red-400', dots: 3 },
};

const DEFAULT_ENTRY = { content: '', topic: 'algebra', type: 'formula', difficulty: 'medium', tags: '' };

// ============================================================================
// Memoized Subcomponents
// ============================================================================

const TopicIcon = React.memo(({ topic }) => {
    const config = TOPIC_CONFIG[topic] || { icon: 'lucide:book', color: 'text-neutral-400' };
    return <Icon icon={config.icon} className={config.color} width={18} />;
});

const TypeBadge = React.memo(({ type }) => {
    const config = TYPE_CONFIG[type] || { label: type, color: 'bg-neutral-500/20 text-neutral-300 border-neutral-500/30' };
    return (
        <span className={`px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider rounded border ${config.color}`}>
            {config.label}
        </span>
    );
});

const DifficultyIndicator = React.memo(({ difficulty }) => {
    const config = DIFFICULTY_CONFIG[difficulty] || DIFFICULTY_CONFIG.medium;
    return (
        <div className="flex items-center gap-1">
            {[0, 1, 2].map(i => (
                <div key={i} className={`w-1.5 h-1.5 rounded-full ${i < config.dots ? config.bgColor : 'bg-neutral-700'}`} />
            ))}
            <span className={`text-[10px] ml-1 ${config.color}`}>{config.label}</span>
        </div>
    );
});

const StatsCard = React.memo(({ icon, iconBg, value, label }) => (
    <div className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-4">
        <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg ${iconBg} flex items-center justify-center`}>
                <Icon icon={icon} width={20} />
            </div>
            <div>
                <p className="text-2xl font-bold text-white">{value}</p>
                <p className="text-xs text-neutral-500">{label}</p>
            </div>
        </div>
    </div>
));

const EntryCard = React.memo(({ entry, isExpanded, onToggle, onDelete }) => {
    const topicConfig = TOPIC_CONFIG[entry.metadata.topic] || { bg: 'bg-neutral-500/10', border: 'border-neutral-500/30' };

    return (
        <div className={`group relative bg-neutral-900/60 backdrop-blur border rounded-lg overflow-hidden transition-all duration-200 hover:border-neutral-600 ${topicConfig.border}`}>
            <div className={`px-4 py-3 cursor-pointer ${topicConfig.bg}`} onClick={() => onToggle(entry.id)}>
                <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                        <TopicIcon topic={entry.metadata.topic} />
                        <TypeBadge type={entry.metadata.type} />
                        <DifficultyIndicator difficulty={entry.metadata.difficulty} />
                    </div>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={(e) => { e.stopPropagation(); onDelete(entry.id); }}
                            className="p-1 opacity-0 group-hover:opacity-100 text-neutral-500 hover:text-red-400 transition-all"
                            title="Delete"
                        >
                            <Icon icon="lucide:trash-2" width={14} />
                        </button>
                        <Icon icon={isExpanded ? 'lucide:chevron-up' : 'lucide:chevron-down'} className="text-neutral-500" width={16} />
                    </div>
                </div>
            </div>

            <div className={`px-4 pb-4 pt-2 ${isExpanded ? '' : 'line-clamp-3'}`}>
                <div className="prose prose-sm prose-invert max-w-none text-neutral-300 leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                        {entry.content}
                    </ReactMarkdown>
                </div>
            </div>

            {entry.metadata.tags?.length > 0 && (
                <div className="px-4 pb-3 flex flex-wrap gap-1.5">
                    {entry.metadata.tags.map((tag, idx) => (
                        <span key={idx} className="px-2 py-0.5 text-[10px] bg-neutral-800 text-neutral-400 rounded-full">
                            #{tag}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
});

// ============================================================================
// Main Component
// ============================================================================

const KnowledgeBase = () => {
    const [entries, setEntries] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedTopic, setSelectedTopic] = useState('all');
    const [selectedType, setSelectedType] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedEntry, setExpandedEntry] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [viewMode, setViewMode] = useState('cards');
    const [newEntry, setNewEntry] = useState(DEFAULT_ENTRY);
    const [saving, setSaving] = useState(false);

    // Fetch data on mount
    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getKnowledgeBase();
            setEntries(data.entries || []);
            setStats(data.stats);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    // Filter entries - O(n) single pass with memoization
    const filteredEntries = useMemo(() => {
        const searchLower = searchQuery.toLowerCase();
        return entries.filter(entry => {
            const { topic, type, tags = [] } = entry.metadata;
            if (selectedTopic !== 'all' && topic !== selectedTopic) return false;
            if (selectedType !== 'all' && type !== selectedType) return false;
            if (searchQuery) {
                const inContent = entry.content.toLowerCase().includes(searchLower);
                const inTags = tags.some(t => t.toLowerCase().includes(searchLower));
                if (!inContent && !inTags) return false;
            }
            return true;
        });
    }, [entries, selectedTopic, selectedType, searchQuery]);

    // Group by topic - O(n)
    const groupedEntries = useMemo(() => {
        return filteredEntries.reduce((acc, entry) => {
            const topic = entry.metadata.topic || 'other';
            (acc[topic] = acc[topic] || []).push(entry);
            return acc;
        }, {});
    }, [filteredEntries]);

    const topics = useMemo(() => stats?.topics ? Object.keys(stats.topics).sort() : [], [stats]);

    const handleToggleExpand = useCallback((id) => {
        setExpandedEntry(prev => prev === id ? null : id);
    }, []);

    const handleDelete = useCallback(async (id) => {
        if (!confirm('Delete this knowledge entry?')) return;
        try {
            await deleteKnowledgeEntry(id);
            setEntries(prev => prev.filter(e => e.id !== id));
        } catch (err) {
            setError(err.message);
        }
    }, []);

    const handleSubmit = useCallback(async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const tags = newEntry.tags.split(',').map(t => t.trim()).filter(Boolean);
            await createKnowledgeEntry({ ...newEntry, tags });
            await fetchData();
            setNewEntry(DEFAULT_ENTRY);
            setShowAddModal(false);
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    }, [newEntry, fetchData]);

    const updateNewEntry = useCallback((field, value) => {
        setNewEntry(prev => ({ ...prev, [field]: value }));
    }, []);

    if (loading) {
        return (
            <div className="p-6 max-w-7xl mx-auto flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-4">
                    <Icon icon="lucide:loader-2" className="text-indigo-400 animate-spin" width={40} />
                    <p className="text-neutral-400">Loading knowledge base...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                <div>
                    <h2 className="text-2xl font-semibold text-white flex items-center gap-3">
                        <Icon icon="lucide:library" className="text-indigo-400" />
                        Knowledge Base
                    </h2>
                    <p className="text-neutral-400 text-sm mt-1">Mathematical formulas and reference materials for RAG</p>
                </div>
                <button onClick={() => setShowAddModal(true)} className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-indigo-500/20">
                    <Icon icon="lucide:plus" width={16} />
                    Add Knowledge
                </button>
            </div>

            {/* Error */}
            {error && (
                <div className="mb-6 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
                    <Icon icon="lucide:alert-circle" className="text-red-400" width={20} />
                    <span className="text-red-300 text-sm">{error}</span>
                    <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">
                        <Icon icon="lucide:x" width={16} />
                    </button>
                </div>
            )}

            {/* Stats */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <StatsCard icon="lucide:book-open" iconBg="bg-indigo-500/20 text-indigo-400" value={stats.total_entries} label="Total Entries" />
                    <StatsCard icon="lucide:folder" iconBg="bg-purple-500/20 text-purple-400" value={Object.keys(stats.topics).length} label="Topics" />
                    <StatsCard icon="lucide:lightbulb" iconBg="bg-emerald-500/20 text-emerald-400" value={stats.types?.formula || 0} label="Formulas" />
                    <StatsCard icon="lucide:alert-triangle" iconBg="bg-amber-500/20 text-amber-400" value={stats.types?.pitfall || 0} label="Pitfalls" />
                </div>
            )}

            {/* Filters */}
            <div className="flex flex-col md:flex-row gap-4 mb-6">
                <div className="relative flex-1">
                    <Icon icon="lucide:search" className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" width={18} />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search..."
                        className="w-full pl-10 pr-4 py-2.5 bg-neutral-900 border border-neutral-800 rounded-lg text-white placeholder-neutral-600 focus:outline-none focus:border-indigo-500"
                    />
                </div>
                <select value={selectedTopic} onChange={(e) => setSelectedTopic(e.target.value)} className="px-4 py-2.5 bg-neutral-900 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-indigo-500 min-w-[160px]">
                    <option value="all">All Topics</option>
                    {topics.map(t => <option key={t} value={t}>{t.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>)}
                </select>
                <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)} className="px-4 py-2.5 bg-neutral-900 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-indigo-500 min-w-[140px]">
                    <option value="all">All Types</option>
                    {Object.entries(TYPE_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                </select>
                <div className="flex bg-neutral-900 border border-neutral-800 rounded-lg overflow-hidden">
                    <button onClick={() => setViewMode('cards')} className={`px-3 py-2 ${viewMode === 'cards' ? 'bg-neutral-800 text-white' : 'text-neutral-500 hover:text-white'}`}>
                        <Icon icon="lucide:layout-grid" width={18} />
                    </button>
                    <button onClick={() => setViewMode('list')} className={`px-3 py-2 ${viewMode === 'list' ? 'bg-neutral-800 text-white' : 'text-neutral-500 hover:text-white'}`}>
                        <Icon icon="lucide:list" width={18} />
                    </button>
                </div>
            </div>

            {/* Count */}
            <p className="text-sm text-neutral-500 mb-4">
                Showing <span className="text-white font-medium">{filteredEntries.length}</span> of {entries.length} entries
            </p>

            {/* Content */}
            {filteredEntries.length === 0 ? (
                <div className="bg-neutral-900/60 backdrop-blur-xl border border-dashed border-neutral-800 rounded-lg p-16 flex flex-col items-center justify-center">
                    <div className="w-16 h-16 rounded-full bg-neutral-800 flex items-center justify-center mb-6">
                        <Icon icon="lucide:search-x" className="text-neutral-500" width={32} />
                    </div>
                    <h3 className="text-neutral-200 font-medium mb-2">No entries found</h3>
                    <p className="text-neutral-500 text-sm text-center max-w-[300px]">
                        {searchQuery || selectedTopic !== 'all' ? 'Try adjusting your filters.' : 'Add your first knowledge entry.'}
                    </p>
                </div>
            ) : viewMode === 'list' ? (
                <div className="space-y-8">
                    {Object.entries(groupedEntries).map(([topic, items]) => {
                        const cfg = TOPIC_CONFIG[topic] || { icon: 'lucide:book', color: 'text-neutral-400', bg: 'bg-neutral-800' };
                        return (
                            <div key={topic}>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className={`w-8 h-8 rounded-lg ${cfg.bg} flex items-center justify-center`}>
                                        <Icon icon={cfg.icon} className={cfg.color} width={18} />
                                    </div>
                                    <h3 className="text-lg font-semibold text-white">{topic.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
                                    <span className="text-sm text-neutral-500">({items.length})</span>
                                </div>
                                <div className="space-y-3 ml-11">
                                    {items.map(entry => (
                                        <EntryCard key={entry.id} entry={entry} isExpanded={expandedEntry === entry.id} onToggle={handleToggleExpand} onDelete={handleDelete} />
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredEntries.map(entry => (
                        <EntryCard key={entry.id} entry={entry} isExpanded={expandedEntry === entry.id} onToggle={handleToggleExpand} onDelete={handleDelete} />
                    ))}
                </div>
            )}

            {/* Add Modal */}
            {showAddModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
                    <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-2xl mx-4 shadow-2xl">
                        <div className="px-6 py-4 border-b border-neutral-800 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center">
                                    <Icon icon="lucide:plus" className="text-indigo-400" width={20} />
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold text-white">Add Knowledge Entry</h3>
                                    <p className="text-xs text-neutral-500">Add formulas or notes to the RAG system</p>
                                </div>
                            </div>
                            <button onClick={() => setShowAddModal(false)} className="p-2 text-neutral-500 hover:text-white transition-colors">
                                <Icon icon="lucide:x" width={20} />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-neutral-300 mb-2">Content <span className="text-red-400">*</span></label>
                                <textarea
                                    value={newEntry.content}
                                    onChange={(e) => updateNewEntry('content', e.target.value)}
                                    placeholder="Enter formula or explanation. Use LaTeX: $x^2 + y^2 = r^2$"
                                    rows={6}
                                    required
                                    minLength={10}
                                    className="w-full px-4 py-3 bg-neutral-950 border border-neutral-800 rounded-lg text-white placeholder-neutral-600 focus:outline-none focus:border-indigo-500 resize-none"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-neutral-300 mb-2">Topic</label>
                                    <select value={newEntry.topic} onChange={(e) => updateNewEntry('topic', e.target.value)} className="w-full px-4 py-2.5 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-indigo-500">
                                        {Object.keys(TOPIC_CONFIG).map(t => <option key={t} value={t}>{t.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-neutral-300 mb-2">Type</label>
                                    <select value={newEntry.type} onChange={(e) => updateNewEntry('type', e.target.value)} className="w-full px-4 py-2.5 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-indigo-500">
                                        {Object.entries(TYPE_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-neutral-300 mb-2">Difficulty</label>
                                <div className="flex gap-3">
                                    {Object.entries(DIFFICULTY_CONFIG).map(([key, cfg]) => (
                                        <button
                                            key={key}
                                            type="button"
                                            onClick={() => updateNewEntry('difficulty', key)}
                                            className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium transition-all ${newEntry.difficulty === key
                                                    ? key === 'easy' ? 'bg-green-500/20 border-green-500/50 text-green-300'
                                                        : key === 'medium' ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                                                            : 'bg-red-500/20 border-red-500/50 text-red-300'
                                                    : 'bg-neutral-900 border-neutral-800 text-neutral-500 hover:border-neutral-700'
                                                }`}
                                        >
                                            {cfg.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-neutral-300 mb-2">Tags</label>
                                <input
                                    type="text"
                                    value={newEntry.tags}
                                    onChange={(e) => updateNewEntry('tags', e.target.value)}
                                    placeholder="quadratic, roots (comma-separated)"
                                    className="w-full px-4 py-2.5 bg-neutral-950 border border-neutral-800 rounded-lg text-white placeholder-neutral-600 focus:outline-none focus:border-indigo-500"
                                />
                            </div>

                            <div className="flex items-center justify-end gap-3 pt-4 border-t border-neutral-800">
                                <button type="button" onClick={() => setShowAddModal(false)} className="px-4 py-2 text-sm text-neutral-400 hover:text-white transition-colors">Cancel</button>
                                <button type="submit" disabled={saving || newEntry.content.length < 10} className="flex items-center gap-2 px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors">
                                    {saving ? <><Icon icon="lucide:loader-2" className="animate-spin" width={16} />Saving...</> : <><Icon icon="lucide:plus" width={16} />Add Entry</>}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default KnowledgeBase;
