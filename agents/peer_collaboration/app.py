# agents/peer_collaboration/app.py

from fastapi import FastAPI
from .routing import router

app = FastAPI(title="Peer Collaboration Agent API")
app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Peer Collaboration Agent is running"}
