"""
Utilidades internacionales para manejar números de teléfono de cualquier país
"""
import re

# Configuración de países soportados
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
    
    Args:
        numero_limpio (str): Número limpio (solo dígitos)
        
    Returns:
        str: Código de país o None si no se reconoce
    """
    numero_limpio = str(numero_limpio)
    
    # Probar códigos de 3 dígitos primero, luego 2, luego 1
    for codigo in sorted(PAISES_SOPORTADOS.keys(), key=len, reverse=True):
        if numero_limpio.startswith(codigo):
            return codigo
    
    return None


def formatear_numero_internacional(numero_raw):
    """
    Formatea cualquier número internacional según su país
    
    Args:
        numero_raw (str): Número en cualquier formato
        
    Returns:
        str: Número formateado o None si no es válido
    """
    if not numero_raw:
        return None
        
    # Limpiar número (solo dígitos)
    numero_limpio = re.sub(r'[^0-9]', '', str(numero_raw))
    
    if len(numero_limpio) < 10:  # Muy corto para ser internacional
        return None
    
    # RETROCOMPATIBILIDAD: Si es 10 dígitos y empieza con 3, asumir Colombia
    if len(numero_limpio) == 10 and numero_limpio.startswith('3'):
        numero_limpio = '57' + numero_limpio
    
    # Detectar código de país
    codigo_pais = detectar_codigo_pais(numero_limpio)
    
    if not codigo_pais:
        return None
    
    pais_info = PAISES_SOPORTADOS[codigo_pais]
    
    # Validar longitud (permitir variaciones de ±1 dígito)
    longitud_esperada = pais_info['length']
    if not (longitud_esperada - 1 <= len(numero_limpio) <= longitud_esperada + 1):
        return None
    
    # Formatear según el país
    return formatear_por_pais(numero_limpio, codigo_pais)


def formatear_por_pais(numero_limpio, codigo_pais):
    """
    Aplica formato específico por país
    
    Args:
        numero_limpio (str): Número limpio con código de país
        codigo_pais (str): Código de país detectado
        
    Returns:
        str: Número formateado
    """
    if codigo_pais == '1':  # USA/Canadá
        if len(numero_limpio) >= 11:
            return f"+1 {numero_limpio[1:4]} {numero_limpio[4:7]} {numero_limpio[7:11]}"
    
    elif codigo_pais == '52':  # México
        if len(numero_limpio) >= 12:
            return f"+52 {numero_limpio[2:4]} {numero_limpio[4:8]} {numero_limpio[8:12]}"
    
    elif codigo_pais == '57':  # Colombia
        if len(numero_limpio) >= 12:
            return f"+57 {numero_limpio[2:5]} {numero_limpio[5:8]} {numero_limpio[8:12]}"
    
    elif codigo_pais == '44':  # Reino Unido
        if len(numero_limpio) >= 11:
            return f"+44 {numero_limpio[2:6]} {numero_limpio[6:12]}"
    
    elif codigo_pais == '34':  # España
        if len(numero_limpio) >= 11:
            return f"+34 {numero_limpio[2:5]} {numero_limpio[5:8]} {numero_limpio[8:11]}"
    
    elif codigo_pais == '51':  # Perú
        if len(numero_limpio) >= 11:
            return f"+51 {numero_limpio[2:5]} {numero_limpio[5:8]} {numero_limpio[8:11]}"
    
    elif codigo_pais == '507':  # Panamá
        if len(numero_limpio) >= 11:
            return f"+507 {numero_limpio[3:7]} {numero_limpio[7:11]}"
    
    # Formato genérico internacional
    resto = numero_limpio[len(codigo_pais):]
    if len(resto) >= 6:
        mitad = len(resto) // 2
        return f"+{codigo_pais} {resto[:mitad]} {resto[mitad:]}"
    else:
        return f"+{codigo_pais} {resto}"


def limpiar_numero(numero_raw):
    """
    Limpia un número dejando solo dígitos
    
    Args:
        numero_raw (str): Número en cualquier formato
        
    Returns:
        str: Solo dígitos
    """
    if not numero_raw:
        return ""
    return re.sub(r'[^0-9]', '', str(numero_raw))


def validar_numero_internacional(numero):
    """
    Valida si un número es internacional válido
    
    Args:
        numero (str): Número a validar
        
    Returns:
        bool: True si es válido
    """
    formato = formatear_numero_internacional(numero)
    return formato is not None


def obtener_info_pais(numero):
    """
    Obtiene información del país de un número
    
    Args:
        numero (str): Número de teléfono
        
    Returns:
        dict: Información del país o None
    """
    numero_limpio = limpiar_numero(numero)
    codigo_pais = detectar_codigo_pais(numero_limpio)
    
    if codigo_pais:
        return PAISES_SOPORTADOS[codigo_pais]
    
    return None


def es_numero_colombiano(numero):
    """
    Verifica si un número es colombiano (retrocompatibilidad)
    
    Args:
        numero (str): Número de teléfono
        
    Returns:
        bool: True si es colombiano
    """
    numero_limpio = limpiar_numero(numero)
    codigo_pais = detectar_codigo_pais(numero_limpio)
    return codigo_pais == '57'


def obtener_numero_para_whatsapp(numero):
    """
    Obtiene el número limpio para usar en WhatsApp API
    
    Args:
        numero (str): Número formateado
        
    Returns:
        str: Número limpio con código de país (ej: 573001234567)
    """
    return limpiar_numero(numero)