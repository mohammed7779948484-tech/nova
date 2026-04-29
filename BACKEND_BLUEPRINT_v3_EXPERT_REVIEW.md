# 🔬 Backend Blueprint v3 — مراجعة خبيرة + تعديلات

> **المُراجِع:** AI Expert Agent (Z.ai Code)
> **المرجع:** `wassim249-backend/` (reference-template) + `yerdaulet-damir-backend/python-backend/` (base)
> **تاريخ:** 2025-04-29 | **الإصدار:** 3.0 Expert Review
> **الأساس:** مراجعة شاملة لكود المصدر الفعلي لكلا المستودعين (ليس فقط README)

---

## 📊 تقييم عام — الخلاصة أولاً

| المعيار | wassim249 (المرجع) | yerdaulet-damir (الأساس) |
|---------|-------------------|------------------------|
| **جودة الكود** | ★★★★☆ إنتاجي حقيقي | ★★★☆☆ MVP أولي |
| **نضج البنية** | ناضج — retry, fallback, metrics, profiling | نظيف — لكن كثير scaffold غير مكتمل |
| **PostgresSaver** | ✅ مكتمل ومجرب | ❌ InMemorySaver فقط |
| **HITL (interrupt)** | ✅ مكتمل + Command(resume=...) | ❌ غير موجود |
| **Multi-tenant** | ❌ single-tenant فقط | ✅ Supabase RLS + tenant isolation |
| **Channel Adapters** | ❌ web فقط | ⚠️ scaffold فقط (WhatsApp router لا يستدعي graph) |
| **LLM Service** | ★★★★★ circular fallback + retries | ★★☆☆☆ factory بسيط بدون retry |
| **SQL Schema** | ★★★☆☆ Alembic (SQLModel) | ★★★★★ Supabase RLS + triggers + 11 جدول |
| **خطيرة** | sync DB في async context | sync httpx في async tool calls |

**القرار النهائي:** ✅ Blueprint صحيح — yerdaulet-damir كأساس + wassim249 كمرجع لأنماط الإنتاج.

---

## ⚖️ قواعد تنظيم الكود (NON-NEGOTIABLE)

### القاعدة 1: حد 300 سطر لكل ملف
أي ملف `.py` في المشروع MUST NOT يتجاوز **300 سطر** برمجي (بدون counting فاضلة comments و imports).
إذا وصل الملف لحد 300 سطر → MUST يتم تقسيمه فوراً إلى وحدات أصغر.

**كيفية التقسيم:**
- **Models/Schema**: افصل Pydantic models في ملف منفصل (`schemas/`) أو داخل domain module
- **Services**: قسم service كبير إلى sub-services حسب المسؤولية
- **Routes**: قسم router كبير إلى sub-routers حسب resource
- **Tools (LangGraph)**: كل tool في ملف منفصل تحت `src/tools/`
- **Utility functions**: تجمّع في `src/core/utils.py` أو وحدات فرعية

**استثناءات:**
- ملفات الـ migrations (SQL) لا تخضع لهذا الحد
- ملفات الـ tests لكل وحدة يمكن أن تصل 400 سطر كحد أقصى

### القاعدة 2: وحدات متماسكة (Cohesion)
كل ملف MUST يعبّر عن مسؤولية واحدة. إذا كنت تصف الملف بـ "و" (هذا الملف يفلتر ويُرسل ويُسجّل) → يحتاج تقسيم.

---

## 🚨 مشاكل حرجة اكتشفناها في الكود الفعلي

### 🔴 مشكلة 1: WhatsApp Router لا يستدعي الـ Graph فعلياً

```python
# yerdaulet-damir/src/channels/whatsapp/router.py — السطر 29-39
@router.post("")
async def receive_webhook(request: Request):
    payload = await request.json()
    inbound_msg = adapter.parse_webhook(payload)
    
    # Real integration:
    # 1. Start background task to invoke graph using `inbound_msg`.
    # 2. Graph outputs an OutboundMessage.
    # 3. Adapter uses send_reply to send it back.
    
    return {"status": "ok"}  # ← لا يفعل شيئاً!
```

