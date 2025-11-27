# firebase_funcoes.py
import os
import uuid
import json
from pathlib import Path
import base64
from datetime import datetime

import streamlit as st

# -----------------------------------------
# 🔥 CARREGAR CREDENCIAIS DO STREAMLIT SECRETS
# -----------------------------------------
FIREBASE_CREDS_JSON = st.secrets["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
FIREBASE_BUCKET = st.secrets["FIREBASE_BUCKET"]

creds_dict = json.loads(FIREBASE_CREDS_JSON)

from google.oauth2 import service_account
from google.cloud import storage, firestore

credentials = service_account.Credentials.from_service_account_info(creds_dict)

project_id = creds_dict["project_id"]

storage_client = storage.Client(project=project_id, credentials=credentials)
firestore_client = firestore.Client(project=project_id, credentials=credentials)


# -----------------------------------------
# 🔥 FUNÇÃO DE UPLOAD
# -----------------------------------------
def upload_foto_bytes(nome_arquivo, bytes_data, pasta="fotos"):
    bucket = storage_client.bucket(FIREBASE_BUCKET)

    blob_name = f"{pasta}/{uuid.uuid4().hex}_{nome_arquivo}"
    blob = bucket.blob(blob_name)

    blob.upload_from_string(bytes_data, content_type="image/jpeg")
    blob.make_public()

    return blob.public_url


# -----------------------------------------
# 🔥 SALVAR PEDIDO
# -----------------------------------------
def salvar_pedido(dados: dict, foto_bytes: bytes = None, nome_foto: str = None):
    doc_ref = firestore_client.collection("pedidos").document()

    if foto_bytes:
        foto_url = upload_foto_bytes(nome_foto, foto_bytes)
        dados["foto_url"] = foto_url
        dados["tem_foto"] = True
    else:
        dados["tem_foto"] = False

    if "data_criacao" not in dados:
        dados["data_criacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    doc_ref.set(dados)

    return doc_ref.id


# -----------------------------------------
# 🔥 LISTAR PEDIDOS
# -----------------------------------------
def listar_pedidos():
    docs = firestore_client.collection("pedidos") \
        .order_by("data_criacao", direction=firestore.Query.DESCENDING) \
        .stream()

    lista = []
    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        lista.append(item)

    return lista


# -----------------------------------------
# 🔥 ATUALIZAR STATUS
# -----------------------------------------
def atualizar_status(pedido_id, novo_status):
    doc_ref = firestore_client.collection("pedidos").document(pedido_id)
    doc_ref.update({"status": novo_status})
    return True


# -----------------------------------------
# 🔥 UTILS
# -----------------------------------------
def dataurl_para_bytes(data_url):
    header, encoded = data_url.split(",", 1)
    return base64.b64decode(encoded)
