import { useState, useRef, useEffect } from "react";
import { api } from "../api/client";
import { UploadCloud, Check, AlertCircle, Save, FileText } from "lucide-react";

export default function Ingestion() {
    const [file, setFile] = useState(null);
    const [data, setData] = useState(null);
    const [categories, setCategories] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        api.getCategories().then((res) => setCategories(res.categories || []));
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
                // If category_suggested is UNCATEGORIZED, it needs review
                category_approved: t.category_suggested === "Uncategorized" ? "" : t.category_suggested,
            }));
            setData({ ...res, transactions: mapped });
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleCategoryChange = (id, newCategory) => {
        setData((prev) => ({
            ...prev,
            transactions: prev.transactions.map((t) =>
                t.id === id ? { ...t, category_approved: newCategory } : t
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
                    <p style={{ fontSize: "0.9rem" }}>Supports CSV, Excel, PDF</p>
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        style={{ display: "none" }}
                        accept=".csv,.xlsx,.pdf"
                    />
                </div>
                {error && <p style={{ color: "var(--status-fragile)", marginTop: "1rem" }}>{error}</p>}
            </div>
        );
    }

    return (
        <div className="container animate-fade-in">
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

            {loading && <p>Processing...</p>}

            <div className="glass-panel" style={{ borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
                    <thead>
                        <tr style={{ background: "rgba(255,255,255,0.02)", textAlign: "left" }}>
                            <th style={{ padding: "1rem" }}>Date</th>
                            <th style={{ padding: "1rem" }}>Description</th>
                            <th style={{ padding: "1rem" }}>Amount</th>
                            <th style={{ padding: "1rem" }}>Category</th>
                            <th style={{ padding: "1rem" }}>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data?.transactions?.map((t) => (
                            <tr key={t.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                                <td style={{ padding: "1rem", whiteSpace: "nowrap" }}>{t.date}</td>
                                <td style={{ padding: "1rem" }}>{t.description}</td>
                                <td style={{ padding: "1rem", fontFamily: "monospace" }}>{Number(t.amount).toFixed(2)}</td>
                                <td style={{ padding: "1rem" }}>
                                    <select
                                        value={t.category_approved || ""}
                                        onChange={(e) => handleCategoryChange(t.id, e.target.value)}
                                        style={{
                                            background: "rgba(0,0,0,0.3)",
                                            border: "1px solid var(--border-subtle)",
                                            color: "white",
                                            padding: "0.5rem",
                                            borderRadius: "6px",
                                            width: "100%",
                                        }}
                                    >
                                        <option value="">Uncategorized</option>
                                        {categories.map((c) => (
                                            <option key={c} value={c}>{c}</option>
                                        ))}
                                    </select>
                                </td>
                                <td style={{ padding: "1rem" }}>
                                    {(!t.category_approved || t.category_approved === "Uncategorized") ? (
                                        <span style={{ color: "var(--status-fragile)", display: "flex", alignItems: "center", gap: 4 }}>
                                            <AlertCircle size={14} /> Review
                                        </span>
                                    ) : (
                                        <span style={{ color: "var(--status-antifragile)", display: "flex", alignItems: "center", gap: 4 }}>
                                            <Check size={14} /> Ready
                                        </span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
