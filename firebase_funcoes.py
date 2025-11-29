# firebase_funcoes.py
# Integração com Firestore + Storage (usando secrets do Streamlit Cloud)
# Fallback local (db_local.json) apenas se NÃO houver credenciais válidas.

import os
import uuid
import json
import base64
from pathlib import Path
from datetime import datetime

# Tentar importar streamlit para ler st.secrets (no Cloud)
try:
    import streamlit as st  # type: ignore
except Exception:  # em testes sem streamlit
    st = None  # type: ignore

# --------------------------------------------------------------------
# Caminhos para modo local (fallback)
# --------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"
LOCAL_DB = PROJECT_ROOT / "db_local.json"


def _ensure_local_storage():
    """Garante pasta uploads/ e arquivo db_local.json (fallback local)."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not LOCAL_DB.exists():
        LOCAL_DB.write_text(json.dumps({"pedidos": []}, indent=2, ensure_ascii=False))


# --------------------------------------------------------------------
# Inicialização do Firebase (Firestore + Storage)
# --------------------------------------------------------------------
USE_FIREBASE = False
firestore_client = None
storage_client = None
BUCKET_NAME = None

# ---- LENDO CREDENCIAIS DOS SECRETS ----
FIREBASE_CREDS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
FIREBASE_BUCKET_ENV = os.getenv("FIREBASE_BUCKET", "").strip()
creds_dict = None

# 1) Tenta pegar pelos secrets do Streamlit (recomendado no Cloud)
if st is not None:
    try:
        if not FIREBASE_CREDS_JSON:
            val = st.secrets.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "")
            if isinstance(val, dict):
                creds_dict = val
            elif isinstance(val, str):
                FIREBASE_CREDS_JSON = val.strip()
        if not FIREBASE_BUCKET_ENV:
            FIREBASE_BUCKET_ENV = str(
                st.secrets.get("FIREBASE_BUCKET", "")
            ).strip()
    except Exception:
        # Se der erro aqui, só seguimos adiante e tentamos o que tiver
        pass

# 2) Se ainda não temos dict mas temos string JSON, faz o parse
if creds_dict is None and FIREBASE_CREDS_JSON:
    try:
        creds_dict = json.loads(FIREBASE_CREDS_JSON)
    except Exception as e:
        print("⚠️ Erro ao fazer json.loads das credenciais:", repr(e))
        creds_dict = None

# 3) Se temos credenciais, tenta inicializar Firestore + Storage
if creds_dict:
    try:
        from google.cloud import firestore, storage
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_info(
            creds_dict
        )

        project_id = creds_dict.get("project_id") or os.getenv("GCLOUD_PROJECT")
        if not project_id:
            raise RuntimeError("project_id não encontrado nas credenciais.")

        firestore_client = firestore.Client(
            project=project_id, credentials=credentials
        )
        storage_client = storage.Client(project=project_id, credentials=credentials)

        # Bucket: tenta nesta ordem:
        # 1) FIREBASE_BUCKET do secrets/env
        # 2) storage_bucket dentro do JSON (se existir)
        # 3) padrão <project_id>.appspot.com
        BUCKET_NAME = (
            FIREBASE_BUCKET_ENV
            or creds_dict.get("storage_bucket")
            or f"{project_id}.appspot.com"
        )

        USE_FIREBASE = True
        print("✅ Firebase inicializado com sucesso. Projeto:", project_id)
        print("✅ Bucket configurado:", BUCKET_NAME)
    except Exception as e:
        print("⚠️ Não foi possível inicializar Firebase, usando armazenamento local.")
        print("Motivo:", repr(e))
        USE_FIREBASE = False
else:
    print("⚠️ GOOGLE_APPLICATION_CREDENTIALS_JSON não foi encontrado ou é inválido.")
    print("   Usando APENAS armazenamento local (arquivo db_local.json).")
    USE_FIREBASE = False


# --------------------------------------------------------------------
# Funções utilitárias
# --------------------------------------------------------------------
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def dataurl_para_bytes(data_url: str):
    """Converte data:image/...;base64,... para bytes."""
    try:
        header, b64 = data_url.split(",", 1)
        return base64.b64decode(b64)
    except Exception:
        return None


# --------------------------------------------------------------------
# Upload de foto
# --------------------------------------------------------------------
def upload_foto_bytes(nome_arquivo: str, bytes_data: bytes, pasta: str = "fotos"):
    """
    Sobe os bytes para o Firebase Storage e retorna URL pública.
    Se Firebase não estiver disponível, salva localmente (fallback).
    """
    # ----- Firebase -----
    if USE_FIREBASE and storage_client and BUCKET_NAME:
        try:
            bucket = storage_client.bucket(BUCKET_NAME)
            blob_name = f"{pasta}/{uuid.uuid4().hex}_{nome_arquivo}"
            blob = bucket.blob(blob_name)
            blob.upload_from_string(bytes_data, content_type="image/jpeg")

            # Deixa público (ou gera signed URL)
            try:
                blob.make_public()
                url = blob.public_url
            except Exception:
                url = blob.generate_signed_url(expiration=3600 * 24 * 365)

            print("📸 Foto enviada para Firebase Storage:", url)
            return url
        except Exception as e:
            print("⚠️ Erro ao subir foto no Firebase Storage, usando fallback local.")
            print("Motivo:", repr(e))

    # ----- Fallback local -----
    _ensure_local_storage()
    nome = f"{uuid.uuid4().hex}_{nome_arquivo}"
    caminho = UPLOADS_DIR / nome
    with open(caminho, "wb") as f:
        f.write(bytes_data)

    local_url = f"file://{caminho.resolve()}"
    print("📸 Foto salva em modo local:", local_url)
    return local_url


# --------------------------------------------------------------------
# CRUD dos pedidos
# --------------------------------------------------------------------
def salvar_pedido(dados: dict, foto_bytes: bytes = None, nome_foto: str = None):
    """
    Salva novo pedido no Firestore (quando disponível) ou em db_local.json.
    Retorna dict com 'id' e opcionalmente 'foto_url'.
    """
    if foto_bytes and not nome_foto:
        nome_foto = f"{uuid.uuid4().hex}.jpg"

    foto_url = None

    # 1) Firebase
    if USE_FIREBASE and firestore_client:
        try:
            if foto_bytes:
                foto_url = upload_foto_bytes(nome_foto, foto_bytes)
                if foto_url:
                    dados["foto_url"] = foto_url
                    dados["tem_foto"] = True

            if "data_criacao" not in dados:
                dados["data_criacao"] = datetime_now_str()

            doc_ref = firestore_client.collection("pedidos").document()
            doc_ref.set(dados)

            print("✅ Pedido salvo no Firestore com ID:", doc_ref.id)
            return {"id": doc_ref.id, "foto_url": foto_url}
        except Exception as e:
            print("⚠️ Erro em salvar_pedido (Firebase). Indo para fallback local.")
            print("Motivo:", repr(e))

    # 2) Fallback local
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    novo_id = uuid.uuid4().hex[:8]
    dados_local = dict(dados)
    dados_local["id"] = novo_id

    if foto_bytes:
        foto_url = upload_foto_bytes(nome_foto, foto_bytes)
        dados_local["foto_url"] = foto_url
        dados_local["tem_foto"] = True

    if "data_criacao" not in dados_local:
        dados_local["data_criacao"] = datetime_now_str()

    db["pedidos"].append(dados_local)
    LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False))
    print("💾 Pedido salvo em arquivo local com ID:", novo_id)
    return {"id": novo_id, "foto_url": foto_url}


def listar_pedidos():
    """Retorna lista de pedidos como lista de dicts."""
    # 1) Firebase
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
            print(f"📥 listar_pedidos: {len(res)} registros do Firestore.")
            return res
        except Exception as e:
            print("⚠️ Erro em listar_pedidos (Firebase). Usando fallback local.")
            print("Motivo:", repr(e))

    # 2) Fallback local
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    res = db.get("pedidos", [])
    print(f"📥 listar_pedidos: {len(res)} registros do arquivo local.")
    return res


def atualizar_status(pedido_id: str, novo_status: str):
    """Atualiza o status de um pedido."""
    # 1) Firebase
    if USE_FIREBASE and firestore_client:
        try:
            doc_ref = firestore_client.collection("pedidos").document(pedido_id)
            doc_ref.update({"status": novo_status})
            print(
                f"✅ Status do pedido {pedido_id} atualizado no Firestore para {novo_status}."
            )
            return True
        except Exception as e:
            print("⚠️ Erro em atualizar_status (Firebase). Tentando fallback local.")
            print("Motivo:", repr(e))

    # 2) Fallback local
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    alterado = False
    for p in db["pedidos"]:
        if p.get("id") == pedido_id:
            p["status"] = novo_status
            alterado = True
            break

    if alterado:
        LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False))
        print(
            f"💾 Status do pedido {pedido_id} atualizado no arquivo local para {novo_status}."
        )
    else:
        print(f"⚠️ Pedido {pedido_id} não encontrado no arquivo local.")

    return alterado


def atualizar_pedido_foto(pedido_id: str, foto_url: str):
    """Atualiza campos de foto de um pedido."""
    # 1) Firebase
    if USE_FIREBASE and firestore_client:
        try:
            doc_ref = firestore_client.collection("pedidos").document(pedido_id)
            doc_ref.update({"foto_url": foto_url, "tem_foto": True})
            print(f"✅ Foto do pedido {pedido_id} atualizada no Firestore.")
            return True
        except Exception as e:
            print("⚠️ Erro em atualizar_pedido_foto (Firebase). Tentando fallback local.")
            print("Motivo:", repr(e))

    # 2) Fallback local
    _ensure_local_storage()
    db = json.loads(LOCAL_DB.read_text())
    alterado = False
    for p in db["pedidos"]:
        if p.get("id") == pedido_id:
            p["foto_url"] = foto_url
            p["tem_foto"] = True
            alterado = True
            break

    if alterado:
        LOCAL_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False))
        print(f"💾 Foto do pedido {pedido_id} atualizada no arquivo local.")
        return True

    print(f"⚠️ Pedido {pedido_id} não encontrado ao tentar atualizar foto (local).")
    return False


def firebase_status():
    """Retorna infos básicas sobre o backend (para debug na interface)."""
    return {
        "USE_FIREBASE": USE_FIREBASE,
        "BUCKET_NAME": BUCKET_NAME,
    }
