import json
import time
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

# Constants
PLACEHOLDER_URL = "https://via.placeholder.com/1200x1200?text=No+Cover"
MUSICBRAINZ_COVER_API = "https://coverartarchive.org/release/"
SPOTIFY_BLACK = "#191414"
SPOTIFY_WHITE = "#FFFFFF"

def fetch_image(url, album=None, retries=3, timeout=10):
    try:
        # Split the album into artist and album name
        artist_name, album_name = album.split('|')
        
        if url is None and album is not None:
            # Search for the album on MusicBrainz
            search_url = f"https://musicbrainz.org/ws/2/release/?query=artist:{artist_name}+AND+release:{album_name}&fmt=json"
            
            for attempt in range(retries):
                try:
                    response = requests.get(search_url, timeout=timeout)
                    response.raise_for_status()
                    data = response.json()

                    # Find the first result with cover art
                    if data['releases']:
                        mbid = data['releases'][0]['id']
                        cover_url = f"{MUSICBRAINZ_COVER_API}{mbid}/front"
                        img_response = requests.get(cover_url, timeout=timeout)
                        img_response.raise_for_status()
                        
                        if img_response.status_code == 200:
                            print(f"Found cover for: {artist_name} - {album_name} on MusicBrainz after {attempt + 1} attempts.")
                            return Image.open(BytesIO(img_response.content))
                        
                except requests.exceptions.RequestException as e:
                    # Log the error & delay next retry (if applicable)
                    print(f"Error fetching MusicBrainz cover art (Attempt {attempt + 1}/{retries}): {e}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff

                except Exception as anyE:
                    print(f"Non-HTTP Error fetching MusicBrainz cover art (Attempt {attempt + 1}/{retries}): {anyE}")


        # Fallback to placeholder if no URL found
        if url is None:
            url = PLACEHOLDER_URL
        
        # Fetch the image from the JSON URL or placeholder
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        if url == PLACEHOLDER_URL:
            print(f"Couldn't find cover for: {artist_name} - {album_name}. Defaulting to placeholder.")
        else:
            print(f"Found cover (URL) inside the JSON for: {artist_name} - {album_name}.")
        return img

    except Exception as e:
        print(f"Error fetching image: {e}")
        print(f"Defaulting to placeholder for: {artist_name} - {album_name}.")
        return Image.open(BytesIO(requests.get(PLACEHOLDER_URL).content))  # Fallback to placeholder on error

# Load the JSON file 'album.json'
def load_album_data():
    file_path = os.path.join(os.path.dirname(__file__), 'album.json')
    with open(file_path, 'r') as f:
        return json.load(f)

def create_review_image(albums):
    image_width = 200
    image_height = 200
    padding = 20

    # Calculate grid dimensions
    num_albums = len(albums)
    num_columns = 5  # Adjust this based on how many columns you want
    num_rows = (num_albums + num_columns - 1) // num_columns

    # Calculate final image height
    width = num_columns * image_width + (num_columns + 1) * padding
    height = num_rows * (image_height + 40) + (num_rows + 1) * padding + 120  # 120px for title and extra space for text

    background = Image.new("RGB", (width, height), SPOTIFY_BLACK)
    draw = ImageDraw.Draw(background)

    try:
        font = ImageFont.truetype("tahoma.ttf", 50)
    except IOError:
        font = ImageFont.load_default()

    title = "My Year in Review"
    bbox = draw.textbbox((0, 0), title, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw.text(((width - text_width) / 2, 30), title, fill=SPOTIFY_WHITE, font=font)

    # Album covers start
    x = padding
    y = 120 + padding

    try:
        album_font = ImageFont.truetype("tahoma.ttf", 18)
    except IOError:
        album_font = ImageFont.load_default()

    for album, cover_url in albums.items():
        img = fetch_image(cover_url, album)
        img = img.resize((image_width, image_height))
        
        background.paste(img, (x, y))

        artist_name, album_name = album.split('|')

        bbox_artist = draw.textbbox((0, 0), artist_name, font=album_font)
        text_width_artist = bbox_artist[2] - bbox_artist[0]
        text_x_artist = x + (image_width - text_width_artist) / 2
        text_y_artist = y + image_height + 5 
        draw.text((text_x_artist, text_y_artist), artist_name, fill=SPOTIFY_WHITE, font=album_font)

        bbox_album = draw.textbbox((0, 0), album_name, font=album_font)
        text_width_album = bbox_album[2] - bbox_album[0]
        text_x_album = x + (image_width - text_width_album) / 2 
        text_y_album = text_y_artist + 20
        draw.text((text_x_album, text_y_album), album_name, fill=SPOTIFY_WHITE, font=album_font)

        # Update the x position
        x += image_width + padding
        
        if x + image_width + padding > width:
            x = padding
            y += image_height + padding + 40  # Add extra space for album name

    # Save the image & show the result
    output_path = os.path.join(os.path.dirname(__file__), "year_in_review.png")
    background.save(output_path)
    background.show()

def main():
    albums = load_album_data()
    create_review_image(albums)

if __name__ == "__main__":
    main()