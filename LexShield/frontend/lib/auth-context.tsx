"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { fetchApi } from "./api";

type User = {
    id: string;
    email: string;
    full_name: string;
    firm_name: string | null;
    role: string;
};

type AuthContextType = {
    user: User | null;
    loading: boolean;
    logout: () => void;
};

const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    logout: () => {},
});

export function useAuth() {
    return useContext(AuthContext);
}

// Pages that don't require authentication
const PUBLIC_PATHS = ["/login", "/register", "/"];

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    const logout = () => {
        localStorage.removeItem("token");
        setUser(null);
        router.push("/login");
    };

    useEffect(() => {
        const checkAuth = async () => {
            const token = localStorage.getItem("token");

            // No token → if on a protected page, redirect to login
            if (!token) {
                setLoading(false);
                if (!PUBLIC_PATHS.includes(pathname)) {
                    router.push("/login");
                }
                return;
            }

            // Token exists → validate it
            try {
                const userData = await fetchApi("/auth/me");
                setUser(userData);
            } catch {
                // Token is invalid/expired
                localStorage.removeItem("token");
                if (!PUBLIC_PATHS.includes(pathname)) {
                    router.push("/login");
                }
            } finally {
                setLoading(false);
            }
        };

        checkAuth();
    }, [pathname, router]);

    return (
        <AuthContext.Provider value={{ user, loading, logout }}>
            {children}
        </AuthContext.Provider>
    );
}
