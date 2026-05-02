#!/usr/bin/env python3
"""DX Guardian production environment configuration checker.

This script validates that all required environment variables are set
for production deployment. Run this before starting the application.

Usage:
    python check_prod_config.py

Exit codes:
    0 - All checks passed
    1 - Missing required configuration
"""

import os
import sys


# Required environment variables for production
REQUIRED_VARS = {
    'SECRET_KEY': 'Flask session secret key (generate with: python -c "import secrets; print(secrets.token_hex(32))")',
    'WAVELOG_URL': 'Wavelog QSO logging system URL',
    'WAVELOG_API_KEY': 'Wavelog API key for authentication',
    'CLUBLOG_APP_PASSWORD': 'ClubLog application password for callbook lookup',
    'QRZ_USERNAME': 'QRZ.com username for Grid lookup',
    'QRZ_PASSWORD': 'QRZ.com password for Grid lookup',
    'HAMQTH_USERNAME': 'HamQTH.com username for Grid lookup',
    'HAMQTH_PASSWORD': 'HamQTH.com password for Grid lookup',
    'VAPID_PUBLIC_KEY': 'Web Push VAPID public key',
    'VAPID_PRIVATE_KEY_PEM': 'Web Push VAPID private key (PEM format)',
    'VAPID_EMAIL': 'Web Push VAPID contact email',
}

# Optional but recommended
OPTIONAL_VARS = {
    'SOCKETIO_CORS_ALLOWED_ORIGINS': 'SocketIO CORS allowed origins (default: *)',
    'DEBUG': 'Debug mode (should be false in production)',
}


def check_production_mode():
    """Check if running in production mode."""
    flask_env = os.environ.get('FLASK_ENV', '').strip().lower()
    app_env = os.environ.get('APP_ENV', '').strip().lower()
    return flask_env == 'production' or app_env == 'production'


def main():
    is_prod = check_production_mode()
    
    print("=" * 60)
    print("DX Guardian Configuration Check")
    print("=" * 60)
    print()
    
    if is_prod:
        print("Mode: PRODUCTION")
        print()
    else:
        print("Mode: DEVELOPMENT")
        print("Note: Some checks are only enforced in production mode.")
        print()
    
    errors = []
    warnings = []
    
    # Check required variables
    print("Checking required variables...")
    for var, description in REQUIRED_VARS.items():
        value = os.environ.get(var, '').strip()
        if not value:
            if is_prod:
                errors.append(f"Missing required variable: {var}")
            else:
                warnings.append(f"Missing variable (will be required in production): {var}")
        else:
            # Check for default/weak values
            if var == 'SECRET_KEY' and value == 'change-me-in-production':
                errors.append(f"Weak SECRET_KEY detected. Generate a random secret!")
            elif var == 'SECRET_KEY' and len(value) < 32:
                warnings.append(f"SECRET_KEY is shorter than 32 characters")
    
    # Check optional variables
    print("Checking optional variables...")
    for var, description in OPTIONAL_VARS.items():
        value = os.environ.get(var, '').strip()
        if not value:
            print(f"  [OPTIONAL] {var} - not set")
        else:
            if var == 'DEBUG' and value.lower() == 'true' and is_prod:
                warnings.append(f"DEBUG=true in production mode!")
    
    # Print results
    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)
    print()
    
    if errors:
        print("ERRORS (must fix before production):")
        for error in errors:
            print(f"  ❌ {error}")
        print()
    
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
        print()
    
    if not errors and not warnings:
        print("✅ All checks passed!")
        print()
    
    # Summary
    print("=" * 60)
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print("=" * 60)
    
    if errors:
        print()
        print("Configuration check FAILED. Please fix the errors above.")
        print()
        print("See SECURITY_CONFIG.md for configuration guidance.")
        return 1
    
    if warnings and is_prod:
        print()
        print("Configuration check PASSED with warnings.")
        print("Consider addressing the warnings for better security.")
        return 0
    
    print()
    print("Configuration check PASSED. Ready to start.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
