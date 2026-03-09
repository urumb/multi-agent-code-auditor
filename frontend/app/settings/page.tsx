"use client";

import { useState } from "react";
import { Save, Server, Palette, RotateCcw, Brain } from "lucide-react";
import { toast } from "sonner";

/**
 * Settings page for configuring API endpoint and platform preferences.
 */
export default function SettingsPage() {
    const [apiUrl, setApiUrl] = useState("http://localhost:8000");
    const [model, setModel] = useState("deepseek-r1:8b");
    const [autoRetry, setAutoRetry] = useState(true);

    const handleSave = () => {
        toast.success("Settings saved");
    };

    const handleReset = () => {
        setApiUrl("http://localhost:8000");
        setModel("deepseek-r1:8b");
        setAutoRetry(true);
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
            <div className="glass-card rounded-xl p-5 space-y-4">
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
            <div className="glass-card rounded-xl p-6 space-y-4">
                <div className="flex items-center gap-2">
                    <Brain className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">
                        Model Configuration
                    </h3>
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
                        <option value="deepseek-r1:8b">DeepSeek R1 (8B)</option>
                        <option value="llama3:8b">Llama 3 (8B)</option>
                        <option value="codellama:7b">CodeLlama (7B)</option>
                        <option value="mistral:7b">Mistral (7B)</option>
                    </select>
                    <p className="text-xs text-slate-400 mt-2">
                        This project runs AI models locally using Ollama. The AI analysis pipeline will only work when the backend is running on a machine with Ollama installed and a model downloaded.
                    </p>
                </div>
            </div>

            {/* Preferences */}
            <div className="glass-card rounded-xl p-5 space-y-4">
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
                    className="flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 glow-primary transition-all"
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
