"use client";

import { useState } from "react";
import { fetchInstalledModels } from "@/lib/api";
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
    const [installedModels, setInstalledModels] = useState<string[]>([]);
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

    useEffect(() => {
        // Only offer models that are really installed in Ollama.
        fetchInstalledModels()
            .then(({ models, current }) => {
                setInstalledModels(models);
                if (!localStorage.getItem("model")) setModel(current);
            })
            .catch(() => setInstalledModels([]));
    }, []);

    const handleSave = async () => {
        localStorage.setItem("apiUrl", apiUrl);
        localStorage.setItem("model", model);
        localStorage.setItem("autoRetry", String(autoRetry));

        try {
            // Post settings to backend
            const res = await fetch(`${apiUrl}/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model })
            });
            if (!res.ok) {
                const body = await res.json().catch(() => null);
                toast.error(body?.detail ?? "Backend rejected the model.");
                return;
            }
            toast.success(`Settings saved - using ${model}`);
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
        <div className="max-w-3xl space-y-6">
            {/* Page header */}
            <div>
                <h1 className="text-2xl font-bold text-foreground tracking-tight">
                    Settings
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Configure the auditor platform preferences.
                </p>
            </div>

            {/* API Configuration */}
            <div className="glass-card p-5 space-y-4">
                <div className="flex items-center gap-2">
                    <Server className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">
                        API Configuration
                    </h3>
                </div>
                <div className="space-y-3">
                    <label className="text-sm font-medium text-foreground" htmlFor="api-url">
                        Backend API URL
                    </label>
                    <input
                        id="api-url"
                        type="url"
                        value={apiUrl}
                        onChange={(e) => setApiUrl(e.target.value)}
                        className="w-full rounded-lg border border-border bg-muted/30 px-4 py-2.5 text-sm text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all"
                    />
                    <p className="text-xs text-muted-foreground">
                        The FastAPI backend endpoint for audit requests.
                    </p>
                </div>
            </div>

            {/* Model Configuration */}
            <div className="glass-card p-6 space-y-4">
                <div className="flex items-center gap-2">
                    <Brain className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">
                        Model Configuration
                    </h3>
                    <span className={`ml-auto text-xs px-2 py-1 rounded-full font-medium ${
                        ollamaStatus === "ok" ? "bg-primary/10 text-primary border border-primary/20" :
                        ollamaStatus === "error" ? "bg-red-500/10 text-red-400 border border-red-500/20" :
                        "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                    }`}>
                        {ollamaStatus === "ok" ? "Ollama Connected" :
                         ollamaStatus === "error" ? "Connection Error" : "Checking..."}
                    </span>
                </div>
                <div className="space-y-3">
                    <label className="text-sm font-medium text-foreground" htmlFor="model-select">
                        LLM Model
                    </label>
                    <select
                        id="model-select"
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        className="w-full rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all cursor-pointer"
                    >
                        {(installedModels.includes(model) ? installedModels : [model, ...installedModels]).map((m) => (
                            <option key={m} value={m}>
                                {m}
                            </option>
                        ))}
                    </select>
                    {installedModels.length > 0 && !installedModels.includes(model) && (
                        <p className="text-xs text-yellow-400">
                            {model} is not installed. Run <code>ollama pull {model}</code> first.
                        </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-2">
                        This project runs AI models locally using Ollama. The AI analysis pipeline will only work when the backend is running on a machine with Ollama installed and a model downloaded.
                    </p>
                </div>
            </div>

            {/* Preferences */}
            <div className="glass-card p-5 space-y-4">
                <div className="flex items-center gap-2">
                    <Palette className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">
                        Preferences
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
                        className={`relative h-6 w-11 rounded-full transition-colors ${autoRetry ? "bg-primary" : "bg-muted"
                            }`}
                    >
                        <span
                            className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform ${autoRetry ? "translate-x-5" : "translate-x-0"
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
                    className="flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
                >
                    <Save className="h-4 w-4" />
                    Save Settings
                </button>
                <button
                    type="button"
                    onClick={handleReset}
                    className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-6 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
                >
                    <RotateCcw className="h-4 w-4" />
                    Reset Defaults
                </button>
            </div>
        </div>
    );
}
