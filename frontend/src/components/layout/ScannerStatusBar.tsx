import { useState, useEffect } from 'react';
import { Activity, Clock, Terminal } from 'lucide-react';
import ScannerLogsModal from '../modals/ScannerLogsModal';
import { scannerApi } from '../../api/client';

interface ScannerStatus {
    status: 'active' | 'idle';
    current_index_pattern: string | null;
    eta: string | null;
}

export default function ScannerStatusBar() {
    const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);
    const [status, setStatus] = useState<ScannerStatus>({ status: 'idle', current_index_pattern: null, eta: null });

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const data = await scannerApi.getStatus();
                setStatus(data);
            } catch (e) {
                console.error('Failed to fetch scanner status:', e);
            }
        };
        fetchStatus();
        const interval = setInterval(fetchStatus, 10000);
        return () => clearInterval(interval);
    }, []);

    const isScanning = status.status === 'active';

    return (
        <>
            <div
                onClick={() => setIsLogsModalOpen(true)}
                className="h-8 bg-slate-900 border-t border-slate-800 flex items-center px-4 shrink-0 shadow-sm z-20 text-slate-300 text-xs font-mono cursor-pointer hover:bg-slate-800 transition-colors justify-between"
            >
                <div className="flex items-center space-x-4">
                    {isScanning ? (
                        <>
                            <div className="flex items-center text-blue-400">
                                <Activity className="w-3.5 h-3.5 mr-1.5 animate-pulse" />
                                <span>Сканирование активно</span>
                            </div>
                            <div className="flex items-center text-emerald-400">
                                <span className="mr-2">Текущий паттерн:</span>
                                <span className="bg-slate-800 px-1.5 py-0.5 rounded text-emerald-300">
                                    {status.current_index_pattern || '—'}
                                </span>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="flex items-center text-slate-400">
                                <Activity className="w-3.5 h-3.5 mr-1.5" />
                                <span>Сканер в ожидании</span>
                            </div>
                            <div className="flex items-center text-slate-400">
                                <Clock className="w-3.5 h-3.5 mr-1.5" />
                                <span>Следующий запуск через: {status.eta || '—'}</span>
                            </div>
                        </>
                    )}
                </div>
                <div className="flex items-center text-slate-500 hover:text-slate-300 transition-colors">
                    <Terminal className="w-3.5 h-3.5 mr-1.5" />
                    <span>Посмотреть логи (последние 3)</span>
                </div>
            </div>

            {isLogsModalOpen && (
                <ScannerLogsModal onClose={() => setIsLogsModalOpen(false)} />
            )}
        </>
    );
}