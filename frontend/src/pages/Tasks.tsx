import { useState } from 'react';
import { Database, Search, ChevronRight, CheckSquare, Clock } from 'lucide-react';
import clsx from 'clsx';

export default function Tasks() {
    const [taskSearch, setTaskSearch] = useState('');

    // Mock Data для глобальной истории задач
    const mockTasks = [
        { id: 'EIB-12003', index: 'bcs-tech-logs-*', status: 'IN PROGRESS', author: 'Иванов Иван Иванович', date: '2023-11-20 14:00', url: 'https://jira.example.com/browse/EIB-12003' },
        { id: 'SEC-1004', index: 'syslog-*', status: 'DONE', author: 'Петров Петр Петрович', date: '2023-11-21 09:15', url: 'https://jira.example.com/browse/SEC-1004' },
        { id: 'SEC-108', index: 'client-activity-api-*', status: 'OPEN', author: 'Сидоров Сидор', date: '2023-11-22 17:30', url: 'https://jira.example.com/browse/SEC-108' },
        { id: 'SEC-109', index: 'bcs-frontend-logs-*', status: 'DONE', author: 'Смирнов Алексей', date: '2023-11-23 11:10', url: 'https://jira.example.com/browse/SEC-109' }
    ];

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
                        placeholder="Поиск по номеру задачи, ФИО..."
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
                            {mockTasks
                                .filter(t => t.id.toLowerCase().includes(taskSearch.toLowerCase()) || t.author.toLowerCase().includes(taskSearch.toLowerCase()))
                                .sort((a, b) => a.id.localeCompare(b.id))
                                .map((task) => (
                                    <tr key={task.id} className="border-b border-slate-100 hover:bg-slate-50/50">
                                        <td className="px-6 py-4 font-medium text-blue-600 flex items-center">
                                            <CheckSquare className="w-4 h-4 mr-2" />
                                            {task.id}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center text-slate-600">
                                                <Database className="w-3.5 h-3.5 mr-1.5 text-amber-500" />
                                                <span className="font-mono text-xs">{task.index}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={clsx(
                                                "px-2 py-1 rounded text-[10px] font-bold tracking-wider",
                                                task.status === 'DONE' ? "bg-emerald-100 text-emerald-800" :
                                                    task.status === 'IN PROGRESS' ? "bg-blue-100 text-blue-800" :
                                                        "bg-amber-100 text-amber-800"
                                            )}>{task.status}</span>
                                        </td>
                                        <td className="px-6 py-4 text-slate-700">{task.author}</td>
                                        <td className="px-6 py-4 text-slate-500 whitespace-nowrap">{task.date}</td>
                                        <td className="px-6 py-4">
                                            <a href={task.url} className="text-blue-500 hover:underline flex items-center" target="_blank" rel="noreferrer">
                                                JIRA <ChevronRight className="w-3 h-3 ml-1" />
                                            </a>
                                        </td>
                                    </tr>
                                ))}
                        </tbody>
                    </table>
                    <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex justify-between items-center text-xs text-slate-500">
                        <span>Показано элементов: {mockTasks.length}</span>
                        <div className="flex space-x-2">
                            <button className="px-2 py-1 border border-slate-300 rounded bg-white hover:bg-slate-100 disabled:opacity-50" disabled>Пред</button>
                            <button className="px-2 py-1 border border-slate-300 rounded bg-white hover:bg-slate-100">След</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
