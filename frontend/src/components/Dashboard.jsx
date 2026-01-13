import { useEffect, useState } from "react";
import { api } from "../api/client";
import { TrendingUp, Shield, Zap, Activity, Wallet } from "lucide-react";

export default function Dashboard() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        api.getAuditSummary()
            .then(setData)
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="container" style={{ textAlign: "center", paddingTop: "4rem" }}>
                <p>Loading financial data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="container" style={{ textAlign: "center", paddingTop: "4rem" }}>
                <p style={{ color: "var(--accent-danger)" }}>Error: {error}</p>
                <button className="btn-primary" onClick={() => window.location.reload()} style={{ marginTop: "1rem" }}>
                    Retry
                </button>
            </div>
        );
    }

    const StatCard = ({ title, value, subtext, status, icon: Icon, color }) => (
        <div className="glass-panel" style={{ padding: "1.5rem", borderRadius: "var(--radius-lg)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
                <div style={{ padding: "10px", borderRadius: "10px", background: `${color}20`, color: color }}>
                    <Icon size={24} />
                </div>
                {status && (
                    <span
                        style={{
                            padding: "4px 12px",
                            borderRadius: "20px",
                            fontSize: "0.8rem",
                            fontWeight: 600,
                            background: status === "No Data" ? "#333" :
                                (["Antifragile", "Disciplined", "Steward"].includes(status) ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)"),
                            color: status === "No Data" ? "#aaa" :
                                (["Antifragile", "Disciplined", "Steward"].includes(status) ? "var(--status-antifragile)" : "var(--status-fragile)"),
                        }}
                    >
                        {status}
                    </span>
                )}
            </div>
            <h3 style={{ color: "var(--text-secondary)", marginBottom: "0.5rem", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "1px" }}>
                {title}
            </h3>
            <div style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "0.25rem" }}>
                {value}
            </div>
            {subtext && <div style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>{subtext}</div>}
        </div>
    );

    return (
        <div className="container animate-fade-in">
            <header style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                    <h1 style={{ marginBottom: "0.5rem" }}>Financial Audit</h1>
                    <p>Overview of your financial machine.</p>
                </div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", textAlign: "right" }}>
                    Updated<br />
                    {new Date(data.last_updated).toLocaleDateString()}
                </div>
            </header>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
                {/* Income */}
                <StatCard
                    title="Income"
                    value={`€${data.income}`}
                    subtext="Total processed income"
                    icon={Wallet}
                    color="var(--accent-success)"
                />

                {/* Machine */}
                <StatCard
                    title="Machine"
                    value={`€${data.machine.total}`}
                    subtext={`${(data.machine.percentage * 100).toFixed(1)}% of income`}
                    status={data.machine.status}
                    icon={Zap}
                    color="var(--accent-purple)"
                />

                {/* Flow */}
                <StatCard
                    title="Flow"
                    value={`€${data.flow.total}`}
                    subtext={`${(data.flow.percentage * 100).toFixed(1)}% of income`}
                    status={data.flow.status}
                    icon={TrendingUp}
                    color="var(--accent-primary)"
                />

                {/* Sovereignty */}
                <StatCard
                    title="Sovereignty"
                    value={`€${data.sovereignty.total}`}
                    subtext={`${(data.sovereignty.percentage * 100).toFixed(1)}% of income`}
                    status={data.sovereignty.status}
                    icon={Shield}
                    color="var(--accent-warning)"
                />
            </div>
        </div>
    );
}
