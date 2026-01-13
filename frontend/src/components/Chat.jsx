import { useState, useRef, useEffect } from "react";
import { api } from "../api/client";
import { Send, Bot, User } from "lucide-react";

export default function Chat() {
    const [messages, setMessages] = useState([
        { role: "assistant", content: "Hello! I am your AI Analyst. Ask me anything about your finances." },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = input.trim();
        setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
        setInput("");
        setLoading(true);

        try {
            const res = await api.chat(userMsg);
            setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
        } catch (err) {
            setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I encountered an error." }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container animate-fade-in" style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 100px)" }}>
            <header style={{ marginBottom: "1rem" }}>
                <h1>AI Analyst</h1>
            </header>

            <div
                className="glass-panel"
                style={{
                    flex: 1,
                    borderRadius: "var(--radius-lg)",
                    padding: "1.5rem",
                    overflowY: "auto",
                    marginBottom: "1rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "1.5rem",
                }}
            >
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        style={{
                            display: "flex",
                            alignItems: "flex-start",
                            gap: "1rem",
                            alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                            maxWidth: "80%",
                            flexDirection: msg.role === "user" ? "row-reverse" : "row",
                        }}
                    >
                        <div
                            style={{
                                width: 32,
                                height: 32,
                                borderRadius: "50%",
                                background: msg.role === "user" ? "var(--accent-primary)" : "var(--bg-card-hover)",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                flexShrink: 0,
                            }}
                        >
                            {msg.role === "user" ? <User size={18} /> : <Bot size={18} />}
                        </div>
                        <div
                            style={{
                                background: msg.role === "user" ? "var(--accent-primary)" : "var(--bg-card)",
                                padding: "1rem",
                                borderRadius: "var(--radius-md)",
                                color: "white",
                                lineHeight: 1.5,
                                fontSize: "0.95rem",
                                boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                                whiteSpace: "pre-wrap",
                            }}
                        >
                            {msg.content}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
                        <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--bg-card-hover)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <Bot size={18} />
                        </div>
                        <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>Thinking...</div>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            <form onSubmit={handleSubmit} style={{ display: "flex", gap: "1rem" }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about your spending..."
                    style={{
                        flex: 1,
                        padding: "1rem",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--border-subtle)",
                        background: "var(--bg-card)",
                        color: "white",
                        fontSize: "1rem",
                        outline: "none",
                    }}
                />
                <button
                    type="submit"
                    className="btn-primary"
                    disabled={loading}
                    style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "60px" }}
                >
                    <Send size={20} />
                </button>
            </form>
        </div>
    );
}
