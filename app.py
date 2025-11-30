def mostrar_formulario_adicionar_pedido():
    st.header("📝 Adicionar Novo Pedido")

    with st.form("form_adicionar_pedido"):
        col1, col2 = st.columns(2)

        with col1:
            tecnico = st.text_input("👤 Técnico *", help="Nome do técnico responsável")
            peca = st.text_input("🔧 Peça *", help="Descrição da peça necessária")
            modelo_equipamento = st.text_input("💻 Modelo do Equipamento", help="Modelo do equipamento")

        with col2:
            numero_serie = st.text_input("🔢 Número de Série", help="Número de série do equipamento")
            ordem_servico = st.text_input("📄 OS", help="Número da ordem de serviço")
            observacoes = st.text_area("📝 Observações", help="Observações adicionais")

        st.markdown("---")
        st.subheader("📸 Anexar Foto (Opcional)")

        uploaded_file = st.file_uploader(
            "Selecione uma foto do equipamento/peça",
            type=["jpg", "jpeg", "png", "gif"],
            help="Formatos suportadas: JPG, JPEG, PNG, GIF (máx. 5MB)",
        )

        foto_info = None
        if uploaded_file is not None:
            foto_info = processar_upload_foto(uploaded_file, "preview")
            if foto_info:
                st.success("📸 Foto processada com sucesso!")
                # Mostrar pré-visualização
                st.image(uploaded_file, use_container_width=True, caption="Pré-visualização da foto")

        submitted = st.form_submit_button("➕ Adicionar Pedido")

        if submitted:
            if validar_formulario(tecnico, peca):
                uploaded_bytes = foto_info["bytes"] if foto_info else None
                nome_foto = foto_info["nome"] if foto_info else None
                
                dados = {
                    "tecnico": tecnico,
                    "peca": peca,
                    "modelo": modelo_equipamento or "",
                    "numero_serie": numero_serie or "",
                    "ordem_servico": ordem_servico or "",
                    "observacoes": observacoes or "",
                    "status": "Pendente",
                }
                
                pedido_id = salvar_pedido(dados, uploaded_bytes, nome_foto)
                if pedido_id:
                    time.sleep(2)
                    st.rerun()

def mostrar_lista_pedidos():
    st.header("📋 Lista de Pedidos")

    pedidos = listar_pedidos()

    if not pedidos:
        st.info("📭 Nenhum pedido cadastrado no momento.")
        return

    st.markdown("### 📦 Pedidos cadastrados")
    st.write("")

    for pedido in pedidos:
        status_label = pedido.get("status") or "Pendente"
        emoji_status = STATUS_EMOJIS.get(status_label, "⚪")
        titulo = (
            f"{emoji_status} Pedido — Tecnico: {pedido['tecnico'] or '-'} "
            f"— Nº de Série: {pedido['numero_serie'] or '-'} — Id: {pedido['id']}"
        )

        with st.expander(titulo, expanded=False):
            st.write(f"**Data:** {pedido['data_criacao'] or '-'}")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Técnico:** {pedido['tecnico'] or '-'}")
                st.markdown(f"**Peça:** {pedido['peca'] or '-'}")
                st.markdown(f"**Modelo:** {pedido['modelo'] or '-'}")
                st.markdown(f"**ID:** {pedido['id'] or '-'}")

            with col2:
                st.markdown(f"**Nº Série:** {pedido['numero_serie'] or '-'}")
                st.markdown(f"**OS:** {pedido['ordem_servico'] or '-'}")
                st.markdown(f"**Status:** {formatar_status(status_label)}")

            if pedido["observacoes"]:
                st.markdown("**Observações:**")
                st.markdown(
                    f"<div style='background: rgba(255,255,255,0.02); "
                    f"padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.03);'>"
                    f"{pedido['observacoes']}</div>",
                    unsafe_allow_html=True,
                )

            if pedido.get("tem_foto") and pedido.get("foto_url"):
                try:
                    st.image(pedido["foto_url"], use_container_width=True, caption="Foto do equipamento/peça")
                except Exception:
                    st.warning("⚠️ Não foi possível carregar a imagem deste pedido.")

    # Estatísticas gerais
    try:
        total_pedidos = len(pedidos)
        pendentes = sum(1 for p in pedidos if p.get("status") == "Pendente")
        solicitados = sum(1 for p in pedidos if p.get("status") == "Solicitado")
        entregues = sum(1 for p in pedidos if p.get("status") == "Entregue")

        st.markdown("### 📊 Resumo dos pedidos")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total de Pedidos", total_pedidos)
        with c2:
            st.metric("🔴 Pendentes", pendentes)
        with c3:
            st.metric("🟡 Solicitados", solicitados)
        with c4:
            taxa = (entregues / total_pedidos * 100) if total_pedidos > 0 else 0
            st.metric("🟢 Entregues", f"{entregues} ({taxa:.1f}%)")
    except Exception as e:
        st.error(f"Erro ao calcular estatísticas: {e}")

