from .language_chat import make_language_blueprint

korean_blueprint = make_language_blueprint(
    name="korean",
    route="/api/chat/korean",
    model_name="ft:gpt-4.1-mini-2025-04-14:personal::BthVmuUX",
    system_prompt=(
        "You are a chatbot assistant that **must only speak Korean**. "
        "Always respond **only in Korean** regardless of the user's language. "
        "Never reply in any other language. "
        "If you don't know the answer, say '나는 답을 모른다.' "
        "Always be helpful and truthful."
    ),
    language_suffix="(한국어로만 답변해주세요)",
    empty_doc_response="죄송합니다. 첨부된 문서를 읽을 수 없습니다.",
)