**التأثير:** Blueprint المرحلة 6 تقول "تفعيل invoke_graph() + send_reply()" — هذا **صحيح لكن غير كافٍ**. نحتاج:
- استدعاء graph فعلي مع `tenant_id` من `phone_number_id`
- إدارة `thread_id` فريد لكل عميل WhatsApp (رقم الهاتف)
- إرسال الرد عبر WhatsApp Cloud API فعلياً (ليس فقط print)
- التعامل مع الردود غير النصية (صور، موقع، أصوات)

### 🔴 مشكلة 2: `send_product_image` لا يُرسل صوراً فعلياً

```python
# yerdaulet-damir/src/tools/send_product_image.py
# الاسم مضلل — يُرجع نص يحتوي URL فقط
# لا يُرسل صورة عبر أي قناة
```

**التأثير:** أداة اسمها "أرسل صورة منتج" لكنها تُرجع نص بالـ URL. يجب ربطها بـ channel adapter لإرسال media فعلي.

### 🔴 مشكلة 3: `instructions` من الـ DB لا تُحقن في System Prompt

```python
# yerdaulet-damir/src/config/db_tenant_config.py:214
instructions=[i["instruction"] for i in (instructions or [])],  # ← يُجلب من DB

# لكن في src/nodes/assistant.py:_build_system_prompt()
# ← لا يوجد أي إشارة لـ instructions في الـ prompt!
```

**التأثير:** تعليمات مخصصة لكل agent مخزنة في جدول `agent_instructions` لكنها **لا تُستخدم أبداً**. هذا gap حرج في المرحلة 2.

### 🔴 مشكلة 4: httpx.Sync في Async Context

```python
# yerdaulet-damir/src/repositories/db_repo.py
self.client = httpx.Client(...)  # ← sync client
# يُستدعى داخل tool calls اللي هي async
# هذا يُعطّل event loop
```

**التأثير:** كل طلب بحث منتج يُعطّل event loop بالكامل حتى يكتمل HTTP request. تحت حمولة عالية هذا كارثي.

### 🟡 مشكلة 5: AgentConfig name collision

```python
# tenant_config.py — Pydantic BaseModel
class AgentConfig(BaseModel):
    name: str, role: str, personality: str, rules: list[str]

# db_tenant_config.py — dataclass
@dataclass
class AgentConfig:
    agent_id: str, tenant_id: str, ... products: list, instructions: list
```

**التأثير:** اسمين مختلفين لنفس الاسم. تُسبب ارتباك وبق高校毕业生.

### 🟡 مشكلة 6: Dead State Fields

```python
# yerdaulet-damir/src/state/agent_state.py
matched_products: list[dict]    # ← لا يُكتب إليها أبداً
product_images: list[str]       # ← لا يُكتب إليها أبداً
```

### 🟡 مشكلة 7: Tenant Config لا يُخزّن مؤقتاً (no caching)

```python
# src/nodes/assistant.py:77
tc = await async_get_tenant(tenant_id)  # ← HTTP request في كل رسالة!
```

---

## ✅ ما نأخذه من `reference-template` — مراجعة محدّثة

| الميزة | الملف المرجعي | حالة الكود الفعلي | كيف نطبقه |
|--------|-------------|-------------------|-----------|
| **PostgresSaver** | `graph.py:77-113` | ✅ مكتمل + production degradation | نستخدم نفس النمط مع Supabase pooler |
| **HITL (interrupt)** | `tools/ask_human.py` | ✅ مكتمل + Command(resume) | نستخدم نفس النمط + تعديل للقنوات غير المتزامنة |
| **LLM Service** | `services/llm/service.py` | ★★★★★ circular fallback + retries | **جديد — كان مفقوداً** |
| **Parallel Tool Execution** | `graph.py:191-194` | ✅ asyncio.gather | **جديد — كان مفقوداً** |
| **Rate Limiting** | `core/limiter.py` | ✅ slowapi + Valkey fallback | نستخدم لكن مع X-Forwarded-For |
| **Sanitization** | `utils/sanitization.py` | ⚠️ به bugs (email validation) | نأخذ sanitize_string فقط |
| **Structured Logging** | `core/logging.py` | ✅ structlog + correlation ID + JSONL | نستخدم كما هو |
| **Profiling Middleware** | `core/middleware.py` | ✅ pyinstrument + tracemalloc | **جديد — ممتاز للـ dev** |
| **Docker** | `Dockerfile` + `docker-compose.yml` | ✅ مكتمل + monitoring stack | نأخذ مع تعديلات |
| **Langfuse** | `core/observability.py` | ⚠️ bugs (instance discarded, no flush) | نستخدم مع إصلاح flush on shutdown |
| **Metrics** | `core/metrics.py` + Prometheus | ⚠️ dead code لكن البنية جيدة | نستخدم البنية مع تنظيف |

