from fastapi import FastAPI

from product_recommendation.api import router

app = FastAPI(title="Chobe Product Recommendation Service", version="1.0.0")
app.include_router(router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
