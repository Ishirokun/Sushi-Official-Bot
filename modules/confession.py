import discord
import random
from discord.ext import commands
from asyncio import TimeoutError


def is_me():
    def predicate(ctx):
        return ctx.message.author.id == 258247247987212288
    return commands.check(predicate)


class Reply(discord.ui.View):
    def __init__(self, choices):
        super().__init__(timeout=5)
        for choice in list(choices.keys()):
            self.add_item(Replyee(self, choice))
        self.value = None


class Replyee(discord.ui.Button):
    def __init__(self, view, name):
        self.name = name
        super().__init__(label=f"{name}")

    async def callback(self, interaction: discord.Interaction):
        self.view.value = self.name
        self.view.stop()


class Confession(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
          return
        ctx = message
        if str(message.channel.type) == "private":
            confession = self.client.get_channel(839815940023517225)
            choices = {}
            messages = await confession.history(limit=10).flatten()
            for message in messages:
                if len(choices.keys()) <= 5 and message.embeds:
                    title = message.embeds[0].title
                    if title not in list(choices.keys()):
                        choices[title] = message
            view = Reply(choices)
            
            reply_message = await ctx.channel.send(
                content="Replying to :",
                view=view
            )

            await view.wait()
            await reply_message.delete()

            yama_id = ctx.author.id + 420
            random.seed(yama_id)
            embed = discord.Embed()
            embed.title = f"Yamasushie #{random.randint(1,1000000000)}"
            embed.description = ctx.content
            if ctx.attachments:
                embed.set_image(url=ctx.attachments[0].url)

            if view.value is None:
                await confession.send(embed=embed)
            else:
                replying_to = choices[view.value]
                embed.set_footer(text=f"Replying to : {view.value}")
                await replying_to.reply(embed=embed)

    @commands.command()
    @is_me()
    async def whois(self, ctx, *, confession_id: int):
        for member in ctx.guild.members:
            random.seed(member.id + 420)
            if random.randint(1,1000000000) == confession_id:
              await ctx.send(f"That user is ||{member.mention}||", delete_after=5)



    @commands.Cog.listener()
    async def on_button_click(self, interaction):
        if interaction.component.id.startswith("reply"):
            pass


def setup(client):
    client.add_cog(Confession(client))