### 🆕 ميزات جديدة نضيفها (لم تكن في Blueprint الأصلي)

| الميزة | المصدر | السبب |
|--------|-------|-------|
| **LLM Circular Fallback + Retries** | wassim249 `llm/service.py` | الـ base يُنشئ model fresh كل مرة بدون retry |
| **Parallel Tool Execution** | wassim249 `graph.py:191` | الـ base يُنفذ tools بالتسلسل |
| **LLM Registry** | دمج الاثنين | base: multi-provider factory + reference: per-model config |
| **Tenant Config Caching** | تصميمنا | كل رسالة تسوي HTTP request للـ DB حالياً |
| **Dead Code Cleanup** | تحليل الكود | ProductCatalog, JSON repo unreachable, dead state fields |

---

## 🔧 المراحل المحدّثة

---

### المرحلة 0: تنظيف الكود + إصلاحات أساسية (جديدة)

> ⚠️ **هذه المرحلة لم تكن في Blueprint الأصلي وهي مطلوبة قبل أي شيء**

**المدة:** يوم واحد | **الأولوية:** 🔴 حرج

| الملف | التغيير | السبب |
|-------|--------|-------|
| `src/state/agent_state.py` | إزالة `matched_products` و `product_images` (dead fields) | لا يُكتب إليها أبداً |
| `src/models/catalog.py` | حذف بالكامل (dead code) | الـ repositories استبدلته |
| `src/repositories/json_repo.py` | حذف أو تحويل لـ fallback فقط | `__init__.py` يستورد من db_repo فقط |
| `src/config/db_tenant_config.py` | إعادة تسمية `AgentConfig` → `DBAgentConfig` | حل name collision مع `tenant_config.py` |
| `src/config/tenant_config.py` | إضافة `instructions: list[str]` لـ `AgentConfig` | لتخزين instructions من DB |
| `src/repositories/db_repo.py` | تحويل `httpx.Client` → `httpx.AsyncClient` + TTL cache | يُعطّل event loop حالياً |
| `src/nodes/assistant.py` | حقن `instructions` في `_build_system_prompt()` |_instructions تُجلب لكن لا تُستخدم |
| `src/tools/send_product_image.py` | إعادة تسمية → `get_product_details` | الاسم الحالي مضلل |
| `pyproject.toml` | تحديث pinning: `>=` → `~=` أو explicit versions | يتغير مع كل major release |

---

### المرحلة 1: PostgresSaver + ConversationService (محدّثة)

**المرجع:** `wassim249-backend/app/core/langgraph/graph.py:77-113` + `create_graph():198-241`
**المدة:** 3 أيام | **الأولوية:** 🔴 حرج

#### تحسينات على Blueprint الأصلي

| التعديل | التفصيل |
|---------|---------|
| **Connection Pool Lifecycle** | الـ reference يُنشئ pool بـ `max_size=20` مع `autocommit=True`. يجب ضبط `max_size` حسب Supabase pooler (connection pooling mode) |
| **Production Degradation** | الـ reference يكمل بدون checkpointer إذا فشل DB في production. نحتفظ بهذا النمط |
| **Graph Compilation Strategy** | الـ reference يبني graph واحد مع checkpointer. نحتاج graph per tenant (multi-tenant) مع نفس pool |
| **Parallel Tool Execution** | إضافة `asyncio.gather` للـ tool execution (من reference `graph.py:191-194`) |

#### التغييرات المحدّثة

| الملف | التغيير |
|-------|--------|
| `src/graphs/sales_graph.py` | استبدال `InMemorySaver` بـ `AsyncPostgresSaver` + `AsyncConnectionPool` مع multi-tenant support |
| `src/services/conversation_service.py` | **جديد** — حفظ conversations/messages في Supabase عبر PostgREST |
| `src/services/graph_service.py` | **جديد** — إدارة graph instances + pool lifecycle |
| `src/channels/web/router.py` | استخدام `graph_service.invoke()` بدل graph محلي |
| `src/app.py` | إضافة pool open/close في lifespan |
| `pyproject.toml` | إضافة `langgraph-checkpoint-postgres>=2.0`, `psycopg[binary]>=3.0`, `psycopg-pool>=3.0` |

