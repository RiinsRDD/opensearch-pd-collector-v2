import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 3000,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const indicesApi = {
    getTree: async () => {
        const response = await apiClient.get('/indices');
        return response.data;
    },
};

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

export const settingsApi = {
    getSettings: async (): Promise<GlobalSettingsData> => {
        const response = await apiClient.get('/settings/global');
        return response.data;
    },
    saveSettings: async (data: GlobalSettingsData): Promise<any> => {
        const response = await apiClient.post('/settings/global', data);
        return response.data;
    }
};

export const exclusionsApi = {
    getGlobal: async () => {
        const response = await apiClient.get('/settings/exclusions/global');
        return response.data;
    },
    addGlobal: async (data: { pdn_type: string; rule_type: string; value: string }) => {
        const response = await apiClient.post('/settings/exclusions/global', data);
        return response.data;
    },
    deleteGlobal: async (id: number) => {
        const response = await apiClient.delete(`/settings/exclusions/global/${id}`);
        return response.data;
    },
    getIndex: async (indexPattern?: string) => {
        const response = await apiClient.get('/settings/exclusions/index', {
            params: indexPattern ? { index_pattern: indexPattern } : {},
        });
        return response.data;
    },
    addIndex: async (data: { index_pattern: string; pdn_type: string; key_path: string }) => {
        const response = await apiClient.post('/settings/exclusions/index', data);
        return response.data;
    },
    deleteIndex: async (id: number) => {
        const response = await apiClient.delete(`/settings/exclusions/index/${id}`);
        return response.data;
    },
    getIndicesList: async () => {
        const response = await apiClient.get('/settings/exclusions/indices-list');
        return response.data;
    },
};

export interface PdnType {
    id: number;
    pdn_type: string;
    value: string;
    is_active: boolean;
    is_system: boolean;
}

export const pdnTypesApi = {
    getAll: async (): Promise<PdnType[]> => {
        const response = await apiClient.get('/settings/pdn-types');
        return response.data;
    },
    getTypesList: async (): Promise<string[]> => {
        const response = await apiClient.get('/settings/pdn-types/list');
        return response.data;
    },
    create: async (data: { pdn_type: string; regex_value: string }): Promise<any> => {
        const response = await apiClient.post('/settings/pdn-types', data);
        return response.data;
    },
    update: async (id: number, data: { regex_value: string }): Promise<any> => {
        const response = await apiClient.put(`/settings/pdn-types/${id}`, data);
        return response.data;
    },
    delete: async (id: number): Promise<any> => {
        const response = await apiClient.delete(`/settings/pdn-types/${id}`);
        return response.data;
    }
};

export interface ScanFieldConfig {
    id: number;
    index_pattern: string;
    field_path: string;
    is_active: boolean;
    is_required: boolean;
    created_at: string | null;
}

export const scanFieldsApi = {
    getAll: async (): Promise<ScanFieldConfig[]> => {
        const response = await apiClient.get('/settings/scan-fields');
        return response.data;
    },
    create: async (data: { index_pattern: string; field_path: string }): Promise<any> => {
        const response = await apiClient.post('/settings/scan-fields', data);
        return response.data;
    },
    delete: async (id: number): Promise<any> => {
        const response = await apiClient.delete(`/settings/scan-fields/${id}`);
        return response.data;
    },
};

export interface IndexOwnerData {
    id: number;
    index_pattern: string;
    cmdb_url: string | null;
    tech_debt_id: string | null;
    fio: string | null;
}

export const indexOwnersApi = {
    getAll: async (): Promise<IndexOwnerData[]> => {
        const response = await apiClient.get('/settings/index-owners/');
        return response.data;
    },
    create: async (data: Omit<IndexOwnerData, 'id'>): Promise<IndexOwnerData> => {
        const response = await apiClient.post('/settings/index-owners/', data);
        return response.data;
    },
    update: async (id: number, data: Omit<IndexOwnerData, 'id'>): Promise<IndexOwnerData> => {
        const response = await apiClient.put(`/settings/index-owners/${id}`, data);
        return response.data;
    },
    delete: async (id: number): Promise<void> => {
        await apiClient.delete(`/settings/index-owners/${id}`);
    }
};
