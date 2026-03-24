from .language_chat import make_language_blueprint

spanish_blueprint = make_language_blueprint(
    name="spanish",
    route="/api/chat/spanish",
    model_name="ft:gpt-4.1-mini-2025-04-14:personal::BtJIlsUg",
    system_prompt=(
        "You are a chatbot assistant that **must only speak Spanish**. "
        "Always respond **only in Spanish** regardless of the user's language. "
        "Never reply in any other language. "
        "If you don't know the answer, say 'No sé la respuesta.' "
        "Always be helpful and truthful."
    ),
    language_suffix="(responde solo en espanol)",
    empty_doc_response="Lo siento, no puedo leer el documento adjunto.",
)
