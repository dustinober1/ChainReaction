"use client";

import { useState, useEffect } from "react";

interface Alert {
    id: string;
    severity: "critical" | "high" | "medium" | "low";
    title: string;
    description: string;
    timestamp: Date;
    acknowledged: boolean;
}

interface AlertsPanelProps {
    alerts: Alert[];
    onAlertClick?: (alert: Alert) => void;
    onAcknowledge?: (alertId: string) => void;
}

// Separate component for relative time to isolate hydration
function RelativeTime({ date }: { date: Date }) {
    const [timeText, setTimeText] = useState<string>("");

    useEffect(() => {
        const calculateTime = () => {
            const now = new Date();
            const diff = now.getTime() - date.getTime();
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(minutes / 60);

            if (minutes < 1) return "Just now";
            if (minutes < 60) return `${minutes}m ago`;
            if (hours < 24) return `${hours}h ago`;
            return date.toLocaleDateString();
        };

        setTimeText(calculateTime());

        // Update every minute
        const interval = setInterval(() => {
            setTimeText(calculateTime());
        }, 60000);

        return () => clearInterval(interval);
    }, [date]);

    // Return empty during SSR, show time only on client
    if (!timeText) return null;

    return <>{timeText}</>;
}

export default function AlertsPanel({
    alerts,
    onAlertClick,
    onAcknowledge,
}: AlertsPanelProps) {
    const getSeverityStyles = (severity: string) => {
        switch (severity) {
            case "critical":
                return "bg-red-500/10 border-red-500/30 text-red-400";
            case "high":
                return "bg-orange-500/10 border-orange-500/30 text-orange-400";
            case "medium":
                return "bg-amber-500/10 border-amber-500/30 text-amber-400";
            case "low":
                return "bg-blue-500/10 border-blue-500/30 text-blue-400";
            default:
                return "bg-gray-500/10 border-gray-500/30 text-gray-400";
        }
    };

    const getSeverityIcon = (severity: string) => {
        if (severity === "critical" || severity === "high") {
            return (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
            );
        }
        return (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        );
    };

    const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;

    return (
        <div className="glass-card h-full flex flex-col">
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold text-white">Alerts</h2>
                    {unacknowledgedCount > 0 && (
                        <span className="px-2 py-0.5 text-xs font-medium bg-red-500/20 text-red-400 rounded-full">
                            {unacknowledgedCount}
                        </span>
                    )}
                </div>
                <button className="text-xs text-gray-400 hover:text-white transition">
                    View All
                </button>
            </div>

            {/* Alerts List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {alerts.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                        <svg className="w-10 h-10 mx-auto mb-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p className="text-sm">No active alerts</p>
                    </div>
                ) : (
                    alerts.map((alert) => (
                        <div
                            key={alert.id}
                            onClick={() => onAlertClick?.(alert)}
                            className={`p-3 rounded-lg border cursor-pointer transition hover:bg-white/5 ${getSeverityStyles(
                                alert.severity
                            )} ${alert.acknowledged ? "opacity-50" : ""}`}
                        >
                            <div className="flex items-start gap-3">
                                <div className={`mt-0.5 ${alert.severity === "critical" ? "pulse-danger" : ""}`}>
                                    {getSeverityIcon(alert.severity)}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-2">
                                        <h3 className="text-sm font-medium truncate">{alert.title}</h3>
                                        <span className="text-xs opacity-70 whitespace-nowrap">
                                            <RelativeTime date={alert.timestamp} />
                                        </span>
                                    </div>
                                    <p className="text-xs opacity-70 mt-1 line-clamp-2">{alert.description}</p>
                                    {!alert.acknowledged && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onAcknowledge?.(alert.id);
                                            }}
                                            className="mt-2 text-xs font-medium px-2 py-1 bg-white/10 hover:bg-white/20 rounded transition"
                                        >
                                            Acknowledge
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