#### نمط Multi-Tenant Graph Service (جديد)

```python
# src/services/graph_service.py — إدارة graph لكل tenant
class GraphService:
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool
        self._graphs: dict[str, CompiledStateGraph] = {}
    
    async def get_graph(self, tenant_id: str) -> CompiledStateGraph:
        if tenant_id not in self._graphs:
            checkpointer = AsyncPostgresSaver(self._pool)
            await checkpointer.setup()
            self._graphs[tenant_id] = build_sales_graph().compile(checkpointer=checkpointer)
        return self._graphs[tenant_id]
    
    async def invoke(self, tenant_id: str, thread_id: str, message: str, channel: str):
        graph = await self.get_graph(tenant_id)
        config = {"configurable": {"thread_id": thread_id, "tenant_id": tenant_id}}
        result = await graph.ainvoke({"messages": [HumanMessage(content=message)]}, config)
        return result
```

> **ملاحظة:** بناء graph منفصل لكل tenant قد لا يكون ضرورياً إذا كان الـ state يحتوي على `tenant_id` في `config`. يمكن استخدام graph واحد مع `tenant_id` في الـ `configurable`. نقيّم هذا أثناء التنفيذ.

#### التحقق
- [ ] المحادثات تبقى بعد إعادة التشغيل
- [ ] كل رسالة تُحفظ في جدول `messages`
- [ ] `GET /api/agents/{slug}/conversations` يعمل
- [ ] **جديد:** Connection pool يعمل مع Supabase connection pooler
- [ ] **جديد:** Parallel tool execution يعمل

---

### المرحلة 2: LLM Service + ذاكرة سياق خدمة العملاء (محدّثة)

**المرجع:** `wassim249-backend/app/services/llm/service.py` (circular fallback) + `wassim249-backend/app/services/llm/registry.py`
**المدة:** 3 أيام (كان يومين) | **الأولوية:** 🔴 حرج (رُفعت)

#### لماذا أضفنا LLM Service هنا؟

الكود الحالي في `assistant.py` يُنشئ LLM fresh كل رسالة:
```python
# yerdaulet-damir/src/nodes/assistant.py:80
model = create_llm(tc).bind_tools(ALL_TOOLS)  # ← كل رسالة! بدون retry!
```

المشاكل:
1. **لا يوجد retry** — إذا OpenAI رجّع rate limit، الطلب يفشل فوراً
2. **لا يوجد fallback** — إذا model معطل، لا يوجد بديل
3. **لا يوجد timeout** — طلب قد يعلق للأبد
4. **no tool binding preservation** — bind_tools يُسمى كل مرة

#### ما نأخذه من reference-template LLM Service

| الميزة | من `llm/service.py` | لماذا مهم |
|--------|---------------------|----------|
| **Circular Fallback** | `_switch_to_next_model()` | إذا model فشل → ينتقل للتالي تلقائياً |
| **Per-model Retries** | `tenacity` + exponential backoff | يُعالج rate limits + timeouts |
| **Total Timeout Budget** | `asyncio.wait_for(timeout=LLM_TOTAL_TIMEOUT)` | يمنع infinite retry loops |
| **Structured Output** | `response_format` + `with_structured_output()` | مفيد لاستخراج السياق |

#### ما نعدّل عليه

| التعديل | السبب |
|---------|-------|
| **Multi-provider Registry** | الـ reference OpenAI-only. الـ base يدعم OpenAI + Anthropic + Google. ندمج الاثنين |
| **Per-tenant Model Config** | كل tenant يحدد provider + model من DB. الـ reference models ثابتة في Registry |
| **Remove OpenAI-only imports** | `from openai import RateLimitError` → generic LangChain exceptions |

#### نمط LLM Service المعدّل

```python
# src/services/llm_service.py — دمج reference pattern + base multi-provider
class TenantLLMService:
    """LLM service with tenant-aware model selection + retries + fallback."""
    
    def __init__(self):
        self._cache: dict[str, Any] = {}  # tenant_id → cached LLM instance
    
    async def get_llm(self, tenant_config: TenantConfig):
        """Get or create LLM for tenant with retry + fallback support."""
        tc = tenant_config
        primary = create_llm(tc)  # من base — يدعم multi-provider
        # نربط primary بـ fallback chain
        # (التفاصيل أثناء التنفيذ)
```

