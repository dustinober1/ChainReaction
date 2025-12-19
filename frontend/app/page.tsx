"use client";

import { useState, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import ChatInterface, { ChatMessage } from "./components/ChatInterface";
import NodeDetailsPanel from "./components/NodeDetailsPanel";
import AlertsPanel from "./components/AlertsPanel";
import { GraphNode, GraphData } from "./components/SupplyChainGraph";

// Dynamically import the graph to avoid SSR issues
const SupplyChainGraph = dynamic(
  () => import("./components/SupplyChainGraph"),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full bg-gray-900/50 rounded-xl">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400 text-sm">Loading graph visualization...</p>
        </div>
      </div>
    ),
  }
);

// Demo data
const generateDemoData = (): GraphData => {
  const nodes: GraphNode[] = [];
  const links: any[] = [];

  // Suppliers
  const suppliers = [
    { id: "SUP-001", name: "Taiwan Semi Co.", location: "Taiwan", riskScore: 75, isAtRisk: true },
    { id: "SUP-002", name: "Vietnam Electronics", location: "Vietnam", riskScore: 30 },
    { id: "SUP-003", name: "German Precision", location: "Germany", riskScore: 15 },
    { id: "SUP-004", name: "Shanghai Components", location: "China", riskScore: 45, isAtRisk: true },
    { id: "SUP-005", name: "Korean Chips Ltd", location: "Korea", riskScore: 20 },
  ];

  suppliers.forEach((s) => {
    nodes.push({
      id: s.id,
      label: "Supplier",
      type: "supplier",
      name: s.name,
      location: s.location,
      riskScore: s.riskScore,
      isAtRisk: s.isAtRisk,
    });
  });

  // Components
  const components = [
    { id: "COMP-001", name: "CPU Unit A", suppliers: ["SUP-001", "SUP-005"], riskScore: 60, isAtRisk: true },
    { id: "COMP-002", name: "Memory Module", suppliers: ["SUP-001", "SUP-004"], riskScore: 55, isAtRisk: true },
    { id: "COMP-003", name: "Display Panel", suppliers: ["SUP-002"], riskScore: 25 },
    { id: "COMP-004", name: "Power Controller", suppliers: ["SUP-003"], riskScore: 10 },
    { id: "COMP-005", name: "Sensor Array", suppliers: ["SUP-002", "SUP-004"], riskScore: 40 },
    { id: "COMP-006", name: "Battery Pack", suppliers: ["SUP-003", "SUP-005"], riskScore: 15 },
  ];

  components.forEach((c) => {
    nodes.push({
      id: c.id,
      label: "Component",
      type: "component",
      name: c.name,
      riskScore: c.riskScore,
      isAtRisk: c.isAtRisk,
    });
    c.suppliers.forEach((s) => {
      links.push({ source: s, target: c.id, type: "SUPPLIES" });
    });
  });

  // Products
  const products = [
    { id: "PROD-001", name: "Smartphone Pro", components: ["COMP-001", "COMP-002", "COMP-003"], riskScore: 70, isAtRisk: true },
    { id: "PROD-002", name: "Tablet Ultra", components: ["COMP-001", "COMP-003", "COMP-006"], riskScore: 55, isAtRisk: true },
    { id: "PROD-003", name: "Smart Watch", components: ["COMP-004", "COMP-005", "COMP-006"], riskScore: 25 },
    { id: "PROD-004", name: "Laptop Elite", components: ["COMP-001", "COMP-002", "COMP-004"], riskScore: 65, isAtRisk: true },
  ];

  products.forEach((p) => {
    nodes.push({
      id: p.id,
      label: "Product",
      type: "product",
      name: p.name,
      riskScore: p.riskScore,
      isAtRisk: p.isAtRisk,
    });
    p.components.forEach((c) => {
      links.push({ source: c, target: p.id, type: "PART_OF" });
    });
  });

  // Risk Event
  nodes.push({
    id: "RISK-001",
    label: "Risk Event",
    type: "risk",
    name: "Taiwan Typhoon",
    location: "Taiwan",
    isRiskSource: true,
    riskScore: 95,
  });
  links.push({ source: "RISK-001", target: "SUP-001", type: "AFFECTS" });

  return { nodes, links };
};

const demoAlerts = [
  {
    id: "ALT-001",
    severity: "critical" as const,
    title: "Taiwan Typhoon Impact",
    description: "Severe weather affecting Taiwan Semi Co. operations. Expected 2-week production delay.",
    timestamp: new Date(Date.now() - 1000 * 60 * 15),
    acknowledged: false,
  },
  {
    id: "ALT-002",
    severity: "high" as const,
    title: "Shanghai Port Congestion",
    description: "Port delays affecting component shipments from Shanghai Components.",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2),
    acknowledged: false,
  },
  {
    id: "ALT-003",
    severity: "medium" as const,
    title: "Price Increase Notice",
    description: "Memory module prices expected to increase 15% next quarter.",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24),
    acknowledged: true,
  },
];

