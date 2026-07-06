"""Script de prueba para generar 4 casos de precios diferentes."""
from TemlateChollos import generar_post_v3

# Casos de prueba
casos = [
    {
        "nombre": "test_1_normal",
        "precio_original": 65.99,
        "precio_oferta": 53.29,
        "categoria": "Gaming",
        "subtitulo": "Mando inalámbrico RGB",
    },
    {
        "nombre": "test_2_gran_descuento",
        "precio_original": 49.99,
        "precio_oferta": 9.99,
        "categoria": "Electrónica",
        "subtitulo": "Cable USB-C 3m",
    },
    {
        "nombre": "test_3_precios_altos",
        "precio_original": 1999.99,
        "precio_oferta": 999.99,
        "categoria": "Monitores",
        "subtitulo": "Pantalla 4K 27 pulgadas",
    },
    {
        "nombre": "test_4_precios_bajos",
        "precio_original": 3.99,
        "precio_oferta": 1.99,
        "categoria": "Accesorios",
        "subtitulo": "Protector de pantalla",
    },
]

for caso in casos:
    try:
        generar_post_v3(
            producto_img_path="producto_test.png",
            precio_original=caso["precio_original"],
            precio_oferta=caso["precio_oferta"],
            output_path=f"{caso['nombre']}.png",
            categoria=caso["categoria"],
            subtitulo=caso["subtitulo"],
            logo_path="logo_telegram.png",
        )
        descuento = round((1 - caso["precio_oferta"] / caso["precio_original"]) * 100)
        ahorro = caso["precio_original"] - caso["precio_oferta"]
        print(f"OK: {caso['nombre']}.png - Descuento: {descuento}%, Ahorro: {ahorro:.2f} EUR")
    except Exception as e:
        print(f"ERROR: {caso['nombre']}.png - Error: {e}")

print("\nTodas las imágenes de prueba han sido generadas.")
