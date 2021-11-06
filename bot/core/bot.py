# Future
from __future__ import annotations

# Standard Library
import collections
import logging
import time
import traceback
from typing import Type

# Packages
import aiohttp
import aioredis
import asyncpg
import discord
import mystbin
import psutil
import slate.obsidian
from discord.ext import commands, tasks

# My stuff
from core import config, values
from utilities import checks, custom, enums, utils


__log__: logging.Logger = logging.getLogger("bot")


class CD(commands.AutoShardedBot):

    def __init__(self) -> None:
        super().__init__(
            status=discord.Status.dnd,
            activity=discord.Activity(type=discord.ActivityType.listening, name="you."),
            allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=False),
            help_command=custom.HelpCommand(),
            intents=discord.Intents.all(),
            command_prefix=commands.when_mentioned_or(config.PREFIX),
            case_insensitive=True,
            owner_ids=values.OWNER_IDS,
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.socket_stats: collections.Counter = collections.Counter()
        self.process: psutil.Process = psutil.Process()

        self.db: asyncpg.Pool = utils.MISSING
        self.redis: aioredis.Redis = utils.MISSING

        self.slate: slate.obsidian.NodePool[CD, custom.Context, slate.obsidian.Player] = slate.obsidian.NodePool()
        self.mystbin: mystbin.Client = mystbin.Client(session=self.session)

        self.first_ready: bool = True
        self.start_time: float = time.time()

        self.add_check(checks.bot, call_once=True)  # type: ignore

        self._log_webhooks: dict[enums.LogType, discord.Webhook] = {
            enums.LogType.DM:    discord.Webhook.from_url(session=self.session, url=config.DM_WEBHOOK_URL),
            enums.LogType.GUILD: discord.Webhook.from_url(session=self.session, url=config.GUILD_WEBHOOK_URL),
            enums.LogType.ERROR: discord.Webhook.from_url(session=self.session, url=config.ERROR_WEBHOOK_URL)
        }
        self._log_queue: dict[enums.LogType, list[discord.Embed]] = collections.defaultdict(list)
        self._log_loop.start()

    # Overridden methods

    async def get_context(self, message: discord.Message, *, cls: Type[commands.Context] = custom.Context) -> commands.Context:
        return await super().get_context(message=message, cls=cls)

    async def is_owner(self, user: discord.User | discord.Member) -> bool:
        return user.id in values.OWNER_IDS

    async def start(self, token: str, *, reconnect: bool = True) -> None:

        try:
            __log__.debug("[POSTGRESQL] Attempting connection.")
            db: asyncpg.Pool = await asyncpg.create_pool(**config.POSTGRESQL, max_inactive_connection_lifetime=0)  # type: ignore
        except Exception as e:
            __log__.critical(f"[POSTGRESQL] Error while connecting.\n{e}\n")
            raise ConnectionError()
        else:
            __log__.info("[POSTGRESQL] Successful connection.")
            self.db = db

        try:
            __log__.debug("[REDIS] Attempting connection.")
            redis = aioredis.from_url(url=config.REDIS, decode_responses=True, retry_on_timeout=True)
            await redis.ping()
        except (aioredis.ConnectionError, aioredis.ResponseError) as e:
            __log__.critical(f"[REDIS] Error while connecting.\n{e}\n")
            raise ConnectionError()
        else:
            __log__.info("[REDIS] Successful connection.")
            self.redis = redis

        for extension in values.EXTENSIONS:
            try:
                self.load_extension(extension)
                __log__.info(f"[EXTENSIONS] Loaded - {extension}")
            except commands.ExtensionNotFound:
                __log__.warning(f"[EXTENSIONS] Extension not found - {extension}")
            except commands.NoEntryPointError:
                __log__.warning(f"[EXTENSIONS] No entry point - {extension}")
            except commands.ExtensionFailed as error:
                __log__.warning(f"[EXTENSIONS] Failed - {extension} - Reason: {traceback.print_exception(type(error), error, error.__traceback__)}")

        await super().start(token=token, reconnect=reconnect)

    async def close(self) -> None:

        await self.session.close()

        if self.db:
            await self.db.close()
        if self.redis:
            await self.redis.close()

        await super().close()

    # Events

    async def on_ready(self) -> None:

        if self.first_ready is False:
            return

        self.first_ready = False
        __log__.info(f"{self.user} is ready.")

    # Logging

    @tasks.loop(seconds=3)
    async def _log_loop(self) -> None:

        for type, queue in self._log_queue.items():

            if not queue:
                continue

            embeds = [queue.pop(0) for _ in range(min(10, len(queue)))]
            await self._log_webhooks[type].send(embeds=embeds)

    async def log(self, type: enums.LogType, /, *, embed: discord.Embed) -> None:
        self._log_queue[type].append(embed)
