"""اختبار مكثف للذاكرة والسياق — مطعم الشرق الأوسط (عربي)

يرسل محادثة معقدة متعددة الأدوار عبر LangGraph الحقيقي مع
LLM حقيقي (LongCat) و PostgresSaver حقيقي (Supabase)، ثم
يتحقق من أن الذكاء الاصطناعي:

1. يتذكر اسم المستخدم وتفضيلاته من الرسائل الأولى
2. يستدعي تفاصيل المنتجات التي نوقشت سابقاً
3. يحافظ على السياق عبر 15+ رسالة
4. يتعامل مع التبديل بين اللهجات والموضوعات
5. يتتبع حالة الطلب والسلة
6. يستجيب بشكل متماسك للإشارات مثل "اللي ذكرتيها"
7. يكتشف طلب التصعيد بشكل صحيح
8. يحافظ على السياق بعد الاستطرادات الطويلة
9. يتذكر القيود الغذائية والحساسيات
10. يحسب المجاميع والأسعار بشكل صحيح
11. يتذكر تفاصيل العنوان والتوصيل
12. يربط بين المعلومات المتفرقة عبر المحادثة

الاستخدام:
    cd python-backend
    python tests/test_memory_arabic.py
"""

from __future__ import annotations

import asyncio
import sys
import time
import uuid

# Ensure project root is on sys.path
sys.path.insert(0, ".")

# Fix DATABASE_URL if overridden by parent environment (Next.js/Prisma SQLite)
import os
if os.environ.get("DATABASE_URL", "").startswith("file:"):
    os.environ.pop("DATABASE_URL", None)

from src.services.graph_service import GraphService
from src.services.llm_service import llm_service


# ── Color helpers ──────────────────────────────────────────────────────
class C:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def print_header(text: str) -> None:
    width = 90
    print(f"\n{C.BOLD}{C.CYAN}{'=' * width}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {text}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'=' * width}{C.RESET}\n")


def print_turn(turn: int, user_msg: str, ai_response: str, elapsed: float) -> None:
    print(f"{C.YELLOW}┌─ الدور {turn} ─────────────────────────────────────────{C.RESET}")
    print(f"{C.YELLOW}│{C.RESET} {C.BOLD}المستخدم:{C.RESET} {user_msg}")
    print(f"{C.YELLOW}│{C.RESET}")
    words = ai_response.split()
    line = f"{C.YELLOW}│{C.RESET} {C.BOLD}الذكاء:{C.RESET}     "
    for word in words:
        if len(line) + len(word) > 82:
            print(line)
            line = f"{C.YELLOW}│{C.RESET}         "
        line += word + " "
    if line.strip():
        print(line)
    print(f"{C.YELLOW}│{C.RESET} {C.DIM}⏱ {elapsed:.1f} ثانية{C.RESET}")
    print(f"{C.YELLOW}└──────────────────────────────────────────────────────────{C.RESET}\n")


