import { useState, useRef, useEffect } from "react";
import { api } from "../api/client";
import { UploadCloud, Check, AlertCircle, Save } from "lucide-react";

export default function Ingestion() {
    const [file, setFile] = useState(null);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Lists from Backend
    const [categories, setCategories] = useState([]);
    const [pillars, setPillars] = useState([]);
    const [integrity, setIntegrity] = useState([]);
    const [triggers, setTriggers] = useState([]);

    const fileInputRef = useRef(null);

    useEffect(() => {
        api.getCategories().then((res) => {
            setCategories(res.categories || []);
            setPillars(res.machine_pillars || []);
            setIntegrity(res.integrity_filters || []);
            setTriggers(res.root_triggers || []);
        });
    }, []);

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            handlePreview(e.target.files[0]);
        }
    };

    const handlePreview = async (selectedFile) => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.ingestPreview(selectedFile);
            // Map to consistent structure
            const mapped = res.transactions.map((t, idx) => ({
                ...t,
                id: idx,
                // Default logic
                category_approved: t.category_suggested === "Uncategorized" ? "" : t.category_suggested,
                machine_pillar: t.machine_pillar || "",
                integrity_filter: t.integrity_filter || "Planned",
                root_trigger: t.root_trigger || "",
                notes: t.notes || "",
            }));
            setData({ ...res, transactions: mapped });
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleFieldChange = (id, field, value) => {
        setData((prev) => ({
            ...prev,
            transactions: prev.transactions.map((t) =>
                t.id === id ? { ...t, [field]: value } : t
            ),
        }));
    };

    const handleCommit = async () => {
        setLoading(true);
        try {
            await api.ingestCommit(data.transactions);
            setData(null);
            setFile(null);
            alert("Transactions committed successfully!");
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Shared Select Style
    const selectStyle = {
        background: "rgba(0,0,0,0.3)",
        border: "1px solid var(--border-subtle)",
        color: "white",
        fontSize: "0.85rem",
        padding: "0.3rem",
        borderRadius: "4px",
        width: "100%",
        cursor: "pointer",
    };

    const inputStyle = {
        ...selectStyle,
        background: "rgba(0,0,0,0.1)",
        cursor: "text",
    };

    if (!data && !loading) {
        return (
            <div className="container animate-fade-in" style={{ textAlign: "center", marginTop: "4rem" }}>
                <h1 style={{ marginBottom: "2rem" }}>Upload Statement</h1>
                <div
                    className="glass-panel"
                    style={{
                        maxWidth: "600px",
                        margin: "0 auto",
                        padding: "4rem 2rem",
                        borderRadius: "var(--radius-lg)",
                        border: "2px dashed var(--border-subtle)",
                        cursor: "pointer",
                        transition: "all 0.2s",
                    }}
                    onClick={() => fileInputRef.current?.click()}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                        e.preventDefault();
                        if (e.dataTransfer.files[0]) {
                            setFile(e.dataTransfer.files[0]);
                            handlePreview(e.dataTransfer.files[0]);
                        }
                    }}
                >
                    <UploadCloud size={48} color="var(--accent-primary)" style={{ marginBottom: "1rem" }} />
                    <h3>Drag & Drop or Click to Upload</h3>
                    <p style={{ fontSize: "0.9rem" }}>Supports CSV Only (Swedbank Format)</p>
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        style={{ display: "none" }}
                        accept=".csv"
                    />
                </div>
                {error && <p style={{ color: "var(--status-fragile)", marginTop: "1rem" }}>{error}</p>}
            </div>
        );
    }

    return (
        <div className="container animate-fade-in" style={{ maxWidth: "1400px" }}>
            <header style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                    <h1>Review Transactions</h1>
                    <p>{file?.name} - {data?.transactions?.length || 0} items</p>
                </div>
                <div style={{ display: "flex", gap: "1rem" }}>
                    <button
                        className="btn-primary"
                        onClick={handleCommit}
                        disabled={loading}
                        style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
                    >
                        <Save size={18} />
                        Commit to Ledger
                    </button>
                </div>
            </header>

            {loading && (
                <div style={{ margin: "2rem auto", maxWidth: "400px", textAlign: "center" }}>
                    <p style={{ marginBottom: "0.5rem", color: "var(--text-secondary)" }}>Processing Statement...</p>
                    <div style={{
                        width: "100%",
                        height: "4px",
                        background: "var(--bg-card)",
                        borderRadius: "2px",
                        overflow: "hidden"
                    }}>
                        <div style={{
                            width: "100%",
                            height: "100%",
                            background: "var(--accent-primary)",
                            animation: "indeterminate 1.5s infinite linear",
                            transformOrigin: "0% 50%",
                        }} />
                    </div>
                </div>
            )}

            <div className="glass-panel" style={{ borderRadius: "var(--radius-lg)", overflow: "hidden", overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", minWidth: "1200px" }}>
                    <thead>
                        <tr style={{ background: "rgba(255,255,255,0.02)", textAlign: "left" }}>
                            <th style={{ padding: "1rem", width: "100px" }}>Date</th>
                            <th style={{ padding: "1rem" }}>Description</th>
                            <th style={{ padding: "1rem", width: "100px" }}>Amount</th>
                            <th style={{ padding: "1rem", width: "160px" }}>Category</th>
                            <th style={{ padding: "1rem", width: "140px" }}>Pillar</th>
                            <th style={{ padding: "1rem", width: "140px" }}>Integrity</th>
                            <th style={{ padding: "1rem", width: "140px" }}>Trigger</th>
                            <th style={{ padding: "1rem" }}>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data?.transactions?.map((t) => (
                            <tr key={t.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                                <td style={{ padding: "0.8rem", whiteSpace: "nowrap" }}>{t.date}</td>
                                <td style={{ padding: "0.8rem" }}>{t.description}</td>
                                <td style={{ padding: "0.8rem", fontFamily: "monospace" }}>{Number(t.amount).toFixed(2)}</td>

                                {/* Category */}
                                <td style={{ padding: "0.8rem" }}>
                                    <select
                                        value={t.category_approved || ""}
                                        onChange={(e) => handleFieldChange(t.id, "category_approved", e.target.value)}
                                        style={selectStyle}
                                    >
                                        <option value="">Uncategorized</option>
                                        {categories.map((c) => (
                                            <option key={c} value={c}>{c}</option>
                                        ))}
                                    </select>
                                </td>

                                {/* Pillar */}
                                <td style={{ padding: "0.8rem" }}>
                                    <select
                                        value={t.machine_pillar || ""}
                                        onChange={(e) => handleFieldChange(t.id, "machine_pillar", e.target.value)}
                                        style={selectStyle}
                                    >
                                        <option value="">-</option>
                                        {pillars.map((p) => (
                                            <option key={p} value={p}>{p}</option>
                                        ))}
                                    </select>
                                </td>

                                {/* Integrity */}
                                <td style={{ padding: "0.8rem" }}>
                                    <select
                                        value={t.integrity_filter || ""}
                                        onChange={(e) => handleFieldChange(t.id, "integrity_filter", e.target.value)}
                                        style={selectStyle}
                                    >
                                        <option value="">-</option>
                                        {integrity.map((i) => (
                                            <option key={i} value={i}>{i}</option>
                                        ))}
                                    </select>
                                </td>

                                {/* Trigger */}
                                <td style={{ padding: "0.8rem" }}>
                                    <select
                                        value={t.root_trigger || ""}
                                        onChange={(e) => handleFieldChange(t.id, "root_trigger", e.target.value)}
                                        style={selectStyle}
                                    >
                                        <option value="">-</option>
                                        {triggers.map((tr) => (
                                            <option key={tr} value={tr}>{tr}</option>
                                        ))}
                                    </select>
                                </td>

                                {/* Notes */}
                                <td style={{ padding: "0.8rem" }}>
                                    <input
                                        type="text"
                                        value={t.notes || ""}
                                        onChange={(e) => handleFieldChange(t.id, "notes", e.target.value)}
                                        style={inputStyle}
                                        placeholder="Add note..."
                                    />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <style>{`
                @keyframes indeterminate {
                    0% { transform: translateX(0) scaleX(0); }
                    40% { transform: translateX(0) scaleX(0.4); }
                    100% { transform: translateX(100%) scaleX(0.5); }
                }
            `}</style>
        </div>
    );
}
