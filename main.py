# main.py
import tkinter as tk
from tkinter import filedialog, messagebox
from sec_scraper import run_downloader
from html_updater import update_12b_section

def start_gui():
    def download_8k():
        ticker = entry.get()
        if not ticker:
            messagebox.showwarning("Input Error", "Please enter a stock ticker.")
            return
        try:
            result = run_downloader(ticker)
            messagebox.showinfo("Download Result", result)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def replace_12b():
        msft_path = filedialog.askopenfilename(title="Select MSFT 8-K HTML", filetypes=[("HTML files", "*.htm *.html")])
        if not msft_path:
            return
        aapl_path = filedialog.askopenfilename(title="Select AAPL 8-K HTML", filetypes=[("HTML files", "*.htm *.html")])
        if not aapl_path:
            return
        try:
            result = update_12b_section(msft_path, aapl_path)
            messagebox.showinfo("12(b) Replacement Complete", result)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    root = tk.Tk()
    root.title("SEC 8-K iXBRL Toolkit")
    root.geometry("420x200")

    # Ticker input section
    label = tk.Label(root, text="Enter Stock Ticker:")
    label.pack(pady=(10, 0))

    entry = tk.Entry(root, width=30)
    entry.pack()

    button_download = tk.Button(root, text="Download 8-K iXBRL", command=download_8k)
    button_download.pack(pady=10)

    # Divider
    divider = tk.Label(root, text="────────────── OR ──────────────")
    divider.pack(pady=5)

    # Replace MSFT 12(b) section
    label2 = tk.Label(root, text="Replace MSFT 12(b) Section with AAPL Data")
    label2.pack(pady=(5, 0))

    button_replace = tk.Button(root, text="Select MSFT + AAPL HTML Files", command=replace_12b)
    button_replace.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    start_gui()