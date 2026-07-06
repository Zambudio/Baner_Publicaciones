"""Crear imágenes de prueba para TemlateChollos.py"""
from PIL import Image, ImageDraw

# Crear imagen de producto (simple, rojo)
producto = Image.new('RGB', (300, 300), color='white')
draw = ImageDraw.Draw(producto)
# Dibujar un rectángulo rojo como "producto"
draw.rectangle([50, 50, 250, 250], fill='red', outline='darkred', width=3)
draw.text((100, 130), "Producto", fill='darkred')
producto.save('producto_test.png')
print("✓ Imagen de producto creada: producto_test.png")

# Crear imagen de logo (simple, azul)
logo = Image.new('RGB', (200, 200), color='white')
draw = ImageDraw.Draw(logo)
# Dibujar un círculo azul como "logo"
draw.ellipse([20, 20, 180, 180], fill='blue', outline='darkblue', width=3)
draw.text((70, 85), "Logo", fill='white')
logo.save('logo_telegram.png')
print("✓ Imagen de logo creada: logo_telegram.png")

print("\nAhora puedes ejecutar: python TemlateChollos.py")
