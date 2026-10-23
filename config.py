from os import getenv
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.API_ID = int(getenv("API_ID", 0))
        self.API_HASH = getenv("API_HASH")
        self.BOT_TOKEN = getenv("BOT_TOKEN")
        self.MONGO_URL = getenv("MONGO_URL")
        self.LOGGER_ID = int(getenv("LOGGER_ID", 0))
        self.OWNER_ID = int(getenv("OWNER_ID", 0))
        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", 60)) * 60
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", 20))
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", 20))
        self.PLAYBACK_SKIP_LIMIT = int(getenv("PLAYBACK_SKIP_LIMIT", 8))

        self.SESSION1 = getenv("SESSION")
        self.SESSION2 = getenv("SESSION2")
        self.SESSION3 = getenv("SESSION3")

        self.ENABLE_EVAL = getenv("ENABLE_EVAL", "False").lower() == "true"
        self.EVAL_AUDIT = getenv("EVAL_AUDIT", "True").lower() == "true"
        self.BROADCAST_AUTO_LEAVE = getenv("BROADCAST_AUTO_LEAVE", "False").lower() == "true"
        self.BROADCAST_RETRY_LIMIT = int(getenv("BROADCAST_RETRY_LIMIT", 3))
        self.BROADCAST_PROGRESS_EVERY = int(getenv("BROADCAST_PROGRESS_EVERY", 25))
        self.MIGRATION_DRY_RUN = getenv("MIGRATION_DRY_RUN", "True").lower() != "false"
        self.MIGRATION_BACKUP_DIR = getenv("MIGRATION_BACKUP_DIR", "migration_backups")

        self.SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/fallenx")
        self.SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/DevilsHeavenMF")
        self.AUTO_LEAVE = getenv("AUTO_LEAVE", "False").lower() == "true"
        self.AUTO_END = getenv("AUTO_END", "False").lower() == "true"
        self.THUMB_GEN = getenv("THUMB_GEN", "True").lower() == "true"
        self.VIDEO_PLAY = getenv("VIDEO_PLAY", "True").lower() == "true"
        self.LANG_CODE = getenv("LANG_CODE", "en")
        self.COOKIES_URL = [
            url for url in getenv("COOKIES_URL", "").split()
            if url and "batbin.me" in url
        ]
        self.DEFAULT_THUMB = getenv(
            "DEFAULT_THUMB",
            "https://te.legra.ph/file/3e40a408286d4eda24191.jpg",
        )
        self.PING_IMG = getenv("PING_IMG", "https://files.catbox.moe/haagg2.png")
        self.START_IMG = getenv("START_IMG", "https://files.catbox.moe/zvziwk.jpg")

    def check(self):
        required = {
            "API_ID": self.API_ID, "API_HASH": self.API_HASH,
            "BOT_TOKEN": self.BOT_TOKEN, "MONGO_URL": self.MONGO_URL,
            "LOGGER_ID": self.LOGGER_ID, "OWNER_ID": self.OWNER_ID,
            "SESSION": self.SESSION1,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
        if self.DURATION_LIMIT <= 0:
            raise SystemExit("DURATION_LIMIT must be positive")
        if self.QUEUE_LIMIT < 1 or self.PLAYLIST_LIMIT < 1:
            raise SystemExit("QUEUE_LIMIT and PLAYLIST_LIMIT must be positive")
        if self.PLAYBACK_SKIP_LIMIT < 1:
            raise SystemExit("PLAYBACK_SKIP_LIMIT must be positive")
        if self.BROADCAST_RETRY_LIMIT < 0 or self.BROADCAST_PROGRESS_EVERY < 1:
            raise SystemExit("Broadcast retry/progress values are invalid")
