from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# Scanner metrics
scan_duration = Histogram(
    'pdn_scan_duration_seconds',
    'Scan duration in seconds',
    ['scan_type', 'index_pattern']
)

scan_findings = Counter(
    'pdn_findings_total',
    'Total findings',
    ['pdn_type', 'status']
)

scan_errors = Counter(
    'pdn_scan_errors_total',
    'Total scan errors',
    ['scan_type', 'error_type']
)

# Jira metrics
jira_tasks_created = Counter(
    'pdn_jira_tasks_created_total',
    'Total Jira tasks created',
    ['index_pattern', 'result']
)

jira_errors = Counter(
    'pdn_jira_errors_total',
    'Total Jira errors',
    ['error_type']
)

# DB metrics
db_query_duration = Histogram(
    'pdn_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation']
)

# Scheduler metrics
scheduler_job_status = Gauge(
    'pdn_scheduler_job_status',
    'Scheduler job status (1=running, 0=stopped)',
    ['job_id']
)

scheduler_last_run = Gauge(
    'pdn_scheduler_last_run_timestamp',
    'Last run timestamp of scheduler job',
    ['job_id']
)

# HTTP request metrics
http_requests_total = Counter(
    'pdn_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'pdn_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Active scans gauge
active_scans = Gauge(
    'pdn_active_scans',
    'Number of currently active scans',
    ['scan_type']
)

# Metrics endpoint
async def metrics_endpoint():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)