"use client";

import { useState } from "react";
import { Save, Server, Palette, RotateCcw, Brain } from "lucide-react";
import { toast } from "sonner";

/**
 * Settings page for configuring API endpoint and platform preferences.
 */
import { useEffect } from "react";

export default function SettingsPage() {
    const [apiUrl, setApiUrl] = useState("http://localhost:8000");
    const [model, setModel] = useState("llama3.2");
    const [autoRetry, setAutoRetry] = useState(true);
    const [ollamaStatus, setOllamaStatus] = useState<"checking" | "ok" | "error">("checking");

    const checkOllamaConnection = async () => {
        setOllamaStatus("checking");
        try {
            // We'll test against the backend health check to confirm backend is up.
            // In a real app we might have a specific endpoint to test ollama.
            const url = localStorage.getItem("apiUrl") || "http://localhost:8000";
            const response = await fetch(`${url}/settings/ollama`);
            if (response.ok) {
                setOllamaStatus("ok");
            } else {
                setOllamaStatus("error");
            }
        } catch {
            setOllamaStatus("error");
        }
    };

    useEffect(() => {
        // Test Ollama connection initially
        checkOllamaConnection();
    }, []);

    useEffect(() => {
        // Load settings from localStorage
        const storedApiUrl = localStorage.getItem("apiUrl");
        if (storedApiUrl && storedApiUrl !== apiUrl) setApiUrl(storedApiUrl);

        const storedModel = localStorage.getItem("model");
        if (storedModel && storedModel !== model) setModel(storedModel);

        const storedAutoRetry = localStorage.getItem("autoRetry");
        if (storedAutoRetry !== null) {
            const isRetry = storedAutoRetry === "true";
            if (isRetry !== autoRetry) setAutoRetry(isRetry);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleSave = async () => {
        localStorage.setItem("apiUrl", apiUrl);
        localStorage.setItem("model", model);
        localStorage.setItem("autoRetry", String(autoRetry));

        try {
            // Post settings to backend
            await fetch(`${apiUrl}/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model })
            });
            toast.success("Settings saved");
            checkOllamaConnection();
        } catch {
            toast.error("Settings saved locally, but failed to sync with backend.");
        }
    };

    const handleReset = () => {
        setApiUrl("http://localhost:8000");
        setModel("llama3.2");
        setAutoRetry(true);
        localStorage.removeItem("apiUrl");
        localStorage.removeItem("model");
        localStorage.removeItem("autoRetry");
        toast.info("Settings reset to defaults");
    };

    return (
        <div className="max-w-3xl space-y-8">
            {/* Page header */}
            <div>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    Settings
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Configure the auditor platform preferences.
                </p>
            </div>

            {/* API Configuration */}
            <div className="glass-card p-6 space-y-5">
                <div className="flex items-center gap-2 border-b border-border pb-4">
                    <Server className="h-4 w-4 text-muted-foreground" />
                    <h3 className="text-sm font-semibold text-foreground">
                        General Configuration
                    </h3>
                </div>
                <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground" htmlFor="api-url">
                        Backend API URL
                    </label>
                    <input
                        id="api-url"
                        type="url"
                        value={apiUrl}
                        onChange={(e) => setApiUrl(e.target.value)}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground font-mono focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all"
                    />
                    <p className="text-xs text-muted-foreground">
                        The FastAPI backend endpoint for audit requests.
                    </p>
                </div>
            </div>

            {/* Model Configuration */}
            <div className="glass-card p-6 space-y-5">
                <div className="flex items-center gap-2 border-b border-border pb-4">
                    <Brain className="h-4 w-4 text-muted-foreground" />
                    <h3 className="text-sm font-semibold text-foreground">
                        Local AI Models
                    </h3>
                    <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                        ollamaStatus === "ok" ? "bg-primary/10 text-primary border border-primary/20" :
                        ollamaStatus === "error" ? "bg-destructive/10 text-destructive border border-destructive/20" :
                        "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                    }`}>
                        {ollamaStatus === "ok" ? "Ollama Connected" :
                         ollamaStatus === "error" ? "Connection Error" : "Checking..."}
                    </span>
                </div>
                <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground" htmlFor="model-select">
                        Active Model
                    </label>
                    <select
                        id="model-select"
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all cursor-pointer"
                    >
                        <option value="deepseek-r1:8b">DeepSeek R1 (8B)</option>
                        <option value="llama3.2">Llama 3.2</option>
                        <option value="llama3:8b">Llama 3 (8B)</option>
                        <option value="codellama:7b">CodeLlama (7B)</option>
                        <option value="mistral:7b">Mistral (7B)</option>
                    </select>
                    <p className="text-xs text-muted-foreground mt-2">
                        This project runs AI models locally using Ollama. The AI analysis pipeline will only work when the backend is running on a machine with Ollama installed and a model downloaded.
                    </p>
                </div>
            </div>

            {/* Preferences */}
            <div className="glass-card p-6 space-y-5">
                <div className="flex items-center gap-2 border-b border-border pb-4">
                    <Palette className="h-4 w-4 text-muted-foreground" />
                    <h3 className="text-sm font-semibold text-foreground">
                        Appearance & Behavior
                    </h3>
                </div>
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm font-medium text-foreground">Auto-retry on failure</p>
                        <p className="text-xs text-muted-foreground">
                            Automatically retry failed audits once.
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={() => setAutoRetry(!autoRetry)}
                        className={`relative h-5 w-9 rounded-full transition-colors ${autoRetry ? "bg-primary" : "bg-secondary"
                            }`}
                    >
                        <span
                            className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white transition-transform ${autoRetry ? "translate-x-4" : "translate-x-0"
                                }`}
                        />
                    </button>
                </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
                <button
                    type="button"
                    onClick={handleSave}
                    className="flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    <Save className="h-4 w-4" />
                    Save Settings
                </button>
                <button
                    type="button"
                    onClick={handleReset}
                    className="flex items-center gap-2 rounded-md border border-border bg-secondary/50 px-5 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                >
                    <RotateCcw className="h-4 w-4" />
                    Reset Defaults
                </button>
            </div>
        </div>
    );
}
