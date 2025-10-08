from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
import routes.user as user
import routes.class_management as class_management
import routes.device as device

# ---------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------
app = FastAPI(
    title="P-Bit WebApp Backend API",
    version="1.0.0",
    description="Backend API for P-Bit Web Application",
)

# ---------------------------------------------------------
# CORS (add BEFORE including routers)
# - Exact allowlist only (safer than '*')
# - Using Bearer tokens => no cookies => allow_credentials=False
# ---------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    # Your LAN dev origin (adjust if your IP/port changes)
    "http://192.168.1.44:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],   # includes OPTIONS (preflight)
    allow_headers=["*"],   # Authorization, Content-Type, etc.
)

# ---------------------------------------------------------
# Routers
# NOTE: Do NOT add extra prefixes here if routers already
# define their own prefixes inside each module.
# ---------------------------------------------------------
app.include_router(user.router)
app.include_router(class_management.router)
app.include_router(device.router)
app.include_router(group.router)
app.include_router(data.router)

@app.get("/")
def read_root():
    return {"message": "P-Bit WebApp Backend API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Backend is running"}

