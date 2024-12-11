import json
import time
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
from typing import Dict, Optional, Union  # These are only for type hints

# Constants
PLACEHOLDER_URL = "https://via.placeholder.com/1200x1200?text=No+Cover"
MUSICBRAINZ_COVER_API = "https://coverartarchive.org/release/"
SPOTIFY_BLACK = "#191414"
SPOTIFY_WHITE = "#FFFFFF"
RETRIES = 3
TIMEOUT = 10
IMAGE_WIDTH = 200
IMAGE_HEIGHT = 200
PADDING = 20
NUM_COLUMNS = 5
TITLE = "My Year in Review"
FONT_PATH = "tahoma.ttf"
OUTPUT_IMAGE = "year_in_review.png"

FontType = Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]


def fetch_image(
    url: Optional[str],
    album: Optional[str],
    retries: int = RETRIES,
    timeout: int = TIMEOUT,
) -> Image.Image:
    # Split the album into artist and album name
    artist_name, album_name = album.split("|") if album else (None, None)

    if url is None and album is not None:
        # Search for the album on MusicBrainz
        search_url = (
            f"https://musicbrainz.org/ws/2/release/?query=artist:{artist_name}"
            f"+AND+release:{album_name}&fmt=json"
        )
        for attempt in range(retries):
            try:
                response = requests.get(search_url, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                # Find the first result with cover art
                if data["releases"]:
                    mbid = data["releases"][0]["id"]
                    cover_url = f"{MUSICBRAINZ_COVER_API}{mbid}/front"
                    img_response = requests.get(cover_url, timeout=timeout)
                    img_response.raise_for_status()
                    print(
                        f"🎉 Found cover for: {artist_name} - {album_name} on "
                        f"MusicBrainz after {attempt + 1} attempts."
                    )
                    return Image.open(BytesIO(img_response.content))
            except requests.exceptions.RequestException as e:
                # Log the error & delay next retry (if applicable)
                print(
                    f"⚠️ Error fetching MusicBrainz cover art (Attempt "
                    f"{attempt + 1}/{retries}): {e}"
                )

                if attempt < retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
            except Exception as anyE:
                print(
                    f"🔴 Non-HTTP Error fetching MusicBrainz cover art "
                    f"(Attempt {attempt + 1}/{retries}): {anyE}"
                )

    # Fallback to placeholder if no URL found
    if url is None:
        url = PLACEHOLDER_URL

    # Fetch the image from the JSON URL or placeholder
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        if url == PLACEHOLDER_URL:
            print(
                f"❌ Couldn't find cover for: {artist_name} - {album_name}. "
                f"Defaulting to placeholder."
            )
        else:
            print(
                f"🌐 Found cover (URL) inside the JSON for: {artist_name} - "
                f"{album_name}."
            )
        return img
    except Exception as e:
        # Fallback to placeholder on error
        print(f"🆘 Error fetching image: {e}")
        print(
            f"🖼️ Defaulting to placeholder for: {artist_name} - {album_name}."
        )
        return Image.open(
            BytesIO(requests.get(PLACEHOLDER_URL).content)
        )  # Fallback to placeholder on error


# Load the JSON file 'album.json'
def load_album_data() -> Dict[str, str]:
    file_path = os.path.join(os.path.dirname(__file__), "album.json")
    with open(file_path, "r") as f:
        return json.load(f)


def create_review_image(albums: Dict[str, str]) -> None:
    # Calculate grid dimensions
    num_albums = len(albums)
    num_rows = (num_albums + NUM_COLUMNS - 1) // NUM_COLUMNS
    # Calculate final image dimensions
    width = NUM_COLUMNS * IMAGE_WIDTH + (NUM_COLUMNS + 1) * PADDING
    height = (
        num_rows * (IMAGE_HEIGHT + 40) + (num_rows + 1) * PADDING + 120
    )  # 120px for title and 40px for text

    background = Image.new("RGB", (width, height), SPOTIFY_BLACK)
    draw = ImageDraw.Draw(background)

    try:
        font: FontType = ImageFont.truetype(FONT_PATH, 50)
    except IOError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), TITLE, font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(
        ((width - text_width) / 2, 30), TITLE, fill=SPOTIFY_WHITE, font=font
    )

    # Album covers start here
    x, y = PADDING, 120 + PADDING

    try:
        album_font: FontType = ImageFont.truetype(FONT_PATH, 18)
    except IOError:
        album_font = ImageFont.load_default()

    for album, cover_url in albums.items():
        img = fetch_image(cover_url, album)
        img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT))
        background.paste(img, (x, y))

        artist_name, album_name = album.split("|")

        bbox_artist = draw.textbbox((0, 0), artist_name, font=album_font)
        text_width_artist = bbox_artist[2] - bbox_artist[0]
        text_x_artist = x + (IMAGE_WIDTH - text_width_artist) / 2
        text_y_artist = y + IMAGE_HEIGHT + 5
        draw.text(
            (text_x_artist, text_y_artist),
            artist_name,
            fill=SPOTIFY_WHITE,
            font=album_font,
        )

        bbox_album = draw.textbbox((0, 0), album_name, font=album_font)
        text_width_album = bbox_album[2] - bbox[0]
        text_x_album = x + (IMAGE_WIDTH - text_width_album) / 2
        text_y_album = text_y_artist + 20
        draw.text(
            (text_x_album, text_y_album),
            album_name,
            fill=SPOTIFY_WHITE,
            font=album_font,
        )

        # Update the x position
        x += IMAGE_WIDTH + PADDING
        if x + IMAGE_WIDTH + PADDING > width:
            x = PADDING
            # Add the 40px for album name
            y += IMAGE_HEIGHT + PADDING + 40

    # Save the image & show the result
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_IMAGE)
    background.save(output_path)
    background.show()


def main() -> None:
    albums = load_album_data()
    create_review_image(albums)


if __name__ == "__main__":
    main()
