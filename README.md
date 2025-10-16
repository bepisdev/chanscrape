# chanscrape
Script to scrape attachments from 4Chan threads

## Usage

### GUI Mode (Recommended)

For an easy-to-use graphical interface, run:

```console
$ python launcher.py --gui
```

Or directly:

```console
$ python gui.py
```

The GUI provides:
- Easy URL input and validation
- Directory browser for output location
- Progress tracking with visual progress bar
- Real-time download logs
- Cancel functionality
- Duplicate file detection

### Command Line Mode

For command-line usage, you can use either:

```console
$ python launcher.py <URL>
```

Or the original script:

```console
$ python main.py <URL>
```

Optionally you can pass a `-o` flag to set an output directory:

```console
$ python main.py -o ./target_thread_name <URL>
```

## Installation

Install dependencies with pip:

```console
$ pip install -r requirements.txt
```

Required dependencies:
- `requests` - for HTTP requests
- `beautifulsoup4` - for HTML parsing
- `rich` - for CLI progress bars (CLI mode only)

## Features

- **GUI Interface**: User-friendly graphical interface with progress tracking
- **CLI Interface**: Command-line interface for automation and scripting
- **Progress Tracking**: Real-time download progress in both modes
- **Error Handling**: Robust error handling with informative messages
- **Duplicate Detection**: Skips already downloaded files
- **Cancellation**: Ability to cancel downloads in progress (GUI mode)
- **Validation**: URL validation to ensure valid 4chan thread URLs

## Supported File Types

The scraper downloads all media files posted in a 4chan thread, including:
- Images (JPG, PNG, GIF, etc.)
- Videos (WEBM, MP4, etc.)
- Other media files attached to posts

## Examples

### GUI Mode
```console
$ python launcher.py --gui
```

### CLI Mode
```console
$ python launcher.py https://boards.4chan.org/g/thread/12345
$ python launcher.py https://boards.4chan.org/g/thread/12345 -o downloads/tech_thread
```
