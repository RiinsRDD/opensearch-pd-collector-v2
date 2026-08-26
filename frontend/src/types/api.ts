/**
 * Shared API types - synchronized with backend models
 * Generated from backend response in /api/v1/indices/
 */

export interface PDNPattern {
    cache_key: string;
    index_pattern: string;
    field_path: string;
    pdn_type: string;
    context_type: 'structured_key' | 'free_text' | 'ambiguous' | 'base';
    key_hint: string | null;
    extra_fields: Record<string, string> | null;
    hit_count: number;
    status: 'new' | 'confirmed' | 'done' | 'false_positive' | 'unverified' | 'archived';
    custom_message: string | null;
    tags: Array<{ id: number; name: string; color: string | null }>;
    examples: string[];
    full_document?: Record<string, unknown> | null;
    has_jira_task: boolean;
}

export interface IndexTreeNode {
    id: string;
    name: string;
    type: 'index' | 'pdn_type' | 'cache_key';
    children?: IndexTreeNode[];
    pattern?: PDNPattern;
    new_count?: number;
}

export interface IndicesTreeResponse {
    tree: IndexTreeNode[];
    new_counts: Record<string, number>;
}

export interface JiraTask {
    id: number;
    jira_issue_key: string;
    index_pattern: string;
    author_name: string | null;
    created_at: string;
    jira_url: string;
}

export interface JiraHistoryResponse {
    items: JiraTask[];
    total: number;
    limit: number;
    page: number;
}

export interface ScannerStatus {
    status: 'active' | 'idle';
    current_index_pattern: string | null;
    eta: string | null;
}

export interface ScannerLog {
    id: number;
    scan_type: string;
    target_index: string | null;
    status: string;
    findings_count: number;
    started_at: string | null;
    duration_seconds: number | null;
    details: string;
}

export interface GlobalSettingsData {
    pdn_flags: Record<string, boolean>;
    examples_count: number;
    scan_interval_hours: number;
    exclude_index_patterns: string[];
    exclude_index_regexes: string[];
    include_index_regexes: string[];
    mail_service_names: string[];
    unknown_mail_service_parts: string[];
    card_bank_bins_4: string[];
    invalid_def_codes: string[];
    surn_ends_cis: string[];
    surn_ends_world: string[];
    patron_ends: string[];
    fio_special_markers: string[];
    jira_base_url: string;
    jira_project_key: string;
    jira_issue_type: string;
    jira_priority: string;
    jira_components: string;
    jira_labels: string;
    jira_dib_service: string;
    jira_epic_link: string;
    jira_cfo: string;
    jira_kipd_type: string;
    jira_task_source: string;
    jira_action_group: string;
    jira_action_type: string;
    jira_process: string;
    jira_criticality_level: string;
    jira_location_type: string;
    jira_it_system: string;
    jira_exploit_poc: string;
    jira_cvss_score: number;
    jira_column_id: string;
    jira_risk_text: string;
    jira_work_description: string;
}