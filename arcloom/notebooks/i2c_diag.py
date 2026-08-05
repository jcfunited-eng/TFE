"""
ArcLoom I2C Bus Diagnostics — read monitor ring buffer.

Usage in Jupyter (after overlay loaded):
    from pynq import MMIO
    mmio = MMIO(0x40000000, 0x100)
    %run i2c_diag.py
"""

REG_I2C_MON_CTRL = 0x68
REG_I2C_MON_DATA = 0x68
REG_I2C_MON_STATUS = 0x6C

def decode_transaction(bytes_list):
    if len(bytes_list) >= 4:
        addr = bytes_list[0][0]
        reg_hi = bytes_list[1][0]
        reg_lo = bytes_list[2][0]
        data = bytes_list[3][0]
        reg = (reg_hi << 8) | reg_lo
        rw = "W" if (addr & 1) == 0 else "R"
        dev = addr >> 1
        naks = sum(1 for _, _, ack in bytes_list if ack == 1)
        status = "OK" if naks == 0 else f"{naks} NAK!"
        print(f"       -> Dev 0x{dev:02X} {rw} Reg 0x{reg:04X} = 0x{data:02X}  [{status}]")

# Read status
status = mmio.read(REG_I2C_MON_STATUS)
count = status & 0x3FF
overflow = bool(status & (1 << 10))
print(f"I2C Monitor: {count} entries, overflow={overflow}")
print()

if count == 0:
    print("No I2C traffic captured!")
else:
    n = min(count, 1024)
    transaction_bytes = []

    for i in range(n):
        mmio.write(REG_I2C_MON_CTRL, i)
        entry = mmio.read(REG_I2C_MON_DATA)

        seq = (entry >> 24) & 0xFF
        byte_val = (entry >> 16) & 0xFF
        byte_pos = (entry >> 8) & 0xFF
        ack = (entry >> 7) & 1
        is_start = (entry >> 6) & 1
        is_stop = (entry >> 5) & 1

        if is_start:
            if transaction_bytes:
                decode_transaction(transaction_bytes)
            transaction_bytes = []
            print(f"  [{i:3d}] START")
        elif is_stop:
            if transaction_bytes:
                decode_transaction(transaction_bytes)
            transaction_bytes = []
            print(f"  [{i:3d}] STOP")
            print()
        else:
            ack_str = "ACK" if ack == 0 else "NAK"
            print(f"  [{i:3d}] 0x{byte_val:02X}  pos={byte_pos}  {ack_str}")
            transaction_bytes.append((byte_val, byte_pos, ack))

    if transaction_bytes:
        decode_transaction(transaction_bytes)

    print(f"\nTotal: {count} entries")
