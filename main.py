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
    name="add_banner",
    description="Add a banner to the Shulert app",
    guild_ids=[guild_id]
)
async def add_banner(ctx,
                     id: Option(str, "Banner ID (unique)", required=True),
                     type: Option(str, "Banner type",
                                  choices=["red", "alert", "warning", "green", "update", "blue", "general", "holiday"],
                                  required=True),
                     persistent: Option(bool, "Banner persistence", required=True),
                     header: Option(str, "Banner header", required=True),
                     content: Option(str, "Banner content", required=True)
                     ):
    file_name = "banners.json"

    header = decode_escapes(header)
    content = decode_escapes(content)

    json_text = {
        "id": id,
        "type": type,
        "persistent": persistent,
        "header": header,
        "content": content
    }

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

    color = discord.Color.default()

    red_types = ["red", "alert", "warning"]
    green_types = ["green", "update"]
    blue_types = ["blue", "general", "holiday"]

    if type in red_types:
        color = discord.Color.from_rgb(229, 62, 62)
    elif type in green_types:
        color = discord.Color.from_rgb(72, 187, 120)
    elif type in blue_types:
        color = discord.Color.from_rgb(83, 132, 214)

    embed = discord.Embed(title=header, description=content, color=color)\
        .set_author(name=id).set_footer(text="Persistent: %s" % persistent)

    await ctx.respond(embed=embed)


bot.run(os.getenv("TOKEN"))
