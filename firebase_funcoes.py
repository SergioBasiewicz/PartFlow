# firebase_funcoes_otimizado.py
# Versão otimizada para Firebase com melhor tratamento de erros

import os
import uuid
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    import streamlit as st
except Exception:
    st = None

# --------------------------------------------------------------------
# Configuração Firebase
# --------------------------------------------------------------------
class FirebaseConfig:
    def __init__(self):
        self.USE_FIREBASE = False
        self.firestore_client = None
        self.storage_client = None
        self.BUCKET_NAME = None
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Inicializa Firebase com credenciais do Streamlit secrets"""
        try:
            # Tentar obter credenciais do Streamlit secrets
            if st is not None:
                try:
                    creds_json = st.secrets["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
                    bucket_name = st.secrets["FIREBASE_BUCKET"]
                except Exception:
                    print("❌ Credenciais não encontradas nos secrets do Streamlit")
                    return
            else:
                # Para ambiente local
                creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
                bucket_name = os.getenv("FIREBASE_BUCKET")
            
            if not creds_json or not bucket_name:
                print("❌ Variáveis de ambiente não configuradas")
                return

            # Importações Firebase
            from google.cloud import firestore, storage
            from google.oauth2 import service_account

            # Converter string JSON para dict se necessário
            if isinstance(creds_json, str):
                creds_dict = json.loads(creds_json)
            else:
                creds_dict = creds_json

            # Criar credenciais
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            
            # Inicializar clientes
            self.firestore_client = firestore.Client(
                project=creds_dict['project_id'], 
                credentials=credentials
            )
            self.storage_client = storage.Client(
                project=creds_dict['project_id'], 
                credentials=credentials
            )
            self.BUCKET_NAME = bucket_name
            self.USE_FIREBASE = True
            
            print("✅ Firebase inicializado com sucesso!")
            print(f"📦 Bucket: {self.BUCKET_NAME}")
            print(f"🏢 Projeto: {creds_dict['project_id']}")
            
        except Exception as e:
            print(f"❌ Erro ao inicializar Firebase: {e}")
            self.USE_FIREBASE = False

# Instância global
firebase_config = FirebaseConfig()

# --------------------------------------------------------------------
# Funções Utilitárias
# --------------------------------------------------------------------
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def dataurl_para_bytes(data_url: str) -> Optional[bytes]:
    """Converte data URL para bytes."""
    try:
        if not data_url or "base64" not in data_url:
            return None
        header, b64 = data_url.split(",", 1)
        return base64.b64decode(b64)
    except Exception as e:
        print(f"❌ Erro ao converter data URL: {e}")
        return None

def generate_unique_filename(original_name: str) -> str:
    """Gera nome único para arquivo."""
    ext = os.path.splitext(original_name)[1] if '.' in original_name else '.jpg'
    return f"{uuid.uuid4().hex}{ext}"

# --------------------------------------------------------------------
# Operações de Storage
# --------------------------------------------------------------------
def upload_foto_bytes(bytes_data: bytes, nome_arquivo: str, pasta: str = "fotos_pedidos") -> Optional[str]:
    """
    Faz upload de bytes para Firebase Storage e retorna URL pública.
    """
    if not firebase_config.USE_FIREBASE:
        print("❌ Firebase não disponível para upload")
        return None

    try:
        from google.cloud import storage
        
        bucket = firebase_config.storage_client.bucket(firebase_config.BUCKET_NAME)
        nome_unico = generate_unique_filename(nome_arquivo)
        blob_path = f"{pasta}/{nome_unico}"
        
        blob = bucket.blob(blob_path)
        blob.upload_from_string(bytes_data, content_type='image/jpeg')
        
        # Tornar público (para URLs acessíveis)
        blob.make_public()
        
        url = blob.public_url
        print(f"✅ Foto enviada: {url}")
        return url
        
    except Exception as e:
        print(f"❌ Erro no upload da foto: {e}")
        return None

def delete_foto(foto_url: str) -> bool:
    """
    Deleta foto do Firebase Storage.
    """
    if not firebase_config.USE_FIREBASE:
        return False

    try:
        from google.cloud import storage
        
        bucket = firebase_config.storage_client.bucket(firebase_config.BUCKET_NAME)
        
        # Extrair caminho do blob da URL
        blob_path = foto_url.split(f"/{firebase_config.BUCKET_NAME}/")[-1].split("?")[0]
        blob = bucket.blob(blob_path)
        
        blob.delete()
        print(f"✅ Foto deletada: {foto_url}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao deletar foto: {e}")
        return False

# --------------------------------------------------------------------
# CRUD de Pedidos - Firestore
# --------------------------------------------------------------------
def salvar_pedido(dados: Dict[str, Any], foto_bytes: bytes = None, nome_foto: str = None) -> Dict[str, Any]:
    """
    Salva pedido no Firestore com tratamento de foto.
    """
    pedido_id = str(uuid.uuid4())
    foto_url = None

    # Processar foto se fornecida
    if foto_bytes and nome_foto:
        foto_url = upload_foto_bytes(foto_bytes, nome_foto)
    
    # Preparar dados do pedido
    pedido_data = {
        **dados,
        "id": pedido_id,
        "data_criacao": datetime_now_str(),
        "data_atualizacao": datetime_now_str(),
        "foto_url": foto_url,
        "tem_foto": foto_url is not None
    }

    # Salvar no Firestore
    if firebase_config.USE_FIREBASE:
        try:
            doc_ref = firebase_config.firestore_client.collection("pedidos").document(pedido_id)
            doc_ref.set(pedido_data)
            print(f"✅ Pedido {pedido_id} salvo no Firestore")
            return {"id": pedido_id, "foto_url": foto_url}
        except Exception as e:
            print(f"❌ Erro ao salvar pedido no Firestore: {e}")
            raise

    raise Exception("Firebase não disponível")

def listar_pedidos(filtros: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Lista pedidos do Firestore com possibilidade de filtros.
    """
    if not firebase_config.USE_FIREBASE:
        return []

    try:
        from google.cloud.firestore import Query
        
        collection_ref = firebase_config.firestore_client.collection("pedidos")
        query = collection_ref
        
        # Aplicar filtros se fornecidos
        if filtros:
            for campo, valor in filtros.items():
                if valor:  # Só filtrar se valor não for vazio
                    query = query.where(campo, "==", valor)
        
        # Ordenar por data de criação (mais recente primeiro)
        query = query.order_by("data_criacao", direction=Query.DESCENDING)
        
        docs = query.stream()
        
        pedidos = []
        for doc in docs:
            pedido_data = doc.to_dict()
            pedido_data["id"] = doc.id
            pedidos.append(pedido_data)
        
        print(f"📥 Carregados {len(pedidos)} pedidos")
        return pedidos
        
    except Exception as e:
        print(f"❌ Erro ao listar pedidos: {e}")
        return []

