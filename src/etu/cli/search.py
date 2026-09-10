"""shared cli search helpers. ranking and deduping rules stay here so each menu does not invent its own version"""

from rapidfuzz import fuzz


def rank_system_matches(query, matches):
    query = query.casefold()

    def score(match):
        name = match["name"].casefold()

        if name == query:
            return (4, 100)

        # prefixes matter a lot for j-space names like j122..., so they rank above generic fuzzy matches
        if name.startswith(query):
            return (3, 100)

        if query in name:
            return (2, 100)

        return (1, fuzz.ratio(query, name))

    return sorted(
        matches,
        key=score,
        reverse=True,
    )

def merge_matches(fuzzy_matches, partial_matches, id_key):
    combined = []
    seen = set()

    # both searches can return the same object, so only the first copy of each id is kept
    for match in fuzzy_matches + partial_matches:
        match_id = match[id_key]

        if match_id in seen:
            continue

        seen.add(match_id)
        combined.append(match)

    return combined
