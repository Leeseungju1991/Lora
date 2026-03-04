from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

class SPIError(Exception):
    pass

@dataclass
class SPIBus:
    """
    MCU <-> LoRa 트랜시버(SX1272) 사이의 SPI 버스를 단순 모델링합니다.

    - 실제 SPI 타이밍/클럭/CS 신호는 구현하지 않고,
      '레지스터 주소에 값을 쓰고(read/write) 읽는다'는 행위만 제공합니다.
    """
    registers: Dict[int, int] = field(default_factory=dict)

    def write_reg(self, addr: int, value: int) -> None:
        if not (0 <= addr <= 0xFF):
            raise SPIError(f"Invalid register address: {addr}")
        self.registers[addr] = value & 0xFF

    def read_reg(self, addr: int) -> int:
        if not (0 <= addr <= 0xFF):
            raise SPIError(f"Invalid register address: {addr}")
        return self.registers.get(addr, 0x00)
