try:
    from RGBMatrixEmulator import graphics
except:
    from rgbmatrix import graphics
from PIL import Image
# import numpy as np

class drawGraphic:

    def __init__(self,x,y,width,height,canvas):
        self.canvas = canvas
        self.sprite = Image.open("day/113.bmp")
        # self.sprite = self.sprite
        self.x = x
        self.y = y 
        self.width = width
        self.height = height
        self.br = 1

    def loadImage(self,filepath):
        self.sprite.close()
        self.sprite = Image.open(filepath)
    
    def setBrightness(self, br):
        self.br = br
    def toCanvas(self):
        if self.sprite is None:
            return
        im = list(self.sprite.getdata())
        ww = 0
        for h in range(self.height):
            for w in range(self.width):
                
                self.canvas.SetPixel(self.x + w,
                                     self.y + h,
                                     self.br * im[ww][0],
                                     self.br * im[ww][1],
                                     self.br * im[ww][2])
                # print(im[ww][0],im[ww][1],im[ww][2])
                ww = ww + 1
                # print(ww)

    
# r = drawGraphic(0,0,10,10,0)
# r.loadImage("day\\113.bmp")
# r.toCanvas()