def mostrar_sidebar_pedidos():
    """Sidebar APENAS para Atualizar Status"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Lista de Pedidos (para referência)")

    pedidos_sidebar = listar_pedidos()

    if not pedidos_sidebar:
        st.sidebar.info("📭 Nenhum pedido encontrado.")
        return

    for pedido in pedidos_sidebar:
        status_label = pedido.get("status") or "Pendente"
        emoji_status = STATUS_EMOJIS.get(status_label, "⚪")
        titulo_expander = (
            f"{emoji_status} {pedido['tecnico'] or '-'} - ID: {pedido['id']}"
        )

        with st.sidebar.expander(titulo_expander, expanded=False):
            st.write(f"**Peça:** {pedido['peca'] or '-'}")
            st.write(f"**Modelo:** {pedido['modelo'] or '-'}")
            st.write(f"**Nº Série:** {pedido['numero_serie'] or '-'}")
            st.write(f"**Status:** {formatar_status(status_label)}")

            if pedido.get("tem_foto") and pedido.get("foto_url"):
                try:
                    st.image(pedido["foto_url"], use_container_width=True, caption="Foto")
                except Exception:
                    st.warning("⚠️ Imagem não carregada")

def mostrar_pagina_atualizar_status():
    st.header("🔄 Atualizar Status do Pedido")
    if not st.session_state.get("autorizado", False):
        mostrar_formulario_autenticacao()
    else:
        mostrar_formulario_atualizacao_status()

def mostrar_formulario_autenticacao():
    with st.form("form_autenticacao"):
        senha = st.text_input("🔒 Digite a senha de autorização", type="password")
        submitted = st.form_submit_button("✅ Validar Senha")
        if submitted:
            if senha == SENHA_AUTORIZACAO:
                st.session_state.autorizado = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta. Tente novamente.")

def mostrar_formulario_atualizacao_status():
    with st.container():
        st.subheader("Atualizar Status do Pedido")

        pedidos = listar_pedidos()

        with st.form("form_atualizacao_status"):
            valor_busca = st.text_input("🔎 ID do Pedido *", help="Digite o ID exato do pedido (veja na sidebar)")

            opcoes_status = [f"{STATUS_EMOJIS[s]} {s}" for s in STATUS_PEDIDO]
            novo_status_formatado = st.selectbox("🔄 Novo Status", opcoes_status)
            novo_status = novo_status_formatado.split(" ", 1)[1]

            submitted = st.form_submit_button("📥 Atualizar Status")

            if submitted:
                if not valor_busca.strip():
                    st.warning("⚠️ Por favor, informe o ID do pedido.")
                    return

                if not pedidos:
                    st.error("Nenhum pedido encontrado para atualizar.")
                    return

                pedido_encontrado = None
                for pedido in pedidos:
                    if pedido.get("id") == valor_busca.strip():
                        pedido_encontrado = pedido
                        break

                if not pedido_encontrado:
                    st.error("❌ Nenhum pedido encontrado com esse ID.")
                    return

                pedido_id_real = pedido_encontrado.get("id")
                if not pedido_id_real:
                    st.error("❌ Pedido encontrado, mas sem ID válido.")
                    return

                if atualizar_status(pedido_id_real, novo_status):
                    time.sleep(2)
                    st.rerun()

    # 🔥 SIDEBAR APENAS AQUI - SOMENTE NA PÁGINA ATUALIZAR STATUS
    mostrar_sidebar_pedidos()
