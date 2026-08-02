from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ALLOWED_IBM_HOSTS = {"skillsbuild.org", "www.skillsbuild.org"}
MAX_RESPONSE_BYTES = 2_000_000
REQUEST_TIMEOUT_SECONDS = 12

_DURATION_PATTERN = re.compile(
    r"(?P<hours>\d+)\s*(?:\+\s*)?(?:hours?|hrs?|h)"
    r"(?:\s*(?P<minutes>\d+)\s*(?:minutes?|mins?|min|m))?"
    r"|(?P<only_minutes>\d+)\s*(?:minutes?|mins?|min)"
    r"|(?P<range_start>\d+)\s*-\s*(?P<range_end>\d+)\s*(?:minutes?|mins?|min)",
    re.IGNORECASE,
)
_MODULE_PATTERN = re.compile(r"^module\s+\d+\b", re.IGNORECASE)


class IBMImportError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IBMOutlineItem:
    module_title: str
    lesson_title: str
    duration_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class IBMCoursePreview:
    source_url: str
    title: str
    description: str
    duration_minutes: int
    language: str
    thumbnail_url: str
    external_key: str
    outline: tuple[IBMOutlineItem, ...]


def normalize_ibm_course_url(value: str) -> str:
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() != "https":
        raise ValueError("Use an https IBM SkillsBuild course link.")
    if host not in ALLOWED_IBM_HOSTS:
        raise ValueError("Paste a public course link from skillsbuild.org.")
    if parsed.username or parsed.password:
        raise ValueError("The course link must not contain login credentials.")
    if parsed.port not in {None, 443}:
        raise ValueError("The IBM SkillsBuild link uses an unsupported port.")
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(("https", host, path, "", parsed.query, ""))


def duration_to_minutes(value: str) -> int | None:
    text = " ".join(value.split())
    iso_match = re.fullmatch(
        r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?",
        text,
        flags=re.IGNORECASE,
    )
    if iso_match:
        total = int(iso_match.group("hours") or 0) * 60
        total += int(iso_match.group("minutes") or 0)
        return total or None
    match = _DURATION_PATTERN.search(text)
    if not match:
        return None
    if match.group("range_end"):
        return int(match.group("range_end"))
    total = int(match.group("hours") or 0) * 60
    total += int(match.group("minutes") or 0)
    total += int(match.group("only_minutes") or 0)
    return total or None


class _CourseHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []
        self.meta = {}
        self.language = ""
        self._ignored_depth = 0
        self._json_ld_depth = 0
        self._json_ld_parts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        lower_tag = tag.lower()
        if lower_tag == "html":
            self.language = attributes.get("lang", "")
        elif lower_tag in {"script", "style", "noscript"}:
            if (
                lower_tag == "script"
                and attributes.get("type", "").lower() == "application/ld+json"
            ):
                self._json_ld_depth += 1
            else:
                self._ignored_depth += 1
        elif lower_tag == "meta":
            key = (
                attributes.get("property")
                or attributes.get("name")
                or ""
            ).lower()
            content = attributes.get("content", "").strip()
            if key and content:
                self.meta[key] = content

    def handle_endtag(self, tag):
        lower_tag = tag.lower()
        if lower_tag == "script" and self._json_ld_depth:
            self._json_ld_depth -= 1
        elif lower_tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data):
        if self._json_ld_depth:
            self._json_ld_parts.append(data)
            return
        if self._ignored_depth:
            return
        value = " ".join(unescape(data).split())
        if value:
            self.lines.append(value)

    @property
    def json_ld_text(self):
        return "".join(self._json_ld_parts)


def _json_ld_course(parser):
    raw = parser.json_ld_text.strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    queue = list(data) if isinstance(data, list) else [data]
    while queue:
        item = queue.pop(0)
        if not isinstance(item, dict):
            continue
        item_type = item.get("@type")
        types = item_type if isinstance(item_type, list) else [item_type]
        if any(str(value).casefold() == "course" for value in types):
            return item
        graph = item.get("@graph")
        if isinstance(graph, list):
            queue.extend(graph)
    return {}


def _next_title(lines, start):
    for value in lines[start:]:
        lower = value.casefold()
        if _MODULE_PATTERN.match(value) or lower == "assessment":
            return ""
        if lower.startswith("image:") or duration_to_minutes(value) is not None:
            continue
        if lower in {"course content", "start learning", "more information"}:
            continue
        if 2 <= len(value) <= 200:
            return value
    return ""


