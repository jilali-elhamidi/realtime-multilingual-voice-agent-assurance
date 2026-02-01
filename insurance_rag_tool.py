import asyncio
import logging
import aiohttp  # <--- NOUVEL IMPORT
import json
from dotenv import load_dotenv  # ✅ تحميل البيئة
from google import genai # ✅ مكتبة جوجل للذكاء الاصطناعي
from sentence_transformers import SentenceTransformer
from chromadb import PersistentClient
from livekit.agents import function_tool
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SENDER_EMAIL = ""
SENDER_PASSWORD = "" # Pas votre mot de passe normal !
RECEIVER_EMAIL = ""

logger = logging.getLogger("tools")


load_dotenv(".env.local")

logger = logging.getLogger("tools")

# 2. إعداد مفتاح Google Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    logger.warning("⚠️ GOOGLE_API_KEY introuvable dans .env.local !")
    client = None
else:
    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    
# =========================
# Lazy load pour modèles et DB
# =========================
_embedding_model = None
_chroma_client = None
_insurance_collection = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        logger.info("🔄 Loading embedding model (insurance)...")
        _embedding_model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
    return _embedding_model

def get_insurance_collection():
    global _chroma_client, _insurance_collection
    if _insurance_collection is None:
        logger.info("📂 Loading insurance sinistre collection...")
        _chroma_client = PersistentClient(path="./chroma_insurance_db")
        _insurance_collection = _chroma_client.get_collection(
            name="insurance_claims_qa"
        )
    return _insurance_collection

# =========================
# RAG TOOL – INSURANCE
# =========================
@function_tool
async def search_insurance_claims(query: str) -> str:
    """
    Search knowledge base for insurance claims (Sinistre).
    Returns exact paragraphs from the documentation.
    """
    logger.info(f"🛡️ RAG Search: {query}")

    try:
        model = get_embedding_model()
        collection = get_insurance_collection()

        query_embedding = model.encode(query).tolist()

        # نطلب 4 نتائج لضمان تغطية الموضوع
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=4, 
            where={"category": "sinistre"}
        )

        if results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]

            # صياغة الرد بشكل يسهل على الموديل فهمه
            response = "## معلومات موثقة من قاعدة البيانات:\n"
            for i, (doc, meta) in enumerate(zip(docs, metas), 1):
                topic = meta.get('topic', 'general')
                # ✅ التغيير: نعيد النص كاملاً بدون قص [:1000]
                response += f"--- معلومة {i} ({topic}) ---\n{doc}\n\n"
            
            return response

        return "للأسف، لم أجد معلومة دقيقة في المراجع حول هذا السؤال."

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return "حدث خطأ تقني في البحث."
        
        
# =========================
# Supervisor AI Async (quasi-temps réel)
# =========================
async def consult_ai_supervisor(user_text: str):
    """
    Analyse text with Gemini Flash using the current google-genai SDK
    and return a classification + reasoning JSON.
    """

    if not GOOGLE_API_KEY:
        return {"classification":"COMPLEXE","reasoning":"No API Key","routing_dept":"Support"}

    prompt = f"""
Agis comme un Superviseur Senior en Assurance.
Analyse cette demande client: '{user_text}'
Réponds en JSON unique avec:
{{"classification":"STANDARD|COMPLEXE|CRITIQUE",
 "confidence":0-100,
 "reasoning":"explication courte",
 "routing_dept":"Support|Juridique|Expertise|Crise"}}
"""

    try:
        # On appelle le modèle via client.models.generate_content
        result = await asyncio.to_thread(
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt]
            )
        )

        text = result.text.strip()
        # Nettoyage si nécessaire
        clean_text = text.replace("```json", "").replace("```", "").strip()
        
        return json.loads(clean_text)

    except Exception as e:
        logger.error(f"❌ Supervisor Error: {e}")
        return {"classification":"COMPLEXE","reasoning":"AI Error","routing_dept":"Backup"}
