# patch_imghdr.py
import sys
import types

# Monkey patch برای Python 3.13+
if not hasattr(sys, 'imghdr'):
    try:
        import imghdr
    except ImportError:
        # ایجاد ماژول جعلی
        imghdr = types.ModuleType('imghdr')
        imghdr.what = lambda *args, **kwargs: None
        sys.modules['imghdr'] = imghdr
        print("✅ imghdr patch اعمال شد.")