def obter_pedido_por_id(pedido_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtém um pedido específico por ID.
    """
    if not firebase_config.USE_FIREBASE:
        return None

    try:
        doc_ref = firebase_config.firestore_client.collection("pedidos").document(pedido_id)
        doc = doc_ref.get()
        
        if doc.exists:
            pedido_data = doc.to_dict()
            pedido_data["id"] = doc.id
            return pedido_data
        else:
            print(f"⚠️ Pedido {pedido_id} não encontrado")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao obter pedido: {e}")
        return None

def atualizar_status(pedido_id: str, novo_status: str) -> bool:
    """
    Atualiza status de um pedido.
    """
    if not firebase_config.USE_FIREBASE:
        return False

    try:
        doc_ref = firebase_config.firestore_client.collection("pedidos").document(pedido_id)
        
        # Verificar se documento existe
        if not doc_ref.get().exists:
            print(f"⚠️ Pedido {pedido_id} não encontrado para atualização")
            return False
        
        doc_ref.update({
            "status": novo_status,
            "data_atualizacao": datetime_now_str()
        })
        
        print(f"✅ Status do pedido {pedido_id} atualizado para: {novo_status}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar status: {e}")
        return False

def atualizar_pedido(pedido_id: str, dados_atualizacao: Dict[str, Any]) -> bool:
    """
    Atualiza múltiplos campos de um pedido.
    """
    if not firebase_config.USE_FIREBASE:
        return False

    try:
        doc_ref = firebase_config.firestore_client.collection("pedidos").document(pedido_id)
        
        if not doc_ref.get().exists:
            return False
        
        dados_atualizacao["data_atualizacao"] = datetime_now_str()
        doc_ref.update(dados_atualizacao)
        
        print(f"✅ Pedido {pedido_id} atualizado")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar pedido: {e}")
        return False

def deletar_pedido(pedido_id: str) -> bool:
    """
    Deleta um pedido e sua foto associada.
    """
    if not firebase_config.USE_FIREBASE:
        return False

    try:
        # Primeiro obtém o pedido para deletar a foto
        pedido = obter_pedido_por_id(pedido_id)
        if not pedido:
            return False
        
        # Deletar foto se existir
        if pedido.get("foto_url"):
            delete_foto(pedido["foto_url"])
        
        # Deletar documento
        doc_ref = firebase_config.firestore_client.collection("pedidos").document(pedido_id)
        doc_ref.delete()
        
        print(f"✅ Pedido {pedido_id} deletado")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao deletar pedido: {e}")
        return False

# --------------------------------------------------------------------
# Estatísticas e Relatórios
# --------------------------------------------------------------------
def obter_estatisticas() -> Dict[str, Any]:
    """
    Retorna estatísticas dos pedidos.
    """
    pedidos = listar_pedidos()
    
    if not pedidos:
        return {
            "total": 0,
            "pendentes": 0,
            "solicitados": 0,
            "entregues": 0,
            "taxa_entrega": 0
        }
    
    total = len(pedidos)
    pendentes = sum(1 for p in pedidos if p.get("status") == "Pendente")
    solicitados = sum(1 for p in pedidos if p.get("status") == "Solicitado")
    entregues = sum(1 for p in pedidos if p.get("status") == "Entregue")
    
    taxa_entrega = (entregues / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "pendentes": pendentes,
        "solicitados": solicitados,
        "entregues": entregues,
        "taxa_entrega": round(taxa_entrega, 1)
    }

def buscar_pedidos(termo: str) -> List[Dict[str, Any]]:
    """
    Busca pedidos por múltiplos campos.
    """
    if not termo:
        return listar_pedidos()
    
    pedidos = listar_pedidos()
    termo_lower = termo.lower()
    
    resultados = []
    for pedido in pedidos:
        # Buscar em múltiplos campos
        campos_busca = [
            pedido.get("id", ""),
            pedido.get("tecnico", ""),
            pedido.get("peca", ""),
            pedido.get("modelo", ""),
            pedido.get("numero_serie", ""),
            pedido.get("ordem_servico", ""),
            pedido.get("observacoes", "")
        ]
        
        if any(termo_lower in str(campo).lower() for campo in campos_busca):
            resultados.append(pedido)
    
    return resultados

# --------------------------------------------------------------------
# Status do Sistema
# --------------------------------------------------------------------
def firebase_status() -> Dict[str, Any]:
    """
    Retorna status do Firebase para debug.
    """
    return {
        "USE_FIREBASE": firebase_config.USE_FIREBASE,
        "BUCKET_NAME": firebase_config.BUCKET_NAME,
        "FIRESTORE_ACTIVE": firebase_config.firestore_client is not None,
        "STORAGE_ACTIVE": firebase_config.storage_client is not None
    }
