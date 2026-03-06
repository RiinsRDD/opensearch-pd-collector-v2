import { createContext, useContext, useState, type ReactNode } from 'react';
import type { PDNPattern } from '../components/tree/IndicesTree';

interface SelectionContextType {
    selectedPatterns: PDNPattern[];
    setSelectedPatterns: (patterns: PDNPattern[]) => void;
    selectedIndexPattern: string | null;
    setSelectedIndexPattern: (idx: string | null) => void;
}

const SelectionContext = createContext<SelectionContextType | undefined>(undefined);

export function SelectionProvider({ children }: { children: ReactNode }) {
    const [selectedPatterns, setSelectedPatterns] = useState<PDNPattern[]>([]);
    const [selectedIndexPattern, setSelectedIndexPattern] = useState<string | null>(null);

    return (
        <SelectionContext.Provider value={{ selectedPatterns, setSelectedPatterns, selectedIndexPattern, setSelectedIndexPattern }}>
            {children}
        </SelectionContext.Provider>
    );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSelection() {
    const context = useContext(SelectionContext);
    if (!context) throw new Error('useSelection must be used within SelectionProvider');
    return context;
}
