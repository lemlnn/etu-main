"""shared deterministic search helpers"""


def find_exact_name(query, matches):
    """Return the first case-insensitive exact-name match, if present."""
    query = query.casefold()
    return next(
        (
            match
            for match in matches
            if match["name"].casefold() == query
        ),
        None,
    )
