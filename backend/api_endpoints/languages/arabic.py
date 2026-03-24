from .language_chat import make_language_blueprint

arabic_blueprint = make_language_blueprint(
    name="arabic",
    route="/api/chat/arabic",
    model_name="ft:gpt-4.1-mini-2025-04-14:personal::BtL5Rskw",
    system_prompt=(
        "You are a chatbot assistant that **must only speak Arabic**. "
        "Always respond **only in Arabic** regardless of the user's language. "
        "Never reply in any other language. "
        "If you don't know the answer, say 'لا أعرف الجواب.' "
        "Always be helpful and truthful."
    ),
    language_suffix="(الرد باللغة العربية فقط)",
    empty_doc_response="عذراً، لا أستطيع قراءة الوثيقة المرفقة.",
)
