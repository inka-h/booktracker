import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from datetime import datetime

# Configuration Constants
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(SCRIPT_DIR, 'books.json')

STATUS_COLORS = {
    "Unread": "#ffffff",    # White
    "Reading": "#fff7e6",   # Light yellow
    "Read": "#f0f7f0"       # Light green
}
STATUSES = list(STATUS_COLORS.keys())
COLUMNS = ["Title", "Author", "Status", "Started", "Finished", "Tags", "Notes"]


class BookTracker:
    def __init__(self, data_file=DATA_FILE):
        self.data_file = data_file
        self.window = tk.Tk()
        self.window.title("Book Tracker")
        self.window.geometry("800x650")
        self.window.minsize(600, 400)

        self.books = self.load_books()
        self.status_filters = {status: tk.BooleanVar(value=True) for status in STATUSES}

        self.tooltip = None

        self.main = ttk.Frame(self.window, padding="10")
        self.main.pack(fill="both", expand=True)

        self.setup_gui()
        self.refresh_book_list()

        icon_path = os.path.join(SCRIPT_DIR, "favicon.ico")
        if os.path.exists(icon_path):
            self.window.iconbitmap(icon_path)

    def ensure_list(self, value):
        if isinstance(value, list):
            return value
        elif value:
            return [value]
        else:
            return []

    def setup_gui(self):
        self.create_input_section()
        self.create_search_section()
        self.create_book_list_section()
        self.create_buttons_section()
        self.update_window_title()

    def create_input_section(self):
        input_container = ttk.Frame(self.main)
        input_container.pack(fill="x", pady=(0, 10))

        self.collapse_btn = ttk.Button(input_container, text="▼", width=3, command=self.toggle_input_frame)
        self.collapse_btn.pack(side="left", padx=(0, 5))

        self.input_frame = ttk.LabelFrame(input_container, text="Add New Book", padding="10")
        self.input_frame.pack(fill="x", expand=True)
        self.input_frame.grid_columnconfigure(1, weight=1)

        self.title_entry = self.create_labeled_entry(self.input_frame, "Title:", 0)
        self.author_entry = self.create_labeled_entry(self.input_frame, "Author:", 1)
        self.tags_entry = self.create_labeled_entry(self.input_frame, "Tags:", 2)
        self.start_date_entry = self.create_labeled_entry(self.input_frame, "Start Date (dd.mm.yyyy):", 3)

        ttk.Button(self.input_frame, text="Add Book", command=self.add_book).grid(row=4, column=1, pady=10)

    def create_search_section(self):
        search_frame = ttk.LabelFrame(self.main, text="Search Books", padding="10")
        search_frame.pack(fill="x", pady=(0, 10))

        search_controls = ttk.Frame(search_frame)
        search_controls.pack(fill="x", pady=(0, 5))

        ttk.Label(search_controls, text="Search in:").pack(side="left", padx=5)
        self.search_field = ttk.Combobox(search_controls, values=["All Fields", "Title", "Author", "Started", "Finished", "Tags", "Notes"], width=10)
        self.search_field.set("All Fields")
        self.search_field.pack(side="left", padx=5)

        self.search_entry = ttk.Entry(search_controls, width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<KeyRelease>', lambda e: self.refresh_book_list())

        ttk.Button(search_controls, text="Clear", command=self.clear_search).pack(side="left", padx=5)

        filter_frame = ttk.Frame(search_frame)
        filter_frame.pack(fill="x")

        ttk.Label(filter_frame, text="Show:").pack(side="left", padx=(5, 10))
        for status, var in self.status_filters.items():
            ttk.Checkbutton(filter_frame, text=status, variable=var, command=self.refresh_book_list).pack(side="left", padx=5)

    def show_tooltip(self, event):
        item_id = self.book_list.identify_row(event.y)
        column = self.book_list.identify_column(event.x)
        if item_id and column == "#7":
            values = self.book_list.item(item_id, 'values')
            if len(values) > 6:
                note = values[6]
                if len(note) > 40:
                    if self.tooltip:
                        self.tooltip.destroy()
                    self.tooltip = tk.Toplevel(self.window)
                    self.tooltip.wm_overrideredirect(True)
                    self.tooltip.geometry(f"+{event.x_root+20}+{event.y_root+20}")
                    label = ttk.Label(self.tooltip, text=note, background="lightgray", relief="solid", borderwidth=1, wraplength=300)
                    label.pack()
                    self.tooltip.after(2000, self.tooltip.destroy)

    def hide_tooltip(self, event):
        if self.tooltip_job:
            self.window.after_cancel(self.tooltip_job)
            self.tooltip_job = None
        if self.tooltip:
            if self.tooltip_shown_time:
                self.window.after_cancel(self.tooltip_shown_time)
                self.tooltip_shown_time = None
            self.tooltip.after(0, self.tooltip.destroy)

    def load_file(self):
        file_path = filedialog.askopenfilename(
            title="Select a JSON File",
            filetypes=(("JSON Files", "*.json"), ("All Files", "*.*"))
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    books = json.load(f)
                    for book in books:
                        book.setdefault("notes", "")
                        book.setdefault("status", "Unread")
                        book["start_date"] = self.ensure_list(book.get("start_date", []))
                        book["date_finished"] = self.ensure_list(book.get("date_finished", []))
                    self.books = books
                    self.data_file = file_path  # Update the active file
                    self.refresh_book_list()
                    self.update_window_title()
                    messagebox.showinfo("Success", f"Loaded books from {file_path}")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")

    def update_window_title(self):
        file_name = os.path.basename(self.data_file)
        self.window.title(f"Book Tracker - {file_name}")

    def create_book_list_section(self):
        tree_frame = ttk.Frame(self.main)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.book_list = ttk.Treeview(tree_frame, columns=COLUMNS, show="headings")
        for col in COLUMNS:
            self.book_list.heading(col, text=col, command=lambda c=col: self.sort_column(c, False))
            self.book_list.column(col, width=100, anchor="center")

        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.book_list.yview)
        self.book_list.configure(yscrollcommand=v_scrollbar.set)

        self.book_list.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")

        self.book_list.bind("<Double-1>", self.on_double_click)
        self.book_list.bind("<Motion>", self.show_tooltip)

    def on_double_click(self, event):
        item_id = self.book_list.selection()[0]
        column = self.book_list.identify_column(event.x)
        column_index = int(column.replace("#", "")) - 1
        column_name = COLUMNS[column_index]

        if column_name in ["Tags", "Notes"]:
            self.edit_cell_in_place(item_id, column_name, column_index)

    def edit_cell_in_place(self, item_id, column_name, column_index):
        x, y, width, height = self.book_list.bbox(item_id, column_name)
        entry = ttk.Entry(self.book_list, width=width)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, self.book_list.item(item_id, 'values')[column_index])
        entry.focus()

        def save_edit(event=None):
            new_value = entry.get()
            if column_name == "Tags":
                new_value = [tag.strip() for tag in new_value.split(",") if tag.strip()]
            self.book_list.set(item_id, column_name, ", ".join(new_value) if isinstance(new_value, list) else new_value)
            book_index = self.book_list.index(item_id)
            self.books[book_index][column_name.lower()] = new_value
            self.save_books()
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)

    def create_buttons_section(self):
        button_frame = ttk.Frame(self.main)
        button_frame.pack(side="bottom", fill="x", pady=10)

        for status in STATUSES:
            ttk.Button(button_frame, text=f"Mark as {status}",
                        command=lambda s=status: self.change_status(s)).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete", command=self.confirm_delete).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Load File", command=self.load_file).pack(side="right", padx=5)

    def create_labeled_entry(self, parent, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=5, pady=5)
        entry = ttk.Entry(parent, width=50)
        entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        return entry

    def toggle_input_frame(self):
        if self.input_frame.winfo_viewable():
            self.input_frame.pack_forget()
            self.collapse_btn.configure(text="▶")
        else:
            self.input_frame.pack(fill="x", expand=True)
            self.collapse_btn.configure(text="▼")

    def add_book(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Input Error", "Please enter a book title.")
            return

        start_date = self.start_date_entry.get().strip()
        try:
            datetime.strptime(start_date, "%d.%m.%Y")
        except ValueError:
            if start_date:
                messagebox.showwarning("Input Error", "Invalid date format. Use DD.MM.YYYY")
                return

        new_book = {
            "title": title,
            "author": self.author_entry.get(),
            "tags": [tag.strip() for tag in self.tags_entry.get().split(",") if tag.strip()],
            "status": "Unread",
            "start_date": [start_date] if start_date else [],
            "date_finished": [],
            "notes": ""
        }
        self.books.append(new_book)
        self.save_books()
        self.refresh_book_list()

        for entry in (self.title_entry, self.author_entry, self.tags_entry, self.start_date_entry):
            entry.delete(0, tk.END)

    def change_status(self, new_status):
        selected = self.book_list.selection()
        if not selected:
            return
        index = self.book_list.index(selected[0])
        self.books[index]["status"] = new_status
        today = datetime.now().strftime("%d.%m.%Y")

        if new_status == "Read":
            if today not in self.ensure_list(self.books[index].get("date_finished", [])):
                self.books[index].setdefault("date_finished", []).append(today)
        elif new_status == "Reading":
            if today not in self.ensure_list(self.books[index].get("start_date", [])):
                self.books[index].setdefault("start_date", []).append(today)

        self.save_books()
        self.refresh_book_list()

    def confirm_delete(self):
        selected = self.book_list.selection()
        if selected:
            item = selected[0]
            book_title = self.book_list.item(item)['values'][0]
            if messagebox.askyesno("Confirm Deletion", f"Delete '{book_title}'?"):
                del self.books[self.book_list.index(item)]
                self.save_books()
                self.refresh_book_list()

    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.refresh_book_list()

    def refresh_book_list(self):
        search_term = self.search_entry.get().strip().lower()
        search_field = self.search_field.get()

        for item in self.book_list.get_children():
            self.book_list.delete(item)

        filtered_books = []
        for book in self.books:
            if search_term:
                matches = {
                    "Title": search_term in book["title"].lower(),
                    "Author": search_term in book["author"].lower(),
                    "Tags": any(search_term in tag.lower() for tag in book["tags"]),
                    "Notes": search_term in book["notes"].lower(),
                    "Started": search_term in (", ".join(self.ensure_list(book.get("start_date", []))) or "").lower(),
                    "Finished": search_term in (", ".join(self.ensure_list(book.get("date_finished", []))) or "").lower(),
                    "All Fields": any(
                        search_term in book[field].lower() for field in ["title", "author", "notes"]
                    ) or any(search_term in tag.lower() for tag in book["tags"]) or
                    search_term in (", ".join(self.ensure_list(book.get("start_date", []))) or "").lower() or
                    search_term in (", ".join(self.ensure_list(book.get("date_finished", []))) or "").lower()
                }
                if not matches.get(search_field, matches["All Fields"]):
                    continue

            filtered_books.append(book)

        for book in filtered_books:
            if not self.status_filters[book["status"]].get():
                continue

            all_start_dates = ", ".join(self.ensure_list(book["start_date"]))
            all_finish_dates = ", ".join(self.ensure_list(book["date_finished"]))

            self.book_list.insert("", tk.END, values=(
                book["title"], book["author"], book["status"], all_start_dates,
                all_finish_dates, ", ".join(book["tags"]), book["notes"]
            ), tags=(f'status_{book["status"]}',))

        for status, color in STATUS_COLORS.items():
            self.book_list.tag_configure(f'status_{status}', background=color)

    def load_books(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                books = json.load(f)
                for book in books:
                    book.setdefault("notes", "")
                    book.setdefault("status", "Unread")
                    book["start_date"] = self.ensure_list(book.get("start_date", []))
                    book["date_finished"] = self.ensure_list(book.get("date_finished", []))
                return books
        except FileNotFoundError:
            return []

    def sort_column(self, col, reverse):
        column_map = {
            "Title": "title",
            "Author": "author",
            "Status": "status",
            "Start Date": "start_date",
            "Date Finished": "date_finished",
            "Tags": "tags",
            "Notes": "notes"
        }

        key = column_map[col]
        if key in ["start_date", "date_finished"]:
            self.books.sort(
                key=lambda book: datetime.strptime(book[key], "%d.%m.%Y") if book[key] else datetime.min,
                reverse=reverse
            )
        else:
            self.books.sort(
                key=lambda book: ", ".join(book[key]) if isinstance(book[key], list) else book[key].lower(),
                reverse=reverse
            )
        self.refresh_book_list()
        self.book_list.heading(col, command=lambda: self.sort_column(col, not reverse))

    def save_books(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.books, f, indent=2)

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    BookTracker().run()
