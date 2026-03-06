import pytest
from app.services.scanner import ScannerService

class MockOpenSearchClient:
    async def search_after_generator(self, index_pattern, max_docs):
        yield {"_id": "1", "_index": "test-idx", "_source": {"name": "Ivan Ivanov", "contact": {"phone": "79991234567"}}}
        yield {"_id": "2", "_index": "test-idx", "_source": {"items": ["apple", "banana"]}}

def test_traverse():
    scanner = ScannerService(MockOpenSearchClient())
    
    obj = {
        "a": 1,
        "b": "test",
        "c": {
            "d": 2,
            "e": ["x", "y"]
        },
        "f": [
            {"g": 3}
        ]
    }
    
    res = scanner._traverse(obj)
    
    res_dict = dict(res)
    assert res_dict["a"] == "1"
    assert res_dict["b"] == "test"
    assert res_dict["c.d"] == "2"
    assert res_dict["c.e[0]"] == "x"
    assert res_dict["c.e[1]"] == "y"
    assert res_dict["f[0].g"] == "3"

def test_calculate_cache_key():
    scanner = ScannerService(MockOpenSearchClient())
    key1 = scanner._calculate_cache_key("idx*", "user.phone", "phone", "79991234567")
    key2 = scanner._calculate_cache_key("idx*", "user.phone", "phone", "79990000000")
    # key is based on index, path, pdn_type only
    assert key1 == key2
    
    key3 = scanner._calculate_cache_key("idx*", "user.email", "email", "test@test.com")
    assert key1 != key3
