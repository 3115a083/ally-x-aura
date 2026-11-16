import unittest
from PIL import Image, ImageDraw
from allylight.sources import hue_game_color

class HueGamePaletteTests(unittest.TestCase):
    def test_eight_background_colors(self):
        # Sample inside each HSV interval, including red hue wraparound.
        import colorsys
        for hue,expected in [(178,(255,0,0)),(10,(255,50,0)),(28,(255,255,0)),
                             (47,(0,255,0)),(85,(0,255,255)),(115,(0,0,255)),
                             (142,(150,0,255)),(157,(255,0,255)),(0,(255,0,0))]:
            rgb=tuple(round(c*255) for c in colorsys.hsv_to_rgb(hue/180,1,1))
            self.assertEqual(hue_game_color(Image.new('RGB',(96,54),rgb)),expected)
    def test_black_white_and_small_ui_accents_are_not_background(self):
        for color in ('black','white'):
            image=Image.new('RGB',(96,54),color)
            ImageDraw.Draw(image).rectangle((0,0,4,4),fill='blue')
            self.assertIsNone(hue_game_color(image))
    def test_background_wins_over_black_geometry_and_other_colors(self):
        image=Image.new('RGB',(96,54),'blue');draw=ImageDraw.Draw(image)
        draw.rectangle((0,35,95,53),fill='black');draw.rectangle((0,0,20,30),fill='red')
        self.assertEqual(hue_game_color(image),(0,0,255))
