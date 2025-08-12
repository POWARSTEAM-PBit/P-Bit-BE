from fastapi import FastAPI
import routes.user as user
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.include_router(user.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "hello"}

