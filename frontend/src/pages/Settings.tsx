import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Tag, Palette, Database, Trash2, Filter, FileMinus, X, Plus, Save, Code } from 'lucide-react';
import GlobalExceptions from '../components/settings/GlobalExceptions';
import IndexExceptions from '../components/settings/IndexExceptions';
import PdnRegexList from '../components/settings/PdnRegexList';
import clsx from 'clsx';
import { settingsApi, type GlobalSettingsData } from '../api/client';

export default function Settings() {
    const [activeTab, setActiveTab] = useState<string>('general');
    const [globalSettings, setGlobalSettings] = useState<GlobalSettingsData | null>(null);
    const [loadingSettings, setLoadingSettings] = useState(false);
    const [editingFields, setEditingFields] = useState<Record<string, string>>({});
    const [viewModal, setViewModal] = useState<{ isOpen: boolean, title: string, items: string[] }>({ isOpen: false, title: '', items: [] });

    useEffect(() => {
        if (activeTab === 'general' && !globalSettings) {
            fetchGlobalSettings();
        }
    }, [activeTab]);

    const fetchGlobalSettings = async () => {
        try {
            setLoadingSettings(true);
            const data = await settingsApi.getSettings();
            setGlobalSettings(data);
        } catch (error) {
            console.error('Failed to load global settings', error);
            // Mock fallback
            setGlobalSettings({
                pdn_flags: { phone: true, email: true, card: true, fio: false },
                examples_count: 5, scan_interval_hours: 24,
                exclude_index_patterns: ['.kibana', '.tasks', '.opensearch-observability'],
                exclude_index_regexes: ['^\\.ds-logs-.*'],
                include_index_regexes: ['.*'],
                mail_service_names: [], unknown_mail_service_parts: [], card_bank_bins_4: [],
                invalid_def_codes: [], surn_ends_cis: [], surn_ends_world: [], patron_ends: [], fio_special_markers: []
            });
        } finally {
            setLoadingSettings(false);
        }
    };

    const saveSettingsServer = async () => {
        if (!globalSettings) return;
        try {
            await settingsApi.saveSettings(globalSettings);
            alert('Настройки успешно сохранены');
        } catch (error) {
            console.error('Failed to save settings', error);
            alert('Ошибка: ' + error);
        }
    };

    const handleSettingChange = (field: keyof GlobalSettingsData, value: any) => {
        setGlobalSettings(prev => prev ? { ...prev, [field]: value } : null);
    };

    const handleEditInlineOpen = (field: keyof GlobalSettingsData) => {
        if (!globalSettings) return;
        setEditingFields(prev => ({
            ...prev,
            [field]: ((globalSettings[field] as string[]) || []).join(', ')
        }));
    };

    const handleEditInlineCancel = (field: keyof GlobalSettingsData) => {
        setEditingFields(prev => {
            const next = { ...prev };
            delete next[field];
            return next;
        });
    };

    const handleEditInlineSave = async (field: keyof GlobalSettingsData) => {
        if (!globalSettings) return;
        const rawValue = editingFields[field] || '';
        const rawItems = rawValue.split(',').map(s => s.trim().toLowerCase()).filter(s => s.length > 0);
        const uniqueSorted = Array.from(new Set(rawItems)).sort();

        const newSettings = { ...globalSettings, [field]: uniqueSorted };
        setGlobalSettings(newSettings);

        handleEditInlineCancel(field);

        try {
            await settingsApi.saveSettings(newSettings);
        } catch (error) {
            console.error('Failed to save settings', error);
            alert('Ошибка при сохранении: ' + error);
        }
    };

    const handleArrayAdd = (field: keyof GlobalSettingsData) => {
        if (!globalSettings) return;
        const val = prompt('Введите значение:');
        if (val) {
            const arr = ((globalSettings[field] as string[]) || []);
            handleSettingChange(field, [...arr, val]);
        }
    };

    const handleArrayRemove = (field: keyof GlobalSettingsData, idx: number) => {
        if (globalSettings) {
            const arr = [...((globalSettings[field] as string[]) || [])];
            arr.splice(idx, 1);
            handleSettingChange(field, arr);
        }
    };

    const renderDictionaryList = (field: keyof GlobalSettingsData, title: string, subtitle: string) => {
        if (!globalSettings) return null;
        if (field === 'unknown_mail_service_parts') {
            const items = (globalSettings[field] as string[]) || [];
            return (
                <div className="p-6 border-b border-slate-100 last:border-b-0">
                    <div className="flex justify-between items-center mb-4">
                        <div>
                            <div className="text-sm font-semibold text-slate-800">{title}</div>
                            <div className="text-xs text-slate-500">{subtitle}</div>
                        </div>
                        <button onClick={() => setViewModal({ isOpen: true, title, items })} className="text-slate-600 hover:bg-slate-100 px-3 py-1.5 rounded-md text-sm font-medium transition cursor-pointer border border-slate-200 shadow-sm">
                            Посмотреть из БД ({items.length})
                        </button>
                    </div>
                </div>
            );
        }

        const items = (globalSettings[field] as string[]) || [];
        const isEditing = typeof editingFields[field] === 'string';

        return (
            <div className="p-6 border-b border-slate-100 last:border-b-0">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <div className="text-sm font-semibold text-slate-800">{title}</div>
                        <div className="text-xs text-slate-500">{subtitle}</div>
                    </div>
                    {!isEditing && (
                        <button onClick={() => handleEditInlineOpen(field)} className="text-indigo-600 hover:bg-indigo-50 px-3 py-1.5 rounded-md text-sm font-medium transition cursor-pointer">
                            Изменить ({items.length})
                        </button>
                    )}
                </div>

                {isEditing ? (
                    <div className="space-y-3">
                        <textarea
                            value={editingFields[field]}
                            onChange={(e) => setEditingFields(prev => ({ ...prev, [field]: e.target.value }))}
                            className="w-full h-32 p-3 border border-slate-300 rounded-md shadow-sm font-mono text-sm focus:ring-indigo-500 focus:border-indigo-500"
                            placeholder="Введите значения через запятую..."
                        />
                        <div className="flex justify-end space-x-3">
                            <button
                                onClick={() => handleEditInlineCancel(field)}
                                className="px-3 py-1.5 bg-white border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={() => handleEditInlineSave(field)}
                                className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 flex items-center shadow-sm"
                            >
                                <Save className="w-4 h-4 mr-2" /> Сохранить
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-wrap gap-2">
                        {items.length === 0 && <span className="text-sm text-slate-400 italic">Нет записей</span>}
                        {items.slice(0, 50).map((item, idx) => (
                            <div key={idx} className="flex items-center bg-slate-50 border border-slate-200 text-slate-700 rounded px-2.5 py-1 text-sm font-mono truncate max-w-[200px]">
                                {item}
                            </div>
                        ))}
                        {items.length > 50 && <span className="text-sm text-slate-400 font-medium ml-2 self-center">...и еще {items.length - 50}</span>}
                    </div>
                )}
            </div>
        );
    };

    const renderArrayList = (field: keyof GlobalSettingsData, title: string, subtitle: string) => {
        if (!globalSettings) return null;
        const items = (globalSettings[field] as string[]) || [];
        return (
            <div className="p-6 border-b border-slate-100 last:border-b-0">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <div className="text-sm font-semibold text-slate-800">{title}</div>
                        <div className="text-xs text-slate-500">{subtitle}</div>
                    </div>
                    <button onClick={() => handleArrayAdd(field)} className="text-indigo-600 hover:bg-indigo-50 px-3 py-1.5 rounded-md text-sm font-medium flex items-center transition">
                        <Plus className="w-4 h-4 mr-1" /> Добавить
                    </button>
                </div>
                <div className="flex flex-wrap gap-2">
                    {items.length === 0 && <span className="text-sm text-slate-400 italic">Нет записей</span>}
                    {items.map((item, idx) => (
                        <div key={idx} className="flex items-center bg-slate-50 border border-slate-200 text-slate-700 rounded px-2.5 py-1 text-sm font-mono">
                            {item}
                            <button onClick={() => handleArrayRemove(field, idx)} className="ml-2 text-slate-400 hover:text-rose-600 transition"><X className="w-3.5 h-3.5" /></button>
                        </div>
                    ))}
                </div>
            </div>
        );
    };
    const [statuses, setStatuses] = useState([
        { id: 'new', label: 'New', color: '#ef4444' }, // red-500
        { id: 'confirmed', label: 'Confirmed', color: '#3b82f6' }, // blue-500
        { id: 'done', label: 'Done', color: '#10b981' }, // emerald-500
        { id: 'false_positive', label: 'False Positive', color: '#eab308' }, // yellow-500
        { id: 'unverified', label: 'Unverified', color: '#94a3b8' } // slate-400
    ]);

    const [tags, setTags] = useState(['High', 'Low', 'U', 'G', 'S', 'Internal', 'Fake']);

    const handleDeleteTag = (tagToDelete: string) => {
        if (confirm(`Вы уверены, что хотите глобально удалить тег "${tagToDelete}" изо всех примеров?`)) {
            setTags(tags.filter(t => t !== tagToDelete));
            // Здесь будет API вызов для глобального удаления тега
        }
    };

    return (
        <div className="flex flex-col h-full bg-slate-50">

            <div className="flex-1 flex overflow-hidden">
                {/* Левое меню настроек */}
                <div className="w-64 bg-white border-r border-slate-200 p-4 space-y-1">
                    <button
                        onClick={() => setActiveTab('general')}
                        className={clsx(
                            "w-full flex items-center px-4 py-2.5 text-sm font-medium rounded-md transition-colors",
                            activeTab === 'general' ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
                        )}
                    >
                        <SettingsIcon className={clsx("w-4 h-4 mr-3 min-w-4", activeTab === 'general' ? "text-indigo-500" : "text-slate-400")} />
                        <span className="truncate">Общие</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('pdn_parsers')}
                        className={clsx(
                            "w-full flex items-center px-4 py-2.5 text-sm font-medium rounded-md transition-colors",
                            activeTab === 'pdn_parsers' ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
                        )}
                    >
                        <Database className={clsx("w-4 h-4 mr-3 min-w-4", activeTab === 'pdn_parsers' ? "text-indigo-500" : "text-slate-400")} />
                        <span className="truncate">Словари парсеров ПДн</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('pdn_regex')}
                        className={clsx(
                            "w-full flex items-center px-4 py-2.5 text-sm font-medium rounded-md transition-colors",
                            activeTab === 'pdn_regex' ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
                        )}
                    >
                        <Code className={clsx("w-4 h-4 mr-3 min-w-4", activeTab === 'pdn_regex' ? "text-indigo-500" : "text-slate-400")} />
                        <span className="truncate">Регулярки ПДн</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('global_exclusions')}
                        className={clsx(
                            "w-full flex items-center px-4 py-2.5 text-sm font-medium rounded-md transition-colors",
                            activeTab === 'global_exclusions' ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
                        )}
                    >
                        <Filter className={clsx("w-4 h-4 mr-3 min-w-4", activeTab === 'global_exclusions' ? "text-indigo-500" : "text-slate-400")} />
                        <span className="truncate">Глобальные исключения</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('index_exclusions')}
                        className={clsx(
                            "w-full flex items-center px-4 py-2.5 text-sm font-medium rounded-md transition-colors",
                            activeTab === 'index_exclusions' ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
                        )}
                    >
                        <FileMinus className={clsx("w-4 h-4 mr-3 min-w-4", activeTab === 'index_exclusions' ? "text-indigo-500" : "text-slate-400")} />
                        <span className="truncate">Исключения индексов</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('statuses')}
                        className={clsx(
                            "w-full flex items-center px-4 py-2.5 text-sm font-medium rounded-md transition-colors",
                            activeTab === 'statuses' ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
                        )}
                    >
                        <Palette className={clsx("w-4 h-4 mr-3 min-w-4", activeTab === 'statuses' ? "text-indigo-500" : "text-slate-400")} />
                        <span className="truncate">Статусы и Цвета</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('tags')}
                        className={clsx(
                            "w-full flex items-center px-4 py-2.5 text-sm font-medium rounded-md transition-colors",
                            activeTab === 'tags' ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
                        )}
                    >
                        <Tag className={clsx("w-4 h-4 mr-3 min-w-4", activeTab === 'tags' ? "text-indigo-500" : "text-slate-400")} />
                        <span className="truncate">Управление тегами</span>
                    </button>
                </div>

                {/* Основная рабочая область */}
                <div className="flex-1 p-8 overflow-auto">
                    <div className="max-w-4xl space-y-6">

                        {activeTab === 'general' && (
                            <>
                                {loadingSettings || !globalSettings ? (
                                    <div className="text-slate-500 text-sm">Загрузка настроек...</div>
                                ) : (
                                    <>
                                        {/* Глобальные параметры */}
                                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                                            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                                                <h3 className="font-semibold text-slate-800 flex items-center">
                                                    <Database className="w-4 h-4 mr-2" /> Базовые настройки
                                                </h3>
                                                <button
                                                    onClick={saveSettingsServer}
                                                    className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded shadow-sm hover:bg-indigo-700 flex items-center transition"
                                                >
                                                    <Save className="w-4 h-4 mr-2" /> Сохранить общие настройки
                                                </button>
                                            </div>
                                            <div className="p-6 space-y-4">
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                    <div>
                                                        <label className="block text-sm font-medium text-slate-700 mb-1">Кол-во сохраняемых примеров</label>
                                                        <input
                                                            type="number"
                                                            value={globalSettings.examples_count}
                                                            onChange={e => handleSettingChange('examples_count', parseInt(e.target.value))}
                                                            className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-indigo-500 sm:text-sm"
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-sm font-medium text-slate-700 mb-1">Интервал сканирования (часов)</label>
                                                        <input
                                                            type="number"
                                                            value={globalSettings.scan_interval_hours}
                                                            onChange={e => handleSettingChange('scan_interval_hours', parseInt(e.target.value))}
                                                            className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-indigo-500 sm:text-sm"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Типы ПДн (Флаги) */}
                                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mt-6">
                                            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50">
                                                <h3 className="font-semibold text-slate-800">Типы ПДн для сканирования</h3>
                                                <p className="text-xs text-slate-500 mt-1">Определяет, какие типы данных (детекторы) будут активно искаться.</p>
                                            </div>
                                            <div className="p-6 bg-slate-50 border-t border-slate-200">
                                                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                                    {Object.entries(globalSettings.pdn_flags || {}).map(([key, value]) => (
                                                        <label key={key} className="flex items-center space-x-3 p-3 bg-white border border-slate-200 rounded cursor-pointer hover:bg-slate-50 shadow-sm">
                                                            <input type="checkbox" checked={value} onChange={e => handleSettingChange('pdn_flags', { ...globalSettings.pdn_flags, [key]: e.target.checked })} className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4" />
                                                            <span className="text-sm font-medium text-slate-700 uppercase">{key}</span>
                                                        </label>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Системные исключения индексов */}
                                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mt-6">
                                            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                                                <h3 className="font-semibold text-slate-800 flex items-center">
                                                    <FileMinus className="w-4 h-4 mr-2 text-slate-500" /> Исключения и фильтры индексов
                                                </h3>
                                            </div>
                                            {renderArrayList('exclude_index_patterns', 'Исключить по полному совпадению (Pattern)', 'Точные имена или подстроки индексов, которые мы не парсим.')}
                                            {renderArrayList('exclude_index_regexes', 'Исключить по регулярному выражению (Regex)', 'Если имя индекса совпадает с регулярным выражением, он игнорируется.')}
                                            {renderArrayList('include_index_regexes', 'Разрешить мониторинг (Include Regex)', 'Сканируются только индексы, подпадающие под одно из разрешающих выражений. (.* для всех)')}
                                        </div>
                                    </>
                                )}
                            </>
                        )}

                        {activeTab === 'pdn_parsers' && (
                            <>
                                {loadingSettings || !globalSettings ? (
                                    <div className="text-slate-500 text-sm">Загрузка настроек...</div>
                                ) : (
                                    <div className="space-y-6">
                                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                                            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                                                <h3 className="font-semibold text-slate-800 flex items-center">
                                                    Словари и списки парсеров
                                                </h3>
                                            </div>
                                            <div className="border-b border-slate-200 bg-slate-100/50 px-6 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Email-парсинг</div>
                                            {renderDictionaryList('mail_service_names', 'Почтовые домены', 'Популярные почтовые сервисы, которые всегда считаются валидным Email.')}
                                            {renderDictionaryList('unknown_mail_service_parts', 'Неизвестные домены', 'Используются только для логгирования или аналитики. Заполняются самим сканером.')}

                                            <div className="border-b border-slate-200 bg-slate-100/50 px-6 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Парсинг банковских карт</div>
                                            {renderDictionaryList('card_bank_bins_4', 'Банковские БИНы (4 цифры)', 'Уникальные 4-х значные начала карт, подтверждающие, что это РФ БИНы.')}

                                            <div className="border-b border-slate-200 bg-slate-100/50 px-6 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Парсинг телефонов</div>
                                            {renderDictionaryList('invalid_def_codes', 'Невалидные DEF-коды', 'Коды операторов, которые не используются настоящими абонентами в РФ (исключаются).')}

                                            <div className="border-b border-slate-200 bg-slate-100/50 px-6 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Парсинг ФИО</div>
                                            {renderDictionaryList('surn_ends_cis', 'Окончания фамилий (СНГ)', 'Типичные окончания фамилий СНГ для детекции ФИО.')}
                                            {renderDictionaryList('surn_ends_world', 'Окончания фамилий (Мир)', 'Западные/европейские окончания фамилий.')}
                                            {renderDictionaryList('patron_ends', 'Окончания отчеств', 'Маркеры, подтверждающие наличие отчества.')}
                                            {renderDictionaryList('fio_special_markers', 'Спец. маркеры ФИО', 'Частицы типа оглы, кызы, фон, де.')}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}

                        {activeTab === 'pdn_regex' && (
                            <PdnRegexList />
                        )}

                        {activeTab === 'global_exclusions' && (
                            <GlobalExceptions />
                        )}

                        {activeTab === 'index_exclusions' && (
                            <IndexExceptions />
                        )}

                        {activeTab === 'statuses' && (
                            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                                <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50">
                                    <h3 className="font-semibold text-slate-800">Настройка статусов</h3>
                                    <p className="text-xs text-slate-500 mt-1">Задайте цвета для различных типов статусов кэш-ключей</p>
                                </div>
                                <div className="p-6">
                                    <div className="space-y-4">
                                        {statuses.map((status, idx) => (
                                            <div key={status.id} className="flex items-center space-x-4">
                                                <div className="w-32 text-sm font-medium text-slate-700">{status.label}</div>
                                                <input
                                                    type="color"
                                                    value={status.color}
                                                    onChange={(e) => {
                                                        const newStatuses = [...statuses];
                                                        newStatuses[idx].color = e.target.value;
                                                        setStatuses(newStatuses);
                                                    }}
                                                    className="w-10 h-10 rounded cursor-pointer border-0 p-0"
                                                />
                                                <div className="text-xs text-slate-400 font-mono uppercase">{status.color}</div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="mt-6 pt-4 border-t border-slate-100">
                                        <button className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md shadow-sm">
                                            Сохранить цвета
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {activeTab === 'tags' && (
                            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                                <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50">
                                    <h3 className="font-semibold text-slate-800">Глобальное управление тегами</h3>
                                    <p className="text-xs text-slate-500 mt-1">Здесь вы можете посмотреть все используемые теги и удалить их у **всех** кэш-ключей сразу.</p>
                                </div>
                                <div className="p-6">
                                    <div className="flex flex-wrap gap-3">
                                        {tags.map(tag => (
                                            <div key={tag} className="flex items-center bg-slate-100 border border-slate-200 rounded-md px-3 py-1.5">
                                                <span className="text-sm font-medium text-slate-700 mr-2">#{tag}</span>
                                                <button
                                                    onClick={() => handleDeleteTag(tag)}
                                                    className="text-slate-400 hover:text-red-500 transition-colors"
                                                    title="Удалить глобально"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                    </div>
                </div>
            </div>

            {/* Read-Only Модалка */}
            {viewModal.isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
                        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                            <h3 className="text-lg font-semibold text-slate-800">Просмотр: {viewModal.title}</h3>
                            <button onClick={() => setViewModal({ ...viewModal, isOpen: false })} className="text-slate-400 hover:text-slate-600">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto">
                            {viewModal.items.length === 0 ? (
                                <p className="text-center text-slate-500 italic py-8">Пусто</p>
                            ) : (
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                                    {viewModal.items.map((item, idx) => (
                                        <div key={idx} className="bg-slate-50 border border-slate-200 text-slate-700 rounded px-2 py-1 text-sm font-mono text-center truncate">
                                            {item}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end">
                            <button
                                onClick={() => setViewModal({ ...viewModal, isOpen: false })}
                                className="px-4 py-2 bg-white border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
                            >
                                Закрыть
                            </button>
                        </div>
                    </div>
                </div>
            )}

        </div >
    );
}
