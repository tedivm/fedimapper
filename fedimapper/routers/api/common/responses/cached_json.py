import typing
from datetime import datetime, timedelta
from wsgiref.handlers import format_date_time

from starlette.background import BackgroundTask
from starlette.responses import JSONResponse

from fedimapper.settings import settings


class CachedJSONResponse(JSONResponse):
    def __init__(
        self,
        content: typing.Any,
        status_code: int = 200,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        media_type: typing.Optional[str] = None,
        background: typing.Optional[BackgroundTask] = None,
        expires_ttl: int = 15 * 60,
        stale_while_revalidate_ttl: int | None = None,
        stale_if_error_ttl: int | None = None,
    ) -> None:
        super().__init__(content, status_code, headers, media_type, background)

        if status_code in [200, 201, 203] and not settings.debug:
            if not stale_while_revalidate_ttl:
                stale_while_revalidate_ttl = expires_ttl * 5
            if not stale_if_error_ttl:
                stale_if_error_ttl = expires_ttl * 5
            self.headers[
                "Cache-Control"
            ] = f"public, stale-while-revalidate={stale_while_revalidate_ttl}, stale-if-error={stale_if_error_ttl}, max-age={expires_ttl}"

            expires_datetime = datetime.now() + timedelta(seconds=expires_ttl)
            expires_timestamp = int(round(expires_datetime.timestamp()))
            self.headers["Expires"] = format_date_time(expires_timestamp)
