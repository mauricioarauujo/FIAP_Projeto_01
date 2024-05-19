"""Preprocessor module for the Embrapa API project."""

import pandas as pd
from unidecode import unidecode
from typing import Dict
import logging
from embrapa_api.preprocessing.constants import (
    PRODUCAO_FILE_PATH,
    PROCESSAMENTO_PATHS,
    COMERCIALIZACAO_FILE_PATH,
    IMPORTACAO_PATHS,
)

logger = logging.getLogger(__name__)


class ProducaoPreprocessor:
    """Preprocessor class for the Producao endpoint."""

    def __init__(self):
        self.rw_producao = self.load_data()

    def load_data(self):
        """Load the data."""
        try:
            logger.info("Loading data from URL.")
            rw_producao = pd.read_csv(
                'http://vitibrasil.cnpuv.embrapa.br/download/Producao.csv', sep=';'
            )

        except Exception as e:
            logger.warning("Failed to load data from URL. Loading from local file.")
            logger.warning(e)
            rw_producao = pd.read_csv(PRODUCAO_FILE_PATH, sep=';')

        return rw_producao

    def preprocess(self):
        """Preprocess the data."""
        TIPO_PRODUTO_MAP = {
            "vm": "Vinho de Mesa",
            "vv": "Vinho Fino de Mesa",
            "su": "Suco",
            "de": "Derivados",
        }
        rf_producao = (
            self.rw_producao.melt(
                id_vars=["id", "produto", "control"],
                var_name="ano",
                value_name="producao_L",
            )
            .rename(
                columns={
                    "id": "ID_PRODUTO",
                    "produto": "NM_PRODUTO",
                    "control": "NM_CONTROLE",
                    "ano": "DT_ANO",
                    "producao_L": "VR_PRODUCAO_L",
                }
            )
            .astype(
                {
                    "ID_PRODUTO": int,
                    "NM_PRODUTO": str,
                    "NM_CONTROLE": str,
                    "DT_ANO": str,
                    "VR_PRODUCAO_L": float,
                }
            )
            .sort_values(by=["ID_PRODUTO", "DT_ANO"])
        )
        rf_producao["NM_PRODUTO"] = (
            rf_producao["NM_PRODUTO"].apply(unidecode).str.title()
        )
        rf_producao["TIPO_PRODUTO"] = (
            rf_producao["NM_CONTROLE"].str.split("_").str[0].map(TIPO_PRODUTO_MAP)
        )

        rf_producao = rf_producao.query("TIPO_PRODUTO.notnull()").drop(
            columns=["NM_CONTROLE"]
        )
        return rf_producao


