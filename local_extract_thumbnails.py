from PIL import Image
from deepface import Deepface
import os

image = Image.open("samples/6.jpg")

sourceHeight = image.height
sourceWidth = image.width
printSize(image)

minLength = min([image.height, image.width])
print(f'MinLength: {minLength}')

xOffset = (sourceWidth - minLength) / 2.0
yOffset = (sourceHeight - minLength) / 2.0
croped = image.crop((xOffset, 
	yOffset, 
	xOffset + minLength,
	yOffset + minLength))
printSize(croped)
croped.show()

target_size = [300, 1000];

for size in target_size:
	cropped_resized = croped.resize((target_size, target_size), resample=Image.LANCZOS)
	printSize(cropped_resized)

	extension = 'jpg'
	quality = 100
	filename = f'samples/crop_and_resize/sample_{targetSize}_{quality}.{extension}'
	cropped_resized.save(filename, quality=quality)
	file_size = os.path.getsize(filename)
	print(file_size/1024/1024)


def printSize(image):
	print(f'Height: {image.height}, Width: {image.width}')


