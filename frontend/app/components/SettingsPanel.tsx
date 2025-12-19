"use client";

import { useState, useEffect } from "react";

interface SettingsPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

interface Settings {
    llmProvider: "openai" | "ollama";
    ollamaModel: string;
    monitorInterval: number;
    confidenceThreshold: number;
    enableNotifications: boolean;
    soundAlerts: boolean;
    darkMode: boolean;
}

export default function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
    const [settings, setSettings] = useState<Settings>({
        llmProvider: "ollama",
        ollamaModel: "qwen3:1.7b",
        monitorInterval: 300,
        confidenceThreshold: 0.7,
        enableNotifications: true,
        soundAlerts: false,
        darkMode: true,
    });
    const [activeTab, setActiveTab] = useState<"general" | "llm" | "notifications">("general");
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        if (isOpen) {
            document.addEventListener("keydown", handleEscape);
        }
        return () => document.removeEventListener("keydown", handleEscape);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const handleSave = () => {
        // In a real app, this would save to localStorage or API
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
    };

    const tabs = [
        { id: "general" as const, label: "General", icon: "⚙️" },
        { id: "llm" as const, label: "LLM", icon: "🤖" },
        { id: "notifications" as const, label: "Notifications", icon: "🔔" },
    ];

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 z-50"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
                <div className="w-full max-w-2xl bg-gray-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
                        <div className="flex items-center gap-3">
                            <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            <h2 className="text-xl font-semibold text-white">Settings</h2>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    <div className="flex">
                        {/* Sidebar */}
                        <div className="w-48 border-r border-white/10 p-2">
                            {tabs.map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`w-full px-3 py-2 text-left rounded-lg transition flex items-center gap-2 ${activeTab === tab.id
                                            ? "bg-blue-500/20 text-blue-400"
                                            : "text-gray-400 hover:text-white hover:bg-white/5"
                                        }`}
                                >
                                    <span>{tab.icon}</span>
                                    <span className="text-sm">{tab.label}</span>
                                </button>
                            ))}
                        </div>

                        {/* Content */}
                        <div className="flex-1 p-6">
                            {activeTab === "general" && (
                                <div className="space-y-6">
                                    <div>
                                        <h3 className="text-lg font-medium text-white mb-4">General Settings</h3>

                                        <div className="space-y-4">
                                            <div>
                                                <label className="block text-sm text-gray-400 mb-2">
                                                    Monitor Interval (seconds)
                                                </label>
                                                <input
                                                    type="number"
                                                    value={settings.monitorInterval}
                                                    onChange={(e) => setSettings({ ...settings, monitorInterval: parseInt(e.target.value) })}
                                                    min={60}
                                                    max={3600}
                                                    className="w-full bg-gray-800 border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                />
                                                <p className="mt-1 text-xs text-gray-500">How often to check for new risks (60-3600)</p>
                                            </div>

                                            <div>
                                                <label className="block text-sm text-gray-400 mb-2">
                                                    Confidence Threshold
                                                </label>
                                                <div className="flex items-center gap-3">
                                                    <input
                                                        type="range"
                                                        value={settings.confidenceThreshold}
                                                        onChange={(e) => setSettings({ ...settings, confidenceThreshold: parseFloat(e.target.value) })}
                                                        min={0}
                                                        max={1}
                                                        step={0.1}
                                                        className="flex-1"
                                                    />
                                                    <span className="text-white w-12 text-right">{Math.round(settings.confidenceThreshold * 100)}%</span>
                                                </div>
                                                <p className="mt-1 text-xs text-gray-500">Minimum confidence for risk detection</p>
                                            </div>

                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <div className="text-sm text-white">Dark Mode</div>
                                                    <div className="text-xs text-gray-500">Always enabled for this UI</div>
                                                </div>
                                                <button
                                                    className={`relative w-12 h-6 rounded-full transition ${settings.darkMode ? "bg-blue-500" : "bg-gray-600"
                                                        }`}
                                                    onClick={() => setSettings({ ...settings, darkMode: !settings.darkMode })}
                                                >
                                                    <div
                                                        className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${settings.darkMode ? "translate-x-7" : "translate-x-1"
                                                            }`}
                                                    />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {activeTab === "llm" && (
                                <div className="space-y-6">
                                    <h3 className="text-lg font-medium text-white mb-4">LLM Configuration</h3>

                                    <div className="space-y-4">
                                        <div>
                                            <label className="block text-sm text-gray-400 mb-2">
                                                LLM Provider
                                            </label>
                                            <div className="flex gap-3">
                                                <button
                                                    onClick={() => setSettings({ ...settings, llmProvider: "ollama" })}
                                                    className={`flex-1 px-4 py-3 rounded-lg border transition ${settings.llmProvider === "ollama"
                                                            ? "border-blue-500 bg-blue-500/10 text-blue-400"
                                                            : "border-white/10 text-gray-400 hover:border-white/20"
                                                        }`}
                                                >
                                                    <div className="text-2xl mb-1">🦙</div>
                                                    <div className="text-sm font-medium">Ollama</div>
                                                    <div className="text-xs opacity-70">Local LLM</div>
                                                </button>
                                                <button
                                                    onClick={() => setSettings({ ...settings, llmProvider: "openai" })}
                                                    className={`flex-1 px-4 py-3 rounded-lg border transition ${settings.llmProvider === "openai"
                                                            ? "border-blue-500 bg-blue-500/10 text-blue-400"
                                                            : "border-white/10 text-gray-400 hover:border-white/20"
                                                        }`}
                                                >
                                                    <div className="text-2xl mb-1">🤖</div>
                                                    <div className="text-sm font-medium">OpenAI</div>
                                                    <div className="text-xs opacity-70">Cloud API</div>
                                                </button>
                                            </div>
                                        </div>

                                        {settings.llmProvider === "ollama" && (
                                            <div>
                                                <label className="block text-sm text-gray-400 mb-2">
                                                    Ollama Model
                                                </label>
                                                <select
                                                    value={settings.ollamaModel}
                                                    onChange={(e) => setSettings({ ...settings, ollamaModel: e.target.value })}
                                                    className="w-full bg-gray-800 border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                >
                                                    <option value="qwen3:1.7b">qwen3:1.7b (Fast)</option>
                                                    <option value="llama3.2">llama3.2 (Balanced)</option>
                                                    <option value="llama3.1">llama3.1 (Quality)</option>
                                                    <option value="mistral">mistral (Capable)</option>
                                                    <option value="mixtral">mixtral (Best)</option>
                                                </select>
                                            </div>
                                        )}

                                        <div className="p-4 bg-gray-800/50 rounded-lg border border-white/5">
                                            <div className="flex items-start gap-3">
                                                <div className="text-blue-400 text-xl">💡</div>
                                                <div>
                                                    <div className="text-sm text-white font-medium">Tip</div>
                                                    <div className="text-xs text-gray-400 mt-1">
                                                        {settings.llmProvider === "ollama"
                                                            ? "Make sure Ollama is running locally on port 11434. Run 'ollama serve' if not started."
                                                            : "Ensure OPENAI_API_KEY is set in your .env file for OpenAI to work."
                                                        }
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {activeTab === "notifications" && (
                                <div className="space-y-6">
                                    <h3 className="text-lg font-medium text-white mb-4">Notification Settings</h3>

                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <div className="text-sm text-white">Enable Notifications</div>
                                                <div className="text-xs text-gray-500">Show browser notifications for new alerts</div>
                                            </div>
                                            <button
                                                className={`relative w-12 h-6 rounded-full transition ${settings.enableNotifications ? "bg-blue-500" : "bg-gray-600"
                                                    }`}
                                                onClick={() => setSettings({ ...settings, enableNotifications: !settings.enableNotifications })}
                                            >
                                                <div
                                                    className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${settings.enableNotifications ? "translate-x-7" : "translate-x-1"
                                                        }`}
                                                />
                                            </button>
                                        </div>

                                        <div className="flex items-center justify-between">
                                            <div>
                                                <div className="text-sm text-white">Sound Alerts</div>
                                                <div className="text-xs text-gray-500">Play sound for critical alerts</div>
                                            </div>
                                            <button
                                                className={`relative w-12 h-6 rounded-full transition ${settings.soundAlerts ? "bg-blue-500" : "bg-gray-600"
                                                    }`}
                                                onClick={() => setSettings({ ...settings, soundAlerts: !settings.soundAlerts })}
                                            >
                                                <div
                                                    className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${settings.soundAlerts ? "translate-x-7" : "translate-x-1"
                                                        }`}
                                                />
                                            </button>
                                        </div>

                                        <div className="pt-4 border-t border-white/10">
                                            <h4 className="text-sm font-medium text-white mb-3">Notification Types</h4>
                                            <div className="space-y-2 text-sm">
                                                <div className="flex items-center gap-2 text-gray-400">
                                                    <div className="w-3 h-3 rounded-full bg-red-500" />
                                                    <span>Critical - Always notify</span>
                                                </div>
                                                <div className="flex items-center gap-2 text-gray-400">
                                                    <div className="w-3 h-3 rounded-full bg-orange-500" />
                                                    <span>High - Notify when enabled</span>
                                                </div>
                                                <div className="flex items-center gap-2 text-gray-400">
                                                    <div className="w-3 h-3 rounded-full bg-amber-500" />
                                                    <span>Medium - Silent notification</span>
                                                </div>
                                                <div className="flex items-center gap-2 text-gray-400">
                                                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                                                    <span>Low - In-app only</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between px-6 py-4 border-t border-white/10 bg-gray-900/50">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition"
                        >
                            Cancel
                        </button>
                        <div className="flex items-center gap-3">
                            {saved && (
                                <span className="text-sm text-green-400 flex items-center gap-1">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                    Saved!
                                </span>
                            )}
                            <button
                                onClick={handleSave}
                                className="px-4 py-2 text-sm font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition"
                            >
                                Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}