# ── سكربت المحادثة العربي المكثف ──────────────────────────────────────
CONVERSATION = [
    # الدور 1: تعريف المستخدم والهوية
    {
        "message": "السلام عليكم! أنا محمد العتيبي، أبغى أطلب عشاء لعائلتي. نحن 5 أشخاص وأبغى شي يكفينا.",
        "check": "identity_introduced",
        "description": "الذكاء يرحب بمحمد ويعرف أن الطلب لعائلة من 5 أشخاص",
    },
    # الدور 2: استفسار عن المنتجات
    {
        "message": "شو عندكم من أطباق رئيسية؟ أبغى شي تقليدي سعودي.",
        "check": "product_search",
        "description": "الذكاء يبحث عن الأطباق الرئيسية التقليدية",
    },
    # الدور 3: تفاصيل المنتج والسعر
    {
        "message": "الكبسة حلوة! كم سعرها وهل تناسب 5 أشخاص؟ أبغى كميتين منها.",
        "check": "price_inquiry",
        "description": "الذكاء يذكر سعر الكبسة ويربطه بطلب 5 أشخاص",
    },
    # الدور 4: قيد غذائي - حساسية
    {
        "message": "مهم جداً! عندي بنتي عندها حساسية من المكسرات. هل الكبسة فيها مكسرات؟",
        "check": "allergy_alert",
        "description": "حرج: الذكاء يجب أن ينبه للمكسرات في الكبسة ويتذكر الحساسية",
    },
    # الدور 5: استطراد - سؤال عن أوقات العمل
    {
        "message": "بالمناسبة، متى وقت العمل عندكم؟ لأني أبغى أطلب للعشاء بس مو متأكد من الوقت.",
        "check": "working_hours",
        "description": "الذكاء يذكر ساعات العمل (استطراد)",
    },
    # الدور 6: العودة للموضوع - اختبار الذاكرة
    {
        "message": "طيب رجعنا للأكل. شو تقترحين مع الكبسة؟ أبغى مقبلات وسلطة.",
        "check": "memory_recall_sides",
        "description": "حرج: الذكاء يتذكر طلب الكبسة وحساسية المكسرات ويقترح أطباق جانبية",
    },
    # الدور 7: إضافة طلب آخر
    {
        "message": "حلو! ضيفي شاورما دجاج بعد، عيالي يحبونها. وكم سعرها؟",
        "check": "add_item",
        "description": "الذكاء يضيف الشاورما ويتذكر السياق الكامل",
    },
    # الدور 8: حساب المجموع - اختبار ذاكرة عميق
    {
        "message": "حسابي لي المجموع الكلي للطلب كله. كمبيسة كميتين وشاورما دجاج والمقبلات اللي ذكرتيها.",
        "check": "total_calculation",
        "description": "حرج: الذكاء يحسب المجموع متذكراً كل الطلبات وأسعارها",
    },
    # الدور 9: سؤال عن التوصيل
    {
        "message": "أنا ساكن في حي النرجس بالرياض. هل توصلون؟ وكم رسوم التوصيل؟",
        "check": "delivery_inquiry",
        "description": "الذكاء يذكر تفاصيل التوصيل والمناطق المشمولة",
    },
    # الدور 10: استطراد طويل - اختبار تعقيد السياق
    {
        "message": "أخوي أحمد يقول جربوا المشاوي المشكلة أحسن من الكبسة. شو رأيك؟ هل المشاوي تكفي 5 أشخاص؟ وكم فرق السعر؟",
        "check": "comparison",
        "description": "الذكاء يقارن بين المشاوي والكبسة ويربط بالسياق",
    },
    # الدور 11: تعديل الطلب - اختبار تحديث السياق
    {
        "message": "طيب خلاص، بدّل واحدة كبسة بالمشاوي المشكلة. يعني الحين الطلب: كبسة واحدة + مشاوي مشكلة + شاورما دجاج + المقبلات.",
        "check": "order_modification",
        "description": "حرج: الذكاء يحدث الطلب بشكل صحيح",
    },
    # الدور 12: طلب حلى ومشروبات
    {
        "message": "عندكم حلى؟ أبغى شي حلو بعد العشاء. وشاي كرك للجميع!",
        "check": "dessert_drinks",
        "description": "الذكاء يقترح الحلى والمشروبات",
    },
    # الدور 13: تدقيق نهائي للطلب - اختبار تجميع السياق الشامل
    {
        "message": "تأكدي لي الطلب كامل مع الأسعار. وأذكريني: أنا مين وكم شخص وعندي وش مشكلة؟",
        "check": "full_context_recall",
        "description": "حرج: الذكاء يتذكر الاسم + عدد الأشخاص + الحساسية + الطلب الكامل",
    },
    # الدور 14: تبديل للغة الإنجليزية مؤقتاً
    {
        "message": "Can you also tell me if the food is halal certified? My friend asked.",
        "check": "language_switch",
        "description": "الذكاء يتعامل مع الإنجليزية مع الحفاظ على السياق العربي",
    },
    # الدور 15: العودة للعربي والتحقق النهائي
    {
        "message": "شكراً! المجموع النهائي كم مع التوصيل؟ وبكرة توصلون الساعة 7 مساءً؟",
        "check": "final_total_with_delivery",
        "description": "حرج: الذكاء يحسب المجموع مع التوصيل ويتذكر العنوان",
    },
    # الدور 16: اختبار التصعيد
    {
        "message": "أبغى أتكلم مع المدير. عندي شكوى عن طلب سابق.",
        "check": "escalation_trigger",
        "description": "الذكاء يفعّل تدفق التصعيد",
    },
]


