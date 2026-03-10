import { useState, useEffect } from 'react';
import { Database, Plus, Trash2, ShieldAlert, Lock } from 'lucide-react';
import { scanFieldsApi, type ScanFieldConfig } from '../../api/client';
import clsx from 'clsx';

export default function ScanFieldsList() {
    const [fields, setFields] = useState<ScanFieldConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [isAddMode, setIsAddMode] = useState(false);
    const [newIndexPattern, setNewIndexPattern] = useState('*');
    const [newFieldPath, setNewFieldPath] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchFields();
    }, []);

    const fetchFields = async () => {
        try {
            setLoading(true);
            const data = await scanFieldsApi.getAll();
            if (Array.isArray(data)) {
                setFields(data);
            } else {
                throw new Error('API returned non-array format');
            }
        } catch (error) {
            console.error('Failed to fetch scan fields', error);
            // Mock data fallback for frontend testing
            setFields([
                { id: 1, index_pattern: '*', field_path: 'NameOfMicroService', is_active: true, is_required: true, created_at: new Date().toISOString() },
                { id: 2, index_pattern: '*', field_path: 'kubernetes.container.name', is_active: true, is_required: true, created_at: new Date().toISOString() },
                { id: 3, index_pattern: 'bcs-tech-logs-*', field_path: 'system.env', is_active: true, is_required: false, created_at: new Date().toISOString() },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async () => {
        if (!newIndexPattern.trim() || !newFieldPath.trim()) {
            alert('Укажите Pattern Индекса и Путь к полю');
            return;
        }
        try {
            setSaving(true);
            await scanFieldsApi.create({ index_pattern: newIndexPattern, field_path: newFieldPath });
            setNewIndexPattern('*');
            setNewFieldPath('');
            setIsAddMode(false);
            fetchFields();
        } catch (error: any) {
            console.error('Failed to add scan field', error);
            alert('Ошибка при добавлении: ' + (error.response?.data?.detail || error.message));
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: number, is_required: boolean) => {
        if (is_required) {
            alert('Обязательные поля нельзя удалить.');
            return;
        }
        if (!confirm('Уверены, что хотите удалить дополнительное поле разграничения?')) return;
        try {
            await scanFieldsApi.delete(id);
            fetchFields();
        } catch (error: any) {
            console.error('Failed to delete scan field', error);
            alert('Ошибка: ' + (error.response?.data?.detail || error.message));
        }
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                <div>
                    <h3 className="font-semibold text-slate-800 flex items-center">
                        <Database className="w-4 h-4 mr-2 text-indigo-500" /> Дополнительные поля разграничения (Scan Fields)
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">Эти поля извлекаются из документа и прикрепляются к cache_key для изоляции находок из разных микросервисов.</p>
                </div>
                {!isAddMode && (
                    <button
                        onClick={() => setIsAddMode(true)}
                        className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 flex items-center transition"
                    >
                        <Plus className="w-4 h-4 mr-1.5" /> Добавить поле
                    </button>
                )}
            </div>

            <div className="p-0">
                {isAddMode && (
                    <div className="p-4 bg-indigo-50/50 border-b border-indigo-100 flex items-end space-x-4">
                        <div className="flex-1">
                            <label className="block text-xs font-medium text-slate-700 mb-1">Pattern Индекса</label>
                            <input
                                type="text"
                                value={newIndexPattern}
                                onChange={e => setNewIndexPattern(e.target.value)}
                                placeholder="*"
                                className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm focus:ring-indigo-500"
                            />
                        </div>
                        <div className="flex-1">
                            <label className="block text-xs font-medium text-slate-700 mb-1">Путь к полю в JSON (field_path)</label>
                            <input
                                type="text"
                                value={newFieldPath}
                                onChange={e => setNewFieldPath(e.target.value)}
                                placeholder="Например: kubernetes.labels.app"
                                className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm focus:ring-indigo-500"
                            />
                        </div>
                        <div className="flex items-center space-x-2 pb-0.5">
                            <button
                                onClick={() => setIsAddMode(false)}
                                className="px-3 py-1.5 border border-slate-300 bg-white text-slate-700 rounded text-sm font-medium hover:bg-slate-50 transition"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={handleAdd}
                                disabled={saving}
                                className="px-4 py-1.5 bg-indigo-600 border border-transparent text-white rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
                            >
                                Сохранить
                            </button>
                        </div>
                    </div>
                )}

                <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium text-xs uppercase tracking-wider">
                        <tr>
                            <th className="px-6 py-3">Pattern Индекса</th>
                            <th className="px-6 py-3">Путь к полю (field_path)</th>
                            <th className="px-6 py-3 text-right">Действия</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {loading ? (
                            <tr>
                                <td colSpan={3} className="px-6 py-8 text-center text-slate-400">Загрузка...</td>
                            </tr>
                        ) : fields.length === 0 ? (
                            <tr>
                                <td colSpan={3} className="px-6 py-8 text-center text-slate-400">Нет добавленных полей разграничения</td>
                            </tr>
                        ) : (
                            fields.map(field => (
                                <tr key={field.id} className="hover:bg-slate-50/50 group">
                                    <td className="px-6 py-3 font-mono text-xs text-slate-700">
                                        {field.index_pattern}
                                    </td>
                                    <td className="px-6 py-3 font-mono text-xs text-slate-700">
                                        <div className="flex items-center">
                                            {field.is_required && <span title="Обязательное системное поле"><Lock className="w-3.5 h-3.5 mr-2 text-rose-500 shrink-0" /></span>}
                                            <span className={clsx(field.is_required && "font-medium text-slate-800")}>
                                                {field.field_path}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-3 text-right">
                                        <button
                                            onClick={() => handleDelete(field.id, field.is_required)}
                                            disabled={field.is_required}
                                            className={clsx(
                                                "p-1.5 rounded transition-colors",
                                                field.is_required
                                                    ? "text-slate-300 cursor-not-allowed"
                                                    : "text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                                            )}
                                            title={field.is_required ? "Нельзя удалить системное поле" : "Удалить"}
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
            {fields.some(f => f.is_required) && (
                <div className="bg-rose-50/50 border-t border-rose-100 px-6 py-3 flex items-start text-xs text-rose-800">
                    <ShieldAlert className="w-4 h-4 mr-2 text-rose-500 shrink-0" />
                    <p>Поля с замком (Lock) являются обязательными для базовой работы системы и корректного отделения находок по микросервисам. Их удаление запрещено.</p>
                </div>
            )}
        </div>
    );
}
