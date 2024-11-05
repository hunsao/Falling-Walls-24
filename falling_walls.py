# 5-11 CANVIS JUAN

import streamlit as st
from streamlit_navigation_bar import st_navbar
from streamlit_carousel import carousel
import streamlit.components.v1 as components
from streamlit.runtime.scriptrunner import RerunException

import io
import os
import re
import json
import uuid
import base64
import random
import time
import pandas as pd
from PIL import Image
from datetime import datetime

from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, HttpRequest
from googleapiclient.errors import HttpError

particles_js = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Particles.js</title>
  <style>
  #particles-js {
    position: fixed;
    width: 100vw;
    height: 100vh;
    top: 0;
    left: 0;
    z-index: -1; /* Send the animation to the back */
  }
  .content {
    position: relative;
    z-index: 1;
    color: white;
  }
  
</style>
</head>
<body>
  <div id="particles-js"></div>
  <div class="content">
    <!-- Placeholder for Streamlit content -->
  </div>
  <script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>
  <script>
    particlesJS("particles-js", {
      "particles": {
        "number": {
          "value": 300,
          "density": {
            "enable": true,
            "value_area": 800
          }
        },
        "color": {
          "value": "#ffffff"
        },
        "shape": {
          "type": "circle",
          "stroke": {
            "width": 0,
            "color": "#000000"
          },
          "polygon": {
            "nb_sides": 5
          },
          "image": {
            "src": "img/github.svg",
            "width": 100,
            "height": 100
          }
        },
        "opacity": {
          "value": 0.5,
          "random": false,
          "anim": {
            "enable": false,
            "speed": 1,
            "opacity_min": 0.2,
            "sync": false
          }
        },
        "size": {
          "value": 2,
          "random": true,
          "anim": {
            "enable": false,
            "speed": 40,
            "size_min": 0.1,
            "sync": false
          }
        },
        "line_linked": {
          "enable": true,
          "distance": 100,
          "color": "#ffffff",
          "opacity": 0.22,
          "width": 1
        },
        "move": {
          "enable": true,
          "speed": 0.2,
          "direction": "none",
          "random": false,
          "straight": false,
          "out_mode": "out",
          "bounce": true,
          "attract": {
            "enable": false,
            "rotateX": 600,
            "rotateY": 1200
          }
        }
      },
      "interactivity": {
        "detect_on": "canvas",
        "events": {
          "onhover": {
            "enable": true,
            "mode": "grab"
          },
          "onclick": {
            "enable": true,
            "mode": "repulse"
          },
          "resize": true
        },
        "modes": {
          "grab": {
            "distance": 100,
            "line_linked": {
              "opacity": 1
            }
          },
          "bubble": {
            "distance": 400,
            "size": 2,
            "duration": 2,
            "opacity": 0.5,
            "speed": 1
          },
          "repulse": {
            "distance": 200,
            "duration": 0.4
          },
          "push": {
            "particles_nb": 2
          },
          "remove": {
            "particles_nb": 3
          }
        }
      },
      "retina_detect": true
    });
  </script>