class ProcessamentoPreprocessor:
    """Preprocessor class for the Processamento endpoint."""

    def __init__(self):
        self.processing_paths = PROCESSAMENTO_PATHS

    def load_data(self, tipo_uva):
        """Load the data."""
        try:
            logger.info("Loading data from URL.")
            data = pd.read_csv(self.processing_paths[tipo_uva]["url"], sep='\t')

        except Exception as e:
            logger.warning("Failed to load data from URL. Loading from local file.")
            logger.warning(e)
            data = pd.read_csv(self.processing_paths[tipo_uva]["path"], sep='\t')

        return data

    def _processa_uvas_processadas(
        self, data: pd.DataFrame, tipo_uva: str, cd_tipo_uva_map: Dict
    ):
        """Trata os dados de uvas processadas para um tipo de uva específico."""
        rf_data = data.melt(
            id_vars=["id", "control", "cultivar"],
            var_name="ano",
            value_name="uvas_processadas_Kg",
        ).rename(
            columns={
                "id": "ID_UVA_PROCESSADA",
                "control": "NM_CONTROLE",
                "cultivar": "NM_UVA",
                "ano": "DT_ANO",
                "uvas_processadas_Kg": "QT_UVAS_PROCESSADAS_KG",
            }
        )
        rf_data["CD_TIPO_VINHO"] = (
            rf_data["NM_CONTROLE"].str.split("_").str[0].map(cd_tipo_uva_map)
        )

        rf_data = rf_data.query("CD_TIPO_VINHO.notnull()").drop(columns=["NM_CONTROLE"])

        rf_data["QT_UVAS_PROCESSADAS_KG"] = rf_data["QT_UVAS_PROCESSADAS_KG"].apply(
            lambda x: float(x) if isinstance(x, (int, float)) else None
        )

        rf_data = rf_data.assign(CD_TIPO_UVA=tipo_uva.lower().replace(" ", "_")).astype(
            {
                "ID_UVA_PROCESSADA": str,
                "NM_UVA": str,
                "DT_ANO": str,
                "CD_TIPO_VINHO": str,
                "CD_TIPO_UVA": str,
                "QT_UVAS_PROCESSADAS_KG": float,
            }
        )
        assert (
            rf_data.groupby(["ID_UVA_PROCESSADA"])["NM_UVA"].nunique() == 1
        ).all, "garantir que o nome da uva é única por ID_UVA_PROCESSADA"

        rf_data["ID_UVA_PROCESSADA"] = (
            rf_data["ID_UVA_PROCESSADA"] + "_" + rf_data["CD_TIPO_UVA"]
        )

        return rf_data

    def processa_viniferas(self):
        CD_TIPO_UVA_MAP = {
            "ti": "Tintas",
            "br": "Brancas e Rosadas",
        }
        TIPO_UVA = "Viniferas"
        data = self.load_data(TIPO_UVA)

        rf_data = self._processa_uvas_processadas(data, TIPO_UVA, CD_TIPO_UVA_MAP)

        return rf_data

    def processa_americanas(self):
        CD_TIPO_UVA_MAP = {
            "ti": "Tintas",
            "br": "Brancas e Rosadas",
        }
        TIPO_UVA = "Americanas"
        data = self.load_data(TIPO_UVA)

        rf_data = self._processa_uvas_processadas(data, TIPO_UVA, CD_TIPO_UVA_MAP)

        return rf_data

    def processa_uvas_de_mesa(self):
        CD_TIPO_UVA_MAP = {
            "ti": "Tintas",
            "br": "Brancas",
        }
        TIPO_UVA = "Uvas de mesa"
        data = self.load_data(TIPO_UVA)

        rf_data = self._processa_uvas_processadas(data, TIPO_UVA, CD_TIPO_UVA_MAP)

        return rf_data

    def processa_sem_classe(self):
        CD_TIPO_UVA_MAP = {
            "sc": "Sem classificação",
        }
        TIPO_UVA = "Sem Classe"
        data = self.load_data(TIPO_UVA)

        rf_data = self._processa_uvas_processadas(data, TIPO_UVA, CD_TIPO_UVA_MAP)

        return rf_data

    def preprocess(self):
        """Preprocess the data."""
        viniferas = self.processa_viniferas()
        americanas = self.processa_americanas()
        uvas_de_mesa = self.processa_uvas_de_mesa()
        sem_classe = self.processa_sem_classe()

        processamento = pd.concat(
            [viniferas, americanas, uvas_de_mesa, sem_classe], ignore_index=True
        ).sort_values(by=["ID_UVA_PROCESSADA", "DT_ANO"])

        return processamento


class ComercializacaoPreprocessor:
    """Preprocessor class for the Comercializacao endpoint."""

    def __init__(self):
        self.comercializacao = self.load_data()

    def load_data(self):
        """Load the data."""
        try:
            logger.info("Loading data from URL.")
            comercializacao = pd.read_csv(
                'http://vitibrasil.cnpuv.embrapa.br/download/Comercio.csv', sep=';'
            )

        except Exception as e:
            logger.warning("Failed to load data from URL. Loading from local file.")
            logger.warning(e)
            comercializacao = pd.read_csv(COMERCIALIZACAO_FILE_PATH, sep=';')

        return comercializacao

    def preprocess(self):
        """Preprocess the data."""
        TIPO_PRODUTO_MAP = {
            "vm": "Vinho de Mesa",
            "ve": "Vinho Especial",
            "es": "Espumante",
            "su": "Suco de Uva",
            "ou": "Outros Vinhos",
        }
        rf_comercializacao = (
            self.comercializacao.melt(
                id_vars=["id", "Produto", "control"],
                var_name="ano",
                value_name="comercializacao_L",
            )
            .rename(
                columns={
                    "id": "ID_PRODUTO",
                    "Produto": "NM_PRODUTO",
                    "control": "NM_CONTROLE",
                    "ano": "DT_ANO",
                    "comercializacao_L": "VR_COMERCIALIZACAO_L",
                }
            )
            .astype(
                {
                    "ID_PRODUTO": int,
                    "NM_PRODUTO": str,
                    "NM_CONTROLE": str,
                    "DT_ANO": str,
                    "VR_COMERCIALIZACAO_L": float,
                }
            )
            .sort_values(by=["ID_PRODUTO", "DT_ANO"])
        )

        rf_comercializacao["NM_PRODUTO"] = (
            rf_comercializacao["NM_PRODUTO"].apply(unidecode).str.title()
        )
        rf_comercializacao["TIPO_PRODUTO"] = (
            rf_comercializacao["NM_CONTROLE"]
            .str.split("_")
            .str[0]
            .map(TIPO_PRODUTO_MAP)
        )

        rf_comercializacao = rf_comercializacao.query("TIPO_PRODUTO.notnull()").drop(
            columns=["NM_CONTROLE"]
        )
        return rf_comercializacao


