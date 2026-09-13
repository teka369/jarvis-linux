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
    arm: int
    z: float


@dataclass
class Star:
    x: float
    y: float
    size: float
    twinkle: float


class AvatarEngine:
    def __init__(self, count: int = 160) -> None:
        self.particles = [
            Particle(
                angle=random.random() * math.tau,
                radius=18 + random.random() * 92,
                speed=0.003 + random.random() * 0.016,
                size=0.8 + random.random() * 2.8,
                arm=random.randint(0, 3),
                z=0.35 + random.random() * 0.65,
            )
            for _ in range(count)
        ]
        self.stars = [
            Star(random.random(), random.random(), 0.6 + random.random() * 1.6, random.random() * math.tau)
            for _ in range(42)
        ]
        self.phase = 0.0
        self.pulse = 0.14

    def tick(self, state: AvatarState, energy: float, dt: float = 0.033) -> None:
        boost = {
            AvatarState.IDLE: 0.28,
            AvatarState.LISTENING: 0.72,
            AvatarState.THINKING: 1.15,
            AvatarState.EXECUTING: 0.95,
            AvatarState.SPEAKING: 0.5 + energy * 1.8,
            AvatarState.ERROR: 0.85,
            AvatarState.HIDDEN: 0.08,
        }.get(state, 0.4)
        target = 0.1 + energy * 0.78
        self.pulse += (target - self.pulse) * min(1.0, dt * 5.5)
        self.phase += dt * (0.35 + boost)
        for p in self.particles:
            p.angle += p.speed * boost * (0.7 + energy * 2.0)
            spiral = math.sin(self.phase * 0.7 + p.arm + p.angle * 0.4) * (1.2 + energy * 8)
            p.radius = max(14.0, min(118.0, p.radius + spiral * 0.015))
        for s in self.stars:
            s.twinkle += dt * 2.2

    def palette(self, state: AvatarState) -> tuple[int, int, int]:
        return {
            AvatarState.IDLE: (70, 170, 255),
            AvatarState.LISTENING: (40, 255, 210),
            AvatarState.THINKING: (170, 110, 255),
            AvatarState.EXECUTING: (80, 210, 255),
            AvatarState.SPEAKING: (140, 200, 255),
            AvatarState.ERROR: (255, 80, 95),
            AvatarState.HIDDEN: (30, 30, 40),
        }.get(state, (70, 170, 255))
