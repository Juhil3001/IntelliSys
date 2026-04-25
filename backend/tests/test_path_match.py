from app.modules.monitoring.path_match import find_best_api, path_matches_template


def test_path_matches_template():
    assert path_matches_template("/a/{b}/c", "/a/1/c")
    assert not path_matches_template("/a/b", "/a/c")
    assert path_matches_template("/items", "/items")


def test_find_best():
    r = [(1, "GET", "/ping"), (2, "GET", "/users/{id}")]
    assert find_best_api("GET", "/ping", r) == 1
    assert find_best_api("GET", "/users/99", r) == 2
