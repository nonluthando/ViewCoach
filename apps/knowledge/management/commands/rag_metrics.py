from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.knowledge.models import KnowledgeDocument, KnowledgeQueryLog


def _percentile(sorted_values, pct):
    """Nearest-rank percentile over an already-sorted list. Pure Python so this
    works against any backend (Postgres in prod, SQLite in tests) without a
    raw-SQL percentile_cont() call."""
    if not sorted_values:
        return None
    index = max(0, min(len(sorted_values) - 1, int(round(pct / 100 * (len(sorted_values) - 1)))))
    return sorted_values[index]


def _exception_type(error_message):
    # _create_log() always stores "{ExceptionType}: {message}" (answering.py)
    if not error_message:
        return "(no error message)"
    return error_message.split(":", 1)[0].strip()


def _rolling_window_breaches(timestamps, *, window_seconds, max_requests):
    """How many requests in `timestamps` landed inside a trailing window that
    already held >= max_requests — i.e. would have been rate-limited by
    views._rate_limit_exceeded(), which counts rows in that same window."""
    timestamps = sorted(timestamps)
    window = timedelta(seconds=window_seconds)
    breaches = 0
    left = 0
    for right in range(len(timestamps)):
        while timestamps[right] - timestamps[left] > window:
            left += 1
        count_in_window = right - left + 1
        if count_in_window > max_requests:
            breaches += 1
    return breaches


