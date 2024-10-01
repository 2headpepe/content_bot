import requests
from consts import stable_diffusion_image_path, sd_token

async def generate_image(prompt, negative_prompt):
    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/ultra",
        headers={
            "authorization": f"Bearer {sd_token}",
            "accept": "image/*",
        },
        files={"none": ''},
        data={
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "aspect_ratio": "9:16",
            "seed": 0,
            "output_format": "webp",
        },
    )

    
    if response.status_code == 200:
        with open(stable_diffusion_image_path, 'wb') as file:
            file.write(response.content)
            return 0
    else:
        return response.json()
