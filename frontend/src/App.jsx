import { useState } from "react";
import { LayoutDashboard, Upload, MessageSquare, Wallet } from "lucide-react";
import Dashboard from "./components/Dashboard";
import Ingestion from "./components/Ingestion";
import Chat from "./components/Chat";
import "./styles/global.css";

function App() {
  const [activeView, setActiveView] = useState("dashboard");

  const NavItem = ({ view, icon: Icon, label }) => (
    <button
      onClick={() => setActiveView(view)}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "transparent",
        border: "none",
        color: activeView === view ? "var(--accent-primary)" : "var(--text-muted)",
        cursor: "pointer",
        padding: "0.5rem",
        transition: "color 0.2s",
      }}
    >
      <Icon size={24} style={{ marginBottom: 4 }} />
      <span style={{ fontSize: "0.75rem", fontWeight: 500 }}>{label}</span>
    </button>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* Main Content Area */}
      <main style={{ flex: 1, overflowY: "auto", position: "relative" }}>
        {activeView === "dashboard" && <Dashboard />}
        {activeView === "ingest" && <Ingestion />}
        {activeView === "chat" && <Chat />}
      </main>

      {/* Bottom Navigation Bar */}
      <nav
        className="glass-panel"
        style={{
          display: "flex",
          justifyContent: "space-around",
          padding: "1rem",
          borderTop: "1px solid var(--border-subtle)",
          position: "sticky",
          bottom: 0,
          zIndex: 100,
        }}
      >
        <NavItem view="dashboard" icon={LayoutDashboard} label="Audit" />
        <NavItem view="ingest" icon={Upload} label="Ingest" />
        <NavItem view="chat" icon={MessageSquare} label="Analyst" />
      </nav>
    </div>
  );
}

export default App;
