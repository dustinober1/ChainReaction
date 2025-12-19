"use client";

import { useState, useEffect } from "react";

interface NotificationsPanelProps {
    isOpen: boolean;
    onClose: () => void;
    alerts: Array<{
        id: string;
        severity: "critical" | "high" | "medium" | "low";
        title: string;
        description: string;
        timestamp: Date;
        acknowledged: boolean;
    }>;
    onAcknowledge: (alertId: string) => void;
    onAcknowledgeAll: () => void;
}

export default function NotificationsPanel({
    isOpen,
    onClose,
    alerts,
    onAcknowledge,
    onAcknowledgeAll,
}: NotificationsPanelProps) {
    const [mounted, setMounted] = useState(false);
    const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;

    useEffect(() => {
        setMounted(true);
    }, []);

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

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case "critical":
                return "bg-red-500";
            case "high":
                return "bg-orange-500";
            case "medium":
                return "bg-amber-500";
            case "low":
                return "bg-blue-500";
            default:
                return "bg-gray-500";
        }
    };

    const formatTime = (date: Date) => {
        if (!mounted) return "";
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (minutes < 1) return "Just now";
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return `${days}d ago`;
    };

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 z-50"
                onClick={onClose}
            />

            {/* Panel */}
            <div className="fixed top-16 right-4 w-96 max-h-[80vh] bg-gray-900 border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                    <div className="flex items-center gap-2">
                        <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                        </svg>
                        <h2 className="text-lg font-semibold text-white">Notifications</h2>
                        {unacknowledgedCount > 0 && (
                            <span className="px-2 py-0.5 text-xs font-medium bg-red-500/20 text-red-400 rounded-full">
                                {unacknowledgedCount}
                            </span>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Actions */}
                {unacknowledgedCount > 0 && (
                    <div className="px-4 py-2 border-b border-white/10 flex justify-between items-center">
                        <span className="text-xs text-gray-400">
                            {unacknowledgedCount} unread notification{unacknowledgedCount !== 1 ? "s" : ""}
                        </span>
                        <button
                            onClick={onAcknowledgeAll}
                            className="text-xs text-blue-400 hover:text-blue-300 transition"
                        >
                            Mark all as read
                        </button>
                    </div>
                )}

                {/* Notifications List */}
                <div className="overflow-y-auto max-h-[60vh]">
                    {alerts.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                            <svg className="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                            </svg>
                            <p className="text-sm">No notifications</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-white/5">
                            {alerts.map((alert) => (
                                <div
                                    key={alert.id}
                                    className={`p-4 hover:bg-white/5 transition cursor-pointer ${alert.acknowledged ? "opacity-50" : ""
                                        }`}
                                >
                                    <div className="flex gap-3">
                                        <div className={`w-2 h-2 mt-2 rounded-full ${getSeverityColor(alert.severity)}`} />
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between gap-2">
                                                <h3 className="text-sm font-medium text-white truncate">
                                                    {alert.title}
                                                </h3>
                                                <span className="text-xs text-gray-500 whitespace-nowrap">
                                                    {formatTime(alert.timestamp)}
                                                </span>
                                            </div>
                                            <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                                                {alert.description}
                                            </p>
                                            {!alert.acknowledged && (
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        onAcknowledge(alert.id);
                                                    }}
                                                    className="mt-2 text-xs text-blue-400 hover:text-blue-300 transition"
                                                >
                                                    Mark as read
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}
