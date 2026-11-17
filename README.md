# FutonScraper

A small desktop app that pulls TV **premieres** and **finales** from [The Futon Critic](http://www.thefutoncritic.com/listings/) listings, lets you filter and pick shows, and copies or exports your picks.

## Features

- Load one day or a 7-day window starting from any date on the calendar
- Show or hide premieres and finales, and hide Netflix if you want
- Check all visible listings at once
- Copy selected titles (deduplicated, without episode numbers) or a full schedule (`date | network | title | type`) to the clipboard
- Export your selection to CSV
- Loads in the background, so the window stays responsive

## Requirements

- Python 3.9 or newer with Tk
- On macOS, Apple's built-in `python3` ships an old Tk that can hang. Use Python from [python.org](https://www.python.org/downloads/) or Homebrew (`brew install python@3.12 python-tk@3.12`) instead.

## Setup

```bash
git clone https://github.com/pkiefe973/FutonScraper.git
cd FutonScraper
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python tvWizard.py
```

Pick a date on the calendar, click **Load Selected Day** or **Load 7-Day Window**, check the shows you want, then copy or export them.

## Notes

- The Futon Critic doesn't serve HTTPS, so the app fetches listings over plain HTTP.
- This scrapes a public web page, so if the site changes its layout, parsing may need an update.
