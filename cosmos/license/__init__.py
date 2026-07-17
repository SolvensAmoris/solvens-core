"""
cosmos/license/__init__.py
========================

License management module for Cosmos.

Usage:
    from cosmos.license import LicenseManager, get_license_manager
    
    lm = LicenseManager()
    license = lm.check()
    
    if license["tier"] == "commercial":
        # Commercial features
        pass
"""

from cosmos.license.manager import LicenseManager, get_license_manager

__all__ = ["LicenseManager", "get_license_manager"]
