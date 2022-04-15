import asyncio
import codecs
import json
import os
import re

import discord
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import Option
from dotenv import load_dotenv
from pytz import utc

from datetime import date

from quart import Quart
from quart import request

load_dotenv()

app = Quart(__name__)
bot = discord.Bot()

guild_id = os.getenv("GUILD_ID")
channel_id = os.getenv("CHANNEL_ID")

red_types = ["red", "alert", "warning"]
green_types = ["green", "update"]
blue_types = ["blue", "general", "holiday"]

red = "#E53E3E"
green = "#48BB78"
blue = "#5384D6"

ESCAPE_SEQUENCE_RE = re.compile(r'''
    ( \\U........      # 8-digit hex escapes
    | \\u....          # 4-digit hex escapes
    | \\x..            # 2-digit hex escapes
    | \\[0-7]{1,3}     # Octal escapes
    | \\N\{[^}]+\}     # Unicode characters by name
    | \\[\\'"abfnrtv]  # Single-character escapes
    )''', re.UNICODE | re.VERBOSE)

hebcal_api = "https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&lg=a"

holiday_banners_list = []

class Shul:
    def __init__(self, name, rabbi, nusach, affiliation, email, phone, website, address):
        super().__init__()
        self.name = name
        self.rabbi = rabbi
        self.nusach = nusach
        self.affiliation = affiliation
        self.email = email
        self.phone = phone
        self.website = website
        self.address = address


def decode_escapes(s):
    if s is not None:
        def decode_match(match):
            return codecs.decode(match.group(0), 'unicode-escape')

        return ESCAPE_SEQUENCE_RE.sub(decode_match, s)
    else:
        return None


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


@bot.slash_command(
    name="add_banner_v2",
    description="Add a banner to the Shulert app V2",
    guild_ids=[guild_id]
)
async def add_banner_v2(ctx,
                        id: Option(str, "Banner ID (unique)", required=True),
                        type: Option(str, "Banner type",
                                     choices=
                                     ["red", "alert", "warning", "green", "update", "blue", "general", "holiday"],
                                     required=True),
                        persistent: Option(bool, "Banner persistence", required=True),
                        header: Option(str, "Banner header", required=True),
                        content: Option(str, "Banner content", required=True),
                        enabled: Option(bool, "Banner enabled state", default=True)
                        ):
    header = decode_escapes(header)
    content = decode_escapes(content)

    json_text = {
        "id": id,
        "type": type,
        "persistent": persistent,
        "header": header,
        "content": content
    }

    if not enabled:
        json_text["enabled"] = enabled

    json_text = add_edit_banner_json(json_text, "V2")

    embed = discord_embed(id=json_text["id"], color=json_text["type"], content=json_text["content"],
                          enabled=json_text.get("enabled", True), header=json_text["header"],
                          persistent=json_text["persistent"])
    await ctx.respond(embed=embed)


@bot.slash_command(
    name="edit_banner_v2",
    description="Edit a banner in the Shulert app V2",
    guild_ids=[guild_id]
)
async def edit_banner_v2(ctx,
                         old_id: Option(str, "Old Banner ID (unique)", required=True),
                         id: Option(str, "Banner ID (unique)", required=False),
                         type: Option(str, "Banner type",
                                      choices=
                                      ["red", "alert", "warning", "green", "update", "blue", "general", "holiday"],
                                      required=False),
                         persistent: Option(bool, "Banner persistence", required=False),
                         header: Option(str, "Banner header", required=False),
                         content: Option(str, "Banner content", required=False),
                         enabled: Option(bool, "Banner enabled state", default=True)
                         ):
    header = decode_escapes(header)
    content = decode_escapes(content)

    json_text = {
        "id": id,
        "type": type,
        "persistent": persistent,
        "header": header,
        "content": content
    }

    if not enabled:
        json_text["enabled"] = enabled

    json_text = add_edit_banner_json(json_text, "V2", old_id)

    embed = discord_embed(id=json_text["id"], color=json_text["type"], content=json_text["content"],
                          enabled=json_text.get("enabled", True), header=json_text["header"],
                          persistent=json_text["persistent"])
    await ctx.respond(embed=embed)


