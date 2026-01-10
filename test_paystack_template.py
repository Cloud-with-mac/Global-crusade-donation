# TEST SCRIPT - Run this to verify Paystack template setup
# Save as: test_paystack_template.py
# Run from project root: python test_paystack_template.py

import os
import sys

print("="*60)
print("PAYSTACK TEMPLATE SETUP CHECKER")
print("="*60)
print()

# Check 1: Template file exists
template_path = os.path.join('donations', 'templates', 'donations', 'paystack_success.html')
print(f"1. Checking template file location...")
print(f"   Looking for: {template_path}")

if os.path.exists(template_path):
    print(f"   ✅ Template file EXISTS!")
    file_size = os.path.getsize(template_path)
    print(f"   File size: {file_size} bytes")
else:
    print(f"   ❌ Template file NOT FOUND!")
    print(f"   Expected location: {os.path.abspath(template_path)}")
    print()
    print("   FIX: Create the file at this location:")
    print(f"   {os.path.abspath(template_path)}")

print()

# Check 2: URLs file exists
urls_path = os.path.join('donations', 'urls.py')
print(f"2. Checking URLs configuration...")
print(f"   Looking for: {urls_path}")

if os.path.exists(urls_path):
    print(f"   ✅ urls.py EXISTS!")
    
    # Check if Paystack URLs are configured
    with open(urls_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    has_initialize = 'paystack/initialize' in content
    has_verify = 'paystack/verify' in content
    has_webhook = 'paystack/webhook' in content
    
    print()
    print("   Paystack URLs check:")
    print(f"   - paystack/initialize/: {'✅ FOUND' if has_initialize else '❌ MISSING'}")
    print(f"   - paystack/verify/:     {'✅ FOUND' if has_verify else '❌ MISSING'}")
    print(f"   - paystack/webhook/:    {'✅ FOUND' if has_webhook else '❌ MISSING'}")
    
    if not all([has_initialize, has_verify, has_webhook]):
        print()
        print("   FIX: Add missing Paystack URLs to donations/urls.py")
else:
    print(f"   ❌ urls.py NOT FOUND!")
    print(f"   Expected location: {os.path.abspath(urls_path)}")

print()

# Check 3: Views file exists
views_path = os.path.join('donations', 'views.py')
print(f"3. Checking views.py...")
print(f"   Looking for: {views_path}")

if os.path.exists(views_path):
    print(f"   ✅ views.py EXISTS!")
    
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_initialize_view = 'def paystack_initialize' in content
    has_verify_view = 'def paystack_verify' in content
    has_webhook_view = 'def paystack_webhook' in content
    
    print()
    print("   Paystack views check:")
    print(f"   - paystack_initialize(): {'✅ FOUND' if has_initialize_view else '❌ MISSING'}")
    print(f"   - paystack_verify():     {'✅ FOUND' if has_verify_view else '❌ MISSING'}")
    print(f"   - paystack_webhook():    {'✅ FOUND' if has_webhook_view else '❌ MISSING'}")
else:
    print(f"   ❌ views.py NOT FOUND!")

print()

# Check 4: Settings
settings_path = os.path.join('global_crusade', 'settings.py')
print(f"4. Checking Django settings...")
print(f"   Looking for: {settings_path}")

if os.path.exists(settings_path):
    print(f"   ✅ settings.py EXISTS!")
    
    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_app_dirs = "'APP_DIRS': True" in content or '"APP_DIRS": True' in content
    has_donations_app = "'donations'" in content or '"donations"' in content
    
    print()
    print("   Template settings check:")
    print(f"   - APP_DIRS: True:        {'✅ FOUND' if has_app_dirs else '❌ MISSING'}")
    print(f"   - donations in INSTALLED_APPS: {'✅ FOUND' if has_donations_app else '❌ MISSING'}")
else:
    print(f"   ❌ settings.py NOT FOUND!")

print()
print("="*60)
print("SUMMARY")
print("="*60)

# Overall status
template_ok = os.path.exists(template_path)
urls_ok = os.path.exists(urls_path) and has_initialize and has_verify and has_webhook
views_ok = os.path.exists(views_path) and has_initialize_view and has_verify_view
settings_ok = os.path.exists(settings_path) and has_app_dirs and has_donations_app

all_ok = template_ok and urls_ok and views_ok and settings_ok

if all_ok:
    print()
    print("✅ ALL CHECKS PASSED!")
    print("Paystack integration should be working correctly.")
    print()
    print("NEXT STEPS:")
    print("1. Make sure Django server is running:")
    print("   python manage.py runserver")
    print()
    print("2. Test Paystack payment on your donation page")
    print()
else:
    print()
    print("❌ SOME CHECKS FAILED!")
    print()
    print("ISSUES FOUND:")
    if not template_ok:
        print("- Template file is missing")
    if not urls_ok:
        print("- Paystack URLs not configured")
    if not views_ok:
        print("- Paystack views are missing")
    if not settings_ok:
        print("- Django settings need updating")
    print()
    print("Please fix the issues above and run this script again.")

print("="*60)
