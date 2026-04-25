"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchApi } from "@/lib/api";

type Project = {
    id: string;
    name: string;
    client_name: string | null;
    description: string | null;
    document_count: number;
};

export default function DashboardPage() {
    const router = useRouter();
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        const loadProjects = async () => {
            try {
                const data = await fetchApi("/projects/");
                setProjects(data);
            } catch (err: any) {
                if (err.message.includes("Could not validate credentials")) {
                    localStorage.removeItem("token");
                    router.push("/login");
                } else {
                    setError("Impossibile caricare i progetti.");
                }
            } finally {
                setLoading(false);
            }
        };
        loadProjects();
    }, [router]);

    return (
        <div className="min-h-screen bg-navy flex">
            {/* Sidebar */}
            <aside className="w-64 border-r border-gray-800 p-6 flex flex-col">
                <h2 className="text-primary font-serif text-2xl font-bold mb-10">LexShield</h2>
                <nav className="flex-1 space-y-2">
                    <Link href="/dashboard" className="block px-4 py-2 text-white bg-gray-800 rounded">
                        Dashboard
                    </Link>
                    <Link href="/upload" className="block px-4 py-2 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded">
                        Nuova Analisi
                    </Link>
                </nav>
                <button
                    onClick={() => { localStorage.removeItem("token"); router.push("/login"); }}
                    className="text-gray-500 hover:text-white text-left px-4 py-2 text-sm"
                >
                    Disconnetti
                </button>
            </aside>

            {/* Main Content */}
            <main className="flex-1 p-10">
                <div className="flex justify-between items-center mb-10">
                    <div>
                        <h1 className="text-3xl font-serif text-white mb-2">I Miei Progetti</h1>
                        <p className="text-gray-400">Gestisci e analizza i tuoi documenti legali.</p>
                    </div>
                    <Link href="/upload" className="bg-primary text-navy font-bold px-6 py-2 rounded hover:brightness-110">
                        + Nuova Analisi
                    </Link>
                </div>

                {error && <p className="text-red-400 mb-6">{error}</p>}

                {loading ? (
                    <p className="text-gray-400">Caricamento progetti...</p>
                ) : projects.length === 0 ? (
                    <div className="glass-card p-10 text-center rounded-lg border border-gray-800/50">
                        <h3 className="text-xl text-white mb-2 font-serif">Nessun progetto trovato</h3>
                        <p className="text-gray-400 mb-6">Inizia la tua prima analisi caricando un documento.</p>
                        <Link href="/upload" className="border border-primary text-primary px-6 py-2 rounded">
                            Carica Documento
                        </Link>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {projects.map((p) => (
                            <div key={p.id} className="glass-card p-6 rounded-lg border border-gray-800/50 hover:border-primary/50 transition-colors">
                                <h3 className="text-xl text-white font-serif mb-1">{p.name}</h3>
                                <p className="text-sm text-primary mb-4">{p.client_name || "Nessun cliente"}</p>
                                <div className="flex justify-between items-end">
                                    <span className="text-xs text-gray-500">{p.document_count} documenti</span>
                                    <button className="text-gray-400 hover:text-white text-sm">Apri →</button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}
