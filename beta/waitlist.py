"""
Waitlist Manager - Beta Invite System

Simple file-based waitlist with invite codes.
HACK: Use JSON file for MVP speed.
"""

import json
import os
import uuid
import hashlib
import time
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path


DATA_DIR = Path("beta_data")
WAITLIST_FILE = DATA_DIR / "waitlist.json"
INVITES_FILE = DATA_DIR / "invites.json"


@dataclass
class WaitlistEntry:
    email: str
    use_case: str = ""
    status: str = "pending"  # pending, invited, active
    invite_code: Optional[str] = None
    invited_at: Optional[float] = None
    created_at: float = None
    source: str = "landing"
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class WaitlistManager:
    """
    Simple file-based waitlist manager.
    
    For MVP, uses JSON files. Easy to migrate to DB later.
    """
    
    def __init__(self, data_dir: str = "beta_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.waitlist_file = self.data_dir / "waitlist.json"
        self.invites_file = self.data_dir / "invites.json"
        
        # Initialize files
        if not self.waitlist_file.exists():
            self._save_waitlist([])
        if not self.invites_file.exists():
            self._save_invites({})
    
    def _load_waitlist(self) -> list:
        with open(self.waitlist_file) as f:
            return [WaitlistEntry(**e) for e in json.load(f)]
    
    def _save_waitlist(self, entries: list):
        with open(self.waitlist_file, 'w') as f:
            json.dump([asdict(e) for e in entries], f, indent=2)
    
    def _load_invites(self) -> dict:
        with open(self.invites_file) as f:
            return json.load(f)
    
    def _save_invites(self, invites: dict):
        with open(self.invites_file, 'w') as f:
            json.dump(invites, f, indent=2)
    
    def add_to_waitlist(
        self,
        email: str,
        use_case: str = "",
        source: str = "landing"
    ) -> tuple[bool, Optional[str]]:
        """
        Add email to waitlist.
        
        Returns:
            (success, message)
        """
        entries = self._load_waitlist()
        
        # Check if already exists
        for e in entries:
            if e.email.lower() == email.lower():
                return False, "Already on waitlist!"
        
        # Generate invite code
        invite_code = self._generate_invite_code(email)
        
        entry = WaitlistEntry(
            email=email,
            use_case=use_case,
            source=source,
            invite_code=invite_code,
            status="invited" if len(entries) < 20 else "pending"  # First 20 get instant invite
        )
        
        if entry.status == "invited":
            entry.invited_at = time.time()
            self._add_invite(invite_code, email)
        
        entries.append(entry)
        self._save_waitlist(entries)
        
        return True, invite_code if entry.status == "invited" else None
    
    def _generate_invite_code(self, email: str) -> str:
        """Generate deterministic invite code."""
        raw = f"{email}{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:8].upper()
    
    def _add_invite(self, code: str, email: str):
        invites = self._load_invites()
        invites[code] = {
            "email": email,
            "created_at": time.time(),
            "activated": False,
        }
        self._save_invites(invites)
    
    def activate_invite(self, code: str) -> bool:
        """Activate an invite code."""
        invites = self._load_invites()
        if code not in invites:
            return False
        
        invites[code]["activated"] = True
        invites[code]["activated_at"] = time.time()
        self._save_invites(invites)
        
        # Update waitlist status
        entries = self._load_waitlist()
        for e in entries:
            if e.invite_code == code:
                e.status = "active"
        self._save_waitlist(entries)
        
        return True
    
    def get_stats(self) -> dict:
        """Get waitlist statistics."""
        entries = self._load_waitlist()
        invites = self._load_invites()
        
        return {
            "total_signups": len(entries),
            "invited": sum(1 for e in entries if e.status in ("invited", "active")),
            "active": sum(1 for e in entries if e.status == "active"),
            "pending": sum(1 for e in entries if e.status == "pending"),
            "total_invites": len(invites),
            "activated_invites": sum(1 for v in invites.values() if v.get("activated")),
        }
    
    def get_all_entries(self) -> list:
        """Get all waitlist entries."""
        return self._load_waitlist()
    
    def invite_next(self, count: int = 10) -> list:
        """Invite next N users from waitlist."""
        entries = self._load_waitlist()
        invites = self._load_invites()
        invited = []
        
        for e in entries:
            if e.status == "pending":
                e.status = "invited"
                e.invited_at = time.time()
                self._add_invite(e.invite_code, e.email)
                invited.append(e)
                
                if len(invited) >= count:
                    break
        
        self._save_waitlist(entries)
        return invited


# Global instance
_manager: Optional[WaitlistManager] = None


def get_manager() -> WaitlistManager:
    global _manager
    if _manager is None:
        _manager = WaitlistManager()
    return _manager


def add_to_waitlist(email: str, use_case: str = "") -> tuple[bool, Optional[str]]:
    """Convenience function."""
    return get_manager().add_to_waitlist(email, use_case)


def activate_invite(code: str) -> bool:
    """Convenience function."""
    return get_manager().activate_invite(code)
