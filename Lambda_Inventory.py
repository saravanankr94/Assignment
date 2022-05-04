from collections import defaultdict
import boto3
import csv
import time


def lambda_handler(event, context):
  
  # Assigning required variables
  servicetag = servicevalue = 'NA'
  value=['Data','Web','Processing']
  alert_instance=[]
  
  # Connect to EC2
  ec2 = boto3.resource('ec2',region_name='us-east-1')
  
  # Getting information on all running instances
  running_instances = ec2.instances.filter(Filters=[{
      'Name': 'instance-state-name',
      'Values': ['running']}])
  
  #Storing values of running instances in dictionary
  ec2info = defaultdict()
  for instance in running_instances:
      for tag in instance.tags:
          print (tag)
          if 'Name' in tag['Key']:
              name = tag['Value']
              continue
          if 'Service' in tag['Key']:
              servicetag = tag['Key']
              servicevalue = tag['Value']
      if (servicetag == 'NA' or servicevalue not in value):
         alert_instance.append(instance.id)
         print (alert_instance)
      
      ec2info[instance.id] = {
          'Name': name,
          'ServiceTag':servicetag,
          'ServiceValue':servicevalue,
          'Class': instance.instance_type,
          'AMI': instance.image.id,
          'Tags': instance.tags
          }
  
  #Outputting the requested values
  attributes = ['Name', 'ServiceTag', 'ServiceValue', 'Class', 'AMI', 'Tags']
  for instance_id, instance in ec2info.items():
      for key in attributes:
          print("{0}: {1}".format(key, instance[key]))
  
  #SNS Alert Function
  def raisealert(test="False"):
    if (test != "True"):
      print ("Sending Alert Mail via SNS")
      MY_SNS_TOPIC_ARN = 'arn:aws:sns:XXXX:XXXXXXXX:sns_mail'
      sns_client = boto3.client('sns')
      sns_client.publish(
          TopicArn = MY_SNS_TOPIC_ARN,
          Subject = 'Instance without proper tag and value',
          Message = str(alert_instance)
          )
    else:
       print ("Its a test event alerting disabled, below are the instance details without tag/value")
       print (alert_instance)
  
  #Checking for Test event, to avoid alerting      
  if (len(alert_instance) != 0):
    if ( event['Test'] != "True" ):
      raisealert()
    else:
      raisealert("True")
  
  #Gathering alerted instance ids for inventory in csv format
  fields = ['Alerted_Instances']
  rows = alert_instance
  with open('/tmp/inventory.csv', 'w') as f:
      write = csv.writer(f)
      write.writerow(fields)
      write.writerow(rows)
  
  with open('/tmp/inventory.csv', 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        print(row)
  
  #Uploading inventory file to S3 with time stamp for future reference      
  s3 = boto3.resource('s3')
  bucket = s3.Bucket('ec2-alerted-instances-inventory')
  timestr = time.strftime("%Y-%m-%d-%H:%M:%S")
  name= 'Inventory_'+timestr+'.csv'
  key = name
  bucket.upload_file('/tmp/inventory.csv', key)
