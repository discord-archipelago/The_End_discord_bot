import discord
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import io
import os
import json
import urllib.request

load_dotenv()

# ══════════════════════════════════════════
#  설정
# ══════════════════════════════════════════
BOT_TOKEN   = os.getenv("BOT_TOKEN")
BG_IMAGE    = "asset/achievement.png"   # 배경 이미지 파일명
FONT_DIR    = "fonts"

# 폰트 목록 (슬래시 커맨드 선택지로 표시됨)
FONTS = {
    "갈무리11 볼드 (기본)": "Galmuri11-Bold.ttf",
    "갈무리14":             "Galmuri14.ttf",
    "갈무리모노9":          "GalmuriMono9.ttf",
    "마인크래프트 (영문)":  "Minecraft.ttf",
    "유니폰트":             "unifont-16.0.02.otf",
}

# 아이콘 Raw URL 베이스
ICON_ITEMS_URL  = "https://raw.githubusercontent.com/Stup1d-discord-bots/minecraft-item-asset-1.21.5/main/items/"
DEFAULT_ICON    = ("grass", "local")   # 기본 아이콘: 잔디블럭

# 업적창 레이아웃 (배경 640x128 기준)
ICON_X, ICON_Y   = 16, 14     # 아이콘 좌상단 위치
ICON_SIZE        = 96          # 아이콘 크기
TITLE_X          = 128         # 텍스트 시작 X (아이콘 오른쪽)
TITLE_Y          = 27          # 머릿글 Y
MAIN_Y           = 67        # 메인 텍스트 Y
TITLE_FONT_SZ    = 28
MAIN_FONT_SZ     = 36

# 머릿글 색상 프리셋
TITLE_COLORS = {
    "노란색 (기본)": (255, 255, 0),
    "흰색":         (255, 255, 255),
    "하늘색":       (85, 255, 255),
    "초록색":       (85, 255, 85),
    "빨간색":       (255, 85, 85),
    "주황색":       (255, 170, 0),
    "분홍색":       (255, 85, 255),
}

# ══════════════════════════════════════════
#  아이템 데이터 로드
# ══════════════════════════════════════════
with open("items.json", encoding="utf-8") as f:
    ITEMS: dict[str, str] = json.load(f)   # {"한글 이름": "english_id"}


# ══════════════════════════════════════════
#  아이콘 다운로드
# ══════════════════════════════════════════
def fetch_icon(item_id: str, folder: str = "items") -> Image.Image | None:
    """아이콘 로드. local이면 asset 폴더에서, 아니면 깃헙에서 다운로드."""
    try:
        if folder == "local":
            img = Image.open(os.path.join("asset", item_id + ".png")).convert("RGBA")
        else:
            url = ICON_ITEMS_URL + item_id + ".png"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")

        # 비율 유지하면서 ICON_SIZE 정사각형에 맞추기 (키우기/줄이기 모두)
        ratio = min(ICON_SIZE / img.width, ICON_SIZE / img.height)
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        img = img.resize((new_w, new_h), Image.NEAREST)
        canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        offset = ((ICON_SIZE - new_w) // 2, (ICON_SIZE - new_h) // 2)
        canvas.paste(img, offset, img)
        return canvas
    except Exception:
        return None


# ══════════════════════════════════════════
#  업적 이미지 생성
# ══════════════════════════════════════════
def create_achievement_image(
    title_text: str,
    main_text: str,
    item_id: str,
    item_folder: str,
    title_color: tuple,
    font_file: str,
) -> io.BytesIO:
    bg = Image.open(BG_IMAGE).convert("RGBA")
    draw = ImageDraw.Draw(bg)

    font_path = os.path.join(FONT_DIR, font_file)
    title_font = ImageFont.truetype(font_path, TITLE_FONT_SZ)
    main_font  = ImageFont.truetype(font_path, MAIN_FONT_SZ)

    icon = fetch_icon(item_id, item_folder)
    if icon:
        bg.paste(icon, (ICON_X, ICON_Y), icon)

    draw.text((TITLE_X, TITLE_Y), title_text, font=title_font, fill=title_color)
    draw.text((TITLE_X, MAIN_Y),  main_text,  font=main_font,  fill=(255, 255, 255))

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ══════════════════════════════════════════
#  봇 & 슬래시 커맨드
# ══════════════════════════════════════════
intents = discord.Intents.default()
client  = discord.Client(intents=intents)
tree    = app_commands.CommandTree(client)


@tree.command(name="업적", description="마크 업적 이미지 생성")
@app_commands.describe(
    머릿글="업적 제목 위에 작게 뜨는 텍스트 (예: 업적 달성!)",
    메인텍스트="업적 이름 (예: 불가능은 없다)",
    아이콘="아이템 아이콘 (한글로 검색)",
    머릿글색="머릿글 색상",
    폰트="사용할 폰트",
)
@app_commands.choices(
    머릿글색=[
        app_commands.Choice(name=k, value=k)
        for k in TITLE_COLORS
    ],
    폰트=[
        app_commands.Choice(name=k, value=v)
        for k, v in FONTS.items()
    ],
)
async def achievement(
    interaction: discord.Interaction,
    머릿글: str = "목표 달성!",
    메인텍스트: str = "불가능은 없다",
    아이콘: str = "잔디",
    머릿글색: str = "노란색 (기본)",
    폰트: str = "unifont-16.0.02.otf",
):
    await interaction.response.defer()
    try:
        # items.json에 없으면 기본값(잔디블럭)
        raw = ITEMS.get(아이콘)
        if raw:
            item_id, item_folder = raw, "items"
        else:
            item_id, item_folder = DEFAULT_ICON  # ("grass", "blocks")

        title_clr = TITLE_COLORS.get(머릿글색, (255, 255, 0))
        buf       = create_achievement_image(머릿글, 메인텍스트, item_id, item_folder, title_clr, 폰트)
        file      = discord.File(buf, filename="achievement.png")
        await interaction.followup.send(file=file)
    except FileNotFoundError as e:
        await interaction.followup.send(f"⚠️ 파일 없음: `{e.filename}`")
    except Exception as e:
        await interaction.followup.send(f"⚠️ 오류: {e}")


# 아이콘 자동완성
@achievement.autocomplete("아이콘")
async def icon_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    results = [
        app_commands.Choice(name=ko, value=ko)
        for ko in ITEMS
        if current.lower() in ko
    ]
    return results[:25]


@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ {client.user} 준비 완료!")


client.run(BOT_TOKEN)
