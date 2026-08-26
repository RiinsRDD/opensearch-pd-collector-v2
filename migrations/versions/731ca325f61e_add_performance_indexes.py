"""add performance indexes

Revision ID: 731ca325f61e
Revises: 13694664e7a5
Create Date: 2026-08-25 17:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '731ca325f61e'
down_revision: Union[str, Sequence[str], None] = '13694664e7a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # PDNPattern: composite index for filtering tree (index_pattern, pdn_type, status)
    op.create_index(
        'ix_pdn_pattern_idx_type_status',
        'pdn_patterns',
        ['index_pattern', 'pdn_type', 'status'],
        unique=False
    )

    # PDNFinding: composite index for top-3 examples (cache_key, found_at DESC)
    op.create_index(
        'ix_pdn_finding_cache_key_found_at',
        'pdn_findings',
        ['cache_key', sa.desc('found_at')],
        unique=False
    )

    # ScannerLog: composite index for scanner status (status, started_at DESC)
    op.create_index(
        'ix_scanner_log_status_started',
        'scanner_logs',
        ['status', sa.desc('started_at')],
        unique=False
    )

    # JiraTask: composite index for tasks by index (index_pattern, created_at DESC)
    op.create_index(
        'ix_jira_task_index_created',
        'jira_tasks',
        ['index_pattern', sa.desc('created_at')],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_jira_task_index_created', table_name='jira_tasks')
    op.drop_index('ix_scanner_log_status_started', table_name='scanner_logs')
    op.drop_index('ix_pdn_finding_cache_key_found_at', table_name='pdn_findings')
    op.drop_index('ix_pdn_pattern_idx_type_status', table_name='pdn_patterns')