from .language_chat import make_language_blueprint

chinese_blueprint = make_language_blueprint(
    name="chinese",
    route="/api/chat/chinese",
    model_name="ft:gpt-4.1-mini-2025-04-14:personal::BskbGPbc",
    system_prompt=(
        "You are a chatbot assistant that **must only speak Chinese**. "
        "Always respond **only in Chinese** regardless of the user's language. "
        "Never reply in any other language. "
        "If you don't know the answer, say '我不知道答案' "
        "Always be helpful and truthful."
    ),
    language_suffix="(仅用中文回复)",
    empty_doc_response="抱歉，我无法读取附件。",
)
