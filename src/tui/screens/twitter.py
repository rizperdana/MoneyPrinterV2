"""Twitter Screen - Twitter bot management."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Label, Static, TextArea

from src.db import get_videos


class TwitterScreen(Screen):
    """Twitter bot screen with post composer, scheduler, and recent tweets."""

    MAX_CHARS = 280

    CSS = """
    TwitterScreen {
        layout: vertical;
        height: 100%;
        padding: 1;
    }

    .screen-header {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }

    .section-header {
        width: 100%;
        height: auto;
        text-style: bold;
        color: $primary;
        padding-top: 1;
        padding-bottom: 1;
    }

    .composer-section {
        height: auto;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .char-count {
        height: auto;
        width: 100%;
        content-align: right middle;
        color: $text-muted;
    }

    .char-count.warning {
        color: #f59e0b;
    }

    .char-count.error {
        color: #ef4444;
    }

    .button-row {
        height: auto;
        width: 100%;
        layout: horizontal;
        padding: 1 0;
    }

    .tweets-section {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .empty-message {
        color: $text-muted;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the Twitter screen layout."""
        # Header
        yield Static("🐦 Twitter Bot", classes="screen-header")

        # Post Composer
        yield Static("Compose Tweet", classes="section-header")
        with Container(classes="composer-section"):
            yield TextArea(
                placeholder="What's happening?",
                id="tweet-composer",
                height=4,
            )
            yield Label(
                f"0/{self.MAX_CHARS} characters",
                id="char-count",
                classes="char-count",
            )
            with Horizontal(classes="button-row"):
                yield Button("Post Tweet", variant="primary", id="btn-post")
                yield Button("Schedule", id="btn-schedule")
                yield Button("Clear", id="btn-clear")

        # Scheduled Tweets
        yield Static("Scheduled Tweets", classes="section-header")
        with Container(classes="tweets-section"):
            yield DataTable(id="scheduled-table")
            yield Static(
                "No scheduled tweets", id="scheduled-empty", classes="empty-message"
            )

        # Recent Tweets
        yield Static("Recent Tweets", classes="section-header")
        with Container(classes="tweets-section"):
            yield DataTable(id="recent-table")
            yield Static("No recent tweets", id="recent-empty", classes="empty-message")

    def on_mount(self) -> None:
        """Initialize the Twitter screen."""
        self._setup_tables()
        self._load_recent_tweets()
        self._load_scheduled_tweets()

    def _setup_tables(self) -> None:
        """Set up the data tables."""
        # Recent tweets table
        recent_table = self.query_one("#recent-table", DataTable)
        recent_table.add_columns("Date", "Tweet", "Status")
        recent_table.cursor_type = "row"

        # Scheduled tweets table
        scheduled_table = self.query_one("#scheduled-table", DataTable)
        scheduled_table.add_columns("Scheduled Time", "Tweet", "Actions")
        scheduled_table.cursor_type = "row"

    def _load_recent_tweets(self) -> None:
        """Load recent tweets from the database."""
        try:
            videos = get_videos(platform="twitter", limit=20)
            recent_table = self.query_one("#recent-table", DataTable)
            recent_empty = self.query_one("#recent-empty", Static)

            if videos:
                recent_empty.display = False
                for video in videos:
                    created_at = video.get("created_at", "Unknown")
                    title = video.get("title", "Untitled")[:50]
                    recent_table.add_row(created_at[:10], title, "Posted")
            else:
                recent_empty.display = True
        except Exception as e:
            pass

    def _load_scheduled_tweets(self) -> None:
        """Load scheduled tweets (placeholder)."""
        # Placeholder - would integrate with a scheduling system
        scheduled_empty = self.query_one("#scheduled-empty", Static)
        scheduled_empty.display = True

    def _update_char_count(self) -> None:
        """Update the character count display."""
        try:
            composer = self.query_one("#tweet-composer", TextArea)
            char_count = self.query_one("#char-count", Label)
            count = len(composer.text)
            char_count.update(f"{count}/{self.MAX_CHARS} characters")

            # Update color based on length
            char_count.remove_class("warning")
            char_count.remove_class("error")
            if count > self.MAX_CHARS:
                char_count.add_class("error")
            elif count > self.MAX_CHARS - 20:
                char_count.add_class("warning")
        except Exception:
            pass

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes for character count."""
        if event.text_area.id == "tweet-composer":
            self._update_char_count()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn-post":
            self._post_tweet()
        elif button_id == "btn-schedule":
            self._schedule_tweet()
        elif button_id == "btn-clear":
            self._clear_composer()

    def _post_tweet(self) -> None:
        """Post a tweet."""
        try:
            composer = self.query_one("#tweet-composer", TextArea)
            tweet_text = composer.text.strip()

            if not tweet_text:
                self.app.notify("Please enter tweet text", severity="warning")
                return

            if len(tweet_text) > self.MAX_CHARS:
                self.app.notify(
                    f"Tweet exceeds {self.MAX_CHARS} characters",
                    severity="error",
                )
                return

            # TODO: Integrate with Twitter class from classes/Twitter.py
            self.app.notify("Tweet posted! (stub)")
            self._clear_composer()
            self._load_recent_tweets()
        except Exception as e:
            self.app.notify(f"Error posting tweet: {e}", severity="error")

    def _schedule_tweet(self) -> None:
        """Schedule a tweet for later posting."""
        try:
            composer = self.query_one("#tweet-composer", TextArea)
            tweet_text = composer.text.strip()

            if not tweet_text:
                self.app.notify("Please enter tweet text", severity="warning")
                return

            # TODO: Implement actual scheduling
            self.app.notify("Tweet scheduled! (stub)")
            self._clear_composer()
        except Exception as e:
            self.app.notify(f"Error scheduling tweet: {e}", severity="error")

    def _clear_composer(self) -> None:
        """Clear the tweet composer."""
        try:
            composer = self.query_one("#tweet-composer", TextArea)
            composer.clear()
            self._update_char_count()
        except Exception:
            pass
