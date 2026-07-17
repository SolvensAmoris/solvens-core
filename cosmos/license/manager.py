"""
cosmos/license/manager.py
=========================

License Manager for Cosmos Compiler
=================================

Dual licensing system:
- Free tier: Apache 2.0
- Commercial tier: COSMOS-COMM-* keys

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional


class LicenseManager:
    """
    Manages Cosmos license keys and tier access.
    
    Tiers:
    - free: Apache 2.0, all core features
    - commercial: COSMOS-COMM-* key, advanced features
    
    Usage:
        lm = LicenseManager()
        license = lm.check()
        
        if license["tier"] == "commercial":
            print("Advanced features enabled")
        else:
            print("Free tier: core features only")
    """
    
    def __init__(self, license_dir: Optional[Path] = None):
        """
        Initialize LicenseManager.
        
        Args:
            license_dir: Custom license directory (default: ~/.cosmos/)
        """
        if license_dir:
            self.license_dir = license_dir
        else:
            self.license_dir = Path.home() / ".cosmos"
        
        self.license_dir.mkdir(parents=True, exist_ok=True)
        self.license_file = self.license_dir / "license.json"
    
    def check(self) -> Dict:
        """
        Check current license status.
        
        Returns:
            Dict with:
            - tier: 'free' or 'commercial'
            - valid: bool
            - features: list of enabled features
            - expires: timestamp or None
        """
        # Free tier is always valid
        features_free = ["core", "lsp", "cli"]
        
        if not self.license_file.exists():
            return {
                "tier": "free",
                "valid": True,
                "features": features_free,
                "expires": None,
                "message": "Free tier (Apache 2.0)"
            }
        
        try:
            data = json.loads(self.license_file.read_text())
        except (json.JSONDecodeError, IOError):
            return {
                "tier": "free",
                "valid": True,
                "features": features_free,
                "expires": None,
                "message": "Invalid license file, using free tier"
            }
        
        tier = data.get("tier", "free")
        expires = data.get("expires", 0)
        
        # Check expiration
        if tier == "commercial":
            if expires > time.time():
                features_commercial = features_free + ["sso", "audit", "priority", "sla"]
                return {
                    "tier": "commercial",
                    "valid": True,
                    "features": features_commercial,
                    "expires": expires,
                    "message": "Commercial license active"
                }
            else:
                return {
                    "tier": "commercial",
                    "valid": False,
                    "features": features_free,
                    "expires": expires,
                    "message": "License expired"
                }
        
        return {
            "tier": "free",
            "valid": True,
            "features": features_free,
            "expires": None,
            "message": "Free tier (Apache 2.0)"
        }
    
    def activate(self, key: str) -> bool:
        """
        Activate a commercial license key.
        
        Args:
            key: License key (format: COSMOS-COMM-XXXX)
            
        Returns:
            True if activation successful, False otherwise
        """
        # Validate key format
        if not key.startswith("COSMOS-COMM-"):
            return False
        
        # In production: validate against cosmos.dev/api/license
        # For now: accept any COSMOS-COMM-* key
        
        try:
            self.license_file.write_text(json.dumps({
                "tier": "commercial",
                "expires": time.time() + 31536000,  # 1 year
                "max_devs": 999,
                "key": key,
                "activated_at": time.time()
            }, indent=2))
            return True
        except IOError:
            return False
    
    def deactivate(self) -> bool:
        """
        Deactivate commercial license (return to free tier).
        
        Returns:
            True if successful
        """
        try:
            if self.license_file.exists():
                self.license_file.unlink()
            return True
        except IOError:
            return False
    
    def get_features(self) -> List[str]:
        """Get list of available features for current tier."""
        return self.check()["features"]
    
    def has_feature(self, feature: str) -> bool:
        """Check if a feature is available in current tier."""
        return feature in self.get_features()
    
    def is_commercial(self) -> bool:
        """Check if current license is commercial tier."""
        return self.check()["tier"] == "commercial"
    
    def is_valid(self) -> bool:
        """Check if current license is valid."""
        return self.check()["valid"]


# Singleton instance
_default_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """Get singleton LicenseManager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = LicenseManager()
    return _default_manager
