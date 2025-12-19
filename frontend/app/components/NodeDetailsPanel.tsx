"use client";

import { GraphNode } from "./SupplyChainGraph";

interface NodeDetailsPanelProps {
    node: GraphNode | null;
    onClose: () => void;
    onViewImpact?: (node: GraphNode) => void;
    onShowConnections?: (node: GraphNode) => void;
}

export default function NodeDetailsPanel({
    node,
    onClose,
    onViewImpact,
    onShowConnections,
}: NodeDetailsPanelProps) {
    if (!node) return null;

    const getTypeColor = (type: string) => {
        switch (type) {
            case "supplier":
                return "bg-blue-500/20 text-blue-400 border-blue-500/30";
            case "component":
                return "bg-purple-500/20 text-purple-400 border-purple-500/30";
            case "product":
                return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
            case "risk":
                return "bg-red-500/20 text-red-400 border-red-500/30";
            default:
                return "bg-gray-500/20 text-gray-400 border-gray-500/30";
        }
    };

    const getRiskLevel = (score?: number) => {
        if (!score) return null;
        if (score >= 70) return { label: "High Risk", color: "text-red-400 bg-red-500/20" };
        if (score >= 40) return { label: "Medium Risk", color: "text-amber-400 bg-amber-500/20" };
        return { label: "Low Risk", color: "text-green-400 bg-green-500/20" };
    };

    const riskLevel = getRiskLevel(node.riskScore);

    return (
        <div className="absolute top-4 right-4 w-80 glass-card overflow-hidden animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="flex items-start justify-between p-4 border-b border-white/10">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                        <span
                            className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getTypeColor(
                                node.type
                            )}`}
                        >
                            {node.type.charAt(0).toUpperCase() + node.type.slice(1)}
                        </span>
                        {node.isRiskSource && (
                            <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-red-500/20 text-red-400 border border-red-500/30 pulse-danger">
                                Risk Event
                            </span>
                        )}
                        {node.isAtRisk && !node.isRiskSource && (
                            <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                                At Risk
                            </span>
                        )}
                    </div>
                    <h3 className="text-lg font-semibold text-white">{node.name}</h3>
                    <p className="text-xs text-gray-400 font-mono">{node.id}</p>
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

            {/* Content */}
            <div className="p-4 space-y-4">
                {/* Risk Score */}
                {node.riskScore !== undefined && riskLevel && (
                    <div>
                        <label className="text-xs text-gray-500 uppercase tracking-wider">Risk Score</label>
                        <div className="mt-1 flex items-center gap-3">
                            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-500 ${node.riskScore >= 70
                                        ? "bg-gradient-to-r from-red-500 to-red-400"
                                        : node.riskScore >= 40
                                            ? "bg-gradient-to-r from-amber-500 to-amber-400"
                                            : "bg-gradient-to-r from-green-500 to-green-400"
                                        }`}
                                    style={{ width: `${node.riskScore}%` }}
                                />
                            </div>
                            <span className={`text-sm font-semibold px-2 py-0.5 rounded ${riskLevel.color}`}>
                                {node.riskScore}%
                            </span>
                        </div>
                        <p className="text-xs text-gray-400 mt-1">{riskLevel.label}</p>
                    </div>
                )}

                {/* Location */}
                {node.location && (
                    <div>
                        <label className="text-xs text-gray-500 uppercase tracking-wider">Location</label>
                        <p className="text-sm text-white mt-1 flex items-center gap-2">
                            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            {node.location}
                        </p>
                    </div>
                )}

                {/* Actions */}
                <div className="pt-2 border-t border-white/10 space-y-2">
                    <button
                        onClick={() => onViewImpact?.(node)}
                        className="w-full px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition flex items-center justify-center gap-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        View Impact Analysis
                    </button>
                    <button
                        onClick={() => onShowConnections?.(node)}
                        className="w-full px-3 py-2 text-sm font-medium text-gray-300 bg-white/5 hover:bg-white/10 rounded-lg transition flex items-center justify-center gap-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                        </svg>
                        Show Connected Nodes
                    </button>
                </div>
            </div>
        </div>
    );
}

