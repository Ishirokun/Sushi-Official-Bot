import os
os.system("python3 -m pip install git+https://github.com/rapptz/discord.py")
import discord
from discord.ext import commands
from modules.database import Database
from dashboard.dashboard import awoken


def is_me():
    def predicate(ctx):
        return ctx.message.author.id == 258247247987212288
    return commands.check(predicate)


class Main(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.client.load_extension('modules.leveling')
        self.client.load_extension('modules.profiler')
        self.client.load_extension('modules.confession')
        self.client.load_extension('modules.inventory')
        self.client.load_extension('modules.economy')
        self.client.load_extension('modules.feeding')

    @commands.Cog.listener()
    async def on_ready(self):
        print("\nBOT HAS STARTED\n")

    c
    async def load(self, ctx, module: str = None):
        if ctx.author.id != 258247247987212288:
            return
        if module is None:
            await ctx.send("Please write a module to load")
        else:
            try:
                self.client.load_extension(f'modules.{module}')
                await ctx.send(f"Loaded the module : {module}")
            except:
                await ctx.send("Fail to unload module")

    @commands.command()
    @is_me()
    async def unload(self, ctx, module: str = None):
        if ctx.author.id != 258247247987212288:
            return
        if module is None:
            await ctx.send("Please write a module to load")
        else:
            try:
                self.client.unload_extension(f'modules.{module}')
                await ctx.send(f"Loaded the module : {module}")
            except:
                await ctx.send("Fail to load module")

    @commands.command()
    @is_me()
    async def reload(self, ctx, module: str = None):
        if ctx.author.id != 258247247987212288:
            return
        if module is None:
            await ctx.send("Please write a module to reload")
            return
        try:
            self.client.reload_extension(f'modules.{module}')
            cog = self.client.get_cog(module)
            try:
                await cog.initialize()
            except:
                pass
            await ctx.send(f"Reloaded the module : {module}")
        except:
            await ctx.send("That module does not exists")

    @commands.Cog.listener()
    async def on_message(self, message):
        pass
        #await self.client.process_commands(message)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.message.delete()
            await ctx.send(
                'This command is on cooldown, you can use it in **{0}** seconds'.format(round(error.retry_after, 2)),
                delete_after=10
            )


class MyNewHelp(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            emby = discord.Embed(description=page)
            await destination.send(embed=emby)


if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.members = True
    client = commands.Bot(command_prefix="s!", intents=intents)
    database = Database(client)
    setattr(database, "client", client)
    setattr(client, "database", database)
    client.add_cog(Main(client))
    client.help_command = MyNewHelp()
    awoken()
    client.run(os.environ["bot_token"])
