from fastapi import FastAPI
import routes.user as user
import routes._class as _class
import routes.class_management as class_management
from fastapi.middleware.cors import CORSMiddleware
from db.init_engine import init_db

# Initialize database tables
init_db()  # Re-enabled after migration

app = FastAPI()

# Add CORS middleware BEFORE including routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",  # just in case
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight requests for 24 hours
)

app.include_router(user.router)
app.include_router(_class.router)
# Include routers AFTER CORS middleware
app.include_router(user.router)
app.include_router(class_management.router)

@app.get("/")
def read_root():
    return {"message": "hello"}

