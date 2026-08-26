import { useState, useRef, useEffect } from 'react';
import IndicesTree from '../components/tree/IndicesTree';
import { JsonView, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';
import { FileText, Database, ShieldAlert, Clock, Tag, CheckSquare, Search, ChevronRight, Key, AlertTriangle, RefreshCw, Trash2, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import { useSelection } from '../context/SelectionContext';
import SingleScanModal from '../components/modals/SingleScanModal';
import { indicesApi, scannerApi } from '../api/client';
import type { PDNPattern, ScannerStatus as ScannerStatusType } from '../types/api';

export default function Dashboard() {
    const { selectedPatterns, setSelectedPatterns, selectedIndexPattern, setSelectedIndexPattern } = useSelection();
    const [activeTab, setActiveTab] = useState<'pattern' | 'examples' | 'raw'>('pattern');
    const [taskSearch, setTaskSearch] = useState('');
    const [isSingleScanModalOpen, setIsSingleScanModalOpen] = useState(false);
    const [sidebarWidth, setSidebarWidth] = useState(350);
    const [treeReloadKey, setTreeReloadKey] = useState(0);
    const [scannerStatus, setScannerStatus] = useState<ScannerStatusType>({ status: 'idle', current_index_pattern: null, eta: null });
    const isResizing = useRef(false);

    useEffect(() => {
        const fetchScannerStatus = async () => {
            try {
                const data = await scannerApi.getStatus();
                setScannerStatus(data);
            } catch (e) {
                console.error('Failed to fetch scanner status:', e);
            }
        };
        fetchScannerStatus();
        const interval = setInterval(fetchScannerStatus, 10000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isResizing.current) return;
            let newWidth = e.clientX;
            if (newWidth < 250) newWidth = 250;
            if (newWidth > 800) newWidth = 800;
            setSidebarWidth(newWidth);
        };

        const handleMouseUp = () => {
            if (isResizing.current) {
                isResizing.current = false;
                document.body.style.cursor = 'default';
                document.body.style.userSelect = 'auto';
            }
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, []);

    const startResizing = () => {
        isResizing.current = true;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    };

    const primaryPattern = selectedPatterns.length > 0 ? selectedPatterns[0] : null;

    const handleStatusChange = async (newStatus: string) => {
        if (!primaryPattern) return;
        try {
            await indicesApi.updatePattern(primaryPattern.cache_key, { status: newStatus });
            const updated = selectedPatterns.map((p: PDNPattern) => p.cache_key === primaryPattern.cache_key ? { ...p, status: newStatus as PDNPattern['status'] } : p);
            setSelectedPatterns(updated);
        } catch (error) {
            console.error('Failed to update status:', error);
            alert('Ошибка при изменении статуса');
        }
    };

    const handleUpdateExamples = async () => {
        if (!primaryPattern) return;
        try {
            await indicesApi.updateExamples(primaryPattern.cache_key);
            setTreeReloadKey((k: number) => k + 1);
        } catch (error) {
            console.error('Failed to update examples:', error);
            alert('Ошибка при обновлении примеров');
        }
    };

    const handleDeletePattern = async () => {
        if (!primaryPattern) return;
        if (!confirm('Удалить паттерн и все примеры?')) return;
        try {
            await indicesApi.deletePattern(primaryPattern.cache_key);
            setSelectedPatterns([]);
            setTreeReloadKey((k: number) => k + 1);
        } catch (error) {
            console.error('Failed to delete pattern:', error);
            alert('Ошибка при удалении паттерна');
        }
    };

    const handleFalsePositive = async () => {
        if (!primaryPattern) return;
        try {
            await indicesApi.updatePattern(primaryPattern.cache_key, { status: 'false_positive' });
            const updated = selectedPatterns.map((p: PDNPattern) => p.cache_key === primaryPattern.cache_key ? { ...p, status: 'false_positive' as PDNPattern['status'] } : p);
            setSelectedPatterns(updated);
        } catch (error) {
            console.error('Failed to mark as false positive:', error);
            alert('Ошибка при отметке как False Positive');
        }
    };

    const handleCustomMessageBlur = async (message: string) => {
        if (!primaryPattern) return;
        try {
            await indicesApi.updatePattern(primaryPattern.cache_key, { custom_message: message });
        } catch (error) {
            console.error('Failed to save custom message:', error);
            alert('Ошибка при сохранении комментария');
        }
    };

    const rawDocument = primaryPattern?.full_document ?? null;

    return (
        <div className="flex h-full w-full bg-white overflow-hidden">

            {/* Левая панель: Explorer Tree */}
            <div
                style={{ width: sidebarWidth }}
                className="shrink-0 h-full border-r border-slate-200 bg-slate-50/30 relative flex group/sidebar"
            >
<div className="flex-1 w-full h-full overflow-hidden">
                        <IndicesTree
                            key={treeReloadKey}
                            selectedCacheKeys={selectedPatterns.map(p => p.cache_key)}
                            selectedIndexPattern={selectedIndexPattern}
                            scanningIndexPattern={scannerStatus.current_index_pattern}
                            onSelectPatterns={(patterns, idxPattern) => {
                                setSelectedPatterns(patterns);
                                if (idxPattern !== undefined) {
                                    setSelectedIndexPattern(idxPattern);
                                }
                            }}
                        />
                    </div>
                {/* Resizer Handle */}
                <div
                    className="w-[3px] cursor-col-resize hover:bg-blue-400 active:bg-blue-500 transition-colors h-full absolute right-0 top-0 z-10"
                    onMouseDown={startResizing}
                />
            </div>

            {/* Правая панель: Рабочая область (Details) */}
            <div className="flex-1 h-full min-w-0 flex flex-col bg-white">
                {primaryPattern ? (
                    <>
                        {/* Заголовок рабочей области для паттерна */}
                        <div className="px-6 py-4 border-b border-slate-200 bg-white shrink-0 flex flex-col">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-xl font-semibold text-slate-800 flex items-center">
                                        <span className="text-blue-600 mr-2">{primaryPattern.pdn_type}</span>
                                        <span className="text-slate-400 font-normal mx-2">/</span>
                                        {primaryPattern.field_path}
                                    </h2>
                                    <div className="text-sm text-slate-500 font-mono mt-1 flex items-center">
                                        Cache Key: {primaryPattern.cache_key}
                                        {primaryPattern.has_jira_task && (
                                            <span className="ml-3 flex items-center text-blue-600">
                                                <CheckSquare className="w-3.5 h-3.5 mr-1" />
                                                Есть Jira задача
                                            </span>
                                        )}
                                    </div>
                                </div>
                                {selectedPatterns.length > 1 && (
                                    <div className="text-sm font-medium bg-blue-50 text-blue-700 px-3 py-1.5 rounded-md border border-blue-200">
                                        Выбрано элементов: {selectedPatterns.length}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Вкладки */}
                        <div className="px-6 border-b border-slate-200 shrink-0 bg-slate-50/50">
                            <nav className="flex space-x-6">
                                <button
                                    onClick={() => setActiveTab('pattern')}
                                    className={clsx(
                                        "py-3 text-sm font-medium border-b-2 transition-colors",
                                        activeTab === 'pattern' ? "border-blue-500 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"
                                    )}
                                >
                                    Паттерн
                                </button>
                                <button
                                    onClick={() => setActiveTab('examples')}
                                    className={clsx(
                                        "py-3 text-sm font-medium border-b-2 transition-colors",
                                        activeTab === 'examples' ? "border-blue-500 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"
                                    )}
                                >
                                    Примеры (3)
                                </button>
                                <button
                                    onClick={() => setActiveTab('raw')}
                                    className={clsx(
                                        "py-3 text-sm font-medium border-b-2 transition-colors flex items-center",
                                        activeTab === 'raw' ? "border-blue-500 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"
                                    )}
                                >
                                    <FileText className="w-4 h-4 mr-1.5" /> Сырой документ
                                </button>
                            </nav>
                        </div>

                        {/* Область контента вкладок */}
                        <div className="flex-1 overflow-y-auto p-6 bg-slate-50/30">

                            {/* Вкладка: ПАТТЕРН */}
                            {activeTab === 'pattern' && (
                                <div className="max-w-4xl space-y-6">
                                    {/* Карточка деталей */}
                                    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                                        <h3 className="text-sm font-semibold text-slate-800 mb-4 flex items-center">
                                            <Database className="w-4 h-4 mr-2 text-slate-400" /> Детали кэша
                                        </h3>
                                        <div className="grid grid-cols-2 gap-y-4 gap-x-8">
<div>
                                                    <div className="text-xs text-slate-500 mb-1">Status</div>
                                                    <span className={clsx(
                                                        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                                                        primaryPattern.status === 'new' && "bg-red-100 text-red-800",
                                                        primaryPattern.status === 'confirmed' && "bg-blue-100 text-blue-800",
                                                        primaryPattern.status === 'false_positive' && "bg-green-100 text-green-800",
                                                        primaryPattern.status === 'unverified' && "bg-slate-200 text-slate-800"
                                                    )}>
                                                        <select
                                                            className="bg-transparent border-none focus:ring-0 outline-none cursor-pointer"
                                                            value={primaryPattern.status}
                                                            onChange={(e) => handleStatusChange(e.target.value)}
                                                        >
                                                            <option value="new">New</option>
                                                            <option value="confirmed">Confirmed</option>
                                                            <option value="false_positive">False Positive</option>
                                                            <option value="unverified">Unverified</option>
                                                        </select>
                                                    </span>
                                                </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Hit Count (сколько раз найдено)</div>
                                                <div className="text-sm font-semibold text-slate-900">{primaryPattern.hit_count}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1 flex items-center"><Clock className="w-3 h-3 mr-1" /> First Seen</div>
                                                <div className="text-sm text-slate-700">2023-10-25 14:30:00</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1 flex items-center"><Clock className="w-3 h-3 mr-1" /> Last Seen</div>
                                                <div className="text-sm text-slate-700">2023-10-26 09:15:00</div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Карточка Контекста обнаружения */}
                                    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                                        <h3 className="text-sm font-semibold text-slate-800 mb-4 flex items-center">
                                            <Search className="w-4 h-4 mr-2 text-slate-400" /> Контекст обнаружения
                                        </h3>
                                        <div className="grid grid-cols-2 gap-y-4 gap-x-8">
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Context Type</div>
                                                <div className="flex items-center">
                                                    {primaryPattern.context_type === 'base' && <><FileText className="w-4 h-4 text-slate-500 mr-1.5" /><span className="text-sm font-medium text-slate-700 bg-slate-100 px-2 py-0.5 rounded">Native Document Field</span></>}
                                                    {primaryPattern.context_type === 'structured_key' && <><Key className="w-4 h-4 text-emerald-500 mr-1.5" /><span className="text-sm font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">Structured Key</span></>}
                                                    {primaryPattern.context_type === 'free_text' && <><FileText className="w-4 h-4 text-blue-500 mr-1.5" /><span className="text-sm font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded">Free Text</span></>}
                                                    {primaryPattern.context_type === 'ambiguous' && <><AlertTriangle className="w-4 h-4 text-amber-500 mr-1.5" /><span className="text-sm font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded">Ambiguous</span></>}
                                                    {!primaryPattern.context_type && <span className="text-sm text-slate-500">-</span>}
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Key Hint</div>
                                                <div className="text-sm font-mono text-slate-800 bg-slate-100 px-2 py-0.5 rounded inline-block">
                                                    {primaryPattern.key_hint || <span className="text-slate-400 italic">None</span>}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Дополнительные поля */}
                                        {primaryPattern.extra_fields && Object.keys(primaryPattern.extra_fields).length > 0 && (
                                            <div className="mt-4 pt-4 border-t border-slate-100">
                                                <div className="text-xs text-slate-500 mb-2">Дополнительные поля разграничения:</div>
                                                <div className="flex flex-wrap gap-2">
                                                    {Object.entries(primaryPattern.extra_fields).map(([key, value]) => (
                                                        <div key={key} className="flex items-center text-xs border border-slate-200 rounded overflow-hidden">
                                                            <span className="bg-slate-50 text-slate-500 px-2 py-1 border-r border-slate-200">{key}</span>
                                                            <span className="bg-white text-slate-700 font-medium px-2 py-1">{value as React.ReactNode}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Карточка тегов */}
                                    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                                        <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center">
                                            <Tag className="w-4 h-4 mr-2 text-slate-400" /> Теги и Разметка
                                        </h3>
                                        <div className="flex flex-wrap gap-2">
                                            {primaryPattern.tags.length > 0 ? primaryPattern.tags.map(tag => (
                                                <span key={tag.id} className={clsx(
                                                    "px-2.5 py-1 rounded-md text-sm border",
                                                    tag.name === 'G' ? "bg-amber-100 text-amber-800 border-amber-200" :
                                                        tag.name === 'S' ? "bg-purple-100 text-purple-800 border-purple-200" :
                                                            tag.name === 'U' ? "bg-emerald-100 text-emerald-800 border-emerald-200" :
                                                                "bg-slate-100 text-slate-700 border-slate-200"
                                                )}>
                                                    #{tag.name}
                                                </span>
                                            )) : (
                                                <span className="text-sm text-slate-400 italic">Нет тегов</span>
                                            )}
                                            <button className="px-2.5 py-1 rounded-md text-slate-500 text-sm border border-dashed border-slate-300 hover:text-blue-600 hover:border-blue-400 transition-colors">
                                                + Добавить тег
                                            </button>
                                        </div>
                                    </div>

                                    {/* Быстрые действия */}
                                    <div className="flex space-x-3">
                                        <button
                                            className="px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium rounded-md shadow-sm transition-colors flex items-center"
                                            onClick={handleUpdateExamples}
                                        >
                                            <RefreshCw className="w-4 h-4 mr-2" />
                                            Обновить примеры
                                        </button>
                                        <button
                                            className="px-4 py-2 bg-white border border-slate-300 hover:bg-red-50 hover:text-red-700 text-slate-700 text-sm font-medium rounded-md shadow-sm transition-colors flex items-center"
                                            onClick={handleDeletePattern}
                                        >
                                            <Trash2 className="w-4 h-4 mr-2" />
                                            Удалить из БД
                                        </button>
                                        <button
                                            className="px-4 py-2 bg-green-50 border border-green-200 hover:bg-green-100 text-green-700 text-sm font-medium rounded-md shadow-sm transition-colors flex items-center"
                                            onClick={handleFalsePositive}
                                        >
                                            <AlertCircle className="w-4 h-4 mr-2" />
                                            Отметить как False Positive
                                        </button>
                                    </div>

                                    {/* Кастомное сообщение для Jira */}
                                    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm mt-6">
                                        <h3 className="text-sm font-semibold text-slate-800 mb-2">Комментарий к задаче (Custom Message)</h3>
                                        <p className="text-xs text-slate-500 mb-3">Этот текст будет добавлен в описание задачи в Jira при её создании.</p>
                                        <textarea
                                            className="w-full text-sm border border-slate-300 rounded-md p-3 focus:ring-blue-500 focus:border-blue-500"
                                            rows={4}
                                            placeholder="Напишите здесь дополнительные комментарии, замечания или инструкции по исправлению ПДн..."
                                            defaultValue={primaryPattern.custom_message || ''}
                                            onBlur={(e) => handleCustomMessageBlur(e.target.value)}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Вкладка: ПРИМЕРЫ */}
                            {activeTab === 'examples' && (
                                <div className="space-y-4">
                                    {primaryPattern.examples && primaryPattern.examples.length > 0 ? (
                                        primaryPattern.examples.map((example: string, idx: number) => (
                                            <div key={idx} className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
                                                <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
                                                    <span className="text-xs font-mono text-slate-500">Пример #{idx + 1}</span>
                                                </div>
                                                <div className="p-4 flex items-center text-sm">
                                                    <span className="font-mono bg-yellow-100 text-yellow-900 px-1 py-0.5 rounded">{example}</span>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-8 text-center text-slate-500">
                                            Нет примеров для этого паттерна
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Вкладка: СЫРОЙ ДОКУМЕНТ */}
                            {activeTab === 'raw' && (
                                rawDocument ? (
                                    <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
                                        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center text-sm text-slate-600">
                                            <ShieldAlert className="w-4 h-4 mr-2 text-amber-500" />
                                            Первый закэшированный сырой документ (PDNFinding.full_document, самый свежий по found_at).
                                        </div>
                                        <div className="p-4 overflow-x-auto text-[13px]">
                                            <JsonView data={rawDocument} shouldExpandNode={() => true} style={defaultStyles} />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-8 text-center text-slate-500">
                                        Нет сырого документа для этого паттерна
                                    </div>
                                )
                            )}

                        </div>
                    </>
                ) : selectedIndexPattern ? (
                    <div className="flex-1 flex flex-col bg-slate-50/20">
                        {/* Заголовок и Вкладки */}
                        <div className="px-8 pt-8 pb-0 flex justify-between items-start border-b border-slate-200 shrink-0">
                            <div>
                                <h2 className="text-2xl font-bold text-slate-800 flex items-center mb-1">
                                    <Database className="w-6 h-6 mr-3 text-amber-500" />
                                    {selectedIndexPattern}
                                </h2>
                                <p className="text-slate-500 text-sm ml-9 mb-4">Список задач, заведенных конкретно по этому индексу</p>
                            </div>
                            <button
                                onClick={() => setIsSingleScanModalOpen(true)}
                                className="flex items-center px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium rounded-md shadow-sm transition-colors mt-1"
                            >
                                <Search className="w-4 h-4 mr-2 text-indigo-500" />
                                Одиночное сканирование (Single Scan)
                            </button>
                        </div>

                        {/* Контент вкладок (Задачи или История) */}
                        <div className="flex-1 p-8 overflow-y-auto">
                            {/* Строка поиска */}
                            <div className="mb-6 max-w-md relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Search className="h-4 w-4 text-slate-400" />
                                </div>
                                <input
                                    type="text"
                                    className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-md leading-5 bg-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm shadow-sm"
                                    placeholder="Поиск по задачам, ФИО..."
                                    value={taskSearch}
                                    onChange={(e) => setTaskSearch(e.target.value)}
                                />
                            </div>

                            {/* Таблица */}
                            <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden min-h-[300px]">
                                <table className="w-full text-left text-sm">
                                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
                                        <tr>
                                            <th className="px-6 py-3">Задача</th>
                                            <th className="px-6 py-3">Статус</th>
                                            <th className="px-6 py-3">Автор (ФИО)</th>
                                            <th className="px-6 py-3">Дата создания</th>
                                            <th className="px-6 py-3">Ссылка</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {/* Mock Data, отсортированная по алфавиту */}
                                        {[
                                            { id: 'EIB-12003', status: 'IN PROGRESS', author: 'Иванов Иван Иванович', date: '2023-11-20 14:00', url: 'https://jira.example.com/browse/EIB-12003' },
                                            { id: 'SEC-1004', status: 'DONE', author: 'Петров Петр Петрович', date: '2023-11-21 09:15', url: 'https://jira.example.com/browse/SEC-1004' },
                                            { id: 'SEC-108', status: 'OPEN', author: 'Сидоров Сидор', date: '2023-11-22 17:30', url: 'https://jira.example.com/browse/SEC-108' }
                                        ]
                                            .filter(t => t.id.toLowerCase().includes(taskSearch.toLowerCase()) || t.author.toLowerCase().includes(taskSearch.toLowerCase()))
                                            .sort((a, b) => a.id.localeCompare(b.id))
                                            .map((task) => (
                                                <tr key={task.id} className="border-b border-slate-100 hover:bg-slate-50/50">
                                                    <td className="px-6 py-4 font-medium text-blue-600 flex items-center">
                                                        <CheckSquare className="w-4 h-4 mr-2" />
                                                        {task.id}
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
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-4">
                        <Database className="w-16 h-16 text-slate-200" />
                        <p className="text-lg">Выберите элемент в дереве слева для просмотра деталей</p>
                    </div>
                )}
            </div>

            {isSingleScanModalOpen && selectedIndexPattern && (
                <SingleScanModal
                    indexName={selectedIndexPattern}
                    onClose={() => setIsSingleScanModalOpen(false)}
                />
            )}
        </div>
    );
}
