from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
import os
import exif 


# ------------------------------------------------
# put image exif data to dynamodbDB

event_key = "baby/3/profile/DSCF7000.JPG";

baby_id = None
key_split = event_key.split('/')
if(key_split[0] == 'baby'):
	baby_id = key_split[1]

image = Image.open("samples/9.jpg")

exif_info = image._getexif()

exif = {}
for tag, value in exif_info.items():
    decoded = TAGS.get(tag, tag)
    exif[decoded] = value
del exif['MakerNote']

original_datetime = None 
if 'DateTime' in exif.keys():
	original_datetime = exif['DateTime']

gps = {}
gps_latitude = None 
gps_logitude = None 
if 'GPSInfo' in exif.keys():
	print("Yes GPS Info exists")
	for key in exif['GPSInfo'].keys():
	    decode = GPSTAGS.get(key,key)
	    gps[decode] = exif['GPSInfo'][key]

	gps_latitude = dms_to_decimal(gps["GPSLatitude"], gps["GPSLatitudeRef"])
	gps_longitude = dms_to_decimal(gps["GPSLongitude"], gps["GPSLongitudeRef"]) 
else: 
	print("GPS Info doesn't exist")

dynamodb = boto3.client("dynamodb")

item = {
        'baby_id': {'S': str(baby_id)},  
        'original_created_at': {'S': str(original_datetime)}, 
        'gps_logitude': {'S': str(gps_latitude)} ,
        'gps_latitude': {'S': str(gps_longitude)},
        'gps_info': {'S': str(gps)},
        'exif_raw': {'S', str(exif)},
    }

table_name = 'image_exif_info_dev' 

try:
    # DynamoDB에 데이터 쓰기
    response = dynamodb.put_item(
        TableName=table_name,
        Item=item
    )
    print(f"데이터 쓰기 성공: {response}")
except Exception as e:
    print(f"데이터 쓰기 실패: {str(e)}")


# ----------------------------------------------------
# put image to s3 after crop and resize 

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


def dms_to_decimal(gpsDMS, direction):

    # 문자열로 입력된 도, 분, 초를 정수로 변환
    degrees = int(gpsDMS[0]) 
    minutes = int(gpsDMS[1])
    seconds = float(gpsDMS[2])

    # 방향 문자열을 소문자로 변환하여 N과 E인 경우 양수로, S와 W인 경우 음수로 설정
    direction = direction.lower()
    multiplier = 1 if direction in ['n', 'e'] else -1

    # 십진수 좌표 계산
    decimal_degrees = degrees + (minutes / 60) + (seconds / 3600)
    decimal_degrees *= multiplier

    return decimal_degrees
