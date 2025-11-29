import os
import uuid
import json
import base64
from pathlib import Path
from datetime import datetime

# --------------------------------------------------------------------
# Configurações Locais (Fallback)
# --------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"
LOCAL_DB = PROJECT_ROOT / "db_local.json"

def _ensure_local_storage():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not LOCAL_DB.exists():
        LOCAL_DB.write_text(json.dumps({"pedidos": []}, indent=2, ensure_ascii=False))

# --------------------------------------------------------------------
# Inicialização do Firebase - VERSÃO SIMPLIFICADA
# --------------------------------------------------------------------
USE_FIREBASE = False
firestore_client = None
storage_client = None
BUCKET_NAME = None

print("=== 🔥 INICIALIZANDO FIREBASE ===")

try:
    import streamlit as st
    from google.cloud import firestore, storage
    from google.oauth2 import service_account
    
    print("✅ Streamlit e Firebase imports OK")
    
    # Verificar secrets
    if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
        print("✅ Credenciais encontradas nos secrets")
        
        creds_data = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
        BUCKET_NAME = st.secrets.get('FIREBASE_BUCKET', 'partflow-81c43.appspot.com')
        
        # Converter string para dict se necessário
        if isinstance(creds_data, str):
            print("📝 Convertendo string para JSON...")
            creds_dict = json.loads(creds_data)
        else:
            creds_dict = creds_data
        
        print(f"🏢 Project ID: {creds_dict.get('project_id')}")
        
        # Inicializar Firebase
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        project_id = creds_dict['project_id']
        
        firestore_client = firestore.Client(credentials=credentials, project=project_id)
        storage_client = storage.Client(credentials=credentials, project=project_id)
        
        USE_FIREBASE = True
        print("🎉 FIREBASE CONFIGURADO COM SUCESSO!")
        print(f"📦 Bucket: {BUCKET_NAME}")
        
    else:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS_JSON não encontrado")

except Exception as e:
    print(f"❌ Erro Firebase: {e}")
    USE_FIREBASE = False

if not USE_FIREBASE:
    _ensure_local_storage()
    print("🔧 Usando modo local")

# --------------------------------------------------------------------
# Funções Principais (mantenha as suas existentes)
# --------------------------------------------------------------------
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def dataurl_para_bytes(data_url: str):
    try:
        if data_url and "base64" in data_url:
            header, b64 = data_url.split(",", 1)
            return base64.b64decode(b64)
    except Exception:
        return None
    return None

def upload_foto_bytes(bytes_data: bytes, nome_arquivo: str):
    if USE_FIREBASE and storage_client:
        try:
            bucket = storage_client.bucket(BUCKET_NAME)
            blob_name = f"fotos/{uuid.uuid4().hex}_{nome_arquivo}"
            blob = bucket.blob(blob_name)
            blob.upload_from_string(bytes_data, content_type='image/jpeg')
            blob.make_public()
            return blob.public_url
        except Exception as e:
            print(f"Erro upload Firebase: {e}")
    
    # Fallback local
    _ensure_local_storage()
    nome_arquivo_local = f"{uuid.uuid4().hex}_{nome_arquivo}"
    caminho_local = UPLOADS_DIR / nome_arquivo_local
    with open(caminho_local, 'wb') as f:
        f.write(bytes_data)
    return f"file://{caminho_local.resolve()}"

def salvar_pedido(dados: dict, foto_bytes: bytes = None, nome_foto: str = None):
    try:
        pedido_id = str(uuid.uuid4())
        foto_url = None
        
        if foto_bytes and nome_foto:
            foto_url = upload_foto_bytes(foto_bytes, nome_foto)
        
        pedido_data = {
            **dados,
            'id': pedido_id,
            'data_criacao': datetime_now_str(),
            'foto_url': foto_url,
            'tem_foto': foto_url is not None
        }
        
        if USE_FIREBASE and firestore_client:
            doc_ref = firestore_client.collection('pedidos').document(pedido_id)
            doc_ref.set(pedido_data)
            print(f"✅ Pedido {pedido_id} salvo no Firestore")
            return pedido_id
        else:
            # Fallback local
            _ensure_local_storage()
            db = json.loads(LOCAL_DB.read_text())
            db['pedidos'].append(pedido_data)
            LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False))
            print(f"💾 Pedido {pedido_id} salvo localmente")
            return pedido_id
            
    except Exception as e:
        print(f"❌ Erro salvar_pedido: {e}")
        return str(uuid.uuid4())

# ... (mantenha suas outras funções listar_pedidos, atualizar_status, etc)

def firebase_status():
    return {
        "USE_FIREBASE": USE_FIREBASE,
        "BUCKET_NAME": BUCKET_NAME,
    }
