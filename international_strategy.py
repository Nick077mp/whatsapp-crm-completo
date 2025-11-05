#!/usr/bin/env python3
"""
Estrategia para hacer el sistema internacional - Soportar cualquier código de país
"""

# ESTRATEGIA COMPLETA PARA INTERNACIONALIZACIÓN

PAISES_SOPORTADOS = {
    # América del Norte
    '1': {'name': 'USA/Canadá', 'format': '+1 XXX XXX XXXX', 'length': 11},
    
    # América Latina
    '52': {'name': 'México', 'format': '+52 XX XXXX XXXX', 'length': 12},  
    '54': {'name': 'Argentina', 'format': '+54 XX XXXX XXXX', 'length': 12},
    '55': {'name': 'Brasil', 'format': '+55 XX XXXXX XXXX', 'length': 13},
    '56': {'name': 'Chile', 'format': '+56 X XXXX XXXX', 'length': 11},
    '57': {'name': 'Colombia', 'format': '+57 XXX XXX XXXX', 'length': 12},
    '58': {'name': 'Venezuela', 'format': '+58 XXX XXX XXXX', 'length': 12},
    '51': {'name': 'Perú', 'format': '+51 XXX XXX XXX', 'length': 11},
    '593': {'name': 'Ecuador', 'format': '+593 XX XXX XXXX', 'length': 12},
    '507': {'name': 'Panamá', 'format': '+507 XXXX XXXX', 'length': 11},
    '506': {'name': 'Costa Rica', 'format': '+506 XXXX XXXX', 'length': 11},
    '504': {'name': 'Honduras', 'format': '+504 XXXX XXXX', 'length': 11},
    '503': {'name': 'El Salvador', 'format': '+503 XXXX XXXX', 'length': 11},
    '502': {'name': 'Guatemala', 'format': '+502 XXXX XXXX', 'length': 11},
    
    # Europa
    '34': {'name': 'España', 'format': '+34 XXX XXX XXX', 'length': 11},
    '33': {'name': 'Francia', 'format': '+33 X XX XX XX XX', 'length': 12},
    '44': {'name': 'Reino Unido', 'format': '+44 XXXX XXXXXX', 'length': 13},
    '49': {'name': 'Alemania', 'format': '+49 XXX XXXXXXX', 'length': 13},
    '39': {'name': 'Italia', 'format': '+39 XXX XXX XXXX', 'length': 13},
    
    # Asia
    '86': {'name': 'China', 'format': '+86 XXX XXXX XXXX', 'length': 14},
    '81': {'name': 'Japón', 'format': '+81 XX XXXX XXXX', 'length': 13},
    '82': {'name': 'Corea del Sur', 'format': '+82 XX XXXX XXXX', 'length': 13},
    '91': {'name': 'India', 'format': '+91 XXXXX XXXXX', 'length': 13},
}

def detectar_codigo_pais(numero_limpio):
    """
    Detecta el código de país de un número internacional
    """
    numero_limpio = str(numero_limpio)
    
    # Probar códigos de 3 dígitos primero
    for codigo in sorted(PAISES_SOPORTADOS.keys(), key=len, reverse=True):
        if numero_limpio.startswith(codigo):
            return codigo
    
    return None

def formatear_numero_internacional(numero_raw):
    """
    Formatea cualquier número internacional según su país
    """
    import re
    
    # Limpiar número
    numero_limpio = re.sub(r'[^0-9]', '', str(numero_raw))
    
    # Detectar código de país
    codigo_pais = detectar_codigo_pais(numero_limpio)
    
    if not codigo_pais:
        return None
    
    pais_info = PAISES_SOPORTADOS[codigo_pais]
    
    # Validar longitud
    if len(numero_limpio) != pais_info['length']:
        return None
    
    # Formatear según el país
    return formatear_por_pais(numero_limpio, codigo_pais)

def formatear_por_pais(numero_limpio, codigo_pais):
    """
    Aplica formato específico por país
    """
    if codigo_pais == '1':  # USA/Canadá
        # +1 555 123 4567
        return f"+1 {numero_limpio[1:4]} {numero_limpio[4:7]} {numero_limpio[7:]}"
    
    elif codigo_pais == '52':  # México
        # +52 55 1234 5678
        return f"+52 {numero_limpio[2:4]} {numero_limpio[4:8]} {numero_limpio[8:]}"
    
    elif codigo_pais == '57':  # Colombia
        # +57 300 123 4567
        return f"+57 {numero_limpio[2:5]} {numero_limpio[5:8]} {numero_limpio[8:]}"
    
    elif codigo_pais == '44':  # Reino Unido
        # +44 7700 123456
        return f"+44 {numero_limpio[2:6]} {numero_limpio[6:]}"
    
    elif codigo_pais == '34':  # España
        # +34 123 456 789
        return f"+34 {numero_limpio[2:5]} {numero_limpio[5:8]} {numero_limpio[8:]}"
    
    elif codigo_pais == '51':  # Perú
        # +51 123 456 789
        return f"+51 {numero_limpio[2:5]} {numero_limpio[5:8]} {numero_limpio[8:]}"
    
    elif codigo_pais == '507':  # Panamá
        # +507 1234 5678
        return f"+507 {numero_limpio[3:7]} {numero_limpio[7:]}"
    
    else:
        # Formato genérico internacional
        resto = numero_limpio[len(codigo_pais):]
        if len(resto) >= 6:
            mitad = len(resto) // 2
            return f"+{codigo_pais} {resto[:mitad]} {resto[mitad:]}"
        else:
            return f"+{codigo_pais} {resto}"

def validar_numero_internacional(numero):
    """
    Valida si un número es internacional válido
    """
    formato = formatear_numero_internacional(numero)
    return formato is not None

# PLAN DE IMPLEMENTACIÓN:

print("""
🌍 PLAN DE INTERNACIONALIZACIÓN DEL SISTEMA

1. REEMPLAZAR FUNCIONES ACTUALES:
   - formatColombianNumber() -> formatInternationalNumber()
   - _extract_real_phone_number() -> _extract_international_phone_number()
   - whatsapp_number property -> international_whatsapp_number property

2. ACTUALIZAR VALIDACIONES:
   - Eliminar checks específicos de '57'
   - Usar detectar_codigo_pais() para cualquier país
   - Mantener compatibilidad con números existentes

3. MODIFICAR app.js:
   - Función universal de formateo
   - Detectar automáticamente código de país
   - Formatear según reglas internacionales

4. ACTUALIZAR Django:
   - Servicio WhatsApp internacional
   - Modelos Contact universales
   - Webhooks que soporten cualquier país

5. MANTENER RETROCOMPATIBILIDAD:
   - Los números colombianos existentes seguirán funcionando
   - Migración gradual sin afectar funcionalidad actual
   - Fallbacks para números no reconocidos
""")

# Ejemplos de uso:
if __name__ == "__main__":
    numeros_test = [
        "573001234567",  # Colombia
        "525512345678",  # México  
        "15551234567",   # USA
        "447700123456",  # Reino Unido
        "34123456789",   # España
        "51123456789",   # Perú
    ]
    
    print("\n📱 EJEMPLOS DE FORMATEO:")
    for numero in numeros_test:
        formato = formatear_numero_internacional(numero)
        codigo = detectar_codigo_pais(numero)
        pais = PAISES_SOPORTADOS.get(codigo, {}).get('name', 'Desconocido')
        
        if formato:
            print(f"  {numero:12} -> {formato:20} ({pais})")
        else:
            print(f"  {numero:12} -> {'ERROR':20} ({pais})")