"""low-level inventory queries against etu's sqlite sde. the queries return plain dictionaries so higher layers stay simple"""

from etu.sde.database import connect
from etu.sde.search import KeywordTrieIndex, TrieIndexCache

def get_category(category_id: int) -> dict | None:
    with connect() as db:
        result = db.execute("""
            SELECT
                category_id,
                name,
                published
            FROM categories
            WHERE category_id = ?
        """, (category_id,)).fetchone()

    if result is None:
        return None

    return dict(result)

def get_type_categories(
    published_only: bool = True,
) -> list[dict]:
    """Return SDE inventory categories that contain searchable item types."""
    published_clause = (
        "AND categories.published = 1 AND types.published = 1"
        if published_only
        else ""
    )

    with connect() as db:
        rows = db.execute(f"""
            SELECT DISTINCT
                categories.category_id,
                categories.name,
                categories.published

            FROM categories

            JOIN groups
                ON groups.category_id = categories.category_id

            JOIN types
                ON types.group_id = groups.group_id

            WHERE 1 = 1
            {published_clause}

            ORDER BY categories.name COLLATE NOCASE,
                     categories.category_id
        """).fetchall()

    return [dict(row) for row in rows]

def get_group(group_id: int) -> dict | None:
    with connect() as db:
        result = db.execute("""
            SELECT
                groups.group_id,
                groups.name,
                groups.category_id,
                groups.published,
                categories.name AS category_name

            FROM groups

            JOIN categories
                ON groups.category_id = categories.category_id

            WHERE groups.group_id = ?
        """, (group_id,)).fetchone()

    if result is None:
        return None

    return dict(result)

def get_type(type_id: int) -> dict | None:
    """
    return an inventory type with its group/category already resolved
    """

    with connect() as db:
        result = db.execute("""
            SELECT
                types.type_id,
                types.name,
                types.description,
                types.meta_group_id,
                types.volume,
                types.packaged_volume,
                types.published,

                groups.group_id,
                groups.name AS group_name,

                categories.category_id,
                categories.name AS category_name

            FROM types

            JOIN groups
                ON types.group_id = groups.group_id

            JOIN categories
                ON groups.category_id = categories.category_id

            WHERE types.type_id = ?
        """, (type_id,)).fetchone()

    if result is None:
        return None

    return dict(result)

def _build_type_search_index(
    published_only: bool,
) -> KeywordTrieIndex:
    where = (
        "WHERE types.published = 1"
        if published_only
        else ""
    )

    with connect() as db:
        rows = db.execute(f"""
            SELECT
                types.type_id,
                types.name,
                types.meta_group_id,
                types.published,

                groups.group_id,
                groups.name AS group_name,

                categories.category_id,
                categories.name AS category_name

            FROM types

            JOIN groups
                ON types.group_id = groups.group_id

            JOIN categories
                ON groups.category_id = categories.category_id

            {where}
        """).fetchall()

    return KeywordTrieIndex(
        rows,
        facet_keys=("category_id",),
    )


_TYPE_SEARCH_INDEX = TrieIndexCache(
    _build_type_search_index
)

def warm_type_search_index(
    published_only: bool = True,
):
    _TYPE_SEARCH_INDEX.get(
        bool(published_only)
    )

def clear_inventory_search_cache():
    _TYPE_SEARCH_INDEX.clear()

def find_types_keywords(
    query: str,
    limit: int | None = 50,
    published_only: bool = True,
    category_id: int | None = None,
) -> list[dict]:
    """Search inventory types using the cached in-memory keyword trie."""
    return _TYPE_SEARCH_INDEX.get(
        bool(published_only)
    ).search(
        query,
        limit=limit,
        filters=(
            {"category_id": int(category_id)}
            if category_id is not None
            else None
        ),
    )

def find_types(
    name: str,
    limit: int = 25,
) -> list[dict]:
    """Compatibility wrapper using the application-wide keyword search."""
    return find_types_keywords(
        name,
        limit=limit,
        published_only=False,
    )
