import { useState } from 'react';
import { X, Search, Clock, FileDigit } from 'lucide-react';

interface SingleScanModalProps {
    indexName: string;
    onClose: () => void;
    onStartScan: (params: any) => void;
}

export default function SingleScanModal({ indexName, onClose, onStartScan }: SingleScanModalProps) {
    const [timeframe, setTimeframe] = useState('24');
    const [maxDocs, setMaxDocs] = useState('10000');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onStartScan({
            indexPattern: indexName,
            hours: parseInt(timeframe, 10),
            maxDocs: parseInt(maxDocs, 10)
        });
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-md flex flex-col overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                    <div className="flex items-center text-slate-800 font-medium">
                        <Search className="w-5 h-5 mr-2 text-indigo-500" />
                        Одиночное сканирование (Single Scan)
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-5 space-y-4">
                    <div className="mb-4">
                        <p className="text-sm text-slate-600">
                            Запуск принудительного сканирования для индекса <span className="font-mono bg-slate-100 px-1 py-0.5 rounded text-slate-800">{indexName}</span>
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center">
                            <Clock className="w-4 h-4 mr-1.5 text-slate-500" />
                            Глубина поиска (часы)
                        </label>
                        <input
                            type="number"
                            min="1"
                            max="720"
                            value={timeframe}
                            onChange={(e) => setTimeframe(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                            required
                        />
                        <p className="mt-1 text-xs text-slate-500">За какой период в прошлое искать (от 1 до 720 часов).</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center">
                            <FileDigit className="w-4 h-4 mr-1.5 text-slate-500" />
                            Лимит документов
                        </label>
                        <input
                            type="number"
                            min="100"
                            max="1000000"
                            step="100"
                            value={maxDocs}
                            onChange={(e) => setMaxDocs(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                            required
                        />
                        <p className="mt-1 text-xs text-slate-500">Максимальное количество анализируемых логов.</p>
                    </div>

                    <div className="pt-4 flex justify-end space-x-3 border-t border-slate-100 mt-6">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 border border-slate-300 text-slate-700 rounded-md text-sm font-medium hover:bg-slate-50 transition-colors"
                        >
                            Отмена
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors shadow-sm"
                        >
                            Запустить сканирование
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
