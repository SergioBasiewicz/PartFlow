# firebase_funcoes.py
# Versão ajustada para Streamlit Cloud + Firebase Storage + Firestore
# Usa:
#   - GOOGLE_APPLICATION_CREDENTIALS_JSON (secrets)
#   - FIREBASE_BUCKET (secrets)
#
# Se algo der errado na inicialização do Firebase, cai em modo local
# (salva JSON em db_local.json e fotos em ./uploads) e escreve logs
# no console.

import os
import uuid
import json
import base64
from pathlib import Path
from datetime import datetime

# -----------------------------------------------------------------------------
# Configuração de caminhos para modo LOCAL (fallback)
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"
LOCAL_DB = PROJECT_ROOT / "db_local.json"


def _ensure_local_storage():
    """Garante que pasta uploads/ e arquivo db_local.json existam."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not LOCAL_DB.exists():
        LOCAL_DB.write_text(json.dumps({"pedidos": []}, indent=2, ensure_ascii=False))


# -----------------------------------------------------------------------------
# Tentativa de inicializar Firebase (Storage + Firestore)
# -----------------------------------------------------------------------------
USE_FIREBASE = True
storage_client = None
firestore_client = None
BUCKET_NAME = None

try:
    from google.cloud import storage, firestore
    from google.oauth2 import service_account
except Exception as e:
    print("⚠️ [firebase_funcoes] Não foi possível importar bibliotecas do Google Cloud:", e)
    USE_FIREBASE = False

if USE_FIREBASE:
    try:
        # Lê credenciais do secret GOOGLE_APPLICATION_CREDENTIALS_JSON
        creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
        if not creds_json:
            raise RuntimeError("Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS_JSON não encontrada.")

        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        project_id = creds_dict.get("project_id")
        if not project_id:
            raise RuntimeError("project_id ausente no JSON de credenciais.")

        # Inicializa clients
        storage_client = storage.Client(project=project_id, credentials=credentials)
        firestore_client = firestore.Client(project=project_id, credentials=credentials)

        # Bucket: pega do secret FIREBASE_BUCKET ou deduz padrão
        BUCKET_NAME = os.getenv("FIREBASE_BUCKET", "").strip()
        if not BUCKET_NAME:
            # fallback pra padrão antigo, se você não definir FIREBASE_BUCKET
            BUCKET_NAME = f"{project_id}.appspot.com"

        print(f"✅ [firebase_funcoes] Firebase inicializado. Projeto: {project_id}, Bucket: {BUCKET_NAME}")

    except Exception as e:
        print("⚠️ [firebase_funcoes] Falha ao inicializar Firebase, usando modo LOCAL:", e)
        USE_FIREBASE = False
        storage_client = None
        firestore_client = None


# -----------------------------------------------------------------------------
# Funções auxiliares
# -----------------------------------------------------------------------------
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def dataurl_para_bytes(data_url: str):
    """Converte data:image/...;base64,... em bytes."""
    try:
        header, b64 = data_url.split(",", 1)
        return base64.b64decode(b64)
    except Exception as e:
        print("⚠️ [firebase_funcoes] Erro ao converter data_url para bytes:", e)
        return None


# -----------------------------------------------------------------------------
# Upload de foto
# -----------------------------------------------------------------------------
def upload_foto_bytes(nome_arquivo: str, bytes_data: bytes, pasta: str = "fotos") -> str:
    """
    Faz upload dos bytes e retorna URL pública (Firebase Storage)
    ou caminho local (modo fallback).
    """
    # Tenta Firebase primeiro
    if USE_FIREBASE and storage_client:
        try:
            bucket = storage_client.bucket(BUCKET_NAME)
            blob_name = f"{pasta}/{uuid.uuid4().hex}_{nome_arquivo}"
            blob = bucket.blob(blob_name)

            blob.upload_from_string(bytes_data, content_type="image/jpeg")
            # Tenta deixar público
            try:
                blob.make_public()
                url = blob.public_url
            except Exception:
                # Se não der pra deixar público, gera URL assinada longa
                url = blob.generate_signed_url(expiration=3600 * 24 * 365)

            print(f"✅ [firebase_funcoes] Foto enviada para Storage: {blob_name}")
            return url

        except Exception as e:
            print("⚠️ [firebase_funcoes] Erro no upload para Firebase Storage, caindo para modo LOCAL:", e)

    # Fallback local
    _ensure_local_storage()
    nome = f"{uuid.uuid4().hex}_{nome_arquivo}"
    caminho = UPLOADS_DIR / nome
    with open(caminho, "wb") as f:
        f.write(bytes_data)

    local_url = f"file://{caminho.resolve()}"
    print(f"💾 [firebase_funcoes] Foto salva localmente em {local_url}")
    return local_url


# -----------------------------------------------------------------------------
# CRUD de pedidos
# -----------------------------------------------------------------------------
def salvar_pedido(dados: dict, foto_bytes: bytes = None, nome_foto: str = None):
    """
    Salva novo pedido no Firestore (se disponível) ou em db_local.json.
    Retorna:
      - dict {"id": <id>, "foto_url": <url>}  (modo Firebase)
      - dict {"id": <id>, "foto_url": <url_ou_None>} (modo local)
    """
    if foto_bytes and not nome_foto:
        nome_foto = f"{uuid.uuid4().hex}.jpg"

    dados_a_salvar = dict(dados)  # cópia pra não mutar original

    # Garante timestamp
    if "data_criacao" not in dados_a_salvar:
        dados_a_salvar["data_criacao"] = datetime_now_str()

    foto_url = None
    if foto_bytes:
        foto_url = upload_foto_bytes(nome_foto, foto_bytes)
        if foto_url:
            dados_a_salvar["foto_url"] = foto_url
            dados_a_salvar["tem_foto"] = True

    # --- Firebase Firestore ---
    if USE_FIREBASE and firestore_client:
        try:
            doc_ref = firestore_client.collection("pedidos").document()
            doc_ref.set(dados_a_salvar)
            print(f"✅ [firebase_funcoes] Pedido salvo no Firestore com ID {doc_ref.id}")
            return {"id": doc_ref.id, "foto_url": foto_url}
        except Exception as e:
            print("⚠️ [firebase_funcoes] Erro ao salvar pedido no Firestore, usando modo LOCAL:", e)

    # --- Fallback LOCAL ---
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text(encoding="utf-8"))
    novo_id = uuid.uuid4().hex[:8]
    dados_local = dict(dados_a_salvar)
    dados_local["id"] = novo_id
    db["pedidos"].append(dados_local)
    LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"💾 [firebase_funcoes] Pedido salvo em db_local.json com ID {novo_id}")
    return {"id": novo_id, "foto_url": foto_url}


def listar_pedidos():
    """
    Retorna lista de pedidos como lista de dicts.
    Prioriza Firestore; se falhar, usa db_local.json.
    """
    # Firestore
    if USE_FIREBASE and firestore_client:
        try:
            from google.cloud import firestore as _fs

            # ordenar por data_criacao asc ou desc (aqui DESC)
            docs = (
                firestore_client.collection("pedidos")
                .order_by("data_criacao", direction=_fs.Query.DESCENDING)
                .stream()
            )
            res = []
            for d in docs:
                obj = d.to_dict()
                obj["id"] = d.id
                res.append(obj)
            print(f"✅ [firebase_funcoes] {len(res)} pedidos carregados do Firestore")
            return res

        except Exception as e:
            print("⚠️ [firebase_funcoes] Erro ao listar pedidos do Firestore, usando modo LOCAL:", e)

    # Local
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text(encoding="utf-8"))
    pedidos = db.get("pedidos", [])
    print(f"💾 [firebase_funcoes] {len(pedidos)} pedidos carregados de db_local.json")
    return pedidos


def atualizar_status(pedido_id: str, novo_status: str) -> bool:
    """
    Atualiza o campo 'status' do pedido.
    Retorna True se conseguiu, False caso contrário.
    """
    # Firestore primeiro
    if USE_FIREBASE and firestore_client:
        try:
            doc_ref = firestore_client.collection("pedidos").document(pedido_id)
            doc_ref.update({"status": novo_status})
            print(f"✅ [firebase_funcoes] Status do pedido {pedido_id} atualizado no Firestore para {novo_status}")
            return True
        except Exception as e:
            print("⚠️ [firebase_funcoes] Erro ao atualizar status no Firestore, tentando modo LOCAL:", e)

    # Local
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text(encoding="utf-8"))
    alterou = False
    for p in db.get("pedidos", []):
        if p.get("id") == pedido_id:
            p["status"] = novo_status
            alterou = True
            break
    if alterou:
        LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"💾 [firebase_funcoes] Status do pedido {pedido_id} atualizado em db_local.json para {novo_status}")
    else:
        print(f"⚠️ [firebase_funcoes] Pedido {pedido_id} não encontrado em db_local.json")
    return alterou
