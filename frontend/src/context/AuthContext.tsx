import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { authApi, getToken, clearToken, type User } from '../api/client';

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchUser = async () => {
        const token = getToken();
        if (!token) {
            setLoading(false);
            return;
        }
        try {
            const userData = await authApi.me();
            setUser(userData);
        } catch {
            clearToken();
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUser();
    }, []);

    const login = async (username: string, password: string) => {
        const { access_token } = await authApi.login(username, password);
        localStorage.setItem('pdn_access_token', access_token);
        const userData = await authApi.me();
        setUser(userData);
    };

    const logout = () => {
        clearToken();
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}