from fastapi import FastAPI
import routes.user as user
import routes.class_management as class_management
import routes.device as device
import routes.group as group
import routes.data as data
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# List the exact origins your frontend will be accessed from
# For example:
frontend_origins = [
    "http://13.239.216.36",      # your EC2 frontend HTTP (port 80)
    "http://localhost:3000",     # local dev frontend
    "http://ec2-13-239-216-36.ap-southeast-2.compute.amazonaws.com",
    "http://localhost:8000",
    "http://localhost:3000"
    # add other origins if needed, e.g. HTTPS or different ports
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    max_age=86400,
)

# Include routers AFTER CORS middleware
app.include_router(user.router)
app.include_router(class_management.router)
app.include_router(device.router)
app.include_router(group.router)
app.include_router(data.router)

@app.get("/")
def read_root():
    print("this is root")
    return {"message": "P-Bit WebApp Backend API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Backend is running"}
