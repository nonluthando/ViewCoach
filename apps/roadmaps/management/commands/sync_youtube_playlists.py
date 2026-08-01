from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.roadmaps.models import YouTubePlaylistRoadmap
from apps.roadmaps.youtube_client import YouTubeDataClient, YouTubeImportError
from apps.roadmaps.youtube_services import sync_youtube_roadmap


class Command(BaseCommand):
    help = (
        "Refresh stored YouTube playlist metadata and availability. "
        "Run at least every 30 days for YouTube API data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Refresh every imported YouTube playlist.",
        )
        parser.add_argument(
            "--stale-days",
            type=int,
            default=29,
            help="Refresh playlists last synced this many days ago.",
        )
        parser.add_argument(
            "--playlist-id",
            help="Refresh one YouTube playlist ID.",
        )

    def handle(self, *args, **options):
        queryset = YouTubePlaylistRoadmap.objects.select_related(
            "roadmap",
            "user",
        )
        if options["playlist_id"]:
            queryset = queryset.filter(playlist_id=options["playlist_id"])
        elif not options["all"]:
            cutoff = timezone.now() - timedelta(days=max(0, options["stale_days"]))
            queryset = queryset.filter(last_synced_at__lte=cutoff)

        sources = list(queryset.order_by("last_synced_at", "pk"))
        if not sources:
            self.stdout.write("No YouTube playlists need refreshing.")
            return

        client = YouTubeDataClient()
        succeeded = 0
        failed = 0
        for source in sources:
            try:
                preview = client.fetch_playlist(source.source_url)
                sync_youtube_roadmap(source=source, preview=preview)
            except YouTubeImportError as exc:
                failed += 1
                self.stderr.write(f"{source.playlist_id}: {exc}")
            else:
                succeeded += 1
                self.stdout.write(
                    f"{source.playlist_id}: refreshed {source.available_video_count} videos"
                )

        if failed:
            raise CommandError(f"Refreshed {succeeded}; {failed} playlist(s) failed.")
        self.stdout.write(self.style.SUCCESS(f"Refreshed {succeeded} YouTube playlist(s)."))
