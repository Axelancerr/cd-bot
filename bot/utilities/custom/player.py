# Future
from __future__ import annotations

# Standard Library
import asyncio
import contextlib
from typing import TYPE_CHECKING

# Packages
import async_timeout
import discord
import slate
import slate.obsidian
import yarl

# My stuff
from core import values
from utilities import custom, enums, exceptions, utils


if TYPE_CHECKING:

    # My stuff
    from core.bot import CD

__all__ = (
    "Player",
)


class Player(slate.obsidian.Player["CD", custom.Context, "Player"]):

    def __init__(self, client: CD, channel: discord.VoiceChannel) -> None:
        super().__init__(client, channel)

        self._queue_add_event: asyncio.Event = asyncio.Event()
        self._track_end_event: asyncio.Event = asyncio.Event()

        self._text_channel: discord.TextChannel | None = None
        self._message: discord.Message | None = None
        self._task: asyncio.Task | None = None

        self._skip_request_ids: set[int] = set()
        self._enabled_filters: set[enums.Filters] = set()

        self.queue: custom.Queue = custom.Queue(self)

    # Properties

    @property
    def text_channel(self) -> discord.TextChannel | None:
        return self._text_channel

    @property
    def voice_channel(self) -> discord.VoiceChannel:
        return self.channel

    # Loop

    async def loop(self) -> None:

        while True:

            self._queue_add_event.clear()
            self._track_end_event.clear()

            if self.queue.is_empty():

                try:
                    with async_timeout.timeout(delay=3600):
                        await self._queue_add_event.wait()
                except asyncio.TimeoutError:
                    await self.disconnect()
                    break

            track = self.queue.get()

            if track.source is slate.obsidian.Source.SPOTIFY:

                try:
                    search = await self.search(f"{track.author} - {track.title}", source=slate.obsidian.Source.YOUTUBE, ctx=track.ctx)
                except exceptions.EmbedError as error:
                    await self.send(embed=error.embed)
                    continue

                track = search.tracks[0]

            await self.play(track)

            await self._track_end_event.wait()

    async def connect(self, *, timeout: float | None = None, reconnect: bool | None = None, self_deaf: bool = True) -> None:

        await super().connect(timeout=timeout, reconnect=reconnect, self_deaf=self_deaf)
        self._task = asyncio.create_task(self.loop())

    async def disconnect(self, *, force: bool = False) -> None:

        await super().disconnect(force=force)
        if self._task is not None and self._task.done() is False:
            self._task.cancel()

    # Events

    async def handle_track_start(self) -> None:
        self._message = await self.invoke_controller()

    async def handle_track_end(self) -> None:

        if self._message:

            old = self.queue._queue_history[0]

            embed = utils.embed(
                description=f"Finished playing **[{old.title}]({old.uri})** by **{old.author}**."
            )
            await self._message.edit(embed=embed)

        self._message = None
        self._current = None
        self._skip_request_ids = set()

        self._track_end_event.set()
        self._track_end_event.clear()

    async def handle_track_error(self) -> None:

        embed = utils.embed(
            colour=values.RED,
            description="Something went wrong while playing a track."
        )
        await self.send(embed=embed)

        await self.handle_track_end()

    # Misc

    async def send(self, *args, **kwargs) -> None:

        if not self.text_channel:
            return

        await self.text_channel.send(*args, **kwargs)

    async def invoke_controller(self, channel: discord.TextChannel | None = None) -> discord.Message | None:

        if (channel := channel or self.text_channel) is None or self.current is None:
            return

        embed = utils.embed(
            title="Now playing:",
            description=f"**[{self.current.title}]({self.current.uri})**\nBy **{self.current.author}**",
            thumbnail=self.current.thumbnail
        )

        embed.add_field(
            name="__Player info:__",
            value=f"**Paused:** {self.paused}\n"
                  f"**Loop mode:** {self.queue.loop_mode.name.title()}\n"
                  f"**Queue length:** {len(self.queue)}\n"
                  f"**Queue time:** {utils.format_seconds(sum(track.length for track in self.queue) // 1000, friendly=True)}\n",
        )
        embed.add_field(
            name="__Track info:__",
            value=f"**Time:** {utils.format_seconds(self.position // 1000)} / {utils.format_seconds(self.current.length // 1000)}\n"
                  f"**Is Stream:** {self.current.is_stream()}\n"
                  f"**Source:** {self.current.source.value.title()}\n"
                  f"**Requester:** {self.current.requester.mention if self.current.requester else 'N/A'}\n"
        )

        if not self.queue.is_empty():

            entries = [f"**{index + 1}.** [{entry.title}]({entry.uri})" for index, entry in enumerate(list(self.queue)[:3])]
            if len(self.queue) > 3:
                entries.append(f"**...**\n**{len(self.queue)}.** [{self.queue[-1].title}]({self.queue[-1].uri})")

            embed.add_field(
                name="__Up next:__",
                value="\n".join(entries),
                inline=False
            )

        return await channel.send(embed=embed)

    async def search(
        self,
        query: str,
        /,
        *,
        source: slate.obsidian.Source,
        ctx: custom.Context | None,
    ) -> slate.obsidian.Result[custom.Context]:

        if (url := yarl.URL(query)) and url.host and url.scheme:
            source = slate.obsidian.Source.NONE

        try:
            search = await self._node.search(query, source=source, ctx=ctx)

        except slate.obsidian.NoResultsFound as error:
            raise exceptions.EmbedError(
                description=f"No {error.search_source.value.lower().replace('_', ' ')} {error.search_type.value}s were found for your search.",
            )

        except (slate.obsidian.SearchFailed, slate.HTTPError):
            raise exceptions.EmbedError(
                description="There was an error while searching for results.",
            )

        return search

    async def queue_search(
        self,
        query: str,
        /,
        *,
        source: slate.obsidian.Source,
        ctx: custom.Context,
        now: bool = False,
        next: bool = False,
        choose: bool = False,
    ) -> None:

        result = await self.search(query, source=source, ctx=ctx)

        if result.search_type in {slate.obsidian.SearchType.TRACK, slate.obsidian.SearchType.SEARCH_RESULT} or isinstance(result.result, list):

            if choose:
                # choice = await ctx.choice(
                #    entries=[f"**{index + 1:}.** [{track.title}]({track.uri})" for index, track in enumerate(result.tracks)],
                #    per_page=10,
                #    title="Select the number of the track you want to play:",
                # )
                tracks = result.tracks[0]
            else:
                tracks = result.tracks[0]

            description = f"Added the {result.search_source.value.lower()} track " \
                          f"[{result.tracks[0].title}]({result.tracks[0].uri}) to the queue."

        else:
            tracks = result.tracks
            description = f"Added the {result.search_source.value.lower()} {result.search_type.name.lower()} " \
                          f"[{result.result.name}]({result.result.url}) to the queue."

        await ctx.reply(
            embed=utils.embed(
                colour=values.GREEN,
                description=description
            )
        )

        self.queue.put(tracks, position=0 if (now or next) else None)
        if now:
            await self.stop()
