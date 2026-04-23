"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchApi } from "@/lib/api";

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const data = await fetchApi("/auth/login", {
                method: "POST",
                body: JSON.stringify({ email, password }),
            });

            localStorage.setItem("token", data.access_token);
            router.push("/dashboard");
        } catch (err: any) {
            setError(err.message || "Invalid credentials");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="min-h-screen bg-navy flex items-center justify-center p-6">
            <div className="glass-card p-10 max-w-md w-full rounded-md mt-[-10vh]">
                <div className="text-center mb-8">
                    <h1 className="text-primary font-serif text-3xl font-bold mb-2">LexShield</h1>
                    <p className="text-gray-400">Accedi al tuo account</p>
                </div>

                {error && (
                    <div className="bg-red-900/50 border border-red-500/50 text-red-200 p-3 rounded mb-6 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                    <div>
                        <label className="block text-gray-400 text-sm mb-1">Email</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full bg-navy border border-gray-700 rounded p-3 text-white focus:outline-none focus:border-primary transition-colors"
                            placeholder="avvocato@studiolegale.it"
                        />
                    </div>
                    <div>
                        <label className="block text-gray-400 text-sm mb-1">Password</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-navy border border-gray-700 rounded p-3 text-white focus:outline-none focus:border-primary transition-colors"
                            placeholder="••••••••"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-primary text-navy font-bold py-3 rounded hover:brightness-110 transition-all mt-2 disabled:opacity-50"
                    >
                        {loading ? "Accesso in corso..." : "Accedi"}
                    </button>
                </form>

                <p className="text-center text-gray-400 text-sm mt-6">
                    Non hai un account? <Link href="/register" className="text-primary hover:underline">Registrati</Link>
                </p>
            </div>
        </main>
    );
}
