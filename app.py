import streamlit as st
import requests
import os
import pandas as pd
from dotenv import load_dotenv

st.set_page_config(page_title="Sistema Acadêmico RAG", page_icon="🎓", layout="wide")

load_dotenv()
API_BASE_URL = "https://api-rag-6qqf.onrender.com"

if "token" not in st.session_state:
    st.session_state.token = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Sistema Acadêmico")
        
        tab_login, tab_register = st.tabs(["Entrar", "Criar Conta (Aluno)"])
        
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Usuário")
                password = st.text_input("Senha", type="password")
                submit_login = st.form_submit_button("Entrar", type="primary")
                
                if submit_login:
                    try:
                        with st.spinner("Autenticando..."):
                            response = requests.post(
                                f"{API_BASE_URL}/token", 
                                data={"username": username, "password": password}
                            )
                            if response.status_code == 200:
                                data = response.json()
                                st.session_state.token = data["access_token"]
                                st.session_state.is_admin = data["is_admin"]
                                st.success("Login realizado!")
                                st.rerun()
                            else:
                                st.error("Usuário ou senha incorretos.")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")

        with tab_register:
            st.info("Crie sua conta para acessar o chat. Seu perfil será de Aluno.")
            with st.form("register_form"):
                new_user = st.text_input("Novo Usuário")
                new_pass = st.text_input("Nova Senha", type="password")
                submit_register = st.form_submit_button("Criar Conta")
                
                if submit_register:
                    if new_user and new_pass:
                        try:
                            with st.spinner("Criando conta..."):
                                response = requests.post(
                                    f"{API_BASE_URL}/register", 
                                    data={"username": new_user, "password": new_pass}
                                )
                                if response.status_code == 200:
                                    st.success("Conta criada! Volte para a aba 'Entrar' e faça login.")
                                else:
                                    st.error(f"Erro: {response.json().get('detail')}")
                        except Exception as e:
                            st.error(f"Erro: {e}")
                    else:
                        st.warning("Preencha todos os campos.")

def chat_page():
    st.header("Converse com os documentos 💬")
    
    try:
        response = requests.get(f"{API_BASE_URL}/list-courses/", headers=get_headers())
        
        if response.status_code == 401:
            st.session_state.token = None
            st.rerun()
            
        response.raise_for_status()
        available_courses = response.json()
        
        if not available_courses:
            st.warning("⚠️ Nenhum curso disponível ainda.")
            return
        
        if "selected_course" not in st.session_state:
            st.session_state.selected_course = available_courses[0]
        
        idx = 0
        if st.session_state.selected_course in available_courses:
            idx = available_courses.index(st.session_state.selected_course)

        selected_course = st.selectbox(
            "Selecione seu curso:",
            options=available_courses,
            index=idx,
            key="course_selector"
        )
        
        if selected_course != st.session_state.selected_course:
            st.session_state.selected_course = selected_course
            st.session_state.chat_history = []
            st.rerun()
        
        st.info(f"Conversando com documentos do curso: **{selected_course}**")
        st.markdown("---")
        
    except Exception as e:
        st.error(f"Erro ao carregar cursos: {e}")
        return
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("source_documents"):
                unique_sources = set(doc['source'] for doc in message["source_documents"])
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
                        headers=get_headers(), 
                        json={
                            "question": user_question, 
                            "course": st.session_state.selected_course,  
                            "chat_history": st.session_state.chat_history
                        }
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        answer = response_data.get("answer")
                        source_documents = response_data.get("source_documents")

                        st.markdown(answer)
                        
                        if source_documents:
                            unique_sources = set(doc['source'] for doc in source_documents)
                            with st.expander("Ver fontes da resposta"):
                                for source_name in sorted(list(unique_sources)):
                                    st.markdown(f"📄 `{source_name}`")
                        
                        st.session_state.chat_history.append({
                            "role": "assistant", 
                            "content": answer,
                            "source_documents": source_documents 
                        })
                    elif response.status_code == 401:
                        st.error("Sessão expirada.")
                        st.session_state.token = None
                        st.rerun()
                    else:
                        st.error(f"Erro: {response.text}")

                except Exception as e:
                    st.error(f"Erro: {e}")

