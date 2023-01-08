from typing import Dict

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fedimapper.models.ban import Ban


async def get_ban_keywords(
    db: AsyncSession, host: str, severity: str | None = None, threshold: int = 0
) -> Dict[str, int]:
    if severity:
        keyword_lookup = select(Ban.keywords).where(Ban.banned_host == host, Ban.severity == severity)
    else:
        keyword_lookup = select(Ban.keywords).where(Ban.banned_host == host)
    results = await db.execute(keyword_lookup)
    keywords = {}
    for row in results:
        row_keywords = row[0]
        for keyword in row_keywords:
            if keyword not in keywords:
                keywords[keyword] = 1
            else:
                keywords[keyword] += 1
    return {k: v for k, v in sorted(keywords.items(), reverse=True, key=lambda item: item[1]) if v >= threshold}