#### ذاكرة سياق خدمة العملاء (محسّنة)

Blueprint الأصلي كان جيد لكن نحتاج تعديل:

| الملف | التغيير |
|-------|--------|
| `src/state/agent_state.py` | إضافة حقول الذاكرة (من Blueprint) + إزالة dead fields |
| `src/services/context_service.py` | **جديد** — `ConversationContext` + استخراج سياق تلقائي |
| `src/nodes/assistant.py` | حقن السياق + **instructions** في system prompt |
| `src/config/tenant_config.py` | إضافة `instructions: list[str]` + app-level caching |

#### Tenant Config Caching (جديد)

```python
# src/config/tenant_config.py — إضافة TTL cache
from cachetools import TTLCache

_tenant_cache = TTLCache(maxsize=100, ttl=300)  # 5 min cache

async def async_get_tenant(tenant_id: str) -> TenantConfig:
    if tenant_id in _tenant_cache:
        return _tenant_cache[tenant_id]
    tc = await _load_from_db(tenant_id)
    _tenant_cache[tenant_id] = tc
    return tc
```

#### التحقق
- [ ] السياق يُحدَّث تلقائياً من الرسائل
- [ ] `handoff_requested` يُفعّل عند طلب مشرف
- [ ] **جديد:** instructions من DB تظهر في system prompt
- [ ] **جديد:** LLM retry + fallback يعمل عند rate limit
- [ ] **جديد:** Tenant config يُخزّن مؤقتاً (لا HTTP request كل رسالة)

---

### المرحلة 3: التدخل البشري Human-in-the-Loop (محدّثة)

**المرجع:** `wassim249-backend/app/core/langgraph/tools/ask_human.py` + `graph.py:283-311` (resume logic)
**المدة:** 4 أيام (كان 3 أيام) | **الأولوية:** 🔴 حرج (رُفعت)

#### تعديلات مهمة

| التعديل | التفصيل |
|---------|---------|
| **Resume في القنوات غير المتزامنة** | Blueprint يقول `Command(resume=...)` — لكن في WhatsApp، العميل يرسل رسالة جديدة بدل resume API. نحتاج mechanism مختلف |
| **Pending Reviews Polling** | المشرف البشري يحتاج يرى المحادثات المعلقة. نحتاج endpoint + optional webhook |
| **Handoff vs Escalation** | فرق بين "اسأل مشرف وراجع" و"سّلم المحادثة لمشرف بالكامل" |

#### آلية HITL لـ WhatsApp (جديد)

```
العميل يرسل رسالة → Graph يعالج → AI يستدعي ask_human()
    ↓
Graph يتوقف (interrupt) → يُرسل للعميل: "تم تحويلك لموظف..."
    ↓
المشرف يرى المحادثة في Dashboard → يكتب رد
    ↓
رد المشرف → Command(resume=response) → Graph يُكمل
```

```python
# src/tools/ask_human.py — محسّن
@tool
def ask_human(question: str) -> str:
    """إيقاف التنفيذ وسؤال المشرف البشري.
    
    يُستدعى عندما:
    1. العميل يطلب التحدث مع موظف
    2. AI غير واثق من الإجابة
    3. الشكوى أو المشكلة معقدة
    """
    user_response = interrupt({
        "type": "human_review",
        "question": question,
        "timestamp": datetime.utcnow().isoformat(),
    })
    return str(user_response)
```

#### التغييرات المحدّثة

| الملف | التغيير |
|-------|--------|
| `src/tools/ask_human.py` | **جديد** — tool مع interrupt + metadata |
| `src/tools/__init__.py` | إضافة `ask_human` |
| `src/tools/escalate_human.py` | **جديد** — tool لتسليم كامل (handoff) |
| `src/api/handoff_routes.py` | **جديد** — pending-reviews, resume, handoff, human-message |
| `src/services/graph_service.py` | إضافة `get_pending_interrupts()` |
| `src/channels/whatsapp/router.py` | إضافة آلية resume عبر رسالة WhatsApp |

#### API للتدخل البشري (محدّث)

