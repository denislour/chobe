from fastapi import FastAPI

from chobe_service_template.api import router

app = FastAPI(title="Chobe satellite service", version="1.0.0")
app.include_router(router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
