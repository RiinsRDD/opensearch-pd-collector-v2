import { useState, useMemo } from 'react';
import { ChevronRight, ChevronDown, Folder, FileDigit, Hash, Filter } from 'lucide-react';
import clsx from 'clsx';

export interface PDNPattern {
    cache_key: string;
    field_path: string;
    pdn_type: string;
    hit_count: number;
    status: 'new' | 'confirmed' | 'done' | 'false_positive' | 'unverified' | 'archived';
    tags: string[];
}

export interface TypeNode {
    type: string;
    count: number;
    patterns: PDNPattern[];
}

export interface IndexPatternNode {
    index_pattern: string;
    total_hits: number;
    types: TypeNode[];
    has_new_tasks?: boolean; // Флаг, есть ли новые задачи по этому индексу
}

interface IndicesTreeProps {
    onSelectPatterns: (patterns: PDNPattern[], indexPattern?: string) => void;
    selectedCacheKeys: string[];
    selectedIndexPattern: string | null;
}

export default function IndicesTree({ onSelectPatterns, selectedCacheKeys, selectedIndexPattern }: IndicesTreeProps) {
    const [expandedIndices, setExpandedIndices] = useState<Record<string, boolean>>({});
    const [expandedTypes, setExpandedTypes] = useState<Record<string, boolean>>({});
    const [filterText, setFilterText] = useState('');

    // Моковые данные
    const mockData: IndexPatternNode[] = [
        {
            index_pattern: 'bcs-tech-logs-*',
            total_hits: 24,
            has_new_tasks: true,
            types: [
                {
                    type: 'PHONE',
                    count: 15,
                    patterns: [
                        { cache_key: 'hash_78da81', field_path: 'req.body.client_phone', pdn_type: 'PHONE', hit_count: 12, status: 'new', tags: ['High'] },
                        { cache_key: 'hash_81bc92', field_path: 'log.message', pdn_type: 'PHONE', hit_count: 3, status: 'confirmed', tags: [] },
                        { cache_key: 'hash_90cd11', field_path: 'user.phone', pdn_type: 'PHONE', hit_count: 5, status: 'new', tags: ['U'] }
                    ]
                },
                {
                    type: 'EMAIL',
                    count: 9,
                    patterns: [
                        { cache_key: 'hash_99zz11', field_path: 'metadata.user.email', pdn_type: 'EMAIL', hit_count: 9, status: 'new', tags: ['Unverified'] }
                    ]
                }
            ]
        },
        {
            index_pattern: 'client-activity-api-*',
            total_hits: 5,
            has_new_tasks: false,
            types: [
                {
                    type: 'FIO',
                    count: 5,
                    patterns: [
                        { cache_key: 'hash_fio_1', field_path: 'author.name', pdn_type: 'FIO', hit_count: 5, status: 'false_positive', tags: ['Fake'] }
                    ]
                }
            ]
        }
    ];

    const filteredData = useMemo(() => {
        if (!filterText.trim()) return mockData;
        const lowerFilter = filterText.toLowerCase();

        return mockData.map(idx => {
            const filteredTypes = idx.types.map(t => {
                const filteredPatterns = t.patterns.filter(p =>
                    p.status.toLowerCase().includes(lowerFilter) ||
                    p.tags.some(tag => tag.toLowerCase().includes(lowerFilter)) ||
                    p.field_path.toLowerCase().includes(lowerFilter)
                );
                return { ...t, patterns: filteredPatterns };
            }).filter(t => t.patterns.length > 0 || t.type.toLowerCase().includes(lowerFilter));

            return { ...idx, types: filteredTypes };
        }).filter(idx => idx.types.length > 0 || idx.index_pattern.toLowerCase().includes(lowerFilter));
    }, [mockData, filterText]);

    const toggleIndex = (name: string) => {
        setExpandedIndices(prev => ({ ...prev, [name]: !prev[name] }));
    };

    const toggleType = (indexName: string, typeName: string) => {
        const key = `${indexName}-${typeName}`;
        setExpandedTypes(prev => ({ ...prev, [key]: !prev[key] }));
    };

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

        // Строгое одиночное выделение
        const newSelectedKeys = [pattern.cache_key];

        // Find full objects for selected keys
        const selectedObjects: PDNPattern[] = [];
        mockData.forEach(idx => idx.types.forEach(t => t.patterns.forEach(p => {
            if (newSelectedKeys.includes(p.cache_key)) {
                selectedObjects.push(p);
            }
        })));

        onSelectPatterns(selectedObjects, undefined);
    };

    const handleIndexClick = (e: React.MouseEvent, idx: IndexPatternNode) => {
        e.stopPropagation();
        toggleIndex(idx.index_pattern);

        // Клик по индексу просто разворачивает его и сбрасывает выбор кэш-ключей + открывает Дашборд индекса
        onSelectPatterns([], idx.index_pattern);
    };

    return (
        <div className="flex flex-col h-full bg-slate-50/50 border-r border-slate-200">
            <div className="px-3 py-2 border-b border-slate-200 bg-slate-100 flex flex-col shrink-0 space-y-2">
                <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                        <Folder className="w-3.5 h-3.5 mr-1.5" /> Индексы
                    </span>
                    <div className="flex space-x-1">
                        <button onClick={expandAll} className="text-[10px] px-1.5 py-0.5 bg-slate-200 hover:bg-slate-300 rounded text-slate-600 transition-colors">Развернуть всё</button>
                        <button onClick={collapseAll} className="text-[10px] px-1.5 py-0.5 bg-slate-200 hover:bg-slate-300 rounded text-slate-600 transition-colors">Свернуть всё</button>
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
                        className="block w-full pl-7 pr-2 py-1 text-xs border border-slate-300 rounded shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        placeholder="Фильтр по статусу, тегу..."
                    />
                </div>
            </div>

            <div className="flex-1 overflow-y-auto px-1 py-2">
                {filteredData.map((idxNode) => {
                    const isIdxExpanded = expandedIndices[idxNode.index_pattern];
                    const isIdxSelected = selectedIndexPattern === idxNode.index_pattern;

                    // Вычисление количества New cache-keys
                    const newCacheKeysCount = idxNode.types.flatMap(t => t.patterns).filter(p => p.status === 'new').length;

                    // Подсветка индекса: если есть новые задачи или новые кэш-ключи
                    const needsHighlight = idxNode.has_new_tasks || newCacheKeysCount > 0;

                    return (
                        <div key={idxNode.index_pattern} className="mb-0.5 select-none">
                            {/* Узел Pattern Индекса */}
                            <div
                                className={clsx(
                                    "flex items-center px-1.5 py-1 rounded cursor-pointer transition-colors group",
                                    isIdxSelected ? "bg-amber-100/60 border border-amber-200/50" : (isIdxExpanded ? "bg-slate-200/50" : "hover:bg-slate-200/30"),
                                    needsHighlight && !isIdxSelected && "bg-blue-50 border-l-2 border-blue-400"
                                )}
                                onClick={(e) => handleIndexClick(e, idxNode)}
                            >
                                {isIdxExpanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-400 mr-1 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400 mr-1 shrink-0" />}

                                <Folder className={clsx("w-4 h-4 mr-1.5 shrink-0", needsHighlight ? "text-blue-500" : (isIdxExpanded ? "text-slate-500" : "text-amber-500"))} />
                                <span className={clsx("text-sm font-medium truncate flex-1", needsHighlight ? "text-blue-800" : "text-slate-700")}>
                                    {idxNode.index_pattern}
                                </span>

                                {newCacheKeysCount > 0 && (
                                    <span className="text-[10px] bg-red-100 text-red-700 px-1.5 py-0.5 rounded ml-2 font-bold" title="Новые примеры">+{newCacheKeysCount}</span>
                                )}
                                <span className="text-[10px] bg-slate-200 text-slate-500 px-1.5 py-0.5 rounded ml-1" title="Всего вхождений">{idxNode.total_hits}</span>
                            </div>

                            {/* Подчиненные узлы: Типы ПДн */}
                            {isIdxExpanded && (
                                <div className="ml-4 mt-0.5 space-y-0.5 border-l border-slate-200/60 pl-1">
                                    {idxNode.types.map(typeNode => {
                                        const typeKey = `${idxNode.index_pattern}-${typeNode.type}`;
                                        const isTypeExpanded = expandedTypes[typeKey];

                                        return (
                                            <div key={typeKey}>
                                                <div
                                                    className="flex items-center px-1.5 py-1 rounded cursor-pointer hover:bg-slate-200/30 transition-colors group"
                                                    onClick={() => toggleType(idxNode.index_pattern, typeNode.type)}
                                                >
                                                    {isTypeExpanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-300 mr-1 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-300 mr-1 shrink-0" />}

                                                    <Hash className="w-3.5 h-3.5 text-slate-400 mr-1.5 shrink-0" />
                                                    <span className="text-[13px] font-medium text-slate-600 flex-1">{typeNode.type}</span>
                                                    <span className="text-[10px] text-slate-400">{typeNode.count}</span>
                                                </div>

                                                {/* Листья: Паттерны */}
                                                {isTypeExpanded && (
                                                    <div className="ml-4 mt-0.5 space-y-0.5 pl-1">
                                                        {typeNode.patterns.map(pattern => {
                                                            const isSelected = selectedCacheKeys.includes(pattern.cache_key);

                                                            return (
                                                                <div
                                                                    key={pattern.cache_key}
                                                                    className={clsx(
                                                                        "flex items-start px-2 py-1.5 rounded cursor-pointer transition-all border",
                                                                        isSelected
                                                                            ? "bg-blue-100/50 border-blue-300 shadow-sm"
                                                                            : "hover:bg-slate-200/40 border-transparent"
                                                                    )}
                                                                    onClick={(e) => handlePatternClick(e, pattern)}
                                                                >

                                                                    <FileDigit className={clsx("w-3.5 h-3.5 mr-2 mt-0.5 shrink-0", pattern.status === 'new' ? "text-red-400" : "text-slate-400")} />

                                                                    <div className="flex-1 min-w-0">
                                                                        <div className={clsx(
                                                                            "text-[13px] leading-tight break-all",
                                                                            isSelected ? "text-blue-800 font-medium" : "text-slate-700"
                                                                        )}>
                                                                            {pattern.field_path}
                                                                        </div>
                                                                        <div className="flex items-center mt-1 space-x-2">
                                                                            <span className="text-[10px] font-mono text-slate-400" title="Cache Key">{pattern.cache_key.substring(0, 8)}...</span>

                                                                            {/* Статус в виде точки */}
                                                                            {pattern.status === 'new' && <span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_4px_rgba(239,68,68,0.5)]" title="Новый" />}
                                                                            {pattern.status === 'confirmed' && <span className="w-2 h-2 rounded-full bg-blue-500" title="Подтвержден" />}
                                                                            {pattern.status === 'done' && <span className="w-2 h-2 rounded-full bg-emerald-500" title="В задаче" />}
                                                                            {pattern.status === 'false_positive' && <span className="w-2 h-2 rounded-full bg-yellow-500" title="Исключение" />}
                                                                            {pattern.status === 'unverified' && <span className="w-2 h-2 rounded-full bg-slate-400" title="Не проверен" />}

                                                                            {/* Теги */}
                                                                            {pattern.tags.map(tag => (
                                                                                <span key={tag} className={clsx(
                                                                                    "text-[9px] px-1 py-0.5 rounded-sm leading-none border",
                                                                                    tag === 'G' ? "bg-amber-100 text-amber-800 border-amber-200" :
                                                                                        tag === 'S' ? "bg-purple-100 text-purple-800 border-purple-200" :
                                                                                            tag === 'U' ? "bg-emerald-100 text-emerald-800 border-emerald-200" :
                                                                                                "bg-slate-200 text-slate-600 border-slate-300"
                                                                                )}>
                                                                                    {tag}
                                                                                </span>
                                                                            ))}

                                                                            <span className="text-[10px] text-slate-500 flex-1 text-right">{pattern.hit_count} hits</span>
                                                                        </div>
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
