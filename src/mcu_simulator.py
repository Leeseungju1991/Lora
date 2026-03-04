from __future__ import annotations

import argparse
import os
import random
import time

from lora_sim.spi_bus import SPIBus
from lora_sim.sx1272 import AirChannel, SX1272, Mode, Reg, IrqFlag
from gateway import Gateway, GatewayDB

class MCUSimulator:
    """
    논문에서 설명한 MCU 측 작업을 '흐름' 중심으로 재현합니다.

    - RTC/SPI/SENSOR/VALUE/RADIO 초기화
    - device_id 기반 노드 식별
    - SX1272를 SPI로 제어하여 payload FIFO에 쓰고 TX 모드로 전환
    - TxDone IRQ를 확인하여 송신 완료 처리
    """
    def __init__(self, device_id: str, radio: SX1272) -> None:
        if len(device_id) != 6:
            raise ValueError("device_id must be 6 chars (e.g., DEV001) for this demo")
        self.device_id = device_id
        self.radio = radio

    def init_peripherals(self) -> None:
        # 데모: 실제 RTC/SPI 초기화 대신 로그/리셋 수행
        self.radio.reset()
        self.radio.set_mode(Mode.STDBY)

    def read_sensor_bytes(self, size: int) -> bytes:
        # 데모: 센서값을 랜덤 바이트로 대체
        return bytes(random.randint(0, 255) for _ in range(size))

    def send_uplink(self, payload_size: int = 12) -> None:
        # 1) payload 구성: [device_id(6)] + [sensor bytes]
        payload = self.device_id.encode("ascii") + self.read_sensor_bytes(payload_size)

        # 2) FIFO에 쓰기
        self.radio.spi.write_reg(Reg.FIFO_ADDR_PTR, 0x00)
        self.radio.write_fifo(payload)

        # 3) TX 모드 요청
        self.radio.clear_irq()
        self.radio.set_mode(Mode.TX)

        # 4) TxDone IRQ 대기(틱 기반)
        while True:
            self.radio.tick()
            flags = self.radio.spi.read_reg(Reg.IRQ_FLAGS)
            if flags & int(IrqFlag.TX_DONE):
                break
            time.sleep(0.05)

        # 5) IRQ 클리어 및 Standby 복귀는 radio.tick()에서 처리
        self.radio.clear_irq()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", required=True, help="6-char device id, e.g., DEV001")
    parser.add_argument("--interval", type=float, default=2.0, help="send interval seconds")
    parser.add_argument("--payload-size", type=int, default=12, help="sensor payload bytes (excluding 6-byte device id)")
    parser.add_argument("--with-gateway", action="store_true", help="run an in-process gateway poller (no web)")
    args = parser.parse_args()

    air = AirChannel()
    spi = SPIBus()
    radio = SX1272(spi=spi, tx_air=air)

    mcu = MCUSimulator(args.device_id, radio)
    mcu.init_peripherals()

    gw = None
    if args.with_gateway:
        db = GatewayDB("gateway.sqlite3")
        db.init()
        gw = Gateway(air, db)

    print(f"[MCU] start device_id={args.device_id} interval={args.interval}s payload_size={args.payload_size}")
    while True:
        mcu.send_uplink(args.payload_size)
        print("[MCU] uplink sent")
        if gw:
            # 가능하면 곧바로 수신 처리
            for _ in range(5):
                if not gw.process_once():
                    break
                time.sleep(0.05)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
