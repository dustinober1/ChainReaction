"use client";

import { useState, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import ChatInterface, { ChatMessage } from "./components/ChatInterface";
import NodeDetailsPanel from "./components/NodeDetailsPanel";
import AlertsPanel from "./components/AlertsPanel";
import NotificationsPanel from "./components/NotificationsPanel";
import SettingsPanel from "./components/SettingsPanel";
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
  const [showNotifications, setShowNotifications] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
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

    // Simulate AI response with varied delay
    await new Promise((resolve) => setTimeout(resolve, 1000 + Math.random() * 1000));

    const lowerMessage = message.toLowerCase();
    let responseContent = "";
    let queryResults: any = null;

    // Handle various question types intelligently
    if (lowerMessage.includes("taiwan") || lowerMessage.includes("typhoon")) {
      responseContent = "**Taiwan Typhoon Impact Analysis**\n\nThe Taiwan typhoon is affecting 3 products through our Taiwan Semi Co. supplier:\n\n• **Smartphone Pro** (70% risk) - Critical\n• **Tablet Ultra** (55% risk) - High\n• **Laptop Elite** (65% risk) - High\n\n**Recommended Actions:**\n1. Activate backup supplier Korean Chips Ltd\n2. Increase safety stock for CPU Units\n3. Notify affected product teams\n4. Monitor weather updates for timeline";
      queryResults = {
        affectedProducts: [
          { id: "PROD-001", name: "Smartphone Pro", riskScore: 70 },
          { id: "PROD-002", name: "Tablet Ultra", riskScore: 55 },
          { id: "PROD-004", name: "Laptop Elite", riskScore: 65 },
        ],
      };
      setHighlightedNodes(new Set(["SUP-001", "PROD-001", "PROD-002", "PROD-004", "RISK-001"]));
    } else if (lowerMessage.includes("single-source") || lowerMessage.includes("single source")) {
      responseContent = "**Single-Source Component Analysis**\n\nComponents with only one supplier (high vulnerability):\n\n• **Display Panel** - only from Vietnam Electronics\n• **Power Controller** - only from German Precision\n\n⚠️ These represent critical supply chain vulnerabilities.\n\n**Recommendation:** Qualify backup suppliers for these components to reduce risk exposure.";
      setHighlightedNodes(new Set(["COMP-003", "COMP-004", "SUP-002", "SUP-003"]));
    } else if ((lowerMessage.includes("biggest") || lowerMessage.includes("highest") || lowerMessage.includes("top")) && lowerMessage.includes("risk")) {
      responseContent = `**Biggest Risk Assessment**\n\n🚨 **Critical Risk: Taiwan Typhoon**\nAffecting Taiwan Semi Co. (SUP-001) with 95% severity\n\n**Impact Chain:**\n• Taiwan Semi Co. → CPU Unit A → Smartphone Pro, Tablet Ultra, Laptop Elite\n• Taiwan Semi Co. → Memory Module → Smartphone Pro, Laptop Elite\n\n**At-Risk Products:**\n1. Smartphone Pro - 70% risk score\n2. Laptop Elite - 65% risk score\n3. Tablet Ultra - 55% risk score\n\n**Immediate Actions Required:**\n1. Contact backup suppliers (Korean Chips Ltd)\n2. Assess current inventory levels\n3. Notify customers of potential delays`;
      setHighlightedNodes(new Set(["RISK-001", "SUP-001", "COMP-001", "COMP-002", "PROD-001", "PROD-002", "PROD-004"]));
      queryResults = {
        affectedProducts: [
          { id: "PROD-001", name: "Smartphone Pro", riskScore: 70 },
          { id: "PROD-004", name: "Laptop Elite", riskScore: 65 },
          { id: "PROD-002", name: "Tablet Ultra", riskScore: 55 },
        ],
      };
    } else if (lowerMessage.includes("overall") || (lowerMessage.includes("supply") && lowerMessage.includes("chain") && lowerMessage.includes("risk"))) {
      responseContent = `**Supply Chain Risk Overview**\n\n📊 **Overall Risk Score: ${stats.avgRiskScore}%**\n\n**Current Status:**\n• ${stats.activeRisks} active risk event(s)\n• ${stats.atRiskProducts} products at risk\n• ${stats.suppliers} suppliers monitored\n• ${stats.components} components tracked\n\n**Highest Risk Suppliers:**\n1. Taiwan Semi Co. - 75% (Typhoon impact)\n2. Shanghai Components - 45% (Port congestion)\n\n**Lowest Risk Suppliers:**\n1. German Precision - 15%\n2. Korean Chips Ltd - 20%`;
    } else if (lowerMessage.includes("supplier") && (lowerMessage.includes("list") || lowerMessage.includes("all") || lowerMessage.includes("show"))) {
      responseContent = `**Supplier Overview**\n\n| Supplier | Location | Risk Score | Status |\n|----------|----------|------------|--------|\n| Taiwan Semi Co. | Taiwan | 75% | ⚠️ At Risk |\n| Shanghai Components | China | 45% | ⚠️ At Risk |\n| Vietnam Electronics | Vietnam | 30% | ✅ OK |\n| Korean Chips Ltd | Korea | 20% | ✅ OK |\n| German Precision | Germany | 15% | ✅ OK |\n\n**Active Issues:**\n• Taiwan Semi Co. affected by typhoon\n• Shanghai Components facing port delays`;
    } else if (lowerMessage.includes("product") && (lowerMessage.includes("list") || lowerMessage.includes("all") || lowerMessage.includes("show"))) {
      responseContent = `**Product Risk Summary**\n\n| Product | Risk Score | Status |\n|---------|------------|--------|\n| Smartphone Pro | 70% | 🔴 High Risk |\n| Laptop Elite | 65% | 🔴 High Risk |\n| Tablet Ultra | 55% | 🟡 Medium Risk |\n| Smart Watch | 25% | 🟢 Low Risk |\n\n**Products at Immediate Risk:**\n• Smartphone Pro - depends on Taiwan Semi Co.\n• Laptop Elite - multiple affected components`;
    } else if (lowerMessage.includes("help") || lowerMessage.includes("what can")) {
      responseContent = `**I can help you with:**\n\n🔍 **Risk Analysis**\n• "What is the biggest risk I'm facing?"\n• "Show overall supply chain risk"\n• "What products are at risk?"\n\n🌪️ **Event Impact**\n• "How does the Taiwan typhoon affect us?"\n• "Show me the impact analysis"\n\n📦 **Inventory & Suppliers**\n• "List all suppliers"\n• "Show single-source components"\n• "What products depend on Taiwan Semi?"\n\n📊 **Reports**\n• "Show product risk summary"\n• "What are our lowest risk suppliers?"\n\nJust ask your question naturally!`;
    } else if (lowerMessage.includes("german") || lowerMessage.includes("precision")) {
      responseContent = `**German Precision Analysis**\n\n📍 **Location:** Germany\n📊 **Risk Score:** 15% (Low)\n\n**Supplies:**\n• Power Controller (COMP-004)\n• Battery Pack (COMP-006) - shared with Korean Chips\n\n**Products Affected:**\n• Smart Watch\n• Laptop Elite\n\n✅ **Status:** Stable supplier with good track record. Low geopolitical risk. Recommended for increased allocation.`;
      setHighlightedNodes(new Set(["SUP-003", "COMP-004", "COMP-006", "PROD-003", "PROD-004"]));
    } else if (lowerMessage.includes("shanghai") || lowerMessage.includes("components") || lowerMessage.includes("port")) {
      responseContent = `**Shanghai Components Analysis**\n\n📍 **Location:** China\n📊 **Risk Score:** 45% (Medium)\n⚠️ **Status:** At Risk\n\n**Current Issue:** Port congestion causing delays\n\n**Supplies:**\n• Memory Module (shared with Taiwan Semi)\n• Sensor Array (shared with Vietnam Electronics)\n\n**Affected Products:**\n• Smartphone Pro\n• Laptop Elite\n\n**Mitigation:** Consider air freight for critical shipments.`;
      setHighlightedNodes(new Set(["SUP-004", "COMP-002", "COMP-005"]));
    } else {
      // Intelligent fallback - try to understand the question
      const words = lowerMessage.split(/\s+/);
      const entities = {
        suppliers: ["taiwan", "vietnam", "german", "shanghai", "korean"],
        products: ["smartphone", "tablet", "watch", "laptop"],
        components: ["cpu", "memory", "display", "power", "sensor", "battery"],
      };

      let foundContext = false;
      for (const word of words) {
        if (entities.suppliers.some(s => word.includes(s))) {
          foundContext = true;
          responseContent = `I can provide detailed analysis on that supplier. Here's what I know:\n\n**Current Supply Chain Status:**\n• ${stats.activeRisks} active risk(s)\n• ${stats.atRiskProducts} products affected\n• Average risk score: ${stats.avgRiskScore}%\n\nTry asking specifically about:\n• "Show Taiwan Semi Co. impact"\n• "What products are at risk?"\n• "What's my biggest risk?"`;
          break;
        }
      }

      if (!foundContext) {
        responseContent = `I understand you're asking about "${message}"\n\n**Based on current data:**\n• ${stats.activeRisks} active risk event(s) detected\n• ${stats.atRiskProducts} products currently at risk\n• Highest risk: Taiwan Semi Co. (typhoon impact)\n\n**Try these specific questions:**\n• "What is my biggest risk?"\n• "Show me products at risk"\n• "Impact of Taiwan typhoon"\n• "List all suppliers"\n• "Help" for more options`;
      }
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

  const handleAcknowledgeAll = useCallback(() => {
    setAlerts((prev) =>
      prev.map((a) => ({ ...a, acknowledged: true }))
    );
  }, []);

  const handleAlertClick = useCallback((alert: any) => {
    if (alert.id === "ALT-001") {
      setHighlightedNodes(new Set(["RISK-001", "SUP-001"]));
      const riskNode = graphData.nodes.find((n) => n.id === "RISK-001");
      if (riskNode) setSelectedNode(riskNode);
    }
  }, [graphData]);

  const handleClearChat = useCallback(() => {
    setMessages([]);
    setHighlightedNodes(new Set());
  }, []);

  // Handler for View Impact Analysis button
  const handleViewImpact = useCallback((node: GraphNode) => {
    // Find connected nodes based on links
    const connectedNodeIds = new Set<string>([node.id]);

    graphData.links.forEach((link: any) => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;

      if (sourceId === node.id) connectedNodeIds.add(targetId);
      if (targetId === node.id) connectedNodeIds.add(sourceId);
    });

    setHighlightedNodes(connectedNodeIds);

    // Send a message to the chat about this node
    const impactMessage = `Tell me about the impact of ${node.name}`;
    handleSendMessage(impactMessage);
  }, [graphData, handleSendMessage]);

  // Handler for Show Connected Nodes button
  const handleShowConnections = useCallback((node: GraphNode) => {
    const connectedNodeIds = new Set<string>([node.id]);

    // Find all directly connected nodes
    graphData.links.forEach((link: any) => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;

      if (sourceId === node.id) connectedNodeIds.add(targetId);
      if (targetId === node.id) connectedNodeIds.add(sourceId);
    });

    setHighlightedNodes(connectedNodeIds);

    // Create informative message
    const connectedNodes = graphData.nodes.filter(n => connectedNodeIds.has(n.id) && n.id !== node.id);
    const suppliers = connectedNodes.filter(n => n.type === 'supplier');
    const components = connectedNodes.filter(n => n.type === 'component');
    const products = connectedNodes.filter(n => n.type === 'product');
    const risks = connectedNodes.filter(n => n.type === 'risk');

    let content = `**Connected Nodes for ${node.name}**\n\n`;
    if (suppliers.length) content += `**Suppliers:** ${suppliers.map(s => s.name).join(', ')}\n`;
    if (components.length) content += `**Components:** ${components.map(c => c.name).join(', ')}\n`;
    if (products.length) content += `**Products:** ${products.map(p => p.name).join(', ')}\n`;
    if (risks.length) content += `**Risk Events:** ${risks.map(r => r.name).join(', ')}\n`;

    const connectionMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "assistant",
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, connectionMessage]);
  }, [graphData]);

  const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;

  return (
    <div className="h-screen bg-gray-950 text-white overflow-hidden">
      {/* Modals */}
      <NotificationsPanel
        isOpen={showNotifications}
        onClose={() => setShowNotifications(false)}
        alerts={alerts}
        onAcknowledge={handleAcknowledge}
        onAcknowledgeAll={handleAcknowledgeAll}
      />
      <SettingsPanel
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />

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
            {/* Notifications Button */}
            <button
              onClick={() => setShowNotifications(true)}
              className="relative p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              {/* Notification Badge */}
              {unacknowledgedCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                  {unacknowledgedCount}
                </span>
              )}
            </button>
            {/* Settings Button */}
            <button
              onClick={() => setShowSettings(true)}
              className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
        </div>
      </header>


      {/* Main Content */}
      <main className="max-w-[1920px] mx-auto p-4 h-[calc(100vh-88px)] overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-full">
          {/* Alerts Panel */}
          <div className="lg:col-span-2 h-full overflow-hidden">
            <AlertsPanel
              alerts={alerts}
              onAlertClick={handleAlertClick}
              onAcknowledge={handleAcknowledge}
            />
          </div>

          {/* Graph Visualization */}
          <div className="lg:col-span-7 h-full relative overflow-hidden">
            <SupplyChainGraph
              data={graphData}
              onNodeClick={handleNodeClick}
              onNodeHover={handleNodeHover}
              selectedNode={selectedNode?.id}
              highlightedNodes={highlightedNodes}
            />

            {/* Node Details Panel */}
            <NodeDetailsPanel
              node={selectedNode}
              onClose={() => setSelectedNode(null)}
              onViewImpact={handleViewImpact}
              onShowConnections={handleShowConnections}
            />
          </div>

          {/* Chat Interface */}
          <div className="lg:col-span-3 h-full overflow-hidden">
            <ChatInterface
              messages={messages}
              onSendMessage={handleSendMessage}
              onClearChat={handleClearChat}
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
