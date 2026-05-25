"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { fetchApi } from "@/lib/api";


type Finding = {
    id: string;
    severity: "Critical" | "High" | "Medium" | "Low";
    category: string;
    finding_type: string;
    claim: string;
    why_weak: string;
    opponent_angle: string | null;
    strengthen_suggestion: string | null;
    attack_suggestion: string | null;
    sezione_documento: string | null;
    estratto_testo: string | null;
    cosa_manca: string | null;
    cosa_contraddetto: string | null;
    base_normativa: string | null;
    come_attacca_controparte: string | null;
    come_rafforzare: string | null;
    adattamento_contesto: string | null;
    impatto_potenziale: string | null;
    elementi_da_verificare: string | null;
    documenti_correlati: any | null;
    confidence: number;
    char_start: number | null;
    char_end: number | null;
};

type SupportDocInfo = {
    document_id: string;
    filename: string;
    role: string;
};

type Analysis = {
    id: string;
    document_id: string;
    session_id: string | null;
    status: string;
    total_score: number | null;
    analysis_mode: string | null;
    support_documents: SupportDocInfo[];
    documents_considered: any | null;
    findings: Finding[];
};

type Document = {
    id: string;
    filename: string;
    normalized_text: string | null;
    status: string;
};

const SEVERITY_COLORS = {
    Critical: "bg-red-500/20 border-red-500 text-red-400",
    High: "bg-orange-500/20 border-orange-500 text-orange-400",
    Medium: "bg-yellow-500/20 border-yellow-500 text-yellow-400",
    Low: "bg-blue-500/20 border-blue-500 text-blue-400",
};

const FINDING_TYPE_LABELS: Record<string, { label: string; color: string }> = {
    internal: { label: "Criticità Interna", color: "bg-red-900/30 text-red-300" },
    cross_document: { label: "Confronto Documentale", color: "bg-purple-900/30 text-purple-300" },
    strengthening: { label: "Da Rafforzare", color: "bg-emerald-900/30 text-emerald-300" },
    attack: { label: "Punto di Attacco", color: "bg-orange-900/30 text-orange-300" },
    normative_gap: { label: "Lacuna Normativa", color: "bg-yellow-900/30 text-yellow-300" },
};

const ROLE_LABELS: Record<string, string> = {
    atto_controparte: "Atto Controparte",
    sentenza: "Sentenza",
    provvedimento: "Provvedimento",
    contratto: "Contratto",
    allegato: "Allegato",
    comunicazione: "Comunicazione",
    memoria: "Memoria",
    documento_probatorio: "Doc. Probatorio",
    altro: "Altro",
};