# =========================
# TOOL 2: Intelligent Handover Async
# =========================
@function_tool
async def transfer_to_advisor(reason: str) -> str:
    """
    Escalade à un agent humain avec analyse supervisée par l'IA.
    Répond quasi-instant, le verdict complet arrive async.
    """
    logger.info(f"🚨 HANDOVER REQUESTED for: {reason}")

    # 1️⃣ Pré-réponse immédiate pour UX (Voice)
    immediate_msg = "SYSTEM: 🔵 Votre demande est en cours d'analyse par notre superviseur IA..."
    
    # 2️⃣ Lancer analyse async en arrière-plan
    async def background_analysis(text):
        judgement = await consult_ai_supervisor(text)
        classification = judgement.get("classification", "STANDARD")
        dept = judgement.get("routing_dept", "Support")
        explanation = judgement.get("reasoning", "N/A")
        priority = "NORMAL"

        if classification == "CRITIQUE":
            ai_msg = f"SYSTEM: 🔴 ALERTE CRITIQUE ({explanation}). Transférez immédiatement à la cellule de CRISE."
            priority = "URGENT"
        elif classification == "COMPLEXE":
            ai_msg = f"SYSTEM: 🟠 Cas complexe détecté ({dept}). Transférez à un Spécialiste Senior."
            priority = "HIGH"
        else:
            ai_msg = "SYSTEM: 🟢 Demande standard, mais le client insiste. Transfert au Support niveau 1."

        # Webhook (preuve technique)
        WEBHOOK_URL = "https://webhook.site/"
        payload = {
            "event": "ai_supervised_handover",
            "user_input": text,
            "ai_analysis": judgement,
            "priority": priority
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(WEBHOOK_URL, json=payload, timeout=2):
                    pass
        except Exception as e:
            logger.error(f"❌ Webhook Error: {e}")

        # Ici vous pouvez pousser ai_msg vers Voice Agent (callback/session)
        logger.info(f"Follow-up message ready: {ai_msg}")

    asyncio.create_task(background_analysis(reason))
    return immediate_msg
    
    
# =========================
# TOOL 3: SMART CRM PROFILER (NOUVEAU & AVANCÉ)
# =========================

# Base de données simulée mais RICHE
ADVANCED_CRM_DB = {
    "A100": {
        "identity": {"name": "M. Abdlbasset elhamrit", "segment": "VIP Gold"},
        "psychology": {"patience": "FAIBLE", "tone_preference": "Direct et Efficace"},
        "history": {"claims": 0, "tenure": "10 ans"},
        "alerts": {"type": "OPPORTUNITÉ", "msg": "Contrat auto expire dans 3 jours."},
        "strategy": "Ne perds pas de temps. Règle le problème vite et propose le renouvellement à la fin."
    },
    "B200": {
        "identity": {"name": "Mme. Samira Idrissi", "segment": "Risque Élevé"},
        "psychology": {"patience": "MOYENNE", "tone_preference": "Formel et Prudent"},
        "history": {"claims": 4, "last_claim": "Fraude suspectée 2023"},
        "alerts": {"type": "WARNING", "msg": "Surveillance Fraude active."},
        "strategy": "Sois très poli mais enregistre tout. Ne promets AUCUN remboursement sans validation chef."
    },
    "C300": {
        "identity": {"name": "M. Rachid Tazi", "segment": "Standard"},
        "psychology": {"patience": "ÉLEVÉE", "tone_preference": "Amical et Pédagogue"},
        "history": {"claims": 1, "status": "En cours"},
        "alerts": {"type": "INFO", "msg": "Dossier bris de glace ouvert hier."},
        "strategy": "Rassure le client sur son dossier en cours. Explique bien les étapes."
    }
}

# --- Stockage temporaire ---
VERIFICATION_SESSION = {}

def send_email_code(code):
    """Envoie un vrai email avec le code"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = "🔐 Code de validation Assurance"

        body = f"Votre code de sécurité est : {code}\n\nNe le partagez pas."
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)
        server.quit()
        logger.info(f"📧 Email envoyé avec succès : {code}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur envoi email: {e}")
        return False

@function_tool
async def identify_and_profile_user(identifier: str) -> str:
    logger.info(f"🔒 AUTH REQUEST: {identifier}")
    clean_id = identifier.strip().upper().replace(" ", "")
    
    profile = ADVANCED_CRM_DB.get(clean_id)
    
    if not profile:
        return "SYSTEM: ❌ Client non trouvé."

    # 1. GÉNÉRATION ALÉATOIRE (C'est "réel" maintenant)
    real_code = str(random.randint(1000, 9999))
    
    # 2. SAUVEGARDE
    VERIFICATION_SESSION["current_user_id"] = clean_id
    VERIFICATION_SESSION["expected_code"] = real_code
    
    # 3. ENVOI RÉEL (Email qui arrive sur votre téléphone)
    # On lance l'envoi (peut prendre 1-2 sec)
    send_email_code(real_code)
    
    # Astuce pour le présentateur : On l'affiche aussi dans la console au cas où l'email traîne
    print(f"\n📢 --- CODE SECRET GÉNÉRÉ : {real_code} ---\n")

    return f"""
    SYSTEM: ✅ Client identifié.
    ACTION : Code de sécurité {real_code} généré et envoyé par email à {RECEIVER_EMAIL}.
    INSTRUCTION : Dis au client : "Pour sécuriser l'accès, je viens de vous envoyer un code de validation sur votre email. Pouvez-vous me le communiquer ?"
    """

@function_tool
async def verify_2fa_code(code: str) -> str:
    # ... (Le reste de la fonction reste identique à ma réponse précédente)
    # Elle comparera le code que vous dites à la voix avec le `real_code` stocké.
    user_id = VERIFICATION_SESSION.get("current_user_id")
    expected = VERIFICATION_SESSION.get("expected_code")

    # Nettoyage (parfois le STT met des espaces "1 2 3 4")
    clean_code = code.strip().replace(" ", "").replace(".", "")
    
    if clean_code == expected:
        profile = ADVANCED_CRM_DB.get(user_id)
        # ... Retourne le profil ...
        return f"AUTH RÉUSSIE pour {profile['identity']['name']}."
    else:
        return f"SYSTEM: ⛔ Code incorrect. Attendu: {expected}, Reçu: {clean_code}."



