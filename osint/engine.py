import asyncio
import re
from typing import Awaitable, Callable, Optional

from .http_client import make_client
from .sources.base import InputType, Result, Source

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BSSID_RE = re.compile(r"^[0-9a-f]{2}([:-][0-9a-f]{2}){5}$", re.I)
DIGITS_RE = re.compile(r"^\+?[\d\s().-]{7,}$")


def detect_input_type(target: str) -> InputType:
    t = target.strip()
    if EMAIL_RE.match(t):
        return "email"
    if BSSID_RE.match(t):
        return "bssid"
    if DIGITS_RE.match(t):
        return "phone"
    if "." in t and " " not in t and "/" not in t:
        return "domain"
    if " " in t:
        return "person"
    return "username"


def _all_sources() -> list[Source]:
    from .sources.annuaire import AnnuaireSource
    from .sources.archive import ArchiveSource
    from .sources.bssid import BssidSource
    from .sources.db_searcher import DBSearcherSource
    from .sources.domain import CrtShSource, DomainInfoSource
    from .sources.duckduckgo import DuckDuckGoSource
    from .sources.github import GitHubUsernameSource
    from .sources.google import GoogleSource
    from .sources.google_activity import GoogleActivitySource
    from .sources.gravatar import GravatarSource
    from .sources.holehe_check import HoleheSource
    from .sources.phone import PhoneInfoSource
    from .sources.username_sites import UsernameSitesSource
    from .sources.wikipedia import WikipediaSource
    from .sources.yandex import YandexSource

    return [
        GravatarSource(),
        HoleheSource(),
        DBSearcherSource(),
        GoogleActivitySource(),
        GitHubUsernameSource(),
        UsernameSitesSource(),
        WikipediaSource(),
        PhoneInfoSource(),
        DomainInfoSource(),
        CrtShSource(),
        BssidSource(),
        GoogleSource(),
        DuckDuckGoSource(),
        YandexSource(),
        ArchiveSource(),
        AnnuaireSource(),
    ]


def get_sources_for(input_type: InputType) -> list[Source]:
    return [s for s in _all_sources() if input_type in s.input_types]


async def run_lookup_stream(
    target: str,
    on_result: Callable[[Result], Awaitable[None]],
    input_type: Optional[InputType] = None,
) -> None:
    if not input_type:
        input_type = detect_input_type(target)
    sources = get_sources_for(input_type)

    async with make_client() as client:

        async def run_one(source: Source) -> None:
            try:
                r = await source.lookup(target, client)
            except Exception as e:
                r = Result(source=source.name, target=target, found=False, error=str(e))
            await on_result(r)

        await asyncio.gather(*(run_one(s) for s in sources))
