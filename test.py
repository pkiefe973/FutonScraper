import tkinter as tk
from tkinter import ttk

def display_titles():
    # Clear existing widgets
    for widget in frame.winfo_children():
        widget.pack_forget()

    # Dummy titles for testing
    for title in range(10):
        var = tk.BooleanVar()
        chk = ttk.Checkbutton(frame, text=f"Title {title+1}", variable=var)
        chk.var = var
        chk.pack(anchor='w', padx=10, pady=5)

    check_all_var.set(False)  # Reset the "Check All" checkbox
    check_all_checkbox.pack(anchor='w', padx=10, pady=5)  # Pack "Check All" checkbox at the bottom

root = tk.Tk()
root.title("Test")

frame = ttk.Frame(root)
frame.pack(padx=10, pady=10)

check_all_var = tk.BooleanVar()
check_all_checkbox = ttk.Checkbutton(root, text="Check All", variable=check_all_var)
check_all_checkbox.pack(anchor='w', padx=10, pady=5)  # Pack "Check All" checkbox at the bottom

load_button = ttk.Button(root, text="Load Titles", command=display_titles)
load_button.pack(pady=10)

root.mainloop()
