import React, { createContext, useContext, useState, ReactNode } from 'react';

interface PDNPattern {
    cache_key: string;
    index_pattern: string;
    field_path: string;
    pdn_type: string;
    context_type: string;
    status: string;
    hit_count: number;
    tags: string[];
}

interface SelectionContextType {
    selectedPatterns: PDNPattern[];
    setSelectedPatterns: (patterns: PDNPattern[]) => void;
    selectedIndexPattern: string | null;
    setSelectedIndexPattern: (idx: string | null) => void;
}

const SelectionContext = createContext<SelectionContextType | undefined>(undefined);

export const SelectionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [selectedPatterns, setSelectedPatterns] = useState<PDNPattern[]>([]);
    const [selectedIndexPattern, setSelectedIndexPattern] = useState<string | null>(null);

    return (
        <SelectionContext.Provider value={{
            selectedPatterns,
            setSelectedPatterns,
            selectedIndexPattern,
            setSelectedIndexPattern
        }}>
            {children}
        </SelectionContext.Provider>
    );
};

export const useSelection = () => {
    const context = useContext(SelectionContext);
    if (!context) {
        throw new Error('useSelection must be used within a SelectionProvider');
    }
    return context;
};
