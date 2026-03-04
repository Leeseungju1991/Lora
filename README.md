# LoRa 프로토콜용 범용 IoT 모듈 예제

논문 **LoRa 프로토콜을 위한 범용성 IoT 모듈 개발  아이디어**를 **실행 가능한 코드(시뮬레이터)** 형태로 재현한 예제입니다. 

Semtech SX1272 계열 LoRa 트랜시버를 **SPI**로 제어하는 MCU 보드(예: A31G123)를 기반으로,
모듈 초기화(RTC/SPI/SENSOR/VALUE/RADIO), 디바이스 ID 기반 식별, 송수신 동작 확인(Web 기반 Gateway 확인),
그리고 송신 플로우(그림 2의 Mode 전환/IRQ 기반 송신 완료 확인)를 구현

> ⚠️ 실제 무선 송수신/하드웨어 레지스터를 직접 제어하는 펌웨어가 아니라,  
> **흐름을 이해하고 재현**하기 위한 Python 기반 시뮬레이션 + 간단한 Gateway/Web 대시보드 예제입니다.

---

## 구성

- `src/lora_sim/` : SX1272 레지스터/모드/IRQ를 흉내내는 시뮬레이터
- `src/mcu_simulator.py` : MCU가 SPI로 LoRa 모듈을 초기화하고 센서값을 패킷으로 송신하는 흐름 구현
- `src/gateway.py` : Gateway(수신기) 역할. 수신 패킷을 SQLite에 저장
- `src/webapp.py` : 수신 데이터 조회용 Flask 웹 UI
- `tests/` : 최소 단위 테스트

---

## 빠른 시작

### 1) 설치
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
```

### 2) Gateway + Web UI 실행
```bash
python src/webapp.py
```

- 기본 접속: http://127.0.0.1:5000

### 3) MCU 시뮬레이터 실행 (패킷 송신)
다른 터미널에서:
```bash
python src/mcu_simulator.py --device-id DEV001 --interval 2
```

웹에서 `Devices`, `Packets` 메뉴를 확인하면, 디바이스 ID와 센서 값이 주기적으로 쌓입니다.

---

## 논문 흐름과 코드 매핑

- **초기화(RTC/SPI/SENSOR/VALUE/RADIO)**: `MCUSimulator.init_peripherals()`  
- **SPI read/write 및 Buffer 접근**: `lora_sim.spi_bus.SPIBus`, `lora_sim.sx1272.SX1272`
- **송신 알고리즘(Mode 요청 → TX → TxDone IRQ → Standby)**:  
  `MCUSimulator.send_uplink()` 내부 상태 전이 + `SX1272.tick()`의 IRQ 플래그 갱신
- **Gateway Web 확인(수신 데이터/디바이스 정보 확인)**: `gateway.GatewayDB`, `webapp.py`

---

## CLI 옵션

### MCU 시뮬레이터
```bash
python src/mcu_simulator.py --device-id DEV001 --interval 2 --payload-size 12
```

- `--device-id`: 디바이스 식별자(ID 기반 Node 식별)
- `--interval`: 송신 주기(초)
- `--payload-size`: 센서 payload 길이

---

## 개발 메모

- **SPI 기반 제어/모드 전환/IRQ 기반 완료 확인**을 중심으로 최소 동작 모델을 구성했습니다.

---
