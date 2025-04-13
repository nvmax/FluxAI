# 📝 Flux AI Discord Bot Commands Guide

## 🎨 Image Generation Commands

### `/comfy`
Generate images from text descriptions
```
/comfy [prompt] [resolution] [upscale_factor] [seed]
```
Parameters:
- `prompt`: Your text description for the image (required)
- `resolution`: Choose image size from options in ratios.json (required)
- `upscale_factor`: Set upscaling factor (1-4, default is 1)
- `seed`: Optional seed for reproducibility

After submitting the command, you can:
- Select LoRAs to apply via a modal
- Adjust AI enhancement level (1-10 scale)
- View generation progress in real-time

### `/pulid`
Generate personalized images based on a reference image and prompt
```
/pulid [prompt] [resolution] [strength] [upscale_factor]
```
Parameters:
- `prompt`: Text description to guide the image generation (required)
- `resolution`: Choose image size from options in ratios.json (required)
- `strength`: Influence of the reference image (0.1-1.0, default is 0.5)
- `upscale_factor`: Set upscaling factor (1-3, default is 1)

After submitting the command:
- You'll be prompted to upload a reference image
- You can select LoRAs to apply via a modal

### `/redux`
Blend two images together - first being the primary image, second being the style image
```
/redux [resolution]
```
Parameters:
- `resolution`: Choose image size from options in ratios.json (required)

After submitting the command:
- A modal will appear to set strength parameters for both images
- You'll be prompted to upload two images sequentially
- The bot generates a new image combining elements from both

### `/video`
Generates a short video based on your text prompt - highly descriptive context improves results
```
/video [prompt]
```
Parameters:
- `prompt`: Your text description for the video (required)

The video generation:
- Uses a random seed for each generation
- Shows progress updates during generation
- Provides controls for regeneration and deletion when complete

## 🔍 LoRA Commands

### `/lorainfo`
View information about available LoRA models
```
/lorainfo [lora_name]
```
Parameters:
- `lora_name`: Optional name of specific LoRA to view details for

Features:
- Displays 5 LoRAs per page with pagination
- Shows preview images from Civitai
- Provides details from lora.json
- Messages are ephemeral (only visible to you)

## 📊 Queue Management Commands

### `/queue`
Show the current queue status
```
/queue
```

### `/clear_queue`
Clear the generation queue (admin only)
```
/clear_queue
```

### `/set_queue_priority`
Set the priority for a user in the queue (admin only)
```
/set_queue_priority [user] [priority]
```
Parameters:
- `user`: The Discord user to set priority for
- `priority`: Priority level (High, Normal, Low)

## 📈 Analytics Commands

### `/stats`
Show usage statistics
```
/stats [days]
```
Parameters:
- `days`: Number of days to show statistics for (default: 7)

### `/reset_stats`
Reset usage statistics (admin only)
```
/reset_stats
```

## 🛡️ Content Filter Commands

### `/add_banned_word`
Add a word to the banned words list (admin only)
```
/add_banned_word [word]
```

### `/remove_banned_word`
Remove a word from the banned words list (admin only)
```
/remove_banned_word [word]
```

### `/list_banned_words`
List all banned words
```
/list_banned_words
```

### `/add_regex_pattern`
Add a regex pattern to the content filter (admin only)
```
/add_regex_pattern [name] [pattern] [description] [severity]
```

### `/warnings`
Check warnings for a user
```
/warnings [user]
```
Parameters:
- `user`: Optional user to check warnings for (defaults to yourself)

### `/warningremove`
Remove all warnings from a user (admin only)
```
/warningremove [user]
```

### `/banned`
List all banned users (admin only)
```
/banned
```

### `/ban`
Ban a user from using the bot (admin only)
```
/ban [user] [reason]
```

### `/unban`
Unban a user from using the bot (admin only)
```
/unban [user]
```

## 🔧 System Commands

### `/sync`
Sync commands with Discord (admin only)
```
/sync
```

## 📊 Advanced Usage

### Combining LoRAs
When using multiple LoRAs:
- Single LoRA: Full weight applied
- Multiple LoRAs: Weights automatically balanced
- LoRA-specific prompts are automatically added from lora.json

### Resolution Guidelines
Larger resolutions take longer to generate:
- Select from a variety of resolutions defined in ratios.json
- Consider the intended use and how resolution will impact the final result
- Higher resolutions require more VRAM

## 🎯 Tips for Best Results

1. **Prompt Writing**
   - Be specific in descriptions
   - Use artistic terms and detailed descriptions
   - Include desired style, lighting, and composition
   - For best results with /video, use highly descriptive prompts

2. **LoRA Selection**
   - Choose complementary styles
   - Test different combinations
   - Use /lorainfo to explore available options
   - Consider how LoRAs will interact with your prompt

3. **Resolution Choice**
   - Match to intended use
   - Consider generation time
   - Balance quality vs speed
   - Square resolutions (1024x1024) often work best for portraits
   - Landscape resolutions work well for scenery

4. **Customization**
   - Experiment with AI enhancement level
     - Scale from 1-10 with 1 preserving your original prompt and 10 being extremely creative
   - Adjust upscaling factor for higher resolution outputs
   - For /redux, try different strength values for each image
   - For /pulid, adjust strength to control how much of the reference image influences the result

5. **Rate Limits**
   - The bot has a limit of 50 requests per hour per user
   - Plan your generations accordingly


 [🏠  Return to main](../readme.md)