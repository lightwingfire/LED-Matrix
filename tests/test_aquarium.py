import unittest
from math import pi
from random import Random
from unittest.mock import patch

from aquarium import Aquarium, Water, genSand


class Canvas:
    def __init__(self, width=128, height=32):
        self.width = width
        self.height = height
        self.pixels = {}

    def SetPixel(self, x, y, red, green, blue):
        self.pixels[x, y] = (red, green, blue)


class AquariumTests(unittest.TestCase):
    def test_swimming_fish_stays_above_sand_and_inside_display(self):
        canvas = Canvas()
        aquarium = Aquarium(canvas)
        aquarium.fish._wanderRandom = Random(7)
        for _ in range(60):
            aquarium.update(.5)
            canvas.pixels.clear()
            aquarium.fish.render(canvas)
            self.assertTrue(canvas.pixels)
            self.assertTrue(all(0 <= x < canvas.width and 0 <= y < canvas.height - aquarium.maxheight
                                for x, y in canvas.pixels))

    def test_one_fish_is_centered_and_uses_aquarium_brightness(self):
        canvas = Canvas()
        aquarium = Aquarium(canvas)
        fish = aquarium.fish
        self.assertEqual(fish.x * 2 + fish.width, canvas.width)
        self.assertEqual(fish.y * 2 + fish.height, canvas.height)
        aquarium.setBrightness(.5)
        aquarium.render()
        self.assertEqual(fish.getBrightness(), .5)
        self.assertEqual(canvas.pixels[canvas.width // 2, canvas.height // 2],
                         tuple(round(channel * .5) for channel in fish.color))

    def test_water_bands_slant_up_to_the_right(self):
        canvas = Canvas()
        Water(canvas).render()
        upper_peak = max(range(40), key=lambda x: canvas.pixels[x, 4][1])
        lower_peak = max(range(40), key=lambda x: canvas.pixels[x, 16][1])
        self.assertGreater(upper_peak, lower_peak)
        self.assertGreater(canvas.pixels[upper_peak, 4][1], canvas.pixels[0, 4][1])

    def test_water_bands_move_right_at_different_speeds(self):
        canvas = Canvas()
        water = Water(canvas)
        def peaks():
            water.render()
            return tuple(max(region, key=lambda x: canvas.pixels[x, 0][1])
                         for region in (range(5, 45), range(45, 85)))
        first = peaks()
        water.update(1)
        later = peaks()
        self.assertGreater(later[0], first[0])
        self.assertGreater(later[1], first[1])
        self.assertNotEqual(later[0] - first[0], later[1] - first[1])
        water.update(1)
        next_peaks = peaks()
        self.assertGreater(next_peaks[0], later[0])
        self.assertGreater(next_peaks[1], later[1])

    def test_water_bands_fade_out_and_back_in(self):
        canvas = Canvas()
        water = Water(canvas)
        water.bands = [dict(water.bands[0], speed=0, fade_speed=1, phase=pi / 2)]
        water.render()
        brightest = max(pixel[1] for pixel in canvas.pixels.values())
        water.update(pi / 2)
        water.render()
        middle = max(pixel[1] for pixel in canvas.pixels.values())
        water.update(pi / 2)
        water.render()
        self.assertEqual(max(pixel[1] for pixel in canvas.pixels.values()), 0)
        water.update(pi)
        water.render()
        self.assertEqual(max(pixel[1] for pixel in canvas.pixels.values()), brightest)
        self.assertGreater(brightest, middle)
        self.assertGreater(middle, 0)

    def test_water_bands_reappear_after_leaving_right_edge(self):
        canvas = Canvas()
        water = Water(canvas)
        water.bands = [dict(water.bands[0], anchor=0, fade_speed=0, phase=pi / 2)]
        water.update(60)
        water.render()
        peak = max(range(canvas.width), key=lambda x: canvas.pixels[x, 0][1])
        self.assertGreater(peak, 0)
        self.assertLess(peak, canvas.width // 2)
        self.assertGreater(canvas.pixels[peak, 0][1], 0)

    def test_water_motion_depends_on_elapsed_time_and_respects_brightness(self):
        first, second = Canvas(), Canvas()
        once, many = Water(first), Water(second)
        once.update(2)
        for _ in range(20):
            many.update(.1)
        once.render()
        many.render()
        self.assertEqual(first.pixels, second.pixels)
        once.setBrightness(0)
        once.render()
        self.assertTrue(all(color == (0, 0, 0) for color in first.pixels.values()))

    def test_gradient_covers_canvas_and_reaches_blue_and_black(self):
        canvas = Canvas()
        Water(canvas).render()
        self.assertEqual(len(canvas.pixels), canvas.width * canvas.height)
        self.assertEqual(canvas.pixels[0, 0], (0, 0, 255))
        self.assertEqual(canvas.pixels[127, 31], (0, 0, 0))
        self.assertTrue(all(canvas.pixels[0, y][2] >= canvas.pixels[0, y + 1][2]
                            for y in range(canvas.height - 1)))

    def test_brightness_and_change_tracking(self):
        canvas = Canvas()
        aquarium = Aquarium(canvas)
        self.assertTrue(aquarium.changed())
        self.assertFalse(aquarium.changed())
        aquarium.update(.1)
        self.assertTrue(aquarium.changed())
        aquarium.setBrightness(.5)
        self.assertEqual(aquarium.water.getBrightness(), .5)
        self.assertTrue(aquarium.changed())
        aquarium.render()
        self.assertEqual(canvas.pixels[0, 0], (0, 0, 128))
        self.assertEqual(canvas.pixels[0, 31], (110, 90, 50))
        aquarium.setBrightness(.5)
        self.assertFalse(aquarium.changed())
        aquarium.setBrightness(0)
        aquarium.render()
        self.assertTrue(all(pixel == (0, 0, 0) for pixel in canvas.pixels.values()))

    def test_render_uses_current_frame_buffer(self):
        original, current = Canvas(), Canvas()
        Aquarium(original).render(current)
        self.assertFalse(original.pixels)
        self.assertEqual(len(current.pixels), current.width * current.height)

    def test_single_row_canvas(self):
        canvas = Canvas(width=2, height=1)
        Water(canvas).render()
        self.assertEqual(len(canvas.pixels), 2)
        self.assertTrue(all(red == 0 and 0 <= green <= 50 and blue == 255
                            for red, green, blue in canvas.pixels.values()))

    def test_flat_sand_fills_bottom_rows_with_selected_color(self):
        canvas = Canvas()
        canvas.pixels = genSand(canvas, 4, 4, 0, (220, 180, 100))
        self.assertEqual(len(canvas.pixels), canvas.width * 4)
        self.assertEqual({y for x, y in canvas.pixels}, {28, 29, 30, 31})
        self.assertEqual(set(canvas.pixels.values()), {(220, 180, 100)})

    def test_sand_roughness_is_bounded(self):
        first = Canvas()
        first.pixels = genSand(first, 8, 3, 100, (220, 180, 100))
        heights = [sum((x, y) in first.pixels for y in range(first.height))
                   for x in range(first.width)]
        self.assertGreater(len(set(heights)), 1)
        self.assertTrue(all(1 <= height <= 8 for height in heights))
        self.assertTrue(all(abs(right - left) <= 1
                            for left, right in zip(heights, heights[1:])))

    def test_neighboring_sand_columns_never_jump_more_than_one_pixel(self):
        for roughnessX, roughnessY in ((1, 100), (2, 50), (3, 100), (10, 25), (100, 100)):
            with self.subTest(roughnessX=roughnessX, roughnessY=roughnessY):
                canvas = Canvas(width=512)
                sand = genSand(canvas, 10, roughnessX, roughnessY, (220, 180, 100))
                heights = [sum((x, y) in sand for y in range(canvas.height))
                           for x in range(canvas.width)]
                self.assertTrue(all(abs(right - left) <= 1
                                    for left, right in zip(heights, heights[1:])))

    def test_roughness_follows_left_column_instead_of_fixed_height_band(self):
        canvas = Canvas()
        with patch('aquarium.Random', return_value=Random(0)):
            sand = genSand(canvas, 8, 1, 100, (220, 180, 100))
        heights = [sum((x, y) in sand for y in range(canvas.height))
                   for x in range(canvas.width)]
        self.assertEqual(heights[0], 8)
        self.assertTrue(all(1 <= height <= 8 for height in heights))
        self.assertTrue(all(abs(right - left) <= 1
                            for left, right in zip(heights, heights[1:])))
        self.assertLess(min(heights), 7)

    def test_sand_height_is_capped_by_ten_and_canvas_height(self):
        for height in (32, 3):
            canvas = Canvas(height=height)
            canvas.pixels = genSand(canvas, 20, 4, 0, (220, 180, 100))
            self.assertEqual(len(canvas.pixels), canvas.width * min(10, height))
        canvas = Canvas()
        canvas.pixels = genSand(canvas, 0, 3, 100, (220, 180, 100))
        self.assertFalse(canvas.pixels)

    def test_sand_uses_component_brightness_and_current_canvas(self):
        original, current = Canvas(), Canvas()
        aquarium = Aquarium(original, maxheight=4, roughnessY=0, color=(220, 180, 100))
        aquarium.setBrightness(.5)
        aquarium.render(current)
        self.assertFalse(original.pixels)
        self.assertTrue(all(current.pixels[x, y] == (110, 90, 50)
                            for x in range(current.width) for y in range(28, 32)))

    def test_initialization_generates_sand_without_drawing_and_frames_reuse_it(self):
        canvas = Canvas()
        aquarium = Aquarium(canvas)
        self.assertTrue(aquarium.sand)
        self.assertFalse(canvas.pixels)
        sand = aquarium.sand
        aquarium.render()
        first_frame = canvas.pixels.copy()
        aquarium.update(.1)
        aquarium.render()
        self.assertNotEqual(canvas.pixels, first_frame)
        self.assertTrue(all(canvas.pixels[position] == color
                            for position, color in sand.items()))
        aquarium.setBrightness(.5)
        aquarium.render()
        self.assertIs(aquarium.sand, sand)
        self.assertEqual(set(aquarium.sand), set(sand))

    def test_regeneration_changes_sand_and_preserves_settings(self):
        with patch('aquarium.Random', side_effect=[Random(0), Random(1)]):
            aquarium = Aquarium(Canvas(), maxheight=6, roughnessX=4, roughnessY=50, color=(220, 180, 100))
            previous = aquarium.sand
            aquarium.setBrightness(.5)
            aquarium.changed()
            aquarium.regenerateSand()
        self.assertNotEqual(aquarium.sand, previous)
        self.assertEqual((aquarium.maxheight, aquarium.roughnessX, aquarium.roughnessY, aquarium.color),
                         (6, 4, 50, (220, 180, 100)))
        self.assertEqual(aquarium.getBrightness(), .5)
        self.assertTrue(aquarium.changed())

    def test_horizontal_roughness_spaces_height_changes(self):
        canvas = Canvas()
        sand = genSand(canvas, 8, 4, 100, (220, 180, 100))
        heights = [sum((x, y) in sand for y in range(canvas.height))
                   for x in range(canvas.width)]
        for x in range(1, canvas.width):
            self.assertEqual(abs(heights[x] - heights[x - 1]), 1 if x % 4 == 0 else 0)

    def test_vertical_roughness_controls_change_frequency(self):
        canvas = Canvas(width=512)
        changes = []
        for roughnessY in (0, 25, 100):
            with patch('aquarium.Random', return_value=Random(0)):
                sand = genSand(canvas, 8, 1, roughnessY, (220, 180, 100))
            heights = [sum((x, y) in sand for y in range(canvas.height))
                       for x in range(canvas.width)]
            changes.append(sum(left != right for left, right in zip(heights, heights[1:])))
        self.assertEqual(changes[0], 0)
        self.assertGreater(changes[1], 0)
        self.assertLess(changes[1], changes[2])
        self.assertEqual(changes[2], canvas.width - 1)


if __name__ == '__main__':
    unittest.main()
