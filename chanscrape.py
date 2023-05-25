import os
import requests
from bs4 import BeautifulSoup
import argparse


def get_media_urls_from_4chan_thread(url):
    response = requests.get(url)
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    media_urls = []
    for file_info in soup.find_all("div", class_="fileText"):
        file_link = file_info.find("a")
        if file_link is not None:
            media_urls.append("https:" + file_link.get("href"))
    return media_urls


def download_media_from_urls(urls, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for i, url in enumerate(urls, start=1):
        filename = url.split("/")[-1]
        output_path = os.path.join(output_dir, filename)
        response = requests.get(url)
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"Downloaded media {i}/{len(urls)}: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download media (images, GIFs, WEBMs) from a 4chan thread")
    parser.add_argument("url", type=str, help="URL of the 4chan thread")
    parser.add_argument("-o", "--output_dir", type=str, default="media", help="Output directory for downloaded media")
    args = parser.parse_args()

    media_urls = get_media_urls_from_4chan_thread(args.url)
    output_dir = args.output_dir
    download_media_from_urls(media_urls, output_dir)
