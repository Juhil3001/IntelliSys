from app.modules.change_detection.service import diff_snapshots


def test_diff_snapshots_detects_hash_change() -> None:
    old = {
        "version": 1,
        "api_list": [
            {
                "method": "GET",
                "endpoint": "/a",
                "name": "x",
                "file_id": 1,
                "content_hash": "h1",
            }
        ],
        "file_paths": ["a.py"],
    }
    new = {
        "version": 1,
        "api_list": [
            {
                "method": "GET",
                "endpoint": "/a",
                "name": "x",
                "file_id": 1,
                "content_hash": "h2",
            }
        ],
        "file_paths": ["a.py"],
    }
    d = diff_snapshots(old, new)
    assert d["added_apis"] == []
    assert d["removed_apis"] == []
    assert len(d["updated_apis"]) == 1
    assert d["updated_apis"][0]["method"] == "GET"


def test_diff_snapshots_unchanged_hash() -> None:
    a = {
        "method": "GET",
        "endpoint": "/x",
        "name": "n",
        "file_id": 1,
        "content_hash": "same",
    }
    d = diff_snapshots({"api_list": [a], "file_paths": []}, {"api_list": [a], "file_paths": []})
    assert d["updated_apis"] == []
