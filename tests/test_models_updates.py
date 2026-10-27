import copy
import hashlib
import io
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import app
import model_sources
import updates
from PySide6.QtWidgets import QApplication


class ModelSourceTests(unittest.TestCase):
    @staticmethod
    def local_model(folder):
        folder.mkdir(exist_ok=True)
        (folder / "model.bin").write_bytes(struct.pack("<IH", 6, 12) + b"WhisperSpec\0")
        (folder / "config.json").write_text('{"suppress_ids": []}')
        (folder / "tokenizer.json").write_text('{}')
        (folder / "vocabulary.json").write_text('{}')
        return model_sources.inspect_local_directory(str(folder))

    def test_local_model_catalog_roundtrip_without_network(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(model_sources, "read_url") as network:
            spec = self.local_model(Path(folder) / "local-model")
            key = model_sources.custom_id(spec)
            catalog = Path(folder) / "catalog.json"
            model_sources.save_catalog(catalog, {key: spec})
            loaded = model_sources.load_catalog(catalog)
            self.assertEqual(loaded[key]["local_path"], spec["local_path"])
            network.assert_not_called()

    def test_local_model_rejects_wrong_format_and_missing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            self.local_model(path)
            (path / "tokenizer.json").unlink()
            with self.assertRaises(ValueError):
                model_sources.inspect_local_directory(folder)
            (path / "model.bin").write_bytes(b'GGUF' + b'0' * 30)
            with self.assertRaises(ValueError):
                model_sources.inspect_local_directory(folder)

    def specification(self):
        spec = copy.deepcopy(app.WHISPER_MODELS["large-v3-turbo"])
        spec["custom"] = True
        return spec

    def test_repo_id_rejects_urls_and_traversal(self):
        for value in ("../foo", "a/../../foo", "https://huggingface.co/a/b", "a/b?x=1", "a/b/c", "a/b\\c"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                model_sources.repository_id(value)

    def test_pinned_revision_controls_custom_identity(self):
        first = self.specification()
        second = copy.deepcopy(first)
        second["revision"] = "a" * 40
        self.assertNotEqual(model_sources.custom_id(first), model_sources.custom_id(second))

    def test_catalog_roundtrip_without_network(self):
        spec = self.specification()
        key = model_sources.custom_id(spec)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.json"
            model_sources.save_catalog(path, {key: spec, "medium": app.WHISPER_MODELS["medium"]})
            loaded = model_sources.load_catalog(path)
            self.assertEqual(set(loaded), {key})
            self.assertFalse(loaded[key]["translation"])

    def test_manifest_rejects_remote_code_and_unknown_paths(self):
        spec = self.specification()
        spec["files"]["../../app.py"] = (10, "a" * 64)
        with self.assertRaises(ValueError):
            model_sources.validate_manifest(spec)

    def test_catalog_rejects_invalid_container(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                model_sources.load_catalog(path)

    def test_feature_size_follows_binary_model(self):
        from faster_whisper.feature_extractor import FeatureExtractor
        model = SimpleNamespace(feature_extractor=FeatureExtractor(), feat_kwargs={},
                                model=SimpleNamespace(n_mels=128))
        app.VoiceApp._match_feature_size(model)
        self.assertEqual(model.feature_extractor.mel_filters.shape[0], 128)

    def test_inspection_checks_whisper_header_and_pins_revision(self):
        docs = {"config.json": b'{"suppress_ids": []}', "tokenizer.json": b'{}',
                "vocabulary.json": b'{}', "preprocessor_config.json": b'{"feature_size":128}'}
        entries = [{"rfilename": name, "size": len(data)} for name, data in docs.items()]
        entries.append({"rfilename": "model.bin", "size": 1000, "lfs": {"sha256": "a" * 64}})
        meta = {"sha": "b" * 40, "siblings": entries, "cardData": {"license": "mit"}}
        def get(url, **kwargs):
            return json.dumps(meta).encode() if "/api/" in url else docs[url.rsplit("/", 1)[-1]]
        header = struct.pack("<IH", 6, 12) + b"WhisperSpec\0"
        with patch.object(model_sources, "read_url", side_effect=get), patch.object(
            model_sources.urllib.request, "urlopen", return_value=io.BytesIO(header)):
            spec = model_sources.inspect_repository("user/arabic-ct2")
        self.assertEqual(spec["revision"], "b" * 40)
        self.assertFalse(spec["translation"])
        self.assertEqual(spec["files"]["tokenizer.json"][1], hashlib.sha256(b'{}').hexdigest())
        with patch.object(model_sources, "read_url", side_effect=get), patch.object(
            model_sources.urllib.request, "urlopen", return_value=io.BytesIO(b"not-whisper")):
            with self.assertRaises(ValueError):
                model_sources.inspect_repository("user/arabic-ct2")


class UpdateTests(unittest.TestCase):
    def test_numeric_version_comparison(self):
        self.assertIsNotNone(updates.newer_release({"tag_name": "v1.10.0"}, "1.9.0"))
        self.assertIsNone(updates.newer_release({"tag_name": "v1.5.0"}, "1.6.0"))
        self.assertIsNone(updates.newer_release({"tag_name": "v1.6.0"}, "1.6.0"))

    def test_no_prerelease_draft_or_unrecognized_tags(self):
        for payload in ({"tag_name": "v9.0.0", "draft": True},
                        {"tag_name": "v9.0.0", "prerelease": True},
                        {"tag_name": "v9.0.0-beta"}, {"tag_name": "bad"}):
            self.assertIsNone(updates.newer_release(payload, "1.6.0"))

    def test_download_link_is_fixed_and_notes_bounded(self):
        result = updates.newer_release({"tag_name": "v2.0.0", "html_url": "https://example.org", "body": "x" * 20000}, "1.6.0")
        self.assertEqual(result["url"], updates.RELEASES_URL)
        self.assertEqual(len(result["notes"]), 16000)


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def test_turbo_disables_translation_and_arabic_is_selectable(self):
        with patch.object(app.sd, "query_devices", return_value=[]):
            dialog = app.SettingsDialog(dict(app.DEFAULT_CONFIG))
        dialog._select_data(dialog.model_combo, "large-v3-turbo")
        self.assertFalse(dialog.translation_hotkey_control.isEnabled())
        self.assertTrue(dialog.model_notice.text())
        self.assertGreaterEqual(dialog.language_combo.findData("ar"), 0)
        dialog._select_data(dialog.model_combo, "large-v2")
        self.assertTrue(dialog.translation_hotkey_control.isEnabled())
        dialog.close()

    def test_overlay_timer_only_runs_when_visible(self):
        overlay = app.VoiceOverlay()
        self.assertFalse(overlay.timer.isActive())
        overlay.show_for_state("listening")
        self.assertTrue(overlay.timer.isActive())
        overlay.hide()
        self.assertFalse(overlay.timer.isActive())

    def test_turbo_guard_never_starts_microphone(self):
        fake = SimpleNamespace(settings_dialog=None, config={"model_id": "large-v3-turbo"},
                               tray=Mock(), recorder=Mock())
        app.VoiceApp.begin_recording(fake, "translate")
        fake.recorder.start.assert_not_called()
        fake.tray.showMessage.assert_called_once()

    def test_custom_manifest_survives_settings_population(self):
        spec = copy.deepcopy(app.WHISPER_MODELS["large-v3-turbo"])
        spec["custom"] = True
        key = model_sources.custom_id(spec)
        with patch.dict(app.WHISPER_MODELS, {key: spec}), patch.object(app.sd, "query_devices", return_value=[]):
            dialog = app.SettingsDialog({**app.DEFAULT_CONFIG, "model_id": key})
            self.assertEqual(dialog.model_combo.currentData(), key)
            self.assertFalse(dialog.translation_hotkey_control.isEnabled())
            dialog.close()

    def test_update_opt_out_makes_no_request(self):
        fake = SimpleNamespace(config={"check_updates": False}, _check_updates=Mock())
        app.VoiceApp._automatic_update_check(fake)
        fake._check_updates.assert_not_called()

    def test_update_interval_does_not_poll_each_hour_after_success(self):
        fake = SimpleNamespace(config={"check_updates": True, "last_update_check": 100000}, _check_updates=Mock())
        with patch.object(app.time, "time", return_value=103600):
            app.VoiceApp._automatic_update_check(fake)
        fake._check_updates.assert_not_called()
        with patch.object(app.time, "time", return_value=190000):
            app.VoiceApp._automatic_update_check(fake)
        fake._check_updates.assert_called_once_with(False)

    def test_failed_model_switch_restores_previous_selection(self):
        fake = SimpleNamespace(config={"model_id": "large-v3-turbo", "model_path": "new"},
                               model_rollback=("medium", "old"), tray=Mock(), _load_model_async=Mock())
        with patch.object(app, "save_config"), patch.object(app, "log_message"):
            app.VoiceApp._model_failed(fake, "error")
        self.assertEqual(fake.config["model_id"], "medium")
        self.assertEqual(fake.config["model_path"], "old")
        self.assertIsNone(fake.model_rollback)
        fake._load_model_async.assert_called_once()

    def test_disabled_translation_has_no_global_hook(self):
        fake = SimpleNamespace(config={**app.DEFAULT_CONFIG, "model_id": "large-v3-turbo"},
            key_pollers=[], keyboard_hooks=[], mouse_hooks=[], cancel_hook=None,
            overlay=Mock(), settings_dialog=None, state="ready", begin_recording=Mock(),
            finish_recording=Mock(), show_error=Mock(), cancel_recording=Mock())
        with patch.object(app, "KeyboardHook") as keyboard, patch.object(app, "KeyStatePoller"), patch.object(app, "log_message"):
            app.VoiceApp._configure_hotkey(fake)
            self.assertEqual([call.args[0] for call in keyboard.call_args_list], ["right_alt", "escape"])
            self.assertTrue(keyboard.call_args_list[-1].kwargs["ignore_modifiers"])

    def test_discard_does_not_concatenate_recording(self):
        recorder = app.AudioRecorder(None, 300)
        recorder.chunks = [app.np.ones(100, dtype=app.np.float32)]
        with patch.object(app.np, "concatenate") as concatenate:
            audio, _, _ = recorder.stop(discard=True)
        concatenate.assert_not_called()
        self.assertEqual(audio.size, 0)
        self.assertEqual(recorder.chunks, [])

    def test_manager_offers_download_resume_and_protects_active_model(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(app, "MODELS_DIR", Path(folder)):
            app.installed_model_path("tiny").mkdir()
            manager = app.ModelManagerDialog({**app.DEFAULT_CONFIG,
                "model_path": str(app.installed_model_path("medium"))})
            rows = list(app.WHISPER_MODELS)
            def buttons(model):
                return manager.table.cellWidget(rows.index(model), 3).findChildren(app.QPushButton)
            self.assertEqual(buttons("base")[0].text(), app.tr("Скачать", "Download"))
            self.assertEqual(buttons("tiny")[0].text(), app.tr("Докачать", "Resume"))
            self.assertEqual(len(buttons("medium")), 1)
            self.assertFalse(buttons("medium")[0].isEnabled())
            manager.close()

    def test_download_dialog_does_not_install_cuda_or_save_settings(self):
        dialog = app.ModelDownloadDialog("tiny")
        with patch.object(app, "ComponentInstallWorker") as worker, patch.object(app.QThreadPool, "globalInstance") as pool, patch.object(app, "save_config") as save:
            dialog._start()
            self.assertEqual(worker.call_args.args[:3], (True, False, "tiny"))
            pool.return_value.start.assert_called_once()
            dialog._completed({"model_id": "tiny", "model_path": "unused"})
            save.assert_not_called()
            self.assertEqual(dialog.result(), app.QDialog.DialogCode.Accepted)

    def test_download_cancellation_waits_for_worker(self):
        dialog = app.ModelDownloadDialog("tiny")
        dialog.worker = Mock()
        dialog.installing = True
        dialog.reject()
        dialog.worker.cancel.assert_called_once()
        self.assertTrue(dialog.installing)
        self.assertFalse(dialog.cancel_button.isEnabled())
        dialog._failed("cancelled")
        self.assertFalse(dialog.installing)
        self.assertEqual(dialog.result(), app.QDialog.DialogCode.Rejected)

    def test_download_failure_allows_retry(self):
        dialog = app.ModelDownloadDialog("tiny")
        dialog.installing = True
        dialog._failed("network unavailable")
        self.assertFalse(dialog.installing)
        self.assertFalse(dialog.retry_button.isHidden())
        self.assertTrue(dialog.cancel_button.isEnabled())
        dialog.close()

    def test_download_dialog_installs_files_without_changing_config(self):
        files = {"model.bin": b"model", "config.json": b"config",
                 "tokenizer.json": b"tokenizer", "vocabulary.txt": b"vocabulary"}
        spec = copy.deepcopy(app.WHISPER_MODELS["tiny"])
        spec["files"] = {name: (len(data), hashlib.sha256(data).hexdigest()) for name, data in files.items()}
        def response(request, **kwargs):
            name = request.full_url.split("?")[0].rsplit("/", 1)[-1]
            return io.BytesIO(files[name])
        with tempfile.TemporaryDirectory() as folder, patch.object(app, "MODELS_DIR", Path(folder) / "models"), patch.object(app, "INSTALL_DIR", Path(folder)), patch.dict(app.WHISPER_MODELS, {"tiny": spec}), patch.object(app.urllib.request, "urlopen", side_effect=response), patch.object(app, "save_config") as save:
            dialog = app.ModelDownloadDialog("tiny")
            dialog._start()
            self.assertTrue(app.QThreadPool.globalInstance().waitForDone(5000))
            self.qt.processEvents()
            self.assertEqual(dialog.result(), app.QDialog.DialogCode.Accepted)
            self.assertTrue(app.whisper_model_available(app.installed_model_path("tiny"), "tiny"))
            save.assert_not_called()

    def test_removing_local_model_keeps_original_files(self):
        with tempfile.TemporaryDirectory() as folder:
            spec = ModelSourceTests.local_model(Path(folder) / "original")
            key = model_sources.custom_id(spec)
            with patch.dict(app.WHISPER_MODELS, {key: spec}), patch.object(app, "CUSTOM_CATALOG_PATH", Path(folder) / "catalog.json"), patch.object(app.QMessageBox, "question", return_value=app.QMessageBox.StandardButton.Yes), patch.object(app.shutil, "rmtree") as remove:
                manager = app.ModelManagerDialog(dict(app.DEFAULT_CONFIG))
                self.assertEqual(app.installed_model_path(key), Path(spec["local_path"]))
                manager._remove_model(key)
                remove.assert_not_called()
                self.assertTrue((Path(spec["local_path"]) / "model.bin").is_file())
                self.assertNotIn(key, app.WHISPER_MODELS)
                manager.close()

    def test_active_directory_alias_cannot_be_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            spec = ModelSourceTests.local_model(Path(folder))
            key = model_sources.custom_id(spec)
            with patch.dict(app.WHISPER_MODELS, {key: spec}), patch.object(app.QMessageBox, "question") as prompt:
                manager = app.ModelManagerDialog({**app.DEFAULT_CONFIG, "model_path": folder})
                manager._remove_model(key)
                prompt.assert_not_called()
                manager.close()


class DownloaderTests(unittest.TestCase):
    def test_complete_corrupt_partial_restarts_without_range(self):
        data = b"good"
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "model.bin"
            target.with_suffix(".bin.part").write_bytes(b"fail")
            worker = app.ComponentInstallWorker(True, False, "medium", Path(folder))
            with patch.object(app.urllib.request, "urlopen", return_value=io.BytesIO(data)) as opened:
                worker._download("https://example.org/model", target, len(data), hashlib.sha256(data).hexdigest(), "model")
            self.assertNotIn("Range", opened.call_args.args[0].headers)
            self.assertEqual(target.read_bytes(), data)

    def test_resumed_download_hashes_prefix_and_new_bytes(self):
        data = b"hello model"
        response = io.BytesIO(data[5:])
        response.status = 206
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "model.bin"
            target.with_suffix(".bin.part").write_bytes(data[:5])
            worker = app.ComponentInstallWorker(True, False, "medium", Path(folder))
            with patch.object(app.urllib.request, "urlopen", return_value=response):
                worker._download("https://example.org/model", target, len(data), hashlib.sha256(data).hexdigest(), "model")
            self.assertEqual(target.read_bytes(), data)

    def test_corrupt_download_does_not_install(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "model.bin"
            worker = app.ComponentInstallWorker(True, False, "medium", Path(folder))
            with patch.object(app.urllib.request, "urlopen", return_value=io.BytesIO(b"bad")), self.assertRaises(RuntimeError):
                worker._download("https://example.org/model", target, 3, hashlib.sha256(b"yes").hexdigest(), "model")
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
