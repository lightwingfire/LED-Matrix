import unittest
from math import pi
from random import Random

from aquarium import Fish


class Canvas:
    width = 128
    height = 32

    def __init__(self):
        self.pixels = {}

    def SetPixel(self, x, y, red, green, blue):
        self.pixels[x, y] = red, green, blue


class FishTests(unittest.TestCase):
    def test_random_swimming_moves_turns_and_stays_inside_bounds(self):
        fish = Fish(Canvas(), x=58, y=12)
        fish.startWandering((2, 7, 114, 14))
        fish._wanderRandom = Random(7)
        positions, directions, targets = [], [], set()
        order = fish.drawOrder
        for _ in range(1200):
            previous = fish.x, fish.y
            fish.update(1 / 30)
            self.assertTrue(2 <= fish.x <= 114 and 7 <= fish.y <= 14)
            self.assertLessEqual(((fish.x - previous[0]) ** 2 +
                                  (fish.y - previous[1]) ** 2) ** .5, 10 / 30 + 1e-9)
            positions.append((fish.x, fish.y))
            directions.append(fish.direction[0])
            targets.add(fish.wanderTarget)
        self.assertGreater(max(x for x, y in positions) - min(x for x, y in positions), 30)
        self.assertGreater(max(y for x, y in positions) - min(y for x, y in positions), 1)
        self.assertGreater(len(targets), 2)
        self.assertLess(min(directions), -.9)
        self.assertGreater(max(directions), .9)
        self.assertEqual(fish.drawOrder, order)

    def test_random_swimming_is_consistent_at_different_frame_rates(self):
        fish = [Fish(Canvas(), x=58, y=12) for _ in range(2)]
        for instance, frame_rate in zip(fish, (30, 60)):
            instance.startWandering((2, 7, 114, 14))
            instance._wanderRandom = Random(4)
            for _ in range(frame_rate * 3):
                instance.update(1 / frame_rate)
        self.assertAlmostEqual(fish[0].x, fish[1].x, delta=.5)
        self.assertAlmostEqual(fish[0].y, fish[1].y, delta=.5)

    def test_left_facing_fish_mirrors_geometry_without_changing_stack(self):
        canvas = Canvas()
        fish = Fish(canvas, x=50, y=12)
        fish.render()
        original = canvas.pixels.copy()
        order = fish.drawOrder
        canvas.pixels.clear()
        fish.setDirection((-5, 0, 0))
        fish.render()
        mirrored = {(2 * fish.x + fish.width - 1 - x, y): color
                    for (x, y), color in original.items()}
        self.assertEqual(canvas.pixels, mirrored)
        self.assertEqual(fish.drawOrder, order)

    def test_end_on_projection_keeps_head_on_top_of_fixed_stack(self):
        for direction in ((0, 0, 1), (0, 0, -1)):
            with self.subTest(direction=direction):
                canvas = Canvas()
                fish = Fish(canvas, x=50, y=12)
                fish.setDirection(direction)
                fish.render()
                self.assertEqual(len({x for x, y in canvas.pixels}), fish.depth)
                self.assertEqual(canvas.pixels[56, 16], fish.colors['head'])

    def test_turnaround_passes_through_3d_heading(self):
        fish = Fish(Canvas(), x=50, y=12)
        fish.swimAmplitude = 0
        fish.turnTo((-1, 0, 0))
        self.assertEqual(fish.direction, (1, 0, 0))
        headings = []
        for _ in range(240):
            fish.update(1 / 30)
            headings.append(fish.direction)
        self.assertTrue(any(abs(x) < .1 and z > .99 for x, y, z in headings))
        self.assertAlmostEqual(fish.direction[0], -1, places=4)
        self.assertAlmostEqual(fish.direction[2], 0, places=4)

    def test_turn_eases_in_and_out_without_overshooting(self):
        fish = Fish(Canvas())
        fish.turnTo((-1, 0, 0))
        angles = [fish._yaw]
        for _ in range(160):
            fish.update(.05)
            angles.append(fish._yaw)
        steps = [right - left for left, right in zip(angles, angles[1:])]
        self.assertGreater(steps[5], steps[0])
        self.assertLess(steps[-1], steps[20])
        self.assertTrue(all(0 <= angle <= pi for angle in angles))

    def test_parts_turn_at_different_rates_from_head_to_tail(self):
        fish = Fish(Canvas())
        fish.turnTo((-1, -.2, 0))
        fish.update(1)
        names = (*fish.followOrder, 'tailfin_top')
        yaw = [fish.partAngles[name][0] for name in names]
        self.assertTrue(all(front > back for front, back in zip(yaw, yaw[1:])))
        self.assertEqual(fish.partAngles['tailfin_top'], fish.partAngles['tailfin_bottom'])
        fish.update(12)
        self.assertTrue(all(abs(fish.partAngles[name][0] - pi) < .001 for name in names))

    def test_parts_remain_connected_during_eased_turns(self):
        canvas = Canvas()
        fish = Fish(canvas, x=50, y=12)
        original_order = fish.drawOrder
        for frame in range(240):
            if frame % 80 == 0:
                fish.turnTo(((-1 if frame != 80 else 1), -.2, 0))
            fish.update(1 / 30)
            canvas.pixels.clear()
            fish.render()
            remaining = set(canvas.pixels)
            pending = [remaining.pop()]
            while pending:
                x, y = pending.pop()
                for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if point in remaining:
                        remaining.remove(point)
                        pending.append(point)
            self.assertFalse(remaining, 'Disconnected fish at frame %s' % frame)
            self.assertEqual(fish.drawOrder, original_order)

    def test_invalid_direction_vectors_are_rejected(self):
        fish = Fish(Canvas())
        for direction in ((0, 0, 0), (float('nan'), 0, 1), (float('inf'), 1, 0)):
            with self.subTest(direction=direction), self.assertRaises(ValueError):
                fish.turnTo(direction)

    def test_vertical_turn_reaches_parts_from_head_to_tailfin(self):
        fish = Fish(Canvas())
        fish.update(.06)
        self.assertLess(fish.partOffsets['head'], 0)
        self.assertTrue(all(offset == 0 for name, offset in fish.partOffsets.items()
                            if name != 'head'))
        fish.update(.48)
        offsets = [fish.partOffsets[name] for name in fish.followOrder]
        self.assertTrue(all(front < back for front, back in zip(offsets, offsets[1:])))
        self.assertEqual(fish.partOffsets['tailfin_top'], 0)
        fish.update(.12)
        self.assertLess(fish.partOffsets['tailfin_top'], 0)
        self.assertEqual(fish.partOffsets['tailfin_top'], fish.partOffsets['tailfin_bottom'])

    def test_fish_motion_uses_elapsed_time(self):
        first, second = Fish(Canvas()), Fish(Canvas())
        first.update(2)
        for _ in range(20):
            second.update(.1)
        for name in first.partOffsets:
            self.assertAlmostEqual(first.partOffsets[name], second.partOffsets[name])

    def test_parts_stay_connected_through_up_and_down_motion(self):
        canvas = Canvas()
        fish = Fish(canvas, x=50, y=12)
        for frame in range(40):
            with self.subTest(frame=frame):
                fish.update(.25)
                canvas.pixels.clear()
                fish.render()
                remaining = set(canvas.pixels)
                pending = [remaining.pop()]
                while pending:
                    x, y = pending.pop()
                    for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if point in remaining:
                            remaining.remove(point)
                            pending.append(point)
                self.assertFalse(remaining)

    def test_parts_overlap_and_form_one_connected_fish(self):
        canvas = Canvas()
        fish = Fish(canvas)
        self.assertEqual(len(fish.tailfin), 2)
        self.assertTrue(all(width == height for x, y, width, height in fish.tailfin))
        self.assertEqual(len(fish.body), 3)
        parts = [set((x + dx, y + dy) for dx in range(width) for dy in range(height))
                 for x, y, width, height in (*fish.tailfin, fish.tail, *fish.body, fish.head)]
        self.assertEqual(len(parts), 7)
        self.assertTrue(all(any(part & other for other in parts if other is not part)
                            for part in parts))
        fish.render()
        remaining = set(canvas.pixels)
        pending = [remaining.pop()]
        while pending:
            x, y = pending.pop()
            for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if point in remaining:
                    remaining.remove(point)
                    pending.append(point)
        self.assertFalse(remaining)

    def test_position_color_brightness_and_current_buffer(self):
        original, current = Canvas(), Canvas()
        fish = Fish(original, x=10, y=5, color=(200, 100, 40))
        fish.setBrightness(.5)
        fish.render(current)
        self.assertFalse(original.pixels)
        self.assertEqual(set(current.pixels.values()),
                         {tuple(round(channel * .5) for channel in color)
                          for color in fish.colors.values()})
        self.assertEqual(min(x for x, y in current.pixels), 10)
        self.assertEqual(min(y for x, y in current.pixels), 5)
        self.assertLess(max(x for x, y in current.pixels), 10 + fish.width)
        self.assertLess(max(y for x, y in current.pixels), 5 + fish.height)

    def test_all_seven_parts_have_visible_distinct_colors(self):
        canvas = Canvas()
        fish = Fish(canvas)
        fish.render()
        self.assertEqual(len(set(fish.colors.values())), 7)
        self.assertEqual(set(canvas.pixels.values()), set(fish.colors.values()))

    def test_fish_is_clipped_at_canvas_edges(self):
        for x, y in ((-5, -3), (120, 28), (200, 100)):
            with self.subTest(x=x, y=y):
                canvas = Canvas()
                Fish(canvas, x, y).render()
                self.assertTrue(all(0 <= px < canvas.width and 0 <= py < canvas.height
                                    for px, py in canvas.pixels))


if __name__ == '__main__':
    unittest.main()
