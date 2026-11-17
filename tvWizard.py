from __future__ import annotations

import csv
import re
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import pyperclip
import requests
from bs4 import BeautifulSoup
from tkcalendar import Calendar


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The site does not serve HTTPS (the TLS handshake is reset), so use HTTP.
BASE_URL = "http://www.thefutoncritic.com/listings/{date}/"
REQUEST_TIMEOUT_SECONDS = 15
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900

NETFLIX_NAMES = {
    "NETFLIX",
    "NETFLIX.COM",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TVListing:
    air_date: date
    network: str
    title: str
    event_type: str
    additional_info: str = ""

    @property
    def display_text(self) -> str:
        details = f" [{self.additional_info}]" if self.additional_info else ""
        return f"{self.network} - {self.title}{details}"


# ---------------------------------------------------------------------------
# Scraping and parsing
# ---------------------------------------------------------------------------

def classify_event(text: str) -> Optional[str]:
    """
    Determine whether listing text represents a premiere or finale.

    Returns:
        "Premiere", "Finale", or None.
    """
    normalized = text.lower()

    if "premiere" in normalized:
        return "Premiere"

    if "finale" in normalized:
        return "Finale"

    return None


def parse_listings(html, listing_date: date) -> list[TVListing]:
    """
    Parse one day of Futon Critic listings HTML into premiere/finale entries.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings = []

    for row in soup.find_all("tr", valign="top"):
        cells = row.find_all("td")

        # The expected table structure contains network in the second cell
        # and program information in the third.
        if len(cells) < 3:
            continue

        network = cells[1].get_text(" ", strip=True)
        program_cell = cells[2]
        title_link = program_cell.find("a")

        if not network or title_link is None:
            continue

        title = title_link.get_text(" ", strip=True)

        if not title:
            continue

        full_program_text = program_cell.get_text(" ", strip=True)
        additional_info = full_program_text.replace(title, "", 1).strip()
        # The site already wraps notes in brackets, e.g. "[series premiere]";
        # strip them so display_text doesn't show "[[...]]".
        additional_info = additional_info.strip("[] ")

        event_type = classify_event(full_program_text)

        if event_type is None:
            continue

        listings.append(
            TVListing(
                air_date=listing_date,
                network=network,
                title=title,
                event_type=event_type,
                additional_info=additional_info,
            )
        )

    return listings


EPISODE_NUMBER_PATTERN = re.compile(r"\s*\(#[^)]*\)\s*$")


def clean_title(title: str) -> str:
    """
    Drop a trailing episode number like "(#201)" or "(#101-103)" so copied
    titles match what the original app produced.
    """
    return EPISODE_NUMBER_PATTERN.sub("", title).strip()


def get_tv_listings(listing_date: date) -> list[TVListing]:
    """
    Download and parse one day of Futon Critic listings.
    """
    formatted_date = listing_date.strftime("%Y/%m/%d")
    url = BASE_URL.format(date=formatted_date)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    return parse_listings(response.content, listing_date)


def get_weekly_listings(start_date: date) -> tuple[list[TVListing], list[str]]:
    """
    Load seven consecutive days of listings.

    Returns both successfully parsed listings and any day-level errors.
    """
    all_listings = []
    errors = []

    for offset in range(7):
        listing_date = start_date + timedelta(days=offset)

        try:
            all_listings.extend(get_tv_listings(listing_date))
        except requests.RequestException as exc:
            errors.append(
                f"{listing_date.strftime('%A, %B %d')}: {exc}"
            )
        except Exception as exc:
            errors.append(
                f"{listing_date.strftime('%A, %B %d')}: "
                f"unexpected parsing error: {exc}"
            )

    return all_listings, errors


def write_listings_csv(output_path: Path, listings: list[TVListing]) -> None:
    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "date",
                "network",
                "title",
                "event_type",
                "additional_info",
            ],
        )
        writer.writeheader()

        for listing in listings:
            writer.writerow(
                {
                    "date": listing.air_date.isoformat(),
                    "network": listing.network,
                    "title": listing.title,
                    "event_type": listing.event_type,
                    "additional_info": listing.additional_info,
                }
            )


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class TVListingsApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TV Premiere and Finale Listings")
        self.center_window(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.selected_date = datetime.today().date()
        self.listings: list[TVListing] = []
        self.listing_vars: dict[TVListing, tk.BooleanVar] = {}

        self.show_premieres_var = tk.BooleanVar(value=True)
        self.show_finales_var = tk.BooleanVar(value=True)
        self.include_netflix_var = tk.BooleanVar(value=True)
        self.check_all_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Select a date and load listings.")

        self.build_interface()
        self.update_date_label()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def build_interface(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.build_controls()
        self.build_results_area()
        self.build_status_bar()

    def build_controls(self):
        controls = ttk.Frame(self.root, padding=12)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        calendar_frame = ttk.LabelFrame(
            controls,
            text="Schedule window",
            padding=10,
        )
        calendar_frame.grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="nw",
            padx=(0, 16),
        )

        self.calendar = Calendar(
            calendar_frame,
            selectmode="day",
            year=self.selected_date.year,
            month=self.selected_date.month,
            day=self.selected_date.day,
        )
        self.calendar.pack()
        self.calendar.bind(
            "<<CalendarSelected>>",
            self.on_date_select,
        )

        options_frame = ttk.LabelFrame(
            controls,
            text="Filters",
            padding=10,
        )
        options_frame.grid(row=0, column=1, sticky="new")
        options_frame.columnconfigure(4, weight=1)

        ttk.Checkbutton(
            options_frame,
            text="Premieres",
            variable=self.show_premieres_var,
            command=self.refresh_display,
        ).grid(row=0, column=0, sticky="w", padx=(0, 14))

        ttk.Checkbutton(
            options_frame,
            text="Finales",
            variable=self.show_finales_var,
            command=self.refresh_display,
        ).grid(row=0, column=1, sticky="w", padx=(0, 14))

        ttk.Checkbutton(
            options_frame,
            text="Include Netflix",
            variable=self.include_netflix_var,
            command=self.refresh_display,
        ).grid(row=0, column=2, sticky="w", padx=(0, 14))

        ttk.Checkbutton(
            options_frame,
            text="Check all visible",
            variable=self.check_all_var,
            command=self.check_all_visible,
        ).grid(row=0, column=3, sticky="w")

        actions_frame = ttk.LabelFrame(
            controls,
            text="Actions",
            padding=10,
        )
        actions_frame.grid(
            row=1,
            column=1,
            sticky="sew",
            pady=(12, 0),
        )

        self.load_day_button = ttk.Button(
            actions_frame,
            text="Load Selected Day",
            command=lambda: self.start_loading(days=1),
        )
        self.load_day_button.pack(side=tk.LEFT, padx=(0, 8))

        self.load_week_button = ttk.Button(
            actions_frame,
            text="Load 7-Day Window",
            command=lambda: self.start_loading(days=7),
        )
        self.load_week_button.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            actions_frame,
            text="Copy Selected Titles",
            command=self.copy_selected_titles,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            actions_frame,
            text="Copy Selected Schedule",
            command=self.copy_selected_schedule,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            actions_frame,
            text="Export Selected CSV",
            command=self.export_selected_csv,
        ).pack(side=tk.LEFT)

        self.date_label = ttk.Label(
            controls,
            font=("TkDefaultFont", 11, "bold"),
        )
        self.date_label.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(12, 0),
        )

    def build_results_area(self):
        results_container = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        results_container.grid(row=1, column=0, sticky="nsew")
        results_container.columnconfigure(0, weight=1)
        results_container.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            results_container,
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            results_container,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.results_frame = ttk.Frame(self.canvas)
        self.results_window = self.canvas.create_window(
            (0, 0),
            window=self.results_frame,
            anchor="nw",
        )

        self.results_frame.bind(
            "<Configure>",
            self.update_scroll_region,
        )
        self.canvas.bind(
            "<Configure>",
            self.resize_results_frame,
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse-wheel support: Windows and macOS send <MouseWheel>,
        # X11 (Linux) sends Button-4 / Button-5.
        self.windowing_system = self.root.tk.call("tk", "windowingsystem")
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind_all(
            "<Button-4>", lambda _e: self.canvas.yview_scroll(-1, "units")
        )
        self.canvas.bind_all(
            "<Button-5>", lambda _e: self.canvas.yview_scroll(1, "units")
        )

    def build_status_bar(self):
        status = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor="w",
            padding=(8, 4),
        )
        status.grid(row=2, column=0, sticky="ew")

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def start_loading(self, days: int):
        self.set_loading_state(True)
        # Capture the date now so changing the calendar mid-load is safe.
        start_date = self.selected_date

        if days == 1:
            self.status_var.set(
                f"Loading listings for "
                f"{start_date.strftime('%B %d, %Y')}..."
            )
        else:
            end_date = start_date + timedelta(days=6)
            self.status_var.set(
                f"Loading listings from "
                f"{start_date.strftime('%B %d')} through "
                f"{end_date.strftime('%B %d, %Y')}..."
            )

        worker = threading.Thread(
            target=self.load_listings_worker,
            args=(start_date, days),
            daemon=True,
        )
        worker.start()

    def load_listings_worker(self, start_date: date, days: int):
        errors: list[str] = []

        try:
            if days == 1:
                listings = get_tv_listings(start_date)
            else:
                listings, errors = get_weekly_listings(start_date)

            listings.sort(
                key=lambda item: (
                    item.air_date,
                    item.network.lower(),
                    item.title.lower(),
                )
            )

        except requests.RequestException as exc:
            # Build the message here: `exc` is unbound once this block exits,
            # so a lambda that reads it later would raise NameError.
            message = f"Could not load listings:\n\n{exc}"
            self.root.after(0, lambda m=message: self.show_loading_error(m))
            return

        except Exception as exc:
            message = f"An unexpected error occurred:\n\n{exc}"
            self.root.after(0, lambda m=message: self.show_loading_error(m))
            return

        self.root.after(0, lambda: self.finish_loading(listings, errors))

    def finish_loading(
        self,
        listings: list[TVListing],
        errors: list[str],
    ):
        self.listings = listings
        self.listing_vars = {
            listing: tk.BooleanVar(value=False)
            for listing in listings
        }

        self.check_all_var.set(False)
        self.set_loading_state(False)
        self.refresh_display()

        if not listings:
            self.status_var.set(
                "No premieres or finales were found for this window."
            )
            if errors:
                messagebox.showwarning(
                    "Some listings could not be loaded",
                    "\n".join(errors),
                )
        elif errors:
            self.status_var.set(
                f"Loaded {len(listings)} listings, but "
                f"{len(errors)} day(s) could not be loaded."
            )
            messagebox.showwarning(
                "Some listings could not be loaded",
                "\n".join(errors),
            )
        else:
            self.status_var.set(
                f"Loaded {len(listings)} premiere/finale listings."
            )

    def show_loading_error(self, message: str):
        self.set_loading_state(False)
        self.status_var.set("Unable to load listings.")
        messagebox.showerror("Loading error", message)

    def set_loading_state(self, loading: bool):
        state = tk.DISABLED if loading else tk.NORMAL
        self.load_day_button.configure(state=state)
        self.load_week_button.configure(state=state)

    # ------------------------------------------------------------------
    # Display and filtering
    # ------------------------------------------------------------------

    def get_visible_listings(self) -> list[TVListing]:
        visible = []

        for listing in self.listings:
            if (
                listing.event_type == "Premiere"
                and not self.show_premieres_var.get()
            ):
                continue

            if (
                listing.event_type == "Finale"
                and not self.show_finales_var.get()
            ):
                continue

            if (
                not self.include_netflix_var.get()
                and listing.network.upper() in NETFLIX_NAMES
            ):
                continue

            visible.append(listing)

        return visible

    def refresh_display(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        visible_listings = self.get_visible_listings()

        if not visible_listings:
            ttk.Label(
                self.results_frame,
                text="No listings match the current filters.",
                padding=20,
            ).pack(anchor="w")
            return

        listings_by_date: dict[date, list[TVListing]] = {}

        for listing in visible_listings:
            listings_by_date.setdefault(listing.air_date, []).append(listing)

        for listing_date, daily_listings in listings_by_date.items():
            day_frame = ttk.LabelFrame(
                self.results_frame,
                text=listing_date.strftime("%A, %B %d, %Y"),
                padding=10,
            )
            day_frame.pack(
                fill=tk.X,
                expand=True,
                padx=8,
                pady=(8, 4),
            )

            for listing in daily_listings:
                row = ttk.Frame(day_frame)
                row.pack(fill=tk.X, pady=3)

                ttk.Checkbutton(
                    row,
                    text=listing.display_text,
                    variable=self.listing_vars[listing],
                    command=self.on_individual_selection_changed,
                ).pack(side=tk.LEFT, anchor="w")

                event_label = ttk.Label(
                    row,
                    text=listing.event_type,
                    width=10,
                    anchor="center",
                )
                event_label.pack(side=tk.RIGHT, padx=(12, 0))

        self.results_frame.update_idletasks()
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )
        self.canvas.yview_moveto(0)

    def check_all_visible(self):
        state = self.check_all_var.get()

        for listing in self.get_visible_listings():
            self.listing_vars[listing].set(state)

    def on_individual_selection_changed(self):
        visible_listings = self.get_visible_listings()

        all_visible_checked = (
            bool(visible_listings)
            and all(
                self.listing_vars[listing].get()
                for listing in visible_listings
            )
        )

        self.check_all_var.set(all_visible_checked)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def get_selected_listings(self) -> list[TVListing]:
        return [
            listing
            for listing in self.listings
            if self.listing_vars.get(listing)
            and self.listing_vars[listing].get()
        ]

    def copy_selected_titles(self):
        selected = self.get_selected_listings()

        if not selected:
            messagebox.showwarning(
                "Nothing selected",
                "Select at least one listing first.",
            )
            return

        # Preserve order while eliminating duplicate titles.
        unique_titles = list(
            dict.fromkeys(clean_title(listing.title) for listing in selected)
        )

        pyperclip.copy("\n".join(unique_titles))

        self.status_var.set(
            f"Copied {len(unique_titles)} title(s) to the clipboard."
        )

    def copy_selected_schedule(self):
        selected = self.get_selected_listings()

        if not selected:
            messagebox.showwarning(
                "Nothing selected",
                "Select at least one listing first.",
            )
            return

        lines = [
            (
                f"{listing.air_date.strftime('%m/%d/%Y')} | "
                f"{listing.network} | "
                f"{listing.title} | "
                f"{listing.event_type}"
            )
            for listing in selected
        ]

        pyperclip.copy("\n".join(lines))

        self.status_var.set(
            f"Copied {len(lines)} scheduled listing(s) to the clipboard."
        )

    def export_selected_csv(self):
        selected = self.get_selected_listings()

        if not selected:
            messagebox.showwarning(
                "Nothing selected",
                "Select at least one listing first.",
            )
            return

        default_name = (
            f"tv_listings_"
            f"{self.selected_date.strftime('%Y-%m-%d')}.csv"
        )

        filename = filedialog.asksaveasfilename(
            title="Export selected listings",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )

        if not filename:
            return

        output_path = Path(filename)

        try:
            write_listings_csv(output_path, selected)

            self.status_var.set(
                f"Exported {len(selected)} listing(s) to "
                f"{output_path.name}."
            )

            messagebox.showinfo(
                "Export complete",
                f"Saved {len(selected)} listings to:\n\n"
                f"{output_path}",
            )

        except OSError as exc:
            messagebox.showerror(
                "Export error",
                f"Could not save the CSV file:\n\n{exc}",
            )

    # ------------------------------------------------------------------
    # Events and layout
    # ------------------------------------------------------------------

    def on_date_select(self, _event=None):
        self.selected_date = self.calendar.selection_get()
        self.update_date_label()

    def update_date_label(self):
        end_date = self.selected_date + timedelta(days=6)

        self.date_label.configure(
            text=(
                f"Selected date: "
                f"{self.selected_date.strftime('%A, %B %d, %Y')}  |  "
                f"7-day window ends: "
                f"{end_date.strftime('%A, %B %d, %Y')}"
            )
        )

    def update_scroll_region(self, _event=None):
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )

    def resize_results_frame(self, event):
        self.canvas.itemconfigure(
            self.results_window,
            width=event.width,
        )

    def on_mousewheel(self, event):
        if not event.delta:
            return

        if self.windowing_system == "aqua":
            # macOS reports small deltas (typically +/-1 to a few).
            step = -event.delta
        else:
            # Windows reports multiples of 120 per wheel notch.
            step = int(-event.delta / 120) or (-1 if event.delta > 0 else 1)

        self.canvas.yview_scroll(step, "units")

    def center_window(self, width: int, height: int):
        self.root.update_idletasks()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)

        self.root.geometry(f"{width}x{height}+{x}+{y}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    TVListingsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
