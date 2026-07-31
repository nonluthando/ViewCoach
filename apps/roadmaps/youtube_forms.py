from django import forms

from .youtube_client import extract_playlist_id


class YouTubePlaylistImportForm(forms.Form):
    playlist_url = forms.CharField(
        label="YouTube playlist",
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "placeholder": "https://www.youtube.com/playlist?list=...",
                "autocomplete": "off",
                "inputmode": "url",
            }
        ),
    )

    def clean_playlist_url(self):
        value = self.cleaned_data["playlist_url"].strip()
        try:
            extract_playlist_id(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return value
