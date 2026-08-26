import { useState, useEffect } from 'react';
import { Database, Search, CheckSquare, Clock, ChevronLeft, ChevronRight as ChevronRightIcon, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import { indicesApi } from '../api/client';

interface JiraTask {
    id: number;
    jira_issue_key: string;
    index_pattern: string;
    author_name: string;
    created_at: string;
    jira_url: string;
}

export default function Tasks() {
    const [taskSearch, setTaskSearch] = useState('');
    const [tasks, setTasks] = useState<JiraTask[]>([]);
    const [loading, setLoading] = useState(false);
    const [pagination, setPagination] = useState({ page: 1, limit: 20, total: 0 });

    const loadTasks = async () => {
        setLoading(true);
        try {
            const data = await indicesApi.getJiraHistory(pagination.limit, pagination.page);
            setTasks(data.items);
            setPagination(prev => ({ ...prev, total: data.total }));
        } catch (error) {
            console.error('Failed to load tasks:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadTasks();
    }, [pagination.page]);

    const filteredTasks = tasks.filter(t =>
        t.jira_issue_key.toLowerCase().includes(taskSearch.toLowerCase()) ||
        t.author_name.toLowerCase().includes(taskSearch.toLowerCase()) ||
        t.index_pattern.toLowerCase().includes(taskSearch.toLowerCase())
    );

    const totalPages = Math.ceil(pagination.total / pagination.limit);

    return (
        <div className="flex flex-col h-full bg-slate-50/20">
            <div className="px-8 pt-8 pb-6 flex justify-between items-start border-b border-slate-200 shrink-0 bg-white">
                <div>
                    <h2 className="text-2xl font-bold text-slate-800 flex items-center mb-2">
                        <Clock className="w-6 h-6 mr-3 text-indigo-500" />
                        История заведенных задач
                    </h2>
                    <p className="text-slate-500 text-sm">Список всех задач, созданных для исправления инцидентов ПДн.</p>
                </div>
            </div>

            <div className="flex-1 p-8 overflow-y-auto">
                {/* Строка поиска */}
                <div className="mb-6 max-w-md relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                        type="text"
                        className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-md leading-5 bg-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm shadow-sm"
                        placeholder="Поиск по номеру задачи, ФИО, индексу..."
                        value={taskSearch}
                        onChange={(e) => setTaskSearch(e.target.value)}
                    />
                </div>

                {/* Таблица */}
                <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
                            <tr>
                                <th className="px-6 py-3">Задача</th>
                                <th className="px-6 py-3">Индекс (Цель)</th>
                                <th className="px-6 py-3">Статус</th>
                                <th className="px-6 py-3">Автор (ФИО)</th>
                                <th className="px-6 py-3">Дата создания</th>
                                <th className="px-6 py-3">Ссылка</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                                        <Loader2 className="w-5 h-5 mx-auto animate-spin text-blue-500" />
                                        Загрузка...
                                    </td>
                                </tr>
                            ) : filteredTasks.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                                        Задач не найдено
                                    </td>
                                </tr>
                            ) : (
                                filteredTasks.map((task) => (
                                    <tr key={task.id} className="border-b border-slate-100 hover:bg-slate-50/50">
                                        <td className="px-6 py-4 font-medium text-blue-600 flex items-center">
                                            <CheckSquare className="w-4 h-4 mr-2" />
                                            {task.jira_issue_key}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center text-slate-600">
                                                <Database className="w-3.5 h-3.5 mr-1.5 text-amber-500" />
                                                <span className="font-mono text-xs">{task.index_pattern}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={clsx(
                                                "px-2 py-1 rounded text-[10px] font-bold tracking-wider",
                                                task.jira_issue_key.startsWith('EIB') || task.jira_issue_key.startsWith('SEC') ?
                                                    'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800'
                                            )}>
                                                {task.jira_issue_key.startsWith('EIB') ? 'DONE' : task.jira_issue_key.startsWith('SEC') ? 'IN PROGRESS' : 'OPEN'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-slate-700">{task.author_name}</td>
                                        <td className="px-6 py-4 text-slate-500 whitespace-nowrap">
                                            {new Date(task.created_at).toLocaleString('ru-RU', {
                                                year: 'numeric',
                                                month: '2-digit',
                                                day: '2-digit',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                        </td>
                                        <td className="px-6 py-4">
                                            <a href={task.jira_url} className="text-blue-500 hover:underline flex items-center" target="_blank" rel="noreferrer">
                                                JIRA <ChevronRightIcon className="w-3 h-3 ml-1" />
                                            </a>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                    <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex justify-between items-center text-xs text-slate-500">
                        <span>Показано элементов: {filteredTasks.length} из {pagination.total}</span>
                        <div className="flex space-x-2 items-center">
                            <button
                                onClick={() => setPagination(p => ({ ...p, page: p.page - 1 }))}
                                disabled={pagination.page === 1 || loading}
                                className="px-2 py-1 border border-slate-300 rounded bg-white hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                            >
                                <ChevronLeft className="w-3.5 h-3.5 mr-1" /> Пред
                            </button>
                            <span className="px-2">Страница {pagination.page} из {totalPages || 1}</span>
                            <button
                                onClick={() => setPagination(p => ({ ...p, page: p.page + 1 }))}
                                disabled={pagination.page >= totalPages || loading}
                                className="px-2 py-1 border border-slate-300 rounded bg-white hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                            >
                                След <ChevronRightIcon className="w-3.5 h-3.5 ml-1" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}