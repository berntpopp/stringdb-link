"""HTTP server entry point for StringDB-Link."""

import uvicorn

from stringdb_link.app import app
from stringdb_link.config import settings

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_config=None,  # Use our custom logging
        access_log=False,  # Disable uvicorn access log
    )
