import os
import requests
from bs4 import BeautifulSoup
import argparse


def get_image_urls_from_4chan_thread(url):
    response = requests.get(url)
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    image_urls = []
    for link in soup.find_all('a'):
        if link.has_attr('href') and link['href'].startswith('//i.4cdn.org/'):
            image_urls.append('https:' + link['href'])
    return image_urls


def download_images_from_urls(urls, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for i, url in enumerate(urls):
        filename = url.split('/')[-1]
        output_path = os.path.join(output_dir, filename)
        response = requests.get(url)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f'Downloaded image {i+1}/{len(urls)}: {filename}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download images from a 4chan thread')
    parser.add_argument('url', type=str, help='URL of the 4chan thread')
    parser.add_argument('-o', '--output_dir', type=str, default='images', help='Output directory for downloaded images')
    args = parser.parse_args()

    image_urls = get_image_urls_from_4chan_thread(args.url)
    output_dir = args.output_dir
    download_images_from_urls(image_urls, output_dir)
