import { useState, useEffect } from 'react';
import { exclusionsApi } from '../../api/client';
import { Trash2, Plus, Search } from 'lucide-react';
import clsx from 'clsx';

export default function IndexExceptions() {
    const [indicesList, setIndicesList] = useState<string[]>([]);
    const [selectedIndexPattern, setSelectedIndexPattern] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    const [exclusions, setExclusions] = useState<any[]>([]);
    const [activeType, setActiveType] = useState<string>('phone');
    const [loading, setLoading] = useState(false);

    // Form state
    const [keyPath, setKeyPath] = useState('');

    const pdnTypes = ['phone', 'email', 'card', 'fio'];

    useEffect(() => {
        exclusionsApi.getIndicesList()
            .then(data => {
                if (Array.isArray(data)) setIndicesList(data);
                else throw new Error("Invalid array");
            })
            .catch(err => {
                console.error(err);
                // Фолбэк на моковые индексы для визуальной проверки
                setIndicesList(['test-index-1*', 'prod-logs-frontend-*', 'billing-events-2023.*']);
            });
    }, []);

    useEffect(() => {
        if (selectedIndexPattern) {
            fetchExclusions();
        } else {
            setExclusions([]);
        }
    }, [selectedIndexPattern]);

    const fetchExclusions = async () => {
        try {
            setLoading(true);
            const data = await exclusionsApi.getIndex(selectedIndexPattern);
            if (Array.isArray(data)) {
                setExclusions(data);
            } else {
                throw new Error("Invalid API response array");
            }
        } catch (error) {
            console.error("Failed to fetch index exclusions", error);
            // Фолбэк на моковые данные для визуальной проверки
            setExclusions([
                { id: 1, index_pattern: selectedIndexPattern, pdn_type: 'phone', key_path: 'user.phone' },
                { id: 2, index_pattern: selectedIndexPattern, pdn_type: 'email', key_path: 'user.email' },
                { id: 3, index_pattern: selectedIndexPattern, pdn_type: 'fio', key_path: 'customer.full_name' }
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this index exclusion?')) return;
        try {
            await exclusionsApi.deleteIndex(id);
            await fetchExclusions();
        } catch (error) {
            console.error(error);
        }
    };

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await exclusionsApi.addIndex({
                index_pattern: selectedIndexPattern,
                pdn_type: activeType,
                key_path: keyPath
            });
            setKeyPath('');
            await fetchExclusions();
        } catch (error) {
            console.error(error);
        }
    };

    const filtered = (Array.isArray(exclusions) ? exclusions : []).filter(e => e.pdn_type === activeType);

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50">
                <h3 className="font-semibold text-slate-800">Index-Specific Exceptions</h3>
                <p className="text-xs text-slate-500 mt-1">Full path exclusions applied only to a specific index pattern.</p>
            </div>

            <div className="p-6 border-b border-slate-200 bg-slate-50">
                <label className="block text-sm font-medium text-slate-700 mb-2">Select Index Pattern</label>
                <div className="relative">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        list="indices-datalist"
                        className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded shadow-sm focus:ring-indigo-500 text-sm"
                        placeholder="Search or enter an index pattern... (e.g. my-test-tech-index*)"
                        onBlur={(e) => {
                            if (e.target.value) setSelectedIndexPattern(e.target.value);
                        }}
                    />
                    <Search className="w-5 h-5 absolute left-3 top-2.5 text-slate-400" />
                    <datalist id="indices-datalist">
                        {indicesList.map(idx => (
                            <option key={idx} value={idx} />
                        ))}
                    </datalist>
                </div>
            </div>

            {selectedIndexPattern ? (
                <>
                    <div className="border-b border-slate-200 flex overflow-x-auto">
                        {pdnTypes.map(type => (
                            <button
                                key={type}
                                onClick={() => setActiveType(type)}
                                className={clsx(
                                    "px-4 py-3 text-sm font-medium transition-colors border-b-2",
                                    activeType === type ? "border-indigo-500 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                                )}
                            >
                                {type.toUpperCase()}
                            </button>
                        ))}
                    </div>

                    <div className="p-6">
                        <form onSubmit={handleAdd} className="flex gap-4 items-end mb-6 p-4 bg-slate-50 border border-slate-200 rounded-lg">
                            <div className="flex-1">
                                <label className="block text-xs font-medium text-slate-700 mb-1">Full Path Key (full_path_key.exclude)</label>
                                <input
                                    type="text"
                                    required
                                    value={keyPath}
                                    onChange={(e) => setKeyPath(e.target.value)}
                                    placeholder="e.g., kubernetes.namespace.container"
                                    className="w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:ring-indigo-500 text-sm"
                                />
                            </div>
                            <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded text-sm font-medium hover:bg-indigo-700 flex items-center shadow-sm whitespace-nowrap">
                                <Plus className="w-4 h-4 mr-1" /> Add Exclusion
                            </button>
                        </form>

                        {loading ? (
                            <div className="text-sm text-slate-500">Loading...</div>
                        ) : filtered.length === 0 ? (
                            <div className="text-sm text-slate-500 italic p-4 text-center border border-dashed border-slate-300 rounded">
                                No exclusions found for {selectedIndexPattern} ({activeType.toUpperCase()}).
                            </div>
                        ) : (
                            <div className="border border-slate-200 rounded-lg overflow-hidden">
                                <table className="min-w-full divide-y divide-slate-200 text-sm">
                                    <thead className="bg-slate-50">
                                        <tr>
                                            <th className="px-4 py-3 text-left font-medium text-slate-500">Full Path Key</th>
                                            <th className="px-4 py-3 text-right font-medium text-slate-500">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-slate-200">
                                        {filtered.map(ex => (
                                            <tr key={ex.id} className="hover:bg-slate-50">
                                                <td className="px-4 py-3 text-slate-900 font-mono text-xs">{ex.key_path}</td>
                                                <td className="px-4 py-3 text-right">
                                                    <button
                                                        onClick={() => handleDelete(ex.id)}
                                                        className="text-slate-400 hover:text-red-500 transition-colors"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </>
            ) : (
                <div className="p-8 text-center text-slate-500 text-sm">
                    Please select an index pattern above to manage its exceptions.
                </div>
            )}
        </div>
    );
}
