from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class UploadRequestSizeLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        max_file_size: int,
        upload_path: str,
    ) -> None:
        self.app = app
        self.max_request_size = max_file_size + 1024 * 1024
        self.upload_path = upload_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        is_upload = (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == self.upload_path
        )
        if not is_upload:
            await self.app(scope, receive, send)
            return

        content_length = next(
            (
                value
                for key, value in scope.get("headers", [])
                if key.lower() == b"content-length"
            ),
            None,
        )
        if content_length is not None:
            try:
                if int(content_length) > self.max_request_size:
                    await self._send_too_large(scope, receive, send)
                    return
            except ValueError:
                pass

        bytes_received = 0

        async def limited_receive() -> Message:
            nonlocal bytes_received
            message = await receive()
            if message["type"] == "http.request":
                bytes_received += len(message.get("body", b""))
                if bytes_received > self.max_request_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="The uploaded request exceeds the configured size limit.",
                    )
            return message

        await self.app(scope, limited_receive, send)

    @staticmethod
    async def _send_too_large(scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "http_error",
                    "message": "The uploaded request exceeds the configured size limit.",
                }
            },
        )
        await response(scope, receive, send)
