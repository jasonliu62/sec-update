# main.py
import tkinter as tk
from tkinter import messagebox
from sec_scraper import run_downloader

def start_gui():
    def submit():
        ticker = entry.get()
        if not ticker:
            messagebox.showwarning("Input Error", "Please enter a stock ticker.")
            return
        result = run_downloader(ticker)
        messagebox.showinfo("Result", result)

    root = tk.Tk()
    root.title("SEC 8-K iXBRL Downloader")
    root.geometry("400x150")

    label = tk.Label(root, text="Enter Stock Ticker:")
    label.pack(pady=10)

    entry = tk.Entry(root, width=30)
    entry.pack()

    button = tk.Button(root, text="Download 8-K iXBRL", command=submit)
    button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    start_gui()
