"""
Módulo para gerenciar operações com o MongoDB
"""

from pymongo import MongoClient
from config.mongodb_config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME

class MongoDBManager:
    """Classe para gerenciar operações com o MongoDB"""
    
    def __init__(self):
        """Inicializa a conexão com o MongoDB"""
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.collection = self.db[COLLECTION_NAME]
    
    def inserir_muitos(self, documentos):
        """
        Insere múltiplos documentos na coleção
        
        Args:
            documentos (list): Lista de documentos a serem inseridos
            
        Returns:
            int: Número de documentos inseridos
        """
        resultado = self.collection.insert_many(documentos)
        return len(resultado.inserted_ids)
    
    def buscar_todos(self):
        """
        Busca todos os documentos na coleção
        
        Returns:
            list: Lista com todos os documentos
        """
        return list(self.collection.find())
    
    def buscar_por_setor(self, setor):
        """
        Busca empresas por setor
        
        Args:
            setor (str): Setor para filtrar empresas
            
        Returns:
            list: Lista com as empresas do setor especificado
        """
        return list(self.collection.find({"setor": setor}))
    
    def calcular_media_receita_por_setor(self):
        """
        Calcula a média de receita anual agrupada por setor
        
        Returns:
            dict: Dicionário com setores como chaves e médias como valores
        """
        pipeline = [
            {"$group": {
                "_id": "$setor",
                "media_receita": {"$avg": "$receita_anual"}
            }}
        ]
        resultados = self.collection.aggregate(pipeline)
        return {resultado["_id"]: round(resultado["media_receita"], 2) for resultado in resultados}
    
    def close(self):
        """Fecha a conexão com o MongoDB"""
        self.client.close()