# استخدم image فيها Python 3.12 + uv جاهزين (لا نحتاج تثبيت من الصفر)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# ثبّت libpq-dev (مطلوب لـ psycopg للاتصال بـ PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

# انسخ ملفات التبعيات أولاً (للاستفادة من Docker cache)
COPY pyproject.toml uv.lock ./

# ثبّت التبعيات باستخدام uv (أسرع من pip بـ 10-100x)
RUN uv sync --extra dev

# انسخ باقي الملفات
COPY . .

# المنفذ
EXPOSE 8000

# أمر التشغيل الافتراضي
CMD ["uv", "run", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]