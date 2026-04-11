"""AFM Screen - Affiliate Marketing management."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Static, TextArea

from src.db import get_videos


class AFMScreen(Screen):
    """Affiliate Marketing screen with products, pitch generator, and campaigns."""

    CSS = """
    AFMScreen {
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

    .products-section {
        height: auto;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .pitch-section {
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

    .stats-section {
        height: auto;
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
        """Compose the AFM screen layout."""
        # Header
        yield Static("💰 Affiliate Marketing", classes="screen-header")

        with Horizontal(classes="main-content"):
            # Left Panel
            with Vertical(classes="left-panel"):
                # Products
                yield Static("Products", classes="section-header")
                with Container(classes="products-section"):
                    yield DataTable(id="products-table")
                    yield Static(
                        "No products added",
                        id="products-empty",
                        classes="empty-message",
                    )
                    with Horizontal(classes="button-row"):
                        yield Button(
                            "+ Add Product", variant="primary", id="btn-add-product"
                        )
                        yield Button("Import from Amazon", id="btn-import")

                # Pitch Generator
                yield Static("Pitch Generator", classes="section-header")
                with Container(classes="pitch-section"):
                    with Horizontal(classes="form-row"):
                        yield Label("Niche:", classes="form-label")
                        yield Input(
                            placeholder="e.g., tech gadgets",
                            id="input-niche",
                            classes="form-input",
                        )
                    with Horizontal(classes="form-row"):
                        yield Label("Affiliate Link:", classes="form-label")
                        yield Input(
                            placeholder="https://amazon.com/...",
                            id="input-link",
                            classes="form-input",
                        )
                    with Horizontal(classes="button-row"):
                        yield Button(
                            "Generate Pitch", variant="primary", id="btn-pitch"
                        )
                        yield Button("Copy Pitch", id="btn-copy-pitch")
                    yield TextArea(
                        placeholder="Generated pitch will appear here...",
                        id="pitch-output",
                        read_only=True,
                    )

            # Right Panel
            with Vertical(classes="right-panel"):
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
                        yield Button("View All", id="btn-view-campaigns")

                # Performance Stats
                yield Static("Performance", classes="section-header")
                with Container(classes="stats-section"):
                    yield Static(
                        "Total Clicks: 0 | Total Sales: $0.00 | Conversion: 0%",
                        id="afm-stats",
                    )
                    with Horizontal(classes="button-row"):
                        yield Button("Refresh Stats", id="btn-refresh-stats")
                        yield Button("Export Report", id="btn-export-report")

    def on_mount(self) -> None:
        """Initialize the AFM screen."""
        self._setup_tables()
        self._load_products()
        self._load_campaigns()
        self._refresh_stats()

    def _setup_tables(self) -> None:
        """Set up the data tables."""
        # Products table
        products_table = self.query_one("#products-table", DataTable)
        products_table.add_columns("Product", "ASIN", "Clicks", "Sales", "Revenue")
        products_table.cursor_type = "row"

        # Campaigns table
        campaigns_table = self.query_one("#campaigns-table", DataTable)
        campaigns_table.add_columns("Campaign", "Status", "Products", "Revenue")
        campaigns_table.cursor_type = "row"

    def _load_products(self) -> None:
        """Load products (placeholder - would integrate with AFM class)."""
        products_empty = self.query_one("#products-empty", Static)
        products_empty.display = True

    def _load_campaigns(self) -> None:
        """Load campaigns (placeholder)."""
        campaigns_empty = self.query_one("#campaigns-empty", Static)
        campaigns_empty.display = True

    def _refresh_stats(self) -> None:
        """Refresh performance stats."""
        try:
            # Placeholder stats - would integrate with AFM class
            stats = self.query_one("#afm-stats", Static)
            stats.update("Total Clicks: 0 | Total Sales: $0.00 | Conversion: 0%")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn-add-product":
            self._add_product()
        elif button_id == "btn-import":
            self._import_amazon()
        elif button_id == "btn-pitch":
            self._generate_pitch()
        elif button_id == "btn-copy-pitch":
            self._copy_pitch()
        elif button_id == "btn-new-campaign":
            self._new_campaign()
        elif button_id == "btn-view-campaigns":
            self._view_campaigns()
        elif button_id == "btn-refresh-stats":
            self._refresh_stats()
        elif button_id == "btn-export-report":
            self._export_report()

    def _add_product(self) -> None:
        """Add a new product."""
        # TODO: Implement product add form
        self.app.notify("Add product form (stub)", severity="info")

    def _import_amazon(self) -> None:
        """Import products from Amazon."""
        # TODO: Integrate with AffiliateMarketing class
        self.app.notify("Amazon import (stub)", severity="info")

    def _generate_pitch(self) -> None:
        """Generate an affiliate pitch using LLM."""
        try:
            niche_input = self.query_one("#input-niche", Input)
            link_input = self.query_one("#input-link", Input)
            pitch_output = self.query_one("#pitch-output", TextArea)

            niche = niche_input.value.strip()
            affiliate_link = link_input.value.strip()

            if not niche:
                self.app.notify("Please enter a niche", severity="warning")
                return

            # TODO: Integrate with AffiliateMarketing class from classes/AFM.py
            # For now, show placeholder
            pitch_output.text = (
                f"Generated pitch for niche: {niche}\n\n"
                + "This is a placeholder pitch. Integrate with AFM class for actual generation."
            )

            self.app.notify("Pitch generated! (stub)", severity="info")
        except Exception as e:
            self.app.notify(f"Error generating pitch: {e}", severity="error")

    def _copy_pitch(self) -> None:
        """Copy the pitch to clipboard."""
        try:
            pitch_output = self.query_one("#pitch-output", TextArea)
            pitch = pitch_output.text
            if pitch:
                # TODO: Copy to clipboard
                self.app.notify("Pitch copied! (stub)", severity="info")
            else:
                self.app.notify("No pitch to copy", severity="warning")
        except Exception:
            pass

    def _new_campaign(self) -> None:
        """Create a new campaign."""
        # TODO: Implement campaign creation form
        self.app.notify("New campaign form (stub)", severity="info")

    def _view_campaigns(self) -> None:
        """View all campaigns."""
        self.app.notify("View campaigns (stub)", severity="info")

    def _export_report(self) -> None:
        """Export performance report."""
        # TODO: Implement report export
        self.app.notify("Export report (stub)", severity="info")
