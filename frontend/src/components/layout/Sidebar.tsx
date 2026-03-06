import { NavLink } from 'react-router-dom';
import { Database, Settings, CheckSquare, Activity } from 'lucide-react';

export default function Sidebar() {
    const navItems = [
        { label: 'Дерево индексов', icon: Database, path: '/' },
        { label: 'Статистика сканера', icon: Activity, path: '/scanner' },
        { label: 'Задачи Jira', icon: CheckSquare, path: '/tasks' },
        { label: 'Настройки', icon: Settings, path: '/settings' },
    ];

    return (
        <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col hidden md:flex text-slate-300 transition-all duration-300">
            <div className="h-16 flex items-center px-6 border-b border-slate-800 bg-slate-950">
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                    PDN Collector
                </h1>
            </div>

            <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) =>
                            `flex items-center px-3 py-2.5 rounded-lg transition-all duration-200 group ${isActive
                                ? 'bg-primary-600/20 text-blue-400 font-medium'
                                : 'hover:bg-slate-800/50 hover:text-slate-100'
                            }`
                        }
                    >
                        <item.icon className="w-5 h-5 mr-3 shrink-0 opacity-80 group-hover:opacity-100" />
                        <span className="text-sm tracking-wide">{item.label}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="p-4 border-t border-slate-800 bg-slate-900/50">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold border border-indigo-500/30">
                        A
                    </div>
                    <div className="flex flex-col">
                        <span className="text-xs font-semibold text-slate-200">Admin User</span>
                        <span className="text-[10px] text-slate-500">Security Analyst</span>
                    </div>
                </div>
            </div>
        </aside>
    );
}
