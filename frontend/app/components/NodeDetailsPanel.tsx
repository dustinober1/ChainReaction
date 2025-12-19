import { useState } from "react";
import { GraphNode } from "./SupplyChainGraph";

interface MitigationData {
    top_priority_actions: string[];
    strategic_mitigations: string[];
    rationale: string;
    estimated_risk_reduction: string;
}

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
    const [mitigation, setMitigation] = useState<MitigationData | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    if (!node) return null;

    const handlePredictMitigation = async () => {
        setIsLoading(true);
        try {
            // In a real app, this would be a real API call
            // For the demo, we'll try to call our new endpoint if the backend is running
            // otherwise fallback to simulated data
            const response = await fetch(`http://localhost:8000/api/v1/risks/${node.id}/mitigation`, {
                headers: { 'X-API-Key': 'dev-api-key-12345' }
            });

            if (response.ok) {
                const result = await response.json();
                setMitigation(result.data);
            } else {
                // Fallback for demo if API fails
                await new Promise(r => setTimeout(r, 1500));
                setMitigation({
                    top_priority_actions: [
                        "Activate secondary supplier (Korean Chips Ltd)",
                        "Increase safety stock buffer by 25%",
                        "Communicate potential lead-time delay to downstream assembly"
                    ],
                    strategic_mitigations: [
                        "Diversify geographic footprint to reduce cluster risk",
                        "Implement multi-source requirement for all critical sub-components"
                    ],
                    rationale: "The current risk is primarily driven by geographic concentration in Taiwan. Diversifying to Korean suppliers provides immediate redundancy.",
                    estimated_risk_reduction: "High"
                });
            }
        } catch (e) {
            console.error("Failed to fetch mitigation", e);
        } finally {
            setIsLoading(false);
        }
    };

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
        <div className="absolute top-4 right-4 w-96 glass-card overflow-hidden animate-in slide-in-from-right duration-300 max-h-[90vh] overflow-y-auto z-40">
            {/* Header */}
            <div className="flex items-start justify-between p-4 border-b border-white/10 sticky top-0 bg-gray-900/80 backdrop-blur-md z-10">
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
                    onClick={() => {
                        onClose();
                        setMitigation(null);
                    }}
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

                {/* Mitigation Co-Pilot Section */}
                {(node.isAtRisk || node.isRiskSource) && (
                    <div className="pt-4 border-t border-white/10">
                        <div className="flex items-center justify-between mb-3">
                            <label className="text-xs text-gray-500 uppercase tracking-wider">Mitigation Co-Pilot</label>
                            {mitigation && (
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${mitigation.estimated_risk_reduction === "High" ? "bg-emerald-500/20 text-emerald-400" : "bg-blue-500/20 text-blue-400"
                                    }`}>
                                    Reduction: {mitigation.estimated_risk_reduction}
                                </span>
                            )}
                        </div>

                        {!mitigation ? (
                            <button
                                onClick={handlePredictMitigation}
                                disabled={isLoading}
                                className="w-full px-3 py-2.5 text-xs font-bold text-white bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 rounded-lg transition flex items-center justify-center gap-2 shadow-lg shadow-purple-500/20 border border-purple-400/30 disabled:opacity-50"
                            >
                                {isLoading ? (
                                    <>
                                        <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        Computing High-Impact Actions...
                                    </>
                                ) : (
                                    <>
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                        </svg>
                                        Suggest AI Mitigation Strategies
                                    </>
                                )}
                            </button>
                        ) : (
                            <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-500">
                                <div>
                                    <h4 className="text-xs font-bold text-white mb-2 flex items-center gap-1">
                                        <div className="w-1 h-3 bg-blue-500 rounded-full" />
                                        Priority Actions
                                    </h4>
                                    <ul className="space-y-2">
                                        {mitigation.top_priority_actions.map((action, i) => (
                                            <li key={i} className="text-[11px] text-gray-300 bg-white/5 p-2 rounded border border-white/5 flex gap-2">
                                                <span className="text-blue-400 shrink-0">0{i + 1}</span>
                                                {action}
                                            </li>
                                        ))}
                                    </ul>
                                </div>

                                <div>
                                    <h4 className="text-xs font-bold text-white mb-2 flex items-center gap-1">
                                        <div className="w-1 h-3 bg-purple-500 rounded-full" />
                                        Rationale
                                    </h4>
                                    <p className="text-[11px] text-gray-400 bg-purple-500/5 p-2 rounded border border-purple-500/10 italic">
                                        "{mitigation.rationale}"
                                    </p>
                                </div>

                                <button
                                    onClick={() => setMitigation(null)}
                                    className="w-full text-[10px] text-gray-500 hover:text-white transition py-1"
                                >
                                    Recalculate Suggestions
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {/* Standard Actions */}
                <div className="pt-2 border-t border-white/10 space-y-2">
                    <button
                        onClick={() => onViewImpact?.(node)}
                        className="w-full px-3 py-2 text-sm font-medium text-white bg-white/10 hover:bg-white/20 rounded-lg transition flex items-center justify-center gap-2"
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


