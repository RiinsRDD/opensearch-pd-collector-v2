import type { IndexTreeNode, IndicesTreeResponse, PDNPattern } from '../types/api';
import type { IndexPatternNode, TypeNode } from '../components/tree/IndicesTree';

interface MappedPattern extends PDNPattern {
    _original: PDNPattern;
}

function mapCacheKeyNode(node: IndexTreeNode): MappedPattern | null {
    if (!node.pattern) return null;
    return {
        ...node.pattern,
        _original: node.pattern,
    };
}

function mapPdnTypeNode(node: IndexTreeNode): TypeNode | null {
    if (node.type !== 'pdn_type' || !node.children) return null;

    const patterns: MappedPattern[] = [];
    node.children.forEach((child: IndexTreeNode) => {
        const mapped = mapCacheKeyNode(child);
        if (mapped) patterns.push(mapped);
    });

    return {
        type: node.name,
        count: patterns.length,
        patterns,
    };
}

function mapIndexNode(node: IndexTreeNode): IndexPatternNode | null {
    if (node.type !== 'index' || !node.children) return null;

    const types: TypeNode[] = [];
    node.children.forEach((child: IndexTreeNode) => {
        const mapped = mapPdnTypeNode(child);
        if (mapped) types.push(mapped);
    });

    const totalHits = types.reduce((sum, t) => sum + t.count, 0);
    const newCount = node.new_count || 0;

    return {
        index_pattern: node.name,
        total_hits: totalHits,
        has_new_tasks: newCount > 0,
        new_count: newCount,
        types,
    };
}

export function mapIndicesTree(response: IndicesTreeResponse): IndexPatternNode[] {
    const { tree, new_counts } = response;

    const indexNodes: IndexPatternNode[] = [];

    tree.forEach((node: IndexTreeNode) => {
        const mapped = mapIndexNode(node);
        if (mapped) {
            if (new_counts[node.name] !== undefined) {
                mapped.new_count = new_counts[node.name];
                mapped.has_new_tasks = new_counts[node.name] > 0;
            }
            indexNodes.push(mapped);
        }
    });

    return indexNodes;
}

export function filterIndicesTree(data: IndexPatternNode[], filterText: string): IndexPatternNode[] {
    if (!filterText.trim()) return data;
    const lowerFilter = filterText.toLowerCase();

    return data.map(idx => {
        const filteredTypes = idx.types.map((t: TypeNode) => {
            const filteredPatterns = t.patterns.filter((p: PDNPattern) =>
                p.status.toLowerCase().includes(lowerFilter) ||
                p.tags.some((tag: { name: string }) => tag.name.toLowerCase().includes(lowerFilter)) ||
                p.field_path.toLowerCase().includes(lowerFilter) ||
                (p.key_hint && p.key_hint.toLowerCase().includes(lowerFilter)) ||
                (p.extra_fields && Object.values(p.extra_fields).some((val: unknown) => String(val).toLowerCase().includes(lowerFilter)))
            );
            return { ...t, patterns: filteredPatterns };
        }).filter(t => t.patterns.length > 0 || t.type.toLowerCase().includes(lowerFilter));

        return { ...idx, types: filteredTypes };
    }).filter(idx => idx.types.length > 0 || idx.index_pattern.toLowerCase().includes(lowerFilter));
}