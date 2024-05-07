# %%
from __future__ import annotations
from abc import abstractmethod
from typing import List, Optional, SupportsFloat as Numeric


class StageDevice:
    @staticmethod
    @abstractmethod
    def list_devices()->List[str | int]:
        """List all available devices.

        Returns:
            List[str | int]: List of device COM ports or serial numbers.
        """
        pass

    @abstractmethod
    def set_stage(self, stage: str):
        pass

    @abstractmethod
    def get_stage(self)->Optional[str]:
        pass

    def __del__(self):
        self.close()
        del self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def get_device_info(ser: int | str)->dict:
        return {}

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def home(self)->bool:
        """Home the device.

        Returns:
            bool: _description_
        """
        pass

    @abstractmethod
    def get_position(self)->Numeric:
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def is_moving(self)->bool:
        pass

    @abstractmethod
    def is_homing(self)->bool:
        pass

    @abstractmethod
    def move_to(self, position: int, backlash: int=None):
        pass

    @abstractmethod
    def move_relative(self, steps: int):
        pass

    @abstractmethod
    def short_name(self)->str:
        pass

    @abstractmethod
    def long_name(self)->str:
        pass