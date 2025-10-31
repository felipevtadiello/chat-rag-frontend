import streamlit as st
import requests
import os
import pandas as pd # Adicione esta importação no topo do app.py
from dotenv import load_dotenv

API_BASE_URL = "http://127.0.0.1:8000" 
load_dotenv()

try:
    API_KEY_HEADER = { "X-Api-Key": os.getenv("API_BACKEND_KEY") }
    ADMIN_PASSWORD_LOCAL = os.getenv("ADMIN_PASSWORD")
    if not API_KEY_HEADER["X-Api-Key"] or not ADMIN_PASSWORD_LOCAL:
        raise KeyError()
except (KeyError, FileNotFoundError):
    st.error("ERRO: Verifique se o seu arquivo .env contém as chaves ADMIN_PASSWORD e API_BACKEND_KEY.")
    st.stop()


def chat_page():
    st.header("Converse com os documentos 💬")
    
    try:
        response = requests.get(f"{API_BASE_URL}/list-courses/", headers=API_KEY_HEADER)
        response.raise_for_status()
        available_courses = response.json()
        
        if not available_courses:
            st.warning("⚠️ Nenhum curso disponível ainda. Entre em contato com o administrador.")
            return
        
        if "selected_course" not in st.session_state:
            st.session_state.selected_course = available_courses[0]
        
        selected_course = st.selectbox(
            "📚 Selecione seu curso:",
            options=available_courses,
            index=available_courses.index(st.session_state.selected_course) if st.session_state.selected_course in available_courses else 0,
            key="course_selector"
        )
        
        if selected_course != st.session_state.selected_course:
            st.session_state.selected_course = selected_course
            st.session_state.chat_history = []
            st.rerun()
        
        st.info(f"🎓 Conversando com documentos do curso: **{selected_course}**")
        st.markdown("---")
        
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar cursos. Verifique se o servidor está rodando. Detalhes: {e}")
        return
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if message.get("source_documents"):
                unique_sources = set()
                for doc in message["source_documents"]:
                    unique_sources.add(doc['source'])
                
                with st.expander("Ver fontes"):
                    for source_name in sorted(list(unique_sources)):
                        st.markdown(f"📄 `{source_name}`") 

    if user_question := st.chat_input("Faça sua pergunta"):
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)
        
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/ask/",
                        headers=API_KEY_HEADER,
                        json={
                            "question": user_question, 
                            "course": st.session_state.selected_course,  
                            "chat_history": st.session_state.chat_history
                        }
                    )
                    response.raise_for_status()
                    
                    response_data = response.json()
                    answer = response_data.get("answer")
                    source_documents = response_data.get("source_documents")

                    st.markdown(answer)
                    
                    if source_documents:
                        unique_sources = set()
                        for doc in source_documents:
                            unique_sources.add(doc['source'])
                        
                        with st.expander("Ver fontes da resposta"):
                            for source_name in sorted(list(unique_sources)):
                                st.markdown(f"📄 `{source_name}`") 
                    
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": answer,
                        "source_documents": source_documents 
                    })

                except requests.exceptions.RequestException as e:
                    st.error(f"Erro de comunicação com a API: {e}")
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")

