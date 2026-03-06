import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, LayoutDashboard, History, Settings, Bell, User } from 'lucide-react';
import { useSelection } from '../../context/SelectionContext';
import clsx from 'clsx';

const Header: React.FC = () => {
    const { selectedPatterns, selectedIndexPattern } = useSelection();
    const location = useLocation();

    const isJiraEnabled = selectedPatterns.length > 0 || selectedIndexPattern !== null;

    const navItems = [
        { label: 'Scanner', path: '/', icon: LayoutDashboard },
        { label: 'Tasks', path: '/tasks', icon: History },
    ];

    return (
        <header className="h-14 bg-slate-900 text-white flex items-center px-4 justify-between border-b border-white/10 shrink-0">
            <div className="flex items-center gap-6">
                <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                    <Shield className="w-6 h-6 text-blue-400" />
                    <span className="font-bold text-lg tracking-tight">PDN Collector</span>
                </Link>

                <nav className="flex items-center gap-1">
                    {navItems.map((item) => (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={clsx(
                                "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                                location.pathname === item.path
                                    ? "bg-white/10 text-white"
                                    : "text-slate-400 hover:text-white hover:bg-white/5"
                            )}
                        >
                            <item.icon className="w-4 h-4" />
                            {item.label}
                        </Link>
                    ))}
                </nav>
            </div>

            <div className="flex items-center gap-4">
                {/* Search placeholder */}
                <div className="relative hidden md:block">
                    <input
                        type="text"
                        placeholder="Search hash or index..."
                        className="w-64 bg-slate-800 border border-slate-700 rounded-md py-1.5 px-3 text-xs focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder:text-slate-500"
                    />
                </div>

                <button
                    disabled={!isJiraEnabled}
                    className={clsx(
                        "px-4 py-1.5 rounded-md text-xs font-semibold transition-all",
                        isJiraEnabled
                            ? "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/40"
                            : "bg-slate-800 text-slate-500 cursor-not-allowed"
                    )}
                >
                    To Jira {selectedPatterns.length > 0 && `(${selectedPatterns.length})`}
                </button>

                <div className="flex items-center gap-3 border-l border-white/10 pl-4 ml-2 text-slate-400">
                    <button className="hover:text-white transition-colors relative">
                        <Bell className="w-5 h-5" />
                        <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full border-2 border-slate-900"></span>
                    </button>

                    <div className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
                        <Link to="/settings" className={clsx(location.pathname === '/settings' ? "text-white" : "text-slate-400 hover:text-white")}>
                            <Settings className="w-5 h-5" />
                        </Link>
                        <User className="w-5 h-5" />
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
