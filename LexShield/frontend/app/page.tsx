"use client";

import { motion } from "framer-motion";
import Link from "next/link";

export default function Home() {
    return (
        <main className="min-h-screen bg-navy flex flex-col items-center justify-center p-6 text-center">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
                className="max-w-4xl"
            >
                <span className="text-primary tracking-widest uppercase text-sm mb-4 block">
                    Intelligenza Artificiale Forense
                </span>
                <h1 className="text-6xl md:text-8xl font-serif font-bold text-white mb-6">
                    LexShield
                </h1>
                <p className="text-xl md:text-2xl text-gray-400 mb-12 font-sans max-w-2xl mx-auto">
                    Identifica punti deboli, argomentazioni incomplete e opportunità di attacco
                    direttamente nei tuoi atti giudiziari e contratti.
                </p>

                <div className="flex flex-col md:flex-row gap-6 justify-center items-center">
                    <Link href="/upload" className="px-8 py-4 bg-primary text-navy font-bold rounded-sm hover:brightness-110 transition-all text-lg min-w-[200px] inline-block">
                        Inizia Ora
                    </Link>
                    <Link href="#features" className="px-8 py-4 border border-primary/40 text-primary font-bold rounded-sm hover:bg-primary/10 transition-all text-lg min-w-[200px] inline-block">
                        Guarda Demo
                    </Link>
                </div>
            </motion.div>

            <div className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-6xl">
                <div className="glass-card p-8 rounded-sm text-left">
                    <h3 className="text-primary font-serif text-2xl mb-4">Analisi Argomentativa</h3>
                    <p className="text-gray-400 text-sm">Rileva gap logici e mancanza di prove a supporto delle tue tesi o di quelle dell'avversario.</p>
                </div>
                <div className="glass-card p-8 rounded-sm text-left">
                    <h3 className="text-primary font-serif text-2xl mb-4">Score di Analisi</h3>
                    <p className="text-gray-400 text-sm">Feedback istantaneo su coerenza, supporto probatorio e rischi procedurali con rating 0-100.</p>
                </div>
                <div className="glass-card p-8 rounded-sm text-left">
                    <h3 className="text-primary font-serif text-2xl mb-4">Report Esportabili</h3>
                    <p className="text-gray-400 text-sm">Genera PDF e DOCX pronti per la revisione interna o per preparare la controffensiva.</p>
                </div>
            </div>
        </main>
    );
}
