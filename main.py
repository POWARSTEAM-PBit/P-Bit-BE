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
<<<<<<< HEAD
    # allow_origins=[
    #     "http://13.239.216.36:80",
    #     "http://127.0.0.1:3000",
    #     "http://localhost:8000",
    #     "http"
    #     "http://localhost:8080",
    #     "http://127.0.0.1:8080",
    #     "http://localhost:4200",
    #     "http://127.0.0.1:4200",
    #     "http://localhost:4000",
    #     "http://127.0.0.1:4000",
    #     "http://localhost:5173",
    #     "http://127.0.0.1:5173",
    #     "http://localhost:5174",
    #     "http://127.0.0.1:5174",
    # ],
    allow_origins=["*"],  # Allow all origins for development; restrict in production
    allow_credentials=False,  # Must be False when using wildcard origins
=======
    allow_origins=["*"],
    allow_credentials=True,
>>>>>>> 9baea566dfb8241c4131331d8ceb9151a8857f66
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
