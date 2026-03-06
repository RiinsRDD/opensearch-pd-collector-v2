import React from 'react';

const Settings: React.FC = () => {
    return (
        <div className="p-8">
            <h1 className="text-2xl font-bold text-slate-900 mb-6">Settings</h1>
            <div className="max-w-4xl bg-white rounded-lg border border-slate-200 shadow-sm p-6">
                <p className="text-slate-600">System configuration options will appear here.</p>
            </div>
        </div>
    );
};

export default Settings;
