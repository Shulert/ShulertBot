import os

import discord
from discord import Option
from dotenv import load_dotenv
import json
import re
import codecs

load_dotenv()

bot = discord.Bot()

guild_id = os.getenv("GUILD_ID")

red_types = ["red", "alert", "warning"]
green_types = ["green", "update"]
blue_types = ["blue", "general", "holiday"]

ESCAPE_SEQUENCE_RE = re.compile(r'''
    ( \\U........      # 8-digit hex escapes
    | \\u....          # 4-digit hex escapes
    | \\x..            # 2-digit hex escapes
    | \\[0-7]{1,3}     # Octal escapes
    | \\N\{[^}]+\}     # Unicode characters by name
    | \\[\\'"abfnrtv]  # Single-character escapes
    )''', re.UNICODE | re.VERBOSE)


def decode_escapes(s):
    def decode_match(match):
        return codecs.decode(match.group(0), 'unicode-escape')

    return ESCAPE_SEQUENCE_RE.sub(decode_match, s)


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
                        enabled: Option(bool, "Banner ", default=True)
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

    file_name = os.getenv("V2_FILE")
    add_banner_json(json_text, file_name)

    color = discord_color(type)
    embed = discord.Embed(title=header, description=content, color=color) \
        .set_author(name=id).set_footer(text="Persistent: %s, Enabled: %s" % (persistent, enabled))

    await ctx.respond(embed=embed)


@bot.slash_command(
    name="add_banner_v1",
    description="Add a banner to the Shulert app V1",
    guild_ids=[guild_id]
)
async def add_banner_v2(ctx,
                        content: Option(str, "Banner content", required=True),
                        type: Option(str, "Banner type",
                                     choices=
                                     ["red", "alert", "warning", "green", "update", "blue", "general", "holiday"],
                                     required=True),
                        enabled: Option(bool, "Banner ", default=True)
                        ):
    content = decode_escapes(content)

    color = "#003171"
    if type in red_types:
        color = "#E53E3E"
    elif type in green_types:
        color = "#48BB78"
    elif type in blue_types:
        color = "#5384D6"

    json_text = {
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

    file_name = os.getenv("V1_FILE")
    add_banner_json(json_text, file_name)

    embed_color = discord_color(type)
    embed = discord.Embed(description=content, color=embed_color).set_footer(text="Enabled: %s" % enabled)

    await ctx.respond(embed=embed)


def add_banner_json(json_text, file_name):
    if os.path.isfile(file_name):
        with open(file_name, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        data["banners"].append(json_text)

    else:
        data = {
            "banners": []
        }

        data["banners"].append(json_text)

    with open(file_name, "w+", encoding="utf-8") as fp:
        json.dump(data, fp, indent=4)


def discord_color(type) -> discord.Color:
    color = discord.Color.default()

    if type in red_types:
        color = discord.Color.from_rgb(229, 62, 62)
    elif type in green_types:
        color = discord.Color.from_rgb(72, 187, 120)
    elif type in blue_types:
        color = discord.Color.from_rgb(83, 132, 214)

    return color


bot.run(os.getenv("TOKEN"))
