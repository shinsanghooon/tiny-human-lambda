import json
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import boto3
import os
import logging

def dms_to_decimal(gpsDMS, direction):
    degrees = int(gpsDMS[0]) 
    minutes = int(gpsDMS[1])
    seconds = float(gpsDMS[2])

    direction = direction.lower()
    multiplier = 1 if direction in ['n', 'e'] else -1

    decimal_degrees = degrees + (minutes / 60) + (seconds / 3600)
    decimal_degrees *= multiplier

    return decimal_degrees


def lambda_handler(event, context):
    
    print(event);
    
    logger = logging.getLogger(context.aws_request_id)
    logger.setLevel(logging.INFO)

    s3 = boto3.client('s3')

    # get source S3 bucket and path
    source_bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    logger.info(f'Read source image - {source_bucket}/{key}')
    
    # create tmp directory for lambda 
    temp_dir = '/tmp'
    os.makedirs(temp_dir, exist_ok=True)
    
    # download image from source bucket
    source_image_path = os.path.join(temp_dir, 'source_image.jpg')
    s3.download_file(source_bucket, key, source_image_path)
    
    image = Image.open(source_image_path)
    
    # crop and resize 
    minLength = min(image.height, image.width)
    xOffset = (image.width - minLength) / 2.0
    yOffset = (image.height - minLength) / 2.0
    
    logger.info('Crop image')
    cropped = image.crop((xOffset, yOffset, xOffset + minLength, yOffset + minLength))
    
    target_sizes = [300, 1000]
    for size in target_sizes:
        # resize target image 
        logger.info(f'Resize image to {size}')
        cropped_resized = cropped.resize((size, size), resample=Image.LANCZOS)
        
        # destination_bucket
        target_bucket = 'tiny-human-thumbnail-dev'  
        
        # destination_path
        file_name, file_extension = os.path.splitext(key)
        target_key = f'{file_name}_{size}{file_extension}'
        
        # temp_file_path
        target_image_path = os.path.join(temp_dir, 'target_image.jpg')
        
        # temp resized file save
        cropped_resized.save(target_image_path, quality=100)
        
        # upload to destionation_bucket
        logger.info(f'Start - Upload to {target_bucket}/{target_key}')
        s3.upload_file(target_image_path, target_bucket, target_key)
        logger.info(f'End - Upload to {target_bucket}/{target_key}')
    
        logger.info(f'Start - Remove {target_key}')    
        os.remove(target_image_path)
        logger.info(f'End - Remove  {target_key}')

    logger.info('Finish to extract thumbnail')
    
    
    # ----------------------------------------
    # put image's exif info to dynamoDB

    logger.info('Start to extract exif info')
    baby_id = None
    key_split = key.split('/')
    if(key_split[0] == 'baby'):
        baby_id = key_split[1]
    logger.info('Extract baby id from key')    

    exif_info = image._getexif()
    if (exif_info is None):
        item = {
                'baby_id': {'S': str(baby_id)},  
                'key_name': {'S': key},
                'original_created_at': {'S': str(None)}, 
                'gps_latitude': {'S': str(None)} ,
                'gps_longitude': {'S': str(None)},
                'gps_info': {'S': str(None)}
            }    
    else:    
        exif = {}
        for tag, value in exif_info.items():
            if (tag not in ['MakerNote', 'PrintImageMatching']):
                decoded = TAGS.get(tag, tag)
                exif[decoded] = value
        
        original_datetime = None 
        if 'DateTime' in exif.keys():
            original_datetime = exif['DateTime']
    
        gps = {}
        gps_latitude = None 
        gps_longitude = None 
        if 'GPSInfo' in exif.keys():
            logger.info("GPS Info exists")
            for key in exif['GPSInfo'].keys():
                decode = GPSTAGS.get(key,key)
                gps[decode] = exif['GPSInfo'][key]
    
            gps_latitude = dms_to_decimal(gps["GPSLatitude"], gps["GPSLatitudeRef"])
            gps_longitude = dms_to_decimal(gps["GPSLongitude"], gps["GPSLongitudeRef"]) 
        else: 
            logger.info("GPS Info doesn't exist")
            
        item = {
                'baby_id': {'S': str(baby_id)},  
                'key_name': {'S': key},
                'original_created_at': {'S': str(original_datetime)}, 
                'gps_latitude': {'S': str(gps_latitude)} ,
                'gps_longitude': {'S': str(gps_longitude)},
                'gps_info': {'S': str(gps)}
            }    

    dynamodb = boto3.client("dynamodb")
    table_name = 'image_exif_info_dev' 

    logger.info(f'Start - put data to dynamoDB({table_name})')
    try:
        # DynamoDB에 데이터 쓰기
        response = dynamodb.put_item(
            TableName=table_name,
            Item=item
        )
        logger.info(f"successs put data to dynabodb : {response}")
    except Exception as e:
        logger.info(f"fail put data to dynabodb: {str(e)}")
        raise e;
    logger.info(f'End - put data to dynamoDB({table_name})')

    logger.info('Finish to extract exif info')

    # clear tmp directory and file
    logger.info(f'Remove Tmp source image')
    os.remove(source_image_path)

    return {
        'statusCode': 200,
        'body': json.dumps('Image processing and Extract exif info completed!')
    }
