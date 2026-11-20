import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "tools/ci/check-android-control-surface.py"
spec = importlib.util.spec_from_file_location("android_control_surface", MODULE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def manifest(body: str, package: str = "") -> str:
    return (
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
        f'{package}><application>{body}</application></manifest>'
    )


class AndroidControlSurfaceTest(unittest.TestCase):
    def test_launcher_and_salvagenet_components_remain_allowed(self):
        guard.check_manifest(manifest("""
            <activity android:name=".MainActivity" android:exported="true">
                <intent-filter>
                    <action android:name="android.intent.action.MAIN" />
                    <category android:name="android.intent.category.LAUNCHER" />
                </intent-filter>
            </activity>
            <activity android:name="org.nodehost.shell.EnrollmentImportActivity" android:exported="true" />
            <service android:name=".service.PodroidService" android:exported="false" />
            <service android:name="org.nodehost.shell.NodeHostService" android:exported="false" />
            <provider android:name="androidx.core.content.FileProvider" android:exported="false" />
        """))
        guard.check_main_activity("class MainActivity : ComponentActivity() {}")

    def test_main_control_components_are_rejected_in_relative_and_full_form(self):
        for tag, name in (
            ("receiver", ".service.VmControlReceiver"),
            ("receiver", "com.excp.podroid.service.VmControlReceiver"),
            ("provider", ".engine.control.ControlProvider"),
            ("provider", "com.excp.podroid.engine.control.ControlProvider"),
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(guard.ControlSurfaceError, "component is registered"):
                    guard.check_manifest(manifest(f'<{tag} android:name="{name}" android:exported="false" />'))

    def test_component_package_attribute_is_used(self):
        with self.assertRaisesRegex(guard.ControlSurfaceError, "VmControlReceiver"):
            guard.check_manifest(manifest(
                '<receiver android:name="VmControlReceiver" />',
                'package="com.excp.podroid.service"',
            ))

    def test_compiled_debug_manifest_cannot_register_test_control(self):
        for tag, name in (("provider", "UmlTestProvider"), ("service", "UmlTestService")):
            with self.subTest(name=name):
                with self.assertRaisesRegex(guard.ControlSurfaceError, name):
                    guard.check_manifest(manifest(
                        f'<{tag} android:name="com.excp.podroid.umltest.{name}" '
                        'android:exported="true" android:permission="android.permission.DUMP" />',
                        'package="com.excp.podroid.debug"',
                    ))

    def test_automation_actions_are_rejected_on_otherwise_allowed_components(self):
        for action in ("START_VM", "STOP_VM"):
            with self.subTest(action=action):
                with self.assertRaisesRegex(guard.ControlSurfaceError, "action is registered"):
                    guard.check_manifest(manifest(
                        '<activity android:name=".MainActivity"><intent-filter>'
                        f'<action android:name="com.excp.podroid.action.{action}" />'
                        '</intent-filter></activity>'
                    ))

    def test_explicit_activity_dispatch_is_rejected_without_manifest_filter(self):
        for text in (
            "handleStartVmIntent(intent)",
            "if (intent.action == VmControlReceiver.ACTION_START_VM) start()",
            'if (intent.action == "com.excp.podroid.action.START_VM") start()',
        ):
            with self.subTest(text=text):
                with self.assertRaisesRegex(guard.ControlSurfaceError, "intent dispatch remains"):
                    guard.check_main_activity(text)

    def test_source_scan_checks_debug_overlay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "android/podroid/app/src"
            (source / "main").mkdir(parents=True)
            (source / "main/AndroidManifest.xml").write_text(manifest(""), encoding="utf-8")
            activity = source / "main/java/com/excp/podroid/MainActivity.kt"
            activity.parent.mkdir(parents=True)
            activity.write_text("class MainActivity {}", encoding="utf-8")
            self.assertEqual(1, guard.check_sources(root))
            (source / "debug").mkdir()
            (source / "debug/AndroidManifest.xml").write_text(manifest(
                '<provider android:name=".umltest.UmlTestProvider" />'
            ), encoding="utf-8")
            with self.assertRaisesRegex(guard.ControlSurfaceError, "debug/AndroidManifest.xml"):
                guard.check_sources(root)

    def test_invalid_decoded_manifest_fails_closed(self):
        for text in ("", "not XML", "<application />"):
            with self.subTest(text=text):
                with self.assertRaises(guard.ControlSurfaceError):
                    guard.check_manifest(text)


if __name__ == "__main__":
    unittest.main()
