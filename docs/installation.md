# 📖 Complete Installation Guide

### Recommended Comfyui download

https://github.com/comfyanonymous/ComfyUI/releases/download/latest/ComfyUI_cu128_50XX.7z

- Complete comfyui with update .bat files and ability to have sage attention and torch installed with out issue. 
- open update folder and run update_comfyui_and_python_dependencies.bat
- From required_files folder (Bot folder), copy 'For ComfyUI portable.bat' to your main ComfyUI directory and run it to install Triton and Sage attention

## 📋 Prerequisites

1. [Comfyui](https://github.com/comfyanonymous/ComfyUI) please install and configure for use.
    - Please enable --listen on your comfyui server. 
    - example: ``.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --listen``
2.  You can also choose to use the link provided in the setup tool to download and install comfyui.   
3.  Ensure you have Python 3.10.7+ installed on your system. You can download it from [python.org](https://www.python.org/downloads/).
4.  Custom Nodes are automatically installed via the setup tool, no longer need to try to hunt down and install them.

## 📦 Required Files

   - Flux Dev requires you to approve the license agreement on huggingface before the setup tool can download the models, please do this before running the setup tool.
   - Click on links below and apply for access to files, no need to download them, they will be automatically downloaded with setup tool, just needs access.
   - [Flux AE.Safetensors](https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors)
   - [Flux1.dev](https://huggingface.co/black-forest-labs/FLUX.1-dev ) 
   - [Flux.1-Redux-dev](https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev/tree/main)
   - [sigclip_vision_384](https://huggingface.co/Comfy-Org/sigclip_vision_384/blob/main/sigclip_vision_patch14_384.safetensors) 

   - Pulid should be downloaded automatically no need to open a repo



## 🔧 Installation Steps

### 1️⃣ ComfyUI Setup
1. Ensure ComfyUI is properly installed
2. Verify your installation directory structure:
   ```
   Example: 
   C:/Comfyui_windows_portable/ComfyUI/
   ```

3. Open Comfyui folder, open Update folder.
   - Run update_comfyui_and_python_dependencies.bat
   - Copy /setup/required files/For ComfyUI portable.bat.
    - run file, this will install Triton and Sage attention.


### 2️⃣ Bot Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/nvmax/FluxAI
   ```

2. Install the required dependencies using the requirements.txt file: 
 ```pip install -r requirements.txt```

3. **Run Setup Tool**
   ```bash
   python setup.py
   ```
   The setup tool will:
   - Copy required files needed to run
   - Setup your .env file with variables specified
   - download all files from huggingface and place them in the required folders
   - install custom nodes needed for the bot to run generations
   


- depending on your setup you may need to edit the json files to select the version of dev flux you are using for pulid and redux. 
- you can open these in comfyui and change the checkpoint in the gui, then click workflow and export api and replace the redux.json and reduxprompt.json files with the new json files. !!! DO NOT CHANGE THE STRUCTURE OF THE WORKFLOWS IN COMFYUI !!!
- manually editing them open the .json files and change the name of the unet_name to the name of the checkpoint you want to use, the checkpoint you use must be in the models/unet folder.

   - In redux.json find and change the name to your checkpoint name.
``` 
      "61": {
    "inputs": {
      "unet_name": "fluxFusionV24StepsGGUFNF4_V2Fp16.safetensors",
      "weight_dtype": "fp8_e4m3fn"
    },
    "class_type": "UNETLoader"
  },
```  
   - in reduxprompt.json find and change the name to your checkpoint name.
```
 "12": {
    "inputs": {
      "unet_name": "fluxFusionV24StepsGGUFNF4_V2Fp16.safetensors",
      "weight_dtype": "fp8_e4m3fn"
    },
    "class_type": "UNETLoader"
  },
```
- here are the names of the checkpoints for each version of Flux that can be used in the json files.
```
'FLUXFusion 6GB': 
        'filename': 'fluxFusionV24StepsGGUFNF4_V2GGUFQ3KM.gguf',

    'FLUXFusion 8GB': 
        'filename': 'fluxFusionV24StepsGGUFNF4_V2GGUFQ50.gguf',
        
    'FLUXFusion 10GB': 
        'filename': 'fluxFusionV24StepsGGUFNF4_V2GGUFQ6K.gguf',
        

    'FLUXFusion 12GB': 
        'filename': 'fluxFusionV24StepsGGUFNF4_V2GGUFQ80.gguf',

    'FLUXFusion 24GB': 
        'filename': 'fluxFusionV24StepsGGUFNF4_V2Fp16.safetensors',

    'FLUX.1 Dev': 
        'filename': 'flux1-dev.safetensors',

    
```
- Please enter in the one you specified when you run the setup.py so your not constantly switching checkpoints and causing slow downs.

- I am working on automating this process so you don't have to do it manually.

### 🤖 Discord Bot Setup

#### 1️⃣ Creating Your Discord Application
1. Visit the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application:
   - Click "New Application"
   - Name your bot
   - Navigate to "Bot" tab
   - Click "Add Bot"

#### 2️⃣ Bot Configuration
1. **Essential Bot Settings**
   - Copy Bot Token (keep secure!)
   - Enable Required Intents:
     ✓ Presence Intent
     ✓ Server Members Intent
     ✓ Message Content Intent

2. **Bot Permissions Setup**
   - Go to "OAuth2" tab
   - Select "bot" under Scopes
   - Required Permissions:
     ```
     ✓ Send Messages
     ✓ Manage Messages
     ✓ Embed Links
     ✓ Attach Files
     ✓ Read Message History
     ✓ Use Slash Commands
     ```
3. **Server Integration**
   - Copy OAuth2 URL
   - Open in new tab
   - Select target server

### 4️⃣ Verification Steps

After installation, verify:
- All dependencies are installed
- Workflow loads correctly
- Bot connects to Discord
- Commands are responsive

## 🔍 Post-Installation

### Testing the Installation
1. Start the bot:
   ```bash
   python run.py
   ```
2. Try basic commands in Discord
3. Verify image generation works

### Common Issues
- Check [Troubleshooting Guide](troubleshooting.md) for common problems
- Verify file permissions
- Confirm Python version compatibility
- if you recieve HTTP Error 400: Bad Request, you need to run the setup tool again. more likely missing a node, a checkpoint or files were not copied over correctly.

## 📚 Next Steps

- [Configure your bot](configuration.md)
- [Learn available commands](commands.md)

## 🆘 Need Help?

- Check our [Troubleshooting Guide](troubleshooting.md)
- Join our [Discord Server](https://discord.gg/V3pRgtzjsN)
- Open an [Issue](https://github.com/nvmax/FluxComfyDiscordbot/issues)
- [🏠  Return to main](../readme.md)
