import json
from PIL import Image
import boto3
import os
import logging

def lambda_handler(event, context):
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
    
    # clear tmp directory and file
    logger.info(f'Remove Tmp source image')
    os.remove(source_image_path)
    
    logger.info('Finish to extract thumbnail')

    return {
        'statusCode': 200,
        'body': json.dumps('Image processing completed!')
    }
