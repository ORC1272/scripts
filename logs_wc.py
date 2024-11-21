import boto3
from datetime import datetime, timedelta

# Configurações
region_name = 'us-east-1'  # Substitua pela sua região
days_to_check = 3

# Inicializar clientes boto3
ecs_client = boto3.client('ecs', region_name=region_name)
logs_client = boto3.client('logs', region_name=region_name)

# Função para verificar movimentações nos logs do CloudWatch
def check_logs(log_group_name):
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days_to_check)).timestamp() * 1000)

    query = f'''
        fields @timestamp, @message
        | sort @timestamp desc
        | limit 1
    '''

    response = logs_client.start_query(
        logGroupName=log_group_name,
        startTime=start_time,
        endTime=end_time,
        queryString=query
    )

    query_id = response['queryId']
    result = logs_client.get_query_results(queryId=query_id)

    if result['status'] == 'Complete' and len(result['results']) > 0:
        return True
    return False

# Listar clusters ECS
clusters = ecs_client.list_clusters()['clusterArns']

for cluster_arn in clusters:
    cluster_name = cluster_arn.split('/')[-1]
    services = ecs_client.list_services(cluster=cluster_arn)['serviceArns']
    
    for service_arn in services:
        service_name = service_arn.split('/')[-1]
        log_group_name = f'/ecs/{service_name}'
        
        try:
            has_activity = check_logs(log_group_name)
            if has_activity:
                print(f"Serviço '{service_name}' no cluster '{cluster_name}' teve movimentações nos últimos {days_to_check} dias.")
            else:
                print(f"Serviço '{service_name}' no cluster '{cluster_name}' NÃO teve movimentações nos últimos {days_to_check} dias.")
        except logs_client.exceptions.ResourceNotFoundException:
            print(f"Log group '{log_group_name}' não encontrado. O serviço '{service_name}' no cluster '{cluster_name}' pode não ter registros no CloudWatch Logs.")

print("Verificação concluída.")
