# Future
from __future__ import annotations

# Packages
import slate
import slate.obsidian

# My stuff
from core.bot import CD
from utilities import custom, exceptions
from utilities.utils import slash


def setup(bot: CD) -> None:
    bot.add_cog(SlashPlay(bot))


class SlashPlay(slash.ApplicationCog[CD]):

    @staticmethod
    async def _ensure_connected(ctx: slash.Context[CD, SlashPlay]) -> None:

        author_voice_channel = ctx.author.voice and ctx.author.voice.channel
        bot_voice_channel = ctx.voice_client and ctx.voice_client.voice_channel

        if not author_voice_channel:
            if bot_voice_channel:
                raise exceptions.EmbedError(description=f"You must be connected to {bot_voice_channel.mention} to use this command.")
            raise exceptions.EmbedError(description="You must be connected to a voice channel to use this command.")

        if bot_voice_channel:
            if bot_voice_channel == author_voice_channel:
                return
            raise exceptions.EmbedError(description=f"You must be connected to {bot_voice_channel.mention} to use this command.")

        await author_voice_channel.connect(cls=custom.Player)  # type: ignore
        ctx.voice_client.text_channel = ctx.channel  # type: ignore

    # Play

    @slash.slash_command(name="play", guild_id=855169856454131712)
    async def play(self, ctx: slash.Context[CD, SlashPlay], next: bool = False, now: bool = False, *, query: str) -> None:

        await self._ensure_connected(ctx)

        assert ctx.voice_client is not None
        await ctx.voice_client.queue_search(query, source=slate.obsidian.Source.YOUTUBE, ctx=ctx, play_next=next, play_now=now)

    @slash.slash_command(name="search", guild_id=855169856454131712)
    async def search(self, ctx: slash.Context[CD, SlashPlay], next: bool = False, now: bool = False, *, query: str) -> None:

        await self._ensure_connected(ctx)

        assert ctx.voice_client is not None
        await ctx.voice_client.queue_search(query, source=slate.obsidian.Source.YOUTUBE, ctx=ctx, search_select=True, play_next=next, play_now=now)

    # Youtube music

    @slash.slash_command(name="youtube-music", guild_id=855169856454131712)
    async def youtube_music(self, ctx: slash.Context[CD, SlashPlay], next: bool = False, now: bool = False, *, query: str) -> None:

        await self._ensure_connected(ctx)

        assert ctx.voice_client is not None
        await ctx.voice_client.queue_search(query, source=slate.obsidian.Source.YOUTUBE_MUSIC, ctx=ctx, play_next=next, play_now=now)

    @slash.slash_command(name="youtube-music-search", guild_id=855169856454131712)
    async def youtube_music_search(self, ctx: slash.Context[CD, SlashPlay], next: bool = False, now: bool = False, *, query: str) -> None:

        await self._ensure_connected(ctx)

        assert ctx.voice_client is not None
        await ctx.voice_client.queue_search(query, source=slate.obsidian.Source.YOUTUBE_MUSIC, ctx=ctx, search_select=True, play_next=next, play_now=now)

    # Soundcloud

    @slash.slash_command(name="soundcloud", guild_id=855169856454131712)
    async def soundcloud(self, ctx: slash.Context[CD, SlashPlay], next: bool = False, now: bool = False, *, query: str) -> None:

        await self._ensure_connected(ctx)

        assert ctx.voice_client is not None
        await ctx.voice_client.queue_search(query, source=slate.obsidian.Source.SOUNDCLOUD, ctx=ctx, play_next=next, play_now=now)

    @slash.slash_command(name="soundcloud-search", guild_id=855169856454131712)
    async def soundcloud_search(self, ctx: slash.Context[CD, SlashPlay], next: bool = False, now: bool = False, *, query: str) -> None:

        await self._ensure_connected(ctx)

        assert ctx.voice_client is not None
        await ctx.voice_client.queue_search(query, source=slate.obsidian.Source.SOUNDCLOUD, ctx=ctx, search_select=True, play_next=next, play_now=now)

    # Local

    @slash.slash_command(name="local", guild_id=855169856454131712)
    async def local(self, ctx: slash.Context[CD, SlashPlay], next: bool = False, now: bool = False, *, query: str) -> None:

        await self._ensure_connected(ctx)

        assert ctx.voice_client is not None
        await ctx.voice_client.queue_search(query, source=slate.obsidian.Source.LOCAL, ctx=ctx, play_next=next, play_now=now)

    # HTTP

    @slash.slash_command(name="http", guild_id=855169856454131712)
    async def http(self, ctx: slash.Context[CD, SlashPlay], next: bool = False, now: bool = False, *, query: str) -> None:

        await self._ensure_connected(ctx)

        assert ctx.voice_client is not None
        await ctx.voice_client.queue_search(query, source=slate.obsidian.Source.HTTP, ctx=ctx, play_next=next, play_now=now)
