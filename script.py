import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp
import re
import json
import zlib

try:
    import brotli

    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False
    print("Brotli не установлен. Установите: pip install brotli")

API_TOKEN = 'Ваш токен для тг бота'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "📥 Отправьте ссылку на TikTok или Pinterest видео\n\nДля Pinterest поддерживаются:\n• Обычные ссылки\n• Короткие ссылки pin.it\n• Видео и GIF")


@dp.message()
async def handle_url(message: types.Message):
    text = message.text.strip()

    if 'tiktok.com' in text or 'vt.tiktok.com' in text:
        await handle_tiktok(message, text)
    elif 'pinterest.com' in text or 'pin.it' in text:
        await handle_pinterest(message, text)
    else:
        await message.answer("❌ Отправьте ссылку на TikTok или Pinterest")


async def handle_tiktok(message: types.Message, text: str):
    match = re.search(r'https?://[^\s]+', text)
    if not match:
        await message.answer("❌ Неверная TikTok ссылка")
        return

    url = match.group(0)
    await message.answer("⏳ Скачиваю TikTok видео...")

    try:
        api_url = f"https://tikwm.com/api/?url={url}"

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get('data', {}).get('play'):
                        video_url = data['data']['play']
                        await message.answer_video(
                            video_url,
                            caption="✅ TikTok видео скачано!"
                        )
                    else:
                        await message.answer("❌ Не удалось получить TikTok видео")
                else:
                    await message.answer("❌ Ошибка TikTok API")

    except asyncio.TimeoutError:
        await message.answer("❌ Таймаут при загрузке TikTok видео")
    except Exception as e:
        await message.answer(f"❌ Ошибка TikTok: {str(e)}")


async def handle_pinterest(message: types.Message, text: str):
    match = re.search(r'https?://[^\s]+', text)
    if not match:
        await message.answer("❌ Неверная Pinterest ссылка")
        return

    url = match.group(0)
    await message.answer("⏳ Скачиваю Pinterest видео...")

    try:
        methods = [
            download_pinterest_method1,
            download_pinterest_method2,
            download_pinterest_method3,
            download_pinterest_method_simple,
        ]

        for i, method in enumerate(methods, 1):
            try:
                print(f"Пробуем метод {i}...")
                video_url = await method(url)
                if video_url:
                    print(f"Метод {i} успешен!")
                    await message.answer_video(
                        video_url,
                        caption=f"✅ Pinterest видео скачано!"
                    )
                    return
            except Exception as e:
                print(f"Метод {i} не сработал: {e}")
                continue

        await message.answer("❌ Не удалось скачать видео. Попробуйте другую ссылку.")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


async def download_pinterest_method1(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            service_url = "https://pinterest-video-downloader.p.rapidapi.com/api/pinterest"
            headers = {
                'X-RapidAPI-Key': 'demo-key-only-for-testing',
                'X-RapidAPI-Host': 'pinterest-video-downloader.p.rapidapi.com',
                'User-Agent': 'Mozilla/5.0'
            }
            params = {'url': url}

            async with session.get(service_url, headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('url'):
                        return data['url']
        except:
            pass

        return None


async def download_pinterest_method2(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            service_url = "https://social-download-all-in-one.p.rapidapi.com/v1/social/pinterest"
            headers = {
                'X-RapidAPI-Key': 'demo-key',  # Демо-ключ
                'X-RapidAPI-Host': 'social-download-all-in-one.p.rapidapi.com',
                'User-Agent': 'Mozilla/5.0'
            }
            params = {'url': url}

            async with session.get(service_url, headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('video_url'):
                        return data['video_url']
        except:
            pass

        return None


async def download_pinterest_method3(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        try:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()

                    patterns = [
                        r'https://[^"]+\.pinimg\.com/videos/[^"]+\.mp4[^"]*',
                        r'https://[^"]+\.pinimg\.com/originals/[^"]+\.mp4[^"]*',
                        r'"videoUrl":"([^"]+)"',
                        r'"url":"(https://[^"]+\.mp4)"',
                        r'src="(https://[^"]+\.mp4)"',
                    ]

                    for pattern in patterns:
                        matches = re.findall(pattern, html)
                        for match in matches:
                            video_url = match if isinstance(match, str) else match[0]
                            video_url = video_url.replace('\\/', '/')
                            if await check_video_url(video_url, session):
                                return video_url

        except Exception as e:
            print(f"Method 3 error: {e}")

        return None


async def download_pinterest_method_simple(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        services = [
            {
                'url': 'https://pinterestdl.com/api/download',
                'method': 'POST',
                'data': {'url': url}
            },
            {
                'url': 'https://pindownloader.com/api/download',
                'method': 'POST',
                'data': {'url': url}
            },
            {
                'url': 'https://pinvid.net/api/download',
                'method': 'POST',
                'data': {'url': url}
            },
            {
                'url': f'https://api.savefrom.net/api/convert',
                'method': 'POST',
                'data': {'url': url, 'format': 'mp4'}
            },
        ]

        for service in services:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0',
                    'Content-Type': 'application/json'
                }

                if service['method'] == 'POST':
                    async with session.post(service['url'], json=service['data'], headers=headers,
                                            timeout=10) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                if data.get('video_url') or data.get('url') or data.get('download_url'):
                                    return data.get('video_url') or data.get('url') or data.get('download_url')
                            except:
                                text = await response.text()
                                video_match = re.search(r'https://[^"]+\.mp4', text)
                                if video_match:
                                    return video_match.group(0)
                else:
                    async with session.get(service['url'], headers=headers, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('video_url'):
                                return data['video_url']
            except:
                continue

        return None


async def check_video_url(url: str, session: aiohttp.ClientSession) -> bool:
    if not url or not url.startswith('http'):
        return False

    video_extensions = ['.mp4', '.mov', '.webm', '.avi', '.mkv']
    if any(url.lower().endswith(ext) for ext in video_extensions):
        return True

    video_keywords = ['video', 'pinimg.com/videos', 'mp4', 'mov']
    if any(keyword in url.lower() for keyword in video_keywords):
        return True

    try:
        async with session.head(url, timeout=3, allow_redirects=True) as response:
            content_type = response.headers.get('Content-Type', '')
            return 'video' in content_type.lower() or 'mp4' in content_type.lower()
    except:
        return False


async def download_pinterest_direct(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            pin_id = extract_pin_id(url)
            if pin_id:
                video_urls = [
                    f"https://v.pinimg.com/videos/mc/{pin_id}.mp4",
                    f"https://v.pinimg.com/videos/hd/{pin_id}.mp4",
                    f"https://v.pinimg.com/videos/{pin_id}.mp4",
                ]

                for video_url in video_urls:
                    if await check_video_url(video_url, session):
                        return video_url
        except:
            pass

        return None


def extract_pin_id(url: str) -> str:
    patterns = [
        r'/pin/(\d+)',
        r'pin/(\d+)',
        r'id=(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


async def main():
    print("Video Downloader Bot запущен")
    print("Поддерживаемые платформы: TikTok, Pinterest")
    await dp.start_polling(bot)


if __name__ == '__main__':

    asyncio.run(main())