class ImportacaoPreprocessor:
    """Preprocessor class for the Importacao endpoint."""

    def __init__(self):
        self.importacao_paths = IMPORTACAO_PATHS

    def load_data(self, produto_importacao):
        """Load the data."""
        try:
            logger.info(f"Loading data from URL. Product: {produto_importacao}")
            data = pd.read_csv(
                self.importacao_paths[produto_importacao]["url"], sep=';'
            )

        except Exception as e:
            logger.warning("Failed to load data from URL. Loading from local file.")
            logger.warning(e)
            data = pd.read_csv(
                self.importacao_paths[produto_importacao]["path"], sep=';'
            )

        return data

    def _processa_importacao(self, data: pd.DataFrame, produto_importacao: str):
        """Trata os dados de uvas processadas para um tipo de uva específico."""
        logger.info(f"Processing importing data for {produto_importacao}...")
        keys = ["Id", "País"]
        valor_cols = [col for col in data.columns if '.1' in col]
        qtd_importada_cols = [
            col for col in data.columns.difference(keys) if col not in valor_cols
        ]

        qtd_importadas_df = (
            data[keys + qtd_importada_cols]
            .melt(id_vars=keys, var_name="ano", value_name="uvas_importadas_kg")
            .rename(
                columns={
                    "Id": "CD_PAIS",
                    "País": "NM_PAIS",
                    "ano": "DT_ANO",
                    "uvas_importadas_kg": "QTD_IMPORTADO_KG",
                }
            )
        )
        vr_valor_df = (
            data[keys + valor_cols]
            .melt(id_vars=keys, var_name="ano", value_name="valor")
            .rename(
                columns={
                    "Id": "CD_PAIS",
                    "País": "NM_PAIS",
                    "ano": "DT_ANO",
                    "valor": "VL_VALOR_IMPORTADO_USD",
                }
            )
            .assign(DT_ANO=lambda x: x["DT_ANO"].str.split(".").str[0])
        )

        rf_data = qtd_importadas_df.merge(
            vr_valor_df, on=["CD_PAIS", "NM_PAIS", "DT_ANO"]
        ).assign(NM_ITEM=produto_importacao)
        # removendo CD_PAIS e organizando colunas
        # Motivo: CD_PAIS nao esta correta para outros datasets
        rf_data = rf_data[
            [
                'NM_PAIS',
                'DT_ANO',
                'NM_ITEM',
                'QTD_IMPORTADO_KG',
                'VL_VALOR_IMPORTADO_USD',
            ]
        ].sort_values(['NM_PAIS', 'DT_ANO'])

        return rf_data

    def processa_vinhos(self):
        PRODUTO_IMPORTACAO = "Vinhos"
        data = self.load_data(PRODUTO_IMPORTACAO)

        rf_data = self._processa_importacao(data, PRODUTO_IMPORTACAO)

        return rf_data

    def processa_sucos(self):
        PRODUTO_IMPORTACAO = "Sucos"
        data = self.load_data(PRODUTO_IMPORTACAO)

        rf_data = self._processa_importacao(data, PRODUTO_IMPORTACAO)

        return rf_data

    # Espumantes, Frescas e Passas
    def processa_espumantes(self):
        PRODUTO_IMPORTACAO = "Espumantes"
        data = self.load_data(PRODUTO_IMPORTACAO)

        rf_data = self._processa_importacao(data, PRODUTO_IMPORTACAO)

        return rf_data

    def processa_frescas(self):
        PRODUTO_IMPORTACAO = "Frescas"
        data = self.load_data(PRODUTO_IMPORTACAO)

        rf_data = self._processa_importacao(data, PRODUTO_IMPORTACAO)

        return rf_data

    def processa_passas(self):
        PRODUTO_IMPORTACAO = "Passas"
        data = self.load_data(PRODUTO_IMPORTACAO)

        rf_data = self._processa_importacao(data, PRODUTO_IMPORTACAO)

        return rf_data

    def preprocess(self):
        """Preprocess the data."""
        vinhos = self.processa_vinhos()
        sucos = self.processa_sucos()
        espumantes = self.processa_espumantes()
        frescas = self.processa_frescas()
        passas = self.processa_passas()

        importacao = pd.concat(
            [vinhos, sucos, espumantes, frescas, passas], ignore_index=True
        ).sort_values(by=["NM_PAIS", "DT_ANO"])

        return importacao