</body>
</html>
"""

st.set_page_config(
    page_title="Falling Walls Summit '24",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed")

#GSERVICES    
def get_google_services():
    try:
        encoded_sa = os.getenv('GOOGLE_SERVICE_ACCOUNT')
        if not encoded_sa:
            raise ValueError("La variable de entorno GOOGLE_SERVICE_ACCOUNT no está configurada")

        sa_json = base64.b64decode(encoded_sa).decode('utf-8')
        sa_dict = json.loads(sa_json)

        credentials = service_account.Credentials.from_service_account_info(
            sa_dict,
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
        )

        drive_service = build('drive', 'v3', credentials=credentials)
        sheets_service = build('sheets', 'v4', credentials=credentials)

        return drive_service, sheets_service
    except Exception as e:
        st.error(f"Error al obtener los servicios de Google: {str(e)}")
        return None, None

def download_file_from_google_drive(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return fh.getvalue()
    except Exception as e:
        st.error(f"Error al descargar el archivo: {str(e)}")
        return None

def extract_folder_id(url):
    match = re.search(r'folders/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    return None

def find_images_folder_and_csv_id(service, parent_folder_name):
    try:
        results = service.files().list(
            q=f"name='{parent_folder_name}' and mimeType='application/vnd.google-apps.folder'",
            fields="nextPageToken, files(id)"
        ).execute()
        parent_folders = results.get('files', [])
        if not parent_folders:
            st.error(f"No se encontró la carpeta principal '{parent_folder_name}'.")
            return None, None
        parent_folder_id = parent_folders[0]['id']
        results = service.files().list(
            q=f"'{parent_folder_id}' in parents",
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        items = results.get('files', [])
        images_folder_id = None
        csv_file_id = None
        for item in items:
            if item['name'] == 'IMAGES' and item['mimeType'] == 'application/vnd.google-apps.folder':
                images_folder_id = item['id']
            elif item['name'].endswith('.csv') and item['mimeType'] == 'text/csv':
                csv_file_id = item['id']
        if not images_folder_id:
            st.error("No se encontró la carpeta 'IMAGES'.")
        return images_folder_id, csv_file_id
    except Exception as e:
        st.error(f"Error al buscar la carpeta 'IMAGES' y el CSV: {str(e)}")
        return None, None

#TOOLS
def generate_user_id():
    return str(uuid.uuid4())  # Unique user ID based on UUID

def display_pdf(pdf_bytes):
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')  # Encode the bytes directly
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="800" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def display_pdf_from_file(pdf_path):
    """Muestra un PDF desde un archivo local"""
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error al cargar el PDF: {str(e)}")

@st.cache_data()
def list_images_in_folder(_service, folder_id):
    try:
        results = _service.files().list(
            q=f"'{folder_id}' in parents and mimeType contains 'image/'",
            fields="nextPageToken, files(id, name)"
        ).execute()
        items = results.get('files', [])
        return items
    except Exception as e:
        st.error(f"Error al listar las imágenes: {str(e)}")
        return []

@st.cache_data()
def get_images_for_prompt_drive(_drive_service, prompt):
    images = {}
    
    neutral_folder_id = "1z8zZJQqMZDFtJG1hx7mosAt_5DlXuZU8"
    older_folder_id = "1-zseBhQMP-KeK8EoLIt6M45zTApHOGzc"

    prompt_formatted = prompt.replace(" ", "_")  
    neutral_filename = f"a_person_{prompt_formatted}.jpg"
    older_filename = f"an_older_person_{prompt_formatted}.jpg"
    
    neutral_image_query = f"'{neutral_folder_id}' in parents"
    neutral_results = _drive_service.files().list(q=neutral_image_query, fields="files(id, name)").execute()
    neutral_files = neutral_results.get('files', [])
    
    neutral_file = next((file for file in neutral_files if file['name'] == neutral_filename), None)

    older_image_query = f"'{older_folder_id}' in parents"
    older_results = _drive_service.files().list(q=older_image_query, fields="files(id, name)").execute()
    older_files = older_results.get('files', [])
    

    older_file = next((file for file in older_files if file['name'] == older_filename), None)

    if neutral_file:
        images['neutral'] = neutral_file 
    if older_file:
        images['older'] = older_file  

    if 'neutral' not in images or 'older' not in images:
        st.error(f"Error: No se encontraron imágenes para el prompt '{prompt_formatted}'. Asegúrate de que existan en Google Drive.")
        return {}

    return images

def get_images_for_prompt(prompt):
    images = {}
    
    prompt_formatted = prompt.replace(" ", "_")  

    neutral_filename = f"a_person_{prompt_formatted}.jpg"
    older_filename = f"an_older_person_{prompt_formatted}.jpg"
    
    neutral_image_path = Path(__file__).parent / "IMAGES" / "neutral" / neutral_filename
    older_image_path = Path(__file__).parent / "IMAGES" / "older" / older_filename

    if os.path.exists(neutral_image_path):
        images['neutral'] = Image.open(neutral_image_path)  # Cargar la imagen neutral
    else:
        st.warning(f"No se encontró la imagen neutral para el prompt '{prompt_formatted}'.")

    if os.path.exists(older_image_path):
        images['older'] = Image.open(older_image_path)  # Cargar la imagen older
    else:
        st.warning(f"No se encontró la imagen older para el prompt '{prompt_formatted}'.")

    if 'neutral' not in images or 'older' not in images:
        st.error(f"Error: No se encontraron ambas imágenes para el prompt '{prompt_formatted}'.")
        return {}

    return images

#SHEETS
def save_responses_to_google_sheets(sheets_service, spreadsheet_id, user_id, user_age, image_responses):
    try:
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        values = []
        
        for image_id, steps_data in image_responses.items():
            image_path = Path(image_id)
            image_type = "older" if "older" in str(image_path) else "neutral"
            prompt = image_path.name.replace("a_person_", "").replace("an_older_person_", "").replace(".jpg", "")
            
            for step_key, step_data in steps_data.items():
                tags_str = "|".join(step_data.get("Tags", []))
                
                words_str = "|".join(step_data.get("Words", []))
                
                # Crear fila con todos los datos
                row = [
                    user_id,                # ID único del usuario
                    current_datetime,       # Timestamp
                    user_age,              # Edad del usuario
                    prompt,                # Prompt utilizado
                    image_type,            # Tipo de imagen (older/neutral)
                    step_key,              # Paso del cuestionario
                    tags_str,              # Tags seleccionados
                    words_str              # Palabras adicionales
                ]
                values.append(row)
        
        body = {
            'values': values
        }
        
        # Enviar datos a Google Sheets
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A1', 
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return True, "Responses saved successfully!"
        
    except Exception as e:
        return False, f"Error saving to Google Sheets: {str(e)}"

def initialize_google_sheet(sheets_service, spreadsheet_id):
    try:
        # Definir los encabezados de las columnas
        headers = [
            ['user_id', 'timestamp', 'user_age', 'prompt', 'image_type', 'step', 'tags', 'words']
        ]
        
        # Verificar si la hoja ya tiene encabezados
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A1:H1'
        ).execute()
        
        if 'values' not in result:
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Sheet1!A1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            st.write("Sheet headers initialized successfully")
            
        return True
    except Exception as e:
        st.error(f"Error initializing Google Sheet: {str(e)}")
        return False

#SENSE DRIVE
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()
    
def save_image_base64(image_path, output_file):
    encoded = image_to_base64(image_path)
    with open(output_file, 'w') as f:
        f.write(encoded)

class LocalImageHandler:
    def __init__(self):
        self.base_folder = Path(__file__).parent / "IMAGES"  # Definir la ruta base de la carpeta IMAGES
        self.prompts = [
            "traveling",
            "eating",
            "planning shopping",
            "taking a break",
            "participating in sports events",
            "receiving personal care services",
            "using computers",
            "in the living room",
            "at work",
            "in a job fair",
            "handling home care tasks",
            "managing the household",
            "moving to a new location",
            "in a study group",
            "in a party",
            "going for walks",
            "heating the dwelling"
        ]
        
    def get_image_path(self, prompt, image_type):
        """
        Obtiene la ruta de la imagen basada en el prompt y tipo.
        `image_type` puede ser 'neutral' o 'older'.
        """
        prefix = "a_person_" if image_type == 'neutral' else "an_older_person_"
        # Convertir el prompt a formato de nombre de archivo
        formatted_prompt = prompt.replace(" ", "_")
        filename = f"{prefix}{formatted_prompt}.jpg"
        image_path = self.base_folder / image_type / filename
        return image_path if image_path.is_file() else None

    def get_images_for_prompt(self, prompt):
        """Obtiene las imágenes neutral y older para un prompt específico si existen."""
        images = {
            'neutral': {
                'path': self.get_image_path(prompt, 'neutral'),
                'name': f"Person {prompt}"
            },
            'older': {
                'path': self.get_image_path(prompt, 'older'),
                'name': f"Older person {prompt}"
            }
        }
        
        # Filtrar imágenes que no se encuentran
        missing_images = [key for key, val in images.items() if val['path'] is None]
        if missing_images:
            missing_str = ", ".join(missing_images)
            raise FileNotFoundError(f"Error: No se encontraron imágenes para: {missing_str}. Prompt: '{prompt}'.")

        return images

    def get_random_prompt(self):
        """Obtiene un prompt aleatorio de la lista"""
        return random.choice(self.prompts)

def initialize_session_state():
    if 'page' not in st.session_state:
        st.session_state.page = 'landing' #intro
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'image_responses' not in st.session_state:
        st.session_state.image_responses = {}
    if 'image_handler' not in st.session_state:
        st.session_state.image_handler = LocalImageHandler()
    if 'current_prompt' not in st.session_state:
        st.session_state.current_prompt = st.session_state.image_handler.get_random_prompt()
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())  # Generar ID único
    if 'user_age' not in st.session_state:
        st.session_state.user_age = None

@st.fragment
def tag_button_fragment(image_id, step_key, tags):
    # Initialize a session state entry for the selected tags
    if image_id not in st.session_state.image_responses:
        st.session_state.image_responses[image_id] = {}
    if step_key not in st.session_state.image_responses[image_id]:
        st.session_state.image_responses[image_id][step_key] = {"Tags": [], "Comments": "", "Words": []}
    
    selected_tags = st.session_state.image_responses[image_id][step_key]["Tags"]
    btn_cols = st.columns(2)

    # Define button styles for selected/unselected states
    st.markdown("""
    <style>
    div.stButton > button:focus, div.stButton > button:active {
        background-color: #1a5d9c;
        color: white !important;
        border: none !important;
        outline: none;
        box-shadow: none !important;
    }
    div.stButton > button {
        display: block;
        margin: 0 auto;
        font-size: 20px;
        padding: 10px 40px;
        background-color: #2986cc;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
    }
    div.stButton > button:hover {
        background-color: #1a5d9c;
        color: #F0FFFF !important;
        border: none;
    }
    .stButton > button[kind=secondary] {
        background-color: #28a745cc;
        color: white;
        border: 1px solid white;
    }
    </style>
    """, unsafe_allow_html=True)

    # Create tag buttons in two columns
    for j, tag in enumerate(tags):
        with btn_cols[j % 2]:
            button_key = f"tag_button_{step_key}_{image_id}_{j}"
            is_selected = tag in selected_tags
            if st.button(tag, key=button_key, use_container_width=True, type="secondary" if is_selected else "primary"):
                if is_selected:
                    selected_tags.remove(tag)
                else:
                    selected_tags.append(tag)
                st.session_state.image_responses[image_id][step_key]["Tags"] = selected_tags
                st.rerun(scope="fragment")

prompts = [
    "traveling",
    "eating",
    "planning shopping",
    "taking a break",
    "participating in sports events",
    "receiving personal care services",
    "using computers",
    "in the living room",
    "at work",
    "in a job fair",
    "handling home care tasks",
    "managing the household",
    "moving to a new location",
    "in a study group",
    "in a party",
    "going for walks",
    "heating the dwelling"]

#MAIN
def main():
    initialize_session_state()

    intro_image = Path(__file__).parent / "IMAGES" / "Imagen_intro.png"
    pdf_path = Path(__file__).parent / "TERMS" / "TERMS.pdf"

    drive_service, sheets_service = get_google_services()

    if not drive_service or not sheets_service:
        st.error("No se pudieron obtener los servicios de Google.")
        return

    drive_url = "https://drive.google.com/drive/u/0/folders/1GwfHfrsEH7jGisVdeUdGJOPG7TlbUyl8"
    parent_folder_name = "10_14_FALLING_WALLS"
    spreadsheet_id = "1kkpKzDOkwJ58vgvp0IIAhS-yOSJxId8VJ4Bjxj7MmJk"

    parent_folder_id = extract_folder_id(drive_url)

    if 'page' not in st.session_state:
        st.session_state.page = 'landing' 

    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'user_id' not in st.session_state:
        st.session_state.user_id = ''
    if 'random_images' not in st.session_state:
        st.session_state.random_images = []
    if 'image_responses' not in st.session_state:
        st.session_state.image_responses = {}
    if 'all_files' not in st.session_state:
        st.session_state.all_files = []


    if parent_folder_id:
        images_folder_id, csv_file_id = find_images_folder_and_csv_id(drive_service, parent_folder_name)
        if images_folder_id: #and csv_file_id:
            current_prompt = random.choice(prompts)  
            images = get_images_for_prompt(current_prompt)  
            if 'neutral' in images and 'older' in images:
                st.session_state.random_images = [images['neutral'], images['older']]
            else:
                st.error("No se encontraron imágenes adecuadas para el prompt.")
            
            if not st.session_state.all_files: 
                results = drive_service.files().list(
                    q=f"'{parent_folder_id}' in parents",  # Query for files in the parent folder
                    fields="nextPageToken, files(id, name, mimeType)"
                ).execute()
                st.session_state.all_files = results.get('files', [])                
        else:
            st.error("No se pudieron encontrar las imágenes")  #o el archivo CSV.
    else:
        st.error("Could not obtain the parent folder ID.")

#Landing
    if st.session_state.page == 'landing':
        components.html(particles_js, height=0, scrolling=False)

        st.markdown(
            """
            <!-- Estilos personalizados para el componente -->
            <style>
                /* Eliminar padding superior en el elemento raíz */
                #root > div:nth-child(1) > div > div > div > div > section > div {
                    padding-top: 0rem;
                }
            </style>

            <!-- Título centrado -->
            <h1 style='text-align: center;'>How is age depicted in AI?</h1>
            """, 
            unsafe_allow_html=True
        )

        video_path = Path(__file__).parent / "IMAGES" / "video.mp4"
        video_file = open(video_path, "rb")
        video_bytes = video_file.read()

        st.markdown(
        """
        <div style="max-width: 800px; margin: 0 auto;">
            <video width="100%" autoplay loop muted>
                <source src="data:video/mp4;base64,{base64_video}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
        """.format(base64_video=base64.b64encode(video_bytes).decode('utf-8')),
        unsafe_allow_html=True)

      
        #st.video(video_bytes, start_time=0, end_time=None, loop=True, autoplay=True, muted=True)

        # st.markdown("""
        # <center>
        # <h3>Ready to play?</h3>
        # <p style="text-align: justify;">
        # Tag images to reveal how Midjourney portrays emotions, roles, and autonomy across ages. Your insights fuel the “Ageism in AI” Project, funded by the Volkswagen Foundation.
        # </p>
        # </center>
        # """, unsafe_allow_html=True)

        st.markdown("""
        <center>
        <h3>Ready to play?</h3>
        </center>
        """, unsafe_allow_html=True)

        st.markdown("""
        <center>
        <h5>Tag images to reveal how Midjourney portrays emotions, roles, and autonomy across ages.</h5>
        </center>
        """, unsafe_allow_html=True)

        st.markdown("""
        <center>
        <h6>Your insights fuel the “Ageism in AI” Project, funded by the Volkswagen Foundation.</h6>
        </center>
        """, unsafe_allow_html=True)


        st.markdown("""
        <style>
        div.stButton > button:focus, /* Añadido :focus */
        div.stButton > button:active {
            background-color: #1a5d9c;
            color: white !important; /* Añadido !important */
            border: none !important;
            outline: none; /* Evita el contorno azul por defecto */
            box-shadow: none !important;
        }

        div.stButton > button {  /* Mayor especificidad para :hover */
            display: block;
            margin: 0 auto;
            font-size: 20px;
            padding: 10px 40px;
            background-color: #2986cc;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;

        }
        div.stButton > button:hover {
            background-color: #1a5d9c;
            color: #F0FFFF !important; /* color al pasar el cursor  */
            border: none;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if st.button("Start", key="intro_button", use_container_width=False):
            st.session_state.page = 'prompt1'
            st.rerun()

#Prompt1
    elif st.session_state.page == 'prompt1':
        if 'current_prompt' not in st.session_state:
            st.session_state.current_prompt = random.choice(prompts) 

        current_prompt = st.session_state.current_prompt  

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            #st.markdown(f"<h2 style='text-align: center;'>STEP {st.session_state.current_step} of 3</h2>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: center;'>How does AI depict individuals {current_prompt.replace('_', ' ')} based on their age?</h2>", unsafe_allow_html=True)
            
            st.markdown("""
            <style>
            div.stButton > button:focus, /* Añadido :focus */
            div.stButton > button:active {
                background-color: #1a5d9c;
                color: white !important; /* Añadido !important */
                border: none !important;
                outline: none; /* Evita el contorno azul por defecto */
                box-shadow: none !important;
            }

            div.stButton > button {  /* Mayor especificidad para :hover */
                display: block;
                margin: 0 auto;
                font-size: 20px;
                padding: 10px 40px;
                background-color: #2986cc;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;

            }
            div.stButton > button:hover {
                background-color: #1a5d9c;
                color: #F0FFFF !important; /* color al pasar el cursor  */
                border: none;
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown("")

            if st.button("GO"):
                st.session_state.page = 'questionnaire'
                st.rerun()

        components.html(particles_js, height=350,width=1050, scrolling=False)

#QUESTIONNAIRE
    elif st.session_state.page == 'questionnaire':
        st.markdown(
        """
        <style>
        #root > div:nth-child(1) > div > div > div > div > section > div {
            padding-top: 0rem;
        }
        /* Estilos más específicos para centrar las imágenes */
        [data-testid="column"] > div:first-child {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        [data-testid="column"] > div:first-child > div {
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        /* Asegurar que el caption también está centrado */
        [data-testid="caption"] {
            text-align: center !important;
        }
        </style>
        """, 
        unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 2, 1.4])

        # Obtener imágenes para el prompt actual
        current_prompt = st.session_state.current_prompt   
        images = st.session_state.image_handler.get_images_for_prompt(current_prompt)

        for i, (key, image_data) in enumerate(images.items()):
                    column = col1 if i == 0 else col2
                    with column:
                        if image_data['path'].exists():
                            image = Image.open(image_data['path'])
                            # st.image(image, width=400,use_column_width=True,caption=f"Prompt: {image_data['name']}")
                            st.image(image,width=400,use_column_width=True)
                            caption_text = image_data['name'].replace("Older person", "<b>Older person</b>").replace("Person", "<b>Person</b>")
                            full_caption = f"<div style='text-align: center;'>Prompt: {caption_text}</div>"
                            st.markdown(full_caption, unsafe_allow_html=True)
                        else:
                            st.error(f"Image not found: {image_data['path']}")
                        
                        image_id = str(image_data['path'])
                        step_key = f"Step {st.session_state.current_step}"

                        if image_id not in st.session_state.image_responses:
                            st.session_state.image_responses[image_id] = {}

                        if step_key not in st.session_state.image_responses[image_id]:
                            st.session_state.image_responses[image_id][step_key] = {"Tags": [], "Comments": "", "Words": []}

                        tags = {
                            1: ["Vulnerable", "Strong", "Hallucinated", "Realistic", "Passive", "Active",
                                "Weak", "Capable", "Relaxed", "Worried"],
                            2: ["Vulnerable", "Strong", "Hallucinated", "Realistic", "Passive", "Active",
                                "Weak", "Capable", "Relaxed", "Worried"],
                            3: ["Vulnerable", "Strong", "Hallucinated", "Realistic", "Passive", "Active",
                                "Weak", "Capable", "Relaxed", "Worried"],
                        }

                        # Crear el multiselect encima de los botones
                        selected_tags = st.session_state.image_responses[image_id][step_key]["Tags"]

                        selected = selected_tags #AFEGIT PER LO D'ADALT

                        st.session_state.image_responses[image_id][step_key]["Tags"] = selected

                        btn_cols = st.columns(2)

                        st.markdown("""
                        <style>
                        div.stButton > button:focus, /* Añadido :focus */
                        div.stButton > button:active {
                            background-color: #1a5d9c;
                            color: white !important; /* Añadido !important */
                            border: none !important;
                            outline: none; /* Evita el contorno azul por defecto */
                            box-shadow: none !important;
                        }

                        div.stButton > button {  /* Mayor especificidad para :hover */
                            display: block;
                            margin: 0 auto;
                            font-size: 20px;
                            padding: 10px 40px;
                            background-color: #2986cc;
                            color: white;
                            border: none;
                            border-radius: 8px;
                            cursor: pointer;

                        }
                        div.stButton > button:hover {
                            background-color: #1a5d9c;
                            color: #F0FFFF !important; /* color al pasar el cursor  */
                            border: none;
                        }
                        /* Estilo para botones seleccionados */
                        .stButton > button[kind=secondary] {
                            background-color: #28a745cc;
                            color: white;
                            border: 1px solid white;
                        }
                                    
                        button[kind=secondary]
                        </style>
                        """, unsafe_allow_html=True)

                        current_step = st.session_state.current_step
                        tag_button_fragment(image_id, step_key, tags[current_step])

                        # Formulario individual para cada imagen
                        form = st.form(key=f'form_step{st.session_state.current_step}_img{i}')
                        comment = form.text_input(
                            label='Describe the image in other words (20 characters):',
                            placeholder="Write here"
                        )
                        submit_button = form.form_submit_button(label='Submit')

                        if submit_button:
                            if comment:
                                if "Words" not in st.session_state.image_responses[image_id][step_key]:
                                    st.session_state.image_responses[image_id][step_key]["Words"] = []
                    
                                words_list = st.session_state.image_responses[image_id][step_key]["Words"]
                                if comment not in words_list:
                                    words_list.append(comment)
                                    st.session_state.image_responses[image_id][step_key]["Words"] = words_list

                        words_list = st.session_state.image_responses[image_id][step_key].get("Words", [])
                        st.multiselect(
                            "Submitted Words",  
                            options=words_list,
                            key=f"words_multiselect_{image_id}_{st.session_state.current_step}", 
                            default=words_list
                        )

        with col3:
            components.html(particles_js, height=880,width=250, scrolling=False)

            st.markdown(f"<h4 style='text-align: center;'> Step {st.session_state.current_step} of 3</h4>", unsafe_allow_html=True)
            
            button_label = "Next Images" if st.session_state.current_step < 3 else "Finish"
            
            if st.button(button_label, key=f"next_button_step{st.session_state.current_step}_unique", use_container_width=True):
                if st.session_state.current_step < 3:
                    st.session_state.current_step += 1
                    st.session_state.current_prompt = random.choice(prompts)  #
                else:
                    st.session_state.page = 'age_input'  
                    st.session_state.current_step = 1  
                    st.session_state.current_prompt = random.choice(prompts)  

                if st.session_state.page != 'age_input':  
                    st.session_state.page = 'prompt1'
                st.rerun()

#EDAT
    elif st.session_state.page == 'age_input':
        st.markdown("<h2 style='text-align: center;'>(Optional) How old are you? </h2>", unsafe_allow_html=True)
        #st.write("")
        #st.markdown("<h5 style='text-align: left;'>Enter your age(optional)</h5>", unsafe_allow_html=True)
        #user_age = st.text_input("", value="", placeholder="...")  # Campo de texto para la edad (opcional)
        user_age = st.number_input("", step=1)  # Campo de texto para la edad (opcional)

        st.markdown("""
        <style>
        div.stButton > button:focus, /* Añadido :focus */
        div.stButton > button:active {
            background-color: #1a5d9c;
            color: white !important; /* Añadido !important */
            border: none !important;
            outline: none; /* Evita el contorno azul por defecto */
            box-shadow: none !important;
        }

        div.stButton > button {  /* Mayor especificidad para :hover */
            display: block;
            margin: 0 auto;
            font-size: 20px;
            padding: 10px 40px;
            background-color: #2986cc;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;

        }
        div.stButton > button:hover {
            background-color: #1a5d9c;
            color: #F0FFFF !important; /* color al pasar el cursor  */
            border: none;
        }
        </style>
        """, unsafe_allow_html=True)

        # Botón de continuar
        if st.button("Submit"):
            st.session_state.user_age = user_age  # Guardar la edad (aunque puede estar en blanco)
            st.session_state.page = 'end'  

        # Botón de omitir
        if st.button("Skip this question"):
            st.session_state.user_age = None  # No guardar la edad
            st.session_state.page = 'end' 
            st.rerun()

#END
    elif st.session_state.page == 'end':
        try:
            # Mensaje de agradecimiento
            st.title("Thanks for participating! 😊")
            st.balloons()
            st.write("We appreciate your time and effort in completing this questionnaire.")
            st.write("How do others tag images? Check out the TV screen to see the most popular results.")
                 
            # Preparar y enviar datos a Google Sheets solo si aún no se han guardado
            if not st.session_state.get('data_saved', False):
                # Solo se ejecuta una vez al finalizar el cuestionario
                current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                values = []

                for image_id, steps_data in st.session_state.image_responses.items():
                    image_path = Path(image_id)
                    image_type = "older" if "older" in str(image_path) else "neutral"
                    prompt = image_path.name.replace("a_person_", "").replace("an_older_person_", "").replace(".jpg", "")

                    for step_key, step_data in steps_data.items():
                        tags_str = "|".join(step_data.get("Tags", []))
                        words_str = "|".join(step_data.get("Words", []))

                        row = [
                            st.session_state.user_id,
                            current_datetime,
                            st.session_state.get('user_age', ''),
                            prompt,
                            image_type,
                            step_key,
                            tags_str,
                            words_str
                        ]
                        values.append(row)

                body = {'values': values}

                # Enviar datos a Google Sheets
                result = sheets_service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range='Sheet1!A1',
                    valueInputOption='USER_ENTERED',
                    insertDataOption='INSERT_ROWS',
                    body=body
                ).execute()

                st.session_state.data_saved = True
                #st.success("✅ Data successfully saved to Google Sheets!")
        
        except Exception as e:
            st.error(f"❌ Error saving to Google Sheets: {str(e)}")
            st.write("Error details:", str(e))
            st.write("Please contact support with the error message above.")
        
        st.markdown("""
        <style>
        div.stButton > button:focus, /* Añadido :focus */
        div.stButton > button:active {
            background-color: #1a5d9c;
            color: white !important; /* Añadido !important */
            border: none !important;
            outline: none; /* Evita el contorno azul por defecto */
            box-shadow: none !important;
        }

        div.stButton > button {  /* Mayor especificidad para :hover */
            display: block;
            margin: 0 auto;
            font-size: 20px;
            padding: 10px 40px;
            background-color: #2986cc;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;

        }
        div.stButton > button:hover {
            background-color: #1a5d9c;
            color: #F0FFFF !important; /* color al pasar el cursor  */
            border: none;
        }
        </style>
        """, unsafe_allow_html=True)

        # if st.button("Start new questionnaire"):
        #     st.session_state.current_step = 1
        #     st.session_state.image_responses = {}
        #     st.session_state.page = 'landing'
        #     st.session_state.user_id = str(uuid.uuid4())
        #     st.session_state.user_age = None
        #     st.session_state.review_mode = False
        #     st.session_state.data_saved = False
        #     st.rerun()

        # Redirigir automáticamente a la página de inicio
        st.session_state.current_step = 1
        st.session_state.image_responses = {}
        st.session_state.page = 'landing'
        st.session_state.user_id = str(uuid.uuid4())
        st.session_state.user_age = None
        st.session_state.review_mode = False
        st.session_state.data_saved = False

        time.sleep(10)

        st.rerun()

if __name__ == "__main__":
    main()
