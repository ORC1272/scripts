import boto3
import requests
from datetime import datetime, timedelta
import base64

# Configurações
region_name = 'us-east-1'  # Substitua pela sua região
days_to_check = 3
splunk_url = 'https://splunk-instance:8089'  # Substitua pelo seu Splunk URL
splunk_user = 'your_splunk_username'  # Substitua pelo seu nome de usuário do Splunk
splunk_password = 'your_splunk_password'  # Substitua pela sua senha do Splunk

# Inicializar clientes boto3
ecs_client = boto3.client('ecs', region_name=region_name)

# Função para verificar movimentações nos logs do Splunk
def check_logs_splunk(service_name):
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_to_check)

    search_query = f'search index=* sourcetype="{service_name}" earliest={start_time.isoformat()} latest={end_time.isoformat()}'
    
    # Codificar as credenciais para a autenticação básica
    auth = base64.b64encode(f'{splunk_user}:{splunk_password}'.encode()).decode()

    headers = {
        'Authorization': f'Basic {auth}'
    }

    data = {
        'search': search_query,
        'output_mode': 'json'
    }

    response = requests.post(f'{splunk_url}/services/search/jobs', headers=headers, data=data)
    if response.status_code == 201:
        job_id = response.json()['sid']
        result_url = f'{splunk_url}/services/search/jobs/{job_id}/results?output_mode=json'
        
        response = requests.get(result_url, headers=headers)
        if response.status_code == 200:
            results = response.json()['results']
            if results:
                return True
    return False

# Listar clusters ECS
clusters = ecs_client.list_clusters()['clusterArns']

for cluster_arn in clusters:
    cluster_name = cluster_arn.split('/')[-1]
    services = ecs_client.list_services(cluster=cluster_arn)['serviceArns']
    
    for service_arn in services:
        service_name = service_arn.split('/')[-1]
        
        try:
            has_activity = check_logs_splunk(service_name)
            if has_activity:
                print(f"Serviço '{service_name}' no cluster '{cluster_name}' teve movimentações nos últimos {days_to_check} dias.")
            else:
                print(f"Serviço '{service_name}' no cluster '{cluster_name}' NÃO teve movimentações nos últimos {days_to_check} dias.")
        except Exception as e:
            print(f"Erro ao verificar logs do serviço '{service_name}' no cluster '{cluster_name}': {str(e)}")

print("Verificação concluída.")
