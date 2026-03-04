from lora_sim.spi_bus import SPIBus
from lora_sim.sx1272 import AirChannel, SX1272, Mode, IrqFlag, Reg
from gateway import Gateway, GatewayDB

def test_tx_flow_sets_irq_and_transmits():
    air = AirChannel()
    spi = SPIBus()
    radio = SX1272(spi=spi, tx_air=air)
    radio.reset()
    radio.set_mode(Mode.STDBY)

    payload = b"DEV001" + b"\x01\x02\x03\x04"
    spi.write_reg(Reg.FIFO_ADDR_PTR, 0x00)
    radio.write_fifo(payload)

    radio.clear_irq()
    radio.set_mode(Mode.TX)

    # tick until sent
    for _ in range(50):
        radio.tick()

    flags = spi.read_reg(Reg.IRQ_FLAGS)
    assert (flags & int(IrqFlag.TX_DONE)) == int(IrqFlag.TX_DONE)

    polled = air.poll()
    assert polled == payload
