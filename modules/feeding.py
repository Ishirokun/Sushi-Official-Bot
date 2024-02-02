import discord
import random
from discord.ext import commands
from discord import Interaction
from datetime import timedelta
from .economy import SushiData, Inventory


class Feeder(discord.ui.View):
    def __init__(self, client, target):
        super().__init__(timeout=120)
        self.client = client
        self.sushi_data = SushiData(client.database)
        self.user = target
        self.target = client.database.get_user(target)
        for sushi in self.sushi_data.sushi_names:
            self.add_item(Feed(self, sushi))


class Feed(discord.ui.Button):
    def __init__(self, view, name):
        super().__init__(label=name)
        self._view = view
        self.name = name
        self.data = self.view.sushi_data.get_data(name)
        self.booster = self.data.get("boost")
        self.duration = timedelta(hours=self.data.get("duration"))

    async def callback(self, interaction: Interaction):
        inventory = Inventory(self.view.client, interaction.user)
        if interaction.user == self.view.user and inventory.get_item(self.name) > 0:
            if not self.data.get("consumable"):
                await interaction.channel.send("You cannot eat this! Feed it to someone instead")
                return
            await inventory.add_item(self.name, add=-1)
            await interaction.channel.send(f"{self.view.user.mention} eaten a {self.name}, Yummy. You have {inventory.get_item(self.name)} left", delete_after=30)
            booster = random.randint(self.booster[0], self.booster[1])
            print(booster)
            await self.view.target.boosters.add_booster(
                boost_id=f"self_{self.name}",
                boost=booster,
                duration=self.duration,
                reason=f"Eating a {self.name}")
        elif inventory.get_item(self.name) is None:
          await interaction.channel.send(f"{interaction.user.mention} You do not have any of {self.name}")
        elif inventory.get_item(self.name) < 1:
          await interaction.channel.send(f"{interaction.user.mention} You do not have any of {self.name}")
        elif inventory.get_item(self.name) > 0:
            if not self.data.get("feedable"):
                await interaction.channel.send("You cannot feed this to someone! Consider eating it")
                return
            await inventory.add_item(self.name, add=-1)
            booster = random.randint(self.booster[0], self.booster[1])
            print(booster)
            await interaction.channel.send(
                f"{self.view.user.mention} has been fed a {self.name} by {interaction.user.mention}, Yummy. You have {inventory.get_item(self.name)} left",
                delete_after=30)
            await self.view.target.boosters.add_booster(
                boost_id=f"fed_{self.name}",
                boost=booster,
                duration=self.duration,
                reason=f"Fed a {self.name} by {interaction.user}")


class Feeding(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.database = client.database
        self.sushi = SushiData(self.database)

    @commands.command(aliases=['eat', 'f', 'e'])
    async def feed(self, ctx, *, member: discord.Member = None):
        if member is None:
            member = ctx.author
        elif member == ctx.author:
            await ctx.send("Note : You can just do `s!feed` without mentioning yourself or just `s!eat`")
        await ctx.send(f"Feeding {member.mention}", view=Feeder(self.client, member))


def setup(client):
    print("Initiating the Feeding Systems")
    client.add_cog(Feeding(client))