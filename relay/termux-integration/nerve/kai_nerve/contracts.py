from __future__ import annotations
from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class RuntimeContract:
    version:str='0.4.0'
    minecraft_ingress_owner:str='kai-nerve-logcat-candidate'
    worldbus_owner:str='existing-kai-minecraft-worldbus'
    physical_actuator_owner:str='none-until-calibrated'
    new_listener_ports:tuple[int,...]=()
    actuation_shipped:bool=False
    main_world_allowed_for_first_sensor_test:bool=False
    def to_dict(self):return asdict(self)
