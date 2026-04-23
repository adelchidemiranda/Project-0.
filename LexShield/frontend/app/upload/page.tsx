"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchApi } from "@/lib/api";

// Document role options for support files
const SUPPORT_ROLES = [
    { value: "atto_controparte", label: "Atto Controparte" },
    { value: "sentenza", label: "Sentenza" },
    { value: "provvedimento", label: "Provvedimento" },
    { value: "contratto", label: "Contratto" },
    { value: "allegato", label: "Allegato" },
    { value: "comunicazione", label: "Comunicazione" },
    { value: "memoria", label: "Memoria" },
    { value: "documento_probatorio", label: "Documento Probatorio" },
    { value: "altro", label: "Altro Documento" },
];

const DOC_TYPES = [
    { value: "contratto", label: "Contratto / Accordo" },
    { value: "atto", label: "Atto Giudiziario (Citazione, Ricorso)" },
    { value: "memoria", label: "Memoria / Comparsa" },
    { value: "diffida", label: "Lettera Formale / Diffida" },
    { value: "parere", label: "Parere Legale" },
    { value: "ricorso", label: "Ricorso" },
    { value: "citazione", label: "Citazione" },
    { value: "comparsa", label: "Comparsa" },
    { value: "altro", label: "Altro" },
];

type SupportFile = {
    id: string;
    file: File;
    role: string;
};

