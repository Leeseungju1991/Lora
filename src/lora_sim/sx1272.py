from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

from .spi_bus import SPIBus

class Reg(IntEnum):
    # 실제 칩 레지스터 전체가 아니라 데모용 최소 subset
    OP_MODE = 0x01
    FIFO = 0x00
    IRQ_FLAGS = 0x12
    IRQ_FLAGS_MASK = 0x11
    FIFO_ADDR_PTR = 0x0D
    FIFO_TX_BASE_ADDR = 0x0E
    PAYLOAD_LENGTH = 0x22

class Mode(IntEnum):
    SLEEP = 0b000
    STDBY = 0b001
    TX = 0b011
    RXCONTINUOUS = 0b101

class IrqFlag(IntEnum):
    TX_DONE = 0b00001000  # 실제 의미와 비트는 단순화(데모)

@dataclass
class SX1272:
    """
    Semtech SX1272 계열 LoRa 트랜시버의 *행동*을 간단히 모사합니다.

    핵심 목표:
    - SPI로 레지스터/버퍼 접근
    - Mode 전환(STDBY/TX)
    - TX Done IRQ 플래그 생성(그림 2의 흐름 재현)
    """
    spi: SPIBus
    tx_air: "AirChannel"
    _mode: Mode = Mode.SLEEP
    _tx_countdown: int = 0
    _fifo: bytearray = field(default_factory=lambda: bytearray(256))

    def reset(self) -> None:
        # 레지스터 초기화(데모)
        self.spi.write_reg(Reg.OP_MODE, int(Mode.SLEEP))
        self.spi.write_reg(Reg.IRQ_FLAGS, 0x00)
        self.spi.write_reg(Reg.FIFO_TX_BASE_ADDR, 0x00)
        self.spi.write_reg(Reg.FIFO_ADDR_PTR, 0x00)
        self.spi.write_reg(Reg.PAYLOAD_LENGTH, 0x00)
        self._mode = Mode.SLEEP
        self._tx_countdown = 0
        self._fifo[:] = b"\x00" * len(self._fifo)

    def set_mode(self, mode: Mode) -> None:
        self._mode = mode
        self.spi.write_reg(Reg.OP_MODE, int(mode))
        if mode == Mode.TX:
            # TX 시작: payload 길이에 비례해서 완료까지 지연(틱 기반)
            payload_len = self.spi.read_reg(Reg.PAYLOAD_LENGTH)
            self._tx_countdown = max(1, payload_len // 4 + 1)

    def write_fifo(self, data: bytes) -> None:
        base = self.spi.read_reg(Reg.FIFO_TX_BASE_ADDR)
        ptr = self.spi.read_reg(Reg.FIFO_ADDR_PTR)
        start = base + ptr
        end = min(len(self._fifo), start + len(data))
        self._fifo[start:end] = data[: (end - start)]
        # addr ptr은 데모로 증가
        self.spi.write_reg(Reg.FIFO_ADDR_PTR, (ptr + len(data)) & 0xFF)
        self.spi.write_reg(Reg.PAYLOAD_LENGTH, len(data) & 0xFF)

    def clear_irq(self) -> None:
        self.spi.write_reg(Reg.IRQ_FLAGS, 0x00)

    def tick(self) -> None:
        """
        시간 경과를 한 step 진행합니다.
        TX 모드면 카운트다운 후 AirChannel로 패킷을 흘리고 TX_DONE IRQ를 올립니다.
        """
        if self._mode != Mode.TX:
            return

        if self._tx_countdown > 0:
            self._tx_countdown -= 1

        if self._tx_countdown == 0:
            # payload 추출
            payload_len = self.spi.read_reg(Reg.PAYLOAD_LENGTH)
            base = self.spi.read_reg(Reg.FIFO_TX_BASE_ADDR)
            payload = bytes(self._fifo[base : base + payload_len])

            self.tx_air.transmit(payload)

            # IRQ: TX_DONE
            flags = self.spi.read_reg(Reg.IRQ_FLAGS)
            self.spi.write_reg(Reg.IRQ_FLAGS, flags | int(IrqFlag.TX_DONE))

            # 자동 Standby(논문 흐름의 "Automatic Mode change STAND-BY" 느낌)
            self.set_mode(Mode.STDBY)


class AirChannel:
    """
    '무선 구간'을 간단히 모델링합니다.
    실제 RF는 없고, Gateway가 poll()로 가져가는 큐로만 동작합니다.
    """
    def __init__(self) -> None:
        self._queue: list[bytes] = []

    def transmit(self, payload: bytes) -> None:
        self._queue.append(payload)

    def poll(self) -> Optional[bytes]:
        if not self._queue:
            return None
        return self._queue.pop(0)
