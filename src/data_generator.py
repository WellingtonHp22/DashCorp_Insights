"""
Módulo para gerar dados fictícios usando a biblioteca Faker
"""

from faker import Faker
import random

def gerar_empresas(quantidade=20):
    """
    Gera dados fictícios de empresas
    
    Args:
        quantidade (int): Quantidade de empresas a serem geradas
        
    Returns:
        list: Lista de dicionários com dados de empresas
    """
    faker = Faker()
    empresas = []

    for _ in range(quantidade):
        empresa = {
            "nome_empresa": faker.company(),
            "setor": random.choice(['Tecnologia', 'Saúde', 'Finanças', 'Educação', 'RH']),
            "receita_anual": round(random.uniform(1000000, 1000000000), 2),
            "numero_funcionarios": random.randint(10, 500),
            "pais": faker.country(),
            "data_fundacao": faker.date_between(start_date='-50y', end_date='today').strftime('%Y-%m-%d')
        }
        empresas.append(empresa)
    
    return empresas