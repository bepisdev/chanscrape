import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import asyncio
import os
import requests
from bs4 import BeautifulSoup
import re
import threading
from pathlib import Path


class ChanScrapeApp(toga.App):
    def startup(self):
        """Initialize the GUI application"""
        self.is_downloading = False
        self.download_thread = None

        # Create main container
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # URL input section
        url_label = toga.Label(
            "4chan Thread URL:",
            style=Pack(padding_bottom=5)
        )
        main_box.add(url_label)

        self.url_input = toga.TextInput(
            placeholder="https://boards.4chan.org/g/thread/12345",
            style=Pack(flex=1, padding_bottom=10)
        )
        main_box.add(self.url_input)

        # Output directory section
        dir_label = toga.Label(
            "Output Directory:",
            style=Pack(padding_bottom=5)
        )
        main_box.add(dir_label)

        dir_box = toga.Box(style=Pack(direction=ROW, padding_bottom=10))

        self.output_dir_input = toga.TextInput(
            value="media",
            style=Pack(flex=1, padding_right=5)
        )
        dir_box.add(self.output_dir_input)

        browse_btn = toga.Button(
            "Browse",
            on_press=self.browse_directory,
            style=Pack(width=80)
        )
        dir_box.add(browse_btn)

        main_box.add(dir_box)

        # Progress section
        progress_label = toga.Label(
            "Progress:",
            style=Pack(padding_top=10, padding_bottom=5)
        )
        main_box.add(progress_label)

        self.progress_bar = toga.ProgressBar(
            max=100,
            style=Pack(flex=1, padding_bottom=5)
        )
        main_box.add(self.progress_bar)

        self.progress_label = toga.Label(
            "Ready",
            style=Pack(padding_bottom=10)
        )
        main_box.add(self.progress_label)

        # Buttons section
        button_box = toga.Box(style=Pack(direction=ROW, padding_bottom=10))

        self.download_btn = toga.Button(
            "Download Media",
            on_press=self.start_download,
            style=Pack(padding_right=5)
        )
        button_box.add(self.download_btn)

        self.cancel_btn = toga.Button(
            "Cancel",
            on_press=self.cancel_download,
            enabled=False,
            style=Pack()
        )
        button_box.add(self.cancel_btn)

        main_box.add(button_box)

        # Log section
        log_label = toga.Label(
            "Log:",
            style=Pack(padding_top=10, padding_bottom=5)
        )
        main_box.add(log_label)

        self.log_text = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, height=200)
        )
        main_box.add(self.log_text)

        # Status bar
        self.status_label = toga.Label(
            "Ready",
            style=Pack(padding_top=10)
        )
        main_box.add(self.status_label)

        # Create main window
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

        self.log("4chan Thread Scraper GUI initialized")

    def log(self, message):
        """Add message to log window"""
        current_text = self.log_text.value or ""
        self.log_text.value = current_text + f"{message}\n"

    async def browse_directory(self, widget):
        """Open directory browser dialog"""
        try:
            folder_path = await self.main_window.select_folder_dialog(
                title="Select Output Directory"
            )
            if folder_path:
                self.output_dir_input.value = str(folder_path)
        except Exception as e:
            self.log(f"Error selecting directory: {str(e)}")

    def validate_url(self, url):
        """Validate if URL is a valid 4chan thread URL"""
        pattern = r'https?://boards\.4chan(?:nel)?\.org/[a-z0-9]+/thread/\d+'
        return re.match(pattern, url) is not None

    def get_media_urls_from_4chan_thread(self, url):
        """Extract media URLs from 4chan thread"""
        try:
            self.log(f"Fetching thread: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            media_urls = []

            for file_info in soup.find_all("div", class_="fileText"):
                file_link = file_info.find("a")
                if file_link is not None:
                    media_urls.append(f"https:{file_link.get('href')}")

            self.log(f"Found {len(media_urls)} media files")
            return media_urls

        except requests.exceptions.RequestException as e:
            self.log(f"Error fetching thread: {str(e)}")
            return []
        except Exception as e:
            self.log(f"Error parsing thread: {str(e)}")
            return []

    def download_media_from_urls(self, urls, output_dir):
        """Download media files from URLs"""
        if not urls:
            self.log("No media URLs to download")
            return

        os.makedirs(output_dir, exist_ok=True)
        total_files = len(urls)

        for i, url in enumerate(urls):
            if not self.is_downloading:  # Check if cancelled
                break

            try:
                filename = url.split("/")[-1]
                output_path = os.path.join(output_dir, filename)

                # Skip if file already exists
                if os.path.exists(output_path):
                    self.log(f"Skipping {filename} (already exists)")
                    progress = ((i + 1) / total_files) * 100
                    self.progress_bar.value = progress
                    self.progress_label.text = f"Skipped {filename} ({i + 1}/{total_files})"
                    continue

                self.log(f"Downloading {filename}...")
                self.progress_label.text = f"Downloading {filename} ({i + 1}/{total_files})"

                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()

                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not self.is_downloading:  # Check if cancelled
                            f.close()
                            os.remove(output_path)  # Remove partial file
                            return
                        f.write(chunk)

                progress = ((i + 1) / total_files) * 100
                self.progress_bar.value = progress
                self.log(f"Downloaded {filename}")

            except requests.exceptions.RequestException as e:
                self.log(f"Error downloading {filename}: {str(e)}")
            except Exception as e:
                self.log(f"Unexpected error downloading {filename}: {str(e)}")

        if self.is_downloading:
            self.log("Download completed!")
            self.progress_label.text = "Download completed!"
        else:
            self.log("Download cancelled")
            self.progress_label.text = "Download cancelled"

    async def start_download(self, widget):
        """Start download process in separate thread"""
        if self.is_downloading:
            return

        url = self.url_input.value.strip()
        output_dir = self.output_dir_input.value.strip()

        # Validate inputs
        if not url:
            await self.main_window.error_dialog("Error", "Please enter a 4chan thread URL")
            return

        if not self.validate_url(url):
            await self.main_window.error_dialog(
                "Error",
                "Please enter a valid 4chan thread URL\n(e.g., https://boards.4chan.org/g/thread/12345)"
            )
            return

        if not output_dir:
            await self.main_window.error_dialog("Error", "Please specify an output directory")
            return

        # Reset progress
        self.progress_bar.value = 0
        self.progress_label.text = "Starting download..."

        # Update UI state
        self.is_downloading = True
        self.download_btn.enabled = False
        self.cancel_btn.enabled = True
        self.status_label.text = "Downloading..."

        # Start download in separate thread
        self.download_thread = threading.Thread(target=self.download_worker, args=(url, output_dir))
        self.download_thread.daemon = True
        self.download_thread.start()

    def download_worker(self, url, output_dir):
        """Worker function for download thread"""
        try:
            # Get media URLs
            media_urls = self.get_media_urls_from_4chan_thread(url)

            if not media_urls:
                # Schedule UI update on main thread
                asyncio.run_coroutine_threadsafe(
                    self.main_window.info_dialog("Warning", "No media files found in the thread"),
                    asyncio.get_event_loop()
                )
                return

            # Download media
            self.download_media_from_urls(media_urls, output_dir)

        except Exception as e:
            self.log(f"Unexpected error: {str(e)}")
            # Schedule UI update on main thread
            asyncio.run_coroutine_threadsafe(
                self.main_window.error_dialog("Error", f"An unexpected error occurred:\n{str(e)}"),
                asyncio.get_event_loop()
            )

        finally:
            # Reset UI state on main thread
            self.download_finished()

    def download_finished(self):
        """Reset UI after download completion"""
        self.is_downloading = False
        self.download_btn.enabled = True
        self.cancel_btn.enabled = False
        self.status_label.text = "Ready"

    async def cancel_download(self, widget):
        """Cancel ongoing download"""
        if self.is_downloading:
            self.is_downloading = False
            self.log("Cancelling download...")
            self.status_label.text = "Cancelling..."


def main():
    return ChanScrapeApp('Chan Scrape', 'org.example.chanscrape')
