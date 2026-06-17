#!/usr/bin/env python3
"""
اسکریپت راه‌اندازی ربات Toobit
"""

import os
import sys
import subprocess
from pathlib import Path


class BotSetup:
    """کلاس راه‌اندازی ربات"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / ".env"
        self.requirements_file = self.project_root / "requirements.txt"
    
    def print_header(self):
        """نمایش هدر"""
        print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║           🤖 ربات معاملاتی Toobit - برنامهٔ راه‌اندازی        ║
║                                                                ║
║                   Smart Trading Bot Setup                      ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """)
    
    def check_python_version(self):
        """بررسی نسخهٔ Python"""
        print("✓ بررسی نسخهٔ Python...")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            print(f"❌ Python 3.9+ الزامی است (شما نسخهٔ {version.major}.{version.minor} دارید)")
            return False
        
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    
    def check_env_file(self):
        """بررسی فایل .env"""
        print("\n✓ بررسی فایل .env...")
        
        if not self.env_file.exists():
            print("⚠️  فایل .env پیدا نشد")
            print("   فایل .env.example را کپی می‌کنم...")
            
            try:
                env_example = self.project_root / ".env.example"
                if env_example.exists():
                    with open(env_example, 'r', encoding='utf-8') as src:
                        with open(self.env_file, 'w', encoding='utf-8') as dst:
                            dst.write(src.read())
                    print("✅ فایل .env ایجاد شد")
                    print("⚠️  لطفا مقادیر را در .env قرار دهید")
                    return False
            except Exception as e:
                print(f"❌ خطا: {e}")
                return False
        
        # بررسی متغیرهای الزامی
        required_vars = ['BOT_TOKEN', 'TOOBIT_API_KEY', 'TOOBIT_SECRET_KEY']
        missing = []
        
        with open(self.env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for var in required_vars:
                if f"{var}=YOUR_" in content or f"{var}=" not in content:
                    missing.append(var)
        
        if missing:
            print(f"❌ متغیرهای الزامی یافت نشد: {', '.join(missing)}")
            print("   لطفا فایل .env را تکمیل کنید")
            return False
        
        print("✅ فایل .env صحیح است")
        return True
    
    def install_requirements(self):
        """نصب وابستگی‌ها"""
        print("\n✓ نصب وابستگی‌ها...")
        
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "--upgrade", "pip"
            ])
            print("✅ pip به‌روزرسانی شد")
            
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-r", str(self.requirements_file)
            ])
            print("✅ تمام وابستگی‌ها نصب شدند")
            return True
        except Exception as e:
            print(f"❌ خطا در نصب: {e}")
            return False
    
    def create_directories(self):
        """ایجاد دایرکتوری‌های لازم"""
        print("\n✓ ایجاد دایرکتوری‌ها...")
        
        dirs = [
            self.project_root / "logs",
            self.project_root / "backups",
            self.project_root / "data"
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(exist_ok=True)
        
        print("✅ دایرکتوری‌ها ایجاد شدند")
    
    def test_imports(self):
        """آزمایش import‌ها"""
        print("\n✓ آزمایش وابستگی‌ها...")
        
        try:
            import telegram
            print(f"✅ python-telegram-bot ({telegram.__version__})")
            
            import dotenv
            print(f"✅ python-dotenv")
            
            import requests
            print(f"✅ requests")
            
            return True
        except ImportError as e:
            print(f"❌ خطا: {e}")
            return False
    
    def display_next_steps(self):
        """نمایش مراحل بعدی"""
        print("""
╔════════════════════════════════════════════════════════════════╗
║                   ✅ راه‌اندازی کامل شد!                       ║
╚════════════════════════════════════════════════════════════════╝

📋 مراحل بعدی:

1️⃣  فایل .env را تکمیل کنید:
    • BOT_TOKEN را از @BotFather دریافت کنید
    • کلیدهای Toobit API را دریافت کنید
    • درگاه‌های پرداخت را تنظیم کنید

2️⃣  دیتابیس را initialize کنید:
    python -c "from database import db; db.init_tables()"

3️⃣  ربات را اجرا کنید:
    python main_bot.py

4️⃣  از منوی /help برای راهنمایی استفاده کنید

💡 نکات:
   • لاگ‌ها در toobit_bot.log ذخیره می‌شوند
   • دیتابیس در toobit_bot.db است
   • قبل از production، .env را امن کنید

📞 اگر مشکلی داشتید:
   • README.md را بخوانید
   • لاگ‌های خطا را بررسی کنید
   • از مجتمع جامعه کمک بخواهید

🚀 موفق باشید!
        """)
    
    def run(self):
        """اجرای کل فرایند"""
        self.print_header()
        
        # مراحل
        steps = [
            ("بررسی نسخهٔ Python", self.check_python_version),
            ("بررسی فایل .env", self.check_env_file),
            ("ایجاد دایرکتوری‌ها", self.create_directories),
            ("نصب وابستگی‌ها", self.install_requirements),
            ("آزمایش import‌ها", self.test_imports),
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                print(f"\n❌ ناکام در مرحلهٔ: {step_name}")
                return False
        
        self.display_next_steps()
        return True


def main():
    """تابع اصلی"""
    setup = BotSetup()
    
    try:
        if setup.run():
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  لغو‌شده توسط کاربر")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
