import random
import discord
import pytz
from discord import InteractionType
from discord.ext import commands
from typing import Dict
from datetime import datetime, timedelta


def is_me():
    def predicate(ctx):
        return ctx.message.author.id == 258247247987212288
    return commands.check(predicate)


class CookRNG:
    def __init__(self, parent):
        self.parent = parent
        self.pool = {
            "Ultimate Sushi": 0.01,
            "Legendary Sushi": 0.1,
            "Epic Sushi": 2,
            "Rare Sushi": 10,
            "Uncommon Sushi": 30,
            "Common Sushi": 100
        }
        self.pity_increase = {
          "Common Sushi": 0.05,
          "Uncommon Sushi": 0.025,
          "Rare Sushi": 0.01
        }

    def cook(self):
        for key in self.pool.keys():
            if key not in list(self.pity_increase.keys()):
              chance = int(100/(self.pool[key] * self.parent.pity))
            else:
              chance = int(100/self.pool[key])
            if chance < 1:
              chance = 1
            x = random.randint(1, chance)
            if x == 1:
                if key in list(self.pity_increase.keys()):
                  self.parent.pity += self.pity_increase.get(key)
                else:
                  self.parent.pity = 1
                return key

class WishRNG:
    def __init__(self, client):
        self.client = client
        self.pool = {
            "Godly Sushi": 0.01,
            "Omega Sushi": 0.1,
            "Wishing Sushi": 0.25,
            "Ultimate Sushi": 0.5,
            "Legendary Sushi": 1,
            "Epic Sushi": 10,
            "Rare Sushi": 100,
        }

    async def wish(self, inventory, user):
        y = random.randint(1,3)
        if y == 1:
            for key in self.pool.keys():
                x = random.randint(1, int(100 / self.pool[key]))
                if x == 1:
                    inventory.add_item(key)
                    return f"You wished and got a {key}"
        if y == 2:
            booster = random.randint(10, 50)
            await user.boosters.add_booster(
                boost_id=f"boost_{inventory.id}",
                boost=booster,
                duration=timedelta(minutes=30.0),
                reason="Wishing")
            return f"The Gods have answered to your calls and given you a boost of {booster}"
        else:
            replies = [
                "It seems like the God of luck is not on your side",
                "Your wishes weren't answered",
                "The sky darkens as you wished, it seems you are unlucky",
                "There was no reply to your wishes",
            ]
            return random.choice(replies)


class Stealing:
    def __init__(self, inventories):
        self.inventories = inventories
        self.pool = {
            "Ultimate Sushi": 0.1,
            "Legendary Sushi": 0.5,
            "Epic Sushi": 5,
            "Rare Sushi": 20,
            "Uncommon Sushi": 40,
            "Common Sushi": 100
        }

    @property
    def user_list(self):
        return [x["_id"] for x in list(self.inventories.find({}))]

    @property
    def random_user(self):
        return random.choice(self.user_list)

    async def steal(self):
        unfortunate = self.inventories.find_one({"_id": self.random_user})
        steal_pool = {}
        for key in unfortunate.keys():
            if key in self.pool.keys() and unfortunate[key] > 0:
                steal_pool[key] = self.pool[key]
        for key in steal_pool.keys():
            chance = int(100/self.pool[key])
            x = random.randint(1, chance)
            if x == 1:
                return [key, unfortunate["_id"]]
        return [None, unfortunate["_id"]]


