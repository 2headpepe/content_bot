import os
from dotenv import load_dotenv

stable_diffusion_image_path = 'stable_diffusion/result_image/image.webp'
negative_prompt = "NG_deepnegative_v1_75t:(worst quality, low quality:2), monochrome, zombie, overexposure, watermark, text, bad anatomy, abnormal hands, extra hands, extra fingers, fused fingers, distorted arm, extra arms, fused arms, extra legs, missing leg, disembodied leg, detached arm, liquid hand, inverted hand, disembodied limb, loli, oversized head, extra body, completely nude, extra navel, hair between eyes, sketch, duplicate, ugly, huge eyes, logo, worst face, bad and mutated hands, blurry:2.0, horror, geometry, bad_prompt, bad hands, missing fingers, multiple limbs, interlocked fingers, ugly fingers, extra digit, extra hands, fingers, and legs, deformed fingers, long fingers, bad artist, bad hand, squint eyes, badhandv4"
allowed_users = [879672892]

load_dotenv()

bot_token = os.getenv("BOT_TOKEN")
sd_token = os.getenv("SD_TOKEN")
pinterest_login = os.getenv("PINTEREST_LOGIN")
pinterest_password = os.getenv("PINTEREST_PASSWORD")
pinterest_basketball_login = os.getenv("PINTEREST_BASKETBALL_LOGIN")
pinterest_basketball_password = os.getenv("PINTEREST_BASKETBALL_PASSWORD")
tg_channel_id = os.getenv("TG_CHANNEL_ID")