def admin_page():
    st.header("Área do Administrador 🔑")

    if not st.session_state.is_admin:
        st.error("🔒 Acesso Negado. Você não é administrador.")
        return

    st.success("Acesso liberado!")
    st.markdown("---")

    try:
        response = requests.get(f"{API_BASE_URL}/list-courses/", headers=get_headers())
        if response.status_code == 200:
            existing_courses = response.json()
        else:
            existing_courses = []
    except:
        existing_courses = []

    st.subheader("Documentos por Curso")
    try:
        response = requests.get(f"{API_BASE_URL}/list-documents/", headers=get_headers())
        
        if response.status_code == 200:
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
                                            headers=get_headers(), 
                                            json={
                                                "filename": doc_name,
                                                "course": course_name  
                                            }
                                        )
                                        if delete_response.status_code == 200:
                                            st.success(f"'{doc_name}' removido com sucesso!")
                                            st.rerun()
                                        else:
                                            st.error(f"Falha: {delete_response.json().get('detail')}")
            else:
                st.info("Nenhum documento processado ainda.")
        else:
            st.error("Erro ao carregar documentos.")
            
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")

    st.markdown("---")
    
    st.subheader("Adicionar Novos Documentos")
    
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
    uploaded_file = st.file_uploader("Carregue o arquivo (PDF):", type=["pdf"])

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
                        headers=get_headers(), 
                        files=files_and_data
                    )
                    if response.status_code == 200:
                         st.success(response.json().get("message", "Documento adicionado!"))
                         st.rerun()
                    elif response.status_code == 403:
                        st.error("Acesso Negado: Apenas administradores podem fazer upload.")
                    else:
                        st.error(f"Falha: {response.json().get('detail')}")
                except Exception as e:
                    st.error(f"Erro: {e}")
        else:
            st.warning("Por favor, preencha todos os campos.")

def dashboard_page():
    st.header("Dashboard de Estatísticas 📈")

    if not st.session_state.is_admin:
        st.error("🔒 Acesso restrito a administradores.")
        return

    st.subheader("Visão Geral")
    try:
        response = requests.get(f"{API_BASE_URL}/stats/overview", headers=get_headers())
        if response.status_code == 200:
            stats = response.json()
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Perguntas", stats.get("total_questions", 0))
            col2.metric("Total de Cursos", stats.get("total_courses", 0))
            col3.metric("Total de Vetores (Chunks)", stats.get("total_vectors", 0))
        else:
            st.error("Erro ao carregar stats.")

    except Exception as e:
        st.error(f"Erro: {e}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Perguntas por Curso")
        try:
            response = requests.get(f"{API_BASE_URL}/stats/questions-by-course", headers=get_headers())
            if response.status_code == 200:
                q_by_course = response.json()
                if q_by_course:
                    df_courses = pd.DataFrame(
                        list(q_by_course.items()), 
                        columns=['Curso', 'Total de Perguntas']
                    ).set_index('Curso')
                    st.bar_chart(df_courses)
                else:
                    st.info("Sem dados.")
        except Exception as e:
            st.error(f"Erro: {e}")

    with col2:
        st.subheader("Documentos por Curso")
        try:
            response = requests.get(f"{API_BASE_URL}/list-documents/", headers=get_headers())
            if response.status_code == 200:
                docs_by_course = response.json()
                if docs_by_course:
                    doc_counts = {course: len(docs) for course, docs in docs_by_course.items()}
                    df_docs = pd.DataFrame(
                        list(doc_counts.items()), 
                        columns=['Curso', 'Total de Documentos']
                    ).set_index('Curso')
                    st.bar_chart(df_docs)
                else:
                    st.info("Sem dados.")
        except Exception as e:
            st.error(f"Erro: {e}")

    st.markdown("---")

    st.subheader("Últimas Perguntas Registradas")
    try:
        response = requests.get(f"{API_BASE_URL}/stats/recent-questions", headers=get_headers())
        if response.status_code == 200:
            recent_questions = response.json()
            
            if recent_questions:
                df_recent = pd.DataFrame(recent_questions)
                
                if 'timestamp' in df_recent.columns:
                    df_recent = df_recent[['timestamp', 'course', 'question', 'answer']]
                    
                    df_recent['timestamp'] = pd.to_datetime(df_recent['timestamp'])
                    df_recent['timestamp'] = df_recent['timestamp'].dt.strftime('%d/%m/%Y %H:%M:%S')

                st.dataframe(
                    df_recent,
                    column_config={
                        "timestamp": "Data/Hora (Brasília)", 
                        "course": "Curso",
                        "question": "Pergunta",
                        "answer": "Resposta"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma pergunta registrada ainda.")
    except Exception as e:
        st.error(f"Erro: {str(e)}")

def main():
    if not st.session_state.token:
        login_page()
    else:
        menu_options = ["Chat com Documentos"]
        
        if st.session_state.is_admin:
            menu_options.extend(["Administrador", "Dashboard"])
            
        selected_page = st.sidebar.radio("Navegação", menu_options)
        
        st.sidebar.markdown("---")
        if st.sidebar.button("Sair (Logout)"):
            st.session_state.token = None
            st.session_state.is_admin = False
            st.session_state.chat_history = []
            st.rerun()

        if selected_page == "Chat com Documentos":
            chat_page()
        elif selected_page == "Administrador":
            admin_page()
        elif selected_page == "Dashboard":
            dashboard_page() 

if __name__ == '__main__':
    main()