class Inventory:
    def __init__(self, client, user):
        self.client = client
        self.inventories = client.database.inventories
        self.database = client.database.users_collection
        self.user = user
        self.id = user.id
        self.cooking = CookRNG(self)
        self.wishing = WishRNG(self)
        self.stealing = Stealing(self.inventories)

    @property
    def inventory(self):
        data = self.inventories.find_one({"_id": self.id})
        if data is None:
            data = {"_id": self.id}
            self.inventories.insert_one(data)
        return data

    @property
    def pity(self):
        pity = self.userdata.get("pity")
        if pity is None:
            return 1
        return pity

    @pity.setter
    def pity(self, value):
        self.set_userdata("pity", value)

    @property
    def now(self):
        tz = pytz.timezone('Asia/Tokyo')
        return datetime.now(tz)

    def get_datetime(self, key: str = None):
        dt = self.userdata.get(key)
        if dt is None:
            self.database.update_one({"_id": self.id}, {"$set": {key: str(self.now)}})
            return self.now
        return datetime.fromisoformat(dt)

    @property
    def userdata(self) -> Dict:
        data = self.database.find_one({"_id": self.id})
        if data is None:
            data = {
                "_id": self.id
            }
            self.database.insert_one(data)
        return data

    def set_userdata(self, key: str, value):
        self.database.update_one({"_id": self.id}, {"$set": {key: value}})

    def on_cooldown(self,
                    key,
                    *,
                    cooldown: timedelta = timedelta(minutes=1.0)
                    ):
        cd = self.get_datetime(key)
        if not self.now < cd:
            end_time = str(self.now + cooldown)
            self.set_userdata(key, end_time)
            return False
        else:
            return True

    def get_cooldown(self, key):
        cd = self.get_datetime(key)
        return cd - self.now

    def get_item(self, item: str):
        return self.inventory.get(item)

    def add_item(self, item: str, *, add: int = 1):
        count = self.get_item(item)
        if count is None:
            
            self.inventories.update_one({"_id": self.id}, {"$set": {item: 0}})
            count = 0
        count += add
        self.inventories.update_one({"_id": self.id}, {"$set": {item: count}})

    async def cook(self, interaction):
        if not self.on_cooldown("cook_cd"):
            sushi = self.cooking.cook()
            self.add_item(sushi)
            await interaction.channel.send(f"{interaction.user.mention} have cooked 1x **{sushi}**", delete_after=60)
        else:
            cooldown = str(self.get_cooldown('cook_cd'))
            cooldown = cooldown.split(".")[0]
            values = cooldown.split(":")
            cooldown = f"{values[1]}:{values[2]}"
            await interaction.followup.send(f"You are on cooldown wait {cooldown}", ephemeral=True)

    async def fish(self):
        if not self.on_cooldown("fish_cd", cooldown=timedelta(minutes=2)):
            print("Fishing")
        else:
            print("On Cooldown")

    async def order(self):
        if not self.on_cooldown("order_cd", cooldown=timedelta(minutes=5)):
            print("Order")
        else:
            print("On Cooldown")

    async def wish(self, interaction):
        if not self.on_cooldown("wish_cd", cooldown=timedelta(minutes=10)):
            user = self.client.database.get_user(self.user)
            reply = await self.wishing.wish(self, user)
            await interaction.channel.send(f"{interaction.user.mention}, {reply}", delete_after=60)
        else:
            cooldown = str(self.get_cooldown('wish_cd'))
            cooldown = cooldown.split(".")[0]
            values = cooldown.split(":")
            cooldown = f"{values[1]}:{values[2]}"
            await interaction.followup.send(f"You are on cooldown wait {cooldown}", ephemeral=True)

    async def steal(self, interaction):
        if not self.on_cooldown("steal_cd", cooldown=timedelta(minutes=2.5)):
            result = await self.stealing.steal()
            if result[1] == 0:
                await interaction.followup.send(f"You didn't find anyone to steal from, sadly"
                                                , ephemeral=True)
                return
            user = interaction.guild.get_member(result[1])
            if result[0] is None:
                await interaction.followup.send(f"You tried to steal from {user.mention}, but failed!"
                                                , ephemeral=True)
                return
            user_inventory = Inventory(self.client, user)
            user_inventory.add_item(result[0], add=-1)
            self.add_item(result[0])
            await interaction.followup.send(f"You stole a **{result[0]}** from {user.mention}", ephemeral=True)
        else:
            cooldown = str(self.get_cooldown('steal_cd'))
            cooldown = cooldown.split(".")[0]
            values = cooldown.split(":")
            cooldown = f"{values[1]}:{values[2]}"
            await interaction.followup.send(f"You are on cooldown wait {cooldown}", ephemeral=True)