export default function Dashboard() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(new Set());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [alerts, setAlerts] = useState(demoAlerts);
  const [stats, setStats] = useState({
    suppliers: 5,
    components: 6,
    products: 4,
    activeRisks: 1,
    atRiskProducts: 3,
    avgRiskScore: 52,
  });

  // Load demo data
  useEffect(() => {
    setGraphData(generateDemoData());
  }, []);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
  }, []);

  const handleNodeHover = useCallback((node: GraphNode | null) => {
    // Could implement hover preview
  }, []);

  const handleSendMessage = useCallback(async (message: string) => {
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: message,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Simulate AI response
    await new Promise((resolve) => setTimeout(resolve, 1500));

    const lowerMessage = message.toLowerCase();
    let responseContent = "";
    let queryResults: any = null;

    if (lowerMessage.includes("taiwan") || lowerMessage.includes("typhoon")) {
      responseContent = "The Taiwan typhoon is affecting 3 products through our Taiwan Semi Co. supplier:\n\n• Smartphone Pro (70% risk)\n• Tablet Ultra (55% risk)\n• Laptop Elite (65% risk)\n\nRecommended actions:\n1. Activate backup supplier Korean Chips Ltd\n2. Increase safety stock for CPU Units\n3. Notify affected product teams";
      queryResults = {
        affectedProducts: [
          { id: "PROD-001", name: "Smartphone Pro", riskScore: 70 },
          { id: "PROD-002", name: "Tablet Ultra", riskScore: 55 },
          { id: "PROD-004", name: "Laptop Elite", riskScore: 65 },
        ],
      };
      setHighlightedNodes(new Set(["SUP-001", "PROD-001", "PROD-002", "PROD-004", "RISK-001"]));
    } else if (lowerMessage.includes("single-source") || lowerMessage.includes("single source")) {
      responseContent = "Single-source components identified:\n\n• Display Panel - only from Vietnam Electronics\n• Power Controller - only from German Precision\n\nThese represent critical supply chain vulnerabilities. Recommend qualifying backup suppliers.";
      setHighlightedNodes(new Set(["COMP-003", "COMP-004", "SUP-002", "SUP-003"]));
    } else if (lowerMessage.includes("risk") && lowerMessage.includes("overall")) {
      responseContent = `Supply chain risk assessment:\n\n📊 Overall Risk Score: ${stats.avgRiskScore}%\n\n• ${stats.activeRisks} active risk event(s)\n• ${stats.atRiskProducts} products affected\n• ${stats.suppliers} suppliers monitored\n\nHighest risk suppliers:\n1. Taiwan Semi Co. (75%)\n2. Shanghai Components (45%)`;
    } else {
      responseContent = "I can help you analyze supply chain risks. Try asking about:\n\n• Impact of specific events (e.g., 'Taiwan typhoon')\n• Single-source components\n• Overall supply chain risk\n• Specific product or supplier risks";
    }

    const assistantMessage: ChatMessage = {
      id: `msg-${Date.now() + 1}`,
      role: "assistant",
      content: responseContent,
      timestamp: new Date(),
      queryResults,
    };
    setMessages((prev) => [...prev, assistantMessage]);
    setIsLoading(false);
  }, [stats]);

  const handleResultClick = useCallback((result: any) => {
    const node = graphData.nodes.find((n) => n.id === result.id);
    if (node) {
      setSelectedNode(node);
    }
  }, [graphData]);

  const handleAcknowledge = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a))
    );
  }, []);

  const handleAlertClick = useCallback((alert: any) => {
    if (alert.id === "ALT-001") {
      setHighlightedNodes(new Set(["RISK-001", "SUP-001"]));
      const riskNode = graphData.nodes.find((n) => n.id === "RISK-001");
      if (riskNode) setSelectedNode(riskNode);
    }
  }, [graphData]);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-white/10 bg-gray-900/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-[1920px] mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold gradient-text">ChainReaction</h1>
              <p className="text-xs text-gray-400">Supply Chain Risk Monitor</p>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="hidden md:flex items-center gap-6 text-sm">
            <StatBadge label="Suppliers" value={stats.suppliers} />
            <StatBadge label="Components" value={stats.components} />
            <StatBadge label="Products" value={stats.products} />
            <StatBadge
              label="Active Risks"
              value={stats.activeRisks}
              variant="danger"
            />
            <StatBadge
              label="At Risk"
              value={stats.atRiskProducts}
              variant="warning"
            />
          </div>

          <div className="flex items-center gap-3">
            <button className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </button>
            <button className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1920px] mx-auto p-4">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-[calc(100vh-88px)]">
          {/* Alerts Panel */}
          <div className="lg:col-span-2 h-full">
            <AlertsPanel
              alerts={alerts}
              onAlertClick={handleAlertClick}
              onAcknowledge={handleAcknowledge}
            />
          </div>

          {/* Graph Visualization */}
          <div className="lg:col-span-7 h-full relative">
            <SupplyChainGraph
              data={graphData}
              onNodeClick={handleNodeClick}
              onNodeHover={handleNodeHover}
              selectedNode={selectedNode?.id}
              highlightedNodes={highlightedNodes}
            />

            {/* Legend */}
            <div className="absolute bottom-4 left-4 glass-card px-3 py-2">
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="text-gray-400">Supplier</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-purple-500" />
                  <span className="text-gray-400">Component</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                  <span className="text-gray-400">Product</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="text-gray-400">Risk</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-amber-500" />
                  <span className="text-gray-400">At Risk</span>
                </div>
              </div>
            </div>

            {/* Node Details Panel */}
            <NodeDetailsPanel
              node={selectedNode}
              onClose={() => setSelectedNode(null)}
            />
          </div>

          {/* Chat Interface */}
          <div className="lg:col-span-3 h-full">
            <ChatInterface
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              onResultClick={handleResultClick}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

function StatBadge({
  label,
  value,
  variant = "default",
}: {
  label: string;
  value: number;
  variant?: "default" | "danger" | "warning";
}) {
  const variantStyles = {
    default: "text-gray-400",
    danger: "text-red-400",
    warning: "text-amber-400",
  };

  return (
    <div className="text-center">
      <div className={`text-lg font-semibold ${variantStyles[variant]}`}>
        {value}
      </div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}
