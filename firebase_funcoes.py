# firebase_funcoes_corrigido.py
import os
import uuid
import json
import base64
from pathlib import Path
from datetime import datetime

# Tentar importar streamlit para ler st.secrets
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except Exception:
    st = None
    STREAMLIT_AVAILABLE = False

# --------------------------------------------------------------------
# Configurações Locais (Fallback)
# --------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"
LOCAL_DB = PROJECT_ROOT / "db_local.json"

def _ensure_local_storage():
    """Garante pasta uploads/ e arquivo db_local.json."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not LOCAL_DB.exists():
        LOCAL_DB.write_text(json.dumps({"pedidos": []}, indent=2, ensure_ascii=False))

# --------------------------------------------------------------------
# Inicialização do Firebase - VERSÃO CORRIGIDA
# --------------------------------------------------------------------
USE_FIREBASE = False
firestore_client = None
storage_client = None
BUCKET_NAME = None

def initialize_firebase():
    """Inicializa Firebase de forma mais robusta"""
    global USE_FIREBASE, firestore_client, storage_client, BUCKET_NAME
    
    print("🔄 Inicializando Firebase...")
    
    # Método 1: Streamlit Secrets (Cloud)
    if STREAMLIT_AVAILABLE:
        try:
            if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
                creds_data = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
                bucket_name = st.secrets.get('FIREBASE_BUCKET', '')
                
                print("✅ Credenciais encontradas nos secrets do Streamlit")
                return _setup_firebase_with_creds(creds_data, bucket_name)
        except Exception as e:
            print(f"❌ Erro ao acessar secrets: {e}")

    # Método 2: Variáveis de ambiente
    env_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    env_bucket = os.getenv('FIREBASE_BUCKET')
    
    if env_creds and env_bucket:
        print("✅ Credenciais encontradas nas variáveis de ambiente")
        return _setup_firebase_with_creds(env_creds, env_bucket)
    
    # Método 3: Arquivo de credenciais local
    creds_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_file and os.path.exists(creds_file):
        try:
            with open(creds_file, 'r') as f:
                creds_data = json.load(f)
            bucket_name = os.getenv('FIREBASE_BUCKET', '')
            print("✅ Credenciais carregadas de arquivo local")
            return _setup_firebase_with_creds(creds_data, bucket_name)
        except Exception as e:
            print(f"❌ Erro ao ler arquivo de credenciais: {e}")

    print("❌ Nenhum método de autenticação do Firebase encontrado")
    print("📁 Usando modo local (fallback)")
    _ensure_local_storage()
    return False

def _setup_firebase_with_creds(creds_data, bucket_name):
    """Configura Firebase com credenciais"""
    global USE_FIREBASE, firestore_client, storage_client, BUCKET_NAME
    
    try:
        from google.cloud import firestore, storage
        from google.oauth2 import service_account
        
        # Se creds_data é string, converter para dict
        if isinstance(creds_data, str):
            creds_data = json.loads(creds_data)
        
        # Validar credenciais
        required_fields = ['project_id', 'private_key', 'client_email']
        for field in required_fields:
            if field not in creds_data:
                print(f"❌ Campo obrigatório faltando: {field}")
                return False
        
        credentials = service_account.Credentials.from_service_account_info(creds_data)
        project_id = creds_data['project_id']
        
        # Inicializar clientes
        firestore_client = firestore.Client(credentials=credentials, project=project_id)
        storage_client = storage.Client(credentials=credentials, project=project_id)
        
        # Configurar bucket
        if bucket_name:
            BUCKET_NAME = bucket_name
        else:
            BUCKET_NAME = f"{project_id}.appspot.com"
        
        USE_FIREBASE = True
        
        print(f"✅ Firebase inicializado com sucesso!")
        print(f"🏢 Projeto: {project_id}")
        print(f"📦 Bucket: {BUCKET_NAME}")
        
        # Teste rápido de conexão
        _test_firebase_connection()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao configurar Firebase: {e}")
        return False

def _test_firebase_connection():
    """Testa a conexão com Firebase"""
    try:
        # Testar Firestore
        firestore_client.collection('test').document('test').set({'test': True})
        firestore_client.collection('test').document('test').delete()
        
        # Testar Storage
        bucket = storage_client.bucket(BUCKET_NAME)
        bucket.exists()
        
        print("✅ Conexões testadas com sucesso")
    except Exception as e:
        print(f"⚠️ Teste de conexão falhou: {e}")

# Inicializar Firebase ao importar o módulo
initialize_firebase()

# --------------------------------------------------------------------
# Funções Utilitárias
# --------------------------------------------------------------------
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def dataurl_para_bytes(data_url: str):
    """Converte data URL para bytes."""
    try:
        if data_url and "base64" in data_url:
            header, b64 = data_url.split(",", 1)
            return base64.b64decode(b64)
    except Exception as e:
        print(f"❌ Erro ao converter data URL: {e}")
    return None

# --------------------------------------------------------------------
# Operações com Fotos
# --------------------------------------------------------------------
def upload_foto_bytes(bytes_data: bytes, nome_arquivo: str) -> str:
    """
    Faz upload para Firebase Storage ou salva localmente.
    """
    # Firebase
    if USE_FIREBASE and storage_client:
        try:
            from google.cloud import storage
            
            bucket = storage_client.bucket(BUCKET_NAME)
            blob_name = f"fotos/{uuid.uuid4().hex}_{nome_arquivo}"
            blob = bucket.blob(blob_name)
            
            blob.upload_from_string(bytes_data, content_type='image/jpeg')
            blob.make_public()
            
            url = blob.public_url
            print(f"✅ Foto enviada para Firebase: {url}")
            return url
            
        except Exception as e:
            print(f"❌ Erro no upload Firebase: {e}")

    # Fallback local
    _ensure_local_storage()
    nome_arquivo_local = f"{uuid.uuid4().hex}_{nome_arquivo}"
    caminho_local = UPLOADS_DIR / nome_arquivo_local
    
    with open(caminho_local, 'wb') as f:
        f.write(bytes_data)
    
    local_url = f"file://{caminho_local.resolve()}"
    print(f"📁 Foto salva localmente: {local_url}")
    return local_url

# --------------------------------------------------------------------
# CRUD de Pedidos - VERSÃO CORRIGIDA
# --------------------------------------------------------------------
def salvar_pedido(dados: dict, foto_bytes: bytes = None, nome_foto: str = None):
    """
    Salva pedido no Firebase ou localmente.
    """
    try:
        pedido_id = str(uuid.uuid4())
        foto_url = None
        
        # Processar foto
        if foto_bytes and nome_foto:
            foto_url = upload_foto_bytes(foto_bytes, nome_foto)
        
        # Preparar dados completos
        pedido_completo = {
            **dados,
            'id': pedido_id,
            'data_criacao': datetime_now_str(),
            'foto_url': foto_url,
            'tem_foto': foto_url is not None
        }
        
        # Tentar Firebase primeiro
        if USE_FIREBASE and firestore_client:
            try:
                doc_ref = firestore_client.collection('pedidos').document(pedido_id)
                doc_ref.set(pedido_completo)
                print(f"✅ Pedido {pedido_id} salvo no Firestore")
                return pedido_id
            except Exception as e:
                print(f"❌ Erro ao salvar no Firestore: {e}")
                # Continuar para fallback local
        
        # Fallback local
        _ensure_local_storage()
        db = json.loads(LOCAL_DB.read_text())
        db['pedidos'].append(pedido_completo)
        LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False))
        
        print(f"💾 Pedido {pedido_id} salvo localmente")
        return pedido_id
        
    except Exception as e:
        print(f"❌ Erro crítico em salvar_pedido: {e}")
        raise

def listar_pedidos():
    """Lista todos os pedidos."""
    # Firebase
    if USE_FIREBASE and firestore_client:
        try:
            from google.cloud.firestore import Query
            
            docs = firestore_client.collection('pedidos').order_by(
                'data_criacao', direction=Query.DESCENDING
            ).stream()
            
            pedidos = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                pedidos.append(data)
            
            print(f"📥 {len(pedidos)} pedidos do Firestore")
            return pedidos
            
        except Exception as e:
            print(f"❌ Erro ao listar do Firestore: {e}")
    
    # Fallback local
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    pedidos = db.get('pedidos', [])
    print(f"📥 {len(pedidos)} pedidos locais")
    return pedidos

def atualizar_status(pedido_id: str, novo_status: str) -> bool:
    """Atualiza status de um pedido."""
    # Firebase
    if USE_FIREBASE and firestore_client:
        try:
            doc_ref = firestore_client.collection('pedidos').document(pedido_id)
            doc = doc_ref.get()
            
            if doc.exists:
                doc_ref.update({'status': novo_status})
                print(f"✅ Status atualizado no Firestore: {pedido_id} -> {novo_status}")
                return True
        except Exception as e:
            print(f"❌ Erro ao atualizar no Firestore: {e}")
    
    # Fallback local
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    
    for pedido in db['pedidos']:
        if pedido.get('id') == pedido_id:
            pedido['status'] = novo_status
            LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False))
            print(f"💾 Status atualizado localmente: {pedido_id} -> {novo_status}")
            return True
    
    print(f"⚠️ Pedido não encontrado: {pedido_id}")
    return False

def firebase_status():
    """Retorna status do Firebase."""
    return {
        "USE_FIREBASE": USE_FIREBASE,
        "BUCKET_NAME": BUCKET_NAME,
        "FIRESTORE_ACTIVE": firestore_client is not None,
        "STORAGE_ACTIVE": storage_client is not None
    }
