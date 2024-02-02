import discord
import typing
import random
from discord.ext import commands, tasks
from collections import Counter
from datetime import timedelta

def is_me():
    def predicate(ctx):
        return ctx.message.author.id == 258247247987212288
    return commands.check(predicate)

class Leveling(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.connected = []
        self.channels = {}
        setattr(client, "connected", self.connected)
        self.just_started = True
        self._cd = commands.CooldownMapping.from_cooldown(1, 60.0, commands.BucketType.member)

    def get_rate_limit(self, message: discord.Message) -> typing.Optional[int]:
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    @tasks.loop(minutes=1.0)
    async def add_exp(self):
        for connected in self.connected:
            await connected.vc_exp(random.randint(5, 10))

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.author.bot:
            return
        if str(ctx.channel.id) not in self.channels.keys():
            self.channels[str(ctx.channel.id)] = []
        self.channels[str(ctx.channel.id)].insert(0, str(ctx.author.id))
        if len(self.channels[str(ctx.channel.id)]) > 10:
            self.channels[str(ctx.channel.id)].pop()
        count = dict(Counter(self.channels[str(ctx.channel.id)]))
        if count[str(ctx.author.id)] > 7:
            self_talk = True
        else:
            self_talk = False
        rate_limit = self.get_rate_limit(ctx)
        if rate_limit is None or ctx.author.id == 258247247987212288:
            if self_talk:
                xp_gain = random.randint(5, 10)
            else:
                xp_gain = random.randint(10, 20)
            await self.client.database.get_user(ctx.author).add_exp(xp_gain)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"A New Member has joined : {member}, Adding to the database")

    @commands.Cog.listener()
    async def on_ready(self):
        print("\nLEVELING MODULE STARTED\n")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if self.just_started:
            for vc in member.guild.voice_channels:
                for member in vc.members:
                    if not member.bot:
                        await self.client.database.get_user(member).update()
            self.just_started = False
            self.add_exp.start()
        try:
            await self.client.database.get_user(member).update()
        except:
            pass

    @commands.command()
    @is_me()
    async def boost(self, ctx, *, user : discord.Member = None):
        if ctx.author.id != 258247247987212288:
            return
        if user is None:
            user = ctx.author
        user_id = user.id
        user_data = self.client.database.get_user(user)
        await user_data.boosters.add_booster(boost=100, duration=timedelta(minutes=3))
        await ctx.send("Given booster!")


def setup(client):
    client.add_cog(Leveling(client))
