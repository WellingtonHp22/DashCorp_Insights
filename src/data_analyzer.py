"""
Módulo para análise e visualização de dados das empresas
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

class AnalisadorDados:
    """Classe para análise e visualização de dados das empresas"""
    
    def __init__(self, dados_empresas):
        """
        Inicializa o analisador com os dados das empresas
        
        Args:
            dados_empresas (list): Lista de dicionários com dados das empresas
        """
        self.df = pd.DataFrame(dados_empresas)
        self.diretorio_saida = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.diretorio_saida, exist_ok=True)
    
    def converter_data_fundacao(self):
        """Converte a coluna de data_fundacao para o tipo datetime"""
        self.df['data_fundacao'] = pd.to_datetime(self.df['data_fundacao'])
        self.df['ano_fundacao'] = self.df['data_fundacao'].dt.year
    
    def visualizar_distribuicao_setores(self):
        """
        Cria um gráfico de pizza com a distribuição de empresas por setor
        
        Returns:
            str: Caminho do arquivo salvo
        """
        count_by_sector = self.df['setor'].value_counts()
        
        plt.figure(figsize=(10, 6))
        plt.pie(count_by_sector, labels=count_by_sector.index, autopct='%1.1f%%', shadow=True)
        plt.title('Distribuição de Empresas por Setor')
        plt.axis('equal')
        
        # Salvar o gráfico
        caminho_arquivo = os.path.join(self.diretorio_saida, 'distribuicao_setores.png')
        plt.savefig(caminho_arquivo)
        plt.close()
        
        return caminho_arquivo
    
    def visualizar_receita_por_setor(self):
        """
        Cria um gráfico de barras com a receita média por setor
        
        Returns:
            str: Caminho do arquivo salvo
        """
        receita_por_setor = self.df.groupby('setor')['receita_anual'].mean().sort_values(ascending=False)
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(receita_por_setor.index, receita_por_setor.values / 1e6)
        
        # Adicionar rótulos nas barras
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.3,
                    f'${height:.1f}M', ha='center', va='bottom')
        
        plt.title('Receita Média Anual por Setor (em milhões)')
        plt.ylabel('Receita Média (milhões $)')
        plt.xlabel('Setor')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Salvar o gráfico
        caminho_arquivo = os.path.join(self.diretorio_saida, 'receita_por_setor.png')
        plt.savefig(caminho_arquivo)
        plt.close()
        
        return caminho_arquivo
    
    def visualizar_funcionarios_por_setor(self):
        """
        Cria um gráfico de barras com o número médio de funcionários por setor
        
        Returns:
            str: Caminho do arquivo salvo
        """
        funcionarios_por_setor = self.df.groupby('setor')['numero_funcionarios'].mean().sort_values(ascending=False)
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(funcionarios_por_setor.index, funcionarios_por_setor.values, color='green')
        
        # Adicionar rótulos nas barras
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{int(height)}', ha='center', va='bottom')
        
        plt.title('Número Médio de Funcionários por Setor')
        plt.ylabel('Média de Funcionários')
        plt.xlabel('Setor')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Salvar o gráfico
        caminho_arquivo = os.path.join(self.diretorio_saida, 'funcionarios_por_setor.png')
        plt.savefig(caminho_arquivo)
        plt.close()
        
        return caminho_arquivo
    
    def exportar_dados_csv(self):
        """
        Exporta os dados para um arquivo CSV
        
        Returns:
            str: Caminho do arquivo salvo
        """
        # Formatar os valores monetários
        self.df['receita_anual_formatada'] = self.df['receita_anual'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        # Reordenar as colunas para melhor visualização
        colunas_ordenadas = ['nome_empresa', 'setor', 'receita_anual_formatada', 'numero_funcionarios', 
                        'pais', 'data_fundacao', 'ano_fundacao']
        
        # Se _id existe no DataFrame, adicione-o ao início
        if '_id' in self.df.columns:
            colunas_ordenadas = ['_id'] + colunas_ordenadas
            
        # Selecionar apenas as colunas que existem no DataFrame
        colunas_para_exportar = [col for col in colunas_ordenadas if col in self.df.columns]
        
        # Remover a coluna receita_anual (usaremos a formatada)
        if 'receita_anual' in colunas_para_exportar and 'receita_anual_formatada' in colunas_para_exportar:
            colunas_para_exportar.remove('receita_anual')
            
        # Renomear as colunas para o Excel
        rename_dict = {
            'nome_empresa': 'Nome da Empresa',
            'setor': 'Setor',
            'receita_anual_formatada': 'Receita Anual',
            'numero_funcionarios': 'Nº de Funcionários',
            'pais': 'País',
            'data_fundacao': 'Data de Fundação',
            'ano_fundacao': 'Ano de Fundação',
            '_id': 'ID'
        }
        
        # Preparar o dataframe para exportação
        df_export = self.df[colunas_para_exportar].copy()
        df_export.rename(columns=rename_dict, inplace=True)
        
        # Salvar em CSV com codificação UTF-8 e separador de ponto e vírgula (melhor para Excel)
        caminho_arquivo = os.path.join(self.diretorio_saida, 'dados_empresas.csv')
        df_export.to_csv(caminho_arquivo, index=False, encoding='utf-8-sig', sep=';')
        
        # Exportar também como Excel se pandas tiver a funcionalidade
        try:
            caminho_excel = os.path.join(self.diretorio_saida, 'dados_empresas.xlsx')
            df_export.to_excel(caminho_excel, index=False, engine='openpyxl')
            return caminho_excel  # Priorizar retornar o caminho do Excel
        except:
            return caminho_arquivo  # Retornar apenas o CSV se Excel falhar
    
    def gerar_relatorio(self):
        """
        Gera um relatório com todas as análises
        
        Returns:
            dict: Dicionário com caminhos dos arquivos gerados
        """
        self.converter_data_fundacao()
        
        relatorio = {
            'distribuicao_setores': self.visualizar_distribuicao_setores(),
            'receita_por_setor': self.visualizar_receita_por_setor(),
            'funcionarios_por_setor': self.visualizar_funcionarios_por_setor(),
            'dados_csv': self.exportar_dados_csv()
        }
        
        return relatorio