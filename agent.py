import logging
from dotenv import load_dotenv
from insurance_rag_tool import search_insurance_claims, transfer_to_advisor, identify_and_profile_user, verify_2fa_code

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
)

from livekit.plugins import noise_cancellation, silero, google
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(".env.local")
logger = logging.getLogger("agent")
logging.basicConfig(level=logging.INFO)

# =========================
# Instructions de l’agent
# =========================
AGENT_INSTRUCTIONS = """
أنت خبير تأمين مغربي ذكي ومحترف (Expert Assurance).

**MÉTA-RÈGLE LINGUISTIQUE (LANGUAGE RULE):**
- Détecte immédiatement la langue du client (Darija, Arabe, ou Français).
- **Réponds toujours dans la même langue que le client.**
- Si les instructions ci-dessous te demandent de dire une phrase, **traduize-la** naturellement dans la langue actuelle de la conversation.

**المهمة:** تسيير المكالمة بذكاء. حاول تتعرف على العميل باش تخدمو حسن، ولكن إلا ماعندوش الرقم، جاوبو على أسئلتو العامة.

**بروتوكول تسيير المكالمة (PROTOCOL):**

1. **مرحلة التعرف الآمن (IDENTIFICATION & SECURITE):**
   - اطلب رقم لاكارط (CIN) أو رقم البوليصة.
   - عندما يعطيك العميل الرقم، استعمل فوراً أداة: `identify_and_profile_user`.
   - **هام جداً:** هذه الأداة سترسل "كود سري" للعميل (Email/SMS) وستطلب منك أن تسأله عنه.
   - قل للعميل: "لقد أرسلت لك رمز تحقق (Code) للحماية. هل يمكنك قراءته لي؟"
   - عندما يعطيك الكود (مثلاً 5892)، استعمل أداة `verify_2fa_code` للتحقق منه.
   - إذا نجح التحقق، ستظهر لك استراتيجية التعامل (VIP/Standard). طبقها فوراً وكمل المكالمة.

2. **مرحلة التقييم والإجابة (THE FILTER & RESOLUTION):**
   - دابا، سواء عرفتيه شكون أو لا، طبق القواعد:

   - **سول راسك:** *واش هادشي إجراء عادي ولا نزاع معقد؟*
   
     أ. **حالات عادية (أسئلة عامة):** - أمثلة: "كيفاش نديكلاري؟"، "شنو الوثائق؟"، "شحال د الوقت؟"، "واش الزجاج مغطي؟".
        - **الإجراء:** استعمل الأداة `search_insurance_claims` وجاوبو من المعلومات اللي فيها.
        - (ملاحظة: وخا مايكونش عندك الرقم ديالو، جاوبو على المساطر العامة).

     ب. **حالات معقدة (دوز الخط فوراً للمستشار):**
        - أمثلة: "الشركة رفضات تخلصني"، "باغي ندعيكم"، "سيارة دبلوماسية/عسكرية"، "غوات وصداع"، "بغيت مسؤول".
        - **الإجراء:** استعمل الأداة `transfer_to_advisor`.

3. **استراتيجية استعمال الأدوات:**
   - جرب دائماً تلقى الجواب بـ `search_insurance_claims`.
   - **ولكن** إلا الأداة رجعات "No information found" أو الجواب عام بزاف -> **ماتقولش ماعرفتش**، دوز الخط بـ `transfer_to_advisor`.

4. **أسلوب الجواب:**
   - كون محترف، ضريف، وهضر نيشان بالدارجة أو اللغة اللي ختارها العميل.
   - عند التحويل: "سمح ليا، هاد الملف حساس وشوية معقد. غادي ندوزك دابا نيت عند مستشار خبير باش يتكلف بيك."

**قواعد صارمة (MAMNOU3):**
- ممنوع تفتي أو تخترع قوانين من راسك.
- ممنوع تعطي استشارة قانونية شخصية.
"""

# =========================
# Classe Agent
# =========================
class Assistant(Agent):
    def __init__(self):
        super().__init__(
            instructions=AGENT_INSTRUCTIONS,
            tools=[search_insurance_claims, transfer_to_advisor,identify_and_profile_user,verify_2fa_code],
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions=(
                "قول جملة ترحيبية قصيرة بالدارجة المغربية: "
                "'السلام عليكم، مرحبا بيك. باش نجبد الدوسي ديالك ونعاونك دغيا، "
                "عطيني عفاك رقم لاكارط (CIN) ولا رقم العقدة (Numéro de Police)؟'"
            )
        )

# =========================
# Prewarm (VAD)
# =========================
def prewarm(proc: JobProcess):
    logger.info("Prewarming VAD model...")
    proc.userdata["vad"] = silero.VAD.load()

# =========================
# Entrypoint LiveKit
# =========================
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            voice="Puck",
            temperature=0.8,
            instructions="You are a multilingual insurance assistant (Darija, Arabic, French). Adapt to the user's language immediately."
        ),
        turn_detection=MultilingualModel(),
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    agent = Assistant()

    logger.info("Connecting to LiveKit room...")
    await ctx.connect()
    logger.info("Connected to LiveKit room")

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )

    logger.info("Agent session started successfully")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="arabic-insurance-agent"
        )
    )