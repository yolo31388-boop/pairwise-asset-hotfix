import pytest

from game.asset_hotfix import (
    manifest_diff,
    parse_range,
    diff_blocks,
    rollback_plan,
    verify_chunk
)


def test_manifest_changed():
    assert manifest_diff({'a': 1}, {'a': 2}) == {'added': [], 'removed': [], 'changed': ['a']}

def test_manifest_added():
    assert manifest_diff({'a': 1}, {'a': 1, 'b': 2}) == {'added': ['b'], 'removed': [], 'changed': []}

def test_manifest_removed():
    assert manifest_diff({'a': 1, 'b': 2}, {'a': 1}) == {'added': [], 'removed': ['b'], 'changed': []}

def test_manifest_unchanged():
    assert manifest_diff({'a': 1}, {'a': 1}) == {'added': [], 'removed': [], 'changed': []}

def test_range_normal():
    assert parse_range('bytes=0-99', 100) == (0, 99)

def test_range_suffix():
    assert parse_range('bytes=-100', 1000) == (900, 999)

def test_range_open_end():
    assert parse_range('bytes=0-', 100) == (0, 99)

def test_range_invalid():
    with pytest.raises(ValueError):
        parse_range('bytes=abc', 100)

def test_diff_blocks_same():
    assert diff_blocks(b'AAA', b'AAA', 3) == []

def test_diff_blocks_one():
    assert diff_blocks(b'AAA', b'AAB', 3) == [0]

def test_diff_blocks_append():
    assert diff_blocks(b'AAA', b'AAAA', 3) == [1]

def test_rollback_removes_extra():
    assert rollback_plan({'a', 'b'}, {'a'}) == ['b']

def test_rollback_keeps_match():
    assert rollback_plan({'a'}, {'a'}) == []

def test_verify_chunk_ok():
    assert verify_chunk(b'abc', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad') is True

def test_verify_chunk_bad():
    assert verify_chunk(b'abc', '0' * 64) is False
