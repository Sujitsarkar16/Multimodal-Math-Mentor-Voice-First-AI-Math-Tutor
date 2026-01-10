import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Icon } from '@iconify/react';
import { getHistory } from '../../services/api';

// Status configuration - O(1) lookup
const STATUS_CONFIG = {
    Correct: { badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', dot: 'bg-emerald-400' },
    Solved: { badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', dot: 'bg-emerald-400' },
    Incorrect: { badge: 'bg-red-500/10 text-red-400 border-red-500/20', dot: 'bg-red-400' },
    default: { badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20', dot: 'bg-amber-400' },
};

const StatusBadge = React.memo(({ status }) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.default;
    return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${config.badge}`}>
            <span className={`w-1 h-1 rounded-full ${config.dot}`} />
            {status}
        </span>
    );
});

const HistoryRow = React.memo(({ item, index }) => (
    <tr className="group hover:bg-neutral-900/50 transition-colors">
        <td className="px-6 py-3 text-xs font-medium text-white font-mono">
            {item.id?.substring(0, 12) || `#${index}`}
        </td>
        <td className="px-6 py-3 text-xs text-neutral-400">{item.date}</td>
        <td className="px-6 py-3 text-xs text-neutral-300">{item.topic}</td>
        <td className="px-6 py-3"><StatusBadge status={item.status} /></td>
        <td className="px-6 py-3 text-xs text-neutral-400">
            {item.confidence ? `${Math.round(item.confidence * 100)}%` : '-'}
        </td>
        <td className="px-6 py-3 text-right">
            <button className="bg-transparent border-none text-neutral-500 hover:text-white cursor-pointer transition-colors" title="View">
                <Icon icon="lucide:external-link" width={16} />
            </button>
        </td>
    </tr>
));

const History = ({ history: localHistory = [] }) => {
    const [serverHistory, setServerHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const result = await getHistory(20);
                setServerHistory(result.entries || []);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    // Merge local + server history, O(n + m) with Set-based dedup
    const combinedHistory = useMemo(() => {
        const localIds = new Set(localHistory.map(h => h.id));

        const serverMapped = serverHistory
            .filter(s => !localIds.has(s.id))
            .map(s => ({
                id: s.id,
                date: new Date(s.created_at).toLocaleDateString(),
                topic: s.topic || 'General',
                status: s.user_feedback === 'correct' ? 'Correct' : s.user_feedback === 'incorrect' ? 'Incorrect' : 'Solved',
                answer: s.final_answer,
                confidence: s.confidence
            }));

        return [...localHistory, ...serverMapped];
    }, [localHistory, serverHistory]);

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <div className="mb-6">
                <h2 className="text-2xl font-semibold text-white">Problem History</h2>
                <p className="text-neutral-400 text-sm mt-1">
                    Archive of solved problems{serverHistory.length > 0 && ` (${serverHistory.length} from server)`}
                </p>
            </div>

            {loading && <div className="text-center py-8 text-neutral-500">Loading history...</div>}

            {error && (
                <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg text-red-200 mb-4">
                    Failed to load: {error}
                </div>
            )}

            <div className="border border-neutral-800 rounded-lg bg-neutral-900/30 overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="border-b border-neutral-800 bg-neutral-900/50">
                            {['Problem ID', 'Date', 'Topic', 'Status', 'Confidence', 'Actions'].map((h, i) => (
                                <th key={h} className={`px-6 py-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider ${i === 5 ? 'text-right' : ''}`}>
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800">
                        {combinedHistory.length > 0 ? (
                            combinedHistory.map((item, idx) => <HistoryRow key={item.id || idx} item={item} index={idx} />)
                        ) : !loading && (
                            <tr>
                                <td colSpan="6" className="px-6 py-12 text-center text-neutral-600">
                                    No history yet. Solve problems to see them here!
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default History;
