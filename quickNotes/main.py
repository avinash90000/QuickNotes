import gi
import os
import json

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

BASE_PATH = os.path.expanduser("~/.local/share/notes")
NOTES_FILE = os.path.expanduser("~/.local/share/notes/.notes.json")

def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    else:
        print("Notes file doesnt exist")
        if not os.path.exists(BASE_PATH):
            print("Creating base path")
            os.mkdir(BASE_PATH)
    return {}

def save_notes(data):
    with open(NOTES_FILE, "w") as f:
        json.dump(data, f, indent=2)


class NotesPopup(Gtk.Window):
    def __init__(self, x=100, y=100):
        super().__init__()
        

        self.set_title("Quick Notes")
        self.set_default_size(400, 400)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)

        self.connect("realize", lambda *a: self.reposition(x, y))
        self.set_opacity(1.0)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("focus-in-event", self.on_focus_in)

        # HeaderBar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Notes")
        header.get_style_context().add_class("slim-headerbar")

        # Create a horizontal box
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Entry for tab name
        self.tab_name_entry = Gtk.Entry()
        self.tab_name_entry.set_placeholder_text("Tab name...")
        #self.tab_name_entry.set_max_width_chars(15)
        #self.tab_name_entry.set_width_chars(10)
        self.tab_name_entry.set_size_request(100, -1)
        self.tab_name_entry.connect("activate", self.on_entry_activate)
        #header.pack_end(self.tab_name_entry)
        # Sticky left widget
        box.pack_start(self.tab_name_entry, True, True, 0)

        # + Button
        plus_btn = Gtk.Button.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        plus_btn.set_relief(Gtk.ReliefStyle.NONE)
        plus_btn.set_focus_on_click(False)
        plus_btn.set_tooltip_text("New Tab")
        plus_btn.connect("clicked", self.add_new_tab)
        #header.pack_end(plus_btn)
        # Expanding middle widget
        box.pack_end(plus_btn, True, True, 0)

        header.pack_start(box)
        self.set_titlebar(header)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            headerbar.slim-headerbar {
                padding-top: 2px;
                padding-bottom: 2px;
                min-height: 24px;
            }
        """)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        self.notes_data = load_notes()
        self.buffers = {}

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.add(self.notebook)


        for name in self.notes_data:
            self.add_note_tab(name, self.notes_data[name])

        self.connect("delete-event", self.on_close)
        self.show_all()

    def reposition(self, x, y):
        alloc = self.get_allocation()
        window_width = alloc.width
        self.move(x - window_width // 2, y + 30)
        self.notebook.grab_focus()
        

    def on_focus_out(self, *_):
        self.set_opacity(0.8)

    def on_focus_in(self, *_):
        self.set_opacity(1.0)

    def on_close(self, *_):
        new_notes_data = {}
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            for name, buffer in self.buffers.items():
                widget = page.get_children()[0]
                if widget.get_buffer() == buffer:
                    start_iter, end_iter = buffer.get_bounds()
                    text = buffer.get_text(start_iter, end_iter, True)
                    new_notes_data[name] = text
                    
        """ for name, buffer in self.buffers.items():
            start_iter, end_iter = buffer.get_bounds()
            text = buffer.get_text(start_iter, end_iter, True)
            self.notes_data[name] = text """
        save_notes(new_notes_data)
        return False

    def add_note_tab(self, name, content=""):
        buffer = Gtk.TextBuffer()
        buffer.set_text(content)

        textview = Gtk.TextView(buffer=buffer)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_width(380)
        scroll.set_min_content_height(180)
        scroll.add(textview)

        self.buffers[name] = buffer

        label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_label = Gtk.Label(label=name)
        close_button = Gtk.Button.new_from_icon_name("window-close", Gtk.IconSize.MENU)
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.set_focus_on_click(False)
        close_button.set_size_request(16, 16)
        close_button.connect("clicked", self.close_tab, scroll, name)

        label_event_box = Gtk.EventBox()
        label_event_box.add(tab_label)
        label_event_box.connect("button-press-event", self.on_tab_double_click, tab_label)

        label_box.pack_start(label_event_box, True, True, 0)
        label_box.pack_start(close_button, False, False, 0)
        label_box.show_all()

        self.notebook.append_page(scroll, label_box)
        self.notebook.set_tab_reorderable(scroll, True)
        self.notebook.show_all()

    def close_tab(self, button, page, name):
        page_num = self.notebook.page_num(page)
        if page_num != -1:
            self.notebook.remove_page(page_num)
            if name in self.buffers:
                del self.buffers[name]
            if name in self.notes_data:
                del self.notes_data[name]

    def add_new_tab(self, button):
        name = self.tab_name_entry.get_text().strip()
        
        # If the name is empty, generate a new name (e.g., New 1, New 2, ...)
        if not name:
            name_base = "New"
            idx = 1
            while f"{name_base} {idx}" in self.buffers:
                idx += 1
            name = f"{name_base} {idx}"
        
        # If the name already exists, switch to the existing tab
        if name in self.buffers:
            self.notebook.set_current_page(
                list(self.buffers.keys()).index(name)
            )
            return

        # Add the new note tab to the data and UI
        self.notes_data[name] = ""
        self.add_note_tab(name)  # This method already adds the tab

        # Set the current page to the newly created tab
        self.notebook.set_current_page(self.notebook.get_n_pages() - 1)

        # Get the current page (the newly added tab's content)
        current_page = self.notebook.get_nth_page(self.notebook.get_current_page())

        # Grab the TextView of the newly added tab and set focus
        textview = current_page.get_children()[0]  # The TextView is inside the ScrolledWindow
        textview.grab_focus()  # Set focus to the TextView

        # Clear the tab name entry field for the next tab name
        self.tab_name_entry.set_text("")


    def on_entry_activate(self, entry):
        self.add_new_tab(None)

    def on_tab_double_click(self, widget, event, label):
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            old_name = label.get_text()

            dialog = Gtk.Dialog(title="Rename Tab", parent=self, flags=Gtk.DialogFlags.MODAL)
            dialog.set_default_size(200, 50)
            dialog.set_resizable(False)
            dialog.set_decorated(True)
            dialog.set_type_hint(Gdk.WindowTypeHint.DIALOG)

            '''
            dialog = Gtk.Dialog(title="Rename Tab", parent=self, flags=Gtk.DialogFlags.MODAL)
            dialog.set_default_size(200, 50)
            dialog.set_resizable(False)
            dialog.set_decorated(False)  # Remove all decorations

            # Custom header bar with just a close button
            header_bar = Gtk.HeaderBar()
            header_bar.set_title("Rename Tab")
            header_bar.set_show_close_button(True)
            dialog.set_titlebar(header_bar)
            '''

            content_area = dialog.get_content_area()
            entry = Gtk.Entry()
            entry.set_text(old_name)
            content_area.add(entry)

            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button("OK", Gtk.ResponseType.OK)
            entry.grab_focus()
            entry.connect("activate", lambda e: dialog.response(Gtk.ResponseType.OK))

            dialog.show_all()
            response = dialog.run()

            new_name = entry.get_text().strip()
            if response == Gtk.ResponseType.OK and new_name and new_name != old_name:
                if new_name in self.notes_data:
                    self.show_message("Tab name already exists.")
                else:
                    label.set_text(new_name)
                    self.notes_data[new_name] = self.notes_data.pop(old_name)
                    self.buffers[new_name] = self.buffers.pop(old_name)
                    save_notes(self.notes_data)

            dialog.destroy()

    def show_message(self, text):
        md = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=text,
        )
        md.run()
        md.destroy()


class TrayApp:
    def __init__(self):
        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_from_icon_name("accessories-text-editor")
        self.status_icon.set_tooltip_text("Click to open notes")
        self.status_icon.set_visible(True)

        
        self.status_icon.connect("activate", self.icon_clicked)
        self.popup = None

    def icon_clicked(self, icon):
        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        _, x, y = pointer.get_position()

        if self.popup is None or not self.popup.is_visible():
            self.popup = NotesPopup(x, y)
        elif self.popup.is_visible():
            self.popup.hide()
            self.popup.on_close()
        else:
            self.popup.present()
            self.popup.grab_focus()


    def run(self):
        Gtk.main()


if __name__ == "__main__":
    TrayApp().run()