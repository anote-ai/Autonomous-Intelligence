from .language_chat import make_language_blueprint

japanese_blueprint = make_language_blueprint(
    name="japanese",
    route="/api/chat/japanese",
    model_name="ft:gpt-4.1-mini-2025-04-14:personal::Bt2nGdcd",
    system_prompt=(
        "You are a chatbot assistant that **must only speak Japanese**. "
        "Always respond **only in Japanese** regardless of the user's language. "
        "Never reply in any other language. "
        "If you don't know the answer, say '答えは分かりません。' "
        "Always be helpful and truthful."
    ),
    language_suffix="(日本語のみで応答します)",
    empty_doc_response="申し訳ありませんが、添付文書を読むことができません。",
)
