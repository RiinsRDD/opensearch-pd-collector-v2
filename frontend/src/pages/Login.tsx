import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(username, password);
            navigate('/');
        } catch (err: unknown) {
            const error = err as { response?: { status?: number } };
            if (error.response?.status === 401) {
                setError('Неверное имя пользователя или пароль');
            } else if (error.response?.status === 403) {
                setError('Доступ запрещен');
            } else {
                setError('Ошибка подключения к серверу');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
            <div className="w-full max-w-md">
                <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-8">
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-indigo-100 mb-4">
                            <Database className="w-8 h-8 text-indigo-600" />
                        </div>
                        <h1 className="text-2xl font-bold text-slate-900">PDN Collector</h1>
                        <p className="text-slate-500 mt-1">Войдите в систему</p>
                    </div>

                    {error && (
                        <div className="mb-6 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-slate-700 mb-1.5">
                                Имя пользователя
                            </label>
                            <input
                                id="username"
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="w-full px-4 py-2.5 border border-slate-300 rounded-md text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
                                placeholder="admin"
                                required
                                autoFocus
                                disabled={loading}
                            />
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1.5">
                                Пароль
                            </label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full px-4 py-2.5 border border-slate-300 rounded-md text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
                                placeholder="••••••••"
                                required
                                disabled={loading}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                        >
                            {loading ? 'Вход...' : 'Войти'}
                        </button>
                    </form>

                    <div className="mt-6 text-center text-sm text-slate-500">
                        <p>Демо-аккаунты:</p>
                        <div className="mt-2 space-y-1 text-xs text-slate-400">
                            <div><code className="bg-slate-100 px-1.5 py-0.5 rounded">admin</code> / <code className="bg-slate-100 px-1.5 py-0.5 rounded">admin123</code></div>
                            <div><code className="bg-slate-100 px-1.5 py-0.5 rounded">analyst</code> / <code className="bg-slate-100 px-1.5 py-0.5 rounded">analyst123</code></div>
                            <div><code className="bg-slate-100 px-1.5 py-0.5 rounded">viewer</code> / <code className="bg-slate-100 px-1.5 py-0.5 rounded">viewer123</code></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}