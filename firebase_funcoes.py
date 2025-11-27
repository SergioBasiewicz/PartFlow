# firebase_funcoes.py
# Versão robusta: usa credenciais do Secret GOOGLE_APPLICATION_CREDENTIALS_JSON
# ou arquivo local credentials/firebase_key.json, com fallback local.

import os
import uuid
import json
import base64
from pathlib import Path
from datetime import datetime

# Tentativa de usar Google Cloud (Firestore + Storage)
USE_FIREBASE = True
try:
    from google.cloud import storage, firestore
    from google.oauth2 import service_account
except Exception:
    USE_FIREBASE = False

# Caminhos locais
PROJECT_ROOT = Path(__file__).parent
LOCAL_CRED_PATH = PROJECT_ROOT / "credentials" / "firebase_key.json"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
LOCAL_DB = PROJECT_ROOT / "db_local.json"


def _ensure_local_storage():
    """Garante estrutura de armazenamento local."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not LOCAL_DB.exists():
        LOCAL_DB.write_text(json.dumps({"pedidos": []}, indent=2, ensure_ascii=False))


def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


# -------------------------------------------------------------------
# Inicialização dos clients Firebase (se possível)
# -------------------------------------------------------------------
storage_client = None
firestore_client = None
BUCKET_NAME = os.environ.get("FIREBASE_BUCKET")  # ex: "partflow-xxxx.appspot.com"

if USE_FIREBASE:
    try:
        # 1) Tenta ler credenciais do Secret GOOGLE_APPLICATION_CREDENTIALS_JSON
        creds_raw = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
        credentials = None
        project_id = None

        if creds_raw:
            if creds_raw.lstrip().startswith("{"):
                # Parece JSON direto
                try:
                    creds_dict = json.loads(creds_raw)
                    credentials = service_account.Credentials.from_service_account_info(creds_dict)
                    project_id = creds_dict.get("project_id")
                except Exception as e:
                    print("⚠️ Erro ao decodificar GOOGLE_APPLICATION_CREDENTIALS_JSON como JSON:", e)
                    credentials = None
            else:
                # Parece caminho de arquivo
                cred_path = Path(creds_raw)
                if cred_path.exists():
                    try:
                        creds_dict = json.loads(cred_path.read_text())
                        credentials = service_account.Credentials.from_service_account_info(creds_dict)
                        project_id = creds_dict.get("project_id")
                    except Exception as e:
                        print("⚠️ Erro ao carregar credenciais do arquivo fornecido em GOOGLE_APPLICATION_CREDENTIALS_JSON:", e)
                        credentials = None

        # 2) Se não conseguiu via secret, tenta arquivo local credentials/firebase_key.json
        if credentials is None and LOCAL_CRED_PATH.exists():
            try:
                local_dict = json.loads(LOCAL_CRED_PATH.read_text())
                credentials = service_account.Credentials.from_service_account_file(str(LOCAL_CRED_PATH))
                project_id = local_dict.get("project_id")
            except Exception as e:
                print("⚠️ Erro ao carregar credenciais de", LOCAL_CRED_PATH, "->", e)
                credentials = None

        # 3) Se ainda não tem credenciais, tenta Application Default Credentials
        if credentials is None:
            try:
                storage_client = storage.Client()
                firestore_client = firestore.Client()
                # se isso deu certo, deixa assim (sem credentials explícitas)
            except Exception as e:
                print("⚠️ Não foi possível usar Application Default Credentials:", e)
                storage_client = None
                firestore_client = None

        else:
            # Temos credentials explícitas
            storage_client = storage.Client(project=project_id, credentials=credentials)
            firestore_client = firestore.Client(project=project_id, credentials=credentials)

        # Definir bucket se não vier por env
        if BUCKET_NAME is None and credentials is not None:
            try:
                # nome padrão do Firebase Storage
                BUCKET_NAME = f"{project_id}.appspot.com"
            except Exception:
                pass

        # Se ainda assim não tiver client válido, desliga Firebase
        if storage_client is None or firestore_client is None or not BUCKET_NAME:
            print("⚠️ Firebase não configurado corretamente. Usando modo LOCAL.")
            USE_FIREBASE = False

    except Exception as e:
        print("⚠️ Falha geral ao inicializar Firebase:", e)
        storage_client = None
        firestore_client = None
        USE_FIREBASE = False


# -------------------------------------------------------------------
# Funções de upload / CRUD
# -------------------------------------------------------------------
def upload_foto_bytes(nome_arquivo, bytes_data, pasta="fotos"):
    """
    Faz upload dos bytes e retorna URL pública (Firebase Storage)
    ou caminho local absoluto (sem 'file://').
    """
    if USE_FIREBASE and storage_client:
        try:
            bucket = storage_client.bucket(BUCKET_NAME)
            blob_name = f"{pasta}/{uuid.uuid4().hex}_{nome_arquivo}"
            blob = bucket.blob(blob_name)
            blob.upload_from_string(bytes_data, content_type="image/jpeg")

            try:
                # tenta deixar público
                blob.make_public()
                return blob.public_url  # https://...
            except Exception:
                # fallback: URL assinada longa
                try:
                    url = blob.generate_signed_url(expiration=3600 * 24 * 365)
                    return url
                except Exception:
                    return None
        except Exception as e:
            print("⚠️ Erro ao fazer upload para Firebase Storage:", e)
            # cai pro modo local

    # -------- Fallback LOCAL --------
    _ensure_local_storage()
    nome = f"{uuid.uuid4().hex}_{nome_arquivo}"
    caminho = UPLOADS_DIR / nome
    with open(caminho, "wb") as f:
        f.write(bytes_data)

    # retorna caminho absoluto tipo "/mount/src/partflow/uploads/xxx.jpg"
    return str(caminho.resolve())


def salvar_pedido(dados: dict, foto_bytes: bytes = None, nome_foto: str = None):
    """
    Salva novo pedido no Firestore (quando disponível) ou em db_local.json.
    Retorna dict com 'id' e possivelmente 'foto_url'.
    """
    if foto_bytes and not nome_foto:
        nome_foto = f"{uuid.uuid4().hex}.jpg"

    # Garante timestamp
    if "data_criacao" not in dados:
        dados["data_criacao"] = datetime_now_str()

    # ---------------- Firebase ----------------
    if USE_FIREBASE and firestore_client:
        try:
            if foto_bytes:
                foto_url = upload_foto_bytes(nome_foto, foto_bytes)
                if foto_url:
                    dados["foto_url"] = foto_url
                    dados["tem_foto"] = True

            doc_ref = firestore_client.collection("pedidos").document()
            doc_ref.set(dados)
            return {"id": doc_ref.id, "foto_url": dados.get("foto_url")}
        except Exception as e:
            print("⚠️ Erro salvar_pedido (firebase):", e)
            # cai para modo local

    # ---------------- Local ----------------
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    novo_id = uuid.uuid4().hex[:8]
    dados_local = dict(dados)
    dados_local["id"] = novo_id

    if foto_bytes:
        foto_url = upload_foto_bytes(nome_foto, foto_bytes)
        dados_local["foto_url"] = foto_url
        dados_local["tem_foto"] = True

    db["pedidos"].append(dados_local)
    LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False))
    return {"id": novo_id, "foto_url": dados_local.get("foto_url")}


def atualizar_pedido_foto(pedido_id, foto_url):
    """Atualiza campo foto_url em Firestore ou arquivo local."""
    if USE_FIREBASE and firestore_client:
        try:
            doc_ref = firestore_client.collection("pedidos").document(pedido_id)
            doc_ref.update({"foto_url": foto_url, "tem_foto": True})
            return True
        except Exception as e:
            print("⚠️ Erro atualizar_pedido_foto (firebase):", e)

    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    for p in db["pedidos"]:
        if p.get("id") == pedido_id:
            p["foto_url"] = foto_url
            p["tem_foto"] = True
            LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False))
            return True
    return False


def listar_pedidos():
    """Retorna lista de pedidos como dicts."""
    if USE_FIREBASE and firestore_client:
        try:
            from google.cloud import firestore as _fs

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
            return res
        except Exception as e:
            print("⚠️ Erro listar_pedidos (firebase):", e)

    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    return db.get("pedidos", [])


def atualizar_status(pedido_id, novo_status):
    """Atualiza status do pedido."""
    if USE_FIREBASE and firestore_client:
        try:
            doc_ref = firestore_client.collection("pedidos").document(pedido_id)
            doc_ref.update({"status": novo_status})
            return True
        except Exception as e:
            print("⚠️ Erro atualizar_status (firebase):", e)

    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    for p in db["pedidos"]:
        if p.get("id") == pedido_id:
            p["status"] = novo_status
            LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False))
            return True
    return False


def dataurl_para_bytes(data_url):
    """Converte data:image/...;base64,... para bytes"""
    try:
        header, b64 = data_url.split(",", 1)
        return base64.b64decode(b64)
    except Exception:
        return None
