import React from 'react';
import { Activity, Terminal } from 'lucide-react';

const ScannerStatusBar: React.FC = () => {
    return (
        <footer className="h-8 bg-slate-100 border-t border-slate-200 flex items-center px-4 justify-between text-[11px] font-medium text-slate-600 shrink-0">
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.4)]"></div>
                    <span>Scanner: IDLE</span>
                </div>
                <div className="h-3 w-px bg-slate-200"></div>
                <div className="flex items-center gap-1.5">
                    <Activity className="w-3 h-3 text-slate-400" />
                    <span>Last scan: 5 minutes ago</span>
                </div>
            </div>

            <button className="flex items-center gap-1.5 hover:text-slate-900 transition-colors group">
                <Terminal className="w-3 h-3 text-slate-400 group-hover:text-slate-900" />
                <span>Open Scanner Logs</span>
            </button>
        </footer>
    );
};

export default ScannerStatusBar;
