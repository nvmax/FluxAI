import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Text, WORD, DISABLED, NORMAL, END
from ttkthemes import ThemedTk
import threading
from setup.setup_support import SetupManager, PreSetupManager, BASE_MODELS, CHECKPOINTS
import os
import json
import shutil
import logging
from pathlib import Path
import asyncio
import aiohttp
import requests
from huggingface_hub import HfApi
import webbrowser

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/setup.log', mode='w', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class SetupUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FluxAI Discord Bot Setup")

        # Set theme
        self.root.set_theme("black")  # Using 'arc' theme, you can change to any other available theme

        # Initialize setup manager
        self.setup_manager = SetupManager()

        # Create variables for form fields
        self.create_variables()

        # Create main UI
        self.create_ui()

        # Load existing values AFTER UI is created
        self.load_existing_values()

    def create_variables(self):
        # Pre-Setup Variables
        self.comfyui_dir = tk.StringVar()

        # Bot Setup Variables
        self.base_dir = tk.StringVar()
        self.hf_token = tk.StringVar()
        self.civitai_token = tk.StringVar()
        self.discord_token = tk.StringVar()
        self.bot_server = tk.StringVar(value="")
        self.server_address = tk.StringVar(value="")
        self.allowed_servers = tk.StringVar()
        self.channel_ids = tk.StringVar()
        self.bot_manager_role_id = tk.StringVar()
        self.selected_checkpoint = tk.StringVar(value="Select a checkpoint...")

        # Progress tracking
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready to install")

        # AI Setup Variables
        self.ai_provider = tk.StringVar(value="lmstudio")
        self.enable_prompt_enhancement = tk.BooleanVar(value=False)
        self.lmstudio_host = tk.StringVar(value="")
        self.lmstudio_port = tk.StringVar(value="")
        self.gemini_api_key = tk.StringVar()
        self.xai_api_key = tk.StringVar()
        self.openai_api_key = tk.StringVar()
        self.anthropic_api_key = tk.StringVar()

        # AI Model Variables
        self.gemini_model = tk.StringVar(value="gemini-pro")
        self.xai_model = tk.StringVar(value="grok-beta")
        self.openai_model = tk.StringVar(value="gpt-3.5-turbo")
        self.anthropic_model = tk.StringVar(value="claude-3-opus-20240229")

        # Content Filter Variables
        self.toxic_threshold = tk.StringVar(value="0.95")
        self.harmful_threshold = tk.StringVar(value="0.9")
        self.sexual_threshold = tk.StringVar(value="0.9")
        self.child_threshold = tk.StringVar(value="0.1")
        self.hate_threshold = tk.StringVar(value="0.7")
        self.violence_threshold = tk.StringVar(value="0.8")
        self.allow_adult_content = tk.BooleanVar(value=True)

        # Warning and Ban Variables
        self.max_warnings = tk.StringVar(value="3")
        self.enable_permanent_ban = tk.BooleanVar(value=True)

    def create_ui(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)

        # Create Pre-Setup tab (first tab)
        self.presetup_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.presetup_tab, text='Pre-Setup')
        self.create_presetup_tab()

        # Create Bot Setup tab
        self.bot_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.bot_tab, text='Bot Setup')
        self.create_bot_tab()

        # Create AI Setup tab
        self.ai_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.ai_tab, text='AI Setup')
        self.create_ai_tab()

        # Create Content tab
        self.content_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.content_tab, text='Content')
        self.create_content_tab()

    def create_presetup_tab(self):
        """Create the Pre-Setup tab UI elements"""
        # Initialize PreSetupManager
        self.presetup_manager = PreSetupManager()

        # Create main container frame
        main_frame = ttk.Frame(self.presetup_tab, padding="10")
        main_frame.pack(fill='both', expand=True)

        # Configure column weights
        main_frame.grid_columnconfigure(0, weight=1, minsize=160)  # Label column
        main_frame.grid_columnconfigure(1, weight=4, minsize=480)  # Entry column
        main_frame.grid_columnconfigure(2, weight=1, minsize=160)  # Button column

        current_row = 0

        # Title and description for Instructions
        title_label = ttk.Label(main_frame, text="ComfyUI Installation Instructions (40xx/50xx GPUs)", font=("TkDefaultFont", 12, "bold"))
        title_label.grid(row=current_row, column=0, columnspan=3, padx=5, pady=10, sticky="nw")
        current_row += 1

        # ComfyUI Installation Instructions
        comfyui_frame = ttk.LabelFrame(main_frame, text="Installation Steps", padding=5)
        comfyui_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

        ttk.Label(comfyui_frame, text="For best performance with 40xx and 50xx series GPUs:", justify="left").pack(anchor="w", padx=5, pady=2)
        ttk.Label(comfyui_frame, text="1. Download latest ComfyUI optimized build:", justify="left").pack(anchor="w", padx=5, pady=2)

        url = "https://github.com/comfyanonymous/ComfyUI/releases/download/latest/ComfyUI_cu128_50XX.7z"
        link_label = ttk.Label(comfyui_frame, text=url, style="Hyperlink.TLabel", cursor="hand2")
        link_label.pack(anchor="w", padx=25, pady=2)
        link_label.bind("<Button-1>", lambda e: self.open_url(url))

        style = ttk.Style()
        style.configure("Hyperlink.TLabel", foreground="#008B8B", font=("TkDefaultFont", 10, "underline"))

        ttk.Label(comfyui_frame, text="2. Open update folder and run:\n   update_comfyui_and_python_dependencies.bat", justify="left").pack(anchor="w", padx=5, pady=2)
        ttk.Label(comfyui_frame, text="3. From required_files folder (Bot folder), copy 'For ComfyUI portable.bat' to your\n   main ComfyUI directory and run it to install Triton and Sage attention", justify="left").pack(anchor="w", padx=5, pady=2)
        ttk.Label(comfyui_frame, text="4. Edit run_nvidia_gpu.bat and add:\n   --use-sage-attention\n   to the end for greatly improved performance", justify="left").pack(anchor="w", padx=5, pady=2)
        ttk.Label(comfyui_frame, text="5. Continue installing custom nodes below, make sure to click Install GitPython button first", justify="left").pack(anchor="w", padx=5, pady=2)

        current_row += 1

        ttk.Separator(main_frame, orient='horizontal').grid(row=current_row, column=0, columnspan=3, sticky='ew', pady=5)
        current_row += 1

        # Custom Nodes Installation Section
        title_label = ttk.Label(main_frame, text="ComfyUI Custom Nodes Installation", font=("TkDefaultFont", 12, "bold"))
        title_label.grid(row=current_row, column=0, columnspan=3, padx=5, pady=10, sticky="nw")
        current_row += 1

        description_text = "This will install essential custom nodes for ComfyUI used by FluxComfy Bot. Make sure to specify your ComfyUI installation directory before proceeding, Where run_nvidia_gpu.bat is located. "
        description_label = ttk.Label(main_frame, text=description_text, wraplength=700)
        description_label.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nw")
        current_row += 1

        # ComfyUI Directory Section
        dir_frame = ttk.LabelFrame(main_frame, text="ComfyUI Location", padding=10)
        dir_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        dir_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(dir_frame, text="ComfyUI Directory:", anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(dir_frame, textvariable=self.comfyui_dir).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(dir_frame, text="Browse", command=self.select_comfyui_directory).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        current_row += 1

        # Progress and Status Section
        progress_frame = ttk.LabelFrame(main_frame, text="Installation Progress", padding=10)
        progress_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.presetup_status_var = tk.StringVar(value="Ready to install custom nodes")
        ttk.Label(progress_frame, textvariable=self.presetup_status_var).grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.presetup_progress_var = tk.DoubleVar()
        self.presetup_progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=600,
            mode="determinate",
            variable=self.presetup_progress_var
        )
        self.presetup_progress_bar.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        current_row += 1

        # Action buttons
        button_frame = ttk.Frame(main_frame, padding=5)
        button_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.install_git_button = ttk.Button(
            button_frame,
            text="Install GitPython",
            command=self.install_gitpython
        )
        self.install_git_button.grid(row=0, column=0, padx=10, pady=5, sticky="e")

        self.presetup_button = ttk.Button(
            button_frame,
            text="Install Custom Nodes",
            command=self.run_presetup
        )
        self.presetup_button.grid(row=0, column=1, padx=10, pady=5, sticky="w")

    def create_bot_tab(self):
        """Create the Bot Setup tab UI elements"""
        # Create main container frame
        main_frame = ttk.Frame(self.bot_tab, padding="10")
        main_frame.pack(fill='both', expand=True)

        # Configure column weights (1/5, 2/3, remainder)
        main_frame.grid_columnconfigure(0, weight=1, minsize=160)  # Label column (1/5)
        main_frame.grid_columnconfigure(1, weight=4, minsize=480)  # Entry column (2/3)
        main_frame.grid_columnconfigure(2, weight=1, minsize=160)  # Button column

        current_row = 0

        # ComfyUI Directory Section
        dir_frame = ttk.LabelFrame(main_frame, text="ComfyUI Directory", padding=10)
        dir_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        dir_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(dir_frame, text="Base Directory:", anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(dir_frame, textvariable=self.base_dir).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(dir_frame, text="Browse", command=self.select_base_directory).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        current_row += 1

        # API Tokens Section
        token_frame = ttk.LabelFrame(main_frame, text="API Tokens", padding=10)
        token_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        token_frame.grid_columnconfigure(1, weight=1)

        # HuggingFace Token
        ttk.Label(token_frame, text="HuggingFace Token:", anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(token_frame, textvariable=self.hf_token, show="*").grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(token_frame, text="Validate", command=lambda: self.validate_token("hf")).grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # CivitAI Token
        ttk.Label(token_frame, text="CivitAI Token:", anchor="e").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(token_frame, textvariable=self.civitai_token, show="*").grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(token_frame, text="Validate", command=lambda: self.validate_token("civitai")).grid(row=1, column=2, padx=5, pady=5, sticky="w")

        # Discord Token
        ttk.Label(token_frame, text="Discord Token:", anchor="e").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(token_frame, textvariable=self.discord_token, show="*").grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        current_row += 1

        # Server Configuration Section
        server_frame = ttk.LabelFrame(main_frame, text="Server Configuration", padding=10)
        server_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        server_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(server_frame, text="Bot Server:", anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(server_frame, textvariable=self.bot_server).grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        ttk.Label(server_frame, text="Server Address:", anchor="e").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(server_frame, textvariable=self.server_address).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        current_row += 1

        # Discord Configuration Section
        discord_frame = ttk.LabelFrame(main_frame, text="Discord Configuration", padding=10)
        discord_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        discord_frame.grid_columnconfigure(1, weight=1)

        # Allowed Server IDs
        ttk.Label(discord_frame, text="Allowed Server IDs:", anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="ne")
        self.server_ids_text = tk.Text(discord_frame, height=3)
        self.server_ids_text.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Channel IDs
        ttk.Label(discord_frame, text="Channel IDs:", anchor="e").grid(row=1, column=0, padx=5, pady=5, sticky="ne")
        self.channel_ids_text = tk.Text(discord_frame, height=3)
        self.channel_ids_text.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Bot Manager Role ID
        ttk.Label(discord_frame, text="Bot Manager Role ID:", anchor="e").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(discord_frame, textvariable=self.bot_manager_role_id).grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        current_row += 1

        # Workflow Selection Section
        workflow_frame = ttk.LabelFrame(main_frame, text="Workflow Selection", padding=10)
        workflow_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        workflow_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(workflow_frame, text="Select Workflow:", anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        config_path = os.path.join(os.getcwd(), 'config')
        workflow_files = []
        if os.path.exists(config_path):
            for file in os.listdir(config_path):
                if file.endswith('.json') and file not in ['lora.json', 'ratios.json', 'Redux.json', 'Reduxprompt.json', 'Pulid6GB.json', 'Pulid8GB.json', 'Pulid10GB.json', 'Pulid12GB.json', 'Pulid24GB.json', 'PulidFluxDev.json', 'Video.json']:
                    workflow_files.append(file)
        workflow_combo = ttk.Combobox(workflow_frame, textvariable=self.selected_checkpoint,
                                    values=sorted(workflow_files), state="readonly")
        workflow_combo.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        workflow_combo.bind("<<ComboboxSelected>>", self.on_checkpoint_selected)
        current_row += 1

        # Installation Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Installation Progress", padding=10)
        progress_frame.grid(row=current_row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var, wraplength=600)
        self.status_label.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        # Create a frame to center the install button
        button_frame = ttk.Frame(progress_frame)
        button_frame.grid(row=2, column=0, pady=10)
        button_frame.grid_columnconfigure(0, weight=1)  # This helps center the button

        self.install_button = ttk.Button(button_frame, text="Install",
                                       command=self.start_installation, width=20)  # Set fixed width
        self.install_button.grid(row=0, column=0)

    def create_ai_tab(self):
        # Create main container with grid
        main_frame = ttk.Frame(self.ai_tab, padding="10")
        main_frame.pack(fill='both', expand=True)

        # Configure column weights (1/5, 4/5)
        main_frame.grid_columnconfigure(0, weight=1, minsize=150)  # Label column (1/5)
        main_frame.grid_columnconfigure(1, weight=4, minsize=600)  # Entry column (4/5)

        current_row = 0

        # AI Configuration Section
        ai_config_frame = ttk.LabelFrame(main_frame, text="AI Configuration", padding=10)
        ai_config_frame.grid(row=current_row, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        ai_config_frame.grid_columnconfigure(1, weight=1)

        # AI Provider Selection
        ttk.Label(ai_config_frame, text="AI Provider:", anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.ai_provider_combo = ttk.Combobox(ai_config_frame, textvariable=self.ai_provider,
                    values=["lmstudio", "openai", "xai", "gemini", "anthropic"],
                    state="readonly")
        self.ai_provider_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.ai_provider_combo.bind("<<ComboboxSelected>>", self.on_ai_provider_changed)

        # Enable Prompt Enhancement
        ttk.Label(ai_config_frame, text="Prompt Enhancement:", anchor="e").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Checkbutton(ai_config_frame, text="Enable",
                       variable=self.enable_prompt_enhancement).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Model Selection
        ttk.Label(ai_config_frame, text="Model Name:", anchor="e").grid(row=2, column=0, padx=5, pady=5, sticky="e")

        # Create a frame to hold all model entry fields
        self.model_frame = ttk.Frame(ai_config_frame)
        self.model_frame.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Gemini model entry
        self.gemini_model_entry = ttk.Entry(self.model_frame, textvariable=self.gemini_model)

        # XAI model entry
        self.xai_model_entry = ttk.Entry(self.model_frame, textvariable=self.xai_model)

        # OpenAI model entry
        self.openai_model_entry = ttk.Entry(self.model_frame, textvariable=self.openai_model)

        # Anthropic model entry
        self.anthropic_model_entry = ttk.Entry(self.model_frame, textvariable=self.anthropic_model)

        # Initially show the appropriate model entry based on selected provider
        self.update_model_entry()

        current_row += 1

        # LMStudio Configuration Section
        lmstudio_frame = ttk.LabelFrame(main_frame, text="LMStudio Configuration", padding=10)
        lmstudio_frame.grid(row=current_row, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        lmstudio_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(lmstudio_frame, text="LMStudio Host:", anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(lmstudio_frame, textvariable=self.lmstudio_host).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(lmstudio_frame, text="LMStudio Port:", anchor="e").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(lmstudio_frame, textvariable=self.lmstudio_port).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        current_row += 1

        # API Keys Section
        api_frame = ttk.LabelFrame(main_frame, text="API Keys", padding=10)
        api_frame.grid(row=current_row, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        api_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(api_frame, text="XAI API Key:", anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(api_frame, textvariable=self.xai_api_key, show="*").grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(api_frame, text="Gemini API Key:", anchor="e").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(api_frame, textvariable=self.gemini_api_key, show="*").grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(api_frame, text="OpenAI API Key:", anchor="e").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(api_frame, textvariable=self.openai_api_key, show="*").grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(api_frame, text="Anthropic API Key:", anchor="e").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(api_frame, textvariable=self.anthropic_api_key, show="*").grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        current_row += 1

        # Save Button - Create a frame to center the button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=current_row, column=0, columnspan=2, pady=10)
        button_frame.grid_columnconfigure(0, weight=1)  # This helps center the button

        save_button = ttk.Button(button_frame, text="Save AI Configuration",
                               command=self.save_ai_configuration, width=20)  # Set fixed width
        save_button.grid(row=0, column=0)

    def select_comfyui_directory(self):
        """Open file dialog to select ComfyUI directory"""
        directory = filedialog.askdirectory(title="Select ComfyUI Directory")
        if directory:
            # Update comfyui_dir in pre-setup tab
            self.comfyui_dir.set(directory)

            # Also update base_dir in bot setup tab
            self.base_dir.set(directory)
            self.setup_manager.base_dir = directory

            # Update COMFYUI_DIR in .env
            self.setup_manager.update_env_file('COMFYUI_DIR', f'"{directory}"')

            # Construct and save the models path to .env
            models_path = os.path.join(directory, "ComfyUI", "models")
            self.setup_manager.update_env_file('COMFYUI_MODELS_PATH', f'"{models_path}"')

            # Update the status label
            self.presetup_status_var.set(f"ComfyUI directory set to: {directory}")

    def install_gitpython(self):
        """Install GitPython package"""
        self.presetup_status_var.set("Installing GitPython package...")
        self.install_git_button.config(state="disabled")

        def install_thread():
            try:
                import subprocess
                import sys

                # Use system Python executable
                python_exe = sys.executable

                if not python_exe:
                    # As a fallback, try common commands
                    python_commands = ["python", "py"]
                    for cmd in python_commands:
                        try:
                            # Check if the command exists
                            result = subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            if result.returncode == 0:
                                python_exe = cmd
                                break
                        except:
                            continue

                if not python_exe:
                    self.presetup_status_var.set("Error: Could not find Python executable")
                    self.install_git_button.config(state="normal")
                    return

                self.presetup_status_var.set(f"Using Python: {python_exe}")

                # Run pip install command
                cmd = [python_exe, "-m", "pip", "install", "gitpython"]
                self.presetup_status_var.set(f"Running: {' '.join(cmd)}")

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    self.presetup_status_var.set(f"Error installing GitPython: {stderr}")
                    self.install_git_button.config(state="normal")
                else:
                    self.presetup_status_var.set("GitPython installed successfully")
                    self.root.after(2000, lambda: self.presetup_status_var.set("Ready to install custom nodes"))
            except Exception as e:
                self.presetup_status_var.set(f"Error: {str(e)}")
                self.install_git_button.config(state="normal")

        # Run in a separate thread to avoid freezing the UI
        threading.Thread(target=install_thread, daemon=True).start()

    def run_presetup(self):
        """Run the pre-setup process to install custom nodes"""
        comfyui_dir = self.comfyui_dir.get()
        if not comfyui_dir:
            messagebox.showerror("Error", "Please specify ComfyUI directory")
            return

        # Disable the button to prevent multiple clicks
        self.presetup_button.config(state="disabled")

        # Update UI
        self.presetup_status_var.set("Initializing pre-setup...")
        self.presetup_progress_var.set(0)

        # Connect callbacks to the PreSetupManager
        self.presetup_manager.status_callback = self.update_presetup_status
        self.presetup_manager.progress_callback = self.update_presetup_progress

        def presetup_thread():
            try:
                # Set the ComfyUI directory
                self.presetup_manager.set_comfyui_dir(comfyui_dir)

                # Run the pre-setup
                result = self.presetup_manager.run_presetup()

                if result:
                    # On success, update base_dir in bot setup tab if not already set
                    if not self.base_dir.get():
                        self.root.after(0, lambda: self.base_dir.set(comfyui_dir))
                        self.setup_manager.base_dir = comfyui_dir

                    self.root.after(0, lambda: self.presetup_status_var.set("Pre-setup completed successfully"))
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Custom nodes installed successfully. Please start ComfyUI to complete the installation."))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Pre-setup failed. Check the logs for details."))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self.presetup_status_var.set(f"Error: {error_msg}"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Pre-setup failed: {error_msg}"))
            finally:
                self.root.after(0, lambda: self.presetup_button.config(state="normal"))

        # Run in a separate thread to keep the UI responsive
        threading.Thread(target=presetup_thread, daemon=True).start()

    def update_presetup_status(self, message):
        """Update the pre-setup status message in the UI"""
        self.root.after(0, lambda: self.presetup_status_var.set(message))

    def update_presetup_progress(self, value):
        """Update the pre-setup progress bar in the UI"""
        self.root.after(0, lambda: self.presetup_progress_var.set(value))

    def select_base_directory(self):
        directory = filedialog.askdirectory(title="Select ComfyUI Base Directory")
        if directory:
            self.base_dir.set(directory)
            self.setup_manager.base_dir = directory

            # Construct and save the models path to .env
            models_path = os.path.join(directory, "ComfyUI", "models")
            self.setup_manager.update_env_file('COMFYUI_MODELS_PATH', f'"{models_path}"')

            # Update the status label
            self.status_label.config(text=f"ComfyUI directory set to: {directory}\nModels path set to: {models_path}")

    def validate_token(self, token_type):
        """Validate API tokens with better error handling"""
        token = self.hf_token.get() if token_type == "hf" else self.civitai_token.get()

        if not token:
            messagebox.showwarning("Token Required", f"Please enter a {token_type.upper()} token")
            return False

        try:
            if token_type == "hf":
                # First check if we've already successfully downloaded files
                if hasattr(self.setup_manager, 'download_success') and self.setup_manager.download_success:
                    messagebox.showinfo("Success", "Token has been verified through successful downloads!")
                    return True

                # Try file access without API validation
                headers = {'Authorization': f'Bearer {token}'}
                test_url = 'https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors'

                try:
                    response = requests.head(test_url, headers=headers, allow_redirects=True, verify=False)
                    if response.status_code == 200:
                        messagebox.showinfo("Success", "HuggingFace token is valid!")
                        return True
                except:
                    pass

                # Only try API validation as a last resort
                try:
                    api = HfApi(token=token)
                    user = api.whoami()
                    if user is not None:
                        messagebox.showinfo("Success", "HuggingFace token is valid!")
                        return True
                except:
                    pass

                messagebox.showerror("Error", "Could not validate token. However, if you're able to download files, you can proceed with the installation.")
                return False

            elif token_type == "civitai":
                # Use SetupManager's CivitAI validation
                if self.setup_manager.validate_civitai_token(token):
                    messagebox.showinfo("Success", "CivitAI token is valid!")
                    return True
                else:
                    messagebox.showerror("Error", "Invalid CivitAI token. Check the logs for details.")
                    return False

        except Exception as e:
            messagebox.showerror("Error", f"Failed to validate {token_type.upper()} token: {str(e)}")
            return False

    def save_configuration(self):
        """Save configuration with better error handling"""
        try:
            # Load existing environment variables first
            env_vars = self.setup_manager.load_env() or {}

            # Ensure COMMAND_PREFIX is set
            if 'COMMAND_PREFIX' not in env_vars:
                env_vars['COMMAND_PREFIX'] = '/'

            # Update API tokens - only if they have values
            tokens = {
                'HUGGINGFACE_TOKEN': self.hf_token.get(),
                'CIVITAI_API_TOKEN': self.civitai_token.get(),
                'DISCORD_TOKEN': self.discord_token.get(),
                'XAI_API_KEY': self.xai_api_key.get(),
                'OPENAI_API_KEY': self.openai_api_key.get(),
                'GEMINI_API_KEY': self.gemini_api_key.get()
            }

            # Only update tokens that have values
            for key, value in tokens.items():
                if value:
                    env_vars[key] = value

            # Update bot configuration - only if they have values
            bot_config = {
                'BOT_SERVER': self.bot_server.get(),
                'SERVER_ADDRESS': self.server_address.get(),
                'ALLOWED_SERVERS': self.server_ids_text.get('1.0', 'end-1c'),
                'CHANNEL_IDS': self.channel_ids_text.get('1.0', 'end-1c'),
                'BOT_MANAGER_ROLE_ID': self.bot_manager_role_id.get()
            }

            # Only update bot config values that have values
            for key, value in bot_config.items():
                if value and value.strip():  # Check for non-empty strings
                    env_vars[key] = value

            # Update AI configuration - only if changed from existing
            ai_config = {
                'AI_PROVIDER': self.ai_provider.get(),
                'ENABLE_PROMPT_ENHANCEMENT': str(self.enable_prompt_enhancement.get()),
                'LMSTUDIO_HOST': self.lmstudio_host.get(),
                'LMSTUDIO_PORT': self.lmstudio_port.get(),
                'XAI_MODEL': 'grok-beta',
                'OPENAI_MODEL': 'gpt-3.5-turbo',
                'EMBEDDING_MODEL': 'text-embedding-ada-002'
            }

            # Only update AI config if values are different from existing
            for key, value in ai_config.items():
                if value and value != env_vars.get(key, ''):
                    env_vars[key] = value
            # Save the configuration
            if self.setup_manager.save_env(env_vars):
                messagebox.showinfo("Success", "Configuration saved successfully!")

        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
            return False

        return True

    def load_existing_values(self):
        """Load existing values from .env file"""
        try:
            # Load environment variables
            env_vars = self.setup_manager.load_env()

            # Set values in UI if they exist in .env
            if 'COMFYUI_DIR' in env_vars:
                comfyui_dir = env_vars['COMFYUI_DIR'].strip('"')
                self.comfyui_dir.set(comfyui_dir)
                self.base_dir.set(comfyui_dir)  # Sync with bot setup tab
                self.setup_manager.base_dir = comfyui_dir

            if 'HUGGINGFACE_TOKEN' in env_vars:
                self.hf_token.set(env_vars['HUGGINGFACE_TOKEN'])

            if 'CIVITAI_API_TOKEN' in env_vars:
                self.civitai_token.set(env_vars['CIVITAI_API_TOKEN'])

            if 'DISCORD_TOKEN' in env_vars:
                self.discord_token.set(env_vars['DISCORD_TOKEN'])

            if 'BOT_SERVER' in env_vars:
                self.bot_server.set(env_vars['BOT_SERVER'])

            if 'SERVER_ADDRESS' in env_vars:
                self.server_address.set(env_vars['SERVER_ADDRESS'])

            if 'ALLOWED_SERVERS' in env_vars:
                self.server_ids_text.delete('1.0', 'end')  # Clear existing text
                self.server_ids_text.insert('1.0', env_vars['ALLOWED_SERVERS'])

            if 'CHANNEL_IDS' in env_vars:
                self.channel_ids_text.delete('1.0', 'end')  # Clear existing text
                self.channel_ids_text.insert('1.0', env_vars['CHANNEL_IDS'])

            if 'BOT_MANAGER_ROLE_ID' in env_vars:
                self.bot_manager_role_id.set(env_vars['BOT_MANAGER_ROLE_ID'])

            # AI Configuration
            if 'AI_PROVIDER' in env_vars:
                self.ai_provider.set(env_vars['AI_PROVIDER'])

            if 'ENABLE_PROMPT_ENHANCEMENT' in env_vars:
                self.enable_prompt_enhancement.set(env_vars['ENABLE_PROMPT_ENHANCEMENT'].lower() == 'true')

            if 'LMSTUDIO_HOST' in env_vars:
                self.lmstudio_host.set(env_vars['LMSTUDIO_HOST'])

            if 'LMSTUDIO_PORT' in env_vars:
                self.lmstudio_port.set(env_vars['LMSTUDIO_PORT'])

            # API Keys
            if 'XAI_API_KEY' in env_vars:
                self.xai_api_key.set(env_vars['XAI_API_KEY'])

            if 'GEMINI_API_KEY' in env_vars:
                self.gemini_api_key.set(env_vars['GEMINI_API_KEY'])

            if 'OPENAI_API_KEY' in env_vars:
                self.openai_api_key.set(env_vars['OPENAI_API_KEY'])

            if 'ANTHROPIC_API_KEY' in env_vars:
                self.anthropic_api_key.set(env_vars['ANTHROPIC_API_KEY'])

            # Model Names
            if 'GEMINI_MODEL' in env_vars:
                self.gemini_model.set(env_vars['GEMINI_MODEL'])

            if 'XAI_MODEL' in env_vars:
                self.xai_model.set(env_vars['XAI_MODEL'])

            if 'OPENAI_MODEL' in env_vars:
                self.openai_model.set(env_vars['OPENAI_MODEL'])

            if 'ANTHROPIC_MODEL' in env_vars:
                self.anthropic_model.set(env_vars['ANTHROPIC_MODEL'])

            # Content Filter Thresholds
            if 'CONTENT_FILTER_TOXIC_THRESHOLD' in env_vars:
                self.toxic_threshold.set(env_vars['CONTENT_FILTER_TOXIC_THRESHOLD'])

            if 'CONTENT_FILTER_HARMFUL_THRESHOLD' in env_vars:
                self.harmful_threshold.set(env_vars['CONTENT_FILTER_HARMFUL_THRESHOLD'])

            if 'CONTENT_FILTER_SEXUAL_THRESHOLD' in env_vars:
                self.sexual_threshold.set(env_vars['CONTENT_FILTER_SEXUAL_THRESHOLD'])

            if 'CONTENT_FILTER_CHILD_THRESHOLD' in env_vars:
                self.child_threshold.set(env_vars['CONTENT_FILTER_CHILD_THRESHOLD'])

            if 'CONTENT_FILTER_HATE_THRESHOLD' in env_vars:
                self.hate_threshold.set(env_vars['CONTENT_FILTER_HATE_THRESHOLD'])

            if 'CONTENT_FILTER_VIOLENCE_THRESHOLD' in env_vars:
                self.violence_threshold.set(env_vars['CONTENT_FILTER_VIOLENCE_THRESHOLD'])

            if 'CONTENT_FILTER_ALLOW_ADULT' in env_vars:
                self.allow_adult_content.set(env_vars['CONTENT_FILTER_ALLOW_ADULT'].lower() == 'true')

            # Warning and Ban Settings
            if 'MAX_WARNINGS' in env_vars:
                self.max_warnings.set(env_vars['MAX_WARNINGS'])

            if 'ENABLE_PERMANENT_BAN' in env_vars:
                self.enable_permanent_ban.set(env_vars['ENABLE_PERMANENT_BAN'].lower() == 'true')

            # Update the model entry field based on the selected provider
            self.update_model_entry()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load existing values: {str(e)}")

    def on_ai_provider_changed(self, event=None):
        """Handle AI provider selection change"""
        self.update_model_entry()

    def update_model_entry(self):
        """Show the appropriate model entry based on selected provider"""
        # Hide all model entries first
        for widget in self.model_frame.winfo_children():
            widget.grid_forget()

        # Show the appropriate model entry based on selected provider
        provider = self.ai_provider.get()
        if provider == "gemini":
            self.gemini_model_entry.grid(row=0, column=0, sticky="ew")
        elif provider == "xai":
            self.xai_model_entry.grid(row=0, column=0, sticky="ew")
        elif provider == "openai":
            self.openai_model_entry.grid(row=0, column=0, sticky="ew")
        elif provider == "anthropic":
            self.anthropic_model_entry.grid(row=0, column=0, sticky="ew")

    def create_content_tab(self):
        """Create the Content tab UI elements"""
        # Create main container frame
        main_frame = ttk.Frame(self.content_tab, padding="10")
        main_frame.pack(fill='both', expand=True)

        # Configure column weights
        main_frame.grid_columnconfigure(0, weight=1, minsize=160)  # Label column
        main_frame.grid_columnconfigure(1, weight=4, minsize=480)  # Entry column

        current_row = 0

        # Title and description
        title_label = ttk.Label(main_frame, text="Content Filter Settings", font=("TkDefaultFont", 12, "bold"))
        title_label.grid(row=current_row, column=0, columnspan=2, padx=5, pady=10, sticky="nw")
        current_row += 1

        # Description
        description = (
            "These settings control how sensitive the content filter is. Higher values mean less filtering (fewer false positives),\n"
            "while lower values mean more filtering (more false positives).\n\n"
        )
        desc_label = ttk.Label(main_frame, text=description, wraplength=600, justify="left")
        desc_label.grid(row=current_row, column=0, columnspan=2, padx=5, pady=5, sticky="nw")
        current_row += 1

        # Create a frame for the threshold settings
        threshold_frame = ttk.LabelFrame(main_frame, text="Threshold Settings", padding=10)
        threshold_frame.grid(row=current_row, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        threshold_frame.grid_columnconfigure(1, weight=1)
        current_row += 1

        # Function to validate threshold input (0.01 to 1.00)
        def validate_threshold(P):
            if P == "":
                return True
            try:
                value = float(P)
                return 0.01 <= value <= 1.00
            except ValueError:
                return False

        # Register validation command
        validate_cmd = self.root.register(validate_threshold)

        # Toxic content threshold
        ttk.Label(threshold_frame, text="Toxic Content Threshold:", anchor="e").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        toxic_entry = ttk.Entry(threshold_frame, textvariable=self.toxic_threshold, width=10, validate="key", validatecommand=(validate_cmd, '%P'))
        toxic_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        # Add a description of what this threshold controls
        ttk.Label(threshold_frame, text="Controls filtering for toxic, offensive, or harmful language (0.01-1.00)",
                 font=("TkDefaultFont", 8), foreground="gray").grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 2), sticky="w")

        # Harmful content threshold
        ttk.Label(threshold_frame, text="Harmful Content Threshold:", anchor="e").grid(row=2, column=0, padx=5, pady=2, sticky="e")
        harmful_entry = ttk.Entry(threshold_frame, textvariable=self.harmful_threshold, width=10, validate="key", validatecommand=(validate_cmd, '%P'))
        harmful_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        # Add a description
        ttk.Label(threshold_frame, text="Controls filtering for obscene, threatening, or identity-based harmful content (0.01-1.00)",
                 font=("TkDefaultFont", 8), foreground="gray").grid(row=3, column=0, columnspan=2, padx=5, pady=(0, 2), sticky="w")

        # Sexual content threshold
        ttk.Label(threshold_frame, text="Sexual Content Threshold:", anchor="e").grid(row=4, column=0, padx=5, pady=2, sticky="e")
        sexual_entry = ttk.Entry(threshold_frame, textvariable=self.sexual_threshold, width=10, validate="key", validatecommand=(validate_cmd, '%P'))
        sexual_entry.grid(row=4, column=1, padx=5, pady=2, sticky="w")

        # Add a description
        ttk.Label(threshold_frame, text="Controls filtering for sexual or adult content (0.01-1.00)",
                 font=("TkDefaultFont", 8), foreground="gray").grid(row=5, column=0, columnspan=2, padx=5, pady=(0, 2), sticky="w")

        # Child content threshold
        ttk.Label(threshold_frame, text="Child Content Threshold:", anchor="e").grid(row=6, column=0, padx=5, pady=2, sticky="e")

        # Create a validation function specifically for child threshold
        def validate_child_threshold(new_value):
            # First validate that it's a valid threshold value
            if not validate_threshold(new_value):
                return False

            # If it's valid, check if it's above 0.1
            try:
                value = float(new_value)
                if value > 0.1:
                    # Schedule the warning to appear after the entry is updated
                    # This avoids validation issues
                    self.root.after(100, lambda: self.show_child_threshold_warning(value))
                return True
            except ValueError:
                return True  # Let the general validator handle this

        # Register the child threshold validation command
        validate_child_cmd = self.root.register(validate_child_threshold)

        child_entry = ttk.Entry(threshold_frame, textvariable=self.child_threshold, width=10,
                               validate="focusout", validatecommand=(validate_child_cmd, '%P'))
        child_entry.grid(row=6, column=1, padx=5, pady=2, sticky="w")

        # Add a description
        ttk.Label(threshold_frame, text="Controls filtering for child-related inappropriate content (0.01-1.00, strictest filter)",
                 font=("TkDefaultFont", 8), foreground="gray").grid(row=7, column=0, columnspan=2, padx=5, pady=(0, 2), sticky="w")

        # Hate speech threshold
        ttk.Label(threshold_frame, text="Hate Speech Threshold:", anchor="e").grid(row=8, column=0, padx=5, pady=2, sticky="e")
        hate_entry = ttk.Entry(threshold_frame, textvariable=self.hate_threshold, width=10, validate="key", validatecommand=(validate_cmd, '%P'))
        hate_entry.grid(row=8, column=1, padx=5, pady=2, sticky="w")

        # Add a description
        ttk.Label(threshold_frame, text="Controls filtering for hate speech and discriminatory content (0.01-1.00)",
                 font=("TkDefaultFont", 8), foreground="gray").grid(row=9, column=0, columnspan=2, padx=5, pady=(0, 2), sticky="w")

        # Violence threshold
        ttk.Label(threshold_frame, text="Violence Threshold:", anchor="e").grid(row=10, column=0, padx=5, pady=2, sticky="e")
        violence_entry = ttk.Entry(threshold_frame, textvariable=self.violence_threshold, width=10, validate="key", validatecommand=(validate_cmd, '%P'))
        violence_entry.grid(row=10, column=1, padx=5, pady=2, sticky="w")

        # Add a description
        ttk.Label(threshold_frame, text="Controls filtering for violent and graphic content (0.01-1.00)",
                 font=("TkDefaultFont", 8), foreground="gray").grid(row=11, column=0, columnspan=2, padx=5, pady=(0, 2), sticky="w")

        # Add checkbox for allowing adult content (moved to the bottom)
        ttk.Label(threshold_frame, text="Adult Content:", anchor="e").grid(row=12, column=0, padx=5, pady=2, sticky="e")
        ttk.Checkbutton(threshold_frame, text="Allow adult content (while still blocking child-related inappropriate content)",
                       variable=self.allow_adult_content).grid(row=12, column=1, padx=5, pady=2, sticky="w")

        # Add a description
        ttk.Label(threshold_frame, text="When enabled, adult content is allowed but child-related inappropriate content is still blocked. "
                 "This setting works in conjunction with the Sexual Content Threshold above.",
                 font=("TkDefaultFont", 8), foreground="gray").grid(row=13, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="w")

        # Create a frame for warning and ban settings
        warning_frame = ttk.LabelFrame(main_frame, text="Warning and Ban Settings", padding=10)
        warning_frame.grid(row=current_row, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        warning_frame.grid_columnconfigure(1, weight=1)
        current_row += 1

        # Description for warning and ban settings
        warning_desc = "Configure how many warnings users receive before action is taken, and whether to permanently ban or temporarily restrict users."
        warning_desc_label = ttk.Label(warning_frame, text=warning_desc, wraplength=600, justify="left")
        warning_desc_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Max warnings setting
        ttk.Label(warning_frame, text="Maximum Warnings:", anchor="e").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        max_warnings_entry = ttk.Entry(warning_frame, textvariable=self.max_warnings, width=5)
        max_warnings_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Add a description
        ttk.Label(warning_frame, text="Number of warnings before action is taken (default: 3)",
                 font=("TkDefaultFont", 8), foreground="gray").grid(row=2, column=0, columnspan=2, padx=5, pady=(0, 10), sticky="w")

        # Enable permanent ban setting
        ttk.Label(warning_frame, text="Action Type:", anchor="e").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        ban_frame = ttk.Frame(warning_frame)
        ban_frame.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Create radio buttons for ban options
        permanent_ban_radio = ttk.Radiobutton(ban_frame, text="Permanent Ban", variable=self.enable_permanent_ban, value=True)
        permanent_ban_radio.pack(side="left", padx=(0, 10))

        temp_restrict_radio = ttk.Radiobutton(ban_frame, text="24-Hour Restriction", variable=self.enable_permanent_ban, value=False)
        temp_restrict_radio.pack(side="left")

        # Add a description
        ttk.Label(warning_frame, text="Choose whether to permanently ban users or temporarily restrict them for 24 hours",
                 font=("TkDefaultFont", 8), foreground="gray").grid(row=4, column=0, columnspan=2, padx=5, pady=(0, 10), sticky="w")

        # Add instructions for threshold settings
        threshold_instructions = (
            # "How to use threshold settings:\n"
            # "• Higher values = less filtering (fewer false positives)\n"
            # "• Lower values = more filtering (more false positives)\n"
            # "• To disable a filter completely, set its threshold to 1.0\n"
            # "• For maximum protection, set thresholds to 0.5 or lower\n"
            # "• Check warning messages to see which threshold was exceeded"
        )

        threshold_instructions_label = ttk.Label(main_frame, text=threshold_instructions, wraplength=600, justify="left")
        threshold_instructions_label.grid(row=current_row, column=0, columnspan=2, padx=5, pady=10, sticky="w")
        current_row += 1

        # Add save button
        save_button = ttk.Button(main_frame, text="Save Content Filter Settings", command=self.save_content_configuration)
        save_button.grid(row=current_row, column=0, columnspan=2, padx=5, pady=10)

    def save_content_configuration(self):
        """Save content filter configuration to .env file"""
        try:
            # Check child threshold value before saving
            try:
                child_threshold_value = float(self.child_threshold.get())
                if child_threshold_value > 0.1:
                    # Show warning again when saving
                    self.show_child_threshold_warning(child_threshold_value)
            except ValueError:
                # If conversion fails, continue with saving
                pass

            env_vars = self.setup_manager.load_env()

            # Save content filter thresholds
            env_vars['CONTENT_FILTER_TOXIC_THRESHOLD'] = self.toxic_threshold.get()
            env_vars['CONTENT_FILTER_HARMFUL_THRESHOLD'] = self.harmful_threshold.get()
            env_vars['CONTENT_FILTER_SEXUAL_THRESHOLD'] = self.sexual_threshold.get()
            env_vars['CONTENT_FILTER_CHILD_THRESHOLD'] = self.child_threshold.get()
            env_vars['CONTENT_FILTER_HATE_THRESHOLD'] = self.hate_threshold.get()
            env_vars['CONTENT_FILTER_VIOLENCE_THRESHOLD'] = self.violence_threshold.get()
            env_vars['CONTENT_FILTER_ALLOW_ADULT'] = str(self.allow_adult_content.get()).lower()

            # Save warning and ban settings
            env_vars['MAX_WARNINGS'] = self.max_warnings.get()
            env_vars['ENABLE_PERMANENT_BAN'] = str(self.enable_permanent_ban.get()).lower()

            # Save all values
            if self.setup_manager.save_env(env_vars):
                logger.info("Content filter configuration saved successfully")
                messagebox.showinfo("Success", "Content filter configuration saved successfully!")
            else:
                logger.error("Failed to save content filter configuration")
                messagebox.showerror("Error", "Failed to save content filter configuration")

        except Exception as e:
            logger.error(f"Error saving content filter configuration: {str(e)}")
            messagebox.showerror("Error", f"Error saving content filter configuration: {str(e)}")
            raise

    def save_ai_configuration(self):
        try:
            env_vars = self.setup_manager.load_env()

            # Save AI configuration
            provider = self.ai_provider.get()
            env_vars['AI_PROVIDER'] = provider
            env_vars['ENABLE_PROMPT_ENHANCEMENT'] = str(self.enable_prompt_enhancement.get())
            env_vars['LMSTUDIO_HOST'] = self.lmstudio_host.get()
            env_vars['LMSTUDIO_PORT'] = self.lmstudio_port.get()

            # Save API keys
            env_vars['XAI_API_KEY'] = self.xai_api_key.get()
            env_vars['OPENAI_API_KEY'] = self.openai_api_key.get()
            env_vars['GEMINI_API_KEY'] = self.gemini_api_key.get()
            env_vars['ANTHROPIC_API_KEY'] = self.anthropic_api_key.get()

            # Save model names based on selected provider
            env_vars['GEMINI_MODEL'] = self.gemini_model.get()
            env_vars['XAI_MODEL'] = self.xai_model.get()
            env_vars['OPENAI_MODEL'] = self.openai_model.get()
            env_vars['ANTHROPIC_MODEL'] = self.anthropic_model.get()

            # Save all values
            if self.setup_manager.save_env(env_vars):
                logger.info("AI configuration saved successfully")
                messagebox.showinfo("Success", "AI configuration saved successfully!")
            else:
                logger.error("Failed to save AI configuration")
                messagebox.showerror("Error", "Failed to save AI configuration")

        except Exception as e:
            logger.error(f"Error saving AI configuration: {str(e)}")
            messagebox.showerror("Error", f"Error saving AI configuration: {str(e)}")
            raise

    def update_progress(self, value, status=""):
        """Update progress bar and status label"""
        try:
            self.progress_var.set(value)
            if status:
                self.status_var.set(status)
            self.root.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating progress: {str(e)}")

    def update_download_progress(self, progress, status=None):
        """Callback for download progress updates"""
        try:
            if isinstance(progress, (int, float)):
                self.progress_var.set(progress)
            if status:
                self.status_var.set(status)
            self.root.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating download progress: {str(e)}")

    def disable_ui(self):
        """Disable UI elements during installation"""
        for tab in [self.bot_tab, self.ai_tab]:
            for child in tab.winfo_children():
                if isinstance(child, ttk.Frame) or isinstance(child, ttk.LabelFrame):
                    for widget in child.winfo_children():
                        if isinstance(widget, (ttk.Entry, ttk.Button, ttk.Combobox)):
                            widget.configure(state='disabled')
                elif isinstance(child, (ttk.Entry, ttk.Button, ttk.Combobox)):
                    child.configure(state='disabled')

    def enable_ui(self):
        """Enable UI elements after installation"""
        for tab in [self.bot_tab, self.ai_tab]:
            for child in tab.winfo_children():
                if isinstance(child, ttk.Frame) or isinstance(child, ttk.LabelFrame):
                    for widget in child.winfo_children():
                        if isinstance(widget, (ttk.Entry, ttk.Button, ttk.Combobox)):
                            widget.configure(state='normal')
                elif isinstance(child, (ttk.Entry, ttk.Button, ttk.Combobox)):
                    child.configure(state='normal')

    def show_child_threshold_warning(self, value):
        """Show a warning when child content threshold is set above 0.1"""
        warning_message = (
            "WARNING: Setting the child content threshold above 0.1 significantly reduces security."
            "\n\nHigher values make the filter less sensitive to potentially inappropriate content."
            "\n\nThe recommended value is 0.1 or lower for maximum protection."
            "\n\nAre you sure you want to continue with this setting?"
        )

        # Show a warning dialog with Yes/No options
        if not messagebox.askyesno("Security Warning", warning_message, icon="warning"):
            # If user selects "No", reset to the recommended value
            self.child_threshold.set("0.1")

    def on_checkpoint_selected(self, event=None):
        """Handle workflow selection"""
        selected = self.selected_checkpoint.get()
        if selected:
            # Map workflow files to model configurations
            workflow_to_model = {
                'fluxfusion6GB4step.json': 'FLUXFusion 6GB',
                'fluxfusion8GB4step.json': 'FLUXFusion 8GB',
                'fluxfusion10GB4step.json': 'FLUXFusion 10GB',
                'fluxfusion12GB4step.json': 'FLUXFusion 12GB',
                'fluxfusion24GB4step.json': 'FLUXFusion 24GB',
                'FluxDev24GB.json': 'FLUX.1 Dev'
            }

            # Map workflow names to Pulid files
            workflow_to_pulid = {
                'fluxfusion6GB4step.json': 'Pulid6GB.json',
                'fluxfusion8GB4step.json': 'Pulid8GB.json',
                'fluxfusion10GB4step.json': 'Pulid10GB.json',
                'fluxfusion12GB4step.json': 'Pulid12GB.json',
                'fluxfusion24GB4step.json': 'Pulid24GB.json',
                'FluxDev24GB.json': 'PulidFluxDev.json'
            }

            # Check if the workflow file exists in the target directory
            target_path = os.path.join(self.base_dir.get(), 'ComfyUI', 'workflows', 'config', selected)
            if os.path.exists(target_path):
                self.install_button.config(text="Update Configuration")
                self.status_var.set("Status: Workflow already installed")
            else:
                self.install_button.config(text="Install")
                self.status_var.set("Status: Ready to install")

            # Store the model name for this workflow
            if selected in workflow_to_model:
                self.selected_model = workflow_to_model[selected]
            else:
                self.selected_model = None

            # Update PULIDWORKFLOW in .env file if workflow has a corresponding Pulid file
            if selected in workflow_to_pulid:
                pulid_file = workflow_to_pulid[selected]
                self.setup_manager.update_env_file('PULIDWORKFLOW', f'"{pulid_file}"')
                self.status_var.set(f"Status: Updated PULIDWORKFLOW to '{pulid_file}'")

    def start_installation(self):
        """Start the installation process"""
        if not self.base_dir.get():
            messagebox.showerror("Error", "Please select ComfyUI Base Directory")
            return

        # Validate directory structure
        if not self.setup_manager.validator.validate_comfyui_directory(self.base_dir.get()):
            messagebox.showerror("Error", "Invalid ComfyUI directory structure")
            return

        # Disable UI elements during installation
        self.disable_ui()

        async def run_async_installation():
            try:
                # Set up manager properties
                self.setup_manager.models_path = os.path.join(self.base_dir.get(), "ComfyUI", "models")
                self.setup_manager.hf_token = self.hf_token.get()
                self.setup_manager.civitai_token = self.civitai_token.get()
                self.setup_manager.progress_callback = self.update_download_progress

                # Copy gguf_reader.py
                self.update_progress(10, "Copying required files...")
                if not self.setup_manager.validator.copy_gguf_reader(os.getcwd(), self.base_dir.get()):
                    raise Exception("Failed to copy gguf_reader.py")

                # Copy upscaler model
                self.update_progress(20, "Copying upscaler model...")
                if not self.setup_manager.validator.copy_upscaler(os.getcwd(), self.base_dir.get()):
                    raise Exception("Failed to copy upscaler model")

                # Copy ratios.json
                self.update_progress(30, "Copying ratios.json...")
                if not self.setup_manager.validator.copy_ratios_json(os.getcwd(), self.base_dir.get()):
                    raise Exception("Failed to copy ratios.json")

                # Process base models
                total_models = len(BASE_MODELS)
                for index, (model_name, model_info) in enumerate(BASE_MODELS.items(), 1):
                    self.update_progress(0, f"Processing {model_name} ({index}/{total_models})...")

                    model_path = os.path.join(
                        self.setup_manager.models_path,
                        model_info['path'].strip('/'),
                        model_info['filename']
                    )

                    if os.path.exists(model_path):
                        self.update_progress(100, f"{model_name} already exists, skipping...")
                        continue

                    self.update_progress(0, f"Downloading {model_name} from {model_info['source']}...")

                    try:
                        token = self.hf_token.get() if model_info['source'] == 'huggingface' else self.civitai_token.get()
                        await self.setup_manager.download_file(
                            file_info=model_info,
                            output_path=model_path,
                            token=token,
                            source=model_info['source']
                        )
                        self.update_progress(100, f"Successfully downloaded {model_name}")
                    except Exception as e:
                        logger.error(f"Error downloading {model_name}: {str(e)}")
                        raise

                # Handle selected workflow and model
                if self.selected_checkpoint.get() and self.selected_checkpoint.get() != "Select a checkpoint...":
                    workflow_file = self.selected_checkpoint.get()
                    self.update_progress(0, f"Processing workflow {workflow_file}...")

                    # Copy workflow file
                    source_path = os.path.join(os.getcwd(), 'config', workflow_file)
                    target_path = os.path.join(self.base_dir.get(), 'ComfyUI', 'workflows', 'config', workflow_file)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    try:
                        # Copy the workflow file
                        shutil.copy2(source_path, target_path)
                        self.update_progress(100, f"Successfully copied workflow file")

                        # Download the corresponding model if needed
                        if hasattr(self, 'selected_model') and self.selected_model in CHECKPOINTS:
                            model_info = CHECKPOINTS[self.selected_model]
                            model_path = os.path.join(
                                self.setup_manager.models_path,
                                model_info['path'].strip('/'),
                                model_info['filename']
                            )

                            if not os.path.exists(model_path):
                                self.update_progress(0, f"Downloading {self.selected_model} model...")
                                token = self.hf_token.get() if model_info['source'] == 'huggingface' else self.civitai_token.get()
                                await self.setup_manager.download_file(
                                    file_info=model_info,
                                    output_path=model_path,
                                    token=token,
                                    source=model_info['source']
                                )
                                self.update_progress(100, f"Successfully downloaded {self.selected_model}")
                            else:
                                self.update_progress(100, f"Checkpoint {self.selected_model} already exists, preserving existing file")

                        # Update .env file with fluxversion
                        self.update_progress(100, "Updating configuration...")
                        self.setup_manager.update_env_file('fluxversion', f'"{workflow_file}"')
                    except Exception as e:
                        logger.error(f"Error processing workflow and model: {str(e)}")
                        raise

                # Save configuration
                self.save_configuration()

                # Complete - update status but don't show popup
                self.update_progress(100, "Installation completed successfully!")

            except Exception as e:
                logger.error(f"Installation failed: {str(e)}")
                messagebox.showerror("Error", f"Installation failed: {str(e)}")
            finally:
                self.enable_ui()

        # Run the async installation in the event loop
        if not hasattr(self, 'loop'):
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        def run_async():
            try:
                self.loop.run_until_complete(run_async_installation())
            except Exception as e:
                messagebox.showerror("Error", f"Installation failed: {str(e)}")
            finally:
                self.enable_ui()

        # Start the async process
        threading.Thread(target=run_async, daemon=True).start()

    def open_url(self, url):
        """Open URL in default browser"""
        webbrowser.open(url)

def main():
    root = ThemedTk(theme="arc")  # Create themed root window
    root.title("FluxComfy Setup")

    # Set a reasonable window size
    window_width = 830
    window_height = 800

    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate position
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    # Set window size and position
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Make window resizable
    root.resizable(True, True)

    app = SetupUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()