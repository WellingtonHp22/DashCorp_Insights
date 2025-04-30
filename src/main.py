"""
Script principal para o projeto de análise de dados empresariais
"""

import os
import sys
import logging
from datetime import datetime

# Adicionar o diretório pai ao sys.path para permitir importações relativas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_generator import gerar_empresas
from src.mongo_manager import MongoDBManager
from src.data_analyzer import AnalisadorDados

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'app.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Função principal do aplicativo"""
    try:
        # Registrar início da execução
        logger.info("Iniciando aplicação de análise de dados empresariais")
        
        # Gerar dados fictícios
        logger.info("Gerando dados de empresas fictícias")
        quantidade_empresas = 100  # Pode ser ajustado conforme necessário
        empresas = gerar_empresas(quantidade_empresas)
        logger.info(f"Gerados dados para {len(empresas)} empresas")
        
        # Conectar ao MongoDB e inserir dados
        logger.info("Conectando ao MongoDB")
        mongo_manager = MongoDBManager()
        
        # Verificar se já existem dados na coleção
        dados_existentes = mongo_manager.buscar_todos()
        
        if not dados_existentes:
            # Inserir dados se a coleção estiver vazia
            logger.info("Inserindo dados no MongoDB")
            num_inseridos = mongo_manager.inserir_muitos(empresas)
            logger.info(f"Inseridos {num_inseridos} documentos no MongoDB")
            dados_empresas = mongo_manager.buscar_todos()
        else:
            logger.info(f"Utilizando {len(dados_existentes)} documentos já existentes no MongoDB")
            dados_empresas = dados_existentes
        
        # Analisar e visualizar dados
        logger.info("Iniciando análise e visualização de dados")
        analisador = AnalisadorDados(dados_empresas)
        relatorio = analisador.gerar_relatorio()
        
        # Exibir resultados
        logger.info("Relatório gerado com sucesso")
        logger.info(f"Arquivos gerados:")
        for nome, caminho in relatorio.items():
            logger.info(f"  - {nome}: {caminho}")
        
        # Calcular estatísticas usando MongoDB
        logger.info("Calculando estatísticas usando agregações do MongoDB")
        media_receita_por_setor = mongo_manager.calcular_media_receita_por_setor()
        
        logger.info("Média de receita anual por setor:")
        for setor, media in media_receita_por_setor.items():
            logger.info(f"  - {setor}: ${media/1e6:.2f} milhões")
        
        # Fechar conexão com o MongoDB
        mongo_manager.close()
        logger.info("Aplicação finalizada com sucesso")
        
        return relatorio
        
    except Exception as e:
        logger.error(f"Erro na execução da aplicação: {str(e)}", exc_info=True)
        return None

if __name__ == "__main__":
    main()