```
=== Human-in-the-Loop ===
GET  /api/agents/{slug}/pending-reviews    → محادثات تنتظر مراجعة (paginated)
GET  /api/conversations/{id}/interrupt-info → تفاصيل interrupt (لماذا توقف)
POST /api/conversations/{id}/resume         → استكمال بعد إجابة المشرف
POST /api/conversations/{id}/handoff        → تسليم كامل لمشرف بشري
POST /api/conversations/{id}/human-message  → رسالة من المشرف (تُدفع للعميل مباشرة)
```

#### التحقق
- [ ] AI يوقف التنفيذ عند `ask_human` tool
- [ ] `POST /resume` يُكمل المحادثة
- [ ] `POST /handoff` يُسلّم لمشرف بشري
- [ ] **جديد:** WhatsApp resume يعمل عبر رسالة جديدة
- [ ] **جديد:** Dashboard يعرض المحادثات المعلقة

---

### المرحلة 4: Rate Limiting + Sanitization (محدّثة)

**المرجع:** `wassim249-backend/app/core/limiter.py` + `app/utils/sanitization.py`
**المدة:** يوم واحد | **الأولوية:** 🟢 متوسط

#### تحسينات

| التعديل | التفصيل |
|---------|---------|
| **X-Forwarded-For** | الـ reference يستخدم `get_remote_address` مباشرة. نحتاج header handling للـ proxy |
| **Per-tenant Rate Limiting** | كل tenant يحتاج limit خاص (حسب subscription plan) |
| **Sanitization bugs** | نأخذ `sanitize_string` فقط. نتجاهل `sanitize_email` (به bug) و `validate_password_strength` (مكرر) |

```python
# src/core/limiter.py — محسّن
def get_client_ip(request: Request) -> str:
    """Get client IP respecting X-Forwarded-For from reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

---

### المرحلة 5: Structured Logging (محسّنة)

**المرجع:** `wassim249-backend/app/core/logging.py`
**المدة:** يوم واحد | **الأولوية:** 🟢 متوسط

#### إضافة (لم تكن في Blueprint الأصلي)

| الميزة | من reference |
|--------|-------------|
| **Logging Context Middleware** | يربط `tenant_id` + `conversation_id` بكل log event |
| **Correlation ID** | كل request يحصل على UUID يظهر في كل log |
| **Dual Output** | console (dev) + JSONL file (prod) مع daily rotation |
| **Request-scoped binding** | `structlog.contextvars.bind_contextvars()` |

```python
# مثال output
{
  "timestamp": "2025-04-29T10:30:00Z",
  "level": "info",
  "event": "chat_request_received",
  "tenant_id": "flower_shop",
  "conversation_id": "conv_abc123",
  "channel": "whatsapp",
  "request_id": "req_xyz789",
  "message_count": 5
}
```

---

### المرحلة 6: تفعيل WhatsApp (محدّثة بشكل كبير)

**المرجع:** `yerdaulet-damir-backend/python-backend/src/channels/whatsapp/` (scaffold) + Meta Cloud API docs
**المدة:** 5 أيام | **الأولوية:** 🔴 حرج (رُفعت من 🟢)

> ⚠️ **هذه هي القناة الأساسية للمنصة — ليست "متوسطة"**

#### ما تحتاجه فعلياً (أكثر من Blueprint الأصلي بكثير)

| الخطوة | التفصيل |
|--------|---------|
| **1. Webhook → Graph** | WhatsApp router يستدعي `graph_service.invoke()` فعلياً |
| **2. Graph → WhatsApp Reply** | `send_reply()` يُرسل عبر Meta Cloud API (ليس print) |
| **3. Thread ID Mapping** | `wa_id` (رقم WhatsApp) → `thread_id` في Supabase |
| **4. Media Messages** | التعامل مع صور/مقاطع/مواقع من WhatsApp |
| **5. Typing Indicator** | إرسال "typing" action أثناء معالجة الرسالة |
| **6. Interactive Messages** | قوائم، أزرار (Interactive Message Templates) |
| **7. Rate Limiting per Phone** | Meta يحدد 80 msg/sec — نحتاج queue |

#### نقطة مهمة: POST /api/chat للـ web مختلف عن WhatsApp

```
Web (SSE):  Client ←SSE stream── FastAPI ←invoke── Graph
WhatsApp:   Client ←API call── FastAPI ←invoke── Graph ←webhook── Meta
```

> WhatsApp **لا يدعم SSE**. الرد يُرسل عبر POST request إلى Meta Cloud API.

#### التغييرات المحدّثة

| الملف | التغيير |
|-------|--------|
| `src/channels/whatsapp/adapter.py` | **إعادة كتابة** — parse webhook + send via Meta API + media handling |
| `src/channels/whatsapp/router.py` | **إعادة كتابة** — invoke graph + send reply + thread mapping |
| `src/channels/whatsapp/client.py` | **جديد** — Meta Cloud API client (httpx async) |
| `src/channels/whatsapp/media.py` | **جديد** — Media upload/download from Meta |
| `src/services/thread_mapping.py` | **جديد** — wa_id → thread_id mapping in Supabase |
| `src/services/graph_service.py` | إضافة `invoke_for_channel()` — يُرسل للعميل مباشرة |

#### Pywa vs Direct HTTP

السؤال: هل نستخدم `pywa` (WhatsApp API wrapper) أم httpx مباشرة؟

| | pywa | httpx مباشرة |
|---|------|-------------|
| **التعقيد** | wrapper جاهز | نكتب API calls يدوياً |
| **المرونة** | محدود لـ Meta API | كامل التحكم |
| **الصيانة** | يعتمد على أطراف ثالثة | نحن نتحكم |
| **التوثيق** | docs.pywa.io | developers.facebook.com |

**التوصية:** httpx مباشرة. السبب:
1. Meta API مستقر وواضح
2. نحتاج تحكم كامل في retry, timeout, queue
3. pywa يضيف dependency قد لا نحتاجه
4. الـ scaffold الحالي في yerdaulet-damir لا يستخدم pywa أصلاً

---

### المرحلة 7: Docker + الإنتاج (محدّثة)

**المرجع:** `wassim249-backend/Dockerfile` + `docker-compose.yml`
**المدة:** 2 يوم | **الأولوية:** 🔴 حرج

#### إضافات على Blueprint الأصلي

| الإضافة | التفصيل |
|---------|---------|
| **Supabase Connection** | Docker compose لا يحتاج PostgreSQL — يستخدم Supabase cloud |
| **Health Check** | إضافة `/health` مع DB connectivity check |
| **Multi-stage Build** | Docker image أصغر |
| **Environment Validation** | فشل سريع إذا env vars مفقودة |
| **Graceful Shutdown** | pool close + in-flight request drain |

```yaml
# docker-compose.yml — مبسّط (بدون PostgreSQL محلي)
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}  # Supabase
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      retries: 3
```

---

## 📋 ملخص الـ APIs النهائي (محدّث)

```
=== Chat (Web) ===
POST /api/chat                        → إرسال رسالة (SSE stream) [rate-limited]
POST /api/chat/simple                 → إرسال رسالة (JSON response)

