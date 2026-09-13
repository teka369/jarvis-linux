from __future__ import annotations

import math
from dataclasses import dataclass

from ...core.events import AvatarState


@dataclass
class Joint:
    x: float
    y: float


class HumanoidRig:
    def __init__(self) -> None:
        self.phase = 0.0
        self.blink = 1.0
        self.look_x = 0.0
        self.look_y = 0.0

    def tick(self, state: AvatarState, energy: float, dt: float) -> None:
        speed = {
            AvatarState.IDLE: 0.55,
            AvatarState.LISTENING: 1.1,
            AvatarState.THINKING: 0.85,
            AvatarState.EXECUTING: 1.4,
            AvatarState.SEARCHING: 1.7,
            AvatarState.SPEAKING: 1.2 + energy,
            AvatarState.ERROR: 2.2,
            AvatarState.HIDDEN: 0.2,
        }.get(state, 0.6)
        self.phase += dt * speed
        t = self.phase % 4.2
        self.blink = 0.08 if 3.85 < t < 4.05 else 1.0
        target_x, target_y = {
            AvatarState.LISTENING: (0.0, -0.15),
            AvatarState.THINKING: (0.35, -0.2),
            AvatarState.SEARCHING: (math.sin(self.phase * 1.4) * 0.7, -0.1),
            AvatarState.SPEAKING: (0.0, 0.05),
            AvatarState.ERROR: (0.15, 0.25),
        }.get(state, (math.sin(self.phase * 0.3) * 0.12, 0.0))
        self.look_x += (target_x - self.look_x) * min(1.0, dt * 5)
        self.look_y += (target_y - self.look_y) * min(1.0, dt * 5)

    def pose(self, state: AvatarState, energy: float) -> dict[str, Joint]:
        p = self.phase
        breath = math.sin(p * 1.3) * 0.012
        sway = math.sin(p * 0.7) * 0.018
        if state == AvatarState.LISTENING:
            sway += 0.01
        if state == AvatarState.ERROR:
            sway += math.sin(p * 8) * 0.02
        hip = Joint(0.50 + sway, 0.58 + breath)
        chest = Joint(0.50 + sway * 0.6, 0.38 + breath)
        neck = Joint(0.50 + sway * 0.4, 0.28 + breath)
        head = Joint(0.50 + sway * 0.35 + self.look_x * 0.02, 0.16 + breath + self.look_y * 0.01)
        if state == AvatarState.THINKING:
            l_sh, r_sh = Joint(0.40, 0.34), Joint(0.60, 0.34)
            l_el, r_el = Joint(0.34, 0.44), Joint(0.62, 0.28)
            l_h, r_h = Joint(0.38, 0.52), Joint(0.54, 0.20)
        elif state == AvatarState.LISTENING:
            l_sh, r_sh = Joint(0.39, 0.34), Joint(0.61, 0.34)
            l_el, r_el = Joint(0.32, 0.42), Joint(0.68, 0.42)
            l_h, r_h = Joint(0.30, 0.36), Joint(0.70, 0.36)
        elif state == AvatarState.SPEAKING:
            open_ = 0.04 + energy * 0.06
            l_sh, r_sh = Joint(0.40, 0.34), Joint(0.60, 0.34)
            l_el, r_el = Joint(0.30, 0.40), Joint(0.70, 0.40)
            l_h, r_h = Joint(0.26, 0.32 + open_), Joint(0.74, 0.32 + open_)
        elif state == AvatarState.SEARCHING:
            l_sh, r_sh = Joint(0.40, 0.34), Joint(0.60, 0.33)
            l_el, r_el = Joint(0.33, 0.28), Joint(0.70, 0.24)
            l_h, r_h = Joint(0.30, 0.20), Joint(0.76, 0.16)
        elif state == AvatarState.EXECUTING:
            l_sh, r_sh = Joint(0.40, 0.34), Joint(0.60, 0.34)
            l_el, r_el = Joint(0.34, 0.46), Joint(0.66, 0.46)
            l_h, r_h = Joint(0.34, 0.56), Joint(0.66, 0.56)
        else:
            l_sh, r_sh = Joint(0.41, 0.35), Joint(0.59, 0.35)
            l_el, r_el = Joint(0.37, 0.46), Joint(0.63, 0.46)
            l_h, r_h = Joint(0.36, 0.56 + math.sin(p) * 0.01), Joint(0.64, 0.56 + math.cos(p) * 0.01)
        l_hip, r_hip = Joint(hip.x - 0.045, hip.y), Joint(hip.x + 0.045, hip.y)
        walk = math.sin(p * 2) * (0.02 if state in {AvatarState.SEARCHING, AvatarState.EXECUTING} else 0.006)
        return {
            "head": head, "neck": neck, "chest": chest, "hip": hip,
            "l_sh": l_sh, "r_sh": r_sh, "l_el": l_el, "r_el": r_el, "l_h": l_h, "r_h": r_h,
            "l_hip": l_hip, "r_hip": r_hip,
            "l_kn": Joint(l_hip.x - 0.01, 0.74 + walk), "r_kn": Joint(r_hip.x + 0.01, 0.74 - walk),
            "l_ft": Joint(l_hip.x - 0.01, 0.90), "r_ft": Joint(r_hip.x + 0.01, 0.90),
        }

    def mouth(self, state: AvatarState, energy: float) -> float:
        if state == AvatarState.SPEAKING:
            return 0.35 + energy * 0.9
        if state == AvatarState.ERROR:
            return 0.55
        if state == AvatarState.THINKING:
            return 0.12
        return 0.18
