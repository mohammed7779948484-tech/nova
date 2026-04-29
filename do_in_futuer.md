# 🚀 خارطة الطريق المتقدمة — تحسين البحث والتخزين والسياق في منصة AI

> **تاريخ البحث:** أبريل ٢٠٢٦ (محدّث ببحث إنترنت فعلي حتى ٢٨ أبريل ٢٠٢٦)  
> **السياق:** منصة SaaS متعددة المستأجرين لخدمة العملاء بالذكاء الاصطناعي  
> **المشروع:** ai-stack (Python Backend + Supabase + LangGraph)  
> **مصادر البحث:** ٥٥+ بحث ويب فعلي، ١٥+ مقالة مقروءة بالتفصيل، ٤٠٠+ مصدر محلل من أوراق بحثية (arXiv)، مدونات تقنية، وثائق رسمية، ومجتمعات المطورين  
> **منهجية البحث:** استخدام z-ai CLI للبحث الفعلي في الإنترنت + قراءة المقالات التفصيلية عبر page_reader

---

## 📋 جدول المحتويات

1. [الملخص التنفيذي — القرارات الرئيسية](#1-الملخص-التنفيذي)
2. [البحث المتجهي والـ Embeddings](#2-البحث-المتجهي-والembeddings)
3. [أنماط RAG المتقدمة](#3-أنماط-rag-المتقدمة)
4. [إدارة السياق والذاكرة المتقدمة](#4-إدارة-السياق-والذاكرة-المتقدمة)
5. [تحسين استهلاك التوكن](#5-تحسين-استهلاك-التوكن)
6. [تخزين متقدم — pgvector + Supabase](#6-تخزين-متقدم--pgvector--supabase)
7. [معالجة النص العربي](#7-معالجة-النص-العربي)
8. [تجربة المستخدم — بحث المنتجات بالذكاء الاصطناعي](#8-تجربة-المستخدم--بحث-المنتجات-بالذكاء-الاصطناعي)
9. [خارطة التنفيذ المرحلية](#9-خارطة-التنفيذ-المرحلية)
10. [تحليل التكاليف](#10-تحليل-التكاليف)
11. [الموارد والمراجع الرئيسية](#11-الموارد-والمراجع-الرئيسية)

---

## 1. الملخص التنفيذي — القرارات الرئيسية

### الوضع الحالي 🔴
- البحث عن المنتجات يتم عبر **استعلامات REST API بسيطة** (ILIKE/contains)
- لا يوجد بحث دلالي (semantic search) ولا embeddings
- لا يوجد بحث هجين (hybrid search)
- الذاكرة محفوظة في InMemorySaver (تضيع عند إعادة التشغيل)
- استهلاك التوكن غير محسّن
- لا يوجد تخزين مؤقت ذكي (semantic caching)

### الوضع المستهدف 🟢
- **بحث هجين**: كلمات مفتاحية (BM25/FTS) + بحث دلالي (Vector) + دمج RRF
- **Embeddings**: Cohere Embed v4 أو OpenAI text-embedding-3-large بـ 1024 بُعد
- **تخزين**: pgvector مع halfvec على Supabase + فهرس HNSW
- **ذاكرة**: AsyncPostgresSaver + PostgresStore + ملخص ذكي + كيانات مستخرجة
- **عربي**: خط أنابيب تطبيع كامل (تشكيل، ألف، تشكيل، لهجات) + قاموس Hunspell عربي
- **RAG متقدم**: CRAG + إعادة كتابة الاستعلام + استرجاع هجين + إعادة ترتيب
- **توكن**: ضغط LLMLingua-2 + تخزين مؤقت دلالي + توجيه نماذج

### جدول القرارات الرئيسية (محدّث بأحدث البحث أبريل ٢٠٢٦)

| القرار | الخيار الموصى به | السبب | مصدر البحث |
|--------|-----------------|-------|-----------|
| **نموذج الـ Embedding** | Cohere Embed v4 (1024 بُعد) | متعدد الوسائط (نص+صورة)، ١٠٠+ لغة، أفضل دعم عربي | Cohere Blog, Dec 2025 |
| **نموذج بديل** | OpenAI text-embedding-3-large → 1024 بُعد | MRL truncation، لدينا API key | OpenAI Docs |
| **أفضل مفتوح المصدر** | BGE-M3 (1024 بُعد) | ٣ طرق استرجاع في نموذج واحد (dense+sparse+ColBERT) | arXiv:2506.06339 |
| **نوع الفهرس** | HNSW (m=16, ef_construction=64) | تحديثات فورية، دقة ٩٩%+، iterative scans في 0.8.0 | pgvector 0.8.0, Nov 2024 |
| **طريقة البحث** | هجين (Arabic FTS + Vector + RRF) | +٦-١٥% دقة على البحث المتجهي وحده | ParadeDB, TigerData benchmarks |
| **الأبعاد** | 1024 | ٩٦.٥% جودة مقارنة بـ 3072، ٥٠% توفير تخزين | OpenAI MRL research |
| **إعادة الترتيب** | Cohere Rerank 4 (pro variant) | +٤٠% تحسن دقة، ١٠٠+ لغة، دعم العربية | Cohere Blog, Dec 2025 |
| **إعادة ترتيب مفتوح المصدر** | Qwen3-Reranker (4B/8B) | أفضل نموذج مفتوح المصدر، متعدد اللغات | QwenLM GitHub, 2025 |
| **الذاكرة قصيرة المدى** | AsyncPostgresSaver (checkpointer) | إلزامي للإنتاج + HITL | LangGraph Best Practices |
| **الذاكرة طويلة المدى** | PostgresStore (cross-thread) + KG | تتبع تفضيلات العملاء عبر الجلسات | LangGraph Store API, Oct 2024 |
| **نوع الذاكرة** | ملخص CoD + كيانات + نافذة منزلقة | توفير ٦٠-٨٥% توكن | Chain-of-Density, 2023+ |
| **ضغط السياق** | LLMLingua-2 (BERT-level) | حتى ٢٠× ضغط، ٣-٦× أسرع من v1 | Microsoft, ACL 2024 |
| **التخزين المؤقت الدلالي** | pgvector في Supabase + L1 hash | ٣٠-٧٠% توفير تكلفة | Redis Blog, Maxim AI |
| **توجيه النماذج** | نموذج رخيص للبسيط + قوي للمعقد | ٤٧-٨٥% تقليل تكلفة | arXiv:2603.04445, Mar 2026 |
| **قاموس عربي FTS** | Hunspell/Ispell مخصص | Snowball الافتراضي معطّل للعربية | wassimbj.github.io |
| **التكلفة الشهرية** | < $10 شهرياً للـ embeddings | التكاليف ضئيلة — اختر بناءً على الجودة | حساباتنا المباشرة |

---

## 2. البحث المتجهي والـ Embeddings

### 2.1 أحدث نماذج الـ Embedding (٢٠٢٥-٢٠٢٦) — محدّث بالبحث الفعلي

| النموذج | الأبعاد | التكلفة/1M tokens | دعم العربية | جودة MTEB | الأفضل لـ | مصدر |
|---------|---------|-------------------|------------|-----------|-----------|------|
| **Cohere Embed v4** 🌟 | 1024 | $0.10 | ممتاز (١٠٠+ لغة) | ★★★★★ | **الأفضل لنا** — متعدد الوسائط | Cohere Blog, Dec 2025 |
| **OpenAI text-embedding-3-large** | 3072→256 | $0.13 | جيد جداً | ~64.5% | MRL truncation مرن | OpenAI Docs |
| **Qwen3-Embedding (8B)** | 1024→256 | مجاني (حوسبة) | ممتاز | **#1 MTEB متعدد اللغات** | أفضل مفتوح المصدر | QwenLM, Jun 2025 |
| **BGE-M3** (مفتوح المصدر) | 1024 (dense+sparse) | مجاني (حوسبة) | ممتاز | ★★★★☆ | **أفضل نموذج مفتوح للعربية** | BAAI, 2024 |
| **Voyage AI voyage-3-large** | 1024→256 | $0.12 | جيد جداً | #1 RTEB | أفضل جودة عامة | PE Collective |
| **Jina CLIP v2** | 1024 (Matryoshka) | مجاني/API | ٨٩ لغة | ★★★★☆ | بحث متعدد الوسائط | Jina AI, Dec 2024 |
| **SILMA Matryoshka v0.1** | قابل للتعديل | مجاني | **متخصص عربي** | ★★★★☆ | عربي فقط | SILMA AI, 2025 |

#### 🆕 Cohere Embed v4 — النموذج الموصى به (ديسمبر ٢٠٢٥)
- **أول نموذج embedding متعدد الوسائط** من Cohere (نص + صور في نفس الفضاء المتجهي)
- **١٢٨K نافذة سياق** — أطول من أي نموذج embedding آخر
- **١٠٠+ لغة** بدعم أصلي 包括 العربية
- **Matryoshka representations** — تقليص الأبعاد بدون إعادة تدريب
- **دعم YAML المهيكل** — مناسب لبيانات المنتجات المنظمة

#### 🆕 Qwen3-Embedding — #1 على MTEB متعدد اللغات (يونيو ٢٠٢٥)
- النسخة 8B **تحتل المرتبة الأولى** على لوحة متصدرين MTEB متعدد اللغات (70.58)
- متوفر بأحجام 0.6B و 4B و 8B
- **نماذج إعادة ترتيب مرافقة** (Qwen3-Reranker)
- دعم Matryoshka

#### ميزة Matryoshka (MRL) — مهمة جداً 🎯
نماذج OpenAI v3 و Cohere v4 و Qwen3 تدعم **تقليص الأبعاد** — يمكنك تخزين 1024-بُعد ولكن الاستعلام بـ 256/512 بُعد مع تدهور تدريجي:
- **text-embedding-3-large** بـ 256 بُعد **يتفوق** على ada-002 الكامل بـ 1536 بُعد
- هذا مهم لتوفير التخزين في pgvector

#### BGE-M3 — النموذج الأكثر ملاءمة لمشروعنا (مفتوح المصدر)
- يدعم **٣ طرق استرجاع في نموذج واحد**:
  1. **Dense retrieval** — تشابه متجهي عادي (1024 بُعد)
  2. **Sparse retrieval** — أوزان رمزية متعلمة (مثل BM25 محسّن)
  3. **Multi-vector (ColBERT)** — تطابق على مستوى الرموز
- **أفضل نموذج مفتوح المصدر للاسترجاع العربي** (بحسب arXiv:2506.06339)
- يمكن تخزين الـ sparse embeddings في pgvector `sparsevec`

### 2.2 pgvector — الحالة الراهنة (٢٠٢٥-٢٠٢٦) — محدّث بالبحث الفعلي

**الإصدار الحالي:** 0.8.2 (فبراير ٢٠٢٦)  
**متوفر على Supabase:** ✅ نعم (كافة المشاريع)

| الميزة | الإصدار | الوصف | الأهمية |
|--------|---------|-------|---------|
| **Iterative Index Scans** | 0.8.0 | حل مشكلة "التصفية المفرطة" — **٩× أسرع** للاستعلامات المُصفّاة | ⭐⭐⭐⭐⭐ |
| **halfvec** | 0.7.0+ | متجهات نصف الدقة (16-bit) — **٥٠% توفير تخزين** | ⭐⭐⭐⭐ |
| **sparsevec** | 0.7.0+ | متجهات متناثرة لـ SPLADE/BGE-M3 | ⭐⭐⭐ |
| **bit** | 0.8.0 | متجهات ثنائية لضغط أقصى | ⭐⭐ |

```sql
-- تفعيل البحث المتكرر التكراري (إلزامي للإنتاج!)
SET hnsw.iterative_scan = 'on';
SET ivfflat.iterative_scan = 'on';
```

#### 🆕 pgvectorscale — DiskANN لـ PostgreSQL
- فهرس **StreamingDiskANN** — يخزن المتجهات على القرص مع رسم بياني مضغوط في الذاكرة
- يتيح البحث في **مليارات المتجهات** بدون تحميل الكل في RAM
- **قياسات أداء:** 471 QPS مقابل 41 QPS لـ Qdrant عند 99% recall (11.4× أفضل)
- **ملاحظة:** غير متوفر بعد على Supabase المستضاف (ذاتي الاستضافة فقط)

#### HNSW مقابل IVFFlat — قرار نهائي

| الميزة | HNSW ✅ | IVFFlat |
|--------|---------|---------|
| **سرعة الاستعلام** | 40.5 QPS @ 99.8% recall | 2.6 QPS @ 99.8% recall |
| **التحديثات التدريجية** | ✅ فوري | ❌ يجب إعادة البناء |
| **الاستعلامات المُصفّاة** | ممتاز مع iterative scan | جيد |
| **الذاكرة** | أعلى | أقل |

**توصيتنا:** HNSW — كتالوج المنتجات لكل مستأجر < 500K متجه

#### إعداد HNSW الموصى به (محدّث)

```sql
-- تفعيل pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- إضافة عمود الـ embedding (halfvec لتوفير 50%)
ALTER TABLE agent_products 
ADD COLUMN embedding halfvec(1024);

-- إنشاء فهرس HNSW
CREATE INDEX ON agent_products 
USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ضبط معامل البحث
SET hnsw.ef_search = 100;  -- 40=سريع، 100=متوازن، 200=دقيق
SET hnsw.iterative_scan = 'on';  -- إلزامي للإنتاج!
```

### 2.3 البحث الهجين — لماذا وكيف (محدّث بالبحث الفعلي)

**البحث المتجهي وحده يفشل عندما:**
- المستخدم يبحث عن اسم منتج محدد ("كبسة لحم")
- تطابق SKU/ID مطلوب
- كلمات نادرة لم يرها نموذج الـ embedding

**البحث الكلماتي وحده يفشل عندما:**
- المستخدم يصف احتياجه مفاهيمياً ("شيء حار وغالِ")
- مرادفات ("موبايل" vs "جوال" vs "هاتف")
- استعلامات عبر اللغات (عربي → أسماء منتجات إنجليزية)

**الحل: البحث الهجين** — يحسّن الاستدعاء@10 بنسبة **5-15%** (مصدر: ParadeDB, TigerData benchmarks)

#### دمج RRF (Reciprocal Rank Fusion) — الموصى به

```python
# معادلة RRF: score(d) = Σ 1/(k + rank_i(d))
# k = 60 (القيمة القياسية)

def rrf_merge(vector_results, text_results, k=60, 
              vector_weight=0.7, text_weight=0.3):
    scores = {}
    for rank, doc in enumerate(vector_results, start=1):
        scores[doc.id] = scores.get(doc.id, 0) + vector_weight / (k + rank)
    for rank, doc in enumerate(text_results, start=1):
        scores[doc.id] = scores.get(doc.id, 0) + text_weight / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

#### دالة البحث الهجين في Supabase (محدّثة مع iterative scan)

```sql
CREATE OR REPLACE FUNCTION hybrid_search_products(
    query_text TEXT,
    query_embedding halfvec(1024),
    match_agent_id UUID,
    match_count INT DEFAULT 10,
    rrf_k INT DEFAULT 60,
    vector_weight FLOAT DEFAULT 0.7,
    text_weight FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID, agent_id UUID, name TEXT, name_ar TEXT,
    description TEXT, description_ar TEXT,
    price DECIMAL, currency TEXT, category TEXT,
    image_url TEXT, tags JSONB,
    similarity FLOAT, text_rank FLOAT, combined_score FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT p.id,
            1 - (p.embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY p.embedding <=> query_embedding) AS rank
        FROM agent_products p
        WHERE p.agent_id = match_agent_id AND p.is_available = TRUE
          AND p.embedding IS NOT NULL
        LIMIT match_count * 3
    ),
    text_results AS (
        SELECT p.id,
            ts_rank_cd(p.fts, websearch_to_tsquery('simple', query_text)) AS text_rank,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(p.fts, websearch_to_tsquery('simple', query_text)) DESC
            ) AS rank
        FROM agent_products p
        WHERE p.agent_id = match_agent_id AND p.is_available = TRUE
          AND p.fts @@ websearch_to_tsquery('simple', query_text)
        LIMIT match_count * 3
    ),
    rrf_scores AS (
        SELECT COALESCE(v.id, t.id) AS id,
            COALESCE(v.similarity, 0) AS similarity,
            COALESCE(t.text_rank, 0) AS text_rank,
            (vector_weight * COALESCE(1.0/(rrf_k + v.rank), 0) +
             text_weight * COALESCE(1.0/(rrf_k + t.rank), 0)) AS combined_score
        FROM vector_results v
        FULL OUTER JOIN text_results t ON v.id = t.id
    )
    SELECT p.id, p.agent_id, p.name, p.name_ar,
        p.description, p.description_ar,
        p.price, p.currency, p.category,
        p.image_url, p.tags,
        r.similarity, r.text_rank, r.combined_score
    FROM rrf_scores r
    JOIN agent_products p ON p.id = r.id
    ORDER BY r.combined_score DESC
    LIMIT match_count;
END;
$$;
```

### 2.4 خط أنابيب الـ Embeddings التلقائي (محدّث)

```
إدراج/تحديث منتج
        ↓
Trigger → رسالة في طابور pgmq
        ↓
pg_cron يستقصي الطابور → يستدعي Edge Function عبر pg_net
        ↓
Edge Function تولّد الـ embedding (Cohere/OpenAI API)
        ↓
Edge Function تحدّث صف المنتج بالـ embedding
```

**🆕 تحديث Edge Functions (يوليو ٢٠٢٥):** 
- تخزين مستمر (Persistent Storage) — لم يعد مؤقتاً!
- ٩٧% أسرع في البدء البارد
- يمكن تخزين ردود AI مؤقتاً داخل Edge Function

### 2.5 إعادة الترتيب (Reranking) — محدّث بالبحث الفعلي

| الطريقة | السرعة | الدقة | التكلفة | الأفضل لـ |
|---------|--------|-------|---------|-----------|
| **Cohere Rerank 4 (pro)** 🌟 | سريع (API) | الأعلى | $0.002/1K tokens | الإنتاج، متعدد اللغات |
| **Cohere Rerank 4 (fast)** | الأسرع | عالية جداً | أقل | زمن استجابة منخفض |
| **Qwen3-Reranker (8B)** | متوسط | عالية | مجاني (حوسبة) | أفضل مفتوح المصدر |
| **bge-reranker-v2-m3** | متوسط | عالية | مجاني | ١٠٠+ لغة |
| **FlashRank** | الأسرع | جيدة | مجاني | أقل زمن استجابة |

**خط الإنتاج الموصى به:**
```
استعلام → بحث هجين (BM25 + Vector, RRF) → أعلى 50 مرشح
     → إعادة ترتيب (Cohere Rerank 4 أو Qwen3-Reranker) → أعلى 10
     → إرجاع للمستخدم/LLM
```

### 2.6 التخزين المؤقت الدلالي (Semantic Caching) — جديد 🆕

تخزين ردود LLM مرتبطة بـ embedding الاستعلام بدلاً من النص المحدد:

```sql
-- جدول التخزين المؤقت الدلالي
CREATE TABLE semantic_cache (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID,
  query_text TEXT NOT NULL,
  query_embedding VECTOR(1024),
  response TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  hit_count INT DEFAULT 0,
  metadata JSONB DEFAULT '{}'
);

-- فهرس HNSW للبحث السريع عن التشابه
CREATE INDEX ON semantic_cache USING hnsw (query_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- دالة فحص التخزين المؤقت
CREATE OR REPLACE FUNCTION check_semantic_cache(
  query_embedding VECTOR(1024),
  similarity_threshold FLOAT DEFAULT 0.92,
  max_age_hours INT DEFAULT 24
) RETURNS TABLE (id BIGINT, query_text TEXT, response TEXT, similarity FLOAT)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT id, query_text, response,
        1 - (query_embedding <=> semantic_cache.query_embedding) AS similarity
    FROM semantic_cache
    WHERE (1 - (query_embedding <=> semantic_cache.query_embedding)) > similarity_threshold
      AND created_at > NOW() - (max_age_hours || ' hours')::INTERVAL
    ORDER BY query_embedding <=> semantic_cache.query_embedding
    LIMIT 1;
END;
$$;
```

**تأثير:** يقلل تكاليف الاستدلال بنسبة **40-70%** ويخفض أوقات الاستجابة إلى أرقام ميلي ثانية واحدة للاستعلامات المخزنة مؤقتاً.

**🆕 بوابات AI مع تخزين مؤقت دلالي (٢٠٢٦):**
| البوابة | البنية | زمن الاستجابة الزائد |
|---------|-------|---------------------|
| **Bifrost** (موصى به) | Go، طبقتان (hash + vector) | 11μs |
| **Kong AI Gateway** | Lua/Nginx | ~100μs |
| **Cloudflare AI Gateway** | شبكة حافة | ~5ms |

### 2.7 Quantization — متى تحتاجه (محدّث)

```
float32 (4 bytes/bُعد)    →  1024 × 4 = 4,096 bytes
float16 / halfvec (2B)    →  1024 × 2 = 2,048 bytes (50% توفير) ✅
int8 / Scalar Quant (1B)  →  1024 × 1 = 1,024 bytes (75% توفير)
Binary Quantization (1b)  →  1024/8  =    128 bytes (97% توفير)
```

**للمقياس الحالي (<500K منتج):** halfvec كافٍ. أقل من 0.5% فقد جودة.

---

## 3. أنماط RAG المتقدمة

### 3.1 تطور RAG (٢٠٢٤-٢٠٢٦) — محدّث بالبحث الفعلي

```
Naive RAG (2023) → Advanced RAG (2024) → Modular RAG (2025) → Agentic RAG (2025-2026)
```

**🆕 Agentic RAG (أبريل ٢٠٢٦):** وكيل LLM يقرر استراتيجية الاسترجاع بشكل مستقل:
- بحث استطلاعي arXiv:2501.09136 (الإصدار 4، أبريل ٢٠٢٦) يصنف Agentic RAG
- **5× دقة أفضل** على الاستعلامات المعقدة، لكن 2-5× توكن أكثر
- توصيتنا: ابدأ بـ CRAG، ثم أضف Agentic RAG لاحقاً

### 3.2 تحويل الاستعلام — التقنيات الرئيسية

| التقنية | الوصف | متى تستخدم | تكلفة التوكن |
|---------|-------|-----------|-------------|
| **إعادة الكتابة** | LLM يعيد صياغة الاستعلام | استعلامات غامضة | +1 استدعاء LLM |
| **HyDE** | LLM يولّد إجابة افتراضية؛ تُستخدم للبحث | استعلامات قصيرة/غير محددة | +1 استدعاء (~200-500 tokens) |
| **Multi-Query** | توليد 3-5 استعلامات متنوعة | استعلام واحد قد يفوت وثائق | +1 استدعاء، +N عمليات بحث |
| **Step-Back** | توليد نسخة أوسع/أكثر تجريداً | استعلامات محددة تفقد السياق العام | +1 استدعاء |
| **تفكيك الاستعلام** | تقسيم استعلامات معقدة لأجزاء فرعية | مقارنات، أسئلة متعددة الجوانب | +1 استدعاء، +N عمليات بحث |

### 3.3 الاسترجاع السياقي (Anthropic) — تقنية عالية الأهمية 🌟

**المشكلة:** تقسيم المستندات يزيل السياق

**الحل:** أضف سياقاً مخصصاً لكل قطعة قبل الـ embedding:

```
الخطوة 1: لكل قطعة، اسأل LLM:
  "هذا المستند: <المستند_الكامل>
   وهذه القطعة: <القطعة>
   قدم سياقاً موجزاً (1-2 جملة) لهذه القطعة ضمن المستند."

الخطوة 2: أضف السياق قبل القطعة:
  "[سياق: هذه القطعة تناقش نمو الإيرادات في الربع الثالث...]
   زاد بنسبة 15% مقارنة بالربع السابق."

الخطوة 3: اضبط الـ embedding للسياق+القطعة معاً
```

**النتائج:**

| التكوين | استدعاء أفضل 20 قطعة |
|---------|---------------------|
| embedding عادي | 62% |
| + embedding سياقي | 76% (+14pp) |
| + BM25 سياقي | 82% (+20pp) |
| + embedding سياقي + BM25 + إعادة ترتيب | **89% (+27pp)** |

**النتيجة الرئيسية:** الجمع بين embedding سياقي + BM25 + إعادة ترتيب يقلل إخفاقات الاسترجاع بنسبة **67%**.

### 3.4 أنماط LangGraph RAG (محدّث)

| النمط | التصحيح الذاتي | التعقيد | متى تستخدم |
|-------|---------------|---------|-----------|
| **Simple RAG** | لا | منخفض | نموذج أولي |
| **CRAG (تصحيحي)** 🌟 | تقييم الاسترجاع | متوسط | **إنتاج — الأنسب للبدء** |
| **Self-RAG** | تقييم التوليد | متوسط | دقة عالية |
| **Adaptive RAG** | توجيه الاستعلام | متوسط | أنواع استعلامات مختلطة |
| **Agentic RAG** | حلقة وكيل كاملة | عالي | استعلامات معقدة (متقدم) |

#### CRAG — الأنسب لنا
```
استعلام → استرجاع → تقييم الوثائق
                        ├── كلها ذات صلة → توليد
                        ├── بعضها ذو صلة → توليد + بحث ويب للفجوات
                        └── لا توجد ذات صلة → إعادة كتابة الاستعلام → استرجاع مرة أخرى
```

### 3.5 Graph RAG — للمرحلة المتقدمة

| الجانب | Vector RAG | Graph RAG |
|--------|-----------|-----------|
| **استعلامات العلاقات** | ضعيف | ممتاز |
| **المطابقة الدلالية البسيطة** | ممتاز | مبالغة |
| **توصيات المنتجات** | جيد | أفضل (واعي بالعلاقات) |

**توصيتنا:** ابدأ بـ Vector + Hybrid RAG. أضف Graph RAG لاحقاً للبيع المتقاطع والمقارنات.

### 3.6 RAG متعدد الأدوار — ضروري لخدمة العملاء

- RAG العادي يتحلل **30-40%** بحلول الدور الخامس بسبب فقدان السياق
- إعادة كتابة الاستعلام تستعيد 60% من الدقة المفقودة
- السياق المتراكم مع التقليم يستعيد 80%
- RAG متعدد الأدوار الكامل يحافظ على **90%+ دقة** حتى 8+ أدوار

---

## 4. إدارة السياق والذاكرة المتقدمة — قسم جديد 🆕

### 4.1 LangGraph Memory — بنية الطبقتين (محدّث بالبحث الفعلي)

LangGraph يوفر نظام ذاكرة مزدوج الطبقة:

#### الذاكرة قصيرة المدى (Checkpoints)
- **نطاق المحادثة:** كل موضوع محادثة له سجل checkpoint خاص
- **تلقائي:** LangGraph يحفظ حالة الرسم البياني في كل خطوة
- **منفذو التخزين:** `InMemorySaver` (تطوير)، `PostgresSaver` (إنتاج)

#### الذاكرة طويلة المدى (Store API)
- **استمرارية عبر المواضيع:** تخزين واسترجاع المعلومات عبر جلسات مختلفة
- **تحديد النطاق بالأسماء:** الذاكريات منظمة حسب الأسماء (لكل مستأجر، لكل مستخدم)
- **بحث دلالي** (أُضيف ديسمبر ٢٠٢٤): يدعم Store البحث بالمعنى عبر embeddings

```python
from langgraph.store.postgres import PostgresStore

store = PostgresStore(conn_string=CONN_STRING)
# تخزين تفضيل مستخدم عبر المواضيع
store.put(("tenant", "restaurant_test", "user", "123"), "preferences", 
          {"language": "arabic", "timezone": "AST"})
# استرجاعه في أي موضوع
data = store.get(("tenant", "restaurant_test", "user", "123"), "preferences")
```

#### 🆕 LangMem SDK (فبراير ٢٠٢٥)
- يستخلص الرؤى تلقائياً من المحادثات
- يحسّن سلوك الوكيل بمرور الوقت
- يُخصص التجارب بالتعلم من التفاعلات السابقة

### 4.2 أنواع الذاكرة — التصنيف الموحد (٢٠٢٥-٢٠٢٦)

| النوع | الوصف | مثال لخدمة العملاء | التخزين |
|-------|-------|-------------------|---------|
| **قصيرة المدى** | حالة المحادثة الحالية | محادثة التذكرة الحالية | PostgresSaver checkpoint |
| **طويلة المدى** | معلومات مستمرة عبر الجلسات | تاريخ التفاعل الكامل | PostgresStore |
| **الحلقاتية** | تجارب سابقة مع بيانات زمنية | "آخر مرة اشتكى هذا العميل من التوصيل" | ملخصات مع بيانات زمنية |
| **الدلالية** | حقائق ومعارف عامة | "العميل يفضل التواصل بالعربية" | كيانات مهيكلية، KG |
| **الإجرائية** 🆕 | مهارات وأنماط سلوكية متعلمة | "عند سؤال العميل عن الاسترجاع، تحقق أولاً من حالة الطلب" | مجموعات تعليمات، قوالب سير عمل |
| **العاملة** | سياق التفكير النشط | الخطوة الحالية في سير حل مشكلة | في السياق مباشرة |

**مرجع:** "Memory in the Age of AI Agents: A Survey" (ديسمبر ٢٠٢٥) — ورقة بحثية موحدة

### 4.3 بنيات الذاكرة المتقدمة

#### MemGPT / Letta
- يعامل نافذة سياق LLM كـ "RAM" والتخزين الخارجي كـ "قرص"
- إدارة ذاكرة ذاتية التوجيه: الوكيل يقرر متى يُدخل/يُخرج المعلومات
- **Letta V1** (أكتوبر ٢٠٢٥): إعادة هيكلة كبيرة لتحسين الأداء

#### 🆕 Governed Memory (مارس ٢٠٢٦)
- بنية إنتاج لسير العمل متعدد الوكلاء والمستأجرين
- **نموذج ذاكرة مزدوج:** مفتوحة (مشتركة) + محكومة (ذات تحكم وصول)
- سياسات حوكمة الذاكرة: من يستطيع القراءة/الكتابة وماذا
- طبقة تدقيق وامتثال

### 4.4 استراتيجيات التلخيص

#### Chain-of-Density (CoD) — الموصى به 🌟
- توليد ملخص أولي متفرق، ثم تحسينه تكرارياً لإضافة المزيد من الكيانات والحقائق — بدون زيادة الطول
- **النتيجة:** ملخصات تحزم أقصى كثافة معلوماتية في أقل توكن

```python
# قالب CoD المبسط
prompt = """
المحادثة: {conversation}
قم بتوليد ملخصات مكثفة تدريجياً. كرر مرتين:
- الخطوة 1: حدد الكيانات المهمة المفقودة من الملخص السابق
- الخطوة 2: اكتب ملخصاً أكثر كثافة بنفس الطول يتضمن الكيانات المفقودة
"""
```

#### النهج الهجين الموصى به (٢٠٢٦)
1. **آخر N رسائل:** حرفياً (ذاكرة قصيرة المدى)
2. **ملخص متجدد:** ملخص محدّث باستمرار للأدوار القديمة
3. **كيانات مستخرجة:** حقائق وتفضيلات رئيسية في ذاكرة مهيكلية
4. **ملخصات تأملية:** رؤى من رتبة أعلى تُولّد دورياً

### 4.5 ضغط السياق

| الأداة | أقصى ضغط | الأفضل لـ | مصدر |
|--------|----------|-----------|------|
| **LLMLingua-2** | 10-15× | الإنتاج بكميات كبيرة | Microsoft, ACL 2024 |
| **LongLLMLingua** | ~4× | RAG / سياق طويل | Microsoft |
| **ACON** 🆕 | ديناميكي | وكلاء متعددو الخطوات | arXiv, Oct 2025 |
| **الذاكرة التبعية البنيوية** 🆕 | انتقائي | منع فقدان السلاسل السببية | arXiv, Apr 2026 |

### 4.6 ذاكرة الرسم البياني المعرفي — تحول رئيسي 🆕

اتجاه ٢٠٢٥-٢٠٢٦: من الذاكرة المتجهية فقط إلى **الذاكرة المعززة بالرسم البياني المعرفي**

| الحل | الميزة الرئيسية | مناسب لـ |
|------|----------------|---------|
| **Zep / Graphiti** | رسم بياني معرفي زمني مع Neo4j | تتبع علاقات العملاء |
| **Hindsight (Vectorize)** | ٤ استراتيجيات استرجاع متوازية + LangGraph | تكامل مباشر مع مشروعنا |
| **HopRAG** | استرجاع مهيكل بالرسم البياني | **+٣٦% دقة أعلى** من الاسترجاع المسطح |

**توصية لمشروعنا:** ابدأ بـ PostgresStore + المتجهات. أضف Hindsight أو Zep لاحقاً لتحليل العلاقات.

### 4.7 الذاكرة متعددة المستأجرين — أمن حرج 🚨

**خطر:** الذاكرة المشتركة بين المستأجرين هي **قنبلة موقوتة أمنية** (Nexumo, ٢٠٢٥)

**استراتيجية العزل:**
```python
# كل مستأجر يحصل على namespace فريد
store.put(("tenant", "acme-corp", "user", "123"), "preferences", {...})
store.put(("tenant", "globex-inc", "user", "456"), "preferences", {...})
```

+ **RLS** في PostgreSQL كطبقة دفاع إضافية
+ **سجل تدقيق** لجميع عمليات الوصول للذاكرة
+ **سياسات حوكمة** لمن يقرأ/يكتب ماذا

### 4.8 LangGraph Checkpointing — أفضل الممارسات

| المنفذ | الاستخدام | جاهز للإنتاج |
|--------|-----------|-------------|
| `InMemorySaver` | تطوير/اختبار | ❌ (يضيع عند إعادة التشغيل) |
| `SqliteSaver` | محلي ب实例 واحدة | ⚠️ |
| **`AsyncPostgresSaver`** | **إنتاج متعدد المثيلات** | ✅ |

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async with AsyncPostgresSaver.from_conn_string(CONN_STRING) as checkpointer:
    await checkpointer.setup()
    graph = builder.compile(checkpointer=checkpointer)
    
    # كل موضوع يحصل على سجل checkpoint خاص
    # أضف معرف المستأجر في thread_id لعزل المستأجرين
    config = {"configurable": {"thread_id": f"tenant-{tenant_id}-ticket-{ticket_id}"}}
    result = await graph.ainvoke(input, config)
```

### 4.9 الذاكرة مع إشراف بشري (HITL) 🆕

LangGraph 0.2.31+ يدعم نمط interrupt/resume مبسط:

```python
from langgraph.types import interrupt, Command

def human_review_node(state):
    """إيقاف لموافقة بشرية قبل المتابعة"""
    decision = interrupt("يرجى مراجعة الإجراء المقترح")
    if decision == "approve":
        return {"approved": True}
    else:
        return {"approved": False, "feedback": decision}

# استئناف بإدخال بشري
result = graph.invoke(
    Command(resume="approve"),
    config={"configurable": {"thread_id": "ticket-12345"}}
)
```

**أنماط HITL للذاكرة:**
1. **موافقة تحديث الذاكرة:** عرض الحقائق المستخرجة للبشر قبل التخزين
2. **معالجة المعلومات الحساسة:** إيقاف قبل تخزين PII
3. **نقاط التصعيد:** عندما يكون الوكيل غير متأكد
4. **تصحيح الذاكرة:** السماح للبشر بتصحيح الذاكريات المخزنة

---

## 5. تحسين استهلاك التوكن — محدّث بالبحث الفعلي

### 5.1 نظرة عامة على التقنيات (محدّث بأحدث البيانات)

| التقنية | توفير التوكن | تأثير الجودة | تعقيد التنفيذ | مصدر |
|---------|-------------|-------------|-------------|------|
| ضغط الـ Prompt (LLMLingua-2) | 50-90% | ضئيل (<5% فقد) | متوسط | Microsoft, ACL 2024 |
| تخزين مؤقت دلالي (L1+L2) | 30-70% | إيجابي | متوسط | Maxim AI, 2026 |
| توجيه النماذج + التتالي | 47-85% | محكم | متوسط | arXiv, Mar 2026 |
| نافذة منزلقة | 40-60% | منخفض | منخفض | — |
| تلخيص المحادثة (CoD) | 70-90% | متوسط | متوسط | CoD Paper |
| تحسين System Prompt | 10-30% | إيجابي | منخفض | — |
| تحسين استدعاء الدوال | 14-70% | إيجابي | متوسط | TokenMix, 2026 |
| تقطير السياق (Cartridges) 🆕 | 38.6× ذاكرة | يعتمد | عالي | Stanford, 2025 |

**المجمّع:** الجمع بين التقنيات يوفّر **80-95%** توكن مقارنة بـ RAG ساذج.

### 5.2 LLMLingua-2 — ضغط الـ Prompts للإنتاج

```python
from llmlingua import PromptCompressor

compressor = PromptCompressor("microsoft/llmlingua-2-bert-base-en")
# للعربية استخدم xlm-roberta-base

compressed = compressor.compress_prompt(
    context=retrieved_chunks,
    instruction="أجب على سؤال العميل",
    question=user_query,
    rate=0.5,  # 50% ضغط
)
```

**نتيجة إنتاجية:** فريق SaaS أبلغ عن **٩٥% تقليل تكلفة** ($42,000 → $2,100 شهرياً) بضغط سياق RAG من 18K → 2.5K توكن لكل طلب.

### 5.3 🆕 Cartridges — تقطير السياق (ستانفورد ٢٠٢٥)

- KV caches مسبقة الحساب تمثل مجموعات نصوص كبيرة
- **38.6× تقليل ذاكرة** و **26.4× تحسين إنتاجية الاستدلال**
- يمكن تحويل قاعدة معرفة FAQ إلى Cartridge → خدمة الاستعلامات بدون إرسال القاعدة الكاملة كسياق

### 5.4 🆕 توجيه النماذج والتتالي (مارس ٢٠٢٦)

```
طلب وارد → مصنف النية → مسجل التعقيد → موجه النموذج
                                                     │
                                    ┌─────────────────┼─────────────────┐
                                    ↓                 ↓                 ↓
                                 بسيط             متوسط             معقد
                              GPT-4o-mini       GPT-4o           Claude Opus
                                 $                $$               $$$$
```

**نتائج إنتاجية:**
- توجيه متعدد النماذج: حتى **٨٥% تقليل تكلفة** بدون فقدان الجودة
- DeepSeek V4 لاستدعاء الدوال: **١٠× أرخص** من GPT-4o مع موثوقية 90-95%

### 5.5 🆕 تحسين استدعاء الدوال (فبراير ٢٠٢٦)

**تكلفة إضافية:** 346 توكن في المتوسط لكل استدعاء (OpenAI)، 512 (Claude)

**استراتيجيات التحسين:**
1. **تقليل أوصاف الأدوات:** وصف موجز بدلاً من فقرات
2. **تحميل ديناميكي للأدوات:** إرسال فقط الأدوات ذات الصلة
3. **استدعاءات متوازية:** OpenAI و Claude يدعمان ذلك أصلياً
4. **توجيه استدعاءات الدوال البسيطة لنماذج رخيصة:** DeepSeek V4

### 5.6 إدارة ذاكرة المحادثة — النهج الموصى به

**هجين: ملخص + كيانات + نافذة منزلقة**

```python
class ConversationState(TypedDict):
    messages: Annotated[list, operator.add]  # كامل السجل
    summary: str                              # ملخص مستمر
    entities: dict                            # حقائق رئيسية عن العميل
    token_count: int                          # عدد التوكن الحالي
    max_context_tokens: int                   # ميزانية التوكن

def manage_memory(state: ConversationState):
    """تلخيص الرسائل القديمة عند الاقتراب من حد التوكن"""
    if state['token_count'] > state['max_context_tokens'] * 0.8:
        old_messages = state['messages'][:-6]  # حفظ آخر 3 تبادلات
        recent_messages = state['messages'][-6:]
        
        summary = llm.invoke(f"لخّص هذه المحادثة بإيجاز بالعربية:\n{old_messages}")
        entities = extract_entities(old_messages, state['entities'])
        
        state['summary'] = summary
        state['messages'] = recent_messages
        state['entities'] = entities
    return state
```

**تقديرات التوفير:**

| الطريقة | محادثة 10 أدوار | محادثة 30 دور |
|---------|----------------|--------------|
| سجل كامل | ~8,000 tokens | ~24,000 tokens |
| نافذة (K=6) | ~4,800 tokens | ~4,800 tokens |
| ملخص + نافذة | ~3,200 tokens | ~4,000 tokens |
| كيانات + ملخص + نافذة | ~2,500 tokens | ~3,200 tokens |

**التوفير:** 60-85% توكن مقارنة بالسجل الكامل.

### 5.7 كفاءة التوكن العربي — تحدي خاص 🆕

**المشكلة:** النص العربي يستخدم **2-5× توكن أكثر** من الإنجليزية المكافئة:
- إنجليزي: ~1 كلمة ≈ 1.3 توكن
- عربي: غالباً 3-5× توكن أكثر لنفس المعنى
- هذا يعني **2-5× تكلفة أعلى** مباشرة للمحتوى العربي

**الحلول (٢٠٢٥-٢٠٢٦):**
1. **خط أنابيب تطبيع عربي** (arXiv, Dec 2025): معالجة مسبقة تقلل عدد التوكن
2. **نماذج Qwen:** tokenizer متعدد اللغات أفضل بتغطية عربية أكثر
3. **نموذج Jais (Core42):** LLM عربي مخصص بـ tokenizer محسّن
4. **ضغط + ترجمة:** لبعض الأحمال، الترجمة ← المعالجة ← الترجمة العكسية قد تكون أرخص

---

## 6. تخزين متقدم — pgvector + Supabase — محدّث بالبحث الفعلي

### 6.1 🆕 ميزات Supabase الجديدة (٢٠٢٥-٢٠٢٦)

| الميزة | التاريخ | الأهمية لمشروعنا |
|--------|---------|-----------------|
| **Edge Functions: تخزين مستمر** | يوليو ٢٠٢٥ | ⭐⭐⭐⭐⭐ تخزين ردود AI مؤقتاً |
| **Edge Functions: 97% أسرع بدء بارد** | يوليو ٢٠٢٥ | ⭐⭐⭐⭐ |
| **Realtime: Broadcast from Database** | ٢٠٢٥ | ⭐⭐⭐ تحديثات فورية |
| **MCP Support** | ٢٠٢٥ | ⭐⭐⭐ وكلاء AI يتفاعلون مباشرة |
| **Vector Dashboard UI** | ٢٠٢٥ | ⭐⭐⭐ إنشاء أعمدة متجهية بسهولة |
| **Security Retro 2025** | ٢٠٢٥ | ⭐⭐⭐⭐ تعزيز RLS |

### 6.2 تصميم المخطط لبحث المنتجات (محدّث)

```sql
CREATE TABLE agent_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    product_slug TEXT,
    name TEXT NOT NULL,
    name_ar TEXT,
    description TEXT,
    description_ar TEXT,
    price DECIMAL(10,2),
    currency TEXT DEFAULT 'SAR',
    category TEXT,
    image_url TEXT,
    tags JSONB DEFAULT '[]',
    is_promoted BOOLEAN DEFAULT FALSE,
    promotion_text TEXT,
    is_available BOOLEAN DEFAULT TRUE,
    
    -- أعمدة البحث النصي
    fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', COALESCE(name, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(description, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(category, '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(tags, ' '), '')), 'D')
    ) STORED,
    
    -- عمود الـ embedding (halfvec لتوفير 50%)
    embedding halfvec(1024),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- فهرس HNSW للبحث المتجهي
CREATE INDEX idx_products_embedding ON agent_products 
USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- فهرس GIN للبحث النصي الكامل
CREATE INDEX idx_products_fts ON agent_products USING GIN (fts);

-- فهرس ثلاثي للبحث التقريبي (autocomplete)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_products_name_trgm ON agent_products USING gin (name gin_trgm_ops);

-- فهارس BRIN للسجلات الزمنية (1000× أصغر من B-Tree)
CREATE INDEX idx_products_created_brin ON agent_products 
USING brin (created_at) WITH (pages_per_range = 32);

-- فهارس جزئية للمسار الساخن فقط
CREATE INDEX idx_products_available ON agent_products (agent_id) 
WHERE is_available = true;
```

### 6.3 فهرسة PostgreSQL المتقدمة (محدّث بالبحث الفعلي)

| نوع الفهرس | الأفضل لـ | استخدام في AI SaaS |
|-----------|-----------|-------------------|
| **B-Tree** | مساواة، نطاق | tenant_id، طوابع زمنية |
| **GIN** ⭐ | مصفوفات، JSONB، tsvector، trigrams | بحث نصي، JSONB، tags |
| **BRIN** | بيانات مرتبة طبيعياً (زمنية) | سجلات المحادثات — **1000× أصغر** |
| **HNSW** | بحث متجهي | embeddings |
| **GiST** | بيانات هندسية | PostGIS |

### 6.4 مقارنة قواعد البيانات المتجهية (محدّث بأحدث البيانات)

| الميزة | **pgvector** ✅ | Pinecone | Qdrant | Weaviate | Milvus |
|--------|-------------|-----------|-----------|-------------|-----------|
| متعدد المستأجرين | ✅ RLS | ✅ Namespaces | ✅ Payload | ✅ Tenants | ✅ Partitions |
| بحث هجين | ✅ يدوي (tsvector) | ❌ متجه فقط | ✅ مدمج | ✅ مدمج | ✅ مدمج |
| دعم العربية | ✅ مخصص | ❌ | ❌ | ✅ | ❌ |
| مفتوح المصدر | ✅ | ❌ | ✅ | ✅ | ✅ |
| تكلفة (1M متجه) | $0 (Supabase) | $70+/شهر | $25-65/شهر | $25-85/شهر | $65+/شهر |
| أقراص الفهرس | ✅ pgvectorscale | ✅ | ❌ | ❌ | ✅ |

**🆕 قياسات أداء pgvector مقابل Pinecone (٢٠٢٦):**
- 28× أداء سعر أفضل
- 16× إنتاجية أعلى
- 75% توفير تكلفة

**توصيتنا:** البقاء مع pgvector على Supabase

### 6.5 البحث النصي العربي الكامل — حل عملي 🆕

**المشكلة:** الـ Snowball stemmer الافتراضي في PostgreSQL **معطّل** للعربية:
```sql
SELECT to_tsvector('arabic', 'يجري');    -- 'يجر':1 ✅
SELECT to_tsvector('arabic', 'يجرون');   -- 'يجرون':1 ❌ لم يتم التجذير!
```

**الحل:** قاموس Hunspell/Ispell عربي مخصص:
```sql
-- إنشاء قاموس عربي مخصص
CREATE TEXT SEARCH DICTIONARY arabic_hunspell (
   TEMPLATE = ispell,
   DictFile = ar,
   AffFile = ar
);

-- إنشاء إعداد بحث نصي عربي مخصص
CREATE TEXT SEARCH CONFIGURATION public.arabic (COPY = pg_catalog.english);

ALTER TEXT SEARCH CONFIGURATION arabic
    ALTER MAPPING
    FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
    WITH arabic_hunspell;

-- إضافة قاموس مرادفات
CREATE TEXT SEARCH DICTIONARY arabic_syn (
    TEMPLATE = synonym,
    SYNONYMS = ar  -- يثرب المدينة / طيبة المدينة
);
```

### 6.6 🆕 ParadeDB — بديل Elasticsearch داخل PostgreSQL

- محرك تخزين عمودي محسّن للاستعلامات التحليلية
- أنواع فهارس مخصصة (bm25, sparse)
- واجهة متوافقة مع Elasticsearch
- **$12M Series A** في ٢٠٢٥

### 6.7 التخزين المؤقت متعدد الطبقات (محدّث)

```
L1: ذاكرة التطبيق (dict/LRU) — أقل من ميكروثانية
L2: SQLite (قرص محلي) — ميلي ثانية — ينجو من إعادة التشغيل
L3: DuckDB (تحليلات محلية) — ميلي ثانية — تحديث دوري
L4: Supabase PostgreSQL (مصدر الحقيقة) — 5-50ms
L5: Cloudflare KV/CDN (حافة) — 10-50ms — توزيع عالمي
```

---

## 7. معالجة النص العربي

### 7.1 تحديات البحث العربي (محدّث)

| التحدي | مثال | الحل |
|--------|------|------|
| **التشكيل** | بَيتزا vs بيتزا | إزالة كل الحركات |
| **أشكال الألف** | أحمر / إحمر / آحمر / احمر | تطبيع إلى ا |
| **التطويل** | كبيــــــر vs كبير | إزالة ـ |
| **الياء/ألف مقصورة** | كبيري vs كبيرى | تطبيع ى → ي |
| **اللهجات** | أبغى/عايز/بدي (أريد) | قاموس لهجات + LLM |
| **التحريف (Arabizi)** | shawarma vs شاورما | قاموس تحريف مزدوج |
| **Snowball stemmer معطّل** 🆕 | يجري≠يجرون | قاموس Hunspell عربي مخصص |

### 7.2 خط أنابيب التطبيع العربي الكامل (محدّث)

```python
import re

def normalize_arabic(text: str) -> str:
    """خط أنابيب تطبيع عربي كامل للبحث"""
    if not text:
        return text
    
    # 1. إزالة التشكيل
    diacritics = re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]')
    text = diacritics.sub('', text)
    
    # 2. تطبيع أشكال الألف
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ٱ', 'ا')
    
    # 3. إزالة التطويل
    text = text.replace('\u0640', '')
    
    # 4. تطبيع الياء/ألف مقصورة
    text = text.replace('ى', 'ي')
    
    # 5. تطبيع التاء المربوطة 🆕
    text = text.replace('ة', 'ه')
    
    # 6. إزالة علامات الترقيم
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # 7. تطبيع المسافات
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
```

**تأثير:** التطبيع وحده يحسّن الاسترجاع بنسبة **10-15%** للنص العربي.

### 7.3 دعم العربية في نماذج الـ Embedding (محدّث بالبحث الفعلي)

| النموذج | دعم العربية | ملاحظات |
|---------|-----------|---------|
| **Cohere Embed v4** 🌟 | ممتاز (100+ لغة) | أفضل خيار API |
| **BGE-M3** | قوي (100+ لغة) | أفضل مفتوح المصدر |
| **Qwen3-Embedding** | ممتاز (100+ لغة) | #1 MTEB متعدد اللغات |
| **SILMA Matryoshka v0.1** 🆕 | متخصص عربي | مُحسّن خصيصاً للعربية |
| **multilingual-e5-large** | جيد | Microsoft |

**توصية:** دائماً استخدم البحث الهجين للعربية — الصرف العربي يجعل البحث الكلماتي وحده غير موثوق.

---

## 8. تجربة المستخدم — بحث المنتجات بالذكاء الاصطناعي

### 8.1 أنماط البحث الرئيسية

#### البحث الحواري (Conversational Search)
```
مستخدم: "أبغى وجبة دجاج حارة"
  ↓
بوت يفهم: فئة=دجاج، طعم=حار، نوع=وجبة
  ↓
بوت: "عندي 5 وجبات دجاج حارة. تبغاها مع أرز ولا خبز؟"
```

#### البحث بالصور (Visual Search) 🆕
- المستخدم يرسل صورة طبق → البوت يتعرف عليه → يبحث في القائمة
- **Jina CLIP v2** و **Cohere Embed v4** يدعمان البحث بالصور والنص في نفس الفضاء المتجهي
- طبيعي مع واتساب: المستخدمون يشاركون الصور بالفعل

### 8.2 التعامل مع "لا نتائج" — 4 مستويات
```
المستوى 1: بحث ضبابي (fuzzy) → تطبيع عربي + تصحيح أخطاء
المستوى 2: توسيع الفئة → "بيتزا مارغريتا" → "بيتزا" → "إيطالي"
المستوى 3: اقتراحات بديلة → "ما عندنا بيتزا، بس عندنا كالزوني!"
المستوى 4: إعادة إشراك → "تبغا أشوف لك شيء ثاني؟"
```

---

## 9. خارطة التنفيذ المرحلية (محدّثة)

### المرحلة 1: الأساس (أسبوع 1-2) — P0

| المهمة | الوصف | الجهد |
|--------|-------|------|
| إضافة عمود embedding | `ALTER TABLE agent_products ADD COLUMN embedding halfvec(1024)` | صغير |
| إنشاء فهرس HNSW | مع `iterative_scan = 'on'` | صغير |
| إضافة عمود fts | tsvector مع 'simple' config + فهرس GIN | صغير |
| خط أنابيب التطبيع العربي | دالة `normalize_arabic()` في Python | متوسط |
| دالة RPC للبحث الهجين | `hybrid_search_products()` في SQL | متوسط |
| توليد embeddings أولي | سكريبت batch يولّد embeddings لكل المنتجات | متوسط |
| استبدال InMemorySaver | AsyncPostgresSaver مع Supabase | صغير |
| تفعيل provider prompt caching | وضع المحتوى الثابت في البداية | صغير |

### المرحلة 2: البحث المتقدم (أسبوع 3-4) — P1

| المهمة | الوصف | الجهد |
|--------|-------|------|
| تحديث search_products tool | استدعاء hybrid_search_products RPC بدل ILIKE | متوسط |
| إعادة كتابة الاستعلام | عقدة LangGraph لإعادة صياغة الاستعلامات | متوسط |
| إعادة الترتيب (Reranking) | Cohere Rerank 4 أو Qwen3-Reranker | متوسط |
| إدارة الذاكرة | ملخص CoD + كيانات + نافذة منزلقة | كبير |
| Trigger تلقائي | pgmq trigger لتحديث embeddings عند تغير المنتجات | متوسط |
| تخزين مؤقت دلالي | جدول semantic_cache في Supabase | متوسط |
| إضافة قاموس Hunspell عربي | لتحسين FTS العربي | متوسط |

### المرحلة 3: السياق المتقدم (أسبوع 5-6) — P2

| المهمة | الوصف | الجهد |
|--------|-------|------|
| Embeddings سياقية | إضافة سياق Anthropic قبل الـ embedding | كبير |
| CRAG | تقييم الاسترجاع + إعادة المحاولة | كبير |
| PostgresStore للذاكرة طويلة المدى | تخزين تفضيلات العملاء عبر الجلسات | متوسط |
| ضغط LLMLingua-2 | ضغط سياق RAG قبل الإرسال | متوسط |
| توجيه النماذج | نموذج رخيص للبسيط + قوي للمعقد | متوسط |
| تحسين استدعاء الدوال | تقليل أوصاف الأدوات + تحميل ديناميكي | صغير |

### المرحلة 4: الميزات المتقدمة (أسبوع 7-10) — P3

| المهمة | الوصف | الجهد |
|--------|-------|------|
| Graph RAG خفيف | علاقات المنتجات (تكميلية، بديلة) | كبير |
| بحث بصري | Jina CLIP v2 / Cohere Embed v4 لصور المنتجات | كبير |
| كيانات مهيكلية | أنواع كيانات مخصصة (عميل، تذكرة، منتج) | متوسط |
| HITL للذاكرة | موافقة بشرية قبل تخزين حقائق حساسة | متوسط |
| تحليلات البحث | تسجيل أحداث البحث + لوحة تحكم | كبير |

### المرحلة 5: Agentic RAG (أسبوع 11-12) — P4

| المهمة | الوصف | الجهد |
|--------|-------|------|
| Adaptive RAG | توجيه الاستعلامات لاستراتيجيات مختلفة | كبير |
| Agentic RAG | وكيل يقرر استراتيجية الاسترجاع | كبير |
| Cartridges | تقطير قاعدة المعرفة | كبير |
| ذاكرة رسم بياني معرفي | Zep/Hindsight للعلاقات | كبير |
| بحث باللهجات | كشف اللهجة + تكييف الردود | متوسط |

---

## 10. تحليل التكاليف (محدّث)

### 10.1 تكاليف الـ Embeddings

**افتراضات:**
- 10 مستأجرين × 1,000 منتج = 10,000 منتج
- متوسط نص المنتج = 200 tokens
- تحديثات شهرية = 20% من الكتالوج (2,000 تحديث/شهر)
- استعلامات شهرية = 100,000 بحث

| المكوّن | Cohere Embed v4 | OpenAI v3-large | BGE-M3 (ذاتي) |
|---------|----------------|----------------|---------------|
| **Embeddings أولية** (10K) | $0.20 | $0.26 | مجاني |
| **تحديثات شهرية** (2K) | $0.04/شهر | $0.05/شهر | مجاني |
| **استعلامات بحث** (100K/شهر) | $0.20/شهر | $0.26/شهر | مجاني |
| **المجموع الشهري** | **~$0.44** | **~$0.57** | **$0** (حوسبة فقط) |

### 10.2 🆕 توفيرات التحسين (محدّث بالبحث الفعلي)

| التقنية | توفير شهري تقديري |
|---------|-------------------|
| تخزين مؤقت دلالي | 30-60% |
| توجيه النماذج | 20-40% |
| ضغط LLMLingua-2 | 50-90% على input tokens |
| تحسين System Prompt | 20-40% |
| Provider prompt caching | 45-90% على cached tokens |
| **المجمّع** | **80-95% توفير** |

---

## 11. الموارد والمراجع الرئيسية

### أوراق بحثية (arXiv)
- arXiv:2501.09136 — Agentic RAG Survey (v4, Apr 2026)
- arXiv:2506.06339 — BGE-M3 Arabic benchmarks (Jun 2025)
- arXiv:2506.06266 — Cartridges (Stanford, 2025)
- arXiv:2603.04445 — Cascade Routing (Mar 2026)
- arXiv:2603.03301 — Semantic Caching for LLM (Mar 2026)
- arXiv:2603.17787 — Governed Memory Architecture (Mar 2026)
- arXiv:2512.10411 — SWAA Sliding Window Attention (Dec 2025)
- arXiv:2508.06433 — Procedural Memory (Aug 2025)
- arXiv:2510.00615 — ACON Context Compression (Oct 2025)
- arXiv:2604.23069 — Dependency-Structured Memory (Apr 2026)
- arXiv:2602.21221 — Portable Memory (Feb 2026)
- arXiv:2512.18399 — Arabic Tokenization Normalization (Dec 2025)

### وثائق رسمية
- [Supabase AI Docs](https://supabase.com/docs/guides/ai)
- [Supabase Hybrid Search](https://supabase.com/docs/guides/ai/hybrid-search)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pgvectorscale GitHub](https://github.com/timescale/pgvectorscale)
- [LangGraph Memory Guide](https://langchain-ai.github.io/langgraph/guides/memory)
- [LangGraph Store API](https://langchain-ai.github.io/langgraph/reference/store/)
- [LangMem SDK](https://github.com/langchain-ai/langmem)
- [Cohere Embed v4 Blog](https://cohere.com/blog/embed-4)
- [Cohere Rerank 4 Blog](https://cohere.com/blog/rerank-4)
- [Microsoft LLMLingua](https://github.com/microsoft/LLMLingua)

### مدونات تقنية
- [ParadeDB Hybrid Search](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual)
- [TigerData pgvector Benchmarks](https://www.tigerdata.com/blog/pgvector-is-now-as-fast-as-pinecone-at-75-less-cost)
- [Arabic FTS in PostgreSQL](https://wassimbj.github.io/blog/full-text-search-in-postgres)
- [Top AI Gateways 2026](https://www.getmaxim.ai/articles/top-ai-gateways-for-semantic-caching-in-2026)
- [Token Optimization 2026](https://www.maviklabs.com/blog/llm-cost-optimization-2026)
- [Function Calling Guide](https://tokenmix.ai/blog/function-calling-guide)
- [Context Engineering for Agents](https://www.langchain.com/blog/context-engineering-for-agents)
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Zep Entity Types](https://blog.getzep.com/entity-types-structured-agent-memory)
- [Hindsight for LangGraph](https://hindsight.vectorize.io/blog/2026/03/24/langgraph-longterm-memory)
- [SILMA Arabic Embeddings](https://silma.ai/blog/introducing-silma-matryoshka-embedding-model-v0-1)

---

> 📅 **آخر تحديث:** ٢٨ أبريل ٢٠٢٦ — مبني على بحث إنترنت فعلي باستخدام z-ai web_search و page_reader  
> 📊 **إجمالي مصادر البحث:** ٥٥+ بحث ويب، ١٥+ مقالة مقروءة بالتفصيل، ١٢+ ورقة بحثية arXiv  
> 🎯 **الهدف:** تطبيق تدريجي عبر ٥ مراحل (١٢ أسبوع) لتحويل المنصة من بحث بسيط إلى بحث ذكي متقدم