=== Webhooks (قنوات خارجية) ===
GET  /webhooks/whatsapp               → التحقق (hub.challenge)
POST /webhooks/whatsapp               → استقبال رسالة WhatsApp
GET  /webhooks/telegram               → (مستقبلي)
POST /webhooks/telegram               → (مستقبلي)

=== Conversations ===
GET  /api/agents/{slug}/conversations → قائمة محادثات (paginated)
GET  /api/conversations/{id}          → محادثة + رسائل
GET  /api/conversations/{id}/checkpoints → نقاط التفرع

=== Human-in-the-Loop ===
GET  /api/agents/{slug}/pending-reviews → محادثات تنتظر مراجعة
GET  /api/conversations/{id}/interrupt-info → تفاصيل التوقف
POST /api/conversations/{id}/resume    → استكمال بعد إجابة المشرف
POST /api/conversations/{id}/handoff   → تسليم بشري كامل
POST /api/conversations/{id}/human-message → رسالة من المشرف

=== Tenant/Agent ===
GET  /api/tenants                     → قائمة المستأجرين
GET  /api/tenants/{slug}/config       → إعدادات agent
GET  /api/tenants/{slug}/products     → منتجات

=== Health ===
GET  /health                          → فحص الخدمة + DB connectivity
```

---

## 📦 التبعيات المطلوبة (محدّث)

```toml
[project]
dependencies = [
    # === Existing (from yerdaulet-damir) ===
    "langgraph>=0.4",
    "langchain-core>=0.3",
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "httpx>=0.26",
    "pydantic>=2.0",
    "openai>=1.0",
    "anthropic>=0.40",
    "google-genai>=1.0",
    "python-dotenv>=1.0",
    
    # === From reference-template ===
    "langgraph-checkpoint-postgres>=2.0",
    "psycopg[binary]>=3.0",
    "psycopg-pool>=3.0",
    "slowapi>=0.1.9",
    "structlog>=25.0",
    "asgi-correlation-id>=4.0",
    "tenacity>=9.0",
    
    # === New additions ===
    "cachetools>=5.0",         # Tenant config TTL cache
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.9",
    "pyinstrument>=5.0",       # Profiling (from reference)
]
observability = [
    "langfuse>=3.0",          # Optional tracing
    "prometheus-client>=0.21",
    "starlette-prometheus>=0.28",
]
```

---

## 🔑 متغيرات البيئة المطلوبة (محدّث)

```env
# === Supabase ===
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
DATABASE_URL=postgresql://postgres.xxx@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# === LLM ===
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# === WhatsApp (Meta Cloud API) ===
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_ACCESS_TOKEN=EAAG...
WHATSAPP_PHONE_NUMBER_ID=123456
WHATSAPP_BUSINESS_ACCOUNT_ID=789012

