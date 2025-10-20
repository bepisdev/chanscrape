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
from concurrent.futures import ThreadPoolExecutor


class ChanScrapeApp(toga.App):
    def __init__(self, *args, **kwargs):
        """Initialize the app with thread-safe components"""
        super().__init__(*args, **kwargs)

        # Initialize thread-safe components first
        self.is_downloading = False
        self.download_thread = None
        self.executor = ThreadPoolExecutor(max_workers=1)

        # Thread-safe communication
        self.download_progress = {'current': 0, 'total': 0, 'status': 'Ready', 'log_messages': []}
        self.download_lock = threading.Lock()

    def startup(self):
        """Initialize the GUI application"""

        # Create main container
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        # URL input section
        url_label = toga.Label(
            "4chan Thread URL:",
            style=Pack(margin_bottom=5)
        )
        main_box.add(url_label)

        self.url_input = toga.TextInput(
            placeholder="https://boards.4chan.org/g/thread/12345",
            style=Pack(flex=1, margin_bottom=10)
        )
        main_box.add(self.url_input)

        # Output directory section
        dir_label = toga.Label(
            "Output Directory:",
            style=Pack(margin_bottom=5)
        )
        main_box.add(dir_label)

        dir_box = toga.Box(style=Pack(direction=ROW, margin_bottom=10))

        self.output_dir_input = toga.TextInput(
            value="media",
            style=Pack(flex=1, margin_right=5)
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
            style=Pack(margin_top=10, margin_bottom=5)
        )
        main_box.add(progress_label)

        self.progress_bar = toga.ProgressBar(
            max=100,
            style=Pack(flex=1, margin_bottom=5)
        )
        main_box.add(self.progress_bar)

        self.progress_label = toga.Label(
            "Ready",
            style=Pack(margin_bottom=10)
        )
        main_box.add(self.progress_label)

        # Buttons section
        button_box = toga.Box(style=Pack(direction=ROW, margin_bottom=10))

        self.download_btn = toga.Button(
            "Download Media",
            on_press=self.start_download,
            style=Pack(margin_right=5)
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
            style=Pack(margin_top=10, margin_bottom=5)
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
            style=Pack(margin_top=10)
        )
        main_box.add(self.status_label)

        # Create main window
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

        self.log_message("4chan Thread Scraper GUI initialized")

        # Start the UI update monitoring using on_running
        self.on_running = self.setup_monitoring

    def log_message(self, message):
        """Add message to thread-safe log buffer"""
        with self.download_lock:
            self.download_progress['log_messages'].append(message)

    def update_ui_from_thread_data(self):
        """Update UI from thread-safe data - called only from main thread"""
        with self.download_lock:
            # Update log
            if self.download_progress['log_messages']:
                current_text = self.log_text.value or ""
                new_messages = '\n'.join(self.download_progress['log_messages'])
                self.log_text.value = current_text + new_messages + '\n'
                self.download_progress['log_messages'].clear()

            # Update progress
            if self.download_progress['total'] > 0:
                progress = (self.download_progress['current'] / self.download_progress['total']) * 100
                self.progress_bar.value = progress

            # Update status
            self.progress_label.text = self.download_progress['status']

    async def setup_monitoring(self, app, **kwargs):
        """Setup the monitoring task"""
        asyncio.create_task(self.monitor_progress())

    async def monitor_progress(self):
        """Monitor download progress and update UI - runs on main thread"""
        while True:
            if self.is_downloading or self.download_progress['log_messages']:
                self.update_ui_from_thread_data()
            await asyncio.sleep(0.1)  # Check every 100ms

    async def browse_directory(self, widget):
        """Open directory browser dialog"""
        try:
            folder_path = await self.main_window.select_folder_dialog(
                title="Select Output Directory"
            )
            if folder_path:
                self.output_dir_input.value = str(folder_path)
        except Exception as e:
            self.log_message(f"Error selecting directory: {str(e)}")

    def validate_url(self, url):
        """Validate if URL is a valid 4chan thread URL"""
        pattern = r'https?://boards\.4chan(?:nel)?\.org/[a-z0-9]+/thread/\d+'
        return re.match(pattern, url) is not None

    def get_media_urls_from_4chan_thread(self, url):
        """Extract media URLs from 4chan thread"""
        try:
            self.log_message(f"Fetching thread: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            media_urls = []

            for file_info in soup.find_all("div", class_="fileText"):
                file_link = file_info.find("a")
                if file_link is not None:
                    media_urls.append(f"https:{file_link.get('href')}")

            self.log_message(f"Found {len(media_urls)} media files")
            return media_urls

        except requests.exceptions.RequestException as e:
            self.log_message(f"Error fetching thread: {str(e)}")
            return []
        except Exception as e:
            self.log_message(f"Error parsing thread: {str(e)}")
            return []

    def download_media_from_urls(self, urls, output_dir):
        """Download media files from URLs - runs in worker thread"""
        if not urls:
            self.log_message("No media URLs to download")
            return

        os.makedirs(output_dir, exist_ok=True)
        total_files = len(urls)

        with self.download_lock:
            self.download_progress['total'] = total_files
            self.download_progress['current'] = 0

        for i, url in enumerate(urls):
            if not self.is_downloading:  # Check if cancelled
                break

            try:
                filename = url.split("/")[-1]
                output_path = os.path.join(output_dir, filename)

                # Skip if file already exists
                if os.path.exists(output_path):
                    self.log_message(f"Skipping {filename} (already exists)")
                    with self.download_lock:
                        self.download_progress['current'] = i + 1
                        self.download_progress['status'] = f"Skipped {filename} ({i + 1}/{total_files})"
                    continue

                self.log_message(f"Downloading {filename}...")
                with self.download_lock:
                    self.download_progress['status'] = f"Downloading {filename} ({i + 1}/{total_files})"

                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()

                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not self.is_downloading:  # Check if cancelled
                            f.close()
                            os.remove(output_path)  # Remove partial file
                            return
                        f.write(chunk)

                with self.download_lock:
                    self.download_progress['current'] = i + 1

                self.log_message(f"Downloaded {filename}")

            except requests.exceptions.RequestException as e:
                self.log_message(f"Error downloading {filename}: {str(e)}")
            except Exception as e:
                self.log_message(f"Unexpected error downloading {filename}: {str(e)}")

        if self.is_downloading:
            self.log_message("Download completed!")
            with self.download_lock:
                self.download_progress['status'] = "Download completed!"
        else:
            self.log_message("Download cancelled")
            with self.download_lock:
                self.download_progress['status'] = "Download cancelled"

    async def start_download(self, widget):
        """Start download process"""
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

        # Start download in thread pool
        loop = asyncio.get_event_loop()
        future = self.executor.submit(self.download_worker, url, output_dir)

        # Monitor the future completion
        asyncio.create_task(self.monitor_download_completion(future))

    async def monitor_download_completion(self, future):
        """Monitor download completion and handle UI updates"""
        try:
            # Wait for completion without blocking
            while not future.done():
                await asyncio.sleep(0.1)

            # Get result (this will raise exception if worker failed)
            result = future.result()

        except Exception as e:
            self.log_message(f"Download error: {str(e)}")
            await self.main_window.error_dialog("Error", f"Download failed:\n{str(e)}")
        finally:
            # Reset UI state
            self.download_finished()

    def download_worker(self, url, output_dir):
        """Worker function for download - runs in thread pool"""
        try:
            # Get media URLs
            media_urls = self.get_media_urls_from_4chan_thread(url)

            if not media_urls:
                self.log_message("No media files found in the thread")
                return

            # Download media
            self.download_media_from_urls(media_urls, output_dir)

        except Exception as e:
            self.log_message(f"Unexpected error: {str(e)}")
            raise  # Re-raise to be handled by monitor

    def download_finished(self):
        """Reset UI after download completion - called from main thread"""
        self.is_downloading = False
        self.download_btn.enabled = True
        self.cancel_btn.enabled = False
        self.status_label.text = "Ready"

    async def cancel_download(self, widget):
        """Cancel ongoing download"""
        if self.is_downloading:
            self.is_downloading = False
            self.log_message("Cancelling download...")
            self.status_label.text = "Cancelling..."


def main():
    return ChanScrapeApp('Chan Scrape', 'org.example.chanscrape')
