"""Account-specific model catalogs; credentials never appear in URL parameters."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.services.provider_service import Provider, ProviderConnection, discover_models

router = APIRouter(prefix="/providers", tags=["providers"])


@router.post("/{provider}/models")
async def live_models(provider: Provider, connection: ProviderConnection):
    result = await discover_models(provider, connection)
    return JSONResponse(result, headers={"Cache-Control": "no-store"})
