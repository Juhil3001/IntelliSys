def path_matches_template(template: str, actual: str) -> bool:
    template = template.split("?")[0].strip()
    actual = actual.split("?")[0].strip()
    if template == actual:
        return True
    ta = [x for x in template.strip("/").split("/") if x or template.strip() == ""]
    aa = [x for x in actual.strip("/").split("/") if x or actual.strip() == ""]
    if not ta and not aa:
        return True
    if len(ta) != len(aa):
        return False
    for t, a in zip(ta, aa, strict=True):
        if t.startswith("{") and t.endswith("}"):
            continue
        if t != a:
            return False
    return True


def find_best_api(
    method: str,
    path: str,
    routes: list[tuple[int, str, str]],
) -> int | None:
    """
    routes: list of (api_id, http_method, endpoint_template)
    Prefer exact path match, then first template match.
    """
    method_u = method.upper()
    exact = None
    templ = None
    for api_id, m, ep in routes:
        if m.upper() != method_u:
            continue
        if ep == path:
            exact = api_id
            break
        if path_matches_template(ep, path):
            templ = api_id
    return exact if exact is not None else templ
