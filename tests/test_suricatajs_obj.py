from suricatajs_obj import SuricataJSObject


def test_calculate_checksum_is_sha256():
    obj = SuricataJSObject("https://example.com/a.js", "alert(1)")
    import hashlib
    expected = hashlib.sha256("alert(1)".encode()).hexdigest()
    assert obj.checksum == expected


def test_save_and_compare_match(fresh_db):
    obj = SuricataJSObject("https://example.com/a.js", "alert(1)")
    obj.save_to_db()
    is_match, stored = obj.compare_with_db()
    assert is_match is True
    assert stored == obj.checksum


def test_compare_mismatch(fresh_db):
    original = SuricataJSObject("https://example.com/a.js", "alert(1)")
    original.save_to_db()
    modified = SuricataJSObject("https://example.com/a.js", "alert(2)")
    is_match, stored = modified.compare_with_db()
    assert is_match is False
    assert stored == original.checksum


def test_compare_no_prior_entry(fresh_db):
    obj = SuricataJSObject("https://example.com/new.js", "const x = 1")
    is_match, stored = obj.compare_with_db()
    assert is_match is False
    assert stored is None


def test_compare_returns_latest_checksum(fresh_db):
    first = SuricataJSObject("https://example.com/a.js", "v1")
    first.save_to_db()
    second = SuricataJSObject("https://example.com/a.js", "v2")
    second.save_to_db()
    probe = SuricataJSObject("https://example.com/a.js", "v2")
    is_match, stored = probe.compare_with_db()
    assert is_match is True
    assert stored == second.checksum
