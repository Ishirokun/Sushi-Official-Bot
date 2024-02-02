import discord
import pytz
import random
from datetime import datetime
from discord.ext import commands, tasks


class SushiData:
    def __init__(self, database):
        self.database = database
        self.sushi_data = database.db["sushidata"]

    def get_data(self, sushi):
        return self.sushi_data.find_one({"name": sushi})

    def get_all(self):
        return list(self.sushi_data.find({}))

    @property
    def sushi_names(self):
        return [x["name"] for x in self.get_all()]


class Library(discord.ui.View):
    def __init__(self,
                 sushi,
                 ):
        self.sushi = sushi
        self.page = 1
        super().__init__(timeout=120)

    async def button_update(self):
        for component in self.children:
            if component.custom_id == "library:page":
                component.label = f"{self.page}/{self.max_pages}"
            if self.page <= 1:
                if component.custom_id == "library:max_left" or component.custom_id == "library:left":
                    component.disabled = True
            else:
                if component.custom_id == "library:max_left" or component.custom_id == "library:left":
                    component.disabled = False
            if self.page >= self.max_pages:
                if component.custom_id == "library:max_right" or component.custom_id == "library:right":
                    component.disabled = True
            else:
                if component.custom_id == "library:max_right" or component.custom_id == "library:right":
                    component.disabled = False

    async def update(self, interaction):
        await self.button_update()
        await interaction.message.edit(embed=self.sushi_pages[self.page-1], view=self)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="⏮", custom_id='library:max_left', disabled=True)
    async def max_left(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page = 1
        await self.update(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="◀", custom_id='library:left', disabled=True)
    async def left_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page -= 1
        await self.update(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="📖", custom_id='library:page', disabled=True)
    async def pages(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.update(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="▶", custom_id='library:right')
    async def right_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page += 1
        await self.update(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="⏭", custom_id='library:max_right')
    async def max_right(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page = self.max_pages
        await self.update(interaction)

    @property
    def max_pages(self):
        return len(self.sushi_pages)

    @staticmethod
    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    @property
    def sushi_pages(self):
        pages = []
        sushi_list = self.sushi.get_all()
        chunks = list(self.chunks(sushi_list, 4))
        for chunk in chunks:
            new_embed = discord.Embed(title="Sushi Library")
            for sushi in chunk:
                if sushi['boost'][0] == sushi['boost'][1]:
                    boost = f"{sushi['boost'][0]}% {round(sushi['duration'], 2)} hr(s)"
                else:
                    boost = f"{sushi['boost'][0]}~{sushi['boost'][1]}% {round(sushi['duration'], 2)} hr(s)"
                new_embed.add_field(name=f"{sushi['name']} {boost}", value=f"{sushi['description']}", inline=False)
            pages.append(new_embed)
        return pages


class EconomyStat:
    def __init__(self, database):
        self.database = database
        self.rich = self.database.db["toprich"]
        self.currencies = self.database.money

    async def top_10(self):
        data = list(self.rich.aggregate([{"$sort": {"rank": 1}}]))
        result = []
        list(data)
        for x in range(10):
            try:
                user_id = data[x]["_id"]
                user = self.database.client.get_user(user_id)
                balance = self.currencies.find_one({"_id": user_id})['currency']
                result.append([user, balance])
            except IndexError:
                pass
        if len(result) < 10:
            for x in range(10-len(result)):
                result.append((0, 0))
        return result

    async def get_embed(self):
        top = await self.top_10()
        embed = discord.Embed()
        embed.set_thumbnail(url=top[0][0].avatar.url)
        embed.title = "Richness Ranking 😎"
        i = 1
        for x in top:
            if x[0] != 0:
                if i == 1:
                    embed.add_field(name=f"{x[0]} 👑", value=f"Net Worth : {x[1]} ¥", inline=False)
                else:
                    embed.add_field(name=f"{x[0]}", value=f"Net Worth : {x[1]} ¥", inline=False)
                i += 1
        return embed


class Inventory:
    def __init__(self, client, member):
        self.client = client
        self.database = client.database
        self.sushidata = SushiData(self.database)
        self.economy = EconomyStat(self.database)
        self.inventories = self.database.inventories
        self.money = self.database.money
        self.member = member
        self.id = member.id

    @property
    def currency(self):
        data = self.money.find_one({"_id": self.id})
        if data is None:
            data = {
                "_id": self.id,
                "currency": 0
            }
            self.money.insert_one(data)
        return data["currency"]

    @currency.setter
    def currency(self, value):
        self.money.update_one({"_id": self.id}, {"$set": {"currency": value}})

    @property
    def items(self):
        return self.inventories.find_one({"_id": self.id})

    def get_item(self, key):
        return self.items.get(key)

    def get_price(self, key):
        data = self.sushidata.get_data(key)
        if data is not None:
            return data["price"]

    def get_sell_price(self, key):
        return int(self.get_price(key)*0.75)

    async def add_item(self, key, *, add: int = 1):
        count = self.get_item(key)
        if count == None:
            count = 0
        if count + add < 0:
            return
        if count is None:
            self.inventories.update_one({"_id": self.id}, {"$set": {key: 0}})
        count += add
        self.inventories.update_one({"_id": self.id}, {"$set": {key: count}})


class SellGUI(discord.ui.View):
    def __init__(self, client, member):
        self.user_id = member.id
        self.inventory = Inventory(client, member)
        self.sushi_data = SushiData(client.database)
        super().__init__(timeout=120)
        for item in self.inventory.items:
            if self.inventory.get_item(item) > 0:
              if item in self.sushi_data.sushi_names:
                  self.add_item(Sell(self, item))

    @property
    def embed(self):
        embed = discord.Embed(title="Sell yo stuff")
        embed.description = f"Your current balance : **{self.inventory.currency} ¥**"
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/855770281448439819.png")
        return embed


class Sell(discord.ui.Button):
    def __init__(self, view, sushi):
        self.sushi = sushi
        self._view = view
        super().__init__(style=discord.ButtonStyle.red, label=f"{self.count}x {sushi} - {self.price}¥")

    @property
    def count(self):
        assert self.view is not None
        return self.view.inventory.get_item(self.sushi)

    @property
    def price(self):
        assert self.view is not None
        return self.view.inventory.get_sell_price(self.sushi)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        if interaction.user.id != self.view.user_id:
            return
        if self.count > 0:
            await self.view.inventory.add_item(self.sushi, add=-1)
            self.view.inventory.currency += self.price
        self.label = f"{self.count}x {self.sushi} - {self.price}¥"
        if self.count < 1:
          self.view.remove_item(self)
          await interaction.message.edit(embed=self.view.embed, view=self.view)
          return
        await interaction.message.edit(embed=self.view.embed, view=self.view)


class ShopGUI(discord.ui.View):
    def __init__(self, client, sushi):
        self.sushi_data = SushiData(client.database)
        self.client = client
        super().__init__(timeout=None)
        for key in sushi.keys():
            self.add_item(Buy(self, key, count=sushi[key]))


class Buy(discord.ui.Button):
    def __init__(self,
                 view,
                 sushi,
                 *,
                 count: int = 10):
        self.sushi = sushi
        self._view = view
        self.count = count
        self.price = view.sushi_data.get_data(self.sushi)["price"]
        super().__init__(style=discord.ButtonStyle.green, label=f"{self.count}x {sushi} - {self.price}¥")

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        inventory = Inventory(self.view.client, interaction.user)
        if self.count > 0 and inventory.currency > self.price:
            await inventory.add_item(self.sushi, add=1)
            inventory.currency -= self.price
            self.count -= 1
        self.label = f"{self.count}x {self.sushi} - {self.price}¥"
        if self.count <= 0:
            self.view.remove_item(self)
            await interaction.followup.send(content="Out of stock!", ephemeral=True)
        else:
            await interaction.followup.send(content=f"Your current money is : **{inventory.currency}¥**", ephemeral=True)
        await interaction.message.edit(view=self.view)


class Economy(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.database = client.database
        self.sushi = SushiData(self.database)
        self.iteration = 0
        self.shop.start()

    @tasks.loop(minutes=1.0)
    async def shop(self):
        if self.iteration % 60 == 0:
            self.weedmarket = ShopGUI(self.client,
                                      {
                                          "420 Weed Sushi": 69
                                      }
                                      )
            self.market = ShopGUI(self.client,
                                  {
                                      "Common Sushi": 50,
                                      "Uncommon Sushi": 25,
                                      "Rare Sushi": 15,
                                      "Epic Sushi": 10,
                                      "Rare Sushi": 5,
                                      "Epic Sushi": 3,
                                      "I Love You Sushi": 4,
                                      "Legendary Sushi": 2,
                                      "Ultimate Sushi": 1
                                  }
                                  )
        shop = self.client.get_channel(878510272254468116)
        self.iteration += 1

    @commands.command(description="Show the top richest users.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def rich(self, ctx):
        economy = EconomyStat(self.database)
        embed = await economy.get_embed()
        await ctx.send(embed=embed, delete_after=60)
        pass

    @commands.command(description="Display the library that contains info on all the Sushi.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def library(self, ctx):
        view = Library(self.sushi)
        await view.button_update()
        await ctx.send(embed=view.sushi_pages[0], view=view)

    @commands.command(description="Brings up the selling GUI.")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def sell(self, ctx):
        view = SellGUI(self.client, ctx.author)
        await ctx.send(embed=view.embed, view=view)

    @commands.command(description="Shows the shop where you can buy stuff.")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def buy(self, ctx):
        view = self.market
        embed = discord.Embed(title="Buy sum stuff yo")
        embed.description = f"Buy yo self sum stuff"
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/855770281448439819.png")
        await ctx.send(content="Buy some stuff", view=view, delete_after=60)

    @commands.command(description="Only works during 4:20am, and 4:20pm Manila/Singapore/Beijing Time.")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def blackmarket(self, ctx):
        tz = pytz.timezone('Asia/Tokyo')
        now = datetime.now(tz)
        if ((now.hour == 5 or now.hour == 17) and now.minute == 20) or ctx.author.id == 258247247987212288:
            embed = discord.Embed()
            embed.title = "Black Market"
            embed.description = "Shhhhhh, come, buy quickly!"
            await ctx.send(view=self.weedmarket, embed=embed, delete_after=60)
        else:
            await ctx.send("The blackmarket is not open yet", delete_after=5)
        


def setup(client):
    print("Initiating the Economy System")
    client.add_cog(Economy(client))
