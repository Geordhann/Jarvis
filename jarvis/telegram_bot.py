"""Parler à Jarvis depuis Telegram (texte et messages vocaux).

Configuration : python -m jarvis --configurer (étape Telegram). Seul ton compte
Telegram est autorisé ; les autres reçoivent au plus leur identifiant.
"""

from __future__ import annotations

import asyncio

from . import config, sessions, tts

MAX_LEN = 4000


def is_configured() -> bool:
    return bool(config.get("telegram_token"))


def _allowed(user_id: int) -> bool:
    owner = config.get("telegram_utilisateur")
    return owner is not None and str(user_id) == str(owner)


async def start() -> object:
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

    async def guard(update: Update) -> bool:
        user = update.effective_user
        if user and _allowed(user.id):
            return True
        if user and not config.get("telegram_utilisateur") and update.message:
            await update.message.reply_text(
                f"Je ne suis pas encore relié à ton compte. Ton identifiant Telegram est {user.id}.\n"
                f"Sur ton ordinateur, lance : python -m jarvis --telegram-autoriser {user.id}"
            )
        return False

    async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, as_voice: bool) -> None:
        chat_id = update.effective_chat.id
        agent = sessions.get(f"telegram:{chat_id}", "telegram")
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        try:
            answer = await asyncio.to_thread(agent.ask, text)
        except Exception as exc:
            print(f"[telegram] erreur : {exc}")
            await update.message.reply_text("Un problème est survenu de mon côté, réessayez dans un instant.")
            return
        for i in range(0, len(answer), MAX_LEN):
            await update.message.reply_text(answer[i:i + MAX_LEN])
        if as_voice and answer:
            await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
            audio = await asyncio.to_thread(tts.synthesize, answer)
            await update.message.reply_voice(voice=audio)

    async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await guard(update):
            await update.message.reply_text("À votre service. Écrivez-moi ou envoyez un message vocal.\n"
                                            "/nouveau pour repartir de zéro.")

    async def on_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await guard(update):
            sessions.reset(f"telegram:{update.effective_chat.id}")
            await update.message.reply_text("C'est oublié. On repart de zéro.")

    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await guard(update):
            await reply(update, context, update.message.text, as_voice=False)

    async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await guard(update):
            return
        if not tts.can_transcribe():
            await update.message.reply_text("Pour les vocaux, il faut une clé ElevenLabs. Écrivez-moi en attendant.")
            return
        media = update.message.voice or update.message.audio
        data = await (await media.get_file()).download_as_bytearray()
        try:
            text = await asyncio.to_thread(tts.transcribe, bytes(data), "vocal.ogg")
        except Exception as exc:
            print(f"[telegram] transcription impossible : {exc}")
            await update.message.reply_text("Je n'ai pas réussi à écouter ce vocal.")
            return
        if text:
            await update.message.reply_text(f"🎙️ « {text} »")
            await reply(update, context, text, as_voice=True)

    app = Application.builder().token(config.get("telegram_token")).build()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("nouveau", on_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("[telegram] bot connecté.")
    return app
