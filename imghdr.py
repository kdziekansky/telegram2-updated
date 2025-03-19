# imghdr.py - zastępcza implementacja dla Python 3.13+
# Umieść ten plik w głównym katalogu projektu

def what(file, h=None):
    """Determine the type of image contained in file.
    
    This is a minimal implementation to make python-telegram-bot work.
    
    Args:
        file: A file object or path to a file.
        h: First few bytes of the file, or None if not provided.
        
    Returns:
        The image type (jpeg, png, gif, etc.) or None if not recognized.
    """
    if h is None:
        if hasattr(file, 'read'):
            position = file.tell()
            h = file.read(32)
            file.seek(position)
        else:
            with open(file, 'rb') as f:
                h = f.read(32)
    
    # Check for JPEG
    if h[0:2] == b'\xff\xd8':
        return 'jpeg'
        
    # Check for PNG
    if h[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
        
    # Check for GIF
    if h[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
        
    # Check for BMP
    if h[:2] == b'BM':
        return 'bmp'
        
    # Check for WEBP
    if h[:4] == b'RIFF' and h[8:12] == b'WEBP':
        return 'webp'
        
    return None