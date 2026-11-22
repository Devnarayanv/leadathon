"""ICS generation for deadlines the user has verified."""
import hashlib
import re
from datetime import date, datetime, timedelta
from typing import List

from schemas import CalendarDeadline

PRODID = "-//Doc Decode//Document Deadlines//EN"


def _escape(text: str) -> str:
    """RFC 5545 text escaping."""
    out = text.replace("\\", "\\\\")
    out = out.replace(";", "\\;").replace(",", "\\,")
    out = out.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return out


def _fold(line: str) -> str:
    """Lines over 75 octets must be folded with a leading space."""
    raw = line.encode("utf-8")
    if len(raw) <= 73:
        return line
    chunks = []
    start = 0
    while start < len(raw):
        end = min(start + 73, len(raw))
        # Do not split a multi-byte character.
        while end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        chunks.append(raw[start:end].decode("utf-8", "ignore"))
        start = end
    return "\r\n ".join(chunks)


def _uid(deadline: CalendarDeadline, filename: str) -> str:
    digest = hashlib.sha1(
        ("%s|%s|%s" % (filename, deadline.date_iso, deadline.description)).encode("utf-8")
    ).hexdigest()[:16]
    return "%s@docdecode.local" % digest


def build_ics(
    filename: str, deadlines: List[CalendarDeadline], reminder_days: int = 3
) -> str:
    """An all-day event per deadline, each with a reminder alarm.

    reminder_days is how many days before the date the alarm fires; 0 puts
    it on the morning of the day itself.
    """
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:" + PRODID,
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for deadline in deadlines:
        day = date.fromisoformat(deadline.date_iso)
        description_parts = ["Deadline found by Doc Decode in: " + filename]
        if deadline.page:
            description_parts.append("Page %d of the document." % deadline.page)
        if deadline.source_text:
            description_parts.append("Document wording: " + deadline.source_text)
        description_parts.append(
            "You confirmed this date yourself. Check it against the original document."
        )
        lines += [
            "BEGIN:VEVENT",
            "UID:" + _uid(deadline, filename),
            "DTSTAMP:" + stamp + "Z",
            # All-day event: DTEND is exclusive.
            "DTSTART;VALUE=DATE:" + day.strftime("%Y%m%d"),
            "DTEND;VALUE=DATE:" + (day + timedelta(days=1)).strftime("%Y%m%d"),
            _fold("SUMMARY:" + _escape("Doc Decode: " + deadline.description)),
            _fold("DESCRIPTION:" + _escape("\n".join(description_parts))),
            "TRANSP:TRANSPARENT",
            "BEGIN:VALARM",
            "TRIGGER:-PT0M" if reminder_days == 0 else "TRIGGER:-P%dD" % reminder_days,
            "ACTION:DISPLAY",
            _fold(
                "DESCRIPTION:"
                + _escape(
                    deadline.description
                    + (" today" if reminder_days == 0 else " in %d days" % reminder_days)
                )
            ),
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def safe_basename(filename: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._-") or "document"
    return stem[:60]
