# import tkinter as tk
# from tkinter import filedialog, messagebox
# from pathlib import Path
# from sec_scraper import run_downloader
# from html_insert import replace_disclosure_block
#
# class SECToolApp:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("SEC 8-K Downloader & HTML Disclosure Inserter")
#         self.root.geometry("600x300")
#
#         self.section_frame = None
#         self.init_ui()
#
#     def init_ui(self):
#         self.menu_frame = tk.Frame(self.root)
#         self.menu_frame.pack(pady=10)
#
#         self.download_btn = tk.Button(self.menu_frame, text="Download 8-K", command=self.show_download_section)
#         self.download_btn.grid(row=0, column=0, padx=10)
#
#         self.insert_btn = tk.Button(self.menu_frame, text="Replace Disclosure", command=self.show_insert_section)
#         self.insert_btn.grid(row=0, column=1, padx=10)
#
#         self.show_download_section()
#
#     def show_download_section(self):
#         self.clear_section()
#         self.section_frame = tk.Frame(self.root)
#         self.section_frame.pack(pady=10)
#
#         tk.Label(self.section_frame, text="Enter Stock Ticker:").pack()
#         self.ticker_entry = tk.Entry(self.section_frame)
#         self.ticker_entry.pack()
#         tk.Button(self.section_frame, text="Download Latest 8-K", command=self.download_8k).pack(pady=5)
#
#     def show_insert_section(self):
#         self.clear_section()
#         self.section_frame = tk.Frame(self.root)
#         self.section_frame.pack(pady=10)
#
#         tk.Label(self.section_frame, text="Select HTML 8-K File to Replace:").pack()
#         self.html_file_btn = tk.Button(self.section_frame, text="Choose HTML File", command=self.select_html_file)
#         self.html_file_btn.pack()
#         self.selected_html_file = tk.Label(self.section_frame, text="No HTML file selected")
#         self.selected_html_file.pack()
#
#         tk.Label(self.section_frame, text="Select Word File to Insert:").pack()
#         self.word_file_btn = tk.Button(self.section_frame, text="Choose Word File", command=self.select_word_file)
#         self.word_file_btn.pack()
#         self.selected_word_file = tk.Label(self.section_frame, text="No Word file selected")
#         self.selected_word_file.pack()
#
#         tk.Button(self.section_frame, text="Start Replacement", command=self.start_insertion).pack(pady=5)
#
#     def clear_section(self):
#         if self.section_frame:
#             self.section_frame.destroy()
#
#     def select_word_file(self):
#         file_path = filedialog.askopenfilename(filetypes=[("Word Files", "*.docx")])
#         self.selected_word_file.config(text=file_path)
#         self.word_file = file_path
#
#     def select_html_file(self):
#         file_path = filedialog.askopenfilename(filetypes=[("HTML Files", "*.htm")])
#         self.selected_html_file.config(text=file_path)
#         self.html_file = file_path
#
#     def download_8k(self):
#         ticker = self.ticker_entry.get().strip()
#         if not ticker:
#             messagebox.showwarning("Input Error", "Please enter a stock ticker.")
#             return
#         result = run_downloader(ticker)
#         messagebox.showinfo("Download Result", result)
#
#     def start_insertion(self):
#         if not hasattr(self, 'word_file') or not Path(self.word_file).exists():
#             messagebox.showerror("Error", "No valid Word file selected.")
#             return
#         if not hasattr(self, 'html_file') or not Path(self.html_file).exists():
#             messagebox.showerror("Error", "No valid HTML file selected.")
#             return
#
#         try:
#             result_path = replace_disclosure_block(self.word_file, self.html_file)
#             messagebox.showinfo("Success", f"Disclosure block replaced. Saved to:\n{result_path}")
#         except Exception as e:
#             messagebox.showerror("Error", str(e))
#
#
# def launch_gui():
#     root = tk.Tk()
#     app = SECToolApp(root)
#     root.mainloop()
#
