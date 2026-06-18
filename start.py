import os
import sys

import uvicorn

from app.config.settings import get_settings


def main():
    env = sys.argv[1] if len(sys.argv) > 1 else "dev"
    os.environ["ENV"] = env

    settings = get_settings()

    print(f"Starting server with [{env}] config...")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
