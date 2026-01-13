const API_BASE = "";

/**
 * Shared API Client for Finance Proxy
 */
export const api = {
    /**
     * Check Backend Health
     */
    async getHealth() {
        const res = await fetch(`${API_BASE}/health`);
        return res.json();
    },

    /**
     * Get Audit Summary
     */
    async getAuditSummary() {
        const res = await fetch(`${API_BASE}/audit/summary`);
        if (!res.ok) throw new Error("Failed to fetch audit summary");
        return res.json();
    },

    /**
     * Upload Statement for Preview
     * @param {File} file
     */
    async ingestPreview(file) {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch(`${API_BASE}/ingest/preview`, {
            method: "POST",
            body: formData,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || res.statusText || "Failed to upload file");
        }
        return res.json();
    },

    /**
     * Commit Transactions
     * @param {Array} transactions
     */
    async ingestCommit(transactions) {
        const res = await fetch(`${API_BASE}/ingest/commit`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ transactions }),
        });
        if (!res.ok) throw new Error("Failed to commit transactions");
        return res.json();
    },

    /**
     * Chat with AI Analyst
     * @param {string} message
     */
    async chat(message) {
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ message }),
        });
        if (!res.ok) throw new Error("Chat request failed");
        return res.json();
    },

    /**
     * Get Categories List
     */
    async getCategories() {
        const res = await fetch(`${API_BASE}/categories`);
        if (!res.ok) throw new Error("Failed to fetch categories");
        return res.json();
    },
};
