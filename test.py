#%%
from pylablib.devices.Thorlabs import list_kinesis_devices
from pylablib.devices import Thorlabs

print(list_kinesis_devices())

print(type(list_kinesis_devices()[0][0]))
print(list_kinesis_devices()[0][0])

# %%
# dev = KinesisMotor(list_kinesis_devices()[0][0])
# dev.open()
# print(dev.get_position())
# dev.move_by(1000)
# print("Waiting for move...")
# dev.wait_for_stop()
# dev.home()
# print("Waiting for home...")
# dev.wait_for_home()
# print("Done.")
# %%
# with Thorlabs.KinesisMotor(list_kinesis_devices()[0][0]) as dev:
with Thorlabs.KinesisMotor("26005554") as dev:
    # dev.open()
    dev._enable_channel(True, 1)
    print(dev.get_position())
    dev.move_by(1000, 1)
    print("Waiting for move...")
    dev.wait_move()
    # dev.wait_for_stop()
    # dev.home()
    # print("Waiting for home...")
    # dev.wait_for_home()
    print("Done.")