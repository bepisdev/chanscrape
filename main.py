import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

class ChanScrapeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("4chan Thread Scraper")
        self.root.geometry("600x500")

        # Variables
        self.download_thread = None
        self.is_downloading = False

        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # URL input section
        ttk.Label(main_frame, text="4chan Thread URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=70)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Output directory section
        ttk.Label(main_frame, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))

        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_frame.columnconfigure(0, weight=1)

        self.output_dir_var = tk.StringVar(value="media")
        dir_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var)
        dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        browse_btn = ttk.Button(dir_frame, text="Browse", command=self.browse_directory)
        browse_btn.grid(row=0, column=1)

        # Progress section
        ttk.Label(main_frame, text="Progress:").grid(row=4, column=0, sticky=tk.W, pady=(10, 5))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        self.progress_label = ttk.Label(main_frame, text="Ready")
        self.progress_label.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # Buttons section
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=(0, 10))

        self.download_btn = ttk.Button(button_frame, text="Download Media", command=self.start_download)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel_download, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT)

        # Log section
        ttk.Label(main_frame, text="Log:").grid(row=8, column=0, sticky=tk.W, pady=(10, 5))

        self.log_text = scrolledtext.ScrolledText(main_frame, height=10, width=70)
        self.log_text.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(9, weight=1)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E))

        # Bind Enter key to URL entry
        url_entry.bind('<Return>', lambda event: self.start_download())

        self.log("4chan Thread Scraper GUI initialized")

    def log(self, message):
        """Add message to log window"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def browse_directory(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)

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
                    self.progress_var.set(progress)
                    self.progress_label.config(text=f"Skipped {filename} ({i + 1}/{total_files})")
                    continue

                self.log(f"Downloading {filename}...")
                self.progress_label.config(text=f"Downloading {filename} ({i + 1}/{total_files})")

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
                self.progress_var.set(progress)
                self.log(f"Downloaded {filename}")

            except requests.exceptions.RequestException as e:
                self.log(f"Error downloading {filename}: {str(e)}")
            except Exception as e:
                self.log(f"Unexpected error downloading {filename}: {str(e)}")

        if self.is_downloading:
            self.log("Download completed!")
            self.progress_label.config(text="Download completed!")
        else:
            self.log("Download cancelled")
            self.progress_label.config(text="Download cancelled")

    def start_download(self):
        """Start download process in separate thread"""
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        output_dir = self.output_dir_var.get().strip()

        # Validate inputs
        if not url:
            messagebox.showerror("Error", "Please enter a 4chan thread URL")
            return

        if not self.validate_url(url):
            messagebox.showerror("Error", "Please enter a valid 4chan thread URL\n(e.g., https://boards.4chan.org/g/thread/12345)")
            return

        if not output_dir:
            messagebox.showerror("Error", "Please specify an output directory")
            return

        # Reset progress
        self.progress_var.set(0)
        self.progress_label.config(text="Starting download...")

        # Update UI state
        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.status_var.set("Downloading...")

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
                self.root.after(0, lambda: messagebox.showwarning("Warning", "No media files found in the thread"))
                return

            # Download media
            self.download_media_from_urls(media_urls, output_dir)

        except Exception as e:
            self.log(f"Unexpected error: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}"))

        finally:
            # Reset UI state
            self.root.after(0, self.download_finished)

    def download_finished(self):
        """Reset UI after download completion"""
        self.is_downloading = False
        self.download_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.status_var.set("Ready")

    def cancel_download(self):
        """Cancel ongoing download"""
        if self.is_downloading:
            self.is_downloading = False
            self.log("Cancelling download...")
            self.status_var.set("Cancelling...")

def main():
    root = tk.Tk()
    app = ChanScrapeGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
