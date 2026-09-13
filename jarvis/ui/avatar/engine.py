from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ...core.events import AvatarState


@dataclass
class Particle:
    angle: float
    radius: float
    speed: float
    size: float
    hue: float


class AvatarEngine:
    def __init__(self, count: int = 90) -> None:
        self.particles = [
            Particle(
                angle=random.random() * math.tau,
                radius=28 + random.random() * 70,
                speed=0.004 + random.random() * 0.018,
                size=1.2 + random.random() * 2.4,
                hue=random.random(),
            )
            for _ in range(count)
        ]
        self.phase = 0.0
        self.pulse = 0.15

    def tick(self, state: AvatarState, energy: float, dt: float = 0.033) -> None:
        boost = {
            AvatarState.IDLE: 0.35,
            AvatarState.LISTENING: 0.7,
            AvatarState.THINKING: 1.05,
            AvatarState.EXECUTING: 0.9,
            AvatarState.SPEAKING: 0.55 + energy * 1.6,
            AvatarState.ERROR: 0.8,
            AvatarState.HIDDEN: 0.1,
        }.get(state, 0.4)
        target = 0.12 + energy * 0.7
        self.pulse += (target - self.pulse) * min(1.0, dt * 6)
        self.phase += dt * (0.4 + boost)
        for p in self.particles:
            p.angle += p.speed * boost * (1.0 + energy * 1.8)
            wobble = math.sin(self.phase + p.angle) * (2 + energy * 10)
            p.radius = max(18.0, p.radius + wobble * 0.02)

    def palette(self, state: AvatarState) -> tuple[int, int, int]:
        return {
            AvatarState.IDLE: (80, 190, 255),
            AvatarState.LISTENING: (70, 255, 210),
            AvatarState.THINKING: (160, 120, 255),
            AvatarState.EXECUTING: (90, 220, 255),
            AvatarState.SPEAKING: (120, 210, 255),
            AvatarState.ERROR: (255, 90, 90),
            AvatarState.HIDDEN: (40, 40, 50),
        }.get(state, (80, 190, 255))
