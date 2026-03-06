import { Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/layout/Header';
import ScannerStatusBar from './components/layout/ScannerStatusBar';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Tasks from './pages/Tasks';
import { SelectionProvider } from './context/SelectionContext';

export default function App() {
  return (
    <SelectionProvider>
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
    </SelectionProvider>
  );
}
