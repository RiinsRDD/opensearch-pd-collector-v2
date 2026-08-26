import { useState, useEffect } from 'react';
import { X, Terminal } from 'lucide-react';
import { scannerApi } from '../../api/client';

interface ScannerLog {
    id: number;
    scan_type: string;
    target_index: string | null;
    status: string;
    findings_count: number;
    started_at: string | null;
    duration_seconds: number | null;
    details: string;
}

interface ScannerLogsModalProps {
    onClose: () => void;
}

export default function ScannerLogsModal({ onClose }: ScannerLogsModalProps) {
    const [logs, setLogs] = useState<ScannerLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const loadLogs = async () => {
            try {
                const data = await scannerApi.getLogs(50);
                setLogs(data);
            } catch (error) {
                console.error('Failed to load scanner logs:', error);
            } finally {
                setIsLoading(false);
            }
        };
        loadLogs();
    }, []);

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '—';
        return new Date(dateStr).toLocaleString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const formatDuration = (seconds: number | null) => {
        if (!seconds) return '—';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}м ${secs}с`;
    };

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
                    {isLoading ? (
                        <div className="flex items-center justify-center h-full text-slate-500">
                            <Terminal className="w-5 h-5 mr-2 animate-spin" />
                            Загрузка логов...
                        </div>
                    ) : logs.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-slate-500">
                            <Terminal className="w-5 h-5 mr-2" />
                            Логов нет
                        </div>
                    ) : (
                        logs.map(log => (
                            <div key={log.id} className="bg-slate-950 border border-slate-800 rounded-md overflow-hidden">
                                <div className="px-4 py-2 bg-slate-800/50 border-b border-slate-800 flex justify-between items-center text-sm">
                                    <span className="text-slate-300 font-mono">{formatDate(log.started_at)}</span>
                                    <div className="flex items-center space-x-4">
                                        <span className="text-slate-400">Длительность: {formatDuration(log.duration_seconds)}</span>
                                        <span className={log.status === 'success' ? 'text-emerald-400' : log.status === 'failed' ? 'text-red-400' : 'text-amber-400'}>
                                            {log.status === 'success' ? 'Success' : log.status === 'failed' ? 'Error' : log.status}
                                        </span>
                                    </div>
                                </div>
                                <div className="p-4 text-slate-300 font-mono text-xs whitespace-pre-wrap max-h-[200px] overflow-y-auto">
                                    {log.details || '—'}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}