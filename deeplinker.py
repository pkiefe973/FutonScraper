import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import pyperclip
import requests
from bs4 import BeautifulSoup
import re
##NOTES
## Xumo Play channels not supported

# Create the main window
root = tk.Tk()
root.title("Deeplink Generator 1.00")
root.geometry("800x600")
root.clipboard_clear()

def center_window(window, width=800, height=600):
    # Get the screen width and height
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # Calculate the position x and y coordinates
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    # Set the geometry of the window
    window.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

center_window(root, 800, 600)

# Add a label
label_header = tk.Label(root, text="Deeplink Generator", font=("Arial", 20, "bold"))
label_header.grid(row=0, column=0, padx=5, pady=7, sticky=tk.W)

label_header2 = tk.Label(root, text="version 1.00", font=("Arial", 12, "bold"))
label_header2.grid(row=1, column=0, padx=5, pady=7, sticky=tk.W)

# Add an entry (text box)
id_entry = tk.Entry(root)
id_entry.grid(row=2, column=0, padx=5, pady=7, sticky=tk.W)

# Create templates for each deeplink type
deeplink_templates = {
    "Peacock": (
        "appmanager:launchApplication#appId=Peacock&additionalLaunchParams="
        "%7B%22param.launchpoint%22%3A%22detail%22%2C%22param.entityId%22%3A%22{}"
        "%22%2C%22launchedFrom%22%3A%22Editorial%22%7D"
    ),
    "Hulu": (
        "appmanager:launchApplication#appId=Hulu&additionalLaunchParams="
        "%7B%22firebase.id%22%3A%22Hulu%2Fseason%22%2C%22param.entityId%22%3A%22{}"
        "%22%2C%22launchedFrom%22%3A%22Editorial%22%7D"
    ),
    "Max": (
        "appmanager:launchApplication#appId=hbo_hbomax&additionalLaunchParams="
        "%7B%22param.launchpoint%22%3A%22detail%22%2C%22launchedFrom%22%3A%22Editorial%22%2C%22param.entityId%22%3A%22"
        "{}%22%7D"
    ),
    "Disney": (
        "appmanager:launchApplication#appId=disneyPlus&additionalLaunchParams=%7B%22param.launchpoint%22%3A%22detail%22%2C%22param.entityId%22%3A%22series_details%7C{}%22%2C%22launchedFrom%22%3A%22Editorial%22%7D"
    ),
    "Xumo Play": (
        "appmanager:launchApplication#appId=xumo&additionalLaunchParams=%7B%22firebase.id%22%3A%22XUMO%2Fvod%22%2C%22param.channelId%22%3A%2299991299%22%2C%22param.assetId%22%3A%22{}%22%2C%22launchedFrom%22%3A%22editorial%22%7D"
    )

    # Add other templates as needed
}

def google_search(site, query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    search_url = f"https://www.google.com/search?q=site:{site} {query}"
    response = requests.get(search_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve search results. Status code: {response.status_code}")
        return None, None, None
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Debugging output: print out the raw HTML
    print("Raw HTML content:")
    print(soup.prettify())  # This will help see the entire HTML structure

    # Find all relevant <a> tags within search results
    search_results = soup.find_all('a')
    print(f"Found {len(search_results)} <a> tags.")  # Debugging output

    for idx, result in enumerate(search_results):
        href = result.get('href')
        if href and site in href:
            # Debugging output
            print(f"Link {idx + 1}: {href}")
            
            # Extract text from possible relevant tags
            link_text = result.get_text()
            if not link_text:
                # Check parent tags for text
                parent = result.find_parent()
                if parent:
                    link_text = parent.get_text()
            
            # Clean and print extracted link text
            link_text = link_text.strip()
            print(f"Link text {idx + 1}: {link_text}")
            
            # Extract ID from the URL
            temp_id = extract_id(href, site)
            print(f"Extracted ID for {site}: {temp_id}")  # Debugging output
            if temp_id:
                return href, link_text, temp_id

    return None, None, None

def extract_id(url, site):
    if site == "disneyplus.com":
        # Extract alphanumeric ID for Disney
        pattern = r"disneyplus\.com/.*/([A-Za-z0-9]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if site == "peacocktv.com":
        #extract 19 digit ID for peacock
        #this approach is not reliable. Suggest using whatever method the MAPS team uses to pull an ID from internal source. 19 digit rex ids work for this!
        pattern = r"peacocktv\.com/.*/([0-9]{19})"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    elif site == "play.xumo.com":
        # Extract ID for Xumo Play (e.g., XM0P97SXC83QZN)
        pattern = r"play\.xumo\.com/.*/(XM0[A-Z0-9]{11})"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        
    else:
        # Extract UUID for other sites
        pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
        match = re.search(pattern, url)
        if match:
            return match.group(0)
    return None

# Function to handle button click
def on_button_click():
    user_input = id_entry.get()
    dl_type = combobox.get()
    
    if not user_input:
        messagebox.showwarning("Input Error", "Please enter an ID.")
        return
    
    if dl_type == "Select an option":
        messagebox.showwarning("Selection Error", "Please select a deeplink type.")
        return
    
    site = ""
    if dl_type == "Max":
        site = "max.com"
    elif dl_type == "Hulu":
        site = "hulu.com"
    elif dl_type == "Disney":
        site = "disneyplus.com"
    elif dl_type == "Peacock":
        site = "peacocktv.com"
    elif dl_type == "Xumo Play":
        site = "play.xumo.com"
    if site:
        search_result_url, show_name, temp_id = google_search(site, user_input)
        if search_result_url is None:
            messagebox.showerror("Search Error", "Failed to retrieve search results or no results found.")
            return
        
        if temp_id is None:
            messagebox.showerror("ID Error", "Failed to extract ID from the search result.")
            return
        
        print(f"Deeplink Type: {dl_type}, ID: {temp_id}")  # Debugging output

        dl_constructed = deeplink_templates.get(dl_type, "Not yet supported.").format(temp_id)
        
        # Display the show name on the UI
        show_name_label.config(text=f"Show: {show_name}")
        
        pyperclip.copy(dl_constructed)
        messagebox.showinfo("Deeplink Generator", f"Your constructed deeplink: \n\n{dl_constructed}.\n\nThis has been copied to the clipboard.")

# Add a dropdown (combobox)
options = ["Select an option", "Peacock", "Hulu", "Max", "Disney","Xumo Play"]  # Add other options as needed
selected_option = tk.StringVar()
combobox = ttk.Combobox(root, textvariable=selected_option, values=options)
combobox.grid(row=2, column=1, padx=5, pady=7, sticky=tk.W)
combobox.current(0)  # Set default option

# Add a button
button = tk.Button(root, text="Generate Deeplink", command=on_button_click)
button.grid(row=3, column=0, padx=5, pady=7, sticky=tk.W)

# Add a label for the show name
show_name_label = tk.Label(root, text="", font=("Arial", 14), wraplength=200)
show_name_label.grid(row=4, column=0, padx=5, pady=7, sticky=tk.W)

# Run the main loop
root.mainloop()