@bot.slash_command(
    name="edit_banner_v1",
    description="Edit a banner in the Shulert app V1",
    guild_ids=[guild_id]
)
async def edit_banner_v1(ctx,
                         old_id: Option(str, "Old Banner ID (unique)", required=True),
                         id: Option(str, "Banner ID (unique)", required=False),
                         content: Option(str, "Banner content", required=False),
                         type: Option(str, "Banner type",
                                      choices=
                                      ["red", "alert", "warning", "green", "update", "blue", "general", "holiday"],
                                      required=False),
                         enabled: Option(bool, "Banner enabled state", default=True)
                         ):
    content = decode_escapes(content)

    color = blue
    if type in red_types:
        color = red
    elif type in green_types:
        color = green
    elif type in blue_types:
        color = blue

    json_text = {
        "id": id,
        "title": content,
        "style": {
            "color": color,
            "fontWeight": "bold",
            "textAlign": "center",
            "fontSize": 16
        }
    }

    if not enabled:
        json_text["enabled"] = enabled

    json_text = add_edit_banner_json(json_text, "V1", old_id)

    embed = discord_embed(id=json_text["id"], color=json_text["style"]["color"], content=json_text["title"],
                          enabled=json_text.get("enabled", True), version="V1")
    await ctx.respond(embed=embed)


@bot.slash_command(
    name="add_banner_v1",
    description="Add a banner to the Shulert app V1",
    guild_ids=[guild_id]
)
async def add_banner_v1(ctx,
                        id: Option(str, "Banner ID (unique)", required=True),
                        content: Option(str, "Banner content", required=True),
                        type: Option(str, "Banner type",
                                     choices=
                                     ["red", "alert", "warning", "green", "update", "blue", "general", "holiday"],
                                     required=True),
                        enabled: Option(bool, "Banner ", default=True)
                        ):
    content = decode_escapes(content)

    color = blue
    if type in red_types:
        color = red
    elif type in green_types:
        color = green
    elif type in blue_types:
        color = blue

    json_text = {
        "id": id,
        "title": content,
        "style": {
            "color": color,
            "fontWeight": "bold",
            "textAlign": "center",
            "fontSize": 16
        }
    }

    if not enabled:
        json_text["enabled"] = enabled

    json_text = add_edit_banner_json(json_text, "V1")

    embed = discord_embed(id=json_text["id"], color=json_text["style"]["color"], content=json_text["title"],
                          enabled=json_text.get("enabled", True), version="V1")
    await ctx.respond(embed=embed)


class Modify(discord.ui.View):
    def __init__(self, version, banner, view_banners_message: discord.Message):
        super().__init__()
        self.version = version
        self.banner = banner
        self.view_banners_message = view_banners_message

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.stop()

        await interaction.message.reply(embed=discord.Embed(title="Deleted `%s`" % self.banner["id"]))
        await interaction.message.delete()

        delete_banner(self.version, self.banner)

        response = view_banners_embed(self.version)
        await self.view_banners_message.edit(content=response[0], view=response[1])


class BannerButton(discord.ui.Button):
    def __init__(self, banner, index, version):
        self.banner = banner
        self.version = version
        super().__init__(
            label=index,
            style=discord.enums.ButtonStyle.primary,
            custom_id=banner["id"],
        )

    async def callback(self, interaction: discord.Interaction):
        id = self.banner["id"]

        if self.version == "V2":
            color = self.banner["type"]
            content = self.banner["content"]
        else:
            color = self.banner["style"]["color"]
            content = self.banner["title"]

        enabled = self.banner.get("enabled", True)
        header = self.banner.get("header", "")
        persistent = self.banner.get("persistent", True)

        view = Modify(self.version, self.banner, interaction.message)
        embed = discord_embed(id, color, content, enabled, header, persistent)
        await interaction.response.send_message(embed=embed, view=view)


