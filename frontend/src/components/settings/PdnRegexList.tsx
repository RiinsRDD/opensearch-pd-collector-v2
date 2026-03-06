import React, { useState, useEffect } from 'react';
import { Trash2, Plus, Code, Shield } from 'lucide-react';
import { pdnTypesApi, type PdnType } from '../../api/client';

export default function PdnRegexList() {
    const [types, setTypes] = useState<PdnType[]>([]);
    const [loading, setLoading] = useState(false);
    const [isAdding, setIsAdding] = useState(false);
    const [newPdnType, setNewPdnType] = useState('');
    const [newRegexValue, setNewRegexValue] = useState('');

    useEffect(() => {
        fetchTypes();
    }, []);

    const fetchTypes = async () => {
        try {
            setLoading(true);
            const data = await pdnTypesApi.getAll();
            if (Array.isArray(data)) {
                setTypes(data);
            } else {
                setTypes([]);
                console.error('API returned non-array:', data);
            }
        } catch (error) {
            console.error('Failed to load PDN types', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAddSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!newPdnType.trim() || !newRegexValue.trim()) {
            alert('Пожалуйста, заполните оба поля');
            return;
        }

        const confirmAdd = window.confirm(`Вы уверены, что хотите добавить новый тип ПДн: ${newPdnType.trim()}?\nЭто создаст системный флаг и активирует парсер.`);
        if (!confirmAdd) return;

        try {
            await pdnTypesApi.create({
                pdn_type: newPdnType.trim().toLowerCase(),
                regex_value: newRegexValue.trim()
            });
            setIsAdding(false);
            setNewPdnType('');
            setNewRegexValue('');
            fetchTypes();
            // Optional: force page reload or alert to notify user about reloading settings
            alert('Тип ПДн успешно добавлен! Перезагрузите страницу настроек чтобы увидеть его везде.');
        } catch (error: any) {
            alert('Ошибка при добавлении типа ПДн: ' + (error.response?.data?.detail || error.message));
        }
    };

    const handleDelete = async (id: number, pdnType: string) => {
        const confirmDelete = window.confirm(`Вы уверены, что хотите удалить тип ПДн "${pdnType}"?\n(Глобальные исключения для него будут сохранены)`);
        if (!confirmDelete) return;

        try {
            await pdnTypesApi.delete(id);
            fetchTypes();
        } catch (error: any) {
            alert('Ошибка при удалении типа ПДн: ' + (error.response?.data?.detail || error.message));
        }
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                <div>
                    <h3 className="font-semibold text-slate-800 flex items-center">
                        <Code className="w-5 h-5 mr-2 text-indigo-500" />
                        Регулярки ПДн (PDN Types)
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">
                        Основные регулярные выражения для поиска ПДн в логах. Системные типы удалить нельзя.
                    </p>
                </div>
                <button
                    onClick={() => setIsAdding(!isAdding)}
                    className="px-3 py-1.5 bg-indigo-50 text-indigo-600 rounded-md text-sm font-medium hover:bg-indigo-100 transition flex items-center"
                >
                    {isAdding ? 'Отмена' : <><Plus className="w-4 h-4 mr-1" /> Добавить тип</>}
                </button>
            </div>

            {isAdding && (
                <div className="p-6 bg-indigo-50/50 border-b border-indigo-100">
                    <form onSubmit={handleAddSubmit} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="md:col-span-1">
                                <label className="block text-sm font-medium text-slate-700 mb-1">Тип ПДн (название)</label>
                                <input
                                    type="text"
                                    value={newPdnType}
                                    onChange={e => setNewPdnType(e.target.value.replace(/[^a-zA-Z0-9_-]/g, ''))}
                                    placeholder="например: inn"
                                    className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-indigo-500 sm:text-sm"
                                    required
                                />
                                <p className="text-[11px] text-slate-500 mt-1">Только латиница, цифры, дефис и подчеркивание.</p>
                            </div>
                            <div className="md:col-span-2">
                                <label className="block text-sm font-medium text-slate-700 mb-1">Регулярное выражение (Regex)</label>
                                <input
                                    type="text"
                                    value={newRegexValue}
                                    onChange={e => setNewRegexValue(e.target.value)}
                                    placeholder="например: \b\d{10,12}\b"
                                    className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-indigo-500 font-mono text-sm"
                                    required
                                />
                            </div>
                        </div>
                        <div className="flex justify-end">
                            <button
                                type="submit"
                                className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 flex items-center"
                            >
                                <Plus className="w-4 h-4 mr-2" /> Добавить с подтверждением
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="p-0">
                {loading ? (
                    <div className="p-6 text-center text-slate-500">Загрузка...</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-slate-600">
                            <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-medium border-b border-slate-200">
                                <tr>
                                    <th className="px-6 py-3 whitespace-nowrap">Тип (pdn_type)</th>
                                    <th className="px-6 py-3">Регулярное Выражение</th>
                                    <th className="px-6 py-3 min-w-[120px]">Статус</th>
                                    <th className="px-6 py-3 text-right">Действия</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {types.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-8 text-center text-slate-500 italic">
                                            Нет добавленных типов ПДн
                                        </td>
                                    </tr>
                                ) : (
                                    types.map((type) => (
                                        <tr key={type.id} className="hover:bg-slate-50/50 transition-colors">
                                            <td className="px-6 py-4 font-mono font-medium text-slate-800">
                                                {type.pdn_type}
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="font-mono text-xs bg-slate-100 p-2 rounded text-slate-700 overflow-x-auto max-w-xl">
                                                    {type.value}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                {type.is_system ? (
                                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                                                        <Shield className="w-3 h-3 mr-1" /> Системный
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200">
                                                        Пользовательский
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                {!type.is_system && (
                                                    <button
                                                        onClick={() => handleDelete(type.id, type.pdn_type)}
                                                        className="text-slate-400 hover:text-red-500 transition-colors p-1"
                                                        title="Удалить тип"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
