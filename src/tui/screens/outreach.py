"""Outreach Screen - Business outreach management."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Static, TextArea

from src.db import get_videos


class OutreachScreen(Screen):
    """Business outreach screen with search, campaigns, templates, and tracking."""

    CSS = """
    OutreachScreen {
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

    .main-content {
        height: 1fr;
        layout: horizontal;
    }

    .left-panel {
        width: 1fr;
        height: 100%;
        padding: 0 1;
    }

    .right-panel {
        width: 1fr;
        height: 100%;
        padding: 0 0 0 1;
    }

    .search-section {
        height: auto;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .campaigns-section {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .template-section {
        height: auto;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .tracking-section {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .form-row {
        height: auto;
        width: 100%;
        layout: horizontal;
        padding: 1 0;
    }

    .form-label {
        width: auto;
        height: auto;
        content-align: left middle;
        color: $text-muted;
    }

    .form-input {
        width: 1fr;
        height: auto;
    }

    .button-row {
        height: auto;
        width: 100%;
        layout: horizontal;
        padding: 1 0;
    }

    .empty-message {
        color: $text-muted;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the Outreach screen layout."""
        # Header
        yield Static("📧 Outreach", classes="screen-header")

        with Horizontal(classes="main-content"):
            # Left Panel
            with Vertical(classes="left-panel"):
                # Business Search
                yield Static("Find Businesses", classes="section-header")
                with Container(classes="search-section"):
                    with Horizontal(classes="form-row"):
                        yield Label("Niche:", classes="form-label")
                        yield Input(
                            placeholder="e.g., restaurants, plumbers",
                            id="input-niche",
                            classes="form-input",
                        )
                    with Horizontal(classes="form-row"):
                        yield Label("Location:", classes="form-label")
                        yield Input(
                            placeholder="e.g., New York, Los Angeles",
                            id="input-location",
                            classes="form-input",
                        )
                    with Horizontal(classes="button-row"):
                        yield Button("🔍 Search", variant="primary", id="btn-search")
                        yield Button("Stop", id="btn-stop-search")

                # Campaigns
                yield Static("Campaigns", classes="section-header")
                with Container(classes="campaigns-section"):
                    yield DataTable(id="campaigns-table")
                    yield Static(
                        "No campaigns yet",
                        id="campaigns-empty",
                        classes="empty-message",
                    )
                    with Horizontal(classes="button-row"):
                        yield Button(
                            "+ New Campaign", variant="primary", id="btn-new-campaign"
                        )
                        yield Button("Refresh", id="btn-refresh-campaigns")

            # Right Panel
            with Vertical(classes="right-panel"):
                # Email Template
                yield Static("Email Template", classes="section-header")
                with Container(classes="template-section"):
                    with Horizontal(classes="form-row"):
                        yield Label("Subject:", classes="form-label")
                        yield Input(
                            placeholder="Email subject...",
                            id="input-subject",
                            classes="form-input",
                        )
                    yield TextArea(
                        placeholder="Dear {{COMPANY_NAME}},\n\n...\n\nBest regards",
                        id="template-body",
                        height=8,
                    )
                    with Horizontal(classes="button-row"):
                        yield Button("Save Template", id="btn-save-template")
                        yield Button("Use Default", id="btn-use-default")

                # Send Tracking
                yield Static("Send Tracking", classes="section-header")
                with Container(classes="tracking-section"):
                    yield DataTable(id="tracking-table")
                    yield Static(
                        "No emails sent yet",
                        id="tracking-empty",
                        classes="empty-message",
                    )
                    yield Static(
                        "Sent: 0 | Delivered: 0 | Opened: 0 | Replied: 0",
                        id="tracking-stats",
                    )
                    with Horizontal(classes="button-row"):
                        yield Button("📧 Send Emails", variant="primary", id="btn-send")
                        yield Button("Export CSV", id="btn-export")

    def on_mount(self) -> None:
        """Initialize the Outreach screen."""
        self._setup_tables()
        self._load_campaigns()
        self._load_tracking()
        self._load_default_template()

    def _setup_tables(self) -> None:
        """Set up the data tables."""
        # Campaigns table
        campaigns_table = self.query_one("#campaigns-table", DataTable)
        campaigns_table.add_columns("Campaign", "Niche", "Businesses", "Sent", "Status")
        campaigns_table.cursor_type = "row"

        # Tracking table
        tracking_table = self.query_one("#tracking-table", DataTable)
        tracking_table.add_columns("Company", "Email", "Sent At", "Status", "Opened")
        tracking_table.cursor_type = "row"

    def _load_campaigns(self) -> None:
        """Load campaigns (placeholder - would integrate with Outreach class)."""
        campaigns_empty = self.query_one("#campaigns-empty", Static)
        campaigns_empty.display = True

    def _load_tracking(self) -> None:
        """Load email tracking data (placeholder)."""
        tracking_empty = self.query_one("#tracking-empty", Static)
        tracking_empty.display = True

    def _load_default_template(self) -> None:
        """Load the default email template."""
        try:
            subject_input = self.query_one("#input-subject", Input)
            body_input = self.query_one("#template-body", TextArea)

            subject_input.value = "Partnership Opportunity with {{COMPANY_NAME}}"
            body_input.text = """Dear {{COMPANY_NAME}},

I hope this email finds you well. I'm reaching out to explore a potential partnership opportunity that could benefit your business.

We help businesses like yours increase their online visibility and customer engagement through innovative marketing solutions.

Would you be open to a brief call this week to discuss how we might work together?

Best regards"""
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn-search":
            self._search_businesses()
        elif button_id == "btn-stop-search":
            self._stop_search()
        elif button_id == "btn-new-campaign":
            self._new_campaign()
        elif button_id == "btn-refresh-campaigns":
            self._load_campaigns()
        elif button_id == "btn-save-template":
            self._save_template()
        elif button_id == "btn-use-default":
            self._load_default_template()
        elif button_id == "btn-send":
            self._send_emails()
        elif button_id == "btn-export":
            self._export_tracking()

    def _search_businesses(self) -> None:
        """Search for businesses using the Google Maps scraper."""
        try:
            niche_input = self.query_one("#input-niche", Input)
            location_input = self.query_one("#input-location", Input)

            niche = niche_input.value.strip()
            location = location_input.value.strip()

            if not niche:
                self.app.notify("Please enter a niche", severity="warning")
                return

            # TODO: Integrate with Outreach class from classes/Outreach.py
            # For now, show placeholder
            self.app.notify(
                f"Searching for {niche} in {location or 'all locations'}... (stub)",
                severity="info",
            )
        except Exception as e:
            self.app.notify(f"Error searching: {e}", severity="error")

    def _stop_search(self) -> None:
        """Stop the business search."""
        self.app.notify("Search stopped", severity="info")

    def _new_campaign(self) -> None:
        """Create a new outreach campaign."""
        # TODO: Implement campaign creation form
        self.app.notify("New campaign form (stub)", severity="info")

    def _save_template(self) -> None:
        """Save the email template."""
        try:
            subject_input = self.query_one("#input-subject", Input)
            body_input = self.query_one("#template-body", TextArea)

            subject = subject_input.value
            body = body_input.text

            # TODO: Save template to config
            self.app.notify("Template saved!", severity="info")
        except Exception as e:
            self.app.notify(f"Error saving template: {e}", severity="error")

    def _send_emails(self) -> None:
        """Send emails to businesses in the current campaign."""
        try:
            template_body = self.query_one("#template-body", TextArea)
            body = template_body.text

            if not body or "{{COMPANY_NAME}}" not in body:
                self.app.notify(
                    "Template must include {{COMPANY_NAME}} placeholder",
                    severity="warning",
                )
                return

            # TODO: Integrate with Outreach class to send emails
            self.app.notify("Sending emails... (stub)", severity="info")
        except Exception as e:
            self.app.notify(f"Error sending emails: {e}", severity="error")

    def _export_tracking(self) -> None:
        """Export tracking data to CSV."""
        # TODO: Implement CSV export
        self.app.notify("Exporting to CSV... (stub)", severity="info")
