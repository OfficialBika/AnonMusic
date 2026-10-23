# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio

from ntgcalls import (
    ConnectionNotFound,
    TelegramServerError,
    RTMPStreamingUnsupported,
    ConnectionError,
    TransportParseException,
)
from pyrogram.errors import ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from anony import app, config, db, lang, logger, queue, thumb, userbot, yt
from anony.helpers import Media, Track, buttons


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        self._chat_locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, chat_id: int) -> asyncio.Lock:
        return self._chat_locks.setdefault(chat_id, asyncio.Lock())

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        try:
            result = await client.pause(chat_id)
            await db.playing(chat_id, paused=True)
            return result
        except (ConnectionNotFound, exceptions.NotInCallError):
            await self.stop(chat_id)
            return False

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        try:
            result = await client.resume(chat_id)
            await db.playing(chat_id, paused=False)
            return result
        except (ConnectionNotFound, exceptions.NotInCallError):
            await self.stop(chat_id)
            return False

    async def stop(self, chat_id: int) -> None:
        try:
            client = await db.get_assistant(chat_id)
        except (IndexError, ValueError, RuntimeError):
            client = None
        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)
        if client is not None:
            try:
                await client.leave_call(chat_id, close=False)
            except Exception as exc:
                logger.debug("Voice call cleanup for %s: %s", chat_id, type(exc).__name__)

    async def play_media(
        self, chat_id: int, message: Message, media: Media | Track, seek_time: int = 0
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (
            await thumb.generate(media) if isinstance(media, Track) else config.DEFAULT_THUMB
        ) if config.THUMB_GEN else None

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
            return

        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT if media.video else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )
        try:
            await client.play(
                chat_id=chat_id, stream=stream,
                config=types.GroupCallConfig(auto_start=False),
            )
            if not seek_time:
                media.time = max(1, media.time)
                await db.add_call(chat_id)
                text = _lang["play_media"].format(
                    media.url, media.title, media.duration, media.user,
                )
                keyboard = buttons.controls(chat_id)
                try:
                    if _thumb:
                        await message.edit_media(
                            media=InputMediaPhoto(media=_thumb, caption=text),
                            reply_markup=keyboard,
                        )
                    else:
                        await message.edit_text(text, reply_markup=keyboard)
                except (ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid):
                    if _thumb:
                        sent = await app.send_photo(
                            chat_id=chat_id, photo=_thumb, caption=text, reply_markup=keyboard
                        )
                    else:
                        sent = await app.send_message(
                            chat_id=chat_id, text=text, reply_markup=keyboard
                        )
                    media.message_id = sent.id
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            await self.play_next(chat_id)
        except (ConnectionError, ConnectionNotFound, TelegramServerError, TransportParseException, TimeoutError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])
        except Exception:
            logger.exception("Unexpected playback error in chat %s", chat_id)
            await self.stop(chat_id)
            try:
                await message.edit_text(_lang["error_tg_server"])
            except Exception:
                pass

    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return
        media = queue.get_current(chat_id)
        if media is None:
            await self.stop(chat_id)
            return
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)

    async def play_next(self, chat_id: int) -> None:
        # This transition is iterative and bounded. It guards against a burst
        # of duplicate StreamEnded and /skip events within this bot process.
        async with self._lock_for(chat_id):
            for _attempt in range(config.PLAYBACK_SKIP_LIMIT):
                loop = await db.get_loop(chat_id)
                current = queue.get_current(chat_id)
                if loop and current is not None:
                    await db.set_loop(chat_id, loop - 1)
                    media = current
                    break

                media = queue.get_next(chat_id)
                if media is None:
                    await self.stop(chat_id)
                    return

                old_message_id = getattr(media, "message_id", 0)
                if old_message_id:
                    try:
                        await app.delete_messages(
                            chat_id=chat_id, message_ids=old_message_id, revoke=True
                        )
                    except Exception:
                        pass
                    media.message_id = 0

                if media.file_path:
                    break
                try:
                    media.file_path = await yt.download(media.id, video=media.video)
                except Exception:
                    logger.exception("Track download raised in chat %s", chat_id)
                    media.file_path = None
                if media.file_path:
                    break
                logger.warning("Skipping unavailable track %s in chat %s", media.id, chat_id)
            else:
                logger.error("Playback skip limit reached in chat %s; stopping queue", chat_id)
                await self.stop(chat_id)
                return

            _lang = await lang.get_lang(chat_id)
            msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
            media.message_id = msg.id
            await self.play_media(chat_id, msg, media)

    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2) if pings else 0.0

    async def decorators(self, client: PyTgCalls) -> None:
        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)

    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")
