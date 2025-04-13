"""
Main View - Handles the UI components for the LoRA Editor
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ui.treeview import LoraTreeview
from ui.controls import NavigationButtons, StatusBar
from lora_database import LoraHistoryEntry

logger = logging.getLogger(__name__)

class MainView:
    """Main view class for the LoRA Editor UI"""

    def __init__(self, root: tk.Tk):
        """Initialize the main view with the root window"""
        self.root = root
        self.root.title("LoRA Configuration Editor")
        self.root.geometry("1100x925")

        # Configure style for dark theme
        self._configure_style()

        # Initialize variables
        self.folder_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.default_var = tk.StringVar()
        self.show_inactive_var = tk.BooleanVar(value=True)
        self.civitai_url_var = tk.StringVar()
        self.hf_url_var = tk.StringVar()
        self.progress_var = tk.IntVar()

        # Create menu bar
        self._create_menu_bar()

        # Create UI components
        self.container = ttk.Frame(self.root, padding=10)
        self.container.grid(row=0, column=0, sticky="nsew")

        # Configure root window grid
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)

        # Create UI sections
        self._create_title_section()
        self._create_folder_section()
        self._create_download_section()
        self._create_default_section()
        self._create_search_section()
        self._create_main_section()
        self._create_buttons()
        self._create_progress_bar()

        # Create context menu
        self._create_context_menu()

        # Create status bar
        self.status_bar = StatusBar(self.root)
        self.status_bar.grid(row=1, column=0, sticky="ew")

    def _configure_style(self):
        """Configure the UI style"""
        style = ttk.Style()
        style.configure("Treeview", background="#2e2e2e", foreground="white", fieldbackground="#2e2e2e")
        style.configure("Treeview.Heading", background="#2e2e2e", foreground="white")
        style.configure("TLabelframe.Label", foreground="white")  # For frame labels
        style.configure("TLabel", foreground="white")  # For regular labels
        style.configure("TCheckbutton", foreground="white")  # For checkbuttons

    def _create_menu_bar(self):
        """Create the menu bar"""
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # Create menus
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.updates_menu = tk.Menu(self.menu_bar, tearoff=0)

        # Add menus to menu bar
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.menu_bar.add_cascade(label="Updates", menu=self.updates_menu)

        # File menu items
        self.file_menu.add_command(label="Save Configuration")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit menu items
        self.edit_menu.add_command(label="Add New LoRA")
        self.edit_menu.add_command(label="Edit Selected LoRA")
        self.edit_menu.add_command(label="Delete Selected LoRA")

        # Updates menu items
        self.updates_menu.add_command(label="Check Selected for Updates")
        self.updates_menu.add_command(label="Check All for Updates")

        logger.info("Menu bar created with File, Edit, and Updates menus")

    def _add_select_all_behavior(self, entry_widget):
        """Add select-all-on-double-click behavior to an entry widget"""
        # Directly bind to the widget to ensure consistent behavior
        entry_widget.bind('<Double-1>', lambda event: self._select_all_text(entry_widget))

    def _select_all_text(self, widget):
        """Select all text in the widget"""
        widget.select_range(0, tk.END)
        # Set focus to ensure the selection is visible
        widget.focus_set()

    def _create_title_section(self):
        """Create the title section"""
        title_frame = ttk.Frame(self.container)
        title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(title_frame, text="LoRA Configuration Editor", font=('Helvetica', 16, 'bold')).pack(side=tk.LEFT)

        # Show inactive checkbox
        show_inactive_check = ttk.Checkbutton(
            title_frame,
            text="Show Inactive",
            variable=self.show_inactive_var
        )
        show_inactive_check.pack(side=tk.RIGHT)

    def _create_folder_section(self):
        """Create the folder selection section"""
        locations_frame = ttk.LabelFrame(self.container, text="Comfyui LoRA Folder", padding=10)
        locations_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # LoRA folder selection
        folder_frame = ttk.Frame(locations_frame)
        folder_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(folder_frame, text="LoRA Folder:").pack(side=tk.LEFT, padx=(0, 5))
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=60)
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self._add_select_all_behavior(folder_entry)
        self.browse_button = ttk.Button(folder_frame, text="Browse")
        self.browse_button.pack(side=tk.LEFT)

    def _create_download_section(self):
        """Create the download section"""
        download_frame = ttk.LabelFrame(self.container, text="Download LoRAs", padding=10)
        download_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        # CivitAI URL
        civitai_frame = ttk.Frame(download_frame)
        civitai_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(civitai_frame, text="CivitAI URL:").pack(side=tk.LEFT, padx=(0, 5))
        civitai_entry = ttk.Entry(civitai_frame, textvariable=self.civitai_url_var, width=80)
        civitai_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        # Directly bind to ensure it works correctly
        civitai_entry.bind('<Double-1>', lambda event: self._select_all_text(civitai_entry))
        self.civitai_button = ttk.Button(civitai_frame, text="Download from CivitAI")
        self.civitai_button.pack(side=tk.LEFT)

        # HuggingFace URL
        hf_frame = ttk.Frame(download_frame)
        hf_frame.pack(fill=tk.X)
        ttk.Label(hf_frame, text="HuggingFace URL:").pack(side=tk.LEFT, padx=(0, 5))
        hf_entry = ttk.Entry(hf_frame, textvariable=self.hf_url_var, width=80)
        hf_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        # Directly bind to ensure it works correctly
        hf_entry.bind('<Double-1>', lambda event: self._select_all_text(hf_entry))
        self.hf_button = ttk.Button(hf_frame, text="Download from HuggingFace")
        self.hf_button.pack(side=tk.LEFT)

    def _create_default_section(self):
        """Create the default LoRA section"""
        default_frame = ttk.LabelFrame(self.container, text="Default LoRA", padding=10)
        default_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        # Default LoRA selection
        ttk.Label(default_frame, text="Default LoRA:").pack(side=tk.LEFT, padx=(0, 5))
        self.default_combo = ttk.Combobox(default_frame, textvariable=self.default_var, width=60)
        self.default_combo.pack(side=tk.LEFT)

    def _create_search_section(self):
        """Create the search section"""
        search_frame = ttk.Frame(self.container)
        search_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT)
        self._add_select_all_behavior(search_entry)

    def _create_main_section(self):
        """Create the main treeview section"""
        main_frame = ttk.Frame(self.container)
        main_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 10))

        # Create navigation buttons frame with border
        nav_frame = ttk.LabelFrame(main_frame, text="Move", padding=(2, 2))
        nav_frame.grid(row=0, column=0, sticky="ns", padx=2)

        # Create navigation buttons with command dictionary
        nav_commands = {
            'up': lambda: None,  # Placeholder, will be set by controller
            'down': lambda: None,
            'up_five': lambda: None,
            'down_five': lambda: None
        }
        self.nav_buttons = NavigationButtons(nav_frame, nav_commands)

        # Create treeview
        columns = ("ID", "Status", "Name", "File", "Weight", "Trigger Words", "URL", "Update")
        self.tree = LoraTreeview(
            main_frame,
            columns=columns,
            selectmode="extended",
            show="headings"  # Only show column headings, not tree structure
        )
        self.tree.grid(row=0, column=1, sticky="nsew")

        # Configure column widths and headings
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Status", width=80, anchor="center")
        self.tree.column("Name", width=200)
        self.tree.column("File", width=200)
        self.tree.column("Weight", width=60, anchor="center")
        self.tree.column("Trigger Words", width=200)
        self.tree.column("URL", width=200)
        self.tree.column("Update", width=100, anchor="center")

        # Configure column headings
        for col in columns:
            self.tree.heading(col, text=col)

        # Configure the update tag with dark teal color
        self.tree.tag_configure('update', background='#008080', foreground='white')

        # Bind context menu to tree now that it's created
        self._bind_context_menu_to_tree()

        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Configure main frame grid weights
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # Make tree container expand to fill available space
        self.container.grid_rowconfigure(5, weight=1)

    def _create_buttons(self):
        """Create the main action buttons"""
        btn_frame = ttk.Frame(self.container)
        btn_frame.grid(row=6, column=0, pady=10)

        button_configs = [
            ("Add Entry", "⊕"),
            ("Edit Entry", "✎"),
            ("Delete Entry", "✖"),
            ("De / Active", "⚡"),
            ("Save", "💾"),
            ("Refresh Files", "🔄"),
            ("Reset LoRA", "⚠")
        ]

        self.buttons = {}
        for text, symbol in button_configs:
            btn = ttk.Button(
                btn_frame,
                text=f"{symbol} {text}",
                width=15
            )
            btn.pack(side=tk.LEFT, padx=5)
            self.buttons[text.lower().replace(" ", "_")] = btn

    def _create_progress_bar(self):
        """Create the progress bar"""
        progress_frame = ttk.Frame(self.container)
        progress_frame.grid(row=7, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(progress_frame, text="Progress:").pack(side=tk.LEFT, padx=(0, 5))
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            variable=self.progress_var
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def set_folder_path(self, path: str):
        """Set the folder path in the UI"""
        self.folder_var.set(path)

    def get_folder_path(self) -> str:
        """Get the folder path from the UI"""
        return self.folder_var.get()

    def set_default_lora(self, lora: str):
        """Set the default LoRA in the UI"""
        self.default_var.set(lora)

    def get_default_lora(self) -> str:
        """Get the default LoRA from the UI"""
        return self.default_var.get()

    def update_available_loras(self, loras: List[str]):
        """Update the list of available LoRAs in the combobox"""
        self.default_combo['values'] = loras

    def clear_tree(self):
        """Clear all items from the treeview"""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def add_tree_item(self, entry: LoraHistoryEntry):
        """Add a LoRA entry to the treeview

        Returns:
            The ID of the inserted item in the treeview
        """
        status = "Active" if entry.is_active else "Inactive"
        # Use display_order + 1 for the visible ID column (1-based indexing for users)
        # but store the actual database ID as a tag for internal use
        values = (
            entry.display_order + 1,  # Show 1-based index in the ID column
            status,
            entry.display_name,
            entry.file_name,
            entry.weight,
            entry.trigger_words,
            entry.url,
            "Update Available" if entry.has_update else "Current"  # Use has_update flag to determine status
        )
        logger.debug(f"Adding tree item: ID={entry.id}, Name={entry.display_name}, Display Order={entry.display_order}")
        item_id = self.tree.insert("", "end", values=values, tags=(str(entry.id),))  # Store actual ID as a tag
        logger.debug(f"Added tree item with ID: {item_id}")
        return item_id

    def get_item_values(self, item_id: str) -> tuple:
        """Get the values for a specific item in the treeview"""
        values = self.tree.item(item_id)['values']
        # Replace the display order with the actual database ID stored in tags
        if values:
            tags = self.tree.item(item_id)['tags']
            if tags:
                # Find the ID tag (the one that's not 'update')
                id_tag = None
                for tag in tags:
                    if tag != 'update':
                        id_tag = tag
                        break

                if id_tag is not None:
                    values = list(values)
                    values[0] = int(id_tag)  # Replace display order with actual ID
                    values = tuple(values)
        return values

    def get_selected_items(self):
        """Get the currently selected items in the treeview

        Returns:
            list: List of selected item IDs
        """
        return self.tree.selection()

    def show_message(self, title: str, message: str, message_type: str = "info"):
        """Show a message dialog"""
        if message_type == "info":
            messagebox.showinfo(title, message)
        elif message_type == "warning":
            messagebox.showwarning(title, message)
        elif message_type == "error":
            messagebox.showerror(title, message)

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Show a yes/no dialog and return the result"""
        return messagebox.askyesno(title, message)

    def ask_folder(self) -> str:
        """Show a folder selection dialog and return the selected path"""
        return filedialog.askdirectory()

    def set_status(self, message: str):
        """Set the status bar message"""
        self.status_bar.set_status(message)

    def set_progress(self, value: int):
        """Set the progress bar value"""
        try:
            # Only show/hide the progress bar when needed to reduce UI updates
            if value > 0 and value < 100:
                # Only show if not already visible
                if not hasattr(self, '_progress_visible') or not self._progress_visible:
                    if not self.progress_bar.winfo_ismapped():
                        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
                    self._progress_visible = True
            elif value >= 100:
                # Only hide if currently visible
                if hasattr(self, '_progress_visible') and self._progress_visible:
                    if self.progress_bar.winfo_ismapped():
                        self.progress_bar.pack_forget()
                    self._progress_visible = False

            # Update progress value without forcing UI updates
            self.progress_var.set(value)
        except Exception as e:
            logger.error(f"Error updating progress bar: {e}")

    def start_progress(self):
        """Start the indeterminate progress indicator"""
        try:
            # Show the progress bar if not already visible
            if not hasattr(self, '_progress_visible') or not self._progress_visible:
                if not self.progress_bar.winfo_ismapped():
                    self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._progress_visible = True

            # Start the indeterminate mode
            self.progress_bar.config(mode='indeterminate')
            self.progress_bar.start(10)  # Speed of 10ms
        except Exception as e:
            logger.error(f"Error starting progress indicator: {e}")

    def stop_progress(self):
        """Stop the indeterminate progress indicator"""
        try:
            # Stop the animation
            self.progress_bar.stop()

            # Reset to determinate mode
            self.progress_bar.config(mode='determinate')

            # Hide the progress bar
            if hasattr(self, '_progress_visible') and self._progress_visible:
                if self.progress_bar.winfo_ismapped():
                    self.progress_bar.pack_forget()
                self._progress_visible = False
        except Exception as e:
            logger.error(f"Error stopping progress indicator: {e}")

    def bind_show_inactive_changed(self, callback: Callable):
        """Bind a callback to the show inactive checkbox"""
        self.show_inactive_var.trace_add('write', lambda *args: callback())

    def bind_search_changed(self, callback: Callable):
        """Bind a callback to the search field"""
        self.search_var.trace_add('write', lambda *args: callback())

    def bind_default_lora_changed(self, callback: Callable):
        """Bind a callback to the default LoRA combobox"""
        self.default_var.trace_add('write', lambda *args: callback())

    def bind_tree_double_click(self, callback: Callable):
        """Bind a callback to the treeview double click event"""
        self.tree.bind("<Double-1>", callback)

    def _create_context_menu(self):
        """Create a context menu for the treeview"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Check for Updates")

    def _bind_context_menu_to_tree(self):
        """Bind the context menu to the treeview"""
        if hasattr(self, 'tree'):
            self.tree.bind("<Button-3>", self._show_context_menu)
            logger.info("Context menu bound to tree")
        else:
            logger.warning("Tree not created yet, cannot bind context menu")

    def _show_context_menu(self, event):
        """Show the context menu on right-click"""
        # Select the item under the cursor
        item = self.tree.identify_row(event.y)
        if item:
            # Select the item
            self.tree.selection_set(item)
            # Show the context menu
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def bind_context_menu_command(self, label: str, callback: Callable):
        """Bind a callback to a context menu item"""
        try:
            for i in range(self.context_menu.index('end') + 1):
                if self.context_menu.entrycget(i, 'label') == label:
                    self.context_menu.entryconfig(i, command=callback)
                    logger.info(f"Bound context menu item {label} to callback")
                    return
            logger.warning(f"Could not find context menu item {label}")
        except Exception as e:
            logger.error(f"Error binding context menu command {label}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def bind_tree_reordered(self, callback: Callable):
        """Bind a callback to the treeview reordered event"""
        self.tree.bind("<<TreeviewReordered>>", lambda e: callback())

    def bind_button(self, button_name: str, callback: Callable):
        """Bind a callback to a button"""
        if button_name in self.buttons:
            self.buttons[button_name].configure(command=callback)

    def bind_browse_button(self, callback: Callable):
        """Bind a callback to the browse button"""
        self.browse_button.configure(command=callback)

    def bind_civitai_button(self, callback: Callable):
        """Bind a callback to the CivitAI download button"""
        self.civitai_button.configure(command=callback)

    def bind_hf_button(self, callback: Callable):
        """Bind a callback to the HuggingFace download button"""
        self.hf_button.configure(command=callback)

    def set_nav_commands(self, commands: Dict[str, Callable]):
        """Set the navigation button commands"""
        self.nav_buttons.set_commands(commands)

    def bind_menu_command(self, menu_name: str, item_label: str, callback: Callable):
        """Bind a callback to a menu item"""
        try:
            # Use the menu attributes directly
            if menu_name == "File":
                menu = self.file_menu
            elif menu_name == "Edit":
                menu = self.edit_menu
            elif menu_name == "Updates":
                menu = self.updates_menu
            else:
                logger.warning(f"Unknown menu: {menu_name}")
                return

            # Find the menu item by label
            for i in range(menu.index('end') + 1):
                try:
                    current_label = menu.entrycget(i, 'label')
                    if current_label == item_label:
                        menu.entryconfig(i, command=callback)
                        logger.info(f"Bound {menu_name} > {item_label} to callback")
                        return
                except tk.TclError as e:
                    # Skip separators
                    logger.debug(f"Skipping menu item {i}: {str(e)}")
                    continue

            logger.warning(f"Could not find menu item {menu_name} > {item_label}")
        except Exception as e:
            logger.error(f"Error binding menu command {menu_name} > {item_label}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def highlight_item_by_id(self, item_id: int):
        """Highlight an item in the treeview by its ID"""
        try:
            # Find the item with the given ID
            for item in self.tree.get_children():
                values = self.tree.item(item, 'values')
                tags = self.tree.item(item, 'tags')
                if values and int(values[0]) == item_id:
                    # Preserve the ID tag and add the update tag
                    new_tags = [tag for tag in tags if tag != 'update']
                    new_tags.append('update')
                    self.tree.item(item, tags=tuple(new_tags))
                    logger.debug(f"Highlighted item with ID {item_id}")
                    return
            logger.warning(f"Could not find item with ID {item_id} to highlight")
        except Exception as e:
            logger.error(f"Error highlighting item with ID {item_id}: {e}")

    def update_lora_status(self, lora_id: int, status: str):
        """Update the update status column for a LoRA"""
        try:
            # Find the item with the given ID in the tags
            for item in self.tree.get_children():
                tags = self.tree.item(item, 'tags')
                # Check if this item has the matching ID tag
                if tags and str(lora_id) in tags:
                    # Get current values
                    values = list(self.tree.item(item, 'values'))
                    # Update status column (index 7)
                    values[7] = status

                    # Update the item
                    self.tree.item(item, values=tuple(values))
                    logger.debug(f"Updated status for LoRA ID {lora_id} to '{status}'")
                    return
            logger.warning(f"Could not find item with ID {lora_id} to update status")
        except Exception as e:
            logger.error(f"Error updating status for LoRA ID {lora_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
