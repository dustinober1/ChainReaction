# Future Roadmap & Project Enhancements

This document outlines 10 high-impact improvements to make ChainReaction a "best-in-class" portfolio project, complete with user stories and actionable task lists.

---

## 1. 💡 AI-Powered Mitigation Co-pilot
**User Story:** *As a Supply Chain Manager, I want the system to suggest specific mitigation strategies (like activating backup suppliers or re-routing shipments) so I can respond to disruptions in minutes instead of hours.*

**Task List:**
- [x] Create a new DSPy module `MitigationSuggester`.
- [x] Integrate historical mitigation data into the prompt context.
- [x] Add a "Suggest Actions" button to the Risk Detail panel in the UI.
- [x] Implement a feedback loop where users can "Accept" or "Reject" suggestions to improve future AI prompts.

## 2. 🗺️ Advanced Geographical Risk Heatmap
**User Story:** *As a Logistics Coordinator, I want to see a real-world map with risk heatmaps so I can visualize how regional events (like hurricanes or strikes) geographically cluster around my suppliers.*

**Task List:**
- [ ] Replace or augment the current map with a Mapbox or Leaflet integration.
- [ ] Implement a "Risk Heatmap" layer based on aggregated entity risk scores in a region.
- [ ] Add geographic polygons to represent weather event footprints (e.g., hurricane paths).
- [ ] Enable map-based filtering of the supply chain graph.

## 3. 📈 Historical Risk Analytics & Trends
**User Story:** *As an Executive, I want to see how our supply chain risk profile has evolved over the last 12 months so I can measure the effectiveness of our resilience investments.*

**Task List:**
- [ ] Implement a Time-Series database (like TimescaleDB) or use Neo4j properties to track historical risk scores.
- [ ] Add an "Analytics" tab to the dashboard with Chart.js or Recharts.
- [ ] Create "Risk Velocity" metrics (how fast a risk is escalating).
- [ ] Export monthly risk PDF reports for stakeholders.

## 4. 🌍 Multi-Language News Intelligence
**User Story:** *As a Global Procurement Head, I want the system to monitor local news in Taiwan, China, and Germany in their native languages so I can catch disruptions before they hit international English news.*

**Task List:**
- [ ] Integrate a translation layer (Google Translate API or LLM-based) into the Scout Agent.
- [ ] Add support for regional RSS feeds and news scrapers.
- [ ] Implement language-specific entity extraction (handling non-Latin characters in supplier names).
- [ ] Add a "Source Language" badge to risk events in the UI.

## 5. 🛠️ Interactive Supply Chain Editor (No-Code UI)
**User Story:** *As a Data Steward, I want to add new suppliers and link them to components directly in the UI so I don't have to use API calls or scripts for manual updates.*

**Task List:**
- [ ] Build a "Control Plane" UI for CRUD operations on Suppliers/Components/Products.
- [ ] Implement drag-and-drop link creation between nodes in the graph view.
- [ ] Add bulk CSV/Excel import for supply chain data.
- [ ] Implement a "Draft Mode" where changes can be reviewed before being committed to the Neo4j graph.

## 6. 🤖 Predictive Impact Modeling (What-If Analysis)
**User Story:** *As a Risk Analyst, I want to simulate a "What-If" scenario (e.g., "What if this specific port closes?") so I can identify hidden single points of failure before a real event happens.*

**Task List:**
- [ ] Create a "Simulation" mode in the dashboard.
- [ ] Implement a graph algorithm to identify "Articulated Points" (nodes whose removal breaks the chain).
- [ ] Generate synthetic risk events for simulation and run the Impact Tracer.
- [ ] Compare "Current State" vs "Simulated State" metrics side-by-side.

## 💬 7. Slack & Microsoft Teams Integration
**User Story:** *As a Response Team member, I want to receive critical alerts directly in our dedicated Slack channel so we can start collaborating immediately without checking the dashboard.*

**Task List:**
- [ ] Build a Notification Dispatcher service.
- [ ] Implement Slack Webhook and Block Kit support for interactive alerts.
- [ ] Add a "Notify on Slack" toggle to the Webhook configuration.
- [ ] Enable "Acknowledge from Slack" functionality using Slack Actions.

## 8. 🛡️ Hallucination Guardrails & Data Verification
**User Story:** *As a Risk Auditor, I want to see the specific snippets of a news article that led the AI to identify a risk so I can verify the information is accurate.*

**Task List:**
- [ ] Update DSPy signatures to return "Citations" or "Source Snippets".
- [ ] Highlight source text in the Risk Detail panel.
- [ ] Implement a "Verification Score" that compares AI output against known ground-truth entities in the graph.
- [ ] Add a "Report AI Error" button to improve the training set.

## 🔐 9. Enterprise-Grade Security & RBAC
**User Story:** *As an IT Manager, I want to restrict "Writer" permissions to specific team leads so that standard users can't accidentally delete or modify critical supply chain data.*

**Task List:**
- [ ] Implement JWT-based authentication in addition to API keys.
- [ ] Build a "Users & Permissions" management dashboard.
- [ ] Add audit logs for every write operation (who changed what and when).
- [ ] Implement row-level security (e.g., users can only see products in their business unit).

## ⚡ 10. Performance Scaling with Neo4j Graph Algorithms
**User Story:** *As a power user with 1,000,000 nodes, I want the impact tracing to happen in milliseconds so the UI remains fluid and responsive.*

**Task List:**
- [ ] Migrate complex Python-side traversals to Neo4j GDS (Graph Data Science) library.
- [ ] Implement "Shortest Path" and "Betweenness Centrality" for faster bottleneck detection.
- [ ] Use Neo4j APOC triggers for real-time risk score propagation.
- [ ] Implement a Redis-based cache for common "Impact Tree" queries.
