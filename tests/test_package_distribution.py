import importlib.util
import pathlib
import tempfile
import unittest
from zipfile import ZipFile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "package_distribution.py"


def load_packager():
    spec = importlib.util.spec_from_file_location("package_distribution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageDistributionTests(unittest.TestCase):
    def test_distribution_contains_only_flat_fonts_and_licenses(self):
        packager = load_packager()

        with tempfile.TemporaryDirectory() as tmp:
            project_root = pathlib.Path(tmp)
            otf_dir = project_root / "otf"
            otf_dir.mkdir()
            for name in packager.EXPECTED_OTF_FILENAMES:
                (otf_dir / name).write_bytes(b"font")
            for source, _ in packager.LICENSE_ENTRIES:
                path = project_root / source
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("license")

            output = project_root / "distribution.zip"
            packager.write_distribution(otf_dir, output, project_root)

            with ZipFile(output) as archive:
                self.assertEqual(
                    archive.namelist(), packager.expected_archive_entries()
                )
            self.assertTrue(
                all("/" not in name for name in packager.expected_archive_entries())
            )

    def test_distribution_requires_the_complete_family(self):
        packager = load_packager()

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                packager.find_expected_otfs(pathlib.Path(tmp))


if __name__ == "__main__":
    unittest.main()
