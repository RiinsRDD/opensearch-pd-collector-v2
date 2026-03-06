import React from 'react';

const Tasks: React.FC = () => {
    return (
        <div className="p-8">
            <h1 className="text-2xl font-bold text-slate-900 mb-6">Jira Tasks</h1>
            <div className="max-w-6xl bg-white rounded-lg border border-slate-200 shadow-sm p-6">
                <p className="text-slate-600">Global task history and status tracking.</p>
            </div>
        </div>
    );
};

export default Tasks;
