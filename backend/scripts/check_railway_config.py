#!/usr/bin/env python3
"""
Railway Configuration Checker for F1 Manager

Run this script to validate that Railway environment variables are configured correctly.
Usage: python backend/scripts/check_railway_config.py
"""
import os
import sys
from urllib.parse import urlparse


def check_config():
    """Check Railway environment configuration and report issues."""
    issues = []
    warnings = []

    # Check DATASTORE_TYPE
    datastore_type = os.getenv('DATASTORE_TYPE', 'local')
    print(f"✓ DATASTORE_TYPE: {datastore_type}")

    if datastore_type == 'local':
        warnings.append("⚠️  Using local JSON storage - data will NOT persist across deployments!")
        warnings.append("   Recommendation: Set DATASTORE_TYPE=postgres for production")

    # Check DATABASE_URL if postgres
    if datastore_type == 'postgres':
        db_url = os.getenv('DATABASE_URL', '')
        if not db_url:
            issues.append("❌ DATABASE_URL is required when DATASTORE_TYPE=postgres")
        else:
            # Validate URL format
            try:
                parsed = urlparse(db_url)
                if parsed.scheme not in ['postgres', 'postgresql']:
                    issues.append(f"❌ DATABASE_URL has invalid scheme: {parsed.scheme}")
                else:
                    print(f"✓ DATABASE_URL: postgresql://{parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}")
            except Exception as e:
                issues.append(f"❌ DATABASE_URL is malformed: {e}")

    # Check JWT secrets
    jwt_secret = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    if jwt_secret == 'jwt-secret-key-change-in-production':
        warnings.append("⚠️  JWT_SECRET_KEY is using default value - set a secure random string!")
    else:
        print(f"✓ JWT_SECRET_KEY: Custom value set (length: {len(jwt_secret)})")

    if secret_key == 'dev-secret-key-change-in-production':
        warnings.append("⚠️  SECRET_KEY is using default value - set a secure random string!")
    else:
        print(f"✓ SECRET_KEY: Custom value set (length: {len(secret_key)})")

    # Check CORS origins
    cors_origins = os.getenv('CORS_ORIGINS', '["http://localhost:8000", "http://127.0.0.1:8000"]')
    print(f"✓ CORS_ORIGINS: {cors_origins}")
    if 'localhost' in cors_origins:
        warnings.append("⚠️  CORS_ORIGINS includes localhost - update for production domain")

    # Print summary
    print("\n" + "="*60)
    if issues:
        print(f"\n❌ CRITICAL ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")

    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  {warning}")

    if not issues and not warnings:
        print("\n✅ Configuration looks good!")

    print("="*60 + "\n")

    # Exit code
    return 0 if not issues else 1


if __name__ == '__main__':
    sys.exit(check_config())
