import pymongo
import dns
import os
import discord
import random
from datetime import timedelta, datetime
import pytz


class Booster:
    def __init__(self,
                 boosters,
                 *,
                 boost_id: str = None,
                 boost: int = None,
                 duration: timedelta = None,
                 reason: str = None,):
        self.collection = boosters.collection
        self.user = boosters.user
        self.boosters = boosters.boosters
        if boost_id is None:
            self.id = random.randint(1, 10000000000000000)
        else:
            self.id = boost_id
        if boost_id in self.boosters.keys():
            if boost is not None:
                self.boost = boost
            if duration is not None:
                self.end_time = str(self.now + duration)
            if reason is not None:
                self.reason = reason
            boost_data = {
                "boost": self.boost,
                "reason": self.reason,
                "end_time": self.end_time
            }
            self.collection.update_one({"_id": self.id}, {"$set": boost_data})
        else:
            data = self.collection.find_one({"_id": self.id})
            if data is not None:
                self.id = data["_id"]
                self.boost = data["boost"]
                self.reason = data["reason"]
                self.end_time = data["end_time"]
            else:
                if boost is not None:
                    self.boost = boost
                if duration is not None:
                    self.end_time = str(self.now + duration)
                if reason is not None:
                    self.reason = reason
                boost_data = {
                    "_id": self.id,
                    "user_id": self.user.id,
                    "boost": self.boost,
                    "reason": self.reason,
                    "end_time": self.end_time
                }
                self.collection.insert_one(boost_data)
        self.boosters[self.id] = self
        self.check()

    @property
    def now(self):
        tz = pytz.timezone('Asia/Tokyo')
        return datetime.now(tz)

    @property
    def time_left(self):
        actual_end_time = datetime.fromisoformat(self.end_time)
        left = actual_end_time - self.now
        if left.total_seconds() > 0:
            seconds = int(left.total_seconds())
            days = int(seconds / 86400)
            hours = int((seconds / 3600) % 24)
            minutes = int((seconds / 60) % 60)
            seconds = int(seconds % 60)
            return f"{days} day(s) {hours} hr(s) {minutes} min(s) {seconds} sec(s)"
        else:
            self.check()
            return "Expired Booster."

    def check(self):
        actual_end_time = datetime.fromisoformat(self.end_time)
        if self.now > actual_end_time:
            del self.boosters[self.id]
            self.collection.delete_one({"_id": self.id})


class Boosters:
    def __init__(self, user, database):
        self.userobj = user
        self.user = user.member
        self.id = self.user.id
        self.collection = database.booster_collection
        self.boosters = {}
        self.booster = 0
        boosters = self.collection.find({"user_id": self.user.id})
        for boost in boosters:
            Booster(self, boost_id=boost["_id"])
            self.booster += boost["boost"]

    @property
    def booster_list(self):
        return list(self.boosters.values())

    async def get_booster(self):
        self.booster = 0
        for booster in self.booster_list:
            self.booster += booster.boost

    async def add_booster(
            self,
            boost_id: str = None,
            boost: int = 10,
            duration: timedelta = timedelta(hours=1),
            reason: str = "None"
            ):
        Booster(self, boost_id=boost_id, boost=boost, duration=duration, reason=reason)


class User:
    def __init__(self, database, member):
        self.member = member
        self.user_id = member.id
        self.database = database
        self.collection = database.xp_collection
        self.boosters = Boosters(self, database)
        if self.collection.find_one({"_id": self.user_id}) is None:
            print(f"Inserting {self.user_id}")
            user_data = {
                "_id": self.user_id,
                "xp": 0
            }
            self.collection.insert_one(user_data)
            self._xp = 0
        else:
            data = self.collection.find_one({"_id": self.user_id})
            self._xp = data["xp"]
        self.level = 0
        self.xp_current = 0
        self.level_check()

    def level_check(self):
        xp = self.xp
        xp2 = 0
        while xp > 0:
            xp2 = xp
            xp -= self.xp_goal
            if xp > 0:
                self.level += 1
        self.xp_current = int(xp2)

    async def update(self):
        if hasattr(self.member.voice, "channel"):
            if self not in self.database.client.connected:
                self.database.client.connected.append(self)
        else:
            if self in self.database.client.connected:
                self.database.client.connected.remove(self)

    @property
    def xp_goal(self):
        if self.level < 100:
            return (self.level * 100) + 15
        elif self.level < 200:
            return (self.level * 125) + 15
        elif self.level < 300:
            return (self.level * 125) + 15
        else:
            return 999999999999

    @property
    def xp(self):
        return self._xp

    @xp.setter
    def xp(self, value):
        self._xp = value
        self.collection.update_one({"_id": self.user_id}, {"$set": {"xp": value}})

    async def vc_exp(self, value):
        await self.boosters.get_booster()
        booster = self.boosters.booster
        try:
            if self.member.voice.self_mute:
                muted = True
            else:
                muted = False
        except:
            muted = False
        try:
            if self.member.voice.self_deaf:
                return
        except:
            pass
        xp_gain = int(value*((100+booster)/100))
        if muted:
            if xp_gain >= 0:
                xp_gain = int(xp_gain/2)
        self.xp += xp_gain
        self.xp_current += xp_gain
        print(f"{value} > +{booster}% > {xp_gain} Muted : {muted} XP for {self.member}")
        if self.xp_current >= self.xp_goal:
            await self.level_up()
            self.level += 1
            self.xp_current = 0
        elif self.xp_current < 0:
            print("De-level.")
            self.level -= 1
            self.xp_current = self.xp_goal + self.xp_current

    async def add_exp(self, value):
        await self.boosters.get_booster()
        booster = self.boosters.booster
        xp_gain = int(value * ((100 + booster) / 100))
        self.xp += xp_gain
        self.xp_current += xp_gain
        print(f"Adding XP for {self.member} : {value} > +{booster}% > {xp_gain}")
        if self.xp_current >= self.xp_goal:
            await self.level_up()
            self.level += 1
            self.xp_current = 0
        elif self.xp_current < 0:
            print("De-level.")
            self.level -= 1
            self.xp_current = self.xp_goal + self.xp_current

    async def level_up(self):
        levelups = await self.database.client.fetch_channel(841489458900631563)
        embed = discord.Embed()
        embed.set_thumbnail(url=self.member.avatar.url)
        embed.title = f"{self.member} just leveled up to level {self.level+1}!"
        embed.description = "Epic bruh moment"
        await levelups.send(content=self.member.mention, embed=embed)


class Database:
    def __init__(self, client):
        self.client = client
        client = pymongo.MongoClient(os.environ["connection_string"])
        self.db = client["Sushibar"]
        self.xp_collection = self.db["levels"]
        self.booster_collection = self.db["boosters"]
        self.inventories = self.db["inventories"]
        self.users_collection = self.db["users"]
        self.money = self.db["money"]
        self.users = {}

    def get_user(self, member):
        if member.bot:
            return
        try:
            return self.users[str(member.id)]
        except KeyError:
            self.users[str(member.id)] = User(self, member)
            return self.users[str(member.id)]

    def get_ranking(self, member):
        if member.bot:
            return
        try:
            data = self.db["ranking"].find_one({"_id": member.id})
            return data["rank"]+1
        except:
            pass

    def get_member(self, rank):
        try:
            data = self.db["ranking"].find_one({"rank": rank})
            return data["_id"]
        except:
            pass