class CookGUI(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Cook', style=discord.ButtonStyle.green, emoji="🍣", custom_id='sushi:cook')
    async def cook(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

    @discord.ui.button(label='Fish', style=discord.ButtonStyle.green, emoji="🎣",custom_id='sushi:fish', disabled=True)
    async def fish(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

    @discord.ui.button(label='Order', style=discord.ButtonStyle.green, emoji="📃", custom_id='sushi:order', disabled=True)
    async def order(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

    @discord.ui.button(label='Wish', style=discord.ButtonStyle.green, emoji="🙏",custom_id='sushi:wish')
    async def wish(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

    @discord.ui.button(label='Steal', style=discord.ButtonStyle.red, emoji="😏", custom_id='sushi:steal')
    async def steal(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass


class Cooking(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.just_started = True
        self.inventories = self.client.database.inventories
        self.threads = self.inventories.find_one({"_id": 0})
        del self.threads["_id"]

    @commands.command(aliases=['inv', 'in', 'i', 'items'], 
                      description="Opens inventory to show your items."
                      )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def inventory(self, ctx, *, member: discord.Member = None):
        await ctx.message.delete()
        if member is None:
            member = ctx.author
        embed = discord.Embed()
        embed.title = "Inventory"
        data = self.inventories.find_one({"_id": member.id})
        for item in data.keys():
            if item != "_id":
                count = data[item]
                if count != 0:
                    embed.add_field(name=item, value=f"{count}x")
        if len(data) == 0:
            embed.add_field(name="Empty", value="Nothing to see here", inline=False)
        embed.set_footer(text=f"{member}", icon_url=member.avatar.url)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        for channel_id in self.threads.values():
            thread = await self.client.fetch_channel(channel_id)
            messages = await thread.history(limit=50).flatten()
            for message in messages:
                print(message.content)
                if not message.author.bot and not message.is_system():
                    await message.delete()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id in self.threads.values() and not message.author.bot:
            await message.delete()

    @commands.command()
    @is_me()
    async def ssz(self, ctx):
        if ctx.author.id != 258247247987212288:
            return
        message = await ctx.send("This channel has now been set as a Special Sushi Zone!")
        await message.pin()
        thread = await message.create_thread(name="Sushi Cooking")
        embed = discord.Embed(title="Sushi Cooking System")
        embed.description = """Cooldowns
                                Cook : 1 minute
                                Fish : 2 minutes
                                Order : 5 minutes
                                Wish : 10 minutes
                                Steal : 2 minutes and 30 seconds"""
        view = CookGUI()
        await thread.send(embed=embed, view=view)
        self.threads[f"{ctx.channel.id}"] = thread.id
        self.inventories.update_one({"_id": 0}, {"$set": {str(ctx.channel.id): thread.id}})
      
    @commands.command()
    async def cooking(self, ctx):
        thread = self.client.get_channel(self.threads[f"{ctx.channel.id}"])
        await thread.add_user(ctx.author)
        messages = await thread.history(limit=5).flatten()
        for message in messages:
            if message.embeds:
                await message.delete()
        embed = discord.Embed(title="Sushi Cooking System")
        embed.description = """Cooldowns\n
                                Cook : 1 minute\n
                                Fish : 2 minutes\n
                                Order : 5 minutes\n
                                Wish : 10 minutes\n
                                Steal : 2 minutes and 30 seconds"""
        view = CookGUI()
        await thread.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type != InteractionType.component:
            return
        try:
          await interaction.response.defer()
        except:
          pass
        if interaction.data["custom_id"].startswith("sushi"):
            user = Inventory(self.client, interaction.user)
            payload = interaction.data["custom_id"].split(":")[1]
            if payload == "cook":
                await user.cook(interaction)
            if payload == "wish":
                await user.wish(interaction)
            if payload == "steal":
              await user.steal(interaction)


def setup(client):
    print("Loading Cooking Module")
    client.add_cog(Cooking(client))