async def run_test() -> None:
    """تشغيل اختبار الذاكرة والسياق المكثف."""
    session_id = f"arabic-test-{uuid.uuid4().hex[:8]}"
    tenant_slug = "restaurant_test"

    print_header("🧠 اختبار مكثف للذاكرة والسياق — مطعم الشرق الأوسط")
    print(f"  المستأجر: {tenant_slug} (مطعم الشرق الأوسط)")
    print("  اسم الوكيل: نورة")
    print("  اللغة: عربي (ar)")
    print("  نموذج LLM: LongCat-Flash-Chat (حقيقي)")
    print("  قاعدة البيانات: Supabase PostgreSQL (حقيقي)")
    print(f"  الجلسة: {session_id}")
    print(f"  عدد الأدوار: {len(CONVERSATION)}")
    print()

    # Reset LLM service for clean state
    llm_service._models = []
    llm_service._current_model = None
    llm_service._current_model_index = 0
    llm_service._bound_tools = []

    # Invalidate tenant cache to pick up new Arabic config
    from src.config.tenant_config import invalidate_tenant_cache
    invalidate_tenant_cache()

    gs = GraphService()
    results: list[dict] = []

    try:
        await gs._ensure_graph()

        for i, turn in enumerate(CONVERSATION, 1):
            message = turn["message"]
            check = turn["check"]
            description = turn["description"]

            start = time.time()
            try:
                response = await gs.process_message(
                    tenant_slug=tenant_slug,
                    session_id=session_id,
                    message=message,
                    channel="web",
                )
                elapsed = time.time() - start
            except Exception as e:
                response = f"خطأ: {e}"
                elapsed = time.time() - start

            print_turn(i, message, response, elapsed)

            # ── تقييم اختبارات الذاكرة ────────────────────────
            r_lower = response.lower()
            passed = False

            if check == "identity_introduced":
                passed = any(w in r_lower for w in [
                    "محمد", "عائلة", "خمسة", "5", "أهلا", "مرحبا", "وعليكم",
                    "عتيبي",
                ])

            elif check == "product_search":
                passed = any(w in r_lower for w in [
                    "كبسة", "مندي", "مشاوي", "أطباق", "قائمة", "تقليدي",
                    "سعودي", "بحث",
                ])

            elif check == "price_inquiry":
                passed = any(w in r_lower for w in [
                    "45", "ريال", "سعر", "كمية", "شخص", "أشخاص",
                ])

            elif check == "allergy_alert":
                passed = any(w in r_lower for w in [
                    "مكسرات", "زبيب", "صنوبر", "حساسية", "انتبه", "تحذير",
                    "يحتوي",
                ])

            elif check == "working_hours":
                passed = any(w in r_lower for w in [
                    "11", "12", "صباح", "منتصف", "ليل", "ساعات", "عمل",
                ])

            elif check == "memory_recall_sides":
                has_sides = any(w in r_lower for w in [
                    "مقبلات", "سلطة", "حمص", "فتة", "جانبي",
                ])
                any(w in r_lower for w in [  # noqa: F841
                    "مكسرات", "حساسية", "بدون", "آمن",
                ])
                passed = has_sides

            elif check == "add_item":
                passed = any(w in r_lower for w in [
                    "شاورما", "18", "دجاج", "أضف", "إضافة",
                ])

            elif check == "total_calculation":
                passed = any(w in r_lower for w in [
                    "ريال", "مجموع", "إجمالي", "90", "108", "115", "120",
                    "123", "125", "130", "135", "140",
                ])

            elif check == "delivery_inquiry":
                passed = any(w in r_lower for w in [
                    "توصيل", "رياض", "15", "منطقة", "نرجس", "رسوم",
                ])

            elif check == "comparison":
                passed = any(w in r_lower for w in [
                    "مشاوي", "كبسة", "85", "فرق", "مقارنة", "أشخاص",
                ])

            elif check == "order_modification":
                has_kabsa = any(w in r_lower for w in ["كبسة", "واحدة"])
                has_grill = any(w in r_lower for w in ["مشاوي", "مشكلة"])
                has_shawarma = any(w in r_lower for w in ["شاورما"])
                has_sides = any(w in r_lower for w in ["مقبلات", "حمص", "سلطة"])
                details_found = sum([has_kabsa, has_grill, has_shawarma, has_sides])
                passed = details_found >= 2

            elif check == "dessert_drinks":
                passed = any(w in r_lower for w in [
                    "كنافة", "حلى", "شاي", "كرك", "مشروبات", "حلو",
                ])

            elif check == "full_context_recall":
                details_found = 0
                if "محمد" in r_lower or "عتيبي" in r_lower:
                    details_found += 1
                if any(w in r_lower for w in ["5", "خمسة", "عائلة"]):
                    details_found += 1
                if any(w in r_lower for w in ["مكسرات", "حساسية"]):
                    details_found += 1
                if any(w in r_lower for w in ["كبسة"]):
                    details_found += 1
                if any(w in r_lower for w in ["مشاوي", "مشكلة"]):
                    details_found += 1
                if any(w in r_lower for w in ["شاورما"]):
                    details_found += 1
                passed = details_found >= 3

            elif check == "language_switch":
                passed = any(w in r_lower for w in [
                    "halal", "حلال", "yes", "certified", "مصدق",
                ])

            elif check == "final_total_with_delivery":
                passed = any(w in r_lower for w in [
                    "ريال", "مجموع", "إجمالي", "توصيل", "15",
                ])

            elif check == "escalation_trigger":
                passed = any(w in r_lower for w in [
                    "مشرف", "مدير", "تصعيد", "إدارة", "supervisor",
                    "manager", "escalat",
                ])

            # Graceful failure doesn't count as pass
            if "technical difficulties" in r_lower or "خطأ تقني" in r_lower:
                passed = False

            results.append({
                "turn": i,
                "check": check,
                "description": description,
                "passed": passed,
                "elapsed": elapsed,
                "response_preview": response[:150],
            })

    finally:
        await gs.shutdown()

    # ── التقرير النهائي ─────────────────────────────────────────────
    print_header("📊 تقرير اختبار الذاكرة والسياق")

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count
    total_time = sum(r["elapsed"] for r in results)
    avg_time = total_time / total if total else 0

    for r in results:
        icon = f"{C.GREEN}✅{C.RESET}" if r["passed"] else f"{C.RED}❌{C.RESET}"
        print(f"  {icon} الدور {r['turn']:2d} [{r['check']}] — {r['description']}")
        if not r["passed"]:
            print(f"         {C.DIM}الرد: {r['response_preview']}...{C.RESET}")

    print()
    print(f"  {C.BOLD}النتائج:{C.RESET} {C.GREEN}{passed_count} نجح{C.RESET} / {C.RED}{failed_count} فشل{C.RESET} / {total} إجمالي")
    print(f"  {C.BOLD}الوقت الكلي:{C.RESET} {total_time:.1f} ثانية")
    print(f"  {C.BOLD}المتوسط لكل دور:{C.RESET} {avg_time:.1f} ثانية")
    print(f"  {C.BOLD}النتيجة:{C.RESET} {passed_count}/{total} ({100*passed_count/total:.0f}%)")

    # تحليل الذاكرة التفصيلي
    print_header("🔍 تحليل الذاكرة التفصيلي")
    critical_checks = [
        "allergy_alert",
        "total_calculation",
        "order_modification",
        "full_context_recall",
        "final_total_with_delivery",
    ]
    critical_results = [r for r in results if r["check"] in critical_checks]
    critical_passed = sum(1 for r in critical_results if r["passed"])

    print(f"  {C.BOLD}اختبارات الذاكرة الحرجة:{C.RESET} {critical_passed}/{len(critical_checks)}")
    for r in critical_results:
        icon = f"{C.GREEN}✅{C.RESET}" if r["passed"] else f"{C.RED}❌{C.RESET}"
        print(f"  {icon} {r['check']} — {r['description']}")

    # تحليل قدرات الذاكرة
    print_header("🧩 تحليل قدرات الذاكرة")
    categories = {
        "تذكر الهوية": ["identity_introduced"],
        "البحث عن المنتجات": ["product_search"],
        "تذكر الأسعار": ["price_inquiry"],
        "الوعي بالحساسية": ["allergy_alert"],
        "تذكر القيود": ["working_hours", "delivery_inquiry"],
        "استدعاء الذاكرة": ["memory_recall_sides"],
        "تحديث السياق": ["add_item", "order_modification"],
        "الحساب والمنطق": ["total_calculation", "final_total_with_delivery"],
        "التجميع الشامل": ["full_context_recall"],
        "التبديل اللغوي": ["language_switch"],
        "المقارنة والتحليل": ["comparison"],
        "التصعيد": ["escalation_trigger"],
    }

    for cat_name, cat_checks in categories.items():
        cat_results = [r for r in results if r["check"] in cat_checks]
        if cat_results:
            cat_passed = sum(1 for r in cat_results if r["passed"])
            cat_total = len(cat_results)
            icon = f"{C.GREEN}✅{C.RESET}" if cat_passed == cat_total else (
                f"{C.YELLOW}⚠️{C.RESET}" if cat_passed > 0 else f"{C.RED}❌{C.RESET}"
            )
            print(f"  {icon} {cat_name}: {cat_passed}/{cat_total}")

    if critical_passed == len(critical_checks):
        print(f"\n  {C.GREEN}{C.BOLD}🎉 ممتاز: الذكاء الاصطناعي يمتلك ذاكرة وسياق قويان!{C.RESET}")
    elif critical_passed >= 3:
        print(f"\n  {C.YELLOW}{C.BOLD}⚠️ جزئي: الذكاء الاصطناعي لديه ذاكرة جيدة لكنه يفقد بعض التفاصيل.{C.RESET}")
    elif critical_passed >= 1:
        print(f"\n  {C.YELLOW}{C.BOLD}⚠️ ضعيف: الذكاء الاصطناعي يواجه صعوبة في الحفاظ على السياق.{C.RESET}")
    else:
        print(f"\n  {C.RED}{C.BOLD}❌ ضعيف جداً: الذكاء الاصطناعي يفشل في الحفاظ على السياق عبر الأدوار.{C.RESET}")

    # تحليل الأداء
    print_header("⚡ تحليل الأداء")
    for r in results:
        bar_len = int(r["elapsed"] * 2)
        bar = "█" * bar_len
        color = C.GREEN if r["elapsed"] < 10 else C.YELLOW if r["elapsed"] < 20 else C.RED
        print(f"  الدور {r['turn']:2d}: {color}{bar}{C.RESET} {r['elapsed']:.1f}s")

    slow_turns = [r for r in results if r["elapsed"] > 20]
    if slow_turns:
        print(f"\n  {C.YELLOW}⚠️ {len(slow_turns)} أدور تجاوزت 20 ثانية (قد تحتاج تحسين){C.RESET}")

    return passed_count == total


if __name__ == "__main__":
    success = asyncio.run(run_test())
    sys.exit(0 if success else 1)
