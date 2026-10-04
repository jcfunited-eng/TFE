"""Transport-only tests. Scripted MMIO is NOT hardware or cognition evidence.

Extract pure definitions so importing the board server cannot load an overlay,
write camera registers, enable motors, or open a network service on the host.
"""
import ast
from pathlib import Path
import threading
import time
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "notebooks" / "loom_display_server.py"
tree = ast.parse(SOURCE.read_text())
names = {"bt_encode", "bt_decode", "bt_trits", "calculate_hardware", "api_calc"}
definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
for node in definitions:
    node.decorator_list = []
namespace = {"time": time, "MATHLOOM_ABI": 0x4D4C0001}
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(SOURCE), "exec"), namespace)
encode, decode, calculate = (namespace[name] for name in ("bt_encode", "bt_decode", "calculate_hardware"))


class ScriptedMMIO:
    """A supplied receipt, not a replacement arithmetic implementation."""
    def __init__(self, registers=None, status=(0, 1), abi=0x4D4C0001):
        self.registers = registers or {}
        self.status = list(status)
        self.abi = abi
        self.writes = []
        self.reads = []

    def read(self, address):
        self.reads.append(address)
        if address == 0x78:
            return self.abi
        if address == 0x7C:
            return self.status.pop(0) if len(self.status) > 1 else self.status[0]
        return self.registers[address]

    def write(self, address, value):
        self.writes.append((address, value))


class TransportTests(unittest.TestCase):
    def test_canonical_encoding_and_range(self):
        for value in range(-265720, 265721):
            self.assertEqual(decode(encode(value)), value)
        for value in (-265721, 265721, True):
            with self.assertRaises(ValueError):
                encode(value)
        with self.assertRaises(ValueError):
            decode(3)

    def test_sum_keeps_carry(self):
        for op, a, b, result in (("add", 265720, 265720, 531440),
                                 ("sub", -265720, 265720, -531440)):
            device = ScriptedMMIO({0x08: encode(result, 13)})
            receipt = calculate(device, a, b, op)
            self.assertEqual(receipt["result"], result)
            self.assertEqual(len(receipt["result_bt"]), 13)

    def test_all_product_bits(self):
        product = encode(-70607118400, 24)
        device = ScriptedMMIO({0x14: product >> 32, 0x0C: product & 0xFFFFFFFF})
        self.assertEqual(calculate(device, -265720, 265720, "mul")["result"], -70607118400)

    def test_compare_positions(self):
        for a, b, flag, result in ((1, 1, 1, 0), (2, 1, 2, 1), (1, 2, 4, -1)):
            device = ScriptedMMIO({0x08: flag << 29})
            self.assertEqual(calculate(device, a, b, "cmp")["result"], result)

    def test_division_waits_for_dedicated_status(self):
        device = ScriptedMMIO({0x0C: encode(-14), 0x10: encode(-2), 0x74: 15}, status=(0, 4, 4, 1))
        result = calculate(device, -100, 7, "div")
        self.assertEqual((result["result"], result["remainder"]), (-14, -2))
        self.assertEqual(device.reads[:5], [0x78, 0x7C, 0x7C, 0x7C, 0x7C])

    def test_full_cycle_count(self):
        device = ScriptedMMIO({0x0C: encode(265720), 0x10: 0, 0x74: 265721})
        self.assertEqual(calculate(device, 265720, 1, "div")["cycles"], 265721)

    def test_timeout_never_reads_product_as_quotient(self):
        device = ScriptedMMIO({0x0C: 1 << 25}, status=(0, 4))
        with self.assertRaises(TimeoutError):
            calculate(device, 100, 7, "div", timeout_seconds=0.001)
        self.assertNotIn(0x0C, device.reads)

    def test_legacy_image_refused_before_writes(self):
        device = ScriptedMMIO(abi=0)
        with self.assertRaises(RuntimeError):
            calculate(device, 1, 2, "add")
        self.assertEqual(device.writes, [])

    def test_busy_divider_refused_before_writes(self):
        device = ScriptedMMIO(status=(4,))
        with self.assertRaises(RuntimeError):
            calculate(device, 1, 2, "add")
        self.assertEqual(device.writes, [])

    def test_divide_by_zero_is_hardware_error(self):
        device = ScriptedMMIO(status=(0, 3))
        with self.assertRaises(ZeroDivisionError):
            calculate(device, 50, 0, "div")
        self.assertIn((0x0C, 1 << 16), device.writes)

    def test_corrupt_result_is_not_corrected_in_software(self):
        for registers in ({0x0C: encode(15), 0x10: encode(2), 0x74: 16},
                          {0x0C: encode(14), 0x10: encode(2), 0x74: 0}):
            with self.assertRaises(RuntimeError):
                calculate(ScriptedMMIO(registers), 100, 7, "div")
        with self.assertRaises(RuntimeError):
            calculate(ScriptedMMIO({0x08: encode(4)}), 1, 2, "add")

    def test_unverified_composed_operations_are_explicit(self):
        for op in ("sqrt", "pow"):
            with self.assertRaises(NotImplementedError):
                calculate(ScriptedMMIO(), 4, 2, op)

    def test_route_owns_lock_for_whole_transaction(self):
        class Request:
            args = {"a": "1", "b": "2", "op": "add"}

        lock = threading.Lock()
        class LockCheckedMMIO(ScriptedMMIO):
            def read(self, address):
                if not lock.locked():
                    raise AssertionError("unserialized hardware read")
                return super().read(address)
            def write(self, address, value):
                if not lock.locked():
                    raise AssertionError("unserialized hardware write")
                super().write(address, value)

        namespace.update(request=Request(), jsonify=lambda x: x, calc_lock=lock,
                         arcloom=LockCheckedMMIO({0x08: encode(3)}))
        self.assertEqual(namespace["api_calc"]()["result"], 3)
        self.assertFalse(lock.locked())


if __name__ == "__main__":
    unittest.main()
