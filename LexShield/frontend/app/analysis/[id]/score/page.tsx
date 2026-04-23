"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { fetchApi } from "@/lib/api";

type Analysis = {
    id: string;
    document_id: string;
    total_score: number;
    subscores: Record<string, number>;
    score_breakdown: any;
};

export default function ScorePage() {
    const { id } = useParams();
    const [analysis, setAnalysis] = useState<Analysis | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadAnalysis = async () => {
            try {
                const data = await fetchApi(`/analysis/${id}`);
                setAnalysis(data);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        loadAnalysis();
    }, [id]);

    if (loading) return <div className="min-h-screen bg-navy text-white flex justify-center items-center">Caricamento score...</div>;
    if (!analysis) return <div className="min-h-screen bg-navy text-white p-10">Analisi non trovata.</div>;

    const scoreLabel = analysis.score_breakdown?.score_label || "Score";
    const scoreColor = analysis.total_score >= 70 ? "text-green-400" : analysis.total_score >= 50 ? "text-yellow-400" : "text-red-500";

    return (
        <div className="min-h-screen bg-navy flex flex-col p-8 items-center">
            <header className="w-full max-w-4xl flex justify-between mb-12">
                <Link href={`/analysis/${id}`} className="text-gray-400 hover:text-white">← Torna al Workspace</Link>
                <button
                    onClick={() => window.open(`http://localhost:8000/analysis/${id}/report`, "_blank")}
                    className="text-primary hover:underline"
                >
                    Scarica PDF Report
                </button>
            </header>

            <div className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-2 gap-12">

                {/* Main Score UI */}
                <div className="flex flex-col items-center justify-center glass-card p-12 rounded-full aspect-square border-primary/30 max-w-sm mx-auto relative shadow-[0_0_50px_rgba(201,168,76,0.1)]">
                    <div className="text-gray-400 uppercase tracking-widest text-sm mb-2">LexShield Score</div>
                    <div className={`text-8xl font-serif font-bold ${scoreColor}`}>
                        {analysis.total_score}
                    </div>
                    <div className="text-gray-300 text-xl font-serif mt-2">{scoreLabel}</div>
                </div>

                {/* Breakdown */}
                <div className="flex flex-col justify-center space-y-6">
                    <h2 className="text-2xl font-serif text-white mb-2">Dimensioni di Rischio</h2>

                    {Object.entries(analysis.subscores || {}).map(([dim, score]) => (
                        <div key={dim} className="space-y-1">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-300 capitalize">{dim.replace("_", " ")}</span>
                                <span className="text-white font-bold">{score}/100</span>
                            </div>
                            <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                                <div
                                    className={`h-full ${score >= 70 ? "bg-green-500" : score >= 50 ? "bg-yellow-500" : "bg-red-500"}`}
                                    style={{ width: `${score}%` }}
                                />
                            </div>
                        </div>
                    ))}

                    <div className="mt-8 pt-6 border-t border-gray-800 flex gap-6">
                        <div className="text-center">
                            <div className="text-3xl font-bold text-red-500">{analysis.score_breakdown.critical_count}</div>
                            <div className="text-xs text-gray-500 uppercase mt-1">Criticità Gravi</div>
                        </div>
                        <div className="text-center">
                            <div className="text-3xl font-bold text-orange-500">{analysis.score_breakdown.high_count}</div>
                            <div className="text-xs text-gray-500 uppercase mt-1">Rischio Alto</div>
                        </div>
                        <div className="text-center">
                            <div className="text-3xl font-bold text-primary">{analysis.score_breakdown.total_findings}</div>
                            <div className="text-xs text-gray-500 uppercase mt-1">Totale Findings</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
