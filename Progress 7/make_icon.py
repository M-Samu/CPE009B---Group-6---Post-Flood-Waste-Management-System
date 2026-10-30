from PIL import Image

# Load the project image
img = Image.open("IconF.png").convert("RGBA")

# Create a square 256x256 transparent canvas
icon_size = 256
canvas = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))

# Resize icon maintaining original aspect ratio
img.thumbnail((220, 220), Image.Resampling.LANCZOS)

# Center the icon on the canvas
paste_x = (icon_size - img.width) // 2
paste_y = (icon_size - img.height) // 2
canvas.paste(img, (paste_x, paste_y), img)

# Save as PNG and Windows ICO format
canvas.save("icon.png")
canvas.save("icon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

print("Successfully generated icon.png and icon.ico!")