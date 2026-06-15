from fastapi import FastAPI
from routes.api import router

app = FastAPI()

app.include_router(router)

@app.get("/")
def home():
    return {"message": "Auth system running 🚀"}