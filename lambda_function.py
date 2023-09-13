import json
from PIL import Image
import boto3
import os
from urllib.parse import unquote_plus
import logging


def lambda_handler(event, context):
    
    print(event);
    
    logger = logging.getLogger(context.aws_request_id)
    logger.setLevel(logging.INFO)

    logger.info(f'Start to extract thumbnail')
    s3 = boto3.client('s3')

    # get source S3 bucket and path
    source_bucket = event['Records'][0]['s3']['bucket']['name']
    keyname = unquote_plus(event['Records'][0]['s3']['object']['key'])
    key_split = keyname.split('.')
    extension = key_split[-1]
    
    response = s3.head_object(Bucket='tiny-human-dev', Key=keyname)
    content_type = response['ContentType']
    logger.info(f'\tContent type - {content_type}')

    logger.info(f'\tRead source file - {source_bucket}/{keyname}')
    
    # create tmp directory for lambda 
    temp_dir = '/tmp'
    os.makedirs(temp_dir, exist_ok=True)
    
    # download image from source bucket
    source_image_path = os.path.join(temp_dir, f'source_image.{extension}')
    s3.download_file(source_bucket, keyname, source_image_path)
    
    
    tmp_thumbnail = '/tmp/video_thumnail.jpg'
    
    if(content_type.startswith('image')):
        image = Image.open(source_image_path)    
    elif(content_type.startswith('video')):
        cap = cv2.VideoCapture(source_image_path)
        ret, frame= cap.read()
        cv2.imwrite(tmp_thumbnail, frame)
        image = Image.open(tmp_thumbnail)
    else:
        raise Exception("지원되지 않는 파일 형식입니다.")
    

    # crop and resize 
    minLength = min(image.height, image.width)
    xOffset = (image.width - minLength) / 2.0
    yOffset = (image.height - minLength) / 2.0
    
    logger.info('\tCrop image')
    cropped = image.crop((xOffset, yOffset, xOffset + minLength, yOffset + minLength))
    
    target_sizes = [300, 1000]
    for size in target_sizes:
        # resize target image 
        logger.info(f'\t\tResize image to {size}')
        cropped_resized = cropped.resize((size, size), resample=Image.LANCZOS)
        
        # destination_bucket
        target_bucket = os.environ['thumbnail_bucket']
        
        # destination_path
        file_name, file_extension = os.path.splitext(keyname)
        target_key = f'{file_name}_{size}{file_extension}'
        
        # temp_file_path
        target_image_path = os.path.join(temp_dir, f'target_image.{extension}')
        
        # temp resized file save
        cropped_resized.save(target_image_path, quality=100)
        
        # upload to destionation_bucket
        logger.info(f'\t\tUpload to {target_bucket}/{target_key}')
        s3.upload_file(target_image_path, target_bucket, target_key)
    
        logger.info(f'\t\tRemove tmp target image {target_key}')    
        os.remove(target_image_path)

    # clear tmp directory and file
    logger.info(f'\tRemove tmp source image')
    os.remove(source_image_path)
    
    if(content_type=='video'):
        logger.info(f'\tRemove tmp thumbnail image')
        os.remove(tmp_thumbnail)
    
    logger.info('Finish to extract thumbnail')


    return {
        'statusCode': 200,
        'body': json.dumps('Image processing and Extract exif info completed!')
    }
