import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/layout/Header';
import ScannerStatusBar from './components/layout/ScannerStatusBar';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Tasks from './pages/Tasks';
import Login from './pages/Login';
import { SelectionProvider } from './context/SelectionContext';
import { AuthProvider, useAuth } from './context/AuthContext';

function ProtectedRoutes() {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-slate-50">
                <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    return (
        <div className="flex flex-col h-screen w-full bg-slate-50 overflow-hidden font-sans">
            <Header />
            <main className="flex-1 min-h-0">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="/tasks" element={<Tasks />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </main>
            <ScannerStatusBar />
        </div>
    );
}

export default function App() {
    return (
        <SelectionProvider>
            <AuthProvider>
                <BrowserRouter>
                    <Routes>
                        <Route path="/login" element={<Login />} />
                        <Route path="/*" element={<ProtectedRoutes />} />
                    </Routes>
                </BrowserRouter>
            </AuthProvider>
        </SelectionProvider>
    );
}