export default function UploadPage() {
    const router = useRouter();
    const [step, setStep] = useState(1);

    // Step 1: Mode
    const [mode, setMode] = useState<"atto_iniziale" | "contestazione" | null>(null);

    // Step 2: Main document
    const [mainFile, setMainFile] = useState<File | null>(null);
    const [pastedText, setPastedText] = useState("");
    const [docType, setDocType] = useState("atto");

    // Step 3: Support documents
    const [supportFiles, setSupportFiles] = useState<SupportFile[]>([]);

    // State
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const addSupportFile = (file: File) => {
        setSupportFiles((prev) => [
            ...prev,
            { id: crypto.randomUUID(), file, role: "allegato" },
        ]);
    };

    const removeSupportFile = (id: string) => {
        setSupportFiles((prev) => prev.filter((f) => f.id !== id));
    };

    const updateSupportRole = (id: string, role: string) => {
        setSupportFiles((prev) =>
            prev.map((f) => (f.id === id ? { ...f, role } : f))
        );
    };

    const handleSubmit = async () => {
        if (!mode) return;
        if (!mainFile && !pastedText) {
            setError("Inserisci un testo o carica un file principale");
            return;
        }

        setLoading(true);
        setError("");

        try {
            const formData = new FormData();
            formData.append("mode", mode);
            if (mainFile) formData.append("main_file", mainFile);
            if (pastedText) formData.append("main_pasted_text", pastedText);
            formData.append("main_doc_type", docType);
            formData.append("language", "it");
            formData.append("jurisdiction", "IT");

            // Add support files
            for (const sf of supportFiles) {
                formData.append("support_files", sf.file);
            }
            // Add roles as comma-separated string
            if (supportFiles.length > 0) {
                formData.append(
                    "support_roles",
                    supportFiles.map((sf) => sf.role).join(",")
                );
            }

            const response = await fetchApi("/documents/analyze-session", {
                method: "POST",
                body: formData,
            });

            // Redirect to analysis page with session_id
            router.push(`/analysis/${response.main_document_id}?session=${response.session_id}`);
        } catch (err: any) {
            setError(err.message || "Errore durante l'invio");
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-navy flex flex-col">
            <header className="border-b border-gray-800 p-4 flex justify-between items-center bg-navy/80 backdrop-blur z-10 sticky top-0">
                <Link href="/dashboard" className="text-primary font-serif font-bold text-xl">
                    LexShield
                </Link>
                <Link href="/dashboard" className="text-gray-400 hover:text-white text-sm">
                    Annulla
                </Link>
            </header>

            <main className="flex-1 p-6 flex justify-center items-start pt-10">
                <div className="max-w-3xl w-full">
                    {/* Progress indicator */}
                    <div className="flex items-center gap-2 mb-8 justify-center">
                        {[1, 2, 3, 4].map((s) => (
                            <div key={s} className="flex items-center gap-2">
                                <div
                                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                                        step >= s
                                            ? "bg-primary text-navy"
                                            : "bg-gray-800 text-gray-500"
                                    }`}
                                >
                                    {s}
                                </div>
                                {s < 4 && (
                                    <div
                                        className={`w-12 h-0.5 ${
                                            step > s ? "bg-primary" : "bg-gray-800"
                                        }`}
                                    />
                                )}
                            </div>
                        ))}
                    </div>

                    {error && <p className="text-red-400 mb-6 text-center">{error}</p>}

                    {/* STEP 1: Mode Selection */}
                    {step === 1 && (
                        <div className="space-y-6">
                            <h1 className="text-3xl font-serif text-white text-center mb-2">
                                Seleziona la Modalità di Analisi
                            </h1>
                            <p className="text-gray-400 text-center text-sm mb-8">
                                Scegli il tipo di analisi in base al tuo obiettivo
                            </p>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Atto Iniziale card */}
                                <button
                                    onClick={() => {
                                        setMode("atto_iniziale");
                                        setStep(2);
                                    }}
                                    className={`glass-card p-8 rounded-lg text-left transition-all hover:border-primary/60 border-2 ${
                                        mode === "atto_iniziale"
                                            ? "border-primary shadow-[0_0_20px_rgba(201,168,76,0.15)]"
                                            : "border-transparent"
                                    }`}
                                >
                                    <div className="text-3xl mb-4">📄</div>
                                    <h3 className="text-xl font-serif text-white mb-3">
                                        Atto Iniziale
                                    </h3>
                                    <p className="text-gray-400 text-sm leading-relaxed">
                                        Analizza un atto o documento autonomo. Ideale per
                                        verificare un atto prima del deposito: trova debolezze,
                                        lacune argomentative e punti da rafforzare.
                                    </p>
                                    <div className="mt-4 flex flex-wrap gap-2">
                                        <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                                            Verifica pre-deposito
                                        </span>
                                        <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                                            Quality check
                                        </span>
                                    </div>
                                </button>

                                {/* Contestazione card */}
                                <button
                                    onClick={() => {
                                        setMode("contestazione");
                                        setStep(2);
                                    }}
                                    className={`glass-card p-8 rounded-lg text-left transition-all hover:border-primary/60 border-2 ${
                                        mode === "contestazione"
                                            ? "border-primary shadow-[0_0_20px_rgba(201,168,76,0.15)]"
                                            : "border-transparent"
                                    }`}
                                >
                                    <div className="text-3xl mb-4">⚔️</div>
                                    <h3 className="text-xl font-serif text-white mb-3">
                                        Contestazione a un Altro Atto
                                    </h3>
                                    <p className="text-gray-400 text-sm leading-relaxed">
                                        Analizza il tuo documento nel contesto dell'atto
                                        avversario e dei documenti allegati. Individua
                                        incongruenze, punti scoperti e contraddizioni cross-documentali.
                                    </p>
                                    <div className="mt-4 flex flex-wrap gap-2">
                                        <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                                            Confronto documentale
                                        </span>
                                        <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                                            Cross-reference
                                        </span>
                                    </div>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* STEP 2: Main Document Upload */}
                    {step === 2 && (
                        <div className="space-y-6">
                            <h1 className="text-3xl font-serif text-white text-center mb-2">
                                Documento Principale
                            </h1>
                            <p className="text-gray-400 text-center text-sm mb-6">
                                Carica l'atto o documento da analizzare
                            </p>

                            <div className="glass-card p-8 rounded-lg space-y-6">
                                {/* File upload */}
                                <div className="border-2 border-dashed border-gray-700 rounded-lg p-8 text-center hover:border-primary/50 transition-colors relative cursor-pointer">
                                    <input
                                        type="file"
                                        accept=".pdf,.docx,.txt"
                                        onChange={(e) => {
                                            setMainFile(e.target.files?.[0] || null);
                                            setPastedText("");
                                        }}
                                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                    />
                                    <div className="pointer-events-none">
                                        <p className="text-gray-300 text-lg mb-2">
                                            {mainFile
                                                ? `✓ ${mainFile.name}`
                                                : "Trascina qui il file (PDF, DOCX, TXT) o clicca"}
                                        </p>
                                        <p className="text-gray-500 text-sm">
                                            Supporta file fino a 10MB
                                        </p>
                                    </div>
                                </div>

                                <div className="text-center text-gray-500 my-2">OPPURE</div>

                                <textarea
                                    value={pastedText}
                                    onChange={(e) => {
                                        setPastedText(e.target.value);
                                        setMainFile(null);
                                    }}
                                    placeholder="Incolla qui il testo del tuo documento..."
                                    className="w-full h-40 bg-[#0f121d] border border-gray-700 rounded p-4 text-gray-300 focus:outline-none focus:border-primary resize-y"
                                />

                                {/* Doc type */}
                                <div>
                                    <label className="block text-gray-400 text-sm mb-2">
                                        Tipo Documento
                                    </label>
                                    <select
                                        value={docType}
                                        onChange={(e) => setDocType(e.target.value)}
                                        className="w-full bg-[#0f121d] border border-gray-700 rounded p-3 text-white focus:outline-none focus:border-primary"
                                    >
                                        {DOC_TYPES.map((dt) => (
                                            <option key={dt.value} value={dt.value}>
                                                {dt.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="flex gap-4">
                                <button
                                    onClick={() => setStep(1)}
                                    className="flex-1 border border-gray-700 text-gray-400 py-3 rounded hover:bg-gray-800 transition-all"
                                >
                                    ← Indietro
                                </button>
                                <button
                                    onClick={() => {
                                        if (!mainFile && !pastedText) {
                                            setError("Carica un file o incolla il testo");
                                            return;
                                        }
                                        setError("");
                                        setStep(3);
                                    }}
                                    className="flex-1 bg-primary text-navy font-bold py-3 rounded hover:brightness-110 transition-all"
                                >
                                    Continua →
                                </button>
                            </div>
                        </div>
                    )}

                    {/* STEP 3: Support Documents */}
                    {step === 3 && (
                        <div className="space-y-6">
                            <h1 className="text-3xl font-serif text-white text-center mb-2">
                                Documenti di Supporto
                            </h1>
                            <p className="text-gray-400 text-center text-sm mb-6">
                                {mode === "contestazione"
                                    ? "Carica l'atto della controparte, sentenze, allegati e altri documenti di riferimento"
                                    : "Aggiungi documenti di contesto per un'analisi più accurata (opzionale)"}
                            </p>

                            <div className="glass-card p-6 rounded-lg">
                                {/* Add support file */}
                                <div className="border-2 border-dashed border-gray-700 rounded-lg p-6 text-center hover:border-primary/50 transition-colors relative cursor-pointer mb-6">
                                    <input
                                        type="file"
                                        accept=".pdf,.docx,.txt"
                                        multiple
                                        onChange={(e) => {
                                            if (e.target.files) {
                                                Array.from(e.target.files).forEach(addSupportFile);
                                            }
                                            e.target.value = "";
                                        }}
                                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                    />
                                    <div className="pointer-events-none">
                                        <p className="text-gray-300 mb-1">
                                            + Aggiungi documenti di supporto
                                        </p>
                                        <p className="text-gray-500 text-xs">
                                            PDF, DOCX, TXT • Puoi aggiungerne più di uno
                                        </p>
                                    </div>
                                </div>

                                {/* List of support files */}
                                {supportFiles.length === 0 ? (
                                    <div className="text-center py-6 text-gray-500">
                                        <p className="text-sm">
                                            Nessun documento di supporto aggiunto
                                        </p>
                                        <p className="text-xs mt-1">
                                            Puoi procedere senza documenti di supporto
                                        </p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {supportFiles.map((sf) => (
                                            <div
                                                key={sf.id}
                                                className="flex items-center gap-4 bg-[#0f121d] p-4 rounded-lg border border-gray-800"
                                            >
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-white text-sm truncate">
                                                        {sf.file.name}
                                                    </p>
                                                    <p className="text-gray-500 text-xs">
                                                        {(sf.file.size / 1024).toFixed(0)} KB
                                                    </p>
                                                </div>
                                                <select
                                                    value={sf.role}
                                                    onChange={(e) =>
                                                        updateSupportRole(sf.id, e.target.value)
                                                    }
                                                    className="bg-navy border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-primary min-w-[180px]"
                                                >
                                                    {SUPPORT_ROLES.map((r) => (
                                                        <option key={r.value} value={r.value}>
                                                            {r.label}
                                                        </option>
                                                    ))}
                                                </select>
                                                <button
                                                    onClick={() => removeSupportFile(sf.id)}
                                                    className="text-red-400 hover:text-red-300 text-sm px-2"
                                                >
                                                    ✕
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-4">
                                <button
                                    onClick={() => setStep(2)}
                                    className="flex-1 border border-gray-700 text-gray-400 py-3 rounded hover:bg-gray-800 transition-all"
                                >
                                    ← Indietro
                                </button>
                                <button
                                    onClick={() => setStep(4)}
                                    className="flex-1 bg-primary text-navy font-bold py-3 rounded hover:brightness-110 transition-all"
                                >
                                    Riepilogo →
                                </button>
                            </div>
                        </div>
                    )}

                    {/* STEP 4: Review & Submit */}
                    {step === 4 && (
                        <div className="space-y-6">
                            <h1 className="text-3xl font-serif text-white text-center mb-2">
                                Riepilogo Analisi
                            </h1>
                            <p className="text-gray-400 text-center text-sm mb-6">
                                Verifica i dati e avvia l'analisi
                            </p>

                            <div className="glass-card p-6 rounded-lg space-y-5">
                                {/* Mode */}
                                <div className="flex justify-between items-center border-b border-gray-800 pb-4">
                                    <span className="text-gray-400 text-sm">Modalità</span>
                                    <span className="text-white font-medium">
                                        {mode === "atto_iniziale"
                                            ? "📄 Atto Iniziale"
                                            : "⚔️ Contestazione"}
                                    </span>
                                </div>

                                {/* Main document */}
                                <div className="flex justify-between items-center border-b border-gray-800 pb-4">
                                    <span className="text-gray-400 text-sm">Documento Principale</span>
                                    <span className="text-white text-sm truncate max-w-[300px]">
                                        {mainFile
                                            ? mainFile.name
                                            : `Testo incollato (${pastedText.length} caratteri)`}
                                    </span>
                                </div>

                                {/* Doc type */}
                                <div className="flex justify-between items-center border-b border-gray-800 pb-4">
                                    <span className="text-gray-400 text-sm">Tipo Documento</span>
                                    <span className="text-white text-sm">
                                        {DOC_TYPES.find((d) => d.value === docType)?.label || docType}
                                    </span>
                                </div>

                                {/* Support docs */}
                                <div>
                                    <span className="text-gray-400 text-sm block mb-3">
                                        Documenti di Supporto ({supportFiles.length})
                                    </span>
                                    {supportFiles.length === 0 ? (
                                        <p className="text-gray-500 text-sm">
                                            Nessun documento di supporto
                                        </p>
                                    ) : (
                                        <div className="space-y-2">
                                            {supportFiles.map((sf) => (
                                                <div
                                                    key={sf.id}
                                                    className="flex justify-between items-center bg-[#0f121d] px-4 py-2 rounded"
                                                >
                                                    <span className="text-white text-sm truncate max-w-[250px]">
                                                        {sf.file.name}
                                                    </span>
                                                    <span className="text-primary text-xs">
                                                        {SUPPORT_ROLES.find((r) => r.value === sf.role)?.label}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="flex gap-4">
                                <button
                                    onClick={() => setStep(3)}
                                    className="flex-1 border border-gray-700 text-gray-400 py-3 rounded hover:bg-gray-800 transition-all"
                                >
                                    ← Modifica
                                </button>
                                <button
                                    onClick={handleSubmit}
                                    disabled={loading}
                                    className="flex-1 bg-primary text-navy font-bold py-4 rounded text-lg hover:brightness-110 transition-all disabled:opacity-50"
                                >
                                    {loading ? (
                                        <span className="flex items-center justify-center gap-2">
                                            <span className="w-5 h-5 border-2 border-navy/30 border-t-navy rounded-full animate-spin"></span>
                                            Invio in corso...
                                        </span>
                                    ) : (
                                        "🔍 Avvia Analisi AI"
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