def dashboard_page():
    st.header("Dashboard de Estatísticas 📈")

    if not st.session_state.get('authenticated', False):
        st.error("🔒 Você precisa estar logado como administrador para ver esta página.")
        st.info("Acesse a página 'Administrador' para fazer login.")
        return

    st.subheader("Visão Geral")
    try:
        # Chama o novo endpoint de overview
        response = requests.get(f"{API_BASE_URL}/stats/overview", headers=API_KEY_HEADER)
        response.raise_for_status()
        stats = response.json()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Perguntas", stats.get("total_questions", 0))
        col2.metric("Total de Cursos", stats.get("total_courses", 0))
        col3.metric("Total de Vetores (Chunks)", stats.get("total_vectors", 0))

    except Exception as e:
        st.error(f"Erro ao carregar visão geral: {e}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Perguntas por Curso")
        try:
            # Chama o endpoint de perguntas por curso
            response = requests.get(f"{API_BASE_URL}/stats/questions-by-course", headers=API_KEY_HEADER)
            response.raise_for_status()
            q_by_course = response.json()

            if q_by_course:
                # Prepara dados para o gráfico de barras
                df_courses = pd.DataFrame(
                    list(q_by_course.items()), 
                    columns=['Curso', 'Total de Perguntas']
                ).set_index('Curso')
                st.bar_chart(df_courses)
            else:
                st.info("Nenhuma pergunta registrada ainda.")

        except Exception as e:
            st.error(f"Erro ao carregar perguntas por curso: {e}")

    with col2:
        st.subheader("Documentos por Curso")
        try:
            # Reutiliza o endpoint existente de listar documentos
            response = requests.get(f"{API_BASE_URL}/list-documents/", headers=API_KEY_HEADER)
            response.raise_for_status()
            docs_by_course = response.json()

            if docs_by_course:
                # Conta os documentos por curso
                doc_counts = {course: len(docs) for course, docs in docs_by_course.items()}
                df_docs = pd.DataFrame(
                    list(doc_counts.items()), 
                    columns=['Curso', 'Total de Documentos']
                ).set_index('Curso')
                st.bar_chart(df_docs)
            else:
                st.info("Nenhum documento encontrado.")
        except Exception as e:
            st.error(f"Erro ao carregar documentos por curso: {e}")

    st.markdown("---")

    st.subheader("Últimas Perguntas Registradas")
    try:
        # Chama o endpoint de perguntas recentes
        response = requests.get(f"{API_BASE_URL}/stats/recent-questions", headers=API_KEY_HEADER)
        response.raise_for_status()
        recent_questions = response.json()
        
        if recent_questions:
            # Formata para um DataFrame do Pandas para exibir bonito
            df_recent = pd.DataFrame(recent_questions)
            df_recent = df_recent[['timestamp', 'course', 'question', 'answer']]
            
            # --- INÍCIO DA CORREÇÃO DE FUSO HORÁRIO ---
            
            # 1. Converte a string de data/hora para um objeto datetime
            #    e informa que o fuso horário original é UTC.
            df_recent['timestamp'] = pd.to_datetime(df_recent['timestamp'], utc=True)
            
            # 2. Converte o fuso horário de UTC para o do Brasil (America/Sao_Paulo)
            try:
                df_recent['timestamp'] = df_recent['timestamp'].dt.tz_convert('America/Sao_Paulo')
            except Exception as e:
                # Fallback caso o fuso 'America/Sao_Paulo' não seja encontrado no sistema
                st.warning("Não foi possível converter para 'America/Sao_Paulo', exibindo em UTC.")
                df_recent['timestamp'] = df_recent['timestamp'].dt.tz_localize(None) # Remove o fuso para formatar
            
            # 3. Formata a string de data/hora já convertida
            df_recent['timestamp'] = df_recent['timestamp'].dt.strftime('%d/%m/%Y %H:%M:%S')
            
            # --- FIM DA CORREÇÃO ---

            st.dataframe(
                df_recent,
                column_config={
                    "timestamp": "Data/Hora (Local)", # Atualizado o nome da coluna
                    "course": "Curso",
                    "question": "Pergunta",
                    "answer": "Resposta"
                },
                use_container_width=True
            )
        else:
            st.info("Nenhuma pergunta registrada ainda.")
    except Exception as e:
        st.error(f"Erro ao carregar perguntas recentes: {str(e)}")
            
