"""Pydantic models for every artifact that crosses a step boundary.

The "file in, file out" contract only holds if a CSV written by step A is
exactly what step B expects — these models are that schema. They validate on
read and serialize on write (core/io.py). `extra="allow"` lets flows carry
additional columns (e.g. template values) through untouched.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Row(BaseModel):
    model_config = ConfigDict(extra="allow")


class Domain(Row):
    domain: str
    company: str = ""
    source: str = ""
    segment: str = ""

    @field_validator("domain")
    @classmethod
    def _canonical(cls, v: str) -> str:
        v = v.strip().lower()
        v = re.sub(r"^https?://", "", v)
        v = v.split("/")[0].removeprefix("www.")
        if not v or "." not in v:
            raise ValueError(f"not a domain: {v!r}")
        return v


class Contact(Row):
    email: str
    first_name: str = ""
    last_name: str = ""
    name: str = ""
    title: str = ""
    company: str = ""
    domain: str = ""

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError(f"not an email address: {v!r}")
        return v


class VerifiedContact(Contact):
    verified: bool = False
    mx_ok: bool = False
    verify_reason: str = ""


class OutboxRow(Row):
    email: str
    subject: str
    body: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError(f"not an email address: {v!r}")
        return v

    @field_validator("subject", "body")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v
