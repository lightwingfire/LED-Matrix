import json
import re
import unittest
from unittest.mock import Mock

from ser import ser
from tickertape import TickerTapeManager


class TickerToggleTests(unittest.TestCase):
    def test_api_and_page_keep_enabled_state(self):
        server = ser()
        client = server.app.test_client()
        self.assertEqual(client.get('/ticker-enabled').json, {'enabled': True})
        for enabled in (False, True):
            self.assertEqual(client.post('/ticker-enabled', json={'enabled': enabled}).json,
                             {'enabled': enabled})
            self.assertEqual(server.getTickerEnabled(), enabled)
            page = client.get('/').data
            state = json.loads(re.search(
                rb'<script id="initial-state" type="application/json">(.*?)</script>',
                page, re.S).group(1))
            self.assertEqual(state['tickerEnabled'], enabled)
        self.assertEqual(server.getTickerSpeed(), 18)
        self.assertEqual(server.getSlider(), 1)

    def test_api_rejects_non_boolean_values(self):
        server = ser()
        client = server.app.test_client()
        for value in (None, 0, 1, 'false', [], {}):
            self.assertEqual(client.post('/ticker-enabled', json={'enabled': value}).status_code, 400)
            self.assertTrue(server.getTickerEnabled())

    def test_hidden_ticker_stops_drawing_and_moving_then_resumes(self):
        # Avoid initializing a physical display or loading fonts.
        ticker = TickerTapeManager.__new__(TickerTapeManager)
        ticker.isHidden = False
        ticker.change = False
        ticker.brightness = 1
        ticker.scrollSpeed = 18
        words = Mock(x=128)
        words.getWidth.return_value = 300
        ticker.queque = [words]
        canvas = Mock()

        ticker.setEnabled(False)
        self.assertTrue(ticker.changed())  # Causes the display loop to clear old text.
        ticker.update(.1)
        ticker.render(canvas)
        words.update.assert_not_called()
        words.render.assert_not_called()
        self.assertEqual(words.x, 128)

        ticker.setBrightness(.4)
        ticker.setEnabled(True)
        self.assertTrue(ticker.changed())
        ticker.update(.1)
        ticker.render(canvas)
        words.update.assert_called_once_with(.1)
        words.render.assert_called_once_with(canvas)
        words.setBrightness.assert_called_once_with(.4)
        self.assertEqual(ticker.scrollSpeed, 18)
        self.assertEqual(ticker.getBrightness(), .4)


if __name__ == '__main__':
    unittest.main()
