"use client";

import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar } from 'recharts';

const riskHistory = [
    { month: 'Jan', risk: 45 },
    { month: 'Feb', risk: 52 },
    { month: 'Mar', risk: 48 },
    { month: 'Apr', risk: 70 }, // Event starts
    { month: 'May', risk: 65 },
    { month: 'Jun', risk: 58 },
];

const riskByCategory = [
    { category: 'Geopolitical', value: 30 },
    { category: 'Weather', value: 85 }, // High due to typhoon
    { category: 'Logistics', value: 45 },
    { category: 'Financial', value: 20 },
    { category: 'Cyber', value: 15 },
];

export default function AnalyticsPanel() {
    return (
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4 h-full overflow-y-auto">
            <div className="bg-gray-800/50 p-4 rounded-xl border border-white/10">
                <h3 className="text-sm font-bold text-gray-300 mb-4">Historical Risk Trends (6 Months)</h3>
                <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={riskHistory}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="month" stroke="#9ca3af" />
                            <YAxis stroke="#9ca3af" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                                itemStyle={{ color: '#f3f4f6' }}
                            />
                            <Line type="monotone" dataKey="risk" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="bg-gray-800/50 p-4 rounded-xl border border-white/10">
                <h3 className="text-sm font-bold text-gray-300 mb-4">Risk Distribution by Category</h3>
                <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={riskByCategory}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="category" stroke="#9ca3af" />
                            <YAxis stroke="#9ca3af" />
                            <Tooltip
                                cursor={{ fill: '#374151', opacity: 0.5 }}
                                contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                            />
                            <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="bg-gray-800/50 p-4 rounded-xl border border-white/10 md:col-span-2">
                <h3 className="text-sm font-bold text-gray-300 mb-4">Key Risk Indicators</h3>
                <div className="grid grid-cols-4 gap-4">
                    <div className="bg-gray-900/50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-red-500">+15%</div>
                        <div className="text-xs text-gray-500">Risk Velocity (MoM)</div>
                    </div>
                    <div className="bg-gray-900/50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-amber-500">$2.4M</div>
                        <div className="text-xs text-gray-500">Value at Risk (VaR)</div>
                    </div>
                    <div className="bg-gray-900/50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-blue-500">12h</div>
                        <div className="text-xs text-gray-500">Avg. Response Time</div>
                    </div>
                    <div className="bg-gray-900/50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-emerald-500">94%</div>
                        <div className="text-xs text-gray-500">Resilience Score</div>
                    </div>
                </div>
            </div>
        </div>
    );
}
