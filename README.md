# 📞 Realtime Multilingual Voice Agent — Assurance
*The Smart Insurance Voice AI*

> **"Make it real."** — Capgemini GenAI Hackathon 2026

![Status](https://img.shields.io/badge/Status-MVP-success) 
![Python](https://img.shields.io/badge/Python-3.10+-blue) 
![LiveKit](https://img.shields.io/badge/Voice-LiveKit-purple) 
![Gemini](https://img.shields.io/badge/AI-Gemini%20Flash-orange)

---

## 📖 About The Project

**OurCallbot** is a **real-time, agentic voice AI** designed to **revolutionize insurance customer support**.  
Unlike traditional IVRs, it **listens, reasons, and acts**, bridging the language gap with **Darija/French** support.

This project was built for the **Capgemini GenAI & Agentic AI Hackathon**, addressing high-volume repetitive claims while improving personalization and efficiency.

---

## 🚀 Key Features (The 4 Super-Powers)

### 1️⃣ ⚡ Instantaneity (Zero Latency)
- Built on **LiveKit** (Go infra) for **real-time WebRTC streaming**  
- Response time < 200ms — **no awkward pauses**

### 2️⃣ 🧠 Absolute Knowledge (RAG)
- Connected to **ChromaDB** vector database for **accurate, context-aware answers**  
- Avoids hallucinations and retrieves **specific clauses** about claims, delays, and coverage

### 3️⃣ 🎭 Hyper-Personalization (Smart CRM)
- Instantly identifies the user via **CIN / phone number**  
- **Dynamic Psychology:** adapts tone per profile (*Direct* for VIPs, *Formal* for High-Risk users)  
- Supports **2FA security verification** via email simulation

### 4️⃣ 🛡️ The Invisible Supervisor
- **Secondary AI model** monitors the conversation in real-time  
- **Crisis Detection:** triggers human handover if anger or legal threats detected, with **full context summary**
### 5️⃣ 🌍 Production-Ready Integration (SIP/Twilio)

- **Universal Connectivity:** Thanks to LiveKit, the agent natively supports **SIP Trunks and Twilio**.
- **Plug & Play:** It can be deployed on a real phone number immediately.
- **Enterprise Webhooks:** Easily integrates with external CRMs (Salesforce, HubSpot) or ticketing tools via standard JSON webhooks.
---

## 🏗️ Technical Architecture

| Component | Technology | Description |
|-----------|------------|-------------|
| **Core Logic** | Python 3.10+ | Main application logic |
| **Voice Transport** | LiveKit | Low-latency audio streaming (WebRTC) |
| **LLM / Intelligence** | Google Gemini 2.5 Flash | Reasoning, conversation, supervision |
| **Knowledge Base** | ChromaDB | Vector store for RAG (Insurance Docs) |
| **Embeddings** | Sentence-Transformers | `paraphrase-multilingual-MiniLM-L12-v2` |
| **Backend API** | FastAPI | Server & webhooks |

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10 or higher  
- API Keys for **Google Gemini** & **LiveKit Cloud**

### 1️⃣ Clone the repository
```bash
git clone https://github.com/jilali-elhamidi/realtime-multilingual-voice-agent-assurance.git
cd realtime-multilingual-voice-agent-assurance
```

### 2️⃣ Create a Virtual Environment
It is **highly recommended** to use a virtual environment to manage project dependencies.

#### 🖥️ Bash / Command Line

```bash
# Create virtual environment
python -m venv venv


# Activate on Mac/Linux
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 3️⃣ Install Dependencies
Install the **LiveKit agents**, specific plugins (Google Gemini, Silero, Noise Cancellation), and **RAG tools**.

#### 🖥️ Bash / Command Line

```bash
# Core Agent & Plugins
pip install livekit livekit-agents livekit-plugins-google livekit-plugins-noise-cancellation livekit-plugins-silero 

# RAG & Vector DB
pip install chromadb sentence-transformers

# Utilities & APIs
pip install requests python-dotenv
pip install "numpy<2"

# Framework API & Serveur (pour backend.py)
pip install fastapi uvicorn

# Outils asynchrones et IA Google (pour insurance_rag_tool.py)
pip install aiohttp google-genai
```

### ⚙️ Configuration

This project uses a **`.env.local`** file in the root directory to store API keys and credentials.  

#### 🔧 Setup

1. Open `.env.local` in the root folder.
2. Fill in your API keys and endpoints:

```env
GEMINI_API_KEY=your_gemini_key
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret

# Email Configuration (For 2FA Feature)
# You must also update 'insurance_rag_tool.py' 
# SENDER_EMAIL=your_email@gmail.com
# SENDER_PASSWORD=your_app_password
```

## ▶️ Usage - 3 Modes

Vous pouvez lancer le projet de trois manières selon vos besoins :

| Mode | Description | Commande | Notes |
|------|-------------|----------|-------|
| **Console Mode (Text Testing)** | Tester la logique, RAG et flux CRM sans voix. Vous tapez, l'agent répond en texte. | `python agent.py console` | Idéal pour le debug rapide. |
| **Voice Agent (LiveKit Mode)** | Connecte l'agent au LiveKit Cloud. Attend qu'un utilisateur rejoigne la room pour parler. | `python agent.py dev` | Log succès : `"Agent session started successfully"` |
| **Backend API (Pour Frontend)** | Démarre le serveur FastAPI pour générer les tokens pour le frontend React. | `uvicorn backend:app --reload` | URL du serveur : [http://127.0.0.1:8000](http://127.0.0.1:8000) |

---
### 4️⃣ Initialize Knowledge Base (RAG)
You must index the insurance documents into ChromaDB before starting the agent.
Run this script once:

```bash
python script_rag.py
```
### ⚠️ Petit Rappel Code (Important)

Dans votre fichier `insurance_rag_tool.py`, la ligne 140 est actuellement "en dur" :
`WEBHOOK_URL = "https://webhook.site/"`
```python
# Dans insurance_rag_tool.py
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://webhook.site/")
```

## 📊 Canva Mini Presentation

Check out this short presentation: 

[View the Canva Presentation](https://canva-presentation-pi.vercel.app/)