def _next_duration(lines, start):
    for value in lines[start:]:
        if _MODULE_PATTERN.match(value) or value.casefold() == "assessment":
            return None
        duration = duration_to_minutes(value)
        if duration is not None:
            return duration
    return None


def _extract_outline(lines, title, duration_minutes):
    items = []
    for index, line in enumerate(lines):
        if _MODULE_PATTERN.match(line):
            items.append(
                IBMOutlineItem(
                    module_title=line,
                    lesson_title=_next_title(lines, index + 1) or line,
                    duration_minutes=_next_duration(lines, index + 1),
                )
            )
        elif line.casefold() == "assessment":
            items.append(
                IBMOutlineItem(
                    module_title="Assessment",
                    lesson_title=(
                        _next_title(lines, index + 1) or "Course assessment"
                    ),
                    duration_minutes=_next_duration(lines, index + 1),
                )
            )
    if items:
        return tuple(items)
    return (
        IBMOutlineItem(
            module_title="Course",
            lesson_title=title,
            duration_minutes=duration_minutes or None,
        ),
    )


def parse_ibm_course_html(*, source_url: str, html: str) -> IBMCoursePreview:
    parser = _CourseHTMLParser()
    parser.feed(html)
    course = _json_ld_course(parser)
    title = (
        str(course.get("name") or "").strip()
        or parser.meta.get("og:title", "").strip()
        or parser.meta.get("twitter:title", "").strip()
    )
    if not title:
        title = next(
            (value for value in parser.lines if 3 <= len(value) <= 180),
            "",
        )
    if not title:
        raise IBMImportError("IBM did not return a recognisable course title.")
    description = " ".join(
        unescape(
            str(course.get("description") or "")
            or parser.meta.get("og:description", "")
            or parser.meta.get("description", "")
        ).split()
    )
    language = str(course.get("inLanguage") or parser.language or "").strip()
    image = course.get("image") or parser.meta.get("og:image", "")
    if isinstance(image, list):
        image = image[0] if image else ""
    if isinstance(image, dict):
        image = image.get("url", "")
    duration_minutes = duration_to_minutes(str(course.get("timeRequired") or ""))
    if duration_minutes is None:
        for index, line in enumerate(parser.lines):
            if line.casefold() == "duration" and index + 1 < len(parser.lines):
                duration_minutes = duration_to_minutes(parser.lines[index + 1])
                if duration_minutes is not None:
                    break
            if line.casefold().startswith("duration:"):
                duration_minutes = duration_to_minutes(line)
                if duration_minutes is not None:
                    break
    duration_minutes = duration_minutes or 0
    external_key = urlparse(source_url).path.rstrip("/").split("/")[-1]
    return IBMCoursePreview(
        source_url=source_url,
        title=title[:140],
        description=description,
        duration_minutes=duration_minutes,
        language=language[:80],
        thumbnail_url=str(image or "")[:500],
        external_key=external_key[:220],
        outline=_extract_outline(parser.lines, title, duration_minutes),
    )


class _IBMRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, new_url):
        try:
            safe_url = normalize_ibm_course_url(new_url)
        except ValueError as exc:
            raise IBMImportError(
                "IBM redirected the request outside skillsbuild.org."
            ) from exc
        return super().redirect_request(
            request,
            fp,
            code,
            msg,
            headers,
            safe_url,
        )


class IBMSkillsBuildClient:
    def fetch_course(self, course_url: str) -> IBMCoursePreview:
        try:
            source_url = normalize_ibm_course_url(course_url)
        except ValueError as exc:
            raise IBMImportError(str(exc)) from exc
        request = Request(
            source_url,
            headers={
                "User-Agent": "ViewCoach/1.0 public-course-importer",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        opener = build_opener(_IBMRedirectHandler())
        try:
            with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                final_url = normalize_ibm_course_url(response.geturl())
                content_type = response.headers.get_content_type()
                if content_type not in {"text/html", "application/xhtml+xml"}:
                    raise IBMImportError(
                        "IBM returned an unsupported course-page format."
                    )
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                charset = response.headers.get_content_charset() or "utf-8"
        except IBMImportError:
            raise
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise IBMImportError(
                "The IBM SkillsBuild course could not be loaded right now."
            ) from exc
        if len(payload) > MAX_RESPONSE_BYTES:
            raise IBMImportError("The IBM course page was unexpectedly large.")
        return parse_ibm_course_html(
            source_url=final_url,
            html=payload.decode(charset, errors="replace"),
        )
