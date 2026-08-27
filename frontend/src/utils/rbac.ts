export type Role = 'viewer' | 'analyst' | 'admin';

/** True if the role can create Jira tasks (analyst+). */
export function canCreateJira(role?: Role | null): boolean {
    return role === 'analyst' || role === 'admin';
}

/** True if the role can edit pattern (status, custom message, update examples, false positive) — analyst+. */
export function canEditPattern(role?: Role | null): boolean {
    return role === 'analyst' || role === 'admin';
}

/** True if the role can delete a pattern — admin only. */
export function canDeletePattern(role?: Role | null): boolean {
    return role === 'admin';
}

/** True if the role can trigger a scan — admin only. */
export function canScan(role?: Role | null): boolean {
    return role === 'admin';
}

/** True if the role can write settings (save forms, owners, regex, scan-fields) — admin only. */
export function canWriteSettings(role?: Role | null): boolean {
    return role === 'admin';
}

/** True if the role is viewer (read-only). */
export function isViewer(role?: Role | null): boolean {
    return role === 'viewer';
}
