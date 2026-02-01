# backend.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
import os

# ⚡ Variables LiveKit
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
ROOM_NAME = "test-room"
AGENT_NAME = "arabic-insurance-agent"

app = FastAPI()

# --- CORS pour frontend React ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # pour test, mettre ton domaine en production
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Route pour générer un token JWT pour le frontend ---
@app.get("/token")
def get_token(identity: str = "frontend-user"):
    """
    Retourne un JWT LiveKit valide pour rejoindre la room.
    Contient les permissions vidéo/audio et le dispatch automatique d'un agent.
    """
    # Création du token
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)\
        .with_identity(identity)\
        .with_name(identity)\
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=ROOM_NAME,
                can_publish=True,
                can_subscribe=True,
                can_publish_sources=["camera", "microphone"]
            )
        )

    # Dispatch automatique de l'agent
    room_config = api.RoomConfiguration(
        agents=[api.RoomAgentDispatch(agent_name=AGENT_NAME, metadata="manual-backend")]
    )
    token.with_room_config(room_config)

    return {"token": token.to_jwt(), "room": ROOM_NAME}