# === App ===
APP_ENV=development
RATE_LIMIT_DEFAULT=200 per day, 50 per hour
LOG_FORMAT=json
LLM_TOTAL_TIMEOUT=60

# === Optional ===
LANGFUSE_TRACING_ENABLED=false
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

---

## 📅 ترتيب التنفيذ المحدّث

| # | المرحلة | المدة | الأولوية | من المرجع؟ | مخاطر |
|---|---------|------|---------|-----------|--------|
| **0** | **تنظيف + إصلاحات أساسية** | **1 يوم** | **🔴 حرج** | ❌ | منخفض — تنظيف فقط |
| **1** | **PostgresSaver + GraphService** | **3 أيام** | **🔴 حرج** | ✅ graph.py | Supabase pooler compatibility |
| **2** | **LLM Service + Context Memory** | **3 أيام** | **🔴 حرج** | ✅ llm/service.py | Multi-provider registry دمج |
| **3** | **Human-in-the-Loop** | **4 أيام** | **🔴 حرج** | ✅ ask_human.py | WhatsApp resume mechanism |
| **4** | **WhatsApp تفعيل كامل** | **5 أيام** | **🔴 حرج** | ❌ scaffold فقط | Meta API integration |
| **5** | **Rate Limiting + Sanitization** | **1 يوم** | **🟡 عالي** | ✅ limiter.py | منخفض |
| **6** | **Structured Logging** | **1 يوم** | **🟡 عالي** | ✅ logging.py | منخفض |
| **7** | **Docker + الإنتاج** | **2 يوم** | **🔴 حرج** | ✅ Dockerfile | Supabase connection |

**المجموع: 20 يوم عمل (~4 أسابيع)**

> مقارنة بالأصل: 17 يوم → 20 يوم (بسبب إضافة المرحلة 0 + توسيع المرحلة 2 + المرحلة 6)

---

## 🎯 التوصيات النهائية

### 1. ابدأ بـ المرحلة 0 فوراً
التنظيف لا يحتاج تصميم — أزيل dead code و.fix الـ bugs الأساسية. هذا سيُسهّل كل المراحل اللاحقة.

### 2. PostgresSaver + LLM Service هما الأساس
بدون PostgresSaver، لا توجد محادثات مستمرة. بدون LLM Service، كل error يُسقط المحادثة. نفّذهما معاً.

### 3. WhatsApp قبل Telegram/Instagram
القناة الأساسية هي WhatsApp. لا تضيع وقت في Telegram أو Instagram الآن. حول WhatsApp من scaffold لـ production قبل أي شيء.

### 4. لا تستخدم mem0
القرار في Blueprint الأصلي صحيح. ذاكرة السياق في الـ state أفضل لخدمة العملاء. أضف RAG لاحقاً إذا احتجت.

### 5. Docker في الآخر
لا داعي لـ Docker أثناء التطوير. Supabase cloud يعمل مباشرة. اترك Docker للنشر.

### 6. اختبار يدوي أولاً
لا تضف pytest في البداية. اختبر WhatsApp يدوياً عبر ngrok + Meta webhook. أضف automated tests لاحقاً.
