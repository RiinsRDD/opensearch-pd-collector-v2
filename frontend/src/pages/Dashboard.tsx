import React from 'react';

const Dashboard: React.FC = () => {
    return (
        <div className="flex h-full">
            <div className="w-[350px] border-r border-slate-200 bg-white p-4">
                <h2 className="text-xl font-semibold mb-4 text-slate-900">Explorer</h2>
                <div className="text-slate-500 italic">IndicesTree placeholder</div>
            </div>
            <div className="flex-1 p-6 bg-slate-50">
                <h1 className="text-2xl font-bold text-slate-900 mb-4">Dashboard</h1>
                <p className="text-slate-600">Select an item from the tree to see details.</p>
            </div>
        </div>
    );
};

export default Dashboard;
