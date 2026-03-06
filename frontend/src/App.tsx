import { Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/layout/Header';
import ScannerStatusBar from './components/layout/ScannerStatusBar';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Tasks from './pages/Tasks';

function App() {
  return (
    <div className="flex flex-col h-screen bg-slate-50 text-slate-900 overflow-hidden">
      <Header />

      <main className="flex-1 overflow-auto">
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

export default App;