def admin_page():
    st.header("Área do Administrador 🔑")

    if st.session_state.get('authenticated', False):
        st.success("Acesso liberado!")
        st.markdown("---")

        try:
            response = requests.get(f"{API_BASE_URL}/list-courses/", headers=API_KEY_HEADER)
            response.raise_for_status()
            existing_courses = response.json()
        except:
            existing_courses = []

        st.subheader("📚 Documentos por Curso")
        try:
            response = requests.get(f"{API_BASE_URL}/list-documents/", headers=API_KEY_HEADER)
            response.raise_for_status()
            documents_by_course = response.json()
            
            if documents_by_course:
                for course_name, doc_list in sorted(documents_by_course.items()):
                    with st.expander(f"🎓 {course_name} ({len(doc_list)} documentos)"):
                        for doc_name in doc_list:
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.info(f"📄 {doc_name}")
                            with col2:
                                if st.button("Remover", key=f"del_{course_name}_{doc_name}", type="primary"):
                                    with st.spinner(f"Removendo {doc_name}..."):
                                        delete_response = requests.post(
                                            f"{API_BASE_URL}/delete-document/",
                                            headers=API_KEY_HEADER,
                                            json={
                                                "filename": doc_name,
                                                "course": course_name  
                                            }
                                        )
                                        if delete_response.status_code == 200:
                                            st.success(f"'{doc_name}' removido com sucesso!")
                                            st.rerun()
                                        else:
                                            st.error(f"Falha ao remover: {delete_response.json().get('detail')}")
            else:
                st.info("Nenhum documento foi processado ainda.")
        except requests.exceptions.RequestException as e:
            st.error(f"Não foi possível buscar documentos. Verifique se a API está rodando. Detalhes: {e}")
        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")

        st.markdown("---")
        st.subheader("➕ Adicionar Novos Documentos")
        
        col1, col2 = st.columns(2)
        with col1:
            course_option = st.radio(
                "Escolha uma opção:",
                ["Selecionar curso existente", "Criar novo curso"],
                key="course_option"
            )
        
        with col2:
            if course_option == "Selecionar curso existente":
                if existing_courses:
                    selected_course = st.selectbox("Curso:", existing_courses)
                else:
                    st.warning("Nenhum curso existe ainda. Crie um novo curso.")
                    selected_course = None
            else:
                selected_course = st.text_input("Nome do novo curso:")
        
        document_name = st.text_input("Nome do Documento (como ele aparecerá na lista):")
        uploaded_file = st.file_uploader("Carregue o arquivo correspondente (PDF, DOCX, TXT):", type=["pdf", "docx", "txt"])

        if st.button("Processar e Adicionar Documento"):
            if uploaded_file and document_name and selected_course:
                with st.spinner("Enviando e processando documento..."):
                    try:
                        files_and_data = {
                            'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type),
                            'doc_name': (None, document_name),
                            'course': (None, selected_course)  
                        }
                        response = requests.post(
                            f"{API_BASE_URL}/upload-and-process/", 
                            headers=API_KEY_HEADER, 
                            files=files_and_data
                        )
                        if response.status_code == 200:
                             st.success(response.json().get("message", "Documento adicionado!"))
                             st.rerun()
                        else:
                            st.error(f"Falha no processamento: {response.json().get('detail')}")
                    except Exception as e:
                        st.error(f"Ocorreu um erro inesperado: {e}")
            else:
                st.warning("Por favor, preencha todos os campos e carregue um arquivo.")

    else:
        st.warning("Você precisa de acesso de administrador para ver esta página.")
        
        password = st.text_input("Digite a senha de administrador", type="password")

        if st.button("Entrar"):
            if password == ADMIN_PASSWORD_LOCAL:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")


def main():
    st.set_page_config(page_title="Chat com Documentos por Curso", page_icon="🎓")
    
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    selected_page = st.sidebar.radio("Navegação", ["Chat com Documentos", "Administrador", "Dashboard"])
    
    if st.session_state['authenticated'] and (selected_page == "Administrador" or selected_page == "Dashboard"): # <- AJUSTE AQUI
        if st.sidebar.button("Sair (Logout)"):
            st.session_state['authenticated'] = False
            st.rerun()

    if selected_page == "Chat com Documentos":
        chat_page()
    elif selected_page == "Administrador":
        admin_page()
    elif selected_page == "Dashboard": # <- ADICIONE AQUI
        dashboard_page() #

if __name__ == '__main__':
    main()