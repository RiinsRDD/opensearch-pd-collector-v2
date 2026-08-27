import { useState, useEffect, useMemo, useCallback } from 'react';
import { ChevronRight, ChevronDown, Folder, Hash, Key, FileText, AlertTriangle, File, Filter, Activity, RefreshCw, AlertCircle, Database } from 'lucide-react';
import clsx from 'clsx';
import { indicesApi } from '../../api/client';
import { mapIndicesTree, filterIndicesTree } from '../../utils/mapIndicesTree';
import type { PDNPattern } from '../../types/api';

export interface TypeNode {
    type: string;
    count: number;
    patterns: PDNPattern[];
}

export interface IndexPatternNode {
    index_pattern: string;
    total_hits: number;
    has_new_tasks?: boolean;
    new_count?: number;
    types: TypeNode[];
}

interface IndicesTreeProps {
    onSelectPatterns: (patterns: PDNPattern[], indexPattern?: string) => void;
    selectedCacheKeys: string[];
    selectedIndexPattern: string | null;
    scanningIndexPattern?: string | null;
    reloadKey?: number;
}

interface TreeState {
    data: IndexPatternNode[];
    loading: boolean;
    error: string | null;
}

export default function IndicesTree({
    onSelectPatterns,
    selectedCacheKeys,
    selectedIndexPattern,
    scanningIndexPattern,
    reloadKey = 0
}: IndicesTreeProps) {
    const [state, setState] = useState<TreeState>({
        data: [],
        loading: true,
        error: null,
    });
    const [expandedIndices, setExpandedIndices] = useState<Record<string, boolean>>({});
    const [expandedTypes, setExpandedTypes] = useState<Record<string, boolean>>({});
    const [filterText, setFilterText] = useState('');

    const fetchTree = useCallback(async () => {
        setState(prev => ({ ...prev, loading: true, error: null }));
        try {
            const response = await indicesApi.getTree();
            const mapped = mapIndicesTree(response);
            setState({ data: mapped, loading: false, error: null });
        } catch (err) {
            const error = err as { response?: { status?: number }; message?: string };
            if (error.response?.status === 401) {
                setState({ data: [], loading: false, error: 'Сессия истекла. Войдите снова.' });
            } else if (error.response?.status === 403) {
                setState({ data: [], loading: false, error: 'Нет прав доступа.' });
            } else {
                setState({ data: [], loading: false, error: 'Не удалось загрузить дерево. Проверьте подключение к API.' });
            }
        }
    }, []);

    useEffect(() => {
        fetchTree();
    }, [fetchTree, reloadKey]);

    const filteredData = useMemo(() => filterIndicesTree(state.data, filterText), [state.data, filterText]);

    const toggleIndex = (name: string) => setExpandedIndices(prev => ({ ...prev, [name]: !prev[name] }));
    const toggleType = (indexName: string, typeName: string) => setExpandedTypes(prev => ({ ...prev, [`${indexName}-${typeName}`]: !prev[`${indexName}-${typeName}`] }));

    const expandAll = () => {
        const newExpandedIndices: Record<string, boolean> = {};
        const newExpandedTypes: Record<string, boolean> = {};
        filteredData.forEach(idx => {
            newExpandedIndices[idx.index_pattern] = true;
            idx.types.forEach(t => {
                newExpandedTypes[`${idx.index_pattern}-${t.type}`] = true;
            });
        });
        setExpandedIndices(newExpandedIndices);
        setExpandedTypes(newExpandedTypes);
    };

    const collapseAll = () => {
        setExpandedIndices({});
        setExpandedTypes({});
    };

    const handlePatternClick = (e: React.MouseEvent, pattern: PDNPattern) => {
        e.stopPropagation();
        onSelectPatterns([pattern], undefined);
    };

    const handleIndexClick = (e: React.MouseEvent, idx: IndexPatternNode) => {
        e.stopPropagation();
        onSelectPatterns([], idx.index_pattern);
    };

    const handleIndexCaretClick = (e: React.MouseEvent, idx: IndexPatternNode) => {
        e.stopPropagation();
        toggleIndex(idx.index_pattern);
    };

    const handleRetry = () => {
        fetchTree();
    };

    if (state.loading) {
        return (
            <div className="flex flex-col h-full bg-slate-50">
                <div className="px-3 py-3 border-b border-slate-200 bg-white">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                            <Folder className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> Файловая система
                        </span>
                    </div>
                </div>
                <div className="flex-1 flex items-center justify-center">
                    <div className="text-center space-y-3">
                        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                        <p className="text-slate-500 text-sm">Загрузка дерева индексов...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (state.error) {
        return (
            <div className="flex flex-col h-full bg-slate-50">
                <div className="px-3 py-3 border-b border-slate-200 bg-white">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                            <Folder className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> Файловая система
                        </span>
                    </div>
                </div>
                <div className="flex-1 flex items-center justify-center p-4">
                    <div className="text-center space-y-3 max-w-xs">
                        <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
                        <p className="text-slate-700">{state.error}</p>
                        <button
                            onClick={handleRetry}
                            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors"
                        >
                            <RefreshCw className="w-4 h-4 mr-1 inline" /> Повторить
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (filteredData.length === 0 && state.data.length === 0) {
        return (
            <div className="flex flex-col h-full bg-slate-50">
                <div className="px-3 py-3 border-b border-slate-200 bg-white">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                            <Folder className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> Файловая система
                        </span>
                    </div>
                    <div className="relative mt-3">
                        <div className="absolute inset-y-0 left-0 pl-2 flex items-center pointer-events-none">
                            <Filter className="h-3 w-3 text-slate-400" />
                        </div>
                        <input
                            type="text"
                            value={filterText}
                            onChange={(e) => setFilterText(e.target.value)}
                            className="block w-full pl-7 pr-2 py-1.5 text-xs bg-white border border-slate-300 rounded shadow-sm text-slate-700 placeholder-slate-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                            placeholder="Поиск по индексу, полю или тегу..."
                        />
                    </div>
                </div>
                <div className="flex-1 flex items-center justify-center p-4">
                    <div className="text-center space-y-2">
                        <Database className="w-12 h-12 text-slate-300 mx-auto" />
                        <p className="text-slate-500">Нет паттернов</p>
                        <p className="text-xs text-slate-400">Запустите seed или сканер</p>
                    </div>
                </div>
            </div>
        );
    }

    if (filteredData.length === 0 && state.data.length > 0) {
        return (
            <div className="flex flex-col h-full bg-slate-50">
                <div className="px-3 py-3 border-b border-slate-200 bg-white flex flex-col shrink-0 space-y-3">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                            <Folder className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> Файловая система
                        </span>
                        <div className="flex space-x-1">
                            <button onClick={expandAll} className="text-[10px] px-1.5 py-0.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded text-slate-600 transition-colors shadow-sm">Развернуть</button>
                            <button onClick={collapseAll} className="text-[10px] px-1.5 py-0.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded text-slate-600 transition-colors shadow-sm">Свернуть</button>
                        </div>
                    </div>
                    <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-2 flex items-center pointer-events-none">
                            <Filter className="h-3 w-3 text-slate-400" />
                        </div>
                        <input
                            type="text"
                            value={filterText}
                            onChange={(e) => setFilterText(e.target.value)}
                            className="block w-full pl-7 pr-2 py-1.5 text-xs bg-white border border-slate-300 rounded shadow-sm text-slate-700 placeholder-slate-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                            placeholder="Поиск по индексу, полю или тегу..."
                        />
                    </div>
                </div>
                <div className="flex-1 flex items-center justify-center p-4">
                    <div className="text-center space-y-2">
                        <Filter className="w-12 h-12 text-slate-300 mx-auto" />
                        <p className="text-slate-500">Ничего не найдено</p>
                        <p className="text-xs text-slate-400">Попробуйте изменить фильтр</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-slate-50 text-slate-700 font-sans selection:bg-blue-100">
            <div className="px-3 py-3 border-b border-slate-200 bg-white flex flex-col shrink-0 space-y-3">
                <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                        <Folder className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> Файловая система
                    </span>
                    <div className="flex space-x-1">
                        <button onClick={expandAll} className="text-[10px] px-1.5 py-0.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded text-slate-600 transition-colors shadow-sm">Развернуть</button>
                        <button onClick={collapseAll} className="text-[10px] px-1.5 py-0.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded text-slate-600 transition-colors shadow-sm">Свернуть</button>
                    </div>
                </div>
                <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-2 flex items-center pointer-events-none">
                        <Filter className="h-3 w-3 text-slate-400" />
                    </div>
                    <input
                        type="text"
                        value={filterText}
                        onChange={(e) => setFilterText(e.target.value)}
                        className="block w-full pl-7 pr-2 py-1.5 text-xs bg-white border border-slate-300 rounded shadow-sm text-slate-700 placeholder-slate-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                        placeholder="Поиск по индексу, полю или тегу..."
                    />
                </div>
            </div>

            <div className="flex-1 overflow-y-auto px-1 py-3 text-[13px]">
                {filteredData.map((idxNode) => {
                    const isIdxExpanded = expandedIndices[idxNode.index_pattern];
                    const isIdxSelected = selectedIndexPattern === idxNode.index_pattern;

                    return (
                        <div key={idxNode.index_pattern} className="mb-0.5 select-none font-medium">
                            {/* Уровень 1: Паттерн Индекса */}
                            <div
                                className={clsx(
                                    "flex items-center px-1.5 py-1 rounded cursor-pointer transition-colors group",
                                    isIdxSelected ? "bg-blue-50 text-blue-700" : "hover:bg-slate-100"
                                )}
                                onDoubleClick={() => toggleIndex(idxNode.index_pattern)}
                                onClick={(e) => handleIndexClick(e, idxNode)}
                            >
                                <div onClick={(e) => handleIndexCaretClick(e, idxNode)} className="p-0.5 -ml-0.5 hover:bg-slate-200 rounded mr-0.5">
                                    {isIdxExpanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0 group-hover:text-slate-600" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0 group-hover:text-slate-600" />}
                                </div>
                                <Folder className="w-4 h-4 mr-1.5 shrink-0 text-amber-500" />
                                {/* ИНДИКАТОР СКАНИРОВАНИЯ */}
                                {scanningIndexPattern === idxNode.index_pattern && (
                                    <span className="ml-2 flex items-center">
                                        <Activity className="w-3.5 h-3.5 text-blue-500 animate-pulse" />
                                    </span>
                                )}
                                <span className={clsx("truncate", isIdxSelected ? "font-semibold" : "")}>
                                    {idxNode.index_pattern}
                                </span>

                                {idxNode.new_count && idxNode.new_count > 0 ? (
                                    <span className="text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded-full ml-2 leading-none font-bold shadow-sm">+{idxNode.new_count}</span>
                                ) : null}
                            </div>

                            {/* Уровень 2: Типы ПДн */}
                            {isIdxExpanded && (
                                <div className="ml-3 mt-0.5 space-y-0.5 border-l border-slate-200 pl-0.5">
                                    {idxNode.types.map(typeNode => {
                                        const typeKey = `${idxNode.index_pattern}-${typeNode.type}`;
                                        const isTypeExpanded = expandedTypes[typeKey];

                                        return (
                                            <div key={typeKey}>
                                                <div
                                                    className="flex items-center px-1.5 py-1 rounded cursor-pointer hover:bg-slate-100 transition-colors group text-slate-600"
                                                    onClick={() => toggleType(idxNode.index_pattern, typeNode.type)}
                                                >
                                                    {isTypeExpanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-400 mr-1 shrink-0 group-hover:text-slate-600" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400 mr-1 shrink-0 group-hover:text-slate-600" />}

                                                    <Hash className="w-4 h-4 text-slate-400 mr-1.5 shrink-0" />
                                                    <span className="font-semibold tracking-wide">{typeNode.type}</span>
                                                </div>

                                                {/* Уровень 3: Паттерны (Cache Keys) */}
                                                {isTypeExpanded && (
                                                    <div className="ml-3 mt-0.5 space-y-1 border-l border-slate-200 pl-0.5 py-1">
                                                        {typeNode.patterns.map(pattern => {
                                                            const isSelected = selectedCacheKeys.includes(pattern.cache_key);

                                                            const extraFieldPills = Object.entries(pattern.extra_fields || {}).map(([key, val], idx) => {
                                                                const colors = [
                                                                    "bg-blue-50 text-blue-600 border-blue-200",
                                                                    "bg-purple-50 text-purple-600 border-purple-200",
                                                                    "bg-cyan-50 text-cyan-600 border-cyan-200",
                                                                ];
                                                                return { key, text: val as string, colorClass: colors[idx % colors.length] };
                                                            });

                                                            return (
                                                                <div
                                                                    key={pattern.cache_key}
                                                                    className={clsx(
                                                                        "flex flex-col px-2 py-1.5 rounded cursor-pointer transition-colors border",
                                                                        isSelected
                                                                            ? "bg-blue-50 border-blue-200 shadow-sm"
                                                                            : "hover:bg-white border-transparent"
                                                                    )}
                                                                    onClick={(e) => handlePatternClick(e, pattern)}
                                                                >
                                                                    <div className="flex items-center">
{/* Иконка */}
                                                                        {pattern.context_type === 'structured_key' ? <Key className="w-3.5 h-3.5 mr-2 text-emerald-500 shrink-0" /> :
                                                                            pattern.context_type === 'free_text' ? <FileText className="w-3.5 h-3.5 mr-2 text-blue-500 shrink-0" /> :
                                                                                pattern.context_type === 'ambiguous' ? <AlertTriangle className="w-3.5 h-3.5 mr-2 text-amber-500 shrink-0" /> :
                                                                                    <File className="w-3.5 h-3.5 mr-2 text-emerald-500 shrink-0" />}

                                                                        {/* Имя поля */}
                                                                       <span className={clsx("text-[13px] tracking-tight", isSelected ? "text-blue-900 font-semibold" : "text-slate-700 font-medium")}>
                                                                            {pattern.field_path}
                                                                        </span>

{/* Бейджи контекста INLINE (для Mode B) */}
                                                                        {pattern.context_type !== 'base' && (
                                                                            <div className="flex items-center ml-2 space-x-1.5">
                                                                                {pattern.context_type === 'structured_key' && (
                                                                                    <>
                                                                                        <span className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded-lg border border-emerald-200 leading-none">structured_key</span>
                                                                                        <span className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded-lg border border-emerald-200 leading-none">key: {pattern.key_hint}</span>
                                                                                    </>
                                                                                )}
                                                                                {pattern.context_type === 'free_text' && (
                                                                                    <>
                                                                                        <span className="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded-lg border border-blue-200 leading-none">free_text</span>
                                                                                        <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded-lg border border-slate-200 leading-none">нет ключа</span>
                                                                                    </>
                                                                                )}
                                                                                {pattern.context_type === 'ambiguous' && (
                                                                                    <>
                                                                                        <span className="text-[10px] px-1.5 py-0.5 bg-amber-50 text-amber-600 rounded-lg border border-amber-200 leading-none">ambiguous</span>
                                                                                        <span className="text-[10px] px-1.5 py-0.5 bg-amber-50 text-amber-600 rounded-lg border border-amber-200 leading-none">key?: {pattern.key_hint}</span>
                                                                                    </>
                                                                                )}
                                                                            </div>
                                                                        )}

                                                                        {/* Точка статуса - сразу после имени/бейджей */}
                                                                        {pattern.status === 'new' && <span className="ml-2 w-1.5 h-1.5 rounded-full bg-red-500 shrink-0 shadow-sm" />}
                                                                        {pattern.status === 'confirmed' && <span className="ml-2 w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0 shadow-sm" />}
                                                                    </div>

{/* Дополнительные поля (Extra fields & Key hints for Mode A) */}
                                                                    <div className="mt-1.5 ml-[26px] flex flex-wrap gap-1.5">
                                                                        {pattern.context_type === 'structured_key' && pattern.key_hint && (
                                                                            <span className="text-[10px] px-1.5 py-[3px] bg-emerald-50 text-emerald-600 rounded-lg border border-emerald-200 leading-none shadow-sm font-medium">
                                                                                key: {pattern.key_hint}
                                                                            </span>
                                                                        )}
                                                                        {extraFieldPills.map((pill, i) => (
                                                                            <span key={i} title={pill.key} className={clsx("text-[10px] px-1.5 py-[3px] rounded-lg border leading-none shadow-sm font-medium", pill.colorClass)}>
                                                                                {pill.text}
                                                                            </span>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}