"""Integration tests for scanner service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.scanner import ScannerService
from app.services.opensearch_client import OpenSearchClient
from app.models.pdn import PDNPattern, PDNFinding
from app.models.settings import RegexRule, SystemSetting
from app.models.tags import Tag
from app.models.logs import ScannerLog
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime


class MockOpenSearchClient:
    """Mock OpenSearch client for testing."""
    
    def __init__(self, documents=None):
        self.documents = documents or []
        self.call_count = 0
    
    async def search_after_generator(self, index_pattern: str, batch_size: int = 10000,
                                      time_from: str = "now-1h", time_to: str = "now",
                                      search_after: list = None, max_docs: int = None, **kwargs):
        self.call_count += 1
        for doc in self.documents:
            yield doc


@pytest.mark.asyncio
async def test_scan_index_creates_patterns_and_findings(db):
    """Integration test: full scan cycle creates patterns and findings."""
    # Setup test data in OS
    test_docs = [
        {
            "_source": {
                "user": {"phone": "79991234567", "email": "test@example.com"},
                "message": "User 79991234567 called"
            },
            "_id": "doc_1",
            "_index": "bcs-tech-logs-2024.01.15"
        }
    ]
    
    os_client = MockOpenSearchClient(test_docs)
    scanner = ScannerService(os_client)
    
    # Add required rules to DB
    rules = [
        RegexRule(pdn_type="phone", rule_type="regex", value=r"7\d{10}", is_active=True),
        RegexRule(pdn_type="email", rule_type="regex", value=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", is_active=True),
    ]
    for rule in rules:
        db.add(rule)
    
    settings = [
        SystemSetting(key="EXAMPLES_COUNT", value="3"),
        SystemSetting(key="SCAN_INTERVAL_HOURS", value="1"),
    ]
    for s in settings:
        db.add(s)
    await db.commit()
    
    # Run scan
    findings_count = await scanner.scan_index(
        db=db,
        index_pattern="bcs-tech-logs-*",
        max_docs=100,
        is_global=False,
        scan_type_tag='S'
    )
    
    # Verify findings
    assert findings_count > 0
    
    # Verify PDNPattern created
    from sqlalchemy import select
    patterns = await db.execute(select(PDNPattern))
    patterns = patterns.scalars().all()
    assert len(patterns) >= 1
    
    # Verify PDNFinding created
    findings = await db.execute(select(PDNFinding))
    findings = findings.scalars().all()
    assert len(findings) >= 1
    
    # Verify finding has correct data
    finding = findings[0]
    assert finding.cache_key is not None
    assert finding.raw_value is not None
    assert finding.field_path is not None


@pytest.mark.asyncio
async def test_scan_index_with_existing_pattern_increments_hit_count(db):
    """Test that scanning existing pattern increments hit_count."""
    os_client = MockOpenSearchClient([
        {
            "_source": {"user": {"phone": "79991234567"}},
            "_id": "doc_1",
            "_index": "bcs-tech-logs-2024.01.15"
        }
    ])
    scanner = ScannerService(os_client)
    
    # Add rules
    db.add(RegexRule(pdn_type="phone", rule_type="regex", value=r"7\d{10}", is_active=True))
    db.add(SystemSetting(key="EXAMPLES_COUNT", value="3"))
    await db.commit()
    
    cache_key = scanner._calculate_cache_key(
        "bcs-tech-logs-*",
        "user.phone",
        "phone",
        "structured_key",
        "phone",
        {},
    )
    existing = PDNPattern(
        cache_key=cache_key,
        index_pattern="bcs-tech-logs-*",
        field_path="user.phone",
        pdn_type="phone",
        context_type="structured_key",
        key_hint="phone",
        hit_count=5,
        status="confirmed"
    )
    db.add(existing)
    await db.commit()
    
    # Scan
    await scanner.scan_index(db, "bcs-tech-logs-*", 100, False, 'S')
    
    # Verify hit_count incremented
    from sqlalchemy import select
    pattern = await db.execute(select(PDNPattern).where(PDNPattern.cache_key == cache_key))
    pattern = pattern.scalars().first()
    assert pattern.hit_count == 6  # 5 + 1


@pytest.mark.asyncio
async def test_scan_respects_exclusions(db):
    """Test that index exclusions are respected during scan."""
    from app.models.settings import IndexKeyExclusion
    
    os_client = MockOpenSearchClient([
        {
            "_source": {"user": {"phone": "79991234567", "email": "test@example.com"}},
            "_id": "doc_1",
            "_index": "bcs-tech-logs-2024.01.15"
        }
    ])
    scanner = ScannerService(os_client)
    
    # Add rules
    db.add(RegexRule(pdn_type="phone", rule_type="regex", value=r"7\d{10}", is_active=True))
    db.add(RegexRule(pdn_type="email", rule_type="regex", value=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", is_active=True))
    db.add(SystemSetting(key="EXAMPLES_COUNT", value="3"))
    
    # Add exclusion for phone on this path
    exclusion = IndexKeyExclusion(
        index_pattern="bcs-tech-logs-*",
        pdn_type="phone",
        key_path="user.phone"
    )
    db.add(exclusion)
    await db.commit()
    
    # Scan
    await scanner.scan_index(db, "bcs-tech-logs-*", 100, False, 'S')
    
    # Verify only email was found, not phone
    from sqlalchemy import select
    findings = await db.execute(select(PDNFinding))
    findings = findings.scalars().all()
    
    # Should only have email finding
    field_paths = {f.field_path for f in findings}
    assert "user.email" in field_paths
    assert "user.phone" not in field_paths  # Excluded


@pytest.mark.asyncio
async def test_sliding_window_examples(db):
    """Test sliding window keeps only latest N examples."""
    os_client = MockOpenSearchClient([
        {
            "_source": {"user": {"phone": "79991234567"}},
            "_id": f"doc_{i}",
            "_index": "bcs-tech-logs-2024.01.15"
        }
        for i in range(10)
    ])
    scanner = ScannerService(os_client)
    
    db.add(RegexRule(pdn_type="phone", rule_type="regex", value=r"7\d{10}", is_active=True))
    db.add(SystemSetting(key="EXAMPLES_COUNT", value="3"))
    await db.commit()
    
    await scanner.scan_index(db, "bcs-tech-logs-*", 100, False, 'S')
    
    # Verify only 3 examples kept per cache_key
    from sqlalchemy import select
    findings = await db.execute(select(PDNFinding))
    findings = findings.scalars().all()
    
    # Group by cache_key
    from collections import defaultdict
    by_cache = defaultdict(list)
    for f in findings:
        by_cache[f.cache_key].append(f)
    
    for cache_key, examples in by_cache.items():
        assert len(examples) <= 3, f"Cache key {cache_key} has {len(examples)} examples, expected <= 3"


@pytest.mark.asyncio
async def test_single_scan_vs_global_scan_tags(db):
    """Test that single scan uses 'S' tag and global uses 'G' tag."""
    from app.models.tags import Tag, PatternTagLink
    
    os_client = MockOpenSearchClient([
        {"_source": {"user": {"phone": "79991234567"}}, "_id": "doc_1", "_index": "test-idx"}
    ])
    scanner = ScannerService(os_client)
    
    db.add(RegexRule(pdn_type="phone", rule_type="regex", value=r"7\d{10}", is_active=True))
    db.add(SystemSetting(key="EXAMPLES_COUNT", value="3"))
    await db.commit()
    
    # Single scan
    await scanner.scan_index(db, "test-idx", 100, False, 'S')
    
    from sqlalchemy import select
    s_tag = (await db.execute(select(Tag).filter(Tag.name == "S"))).scalars().first()
    assert s_tag is not None
    s_links = (await db.execute(select(PatternTagLink).filter(PatternTagLink.tag_id == s_tag.id))).scalars().all()
    assert len(s_links) > 0
    
    # Global scan
    await scanner.scan_index(db, "test-idx-2", 100, True, 'G')
    
    g_tag = (await db.execute(select(Tag).filter(Tag.name == "G"))).scalars().first()
    assert g_tag is not None
    g_links = (await db.execute(select(PatternTagLink).filter(PatternTagLink.tag_id == g_tag.id))).scalars().all()
    assert len(g_links) > 0


@pytest.mark.asyncio
async def test_scan_error_handling(db):
    """Test scanner handles OS errors gracefully."""
    class FailingOSClient:
        async def search_after_generator(self, **kwargs):
            raise ConnectionError("OpenSearch unavailable")
            yield  # async generator, not a coroutine
    
    scanner = ScannerService(FailingOSClient())
    
    db.add(RegexRule(pdn_type="phone", rule_type="regex", value=r"7\d{10}", is_active=True))
    db.add(SystemSetting(key="EXAMPLES_COUNT", value="3"))
    await db.commit()

    with pytest.raises(ConnectionError):
        await scanner.scan_index(db, "test-idx", 100, False, 'S')