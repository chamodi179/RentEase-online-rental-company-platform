from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=f"RentEase API ({settings.APP_MODE})",
    description="Deployed as two isolated instances of the same codebase — "
                 "api-public mounts only /public/* routes, api-admin mounts only /admin/* routes. "
                 "See architecture doc Section 0/4.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "mode": settings.APP_MODE}


# This is the whole point of the two-instance deployment: an api-public
# process never even imports/registers the admin router group, so there is
# nothing for public traffic to reach even if the RBAC check were bypassed.
if settings.APP_MODE == "admin":
    from app.routers.admin import router as admin_router
    app.include_router(admin_router, prefix="/api/v1")
else:
    from app.routers.public import router as public_router
    app.include_router(public_router, prefix="/api/v1")
