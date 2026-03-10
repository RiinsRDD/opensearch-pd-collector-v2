import { useState, useMemo } from 'react';
import { ChevronRight, ChevronDown, Folder, Hash, Key, FileText, AlertTriangle, File, Filter } from 'lucide-react';
import clsx from 'clsx';

export interface PDNPattern {
    cache_key: string;
    field_path: string;
    pdn_type: string;
    hit_count: number;
    status: 'new' | 'confirmed' | 'done' | 'false_positive' | 'unverified' | 'archived';
    tags: string[];
    is_free_text?: boolean;
    context_type?: 'structured_key' | 'free_text' | 'ambiguous' | 'base';
    key_hint?: string;
    extra_fields?: Record<string, string>;
}

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
}

const mockData: IndexPatternNode[] = [
    {
        index_pattern: 'bcs-tech-logs-*',
        total_hits: 42,
        has_new_tasks: true,
        new_count: 5,
        types: [
            {
                type: 'PHONE',
                count: 28,
                patterns: [
                    {
                        cache_key: 'a8f2c184', field_path: 'req.body.client_phone', pdn_type: 'PHONE',
                        is_free_text: false, context_type: 'base',
                        extra_fields: { 'NameOfMicroService': 'auth-svc', 'kubernetes.container.name': 'api-gw' },
                        hit_count: 12, status: 'new', tags: []
                    },
                    {
                        cache_key: 'c4e9b321', field_path: 'user.phone', pdn_type: 'PHONE',
                        is_free_text: false, context_type: 'base',
                        extra_fields: { 'NameOfMicroService': 'user-svc', 'kubernetes.container.name': 'main-app' },
                        hit_count: 5, status: 'confirmed', tags: []
                    },
                    {
                        cache_key: 'f1a2b349', field_path: 'message', pdn_type: 'PHONE',
                        is_free_text: true, context_type: 'structured_key', key_hint: 'phone',
                        extra_fields: { 'NameOfMicroService': 'api-gw', 'kubernetes.container.name': 'worker-pod' },
                        hit_count: 8, status: 'new', tags: []
                    },
                    {
                        cache_key: 'd7c8e1a2', field_path: 'message', pdn_type: 'PHONE',
                        is_free_text: true, context_type: 'free_text',
                        extra_fields: { 'NameOfMicroService': 'logger-svc', 'kubernetes.container.name': 'logger-pod' },
                        hit_count: 3, status: 'confirmed', tags: []
                    },
                    {
                        cache_key: 'b2a1c4df', field_path: 'raw_message', pdn_type: 'PHONE',
                        is_free_text: true, context_type: 'ambiguous', key_hint: 'данные клиента',
                        extra_fields: { 'NameOfMicroService': 'api-gw', 'kubernetes.container.name': 'api-gw' },
                        hit_count: 1, status: 'new', tags: []
                    }
                ]
            },
            {
                type: 'EMAIL',
                count: 14,
                patterns: [
                    {
                        cache_key: 'e5f6a7b8', field_path: 'metadata.user.email', pdn_type: 'EMAIL',
                        is_free_text: false, context_type: 'base',
                        extra_fields: { 'NameOfMicroService': 'auth-svc', 'kubernetes.container.name': 'auth-pod' },
                        hit_count: 9, status: 'new', tags: []
                    },
                    {
                        cache_key: 'a1b2c3d4', field_path: 'log.body', pdn_type: 'EMAIL',
                        is_free_text: true, context_type: 'structured_key', key_hint: 'email',
                        extra_fields: { 'NameOfMicroService': 'mailer-svc', 'kubernetes.container.name': 'mail-pod' },
                        hit_count: 5, status: 'unverified', tags: []
                    }
                ]
            }
        ]
    },
    {
        index_pattern: 'client-activity-api-*',
        total_hits: 5,
        has_new_tasks: false,
        types: []
    }
];

export default function IndicesTree({ onSelectPatterns, selectedCacheKeys, selectedIndexPattern }: IndicesTreeProps) {
    const [expandedIndices, setExpandedIndices] = useState<Record<string, boolean>>({});
    const [expandedTypes, setExpandedTypes] = useState<Record<string, boolean>>({});
    const [filterText, setFilterText] = useState('');

    const filteredData = useMemo(() => {
        if (!filterText.trim()) return mockData;
        const lowerFilter = filterText.toLowerCase();

        return mockData.map(idx => {
            const filteredTypes = idx.types.map(t => {
                const filteredPatterns = t.patterns.filter(p =>
                    p.status.toLowerCase().includes(lowerFilter) ||
                    p.tags.some(tag => tag.toLowerCase().includes(lowerFilter)) ||
                    p.field_path.toLowerCase().includes(lowerFilter) ||
                    (p.key_hint && p.key_hint.toLowerCase().includes(lowerFilter)) ||
                    (p.extra_fields && Object.values(p.extra_fields).some(val => val.toLowerCase().includes(lowerFilter)))
                );
                return { ...t, patterns: filteredPatterns };
            }).filter(t => t.patterns.length > 0 || t.type.toLowerCase().includes(lowerFilter));

            return { ...idx, types: filteredTypes };
        }).filter(idx => idx.types.length > 0 || idx.index_pattern.toLowerCase().includes(lowerFilter));
    }, [filterText]);

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

    return (
        <div className="flex flex-col h-full bg-slate-50 text-slate-700 font-sans selection:bg-blue-100">
            <div className="px-3 py-3 border-b border-slate-200 bg-white flex flex-col shrink-0 space-y-3">
                <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                        <Folder className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> Файловая система
                    </span>
                    <div className="flex space-x-1">
                        <button onClick={expandAll} className="text-[10px] px-1.5 py-0.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded text-slate-600 transition-colors shadow-sm">Разварачивать</button>
                        <button onClick={collapseAll} className="text-[10px] px-1.5 py-0.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded text-slate-600 transition-colors shadow-sm">Сворачивать</button>
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
                                                                        {pattern.is_free_text ? (
                                                                            pattern.context_type === 'structured_key' ? <Key className="w-3.5 h-3.5 mr-2 text-emerald-500 shrink-0" /> :
                                                                                pattern.context_type === 'free_text' ? <FileText className="w-3.5 h-3.5 mr-2 text-blue-500 shrink-0" /> :
                                                                                    <AlertTriangle className="w-3.5 h-3.5 mr-2 text-amber-500 shrink-0" />
                                                                        ) : (
                                                                            <File className="w-3.5 h-3.5 mr-2 text-emerald-500 shrink-0" />
                                                                        )}

                                                                        {/* Имя поля */}
                                                                        <span className={clsx("text-[13px] tracking-tight", isSelected ? "text-blue-900 font-semibold" : "text-slate-700 font-medium")}>
                                                                            {pattern.field_path}
                                                                        </span>

                                                                        {/* Бейджи контекста INLINE (для Mode B) */}
                                                                        {pattern.is_free_text && (
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
                                                                        {!pattern.is_free_text && pattern.key_hint && (
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

