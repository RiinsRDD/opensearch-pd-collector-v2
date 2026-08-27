/**
 * Архив UX-stub для дерева индексов — НЕ ИМПОРТИРОВАТЬ ИЗ pages/components.
 * Этот файл сохранён как справочник формы узлов для сверки UX при редизайне.
 * Живой UI использует API: GET /api/v1/indices → indicesApi.getTree().
 */

import type { IndexPatternNode } from '../components/tree/IndicesTree';

export const mockData: IndexPatternNode[] = [
    {
        index_pattern: 'bcs-tech-logs-*',
        total_hits: 42,
        has_new_tasks: true,
        new_count: 5,
        types: [
            {
                type: 'PHONE',
                count: 28,
                patterns: [
                    {
                        cache_key: 'a8f2c184', field_path: 'req.body.client_phone', pdn_type: 'PHONE',
                        index_pattern: 'bcs-tech-logs-*', context_type: 'base', key_hint: null,
                        extra_fields: { 'NameOfMicroService': 'auth-svc', 'kubernetes.container.name': 'api-gw' },
                        hit_count: 12, status: 'new', custom_message: null,
                        tags: [], examples: ['79265554433', '79261234567', '79268889999'],
                        has_jira_task: false,
                    },
                    {
                        cache_key: 'c4e9b321', field_path: 'user.phone', pdn_type: 'PHONE',
                        index_pattern: 'bcs-tech-logs-*', context_type: 'base', key_hint: null,
                        extra_fields: { 'NameOfMicroService': 'user-svc', 'kubernetes.container.name': 'main-app' },
                        hit_count: 5, status: 'confirmed', custom_message: null,
                        tags: [], examples: ['79261234567'],
                        has_jira_task: true,
                    },
                    {
                        cache_key: 'f1a2b349', field_path: 'message', pdn_type: 'PHONE',
                        index_pattern: 'bcs-tech-logs-*', context_type: 'structured_key', key_hint: 'phone',
                        extra_fields: { 'NameOfMicroService': 'api-gw', 'kubernetes.container.name': 'worker-pod' },
                        hit_count: 8, status: 'new', custom_message: null,
                        tags: [], examples: ['79265554433', '79268889999', '79261112222'],
                        has_jira_task: false,
                    },
                    {
                        cache_key: 'd7c8e1a2', field_path: 'message', pdn_type: 'PHONE',
                        index_pattern: 'bcs-tech-logs-*', context_type: 'free_text', key_hint: null,
                        extra_fields: { 'NameOfMicroService': 'logger-svc', 'kubernetes.container.name': 'logger-pod' },
                        hit_count: 3, status: 'confirmed', custom_message: null,
                        tags: [], examples: ['79261234567'],
                        has_jira_task: false,
                    },
                    {
                        cache_key: 'b2a1c4df', field_path: 'raw_message', pdn_type: 'PHONE',
                        index_pattern: 'bcs-tech-logs-*', context_type: 'ambiguous', key_hint: 'данные клиента',
                        extra_fields: { 'NameOfMicroService': 'api-gw', 'kubernetes.container.name': 'api-gw' },
                        hit_count: 1, status: 'new', custom_message: null,
                        tags: [], examples: ['79265554433'],
                        has_jira_task: false,
                    }
                ]
            },
            {
                type: 'EMAIL',
                count: 14,
                patterns: [
                    {
                        cache_key: 'e5f6a7b8', field_path: 'metadata.user.email', pdn_type: 'EMAIL',
                        index_pattern: 'bcs-tech-logs-*', context_type: 'base', key_hint: null,
                        extra_fields: { 'NameOfMicroService': 'auth-svc', 'kubernetes.container.name': 'auth-pod' },
                        hit_count: 9, status: 'new', custom_message: null,
                        tags: [], examples: ['test@bcs.ru', 'admin@bcs.ru'],
                        has_jira_task: false,
                    },
                    {
                        cache_key: 'a1b2c3d4', field_path: 'log.body', pdn_type: 'EMAIL',
                        index_pattern: 'bcs-tech-logs-*', context_type: 'structured_key', key_hint: 'email',
                        extra_fields: { 'NameOfMicroService': 'mailer-svc', 'kubernetes.container.name': 'mail-pod' },
                        hit_count: 5, status: 'unverified', custom_message: null,
                        tags: [], examples: ['user@example.com'],
                        has_jira_task: false,
                    }
                ]
            }
        ]
    },
    {
        index_pattern: 'client-activity-api-*',
        total_hits: 5,
        has_new_tasks: false,
        types: []
    }
];