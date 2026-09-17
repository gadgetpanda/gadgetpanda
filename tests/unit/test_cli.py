from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from gadgetpanda.cli import main, parse_sex
from gadgetpanda.models import PpgSample, Raw6D


class TestParseSex(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(parse_sex("1"), 1)
        self.assertEqual(parse_sex("ชาย"), 1)
        self.assertEqual(parse_sex("male"), 1)
        self.assertEqual(parse_sex("0"), 0)
        self.assertEqual(parse_sex("หญิง"), 0)
        self.assertEqual(parse_sex("female"), 0)

    def test_invalid(self):
        with self.assertRaises(Exception):
            parse_sex("other")


class TestCliMain(unittest.TestCase):
    def test_user_sex_missing_value(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            main(["ring", "user", "--age", "32", "--weight", "78", "--height", "182", "--sex"])
        self.assertEqual(cm.exception.code, 2)
        self.assertTrue("--sex 1" in err.getvalue() or "ชาย" in err.getvalue())

    def test_user_accepts_male_flag(self):
        with patch("gadgetpanda.cli.asyncio.run") as run:
            main(["ring", "user", "--age", "32", "--weight", "78", "--height", "182", "--male"])
            self.assertTrue(run.called)
            coro = run.call_args.args[0]
            self.assertEqual(coro.cr_frame.f_locals["sex"], 1)
            coro.close()

    def test_user_accepts_sex_word(self):
        with patch("gadgetpanda.cli.asyncio.run") as run:
            main(["ring", "user", "--age", "32", "--weight", "78", "--height", "182", "--sex", "หญิง"])
            coro = run.call_args.args[0]
            self.assertEqual(coro.cr_frame.f_locals["sex"], 0)
            coro.close()

    def test_scan_default(self):
        with patch("gadgetpanda.cli.asyncio.run") as run:
            main([])
            self.assertTrue(run.called)
            run.call_args.args[0].close()

    def test_dog_caps(self):
        out = io.StringIO()
        with redirect_stdout(out):
            main(["dog", "caps", "--model", "x1"])
        text = out.getvalue()
        self.assertIn("x1", text)
        self.assertIn("FX_VOICE", text)

    def test_dog_scan_dispatches(self):
        with patch("gadgetpanda.cli.asyncio.run") as run:
            main(["dog", "scan", "--loose"])
            self.assertTrue(run.called)
            run.call_args.args[0].close()


class TestCliPrinters(unittest.TestCase):
    def test_print_imu_uses_peak_gyro(self):
        from gadgetpanda.cli import _print_imu

        out = io.StringIO()
        with redirect_stdout(out):
            _print_imu(
                (
                    Raw6D(-128, 3520, -2240, 0, 0, 0),
                    Raw6D(-100, 3400, -2000, 12, -4, 3),
                )
            )
        text = out.getvalue()
        self.assertIn("gyro=(12,-4,3)", text)
        self.assertIn("gyros=(0,0,0) (12,-4,3)", text)

    def test_print_ppg_values(self):
        from gadgetpanda.cli import _print_ppg

        out = io.StringIO()
        with redirect_stdout(out):
            _print_ppg((PpgSample(flag=1, value=1200), PpgSample(flag=1, value=1198)))
        self.assertIn("ppg flag=1 n=2 1200 1198", out.getvalue())

    def test_brand_display_on_print(self):
        from gadgetpanda.cli import _print
        from gadgetpanda.models import oem_vendor_mark

        out = io.StringIO()
        with redirect_stdout(out):
            _print(f"connected {oem_vendor_mark()} RL503")
        text = out.getvalue()
        self.assertIn("gadgetpanda", text)
        self.assertIn("RING503PANDA", text)
        self.assertNotIn(oem_vendor_mark().lower(), text.lower())


if __name__ == "__main__":
    unittest.main()
