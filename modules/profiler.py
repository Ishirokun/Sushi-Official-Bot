import random
import discord
import asyncio
from discord.ext import commands
from datetime import timedelta
from .economy import Inventory


class Profile(discord.ui.View):
    def __init__(self,
                 client,
                 member,
                 ):
        self.member = member
        self.inventory = Inventory(client, member)
        self.client = client
        self.page = 1
        super().__init__(timeout=120)

    def title_parser(self, member):
        rank = self.client.database.get_ranking(member)
        if rank == 1:
            emoji = "👑"
        elif rank <= 10:
            emoji = "🍣"
        else:
            emoji = ""
        return f"{member} - {emoji} Ranked #{rank}"

    async def profile(self):
        user = self.user
        await user.boosters.get_booster()
        embed = discord.Embed()
        embed.title = self.title_parser(self.member)
        embed.description = "No description yet"
        embed.add_field(name="Level", value=f"{user.level}")
        embed.add_field(name="XP", value=f"{user.xp_current}/{user.xp_goal}")
        embed.add_field(name="Money", value=f"{self.inventory.currency} ¥")
        embed.add_field(name="Booster", value=f"{user.boosters.booster}%")
        embed.add_field(name="Badges", value="_ _")
        embed.set_thumbnail(url=self.member.avatar.url)
        return embed

    async def button_update(self):
        for component in self.children:
            if component.custom_id == "sushi:page":
                component.label = f"{self.page}/{self.max_pages}"
            if self.page <= 1:
                if component.custom_id == "sushi:max_left" or component.custom_id == "sushi:left":
                    component.disabled = True
            else:
                if component.custom_id == "sushi:max_left" or component.custom_id == "sushi:left":
                    component.disabled = False
            if self.page >= self.max_pages:
                if component.custom_id == "sushi:max_right" or component.custom_id == "sushi:right":
                    component.disabled = True
            else:
                if component.custom_id == "sushi:max_right" or component.custom_id == "sushi:right":
                    component.disabled = False

    async def update(self, interaction):
        await self.button_update()
        if self.page == 1:
            profile = await self.profile()
            await interaction.message.edit(embed=profile, view=self)
        else:
            await interaction.message.edit(embed=self.booster_pages[self.page-2], view=self)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="⏮", custom_id='sushi:max_left', disabled=True)
    async def max_left(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page = 1
        await self.update(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="◀", custom_id='sushi:left', disabled=True)
    async def left_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page -= 1
        await self.update(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="📖", custom_id='sushi:page', disabled=True)
    async def pages(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.update(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="▶", custom_id='sushi:right')
    async def right_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page += 1
        await self.update(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="⏭", custom_id='sushi:max_right')
    async def max_right(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page = self.max_pages
        await self.update(interaction)

    @property
    def user(self):
        return self.client.database.get_user(self.member)

    @property
    def max_pages(self):
        return len(self.booster_pages)+1

    @staticmethod
    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    @property
    def booster_pages(self):
        pages = []
        boosters = self.user.boosters.booster_list
        chunks = list(self.chunks(boosters, 9))
        for chunk in chunks:
            new_embed = discord.Embed(title="Boosters 3.0")
            new_embed.set_footer(text=f"Boosters of {self.member}", icon_url=self.member.avatar.url)
            for boost in chunk:
                new_embed.add_field(name=f"{boost.boost}% - {boost.reason}", value=f"{boost.time_left}")
            pages.append(new_embed)
        return pages


class Profiler(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(
        aliases=['p'],
    )
    async def profile(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        view = Profile(self.client, member)
        await view.button_update()
        embed = await view.profile()
        await ctx.send(embed=embed, view=view)

    @commands.command(aliases=['lb', 'leaders', 'toplist'])
    async def leaderboards(self, ctx):
        embed = discord.Embed(title="Leaderboards for Sushi Leveling")
        x = 0
        i = 0
        while i < 10:
            user = self.client.get_user(self.client.database.get_member(x))
            print(user)
            if user is not None:
              user_data = self.client.database.get_user(user)
              if x == 0:
                embed.set_thumbnail(url=user.avatar.url)
              embed.add_field(name=f"#{x+1} - {user}", value=f"Lv.{user_data.level} XP {user_data.xp}", inline=False)
              i += 1
            x += 1
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content:
            if "earl is a great mod" in message.content.lower():
                user = self.client.database.get_user(message.author)
                await user.boosters.add_booster(
                    boost_id=f"earl_{message.author.id}",
                    boost=10,
                    duration=timedelta(hours=1.0),
                    reason="Earl is a great mod")
        if message.mentions:
            if not message.mentions[0] == message.author:
                return


def setup(client):
    client.add_cog(Profiler(client))