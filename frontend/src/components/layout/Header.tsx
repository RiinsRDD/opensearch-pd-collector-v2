import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Bell, Search, Settings, CheckSquare, ChevronDown, Database, X, LogOut } from 'lucide-react';
import { useSelection } from '../../context/SelectionContext';
import { useAuth } from '../../context/AuthContext';
import { indicesApi } from '../../api/client';
import { canCreateJira } from '../../utils/rbac';
import type { PDNPattern } from '../../types/api';

export default function Header() {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isJiraModalOpen, setIsJiraModalOpen] = useState(false);
    const [jiraComment, setJiraComment] = useState('');
    const { selectedPatterns, selectedIndexPattern, setSelectedPatterns } = useSelection();
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    // Кнопка активна если выделен хотя бы один пример ИЛИ если выбран индекс целиком в дереве (selectedIndexPattern)
    const hasSelection = selectedPatterns.length > 0 || selectedIndexPattern !== null;
    // Для Jira берутся только confirmed
    const confirmedCount = selectedPatterns.filter(p => p.status === 'confirmed').length;
    // Заводить задачу в Jira могут только analyst и admin
    const showJiraButton = canCreateJira(user?.role);

    const handleCreateJiraTask = async () => {
        const cacheKeys = selectedPatterns.filter(p => p.status === 'confirmed').map(p => p.cache_key);
        if (cacheKeys.length === 0) {
            alert('Нет confirmed паттернов для создания задачи');
            return;
        }
        try {
            await indicesApi.createJiraTasks({ cache_keys: cacheKeys, custom_message: jiraComment });
            setIsJiraModalOpen(false);
            setJiraComment('');
            // Обновить дерево через перезагрузку контекста (has_jira_task = true)
            const updated = selectedPatterns.map((p: PDNPattern) => cacheKeys.includes(p.cache_key) ? ({ ...p, has_jira_task: true } as PDNPattern) : p);
            setSelectedPatterns(updated);
        } catch (error) {
            console.error('Failed to create Jira task:', error);
            alert('Ошибка при создании задачи в Jira');
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const getRoleLabel = (role: string) => {
        switch (role) {
            case 'admin': return 'Администратор';
            case 'analyst': return 'Аналитик';
            case 'viewer': return 'Наблюдатель';
            default: return role;
        }
    };

    const getRoleColor = (role: string) => {
        switch (role) {
            case 'admin': return 'bg-red-500/20 text-red-400 border-red-500/30';
            case 'analyst': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
            case 'viewer': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
            default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
        }
    };

    return (
        <header className="h-14 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 shrink-0 shadow-sm z-20 text-slate-200">
            <div className="flex items-center space-x-6">
                <NavLink to="/" className="flex items-center space-x-2">
                    <Database className="w-5 h-5 text-blue-400" />
                    <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                        PDN Collector
                    </h1>
                </NavLink>

                {/* Верхнее меню вместо сайдбара */}
                <nav className="hidden md:flex items-center space-x-1">
                    <NavLink to="/" className={({ isActive }) => `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}>
                        Сканер
                    </NavLink>
                    <NavLink to="/tasks" className={({ isActive }) => `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}>
                        Задачи
                    </NavLink>
                </nav>
            </div>

            <div className="flex items-center space-x-3">
                {/* Глобальная кнопка заведения задачи — только для analyst/admin */}
                {showJiraButton && (
                <button
                    disabled={!hasSelection}
                    onClick={() => setIsJiraModalOpen(true)}
                    className="disabled:opacity-50 disabled:cursor-not-allowed group relative px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-md shadow-sm transition-colors hidden md:block mr-2"
                >
                    Завести задачу в Jira
                    {confirmedCount > 0 && <span className="ml-1.5 bg-indigo-500 px-1.5 rounded-full text-xs">{confirmedCount}</span>}

                    {!hasSelection && (
                        <span className="hidden group-hover:block absolute top-[110%] left-1/2 -translate-x-1/2 w-48 bg-slate-800 text-xs text-white p-2 rounded shadow-lg z-50 pointer-events-none">
                            Выберите Индекс или отметьте чекбоксы примеров
                        </span>
                    )}
                </button>
                )}
                <div className="relative hidden md:block group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-4 w-4 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                    </div>
                    <input
                        type="text"
                        className="block w-64 pl-9 pr-3 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all"
                        placeholder="Поиск по хэшам или индексам..."
                    />
                </div>

                <button className="p-1.5 text-slate-400 hover:text-slate-200 rounded-md transition-colors relative">
                    <Bell className="h-5 w-5" />
                    <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-red-500 border-2 border-slate-900"></span>
                </button>

                {/* Выпадающее меню настроек профиля */}
                <div className="relative">
                    <button
                        onClick={() => setIsMenuOpen(!isMenuOpen)}
                        className="flex items-center space-x-2 p-1.5 hover:bg-slate-800 rounded-md transition-colors"
                    >
                        <div className={`w-7 h-7 rounded-sm flex items-center justify-center text-sm font-bold border ${getRoleColor(user?.role || 'viewer')}`}>
                            {user?.username?.charAt(0).toUpperCase() || 'A'}
                        </div>
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                    </button>

                    {isMenuOpen && user && (
                        <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 border border-slate-200 text-slate-700 z-50">
                            <div className="px-4 py-2 border-b border-slate-100">
                                <p className="text-sm font-medium text-slate-900">{user.username}</p>
                                <p className="text-xs text-slate-500">{getRoleLabel(user.role)}</p>
                            </div>
                            <NavLink to="/settings" onClick={() => setIsMenuOpen(false)} className="flex items-center px-4 py-2 text-sm hover:bg-slate-50 hover:text-blue-600">
                                <Settings className="w-4 h-4 mr-2" /> Настройки системы
                            </NavLink>
                            <NavLink to="/tasks" onClick={() => setIsMenuOpen(false)} className="flex items-center px-4 py-2 text-sm hover:bg-slate-50 hover:text-blue-600">
                                <CheckSquare className="w-4 h-4 mr-2" /> Мои Задачи Jira
                            </NavLink>
                            <div className="border-t border-slate-100 my-1"></div>
                            <button onClick={handleLogout} className="flex items-center px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left">
                                <LogOut className="w-4 h-4 mr-2" /> Выйти
                            </button>
                        </div>
                    )}
                </div>

                {/* Jira Modal */}
                {isJiraModalOpen && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setIsJiraModalOpen(false)}>
                        <div className="bg-white rounded-lg p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-semibold">Создать задачу в Jira</h3>
                                <button onClick={() => setIsJiraModalOpen(false)} className="text-slate-400 hover:text-slate-600 transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            <p className="text-sm text-slate-600 mb-4">
                                Выбрано паттернов: {selectedPatterns.length} ({confirmedCount} confirmed)
                            </p>
                            <textarea
                                value={jiraComment}
                                onChange={e => setJiraComment(e.target.value)}
                                placeholder="Дополнительный комментарий к задаче..."
                                className="w-full p-3 border border-slate-300 rounded mb-4"
                                rows={4}
                            />
                            <div className="flex justify-end space-x-3">
                                <button onClick={() => setIsJiraModalOpen(false)} className="px-4 py-2 border border-slate-300 rounded hover:bg-slate-50 transition-colors">Отмена</button>
                                <button
                                    onClick={handleCreateJiraTask}
                                    className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors"
                                >
                                    Создать задачу
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </header>
    );
}