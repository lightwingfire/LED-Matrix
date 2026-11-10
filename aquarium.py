"""Aquarium display mode."""

from random import Random, SystemRandom
from colorsys import hsv_to_rgb
from math import atan2, ceil, cos, exp, floor, hypot, isfinite, pi, sin


class Fish:
    """A fish whose connected parts follow the head with a short delay."""

    def __init__(self, canvas, x=0, y=0, color=None, seed=None):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.baseColor = tuple(color) if color is not None else None
        self.drawOrder = ('tailfin_top', 'tailfin_bottom', 'tail',
                          'body_rear', 'body_middle', 'body_front', 'head')
        self.colors = {name: (0, 0, 0) for name in self.drawOrder}
        self.direction = (1.0, 0.0, 0.0)
        self.turnSpeed = 1.5  # Radians per second.
        self._yaw = self._pitch = 0.0
        self._targetYaw = self._targetPitch = 0.0
        self.turnEase = .6
        self._angularVelocity = [0.0, 0.0]
        self.time = 0.0
        self.swimAmplitude = 3.0
        self.swimSpeed = .8
        self.partDelay = .12
        self.followOrder = ('head', 'body_front', 'body_middle', 'body_rear', 'tail')
        self.partOffsets = {name: 0.0 for name in self.colors}
        self.partAngles = {name: (0.0, 0.0) for name in self.colors}
        self._partVelocity = {name: [0.0, 0.0] for name in self.colors}
        self.partTurnEase = dict(head=.10, body_front=.16, body_middle=.22,
                                 body_rear=.28, tail=.34, tailfin_top=.42,
                                 tailfin_bottom=.42)
        self.wandering = False
        self.wanderTarget = None
        self.wanderSpeed = 8.0
        self._wanderRandom = None
        self.brightness = 1.0
        self.shadowMode = False
        self.shadowColor = (0, 0, 40)
        self.change = True
        self.buildFish(seed)

    def buildFish(self, seed=None):
        """Build varied, overlapping parts; a seed can reproduce a fish's shape."""
        self.seed = seed if seed is not None else SystemRandom().randrange(2 ** 32)
        rng = Random(self.seed)
        self.height = 8
        self.depth = rng.randint(2, 3)
        # Tail -> rear body -> middle body -> front body -> head: one peak,
        # with gradual decreases on either side instead of narrow valleys.
        peak = rng.randrange(5)
        heights = [0] * 5
        heights[peak] = self.height
        for index in range(peak - 1, -1, -1):
            heights[index] = max(3, heights[index + 1] - rng.randint(1, 2))
        for index in range(peak + 1, len(heights)):
            heights[index] = max(3, heights[index - 1] - rng.randint(1, 2))
        tail_height, rear_height, middle_height, front_height, head_height = heights
        top_fin = bottom_fin = rng.randint(2, 3)
        tail_x = rng.randint(1, top_fin - 1)
        tail_y = (self.height - tail_height) // 2
        self.tailfin = ((0, max(0, tail_y - top_fin + 1), top_fin, top_fin),
                        (0, min(self.height - bottom_fin, tail_y + tail_height - 1),
                         bottom_fin, bottom_fin))
        self.partOverlap = {'tailfin_tail': top_fin - tail_x}
        self.tail = (tail_x, tail_y, rng.randint(3, 6), tail_height)

        def attach(parent_x, parent_width, width, joint):
            # More overlap brings parts closer; retain a visible strip of each.
            overlap = rng.randint(1, min(parent_width - 1, width - 1))
            self.partOverlap[joint] = overlap
            return parent_x + parent_width - overlap

        rear_width = rng.randint(2, 3)
        rear_x = attach(tail_x, self.tail[2], rear_width, 'tail_body')
        rear = (rear_x, (self.height - rear_height) // 2, rear_width, rear_height)
        middle_width = rng.randint(3, 6)
        middle = (attach(rear_x, rear_width, middle_width, 'body_rear_middle'),
                  (self.height - middle_height) // 2, middle_width, middle_height)
        front_width = rng.randint(2, 3)
        front = (attach(middle[0], middle_width, front_width, 'body_middle_front'),
                 (self.height - front_height) // 2,
                 front_width, front_height)
        self.body = (rear, middle, front)
        head_width = rng.randint(2, 3)
        self.head = (attach(front[0], front_width, head_width, 'body_head'),
                     (self.height - head_height) // 2, head_width, head_height)
        self.width = self.head[0] + self.head[2]
        hue = rng.random()
        palette = [tuple(round(channel * 255) for channel in
                         hsv_to_rgb((hue + index / 7) % 1,
                                    rng.uniform(.65, 1), rng.uniform(.7, 1)))
                   for index in range(7)]
        rng.shuffle(palette)
        self.colors = dict(zip(self.drawOrder, palette))
        if self.baseColor is not None:
            self.colors['body_middle'] = self.baseColor
        self.color = self.colors['body_middle']
        self.change = True

    def setShadowMode(self, enabled):
        if self.shadowMode != enabled:
            self.shadowMode = enabled
            self.change = True

    def setBrightness(self, br):
        brightness = max(0.0, min(1.0, br))
        if self.brightness != brightness:
            self.brightness = brightness
            self.change = True

    def getBrightness(self):
        return self.brightness

    def changed(self):
        change = self.change
        self.change = False
        return change

    def turnTo(self, direction):
        """Turn toward an (x, y, z) vector; positive z points into the screen."""
        x, y, z = (float(value) for value in direction)
        length = hypot(x, y, z)
        if not isfinite(length) or length == 0:
            raise ValueError('Fish direction must be a finite, nonzero 3D vector.')
        self._targetYaw = atan2(z, x)
        self._targetPitch = atan2(y, hypot(x, z))

    def setDirection(self, direction):
        """Set the 3D heading immediately instead of animating the turn."""
        self.turnTo(direction)
        self._yaw, self._pitch = self._targetYaw, self._targetPitch
        self.direction = (cos(self._pitch) * cos(self._yaw), sin(self._pitch),
                          cos(self._pitch) * sin(self._yaw))
        self._angularVelocity = [0.0, 0.0]
        for name in self.drawOrder:
            self.partAngles[name] = (self._yaw, self._pitch)
            self._partVelocity[name] = [0.0, 0.0]
        self.change = True

    @staticmethod
    def _easeAngle(current, target, velocity, dt, duration, max_speed):
        """Critically damped angular motion with a bounded cruise speed."""
        error = atan2(sin(current - target), cos(current - target))
        error = max(-max_speed * duration, min(max_speed * duration, error))
        adjusted_target = current - error
        omega = 2 / duration
        decay = exp(-omega * dt)
        impulse = (velocity + omega * error) * dt
        return (adjusted_target + (error + impulse) * decay,
                (velocity - omega * impulse) * decay)

    def update(self, dt):
        if dt <= 0:
            return
        # Small steps keep steering stable when the display frame rate varies.
        steps = max(1, ceil(dt * 30))
        for _ in range(steps):
            self._updateStep(dt / steps)

    def startWandering(self, bounds):
        """Swim between random destinations inside (left, top, right, bottom)."""
        self.swimBounds = bounds
        self.wandering = True
        self.wanderTarget = None

    def _updateWanderTarget(self):
        if self._wanderRandom is None:
            self._wanderRandom = Random()
        if self.wanderTarget is None or hypot(self.wanderTarget[0] - self.x,
                                             self.wanderTarget[1] - self.y) < 1:
            left, top, right, bottom = self.swimBounds
            self.wanderTarget = (self._wanderRandom.uniform(left, right),
                                 self._wanderRandom.uniform(top, bottom))
            self.wanderSpeed = self._wanderRandom.uniform(6, 10)
        dx, dy = self.wanderTarget[0] - self.x, self.wanderTarget[1] - self.y
        if hypot(dx, dy) > 0:
            self.turnTo((dx, dy, 0))

    def _updateStep(self, dt):
        """Pass a gentle vertical turn from the head back to the tailfin."""
        if self.wandering:
            self._updateWanderTarget()
        for index, (attribute, target) in enumerate((('_yaw', self._targetYaw), ('_pitch', self._targetPitch))):
            current = getattr(self, attribute)
            angle, velocity = self._easeAngle(current, target, self._angularVelocity[index],
                                               dt, self.turnEase, self.turnSpeed)
            setattr(self, attribute, angle)
            self._angularVelocity[index] = velocity
        self.direction = (cos(self._pitch) * cos(self._yaw), sin(self._pitch),
                          cos(self._pitch) * sin(self._yaw))
        target_angles = (self._yaw, self._pitch)
        for name in (*self.followOrder, 'tailfin_top', 'tailfin_bottom'):
            if name.startswith('tailfin'):
                target_angles = self.partAngles['tail']
            angles = []
            for index in range(2):
                angle, velocity = self._easeAngle(
                    self.partAngles[name][index], target_angles[index], self._partVelocity[name][index],
                    dt, self.partTurnEase[name], self.turnSpeed * 2)
                angles.append(angle)
                self._partVelocity[name][index] = velocity
            self.partAngles[name] = tuple(angles)
            target_angles = self.partAngles[name]
        if self.wandering:
            dx, dy = self.wanderTarget[0] - self.x, self.wanderTarget[1] - self.y
            distance = hypot(dx, dy)
            if distance > 0:
                # Slow during turns instead of sliding backward toward a target.
                alignment = max(0, (self.direction[0] * dx + self.direction[1] * dy) / distance)
                travel = min(distance, self.wanderSpeed * dt) * alignment ** 2
                left, top, right, bottom = self.swimBounds
                self.x = max(left, min(right, self.x + self.direction[0] * travel))
                self.y = max(top, min(bottom, self.y + self.direction[1] * travel))
        self.time += dt
        for index, name in enumerate(self.followOrder):
            elapsed = max(0.0, self.time - index * self.partDelay)
            self.partOffsets[name] = -self.swimAmplitude * sin(elapsed * self.swimSpeed)
        elapsed = max(0.0, self.time - len(self.followOrder) * self.partDelay)
        fin_offset = -self.swimAmplitude * sin(elapsed * self.swimSpeed)
        self.partOffsets['tailfin_top'] = fin_offset
        self.partOffsets['tailfin_bottom'] = fin_offset
        self.change = True

    def render(self, canvas=None):
        canvas = canvas if canvas is not None else self.canvas
        rectangles = (*self.tailfin, self.tail, *self.body, self.head)
        parts = dict(zip(self.drawOrder, rectangles))
        forwards = {name: (cos(pitch) * cos(yaw), sin(pitch), cos(pitch) * sin(yaw))
                    for name, (yaw, pitch) in self.partAngles.items()}
        # Anchor the spine at the middle body. Neighboring segments share a joint,
        # so different turn rates bend the fish rather than separating its parts.
        along = {name: rect[0] + rect[2] / 2 - self.width / 2 for name, rect in parts.items()}
        middle = 'body_middle'
        spine = {middle: tuple(value * along[middle] for value in forwards[middle])}
        for chain in ((middle, 'body_front', 'head'),
                      (middle, 'body_rear', 'tail', 'tailfin_top')):
            for parent, child in zip(chain, chain[1:]):
                distance = along[child] - along[parent]
                spine[child] = tuple(spine[parent][axis] + distance *
                                     (forwards[parent][axis] + forwards[child][axis]) / 2
                                     for axis in range(3))
        spine['tailfin_bottom'] = tuple(
            spine['tailfin_top'][axis] + (along['tailfin_bottom'] - along['tailfin_top']) *
            forwards['tailfin_bottom'][axis] for axis in range(3))
        # Keep the stack fixed, even when the fish faces away or turns left.
        for (x, y, width, height), name in zip(rectangles, self.drawOrder):
            yaw, pitch = self.partAngles[name]
            forward = forwards[name]
            up = (-sin(pitch) * cos(yaw), cos(pitch), -sin(pitch) * sin(yaw))
            side = (-sin(yaw), 0.0, cos(yaw))
            color = self.shadowColor if self.shadowMode else self.colors[name]
            red, green, blue = (round(channel * self.brightness) for channel in color)
            vertical = y + height / 2 - self.height / 2
            center_x = self.x + self.width / 2 + spine[name][0] + up[0] * vertical
            center_y = (self.y + self.height / 2 + spine[name][1] +
                        up[1] * vertical + self.partOffsets[name])
            half_width = (abs(forward[0]) * width + abs(up[0]) * height + abs(side[0]) * self.depth) / 2
            half_height = (abs(forward[1]) * width + abs(up[1]) * height + abs(side[1]) * self.depth) / 2
            projected_width = max(1, round(2 * half_width))
            projected_height = max(1, round(2 * half_height))
            left = floor(center_x - projected_width / 2 + .5)
            top = floor(center_y - projected_height / 2 + .5)
            right, bottom = left + projected_width, top + projected_height
            for pixel_y in range(max(0, top), min(canvas.height, bottom)):
                for pixel_x in range(max(0, left), min(canvas.width, right)):
                    canvas.SetPixel(pixel_x, pixel_y, red, green, blue)


class Water:
    def __init__(self, canvas):
        self.canvas = canvas
        self.brightness = 1.0
        self.change = True
        self.time = 0.0
        self.slant = 0.65
        self.bands = [
            dict(anchor=canvas.width * .20, width=7, speed=3.0,
                 fade_speed=.60, phase=0.0),
            dict(anchor=canvas.width * .52, width=10, speed=1.8,
                 fade_speed=.43, phase=pi),
            dict(anchor=canvas.width * .83, width=8, speed=4.5,
                 fade_speed=.77, phase=.6),
        ]

    def setBrightness(self, br):
        brightness = max(0.0, min(1.0, br))
        if self.brightness != brightness:
            self.brightness = brightness
            self.change = True

    def getBrightness(self):
        return self.brightness

    def changed(self):
        change = self.change
        self.change = False
        return change

    def update(self, dt):
        """Advance drifting bands and their independent fade cycles."""
        if dt > 0:
            self.time += dt
            self.change = True

    def render(self, canvas=None):
        """Draw blue water with soft, moving / shaped light bands."""
        canvas = canvas if canvas is not None else self.canvas
        margin = max(band['width'] for band in self.bands)
        span = canvas.width + ceil(canvas.height * self.slant) + 2 * margin
        # Wrap only after the band has fully left the diagonal drawing area.
        positions = [((band['anchor'] + self.time * band['speed'] + margin) % span - margin,
                      band['width'],
                      .5 + .5 * sin(self.time * band['fade_speed'] + band['phase']))
                     for band in self.bands]
        # The diagonal field is shared by every row, avoiding per-pixel trig.
        lights = []
        for diagonal in range(canvas.width + ceil(canvas.height * self.slant) + 1):
            light = sum(fade * max(0.0, 1 - abs(diagonal - center) / width) ** 2
                        for center, width, fade in positions)
            lights.append(min(1.0, light))
        for y in range(canvas.height):
            depth = 1 - y / max(canvas.height - 1, 1)
            offset = round(y * self.slant)
            for x in range(canvas.width):
                light = lights[x + offset]
                green = round(50 * light * depth * self.brightness)
                blue = round(min(255, (255 + 70 * light) * depth) * self.brightness)
                canvas.SetPixel(x, y, 0, green, blue)


def genSand(canvas, maxheight, roughnessX, roughnessY, color):
    """Generate sand pixels from the bottom, using an RGB color tuple.

    maxheight is capped at 10 pixels. roughnessX is the number of columns
    between height-change attempts (minimum 1). roughnessY is the percentage
    chance of a one-pixel rise or fall at each attempt (0-100; 0 is flat).
    Sand stays at least one pixel deep when maxheight is positive. Return pixels
    without drawing so the generated sand can be reused between frames.
    """
    maxheight = max(0, min(10, canvas.height, int(maxheight)))
    roughnessX = max(1, int(roughnessX))
    roughnessY = max(0.0, min(100.0, float(roughnessY)))
    sand = {}
    terrain = Random()
    height = maxheight
    for x in range(canvas.width):
        if maxheight > 1 and x > 0 and x % roughnessX == 0 and terrain.random() * 100 < roughnessY:
            height = terrain.choice([level for level in (height - 1, height + 1)
                                     if 1 <= level <= maxheight])
        for y in range(canvas.height - height, canvas.height):
            sand[x, y] = tuple(color)
    return sand


class Aquarium:
    def __init__(self, canvas, maxheight=3, roughnessX=4, roughnessY=50, color=(220, 180, 100)):
        self.canvas = canvas
        self.water = Water(canvas)
        self.fish = Fish(canvas)
        self.fish.id = 1
        self.fishes = [self.fish]
        self._nextFishId = 2
        self.shadowMode = False
        self.fish.x = (canvas.width - self.fish.width) // 2
        self.fish.y = (canvas.height - self.fish.height) // 2
        self.brightness = 1.0
        self.change = True
        self.genSand(maxheight, roughnessX, roughnessY, color)
        self.fish.startWandering(self._swimBounds())

    def _swimBounds(self, fish=None):
        fish = fish if fish is not None else self.fish
        # Reserve space for rotation, vertical follow-through, and the sand bed.
        radius = ceil(hypot(fish.width, fish.height, fish.depth) / 2)
        vertical_margin = radius + ceil(fish.swimAmplitude)
        sand_height = max(0, min(10, self.canvas.height, int(self.maxheight)))
        left = max(0, radius - fish.width / 2)
        top = max(0, vertical_margin - fish.height / 2)
        right = max(left, self.canvas.width - radius - fish.width / 2)
        bottom = max(top, self.canvas.height - sand_height - vertical_margin - fish.height / 2)
        return left, top, right, bottom

    def addFish(self):
        fish = Fish(self.canvas)
        fish.id = self._nextFishId
        self._nextFishId += 1
        left, top, right, bottom = self._swimBounds(fish)
        fish.x = max(left, min(right, (self.canvas.width - fish.width) / 2))
        fish.y = max(top, min(bottom, (self.canvas.height - fish.height) / 2))
        fish.setBrightness(self.brightness)
        fish.setShadowMode(self.shadowMode)
        fish.startWandering((left, top, right, bottom))
        self.fishes.append(fish)
        if self.fish is None:
            self.fish = fish
        self.change = True
        return fish

    def fishStats(self):
        return [dict(id=fish.id, seed=fish.seed, speed=round(fish.wanderSpeed, 1))
                for fish in self.fishes]

    def deleteFish(self, fish_id):
        fish = next((fish for fish in self.fishes if fish.id == fish_id), None)
        if fish is None:
            return False
        self.fishes.remove(fish)
        self.fish = self.fishes[0] if self.fishes else None
        self.change = True
        return True

    def setShadowMode(self, enabled):
        self.shadowMode = enabled
        for fish in self.fishes:
            fish.setShadowMode(enabled)

    def setBrightness(self, br):
        brightness = max(0.0, min(1.0, br))
        if self.brightness != brightness:
            self.brightness = brightness
            self.water.setBrightness(brightness)
            for fish in self.fishes:
                fish.setBrightness(brightness)
            self.change = True

    def getBrightness(self):
        return self.brightness

    def changed(self):
        change = self.change
        self.change = False
        water_changed = self.water.changed()
        fish_changed = any([fish.changed() for fish in self.fishes])
        return change or water_changed or fish_changed

    def update(self, dt):
        self.water.update(dt)
        for fish in self.fishes:
            fish.update(dt)

    def drawWater(self, canvas=None):
        self.water.render(canvas)

    def genSand(self, maxheight, roughnessX, roughnessY, color):
        self.maxheight = maxheight
        self.roughnessX = roughnessX
        self.roughnessY = roughnessY
        self.color = tuple(color)
        self.sand = genSand(self.canvas, maxheight, roughnessX, roughnessY, color)
        self.change = True

    def regenerateSand(self):
        self.genSand(self.maxheight, self.roughnessX, self.roughnessY, self.color)

    def regenerateFish(self, fish_id=None):
        fish = self.fish if fish_id is None else next((fish for fish in self.fishes if fish.id == fish_id), None)
        if fish is None:
            return False
        center_x = fish.x + fish.width / 2
        center_y = fish.y + fish.height / 2
        fish.buildFish()
        left, top, right, bottom = self._swimBounds(fish)
        fish.x = max(left, min(right, center_x - fish.width / 2))
        fish.y = max(top, min(bottom, center_y - fish.height / 2))
        fish.startWandering((left, top, right, bottom))
        self.change = True

    def render(self, canvas=None):
        canvas = canvas if canvas is not None else self.canvas
        self.drawWater(canvas)
        for (x, y), color in self.sand.items():
            red, green, blue = (round(channel * self.brightness) for channel in color)
            canvas.SetPixel(x, y, red, green, blue)
        for fish in self.fishes:
            fish.render(canvas)
