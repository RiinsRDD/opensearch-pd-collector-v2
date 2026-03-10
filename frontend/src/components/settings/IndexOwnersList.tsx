import React, { useState, useEffect } from 'react';
import { Trash2, Plus, Edit2, Save, X } from 'lucide-react';
import { indexOwnersApi, type IndexOwnerData } from '../../api/client';

export const IndexOwnersList: React.FC = () => {
    const [owners, setOwners] = useState<IndexOwnerData[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [isAdding, setIsAdding] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [formData, setFormData] = useState<Omit<IndexOwnerData, 'id'>>({
        index_pattern: '',
        cmdb_url: '',
        tech_debt_id: '',
        fio: ''
    });

    const [mockMode, setMockMode] = useState(false);

    useEffect(() => {
        fetchOwners();
    }, []);

    const fetchOwners = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await indexOwnersApi.getAll();
            setOwners(data);
            setMockMode(false);
        } catch (err: any) {
            console.error('Failed to fetch owners:', err);
            setError('Не удалось загрузить владельцев индексов. Используются mock-данные.');
            setMockMode(true);
            setOwners([
                { id: 1, index_pattern: 'bcs-dubai-tech', cmdb_url: 'https://sd-jira.bcs.ru/secure/insight/assets/CMDB-2803910', tech_debt_id: '51495', fio: 'GasanovOI' },
                { id: 2, index_pattern: 'bcs-copilot-tech', cmdb_url: 'https://sd-jira.bcs.ru/secure/insight/assets/CMDB-2617286', tech_debt_id: '51493', fio: 'KlimenkoKA' }
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!formData.index_pattern) return;

        try {
            if (editingId) {
                if (mockMode) {
                    setOwners(owners.map(o => o.id === editingId ? { ...formData, id: editingId } : o));
                } else {
                    const updated = await indexOwnersApi.update(editingId, formData);
                    setOwners(owners.map(o => o.id === editingId ? updated : o));
                }
            } else {
                if (mockMode) {
                    setOwners([...owners, { ...formData, id: Date.now() }]);
                } else {
                    const created = await indexOwnersApi.create(formData);
                    setOwners([...owners, created]);
                }
            }
            setIsAdding(false);
            setEditingId(null);
            setFormData({ index_pattern: '', cmdb_url: '', tech_debt_id: '', fio: '' });
        } catch (err: any) {
            console.error('Save failed', err);
            alert(err.response?.data?.detail || 'Ошибка сохранения');
        }
    };

    const handleEdit = (owner: IndexOwnerData) => {
        setFormData({
            index_pattern: owner.index_pattern,
            cmdb_url: owner.cmdb_url || '',
            tech_debt_id: owner.tech_debt_id || '',
            fio: owner.fio || ''
        });
        setEditingId(owner.id);
        setIsAdding(true);
    };

    const handleDelete = async (id: number) => {
        if (!window.confirm('Вы уверены, что хотите удалить эту запись?')) return;

        try {
            if (mockMode) {
                setOwners(owners.filter(o => o.id !== id));
            } else {
                await indexOwnersApi.delete(id);
                setOwners(owners.filter(o => o.id !== id));
            }
        } catch (err) {
            console.error('Delete failed', err);
            alert('Ошибка удаления');
        }
    };

    const cancelEdit = () => {
        setIsAdding(false);
        setEditingId(null);
        setFormData({ index_pattern: '', cmdb_url: '', tech_debt_id: '', fio: '' });
    };

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-slate-200">Маппинг владельцев индексов (Index Owners)</h3>
                {!isAdding && (
                    <button
                        onClick={() => setIsAdding(true)}
                        className="flex items-center px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-md transition-colors"
                    >
                        <Plus className="w-4 h-4 mr-1.5" />
                        Добавить маппинг
                    </button>
                )}
            </div>

            {error && (
                <div className="p-3 mb-4 text-sm text-amber-200 bg-amber-900/30 border border-amber-700/50 rounded-md">
                    {error}
                </div>
            )}

            {isAdding && (
                <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 mb-6 shadow-md">
                    <h4 className="text-md font-medium text-slate-200 mb-3">
                        {editingId ? 'Редактировать связку' : 'Новая связка'}
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Index Pattern</label>
                            <input
                                type="text"
                                value={formData.index_pattern}
                                onChange={(e) => setFormData({ ...formData, index_pattern: e.target.value })}
                                className="w-full bg-slate-900/50 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                                placeholder="Например: bcs-dubai-tech или bcs-tech-logs-*"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">ФИО (Assignee)</label>
                            <input
                                type="text"
                                value={formData.fio || ''}
                                onChange={(e) => setFormData({ ...formData, fio: e.target.value })}
                                className="w-full bg-slate-900/50 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                                placeholder="Например: GasanovOI"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Тех. Долг ID (Child ID)</label>
                            <input
                                type="text"
                                value={formData.tech_debt_id || ''}
                                onChange={(e) => setFormData({ ...formData, tech_debt_id: e.target.value })}
                                className="w-full bg-slate-900/50 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                                placeholder="Например: 51493"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">CMDB URL (Для справки)</label>
                            <input
                                type="text"
                                value={formData.cmdb_url || ''}
                                onChange={(e) => setFormData({ ...formData, cmdb_url: e.target.value })}
                                className="w-full bg-slate-900/50 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                                placeholder="https://jira.../CMDB-2793524"
                            />
                        </div>
                    </div>
                    <div className="flex justify-end space-x-3 mt-4">
                        <button
                            onClick={cancelEdit}
                            className="flex items-center px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-md transition-colors"
                        >
                            <X className="w-4 h-4 mr-1.5" />
                            Отмена
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={!formData.index_pattern}
                            className={`flex items-center px-3 py-1.5 text-sm rounded-md transition-colors ${!formData.index_pattern ? 'bg-blue-900/50 text-slate-500 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 text-white'}`}
                        >
                            <Save className="w-4 h-4 mr-1.5" />
                            Сохранить
                        </button>
                    </div>
                </div>
            )}

            {loading && !owners.length ? (
                <div className="flex justify-center p-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
                </div>
            ) : owners.length === 0 ? (
                <div className="text-center p-8 text-slate-400 bg-slate-800/30 rounded-lg border border-slate-700/50">
                    Нет настроенных владельцев индексов
                </div>
            ) : (
                <div className="overflow-x-auto shadow-sm ring-1 ring-slate-700 rounded-lg">
                    <table className="min-w-full divide-y divide-slate-700">
                        <thead className="bg-slate-800">
                            <tr>
                                <th scope="col" className="py-3 px-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    Index Pattern
                                </th>
                                <th scope="col" className="py-3 px-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    ФИО (Assignee)
                                </th>
                                <th scope="col" className="py-3 px-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    Тех. Долг ID
                                </th>
                                <th scope="col" className="py-3 px-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    CMDB URL
                                </th>
                                <th scope="col" className="py-3 px-4 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    Действия
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-slate-900/50 divide-y divide-slate-800">
                            {owners.map((owner) => (
                                <tr key={owner.id} className="hover:bg-slate-800/50 transition-colors">
                                    <td className="py-3 px-4 text-sm text-slate-300 font-mono">
                                        {owner.index_pattern}
                                    </td>
                                    <td className="py-3 px-4 text-sm text-slate-300">
                                        {owner.fio || <span className="text-slate-500 italic">не указано</span>}
                                    </td>
                                    <td className="py-3 px-4 text-sm text-slate-300">
                                        {owner.tech_debt_id || <span className="text-slate-500 italic">-</span>}
                                    </td>
                                    <td className="py-3 px-4 text-sm text-blue-400">
                                        {owner.cmdb_url ? (
                                            <a href={owner.cmdb_url} target="_blank" rel="noopener noreferrer" className="hover:underline max-w-xs truncate block">
                                                {owner.cmdb_url.split('/').pop() || 'Ссылка'}
                                            </a>
                                        ) : (
                                            <span className="text-slate-500 italic">-</span>
                                        )}
                                    </td>
                                    <td className="py-3 px-4 text-right text-sm font-medium">
                                        <div className="flex items-center justify-end space-x-2">
                                            <button
                                                onClick={() => handleEdit(owner)}
                                                className="text-slate-400 hover:text-blue-400 p-1 rounded-md transition-colors"
                                                title="Редактировать"
                                            >
                                                <Edit2 className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(owner.id)}
                                                className="text-slate-400 hover:text-red-400 p-1 rounded-md transition-colors"
                                                title="Удалить"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};
