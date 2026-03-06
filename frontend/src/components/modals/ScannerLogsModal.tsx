import { X, Terminal } from 'lucide-react';

interface ScannerLogsModalProps {
    onClose: () => void;
}

export default function ScannerLogsModal({ onClose }: ScannerLogsModalProps) {
    // В будущем эти данные будут получены из API (/api/v1/scanner/logs)
    const mockLogs = [
        { id: 1, date: "2023-10-25 14:00", duration: "45m", status: "Success", details: "[INFO] Scan started...\n[INFO] Found 120 new hits in bcs-tech-logs-*\n[INFO] Completed." },
        { id: 2, date: "2023-10-24 14:00", duration: "42m", status: "Success", details: "[INFO] Scan started...\n[INFO] Found 55 new hits in bcs-career-*\n[INFO] Completed." },
        { id: 3, date: "2023-10-23 14:00", duration: "10m", status: "Error", details: "[INFO] Scan started...\n[ERROR] Connection timeout to OpenSearch." },
    ];

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-xl w-full max-w-4xl max-h-[80vh] flex flex-col overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-700 flex justify-between items-center bg-slate-800 shrink-0">
                    <div className="flex items-center text-slate-200 font-medium">
                        <Terminal className="w-5 h-5 mr-2 text-blue-400" />
                        Логи глобального сканера
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-200 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-5 space-y-6">
                    {mockLogs.map(log => (
                        <div key={log.id} className="bg-slate-950 border border-slate-800 rounded-md overflow-hidden">
                            <div className="px-4 py-2 bg-slate-800/50 border-b border-slate-800 flex justify-between items-center text-sm">
                                <span className="text-slate-300 font-mono">{log.date}</span>
                                <div className="flex items-center space-x-4">
                                    <span className="text-slate-400">Длительность: {log.duration}</span>
                                    <span className={log.status === 'Success' ? 'text-emerald-400' : 'text-red-400'}>
                                        {log.status}
                                    </span>
                                </div>
                            </div>
                            <div className="p-4 text-slate-300 font-mono text-xs whitespace-pre-wrap">
                                {log.details}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
