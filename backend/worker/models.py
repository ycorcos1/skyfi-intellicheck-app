"""
Data models for worker results and signals.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CheckStatus(str, Enum):
    """Status of an individual check."""
    SUCCESS = "success"
    FAILED = "failed"


class SignalStatus(str, Enum):
    """Status of a verification signal."""
    OK = "ok"
    SUSPICIOUS = "suspicious"
    MISMATCH = "mismatch"
    FAILED = "failed"


class SignalSeverity(str, Enum):
    """Severity level of a signal."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class WhoisResult:
    """WHOIS lookup result."""
    domain_age_days: Optional[int] = None
    registrar: Optional[str] = None
    privacy_enabled: Optional[bool] = None
    creation_date: Optional[datetime] = None
    status: CheckStatus = CheckStatus.FAILED
    error: Optional[str] = None


@dataclass
class DNSResult:
    """DNS query result."""
    resolves: bool = False
    nameservers: List[str] = None
    a_records: List[str] = None
    status: CheckStatus = CheckStatus.FAILED
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.nameservers is None:
            self.nameservers = []
        if self.a_records is None:
            self.a_records = []


@dataclass
class WebResult:
    """HTTP homepage fetch result."""
    reachable: bool = False
    status_code: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    content_length: int = 0
    status: CheckStatus = CheckStatus.FAILED
    error: Optional[str] = None


@dataclass
class MXResult:
    """MX record validation result."""
    has_mx_records: bool = False
    mx_records: List[str] = None
    email_configured: bool = False
    status: CheckStatus = CheckStatus.FAILED
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.mx_records is None:
            self.mx_records = []


@dataclass
class PhoneResult:
    """Phone normalization result."""
    normalized: Optional[str] = None  # E.164 format
    valid: bool = False
    region: Optional[str] = None
    status: CheckStatus = CheckStatus.FAILED
    error: Optional[str] = None


@dataclass
class Signal:
    """Verification signal."""
    field: str
    status: SignalStatus
    value: str
    weight: int
    severity: SignalSeverity


@dataclass
class AnalysisResult:
    """Complete analysis result."""
    successful_checks: List[str]
    failed_checks: List[str]
    signals: List[Signal]
    rule_score: int
    submitted_data: Dict[str, Any]
    discovered_data: Dict[str, Any]