class ShulView(discord.ui.View):
    def __init__(self, shul):
        super().__init__()
        self.shul = shul

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.stop()

        await interaction.message.reply(embed=discord.Embed(title="Approved `%s`" % self.shul.name))

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
    async def deny(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.stop()

        await interaction.message.reply(embed=discord.Embed(title="Denied `%s`" % self.shul.name))


@bot.slash_command(
    name="view_banners",
    description="View the banners added to the Shulert app",
    guild_ids=[guild_id]
)
async def view_banners(ctx,
                       version: Option(str, "Banner version",
                                       choices=
                                       ["V2", "V1"],
                                       required=True)):
    response = view_banners_embed(version)

    await ctx.respond(response[0], view=response[1])


def holiday_banners():
    holidays = {
        "rosh hashana": {
            "header": "Happy Rosh Hashanah!",
            "content": "Wishing you a happy, healthy and sweet New Year!"
        },
        "sukkos": {
            "header": "Happy Succos!",
            "content": "Wishing you a happy and healthy Succos!"
        },
        "chanukah": {
            "header": "Happy Chanukah!",
            "content": "Wishing you a happy and healthy Chanukah!"
        },
        "tu bishvat": {
            "header": "Happy Tu B'Shvat!",
            "content": "Wishing you a happy and healthy Tu B'Shvat!"
        },
        "purim": {
            "header": "Happy Purim!",
            "content": "Wishing you a happy and healthy Purim!"
        },
        "pesach": {
            "header": "Happy Pesach!",
            "content": "Wishing you a happy and healthy Pesach!"
        },
        "lag baomer": {
            "header": "Happy Lag B'Omer!",
            "content": "Wishing you a happy and healthy Lag B'Omer!"
        },
        "shavuos": {
            "header": "Happy Shavuos!",
            "content": "Wishing you a happy and healthy Shavuos!"
        }
    }

    today = date.today()
    req = requests.get(hebcal_api + f"&start={today}&end={today}")
    res = req.json()

    if len(res["items"]) >= 1:
        item = res["items"][0]
        title = item["title"].lower()

        holiday = None
        for key in holidays.keys():
            if key in title:
                holiday = holidays[key]

        if holiday is not None:
            header = decode_escapes(holiday["header"])
            content = decode_escapes(holiday["content"])
            underscore_title = title.replace(" ", "_")
            id = f"{underscore_title}_{today.year}"

            json_text = {
                "id": id,
                "type": "holiday",
                "persistent": True,
                "header": header,
                "content": content
            }

            if id not in holiday_banners_list:
                add_edit_banner_json(json_text, "V2")
                holiday_banners_list.append(title)

    for holiday_banner in holiday_banners_list:
        titles = [x["title"].lower() for x in res["items"]]
        if holiday_banner not in titles:
            underscore_title = holiday_banner.replace(" ", "_")
            id = f"{underscore_title}_{today.year}"

            for banner in get_banners("V2")[1]:
                if banner["id"] == id:
                    delete_banner("V2", banner)


def view_banners_embed(version):
    banners = get_banners(version)[1]
    if len(banners) >= 1:
        view = discord.ui.View(timeout=None)

        banner_ids = []
        for index, banner in enumerate(banners):
            banner_ids.append("[%s] %s" % (index, banner["id"]))
            view.add_item(BannerButton(banner, index, version))

        banner_message = "```\n%s```" % '\n'.join(banner_ids)
        return banner_message, view
    else:
        view = discord.ui.View()
        banner_message = "```\nNo banners```"
        return banner_message, view


def get_banners(version):
    if version == "V2":
        file_name = os.getenv("V2_FILE")
    else:
        file_name = os.getenv("V1_FILE")

    if os.path.isfile(file_name):
        with open(file_name, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    else:
        data = {
            "banners": []
        }

    return data, data["banners"]


def delete_banner(version, banner):
    banners = get_banners(version)
    banners[1].remove(banner)

    if version == "V2":
        file_name = os.getenv("V2_FILE")
    else:
        file_name = os.getenv("V1_FILE")

    with open(file_name, "w+", encoding="utf-8") as fp:
        json.dump(banners[0], fp, indent=4)


def add_edit_banner_json(json_text, version, old_id=None):
    banners = get_banners(version)
    if old_id is not None:
        banner_old = None
        banner_index = -1
        for index, banner in enumerate(banners[1]):
            if banner["id"] == old_id:
                banner_index = index
                banner_old = banner

        if json_text["id"] is None:
            json_text["id"] = banner_old["id"]

        if version == "V2":
            if json_text["type"] is None:
                json_text["type"] = banner_old["type"]

            if json_text["persistent"] is None:
                json_text["persistent"] = banner_old["persistent"]

            if json_text["header"] is None:
                json_text["header"] = banner_old["header"]

            if json_text["content"] is None:
                json_text["content"] = banner_old["content"]
        else:
            if json_text["title"] is None:
                json_text["title"] = banner_old["title"]

            if json_text["style"]["color"] is None:
                json_text["style"]["color"] = banner_old["style"]["color"]

        banners[1][banner_index] = json_text
    else:
        banners[1].append(json_text)

    if version == "V2":
        file_name = os.getenv("V2_FILE")
    else:
        file_name = os.getenv("V1_FILE")

    with open(file_name, "w+", encoding="utf-8") as fp:
        json.dump(banners[0], fp, indent=4)

    return json_text


def discord_color(type, version) -> discord.Color:
    color = discord.Color.default()

    if type in red_types or type == red:
        color = discord.Color.from_rgb(229, 62, 62)
    elif type in green_types or type == green:
        color = discord.Color.from_rgb(72, 187, 120)
    elif type in blue_types or type == blue:
        color = discord.Color.from_rgb(83, 132, 214)

    return color


@app.route("/shul/add", methods=["POST"])
async def add_shul_handle():
    data = await request.get_json()
    name = data.get('name')
    rabbi = data.get('rabbi')
    nusach = data.get('nusach')
    affiliation = data.get('affiliation')
    email = data.get('email')
    phone = data.get('phone')
    website = data.get('website')
    address = data.get('address')

    view = ShulView(Shul(name, rabbi, nusach, affiliation, email, phone, website, address))
    embed = shul_discord_embed(name, nusach, affiliation, address, rabbi, email, phone, website)
    await bot.get_channel(int(channel_id)).send(embed=embed, view=view)
    return "Embed Sent Successfully"


def shul_discord_embed(name, nusach, affiliation, address, rabbi, email, phone, website):
    embed = discord.Embed(title=name, description=address) \
        .add_field(name="Rabbi", value=rabbi, inline=False) \
        .add_field(name="Email", value=email, inline=False) \
        .add_field(name="Phone", value=phone, inline=False) \
        .add_field(name="Website", value=website, inline=False) \
        .set_footer(text="Nusach: %s, Affiliation: %s" % (nusach, affiliation))
    return embed


def discord_embed(id, color, content, enabled, header="", persistent=True, version = "V2"):
    color = discord_color(color, version)
    embed = discord.Embed(title=header, description=content, color=color) \
        .set_author(name=id).set_footer(text="Persistent: %s, Enabled: %s" % (persistent, enabled))
    return embed


if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.configure(timezone=utc)
    scheduler.add_job(holiday_banners, 'cron', hour=0)
    scheduler.start()

    try:
        bot.loop.create_task(app.run_task(port=int(os.getenv("PORT"))))
        bot.run(os.getenv("TOKEN"))
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