export default function AnalysisWorkspacePage() {
    const { id } = useParams();
    const searchParams = useSearchParams();
    const sessionId = searchParams.get("session");
    const router = useRouter();


    const [analysis, setAnalysis] = useState<Analysis | null>(null);
    const [document, setDocument] = useState<Document | null>(null);
    const [selectedFinding, setSelectedFinding] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [filterType, setFilterType] = useState<string>("all");

    useEffect(() => {

        let interval: NodeJS.Timeout;

        const loadData = async () => {
            try {
                const docData = await fetchApi(`/documents/${id}`);
                setDocument(docData);

                if (docData.status === "processing" || docData.status === "pending") {
                    if (!interval) {
                        interval = setInterval(loadData, 3000);
                    }
                    return;
                }

                if (docData.status === "done") {
                    if (interval) clearInterval(interval);
                    // Use session endpoint if available
                    const endpoint = sessionId
                        ? `/analysis/session/${sessionId}`
                        : `/analysis/${id}`;
                    const analysisData = await fetchApi(endpoint);
                    setAnalysis(analysisData);
                    setLoading(false);
                }

                if (docData.status === "error") {
                    if (interval) clearInterval(interval);
                    setLoading(false);
                }
            } catch (err: any) {
                console.error("Failed to load analysis", err);
            }
        };

        loadData();

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [id, sessionId]);

    // Also poll session status if session ID is available
    useEffect(() => {
        if (!sessionId) return;
        let interval: NodeJS.Timeout;

        const checkSession = async () => {
            try {
                const status = await fetchApi(`/documents/session/${sessionId}/status`);
                if (status.status === "done" || status.status === "error") {
                    clearInterval(interval);
                    // Reload full data
                    const docData = await fetchApi(`/documents/${id}`);
                    setDocument(docData);
                    if (docData.status === "done") {
                        const analysisData = await fetchApi(`/analysis/session/${sessionId}`);
                        setAnalysis(analysisData);
                        setLoading(false);
                    }
                }
            } catch {
                // Ignore errors during polling
            }
        };

        interval = setInterval(checkSession, 3000);
        return () => clearInterval(interval);
    }, [sessionId, id]);



    if (loading || document?.status === "processing" || document?.status === "pending") {
        return (
            <div className="min-h-screen bg-navy flex flex-col items-center justify-center">
                <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
                <h2 className="text-xl font-serif text-white mb-2">Analisi in corso...</h2>
                <p className="text-gray-400 max-w-md text-center">
                    LexShield sta analizzando il documento {document?.filename}
                    {analysis?.support_documents && analysis.support_documents.length > 0
                        ? ` e ${analysis.support_documents.length} documenti di supporto`
                        : ""}
                    . Questa operazione può richiedere qualche minuto.
                </p>
            </div>
        );
    }

    if (document?.status === "error") {
        return (
            <div className="min-h-screen bg-navy flex flex-col items-center justify-center p-6">
                <h2 className="text-2xl font-serif text-red-500 mb-2">Errore di Analisi</h2>
                <p className="text-gray-400 mb-6">
                    Si è verificato un errore durante l'elaborazione del documento.
                </p>
                <Link
                    href="/dashboard"
                    className="bg-primary text-navy font-bold px-6 py-2 rounded"
                >
                    Torna alla Dashboard
                </Link>
            </div>
        );
    }

    // Filter findings
    const filteredFindings =
        filterType === "all"
            ? analysis?.findings || []
            : (analysis?.findings || []).filter((f) => f.finding_type === filterType);

    // Count by type
    const typeCounts: Record<string, number> = {};
    for (const f of analysis?.findings || []) {
        typeCounts[f.finding_type] = (typeCounts[f.finding_type] || 0) + 1;
    }

    return (
        <div className="h-screen flex flex-col bg-navy overflow-hidden">
            {/* Header */}
            <header className="h-auto min-h-[64px] border-b border-gray-800 px-4 py-3 flex flex-wrap justify-between items-center bg-navy z-10 gap-2">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard" className="text-gray-400 hover:text-white">
                        ← Indietro
                    </Link>
                    <h1 className="text-white font-serif text-lg truncate max-w-[300px]">
                        {document?.filename}
                    </h1>
                    {analysis?.analysis_mode && (
                        <span className="text-xs px-2 py-1 rounded bg-primary/10 text-primary">
                            {analysis.analysis_mode === "atto_iniziale"
                                ? "📄 Atto Iniziale"
                                : "⚔️ Contestazione"}
                        </span>
                    )}
                </div>
                <div className="flex gap-3 items-center">
                    {analysis?.support_documents && analysis.support_documents.length > 0 && (
                        <span className="text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded">
                            {analysis.support_documents.length} doc. supporto
                        </span>
                    )}
                    <span className="text-primary font-bold text-sm">
                        Score: {analysis?.total_score?.toFixed(0)}/100
                    </span>
                    <button
                        onClick={() =>
                            window.open(
                                `http://localhost:8000/analysis/${id}/report`,
                                "_blank"
                            )
                        }
                        className="bg-primary text-navy font-bold px-4 py-2 rounded text-sm hover:brightness-110"
                    >
                        Esporta PDF
                    </button>
                </div>
            </header>

            {/* Support docs bar (if any) */}
            {analysis?.support_documents && analysis.support_documents.length > 0 && (
                <div className="bg-[#0f121d] border-b border-gray-800 px-4 py-2 flex gap-3 items-center overflow-x-auto">
                    <span className="text-gray-500 text-xs whitespace-nowrap">
                        Documenti considerati:
                    </span>
                    {analysis.support_documents.map((sd) => (
                        <span
                            key={sd.document_id}
                            className="text-xs bg-gray-800 text-gray-300 px-2 py-1 rounded whitespace-nowrap"
                        >
                            {sd.filename}{" "}
                            <span className="text-primary">
                                ({ROLE_LABELS[sd.role] || sd.role})
                            </span>
                        </span>
                    ))}
                </div>
            )}

            {/* Workspace Split View */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Panel: Document Text */}
                <div className="w-1/2 md:w-3/5 border-r border-gray-800 overflow-y-auto p-8 relative scroll-smooth bg-[#0f121d]">
                    {document?.normalized_text ? (
                        <div className="text-gray-300 font-serif text-lg leading-relaxed whitespace-pre-wrap">
                            {document.normalized_text}
                        </div>
                    ) : (
                        <p className="text-gray-500">
                            Testo del documento non disponibile.
                        </p>
                    )}
                </div>

                {/* Right Panel: Findings */}
                <div className="w-1/2 md:w-2/5 overflow-y-auto bg-navy">
                    {/* Filter bar */}
                    <div className="sticky top-0 bg-navy z-10 p-4 pb-2 border-b border-gray-800">
                        <h2 className="text-xl font-serif text-white mb-3">
                            Rilievi ({analysis?.findings?.length || 0})
                        </h2>
                        <div className="flex flex-wrap gap-2">
                            <button
                                onClick={() => setFilterType("all")}
                                className={`text-xs px-3 py-1 rounded transition-all ${
                                    filterType === "all"
                                        ? "bg-primary text-navy font-bold"
                                        : "bg-gray-800 text-gray-400 hover:text-white"
                                }`}
                            >
                                Tutti
                            </button>
                            {Object.entries(FINDING_TYPE_LABELS).map(([type, { label }]) =>
                                typeCounts[type] ? (
                                    <button
                                        key={type}
                                        onClick={() => setFilterType(type)}
                                        className={`text-xs px-3 py-1 rounded transition-all ${
                                            filterType === type
                                                ? "bg-primary text-navy font-bold"
                                                : "bg-gray-800 text-gray-400 hover:text-white"
                                        }`}
                                    >
                                        {label} ({typeCounts[type]})
                                    </button>
                                ) : null
                            )}
                        </div>
                    </div>

                    {/* Finding cards */}
                    <div className="p-4 space-y-4">
                        {filteredFindings.map((f) => {
                            const isExpanded = selectedFinding === f.id;
                            const typeInfo =
                                FINDING_TYPE_LABELS[f.finding_type] ||
                                FINDING_TYPE_LABELS.internal;

                            return (
                                <div
                                    key={f.id}
                                    onClick={() =>
                                        setSelectedFinding(isExpanded ? null : f.id)
                                    }
                                    className={`glass-card rounded-lg border cursor-pointer transition-all ${
                                        isExpanded
                                            ? "border-primary shadow-[0_0_15px_rgba(201,168,76,0.15)]"
                                            : "border-gray-800 hover:border-gray-600"
                                    }`}
                                >
                                    {/* Header */}
                                    <div className="p-4 pb-3">
                                        <div className="flex justify-between items-start mb-2 gap-2">
                                            <div className="flex flex-wrap gap-2">
                                                <span
                                                    className={`text-xs px-2 py-0.5 rounded ${typeInfo.color}`}
                                                >
                                                    {typeInfo.label}
                                                </span>
                                                <span className="text-white font-medium text-xs bg-gray-800 px-2 py-0.5 rounded">
                                                    {f.category}
                                                </span>
                                            </div>
                                            <span
                                                className={`text-xs font-bold border rounded px-2 py-0.5 shrink-0 ${
                                                    SEVERITY_COLORS[f.severity]
                                                }`}
                                            >
                                                {f.severity.toUpperCase()}
                                            </span>
                                        </div>

                                        {/* Claim excerpt */}
                                        <p className="text-gray-300 text-sm italic border-l-2 border-primary pl-3 bg-[#0f121d] p-2 rounded-r">
                                            &quot;...{f.claim.slice(0, 200)}
                                            {f.claim.length > 200 ? "..." : ""}&quot;
                                        </p>
                                    </div>

                                    {/* Core info (always visible) */}
                                    <div className="px-4 pb-4 space-y-3">
                                        <div>
                                            <h4 className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">
                                                Problema
                                            </h4>
                                            <p className="text-sm text-gray-300">
                                                {f.why_weak}
                                            </p>
                                        </div>

                                        {/* Expanded content */}
                                        {isExpanded && (
                                            <div className="space-y-3 pt-2 border-t border-gray-800">
                                                {/* Cosa manca */}
                                                {f.cosa_manca && (
                                                    <div>
                                                        <h4 className="text-xs text-yellow-500 uppercase font-bold tracking-wider mb-1">
                                                            Cosa Manca
                                                        </h4>
                                                        <p className="text-sm text-yellow-200/80">
                                                            {f.cosa_manca}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* Base normativa */}
                                                {f.base_normativa && (
                                                    <div className="bg-indigo-950/30 p-3 rounded border border-indigo-800/30">
                                                        <h4 className="text-xs text-indigo-400 uppercase font-bold tracking-wider mb-1">
                                                            Base Normativa
                                                        </h4>
                                                        <p className="text-sm text-indigo-200/80">
                                                            {f.base_normativa}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* Come attacca la controparte / Opponent angle */}
                                                {(f.come_attacca_controparte ||
                                                    f.opponent_angle) && (
                                                    <div>
                                                        <h4 className="text-xs text-red-500 uppercase font-bold tracking-wider mb-1">
                                                            Come Attacca la Controparte
                                                        </h4>
                                                        <p className="text-sm text-red-200/80">
                                                            {f.come_attacca_controparte ||
                                                                f.opponent_angle}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* Come rafforzare */}
                                                {(f.come_rafforzare ||
                                                    f.strengthen_suggestion) && (
                                                    <div className="bg-primary/5 p-3 rounded">
                                                        <h4 className="text-xs text-primary uppercase font-bold tracking-wider mb-1">
                                                            Come Rafforzare
                                                        </h4>
                                                        <p className="text-sm text-primary/90">
                                                            {f.come_rafforzare ||
                                                                f.strengthen_suggestion}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* Attack suggestion */}
                                                {f.attack_suggestion && (
                                                    <div className="bg-orange-950/20 p-3 rounded">
                                                        <h4 className="text-xs text-orange-400 uppercase font-bold tracking-wider mb-1">
                                                            Strategia di Attacco
                                                        </h4>
                                                        <p className="text-sm text-orange-200/80">
                                                            {f.attack_suggestion}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* Impatto potenziale */}
                                                {f.impatto_potenziale && (
                                                    <div>
                                                        <h4 className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">
                                                            Impatto Potenziale
                                                        </h4>
                                                        <p className="text-sm text-gray-300">
                                                            {f.impatto_potenziale}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* Documenti correlati */}
                                                {f.documenti_correlati &&
                                                    Array.isArray(f.documenti_correlati) &&
                                                    f.documenti_correlati.length > 0 && (
                                                        <div className="bg-purple-950/20 p-3 rounded border border-purple-800/20">
                                                            <h4 className="text-xs text-purple-400 uppercase font-bold tracking-wider mb-2">
                                                                Documenti Considerati
                                                            </h4>
                                                            <div className="space-y-1">
                                                                {f.documenti_correlati.map(
                                                                    (dc: any, i: number) => (
                                                                        <div
                                                                            key={i}
                                                                            className="flex justify-between text-xs"
                                                                        >
                                                                            <span className="text-purple-200">
                                                                                {dc.filename}
                                                                            </span>
                                                                            <span className="text-purple-400">
                                                                                {dc.relevance ||
                                                                                    dc.role}
                                                                            </span>
                                                                        </div>
                                                                    )
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}

                                                {/* Elementi da verificare */}
                                                {f.elementi_da_verificare && (
                                                    <div className="bg-amber-950/20 p-3 rounded border border-amber-800/20">
                                                        <h4 className="text-xs text-amber-400 uppercase font-bold tracking-wider mb-1">
                                                            ⚠ Da Verificare (Professionista)
                                                        </h4>
                                                        <p className="text-sm text-amber-200/80">
                                                            {f.elementi_da_verificare}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* Confidence */}
                                                <div className="flex items-center gap-3 pt-2">
                                                    <span className="text-xs text-gray-500">
                                                        Confidenza:{" "}
                                                        {(f.confidence * 100).toFixed(0)}%
                                                    </span>
                                                    <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                                                        <div
                                                            className="bg-primary h-1.5 rounded-full transition-all"
                                                            style={{
                                                                width: `${f.confidence * 100}%`,
                                                            }}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Expand indicator */}
                                        <div className="text-center">
                                            <span className="text-gray-600 text-xs">
                                                {isExpanded
                                                    ? "▲ Chiudi dettagli"
                                                    : "▼ Mostra dettagli"}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}
