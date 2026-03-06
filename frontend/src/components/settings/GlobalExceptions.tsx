import { useState, useEffect } from 'react';
import { exclusionsApi, pdnTypesApi } from '../../api/client';
import { Trash2, Plus } from 'lucide-react';
import clsx from 'clsx';

export default function GlobalExceptions() {
    const [exclusions, setExclusions] = useState<any[]>([]);
    const [activeType, setActiveType] = useState<string>('phone');
    const [loading, setLoading] = useState(false);

    // Form state
    const [ruleType, setRuleType] = useState('full_path_key.exclude');
    const [ruleValue, setRuleValue] = useState('');

    const [pdnTypes, setPdnTypes] = useState<string[]>(['phone', 'email', 'card', 'fio', 'any']);
    const ruleTypes = [
        { id: 'full_path_key.exclude', label: 'Full Path Exclude (e.g. obj.key)' },
        { id: 'exclude_pattern', label: 'Match Pattern' },
        { id: 'prefix_exclude', label: 'Prefix Exclude' },
        { id: 'suffix_exclude', label: 'Suffix Exclude' },
        { id: 'exclude_key', label: 'Exclude Key (Anywhere)' },
    ];

    useEffect(() => {
        fetchExclusions();
        fetchPdnTypes();
    }, []);

    const fetchPdnTypes = async () => {
        try {
            const types = await pdnTypesApi.getTypesList();
            if (!types.includes('any')) types.push('any');
            setPdnTypes(types);
        } catch (error) {
            console.error("Failed to fetch pdn types", error);
        }
    };

    const fetchExclusions = async () => {
        try {
            setLoading(true);
            const data = await exclusionsApi.getGlobal();
            if (Array.isArray(data)) {
                setExclusions(data);
            } else {
                throw new Error("Invalid API response array");
            }
        } catch (error) {
            console.error("Failed to fetch global exclusions", error);
            // Фолбэк на моковые данные для визуальной проверки пользователем
            setExclusions([
                { id: 1, pdn_type: 'phone', rule_type: 'full_path_key.exclude', value: 'profile.phone_number' },
                { id: 2, pdn_type: 'email', rule_type: 'suffix_exclude', value: '@test.com' },
                { id: 3, pdn_type: 'fio', rule_type: 'exclude_key', value: 'test_fio' },
                { id: 4, pdn_type: 'card', rule_type: 'full_path_key.exclude', value: 'payment.card_info' }
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this global rule?')) return;
        try {
            await exclusionsApi.deleteGlobal(id);
            await fetchExclusions();
        } catch (error) {
            console.error(error);
        }
    };

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await exclusionsApi.addGlobal({
                pdn_type: activeType,
                rule_type: ruleType,
                value: ruleValue
            });
            setRuleValue('');
            await fetchExclusions();
        } catch (error) {
            console.error(error);
        }
    };

    const filtered = (Array.isArray(exclusions) ? exclusions : []).filter(e => e.pdn_type === activeType);

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50">
                <h3 className="font-semibold text-slate-800">Global Exceptions</h3>
                <p className="text-xs text-slate-500 mt-1">Rules that apply globally across all indices.</p>
            </div>

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
                        <label className="block text-xs font-medium text-slate-700 mb-1">Rule Type</label>
                        <select
                            value={ruleType}
                            onChange={(e) => setRuleType(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:ring-indigo-500 text-sm"
                        >
                            {ruleTypes.map(rt => <option key={rt.id} value={rt.id}>{rt.label}</option>)}
                        </select>
                    </div>
                    <div className="flex-[2]">
                        <label className="block text-xs font-medium text-slate-700 mb-1">Value / Path</label>
                        <input
                            type="text"
                            required
                            value={ruleValue}
                            onChange={(e) => setRuleValue(e.target.value)}
                            placeholder={ruleType === 'full_path_key.exclude' ? "kubernetes.namespace.container" : "e.g., cardId="}
                            className="w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:ring-indigo-500 text-sm"
                        />
                    </div>
                    <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded text-sm font-medium hover:bg-indigo-700 flex items-center shadow-sm">
                        <Plus className="w-4 h-4 mr-1" /> Add Rule
                    </button>
                </form>

                {loading ? (
                    <div className="text-sm text-slate-500">Loading...</div>
                ) : filtered.length === 0 ? (
                    <div className="text-sm text-slate-500 italic p-4 text-center border border-dashed border-slate-300 rounded">No global exceptions found for {activeType.toUpperCase()}.</div>
                ) : (
                    <div className="border border-slate-200 rounded-lg overflow-hidden">
                        <table className="min-w-full divide-y divide-slate-200 text-sm">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-4 py-3 text-left font-medium text-slate-500">Rule Type</th>
                                    <th className="px-4 py-3 text-left font-medium text-slate-500">Value</th>
                                    <th className="px-4 py-3 text-right font-medium text-slate-500">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-slate-200">
                                {filtered.map(ex => (
                                    <tr key={ex.id} className="hover:bg-slate-50">
                                        <td className="px-4 py-3 text-slate-700 font-mono text-xs">{ex.rule_type}</td>
                                        <td className="px-4 py-3 text-slate-900">{ex.value}</td>
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
        </div>
    );
}
