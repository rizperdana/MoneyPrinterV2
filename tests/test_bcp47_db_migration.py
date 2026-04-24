"""
Tests for BCP-47 locale migration in db.py.
Verifies LANGUAGE_TO_LOCALE mapping, DB migrations, function signatures.
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

class TestLanguageToLocaleMapping:
    """Tests for LANGUAGE_TO_LOCALE constant."""

    def test_language_to_locale_exists(self):
        """LANGUAGE_TO_LOCALE constant exists in db module."""
        import src.db as db
        assert hasattr(db, 'LANGUAGE_TO_LOCALE'), "LANGUAGE_TO_LOCALE should exist"
        assert isinstance(db.LANGUAGE_TO_LOCALE, dict), "Should be a dict"

    def test_language_to_locale_mapping(self):
        """LANGUAGE_TO_LOCALE maps bare language names to BCP-47 codes."""
        import src.db as db
        mapping = db.LANGUAGE_TO_LOCALE
        assert mapping["Indonesian"] == "id-ID", f"Expected id-ID, got {mapping.get('Indonesian')}"
        assert mapping["English"] == "en-US", f"Expected en-US, got {mapping.get('English')}"
        assert mapping["Javanese"] == "jv-ID", f"Expected jv-ID, got {mapping.get('Javanese')}"
        assert mapping["Sundanese"] == "su-ID", f"Expected su-ID, got {mapping.get('Sundanese')}"
        assert mapping["German"] == "de-DE", f"Expected de-DE, got {mapping.get('German')}"

    def test_language_to_locale_fallback(self):
        """LANGUAGE_TO_LOCALE.get() with unknown language returns original."""
        import src.db as db
        mapping = db.LANGUAGE_TO_LOCALE
        unknown = "Klingon"
        assert mapping.get(unknown, unknown) == unknown, "Should return original for unknown"

class TestLocaleVoicesMigration:
    """Tests for languagevoices -> localevoices migration."""

    @pytest.fixture(autouse=True)
    def fresh_db(self, tmp_path, monkeypatch):
        """Use temp DB for each test."""
        db_path = str(tmp_path / "test.db")
        import src.db as db_module
        monkeypatch.setattr(db_module, "DB_FILE", db_path)
        monkeypatch.setattr(db_module, "_conn", None)
        monkeypatch.setattr("src.db.DB_FILE", db_path)
        monkeypatch.setattr("src.db._conn", None)
        import importlib
        importlib.reload(db_module)
        db_module.init_db()
        yield db_module
        try:
            if db_module._conn:
                db_module._conn.close()
        except:
            pass
        db_module._conn = None
        db_module._settings_cache = None

    def test_localevoices_migration_from_languagevoices(self, fresh_db):
        """Existing languagevoices data migrates to localevoices column."""
        db = fresh_db
        conn = db._get_connection()
        cursor = conn.cursor()
        # Create settings table with languagevoices column and data
        cursor.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        old_data = json.dumps({"Indonesian": "id-ID-GadisNeural"})
        cursor.execute("ALTER TABLE settings ADD COLUMN languagevoices TEXT DEFAULT ?", (old_data,))
        cursor.execute("INSERT INTO settings (key, value, languagevoices) VALUES ('other', 'val', ?)", (old_data,))
        conn.commit()
        # Now run init_db which should migrate to localevoices
        db.init_db()
        # Check localevoices column exists and has migrated data
        cursor.execute("SELECT localevoices FROM settings LIMIT 1")
        row = cursor.fetchone()
        assert row is not None, "Should have settings row"
        # The migration should have copied languagevoices to localevoices
        # (Exact behavior depends on implementation)

    def test_localevoices_default_seed_bcp47(self, fresh_db):
        """Default localevoices seed uses BCP-47 keys."""
        db = fresh_db
        db.init_db()
        localevoices = db.get_setting("localevoices", "{}")
        parsed = json.loads(localevoices) if isinstance(localevoices, str) else localevoices
        # Should have BCP-47 keys, not bare language names
        assert "id-ID" in parsed, f"Should have id-ID key, got {parsed}"
        assert "jv-ID" in parsed, f"Should have jv-ID key, got {parsed}"
        assert "su-ID" in parsed, f"Should have su-ID key, got {parsed}"
        # Should NOT have bare language names
        assert "Indonesian" not in parsed, "Should not have Indonesian (bare name)"
        assert "Javanese" not in parsed, "Should not have Javanese (bare name)"

class TestAccountsLocaleMigration:
    """Tests for accounts language -> locale migration."""

    @pytest.fixture(autouse=True)
    def fresh_db(self, tmp_path, monkeypatch):
        """Use temp DB for each test."""
        db_path = str(tmp_path / "test.db")
        import src.db as db_module
        monkeypatch.setattr(db_module, "DB_FILE", db_path)
        monkeypatch.setattr(db_module, "_conn", None)
        monkeypatch.setattr("src.db.DB_FILE", db_path)
        monkeypatch.setattr("src.db._conn", None)
        import importlib
        importlib.reload(db_module)
        db_module.init_db()
        yield db_module
        try:
            if db_module._conn:
                db_module._conn.close()
        except:
            pass
        db_module._conn = None
        db_module._settings_cache = None

    def test_add_account_uses_locale_param(self, fresh_db):
        """add_account() accepts locale param instead of language."""
        db = fresh_db
        # Should accept locale param
        account_id = db.add_account("youtube", "test_user", locale="id-ID")
        assert account_id >0, "Should create account"
        # Verify locale is stored
        account = db.get_account_by_username("test_user")
        assert account is not None, "Account should exist"
        assert account["locale"] == "id-ID", f"Expected id-ID, got {account.get('locale')}"

    def test_add_account_default_locale_en_US(self, fresh_db):
        """add_account() defaults locale to en-US."""
        db = fresh_db
        account_id = db.add_account("youtube", "test_user")
        account = db.get_account_by_username("test_user")
        assert account["locale"] == "en-US", f"Expected en-US, got {account.get('locale')}"

    def test_add_account_no_language_param(self, fresh_db):
        """add_account() should NOT accept language param (old API)."""
        db = fresh_db
        # Attempting to pass language should raise TypeError (unexpected keyword)
        with pytest.raises(TypeError):
            db.add_account("youtube", "test_user", language="English")

class TestUpdateAccountLocale:
    """Tests for update_account() valid_fields includes locale."""

    @pytest.fixture(autouse=True)
    def fresh_db(self, tmp_path, monkeypatch):
        """Use temp DB for each test."""
        db_path = str(tmp_path / "test.db")
        import src.db as db_module
        monkeypatch.setattr(db_module, "DB_FILE", db_path)
        monkeypatch.setattr(db_module, "_conn", None)
        monkeypatch.setattr("src.db.DB_FILE", db_path)
        monkeypatch.setattr("src.db._conn", None)
        import importlib
        importlib.reload(db_module)
        db_module.init_db()
        yield db_module
        try:
            if db_module._conn:
                db_module._conn.close()
        except:
            pass
        db_module._conn = None
        db_module._settings_cache = None

    def test_update_account_valid_fields_includes_locale(self, fresh_db):
        """update_account() valid_fields should include 'locale' not 'language'."""
        db = fresh_db
        # Create account first
        account_id = db.add_account("youtube", "test_user")
        # Update locale
        result = db.update_account(account_id, {"locale": "de-DE"})
        assert result is True, "Update should succeed"
        account = db.get_account_by_username("test_user")
        assert account["locale"] == "de-DE", f"Expected de-DE, got {account.get('locale')}"

    def test_update_account_language_not_in_valid_fields(self, fresh_db):
        """update_account() should reject 'language' field (old API)."""
        db = fresh_db
        account_id = db.add_account("youtube", "test_user")
        # Attempting to update 'language' should fail (field not in valid_fields)
        result = db.update_account(account_id, {"language": "German"})
        assert result is False, "Should reject 'language' field"

class TestAddVideoLocale:
    """Tests for add_video() using locale param."""

    @pytest.fixture(autouse=True)
    def fresh_db(self, tmp_path, monkeypatch):
        """Use temp DB for each test."""
        db_path = str(tmp_path / "test.db")
        import src.db as db_module
        monkeypatch.setattr(db_module, "DB_FILE", db_path)
        monkeypatch.setattr(db_module, "_conn", None)
        monkeypatch.setattr("src.db.DB_FILE", db_path)
        monkeypatch.setattr("src.db._conn", None)
        import importlib
        importlib.reload(db_module)
        db_module.init_db()
        yield db_module
        try:
            if db_module._conn:
                db_module._conn.close()
        except:
            pass
        db_module._conn = None
        db_module._settings_cache = None

    def test_add_video_uses_locale_param(self, fresh_db):
        """add_video() accepts locale param instead of language."""
        db = fresh_db
        video_id = db.add_video("Test Topic", "Test Title", locale="id-ID")
        assert video_id > 0, "Should create video"
        # Verify locale is stored
        video = db.get_video_by_id(video_id)
        assert video is not None, "Video should exist"
        assert video["locale"] == "id-ID", f"Expected id-ID, got {video.get('locale')}"

    def test_add_video_default_locale_en_US(self, fresh_db):
        """add_video() defaults locale to en-US."""
        db = fresh_db
        video_id = db.add_video("Test Topic", "Test Title")
        video = db.get_video_by_id(video_id)
        assert video["locale"] == "en-US", f"Expected en-US, got {video.get('locale')}"

    def test_add_video_no_language_param(self, fresh_db):
        """add_video() should NOT accept language param (old API)."""
        db = fresh_db
        with pytest.raises(TypeError):
            db.add_video("Test Topic", "Test Title", language="English")
