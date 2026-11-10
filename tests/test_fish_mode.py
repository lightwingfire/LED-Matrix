import ast
import asyncio
import json
from pathlib import Path
import re
import time
import unittest
from unittest.mock import AsyncMock, Mock

from ser import ser
from aquarium import Aquarium


class FishModeTests(unittest.TestCase):
    def test_mode_round_trip_preserves_settings(self):
        server = ser()
        client = server.app.test_client()
        client.post('/ticker-speed', json={'speed': 27})
        client.post('/ticker-enabled', json={'enabled': False})
        client.post('/', json={'out': 40})
        self.assertEqual(client.get('/fish-mode').json, {'enabled': False})
        for enabled in (True, False):
            self.assertEqual(client.post('/fish-mode', json={'enabled': enabled}).json,
                             {'enabled': enabled})
            self.assertEqual(server.getFishMode(), enabled)
            state = json.loads(re.search(
                rb'<script id="initial-state" type="application/json">(.*?)</script>',
                client.get('/').data, re.S).group(1))
            self.assertEqual(state['fishMode'], enabled)
        self.assertEqual(server.getTickerSpeed(), 27)
        self.assertFalse(server.getTickerEnabled())
        self.assertEqual(server.getSlider(), .4)

    def test_rejects_invalid_mode_values(self):
        server = ser()
        client = server.app.test_client()
        for value in (None, 0, 1, 'true', [], {}):
            self.assertEqual(client.post('/fish-mode', json={'enabled': value}).status_code, 400)
            self.assertFalse(server.getFishMode())

    def test_sand_requests_require_fish_mode_and_are_consumed_once(self):
        server = ser()
        client = server.app.test_client()
        self.assertEqual(client.post('/aquarium/sand', json={}).status_code, 409)
        self.assertFalse(server.consumeSandRequest())
        client.post('/fish-mode', json={'enabled': True})
        response = client.post('/aquarium/sand', json={})
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.json['queued'])
        self.assertTrue(server.consumeSandRequest())
        self.assertFalse(server.consumeSandRequest())
        self.assertEqual(client.get('/aquarium/sand').status_code, 405)

    def test_display_renders_aquarium_and_restores_elements(self):
        # Execute the real display loop without initializing hardware, a web server,
        # or the local credential loader at module import.
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'main.py').read_text())
        main_function = next(node for node in tree.body
                             if isinstance(node, ast.AsyncFunctionDef) and node.name == 'main')
        server = Mock()
        server.getFishMode.side_effect = [False, True, False]
        server.consumeSandRequest.return_value = True
        server.getSlider.return_value = .4
        clock, weather, ticker = Mock(), Mock(), Mock()
        clock.newHour.return_value = False
        for element in (clock, weather, ticker):
            element.changed.return_value = False
        weather.location = server.getWeatherLocation.return_value
        weather.refreshInfo = AsyncMock()
        ticker.refreshInfo = AsyncMock()
        aquariums = []
        def create_aquarium(canvas):
            aquarium = Aquarium(canvas)
            aquarium.regenerateSand = Mock(wraps=aquarium.regenerateSand)
            aquariums.append(aquarium)
            return aquarium
        namespace = dict(asyncio=asyncio, time=time, threading=Mock(), ser=lambda: server,
                         ClockFace=lambda *args: clock, weatherManager=lambda *args: weather,
                         TickerTapeManager=lambda *args: ticker, Aquarium=create_aquarium)
        exec(compile(ast.Module(body=[main_function], type_ignores=[]), 'main.py', 'exec'), namespace)
        canvas = Mock(width=128, height=32)
        aquarium_canvas = Mock(width=128, height=32)
        restored_canvas = Mock()
        matrix = Mock()

        class EndFrames(Exception):
            pass

        matrix.SwapOnVSync.side_effect = [aquarium_canvas, restored_canvas, EndFrames()]
        with self.assertRaises(EndFrames):
            asyncio.run(namespace['main'](matrix, canvas))
        canvas.Clear.assert_called_once()
        aquarium_canvas.Clear.assert_called_once()
        restored_canvas.Clear.assert_called_once()
        self.assertGreater(aquarium_canvas.SetPixel.call_count, 128 * 32)
        self.assertEqual(aquarium_canvas.SetPixel.call_args_list[0].args, (0, 0, 0, 0, 102))
        aquarium_canvas.SetPixel.assert_any_call(127, 31, 88, 72, 40)
        aquarium_canvas.SetPixel.assert_any_call(64, 16, 102, 64, 16)
        for element in (clock, weather, ticker):
            self.assertEqual(element.render.call_count, 2)
        self.assertEqual(clock.updateFace.call_count, 2)
        self.assertEqual(weather.update.call_count, 2)
        self.assertEqual(ticker.update.call_count, 2)
        server.consumeSandRequest.assert_called_once()
        aquariums[0].regenerateSand.assert_called_once()


if __name__ == '__main__':
    unittest.main()
