import boto3
import os
from datetime import datetime, timedelta

# Configurações
log_files = ["/var/log/auth.log", "/var/log/syslog", "/var/log/daemon.log", "/var/log/messages", "/var/log/boot.log"]
output_dir = "./ecs_logs"

# Função para baixar logs de instâncias EC2
def download_logs_from_ec2(instance_id, log_files):
    ssm_client = boto3.client('ssm')
    ec2_client = boto3.client('ec2')
    
    # Obter informações da instância
    instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])
    cluster_name = instance_info['Reservations'][0]['Instances'][0]['Tags'].get('ClusterName', 'UnknownCluster')
    service_name = instance_info['Reservations'][0]['Instances'][0]['Tags'].get('ServiceName', 'UnknownService')

    for log_file in log_files:
        command = f"cat {log_file}"
        response = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'commands': [command]},
        )
        command_id = response['Command']['CommandId']
        output = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id,
        )
        if output['Status'] == 'Success':
            save_log(output['StandardOutputContent'], cluster_name, service_name, log_file)
        else:
            print(f"Falha ao obter o log {log_file} da instância {instance_id}")

# Função para salvar logs
def save_log(log_content, cluster_name, service_name, log_file):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{cluster_name}_{service_name}_{os.path.basename(log_file)}"
    with open(filename, 'w') as f:
        f.write(log_content)

# Listar clusters ECS
ecs_client = boto3.client('ecs')
clusters = ecs_client.list_clusters()['clusterArns']

for cluster_arn in clusters:
    cluster_name = cluster_arn.split('/')[-1]
    services = ecs_client.list_services(cluster=cluster_arn)['serviceArns']
    for service_arn in services:
        service_name = service_arn.split('/')[-1]
        tasks = ecs_client.list_tasks(cluster=cluster_arn, serviceName=service_name)['taskArns']
        for task_arn in tasks:
            task_info = ecs_client.describe_tasks(cluster=cluster_arn, tasks=[task_arn])['tasks'][0]
            container_instance_arn = task_info['containerInstanceArn']
            container_instance_info = ecs_client.describe_container_instances(cluster=cluster_arn, containerInstances=[container_instance_arn])
            instance_id = container_instance_info['containerInstances'][0]['ec2InstanceId']
            
            # Baixar logs da instância EC2
            download_logs_from_ec2(instance_id, log_files)
