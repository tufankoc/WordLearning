# Creating Kelime Extension Icons

## Required Icon Sizes
- icon16.png (16x16)
- icon32.png (32x32) 
- icon48.png (48x48)
- icon128.png (128x128)

## Method 1: Convert from SVG

Use the provided `icon.svg` file and convert to PNG using online tools or software:

### Online Converters:
1. https://convertio.co/svg-png/
2. https://cloudconvert.com/svg-to-png
3. https://www.online-convert.com/

### Using Inkscape (Command Line):
```bash
# Install Inkscape first
inkscape icon.svg --export-png=icon16.png --export-width=16 --export-height=16
inkscape icon.svg --export-png=icon32.png --export-width=32 --export-height=32
inkscape icon.svg --export-png=icon48.png --export-width=48 --export-height=48
inkscape icon.svg --export-png=icon128.png --export-width=128 --export-height=128
```

### Using ImageMagick:
```bash
convert -background none icon.svg -resize 16x16 icon16.png
convert -background none icon.svg -resize 32x32 icon32.png
convert -background none icon.svg -resize 48x48 icon48.png
convert -background none icon.svg -resize 128x128 icon128.png
```

## Method 2: Simple Placeholder Icons

For development/testing, you can create simple colored squares:

### Create with CSS/HTML:
```html
<div style="width:128px;height:128px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:16px;display:flex;align-items:center;justify-content:center;color:white;font-size:48px;font-family:sans-serif;">📚</div>
```

Take a screenshot and resize as needed.

## Icon Design Guidelines

### Visual Elements:
- 📚 Book symbol for learning
- ➕ Plus symbol for adding vocabulary
- 🎯 Modern gradient (purple to blue)
- Clean, minimal design
- High contrast for small sizes

### Color Scheme:
- Primary: #667eea (light blue)
- Secondary: #764ba2 (purple)
- Accent: #10b981 (green)
- Warning: #f59e0b (amber)

### Design Principles:
- Readable at 16px size
- Consistent with app branding
- Professional appearance
- Clear symbolism (book + learning)

## Temporary Solution

If you need to test the extension immediately, you can:

1. Copy any existing PNG files to the required names
2. Use emoji screenshots (📚) saved as PNG
3. Create simple colored rectangles with online tools
4. Generate proper icons later for production

The extension will work with placeholder icons during development. 