class Command(BaseCommand):
    help = "Report usage, reliability and evaluation-relevant metrics from KnowledgeQueryLog."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="How many days back to report on (default: 30). Use 0 for all time.",
        )
        parser.add_argument(
            "--top",
            type=int,
            default=10,
            help="How many rows to show in each top-N table (default: 10).",
        )

    def handle(self, *args, **options):
        days = options["days"]
        top_n = options["top"]

        queryset = KnowledgeQueryLog.objects.all()
        if days > 0:
            since = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(created_at__gte=since)
            period_label = f"last {days} day(s)"
        else:
            period_label = "all time"

        logs = list(
            queryset.values(
                "status",
                "latency_ms",
                "top_similarity",
                "retrieved_chunk_ids",
                "citations",
                "error_message",
                "question",
                "user_id",
                "created_at",
            )
        )
        total = len(logs)

        self.stdout.write(self.style.MIGRATE_HEADING(f"RAG metrics — {period_label}"))
        if total == 0:
            self.stdout.write("No KnowledgeQueryLog rows in this period.")
            return
        self.stdout.write(f"Total queries: {total}\n")

        # --- 1. Volume & outcome breakdown -----------------------------------
        status_counts = Counter(row["status"] for row in logs)
        self.stdout.write(self.style.MIGRATE_HEADING("Outcome breakdown"))
        for status, _label in KnowledgeQueryLog.Status.choices:
            count = status_counts.get(status, 0)
            pct = (count / total) * 100
            self.stdout.write(f"  {status:<12} {count:>6}  ({pct:5.1f}%)")
        self.stdout.write("")

        # --- 2. Latency ---------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("Latency (ms)"))
        all_latencies = sorted(row["latency_ms"] for row in logs)
        self.stdout.write(
            f"  overall   p50={_percentile(all_latencies, 50)}  "
            f"p95={_percentile(all_latencies, 95)}  "
            f"p99={_percentile(all_latencies, 99)}  "
            f"max={all_latencies[-1]}"
        )
        for status, _label in KnowledgeQueryLog.Status.choices:
            values = sorted(row["latency_ms"] for row in logs if row["status"] == status)
            if not values:
                continue
            self.stdout.write(
                f"  {status:<9} p50={_percentile(values, 50)}  "
                f"p95={_percentile(values, 95)}  n={len(values)}"
            )
        self.stdout.write("")

        # --- 3. Retrieval confidence ---------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("Retrieval confidence (top_similarity)"))
        for status in (KnowledgeQueryLog.Status.ANSWERED, KnowledgeQueryLog.Status.NO_EVIDENCE):
            values = [
                row["top_similarity"]
                for row in logs
                if row["status"] == status and row["top_similarity"] is not None
            ]
            if values:
                self.stdout.write(
                    f"  {status:<12} avg={sum(values) / len(values):.3f}  "
                    f"min={min(values):.3f}  max={max(values):.3f}  n={len(values)}"
                )
            else:
                self.stdout.write(f"  {status:<12} (no scored rows)")
        self.stdout.write("")

        # --- 4. Refusal breakdown (why NO_EVIDENCE happened) ----------------
        no_evidence_rows = [
            row for row in logs if row["status"] == KnowledgeQueryLog.Status.NO_EVIDENCE
        ]
        if no_evidence_rows:
            empty_retrieval = sum(1 for row in no_evidence_rows if not row["retrieved_chunk_ids"])
            had_chunks = [row for row in no_evidence_rows if row["retrieved_chunk_ids"]]
            not_supported = sum(1 for row in had_chunks if not row["error_message"])
            bad_citation = sum(1 for row in had_chunks if row["error_message"])
            self.stdout.write(self.style.MIGRATE_HEADING("Refusal breakdown (NO_EVIDENCE)"))
            self.stdout.write(f"  nothing cleared the similarity threshold : {empty_retrieval}")
            self.stdout.write(f"  model emitted NOT_SUPPORTED              : {not_supported}")
            self.stdout.write(f"  no valid [Source N] citation in answer   : {bad_citation}")
            self.stdout.write("")

        # --- 5. Error taxonomy ------------------------------------------------
        error_rows = [row for row in logs if row["status"] == KnowledgeQueryLog.Status.ERROR]
        if error_rows:
            self.stdout.write(self.style.MIGRATE_HEADING("Error taxonomy (ERROR rows)"))
            for exc_type, count in Counter(
                _exception_type(row["error_message"]) for row in error_rows
            ).most_common(top_n):
                self.stdout.write(f"  {count:>4}  {exc_type}")
            self.stdout.write("")

        # --- 6. Most-cited documents -----------------------------------------
        citation_counter: Counter[str] = Counter()
        for row in logs:
            for citation in row["citations"] or []:
                slug = citation.get("document_slug")
                if slug:
                    citation_counter[slug] += 1
        if citation_counter:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Most-cited documents (top {top_n})"))
            for slug, count in citation_counter.most_common(top_n):
                self.stdout.write(f"  {count:>4}  {slug}")
            self.stdout.write("")

        # --- 7. Published documents never cited (dead weight) ---------------
        published_slugs = set(
            KnowledgeDocument.objects.filter(status=KnowledgeDocument.Status.PUBLISHED).values_list(
                "slug", flat=True
            )
        )
        never_cited = sorted(published_slugs - set(citation_counter))
        if published_slugs:
            self.stdout.write(self.style.MIGRATE_HEADING("Published documents never cited"))
            if never_cited:
                for slug in never_cited[:top_n]:
                    self.stdout.write(f"  {slug}")
                if len(never_cited) > top_n:
                    self.stdout.write(f"  ... and {len(never_cited) - top_n} more")
            else:
                self.stdout.write("  (every published document has been cited at least once)")
            self.stdout.write("")

        # --- 8. Daily volume trend --------------------------------------------
        daily_counts: Counter[str] = Counter()
        for row in logs:
            daily_counts[row["created_at"].date().isoformat()] += 1
        self.stdout.write(self.style.MIGRATE_HEADING("Daily volume (most recent)"))
        for day in sorted(daily_counts)[-top_n:]:
            self.stdout.write(f"  {day}  {daily_counts[day]:>4}")
        self.stdout.write("")

        # --- 9. Most frequent questions ---------------------------------------
        question_counter = Counter(row["question"].strip().lower() for row in logs)
        repeats = [(q, c) for q, c in question_counter.most_common(top_n) if c > 1]
        if repeats:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Most repeated questions (top {top_n})"))
            for question, count in repeats:
                shown = question if len(question) <= 70 else question[:67] + "..."
                self.stdout.write(f"  {count:>4}  {shown}")
            self.stdout.write("")

        # --- 10. User engagement -----------------------------------------------
        user_ids = [row["user_id"] for row in logs if row["user_id"] is not None]
        anonymous = total - len(user_ids)
        if user_ids:
            per_user = Counter(user_ids)
            self.stdout.write(self.style.MIGRATE_HEADING("User engagement"))
            avg_per_user = len(user_ids) / len(per_user)
            self.stdout.write(f"  unique authenticated askers : {len(per_user)}")
            self.stdout.write(
                f"  queries per user (avg/max)  : {avg_per_user:.1f} / {max(per_user.values())}"
            )
            self.stdout.write(f"  anonymous/unauthenticated   : {anonymous}")
            self.stdout.write("")

        # --- 11. Rate-limit pressure --------------------------------------------
        if user_ids:
            by_user_timestamps: dict[int, list] = {}
            for row in logs:
                if row["user_id"] is not None:
                    by_user_timestamps.setdefault(row["user_id"], []).append(row["created_at"])
            window_seconds = settings.RAG_RATE_LIMIT_WINDOW_SECONDS
            max_requests = settings.RAG_MAX_REQUESTS_PER_WINDOW
            total_breaches = sum(
                _rolling_window_breaches(
                    timestamps, window_seconds=window_seconds, max_requests=max_requests
                )
                for timestamps in by_user_timestamps.values()
            )
            users_who_breached = sum(
                1
                for timestamps in by_user_timestamps.values()
                if _rolling_window_breaches(
                    timestamps, window_seconds=window_seconds, max_requests=max_requests
                )
                > 0
            )
            self.stdout.write(self.style.MIGRATE_HEADING("Rate-limit pressure"))
            self.stdout.write(
                f"  limit: {max_requests} requests / {window_seconds}s window"
            )
            self.stdout.write(f"  requests that would have been rate-limited : {total_breaches}")
            self.stdout.write(
                f"  users who hit the limit at least once      : {users_who_breached}"
            )
