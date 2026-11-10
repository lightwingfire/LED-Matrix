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
    def test_delete_fish_api_queues_only_known_fish_in_fish_mode(self):
        server = ser()
        client = server.app.test_client()
        rows = [dict(id=1, seed=123, speed=8), dict(id=2, seed=456, speed=7)]
        server.setFishStats(rows)
        self.assertEqual(client.delete('/aquarium/fishes/2').status_code, 409)
        client.post('/fish-mode', json={'enabled': True})
        self.assertEqual(client.delete('/aquarium/fishes/999').status_code, 404)
        self.assertEqual(client.delete('/aquarium/fishes/2').status_code, 202)
        self.assertEqual(server.consumeFishCommands(), [dict(action='delete', id=2)])
        self.assertEqual(server.consumeFishCommands(), [])
        server.setFishStats(rows[:1])
        self.assertEqual(client.get('/aquarium/fishes').json['fishes'], rows[:1])
        self.assertEqual(client.delete('/aquarium/fishes/2').status_code, 404)

    def test_fish_table_lists_stats_and_queues_individual_actions(self):
        server = ser()
        client = server.app.test_client()
        rows = [dict(id=1, seed=123, speed=8.1), dict(id=2, seed=456, speed=6.5)]
        server.setFishStats(rows)
        response = client.get('/aquarium/fishes')
        self.assertEqual(response.json, {'fishes': rows})
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(client.post('/aquarium/fishes', json={}).status_code, 409)
        self.assertEqual(client.post('/aquarium/fishes/1/regenerate', json={}).status_code, 409)
        client.post('/fish-mode', json={'enabled': True})
        self.assertEqual(client.post('/aquarium/fishes', json={}).status_code, 202)
        self.assertEqual(client.post('/aquarium/fishes/2/regenerate', json={}).status_code, 202)
        self.assertEqual(client.post('/aquarium/fishes/999/regenerate', json={}).status_code, 404)
        self.assertEqual(server.consumeFishCommands(), [dict(action='add'), dict(action='regenerate', id=2)])
        self.assertEqual(server.consumeFishCommands(), [])
        state = json.loads(re.search(
            rb'<script id="initial-state" type="application/json">(.*?)</script>',
            client.get('/').data, re.S).group(1))
        self.assertEqual(state['fishes'], rows)

    def test_shadow_mode_api_validates_and_initializes_page_state(self):
        server = ser()
        client = server.app.test_client()
        self.assertEqual(client.get('/aquarium/shadow').json, {'enabled': False})
        self.assertEqual(client.post('/aquarium/shadow', json={'enabled': True}).json,
                         {'enabled': True})
        self.assertTrue(server.getShadowMode())
        state = json.loads(re.search(
            rb'<script id="initial-state" type="application/json">(.*?)</script>',
            client.get('/').data, re.S).group(1))
        self.assertTrue(state['shadowMode'])
        for invalid in (None, 1, 'true', [], {}):
            self.assertEqual(client.post('/aquarium/shadow', json={'enabled': invalid}).status_code, 400)
            self.assertTrue(server.getShadowMode())
        self.assertFalse(client.post('/aquarium/shadow', json={'enabled': False}).json['enabled'])

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

    def test_fish_requests_require_fish_mode_and_are_consumed_once(self):
        server = ser()
        client = server.app.test_client()
        self.assertEqual(client.post('/aquarium/fish', json={}).status_code, 409)
        self.assertFalse(server.consumeFishRequest())
        client.post('/fish-mode', json={'enabled': True})
        response = client.post('/aquarium/fish', json={})
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.json['queued'])
        self.assertTrue(server.consumeFishRequest())
        self.assertFalse(server.consumeFishRequest())
        self.assertEqual(client.get('/aquarium/fish').status_code, 405)

    def test_display_renders_aquarium_and_restores_elements(self):
        # Execute the real display loop without initializing hardware, a web server,
        # or the local credential loader at module import.
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'main.py').read_text())
        main_function = next(node for node in tree.body
                             if isinstance(node, ast.AsyncFunctionDef) and node.name == 'main')
        server = Mock()
        server.getFishMode.side_effect = [False, True, False]
        server.consumeSandRequest.return_value = True
        server.consumeFishRequest.return_value = True
        server.consumeFishCommands.return_value = [dict(action='add'), dict(action='add'),
                                                   dict(action='regenerate', id=2), dict(action='delete', id=3)]
        server.getShadowMode.return_value = False
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
            aquarium.regenerateFish = Mock(wraps=aquarium.regenerateFish)
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
        self.assertTrue(any(call.args[2:] in
                            {tuple(round(channel * .4) for channel in color)
                             for color in aquariums[0].fish.colors.values()}
                            for call in aquarium_canvas.SetPixel.call_args_list))
        for element in (clock, weather, ticker):
            self.assertEqual(element.render.call_count, 2)
        self.assertEqual(clock.updateFace.call_count, 2)
        self.assertEqual(weather.update.call_count, 2)
        self.assertEqual(ticker.update.call_count, 2)
        server.consumeSandRequest.assert_called_once()
        aquariums[0].regenerateSand.assert_called_once()
        server.consumeFishRequest.assert_called_once()
        self.assertEqual(aquariums[0].regenerateFish.call_count, 2)
        aquariums[0].regenerateFish.assert_any_call(2)
        self.assertEqual(len(aquariums[0].fishes), 2)


if __name__ == '__main__':
    unittest.main()
