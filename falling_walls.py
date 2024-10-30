import streamlit as st
from streamlit_navigation_bar import st_navbar
from streamlit_carousel import carousel
import streamlit.components.v1 as components

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

#GOOGLE SERVICES    
def get_google_services():
    try:
        # Obtener la cadena codificada de la variable de entorno
        encoded_sa = os.getenv('GOOGLE_SERVICE_ACCOUNT')
        if not encoded_sa:
            raise ValueError("La variable de entorno GOOGLE_SERVICE_ACCOUNT no está configurada")

        # Decodificar la cadena
        sa_json = base64.b64decode(encoded_sa).decode('utf-8')

        # Crear un diccionario a partir de la cadena JSON
        sa_dict = json.loads(sa_json)

        # Crear las credenciales
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
        #if not csv_file_id:
            #st.error("No se encontró el archivo CSV.")
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
    
    # Folder IDs for "neutral" and "older"
    neutral_folder_id = "1z8zZJQqMZDFtJG1hx7mosAt_5DlXuZU8"
    older_folder_id = "1-zseBhQMP-KeK8EoLIt6M45zTApHOGzc"

    # Adjust the prompt name for file search
    prompt_formatted = prompt.replace(" ", "_")  # Replace spaces with underscores for filenames

    # Define expected filenames for neutral and older images
    neutral_filename = f"a_person_{prompt_formatted}.jpg"
    older_filename = f"an_older_person_{prompt_formatted}.jpg"
    
    #st.write(f"Looking for images for prompt: {prompt_formatted}")

    # Search for images in the "neutral" folder
    neutral_image_query = f"'{neutral_folder_id}' in parents"
    neutral_results = _drive_service.files().list(q=neutral_image_query, fields="files(id, name)").execute()
    neutral_files = neutral_results.get('files', [])
    
    # Debug: Print all neutral files found
    # st.write("Neutral images found in folder:")
    # for file in neutral_files:
    #     st.write(f"- {file['name']}")

    # Find the specific file matching the prompt for neutral
    neutral_file = next((file for file in neutral_files if file['name'] == neutral_filename), None)

    # Search for images in the "older" folder
    older_image_query = f"'{older_folder_id}' in parents"
    older_results = _drive_service.files().list(q=older_image_query, fields="files(id, name)").execute()
    older_files = older_results.get('files', [])
    
    # Debug: Print all older files found
    # st.write("Older images found in folder:")
    #   for file in older_files:
    #     st.write(f"- {file['name']}")

    # Find the specific file matching the prompt for older
    older_file = next((file for file in older_files if file['name'] == older_filename), None)

    # Check if the images are found
    if neutral_file:
        images['neutral'] = neutral_file  # Take the first image
    if older_file:
        images['older'] = older_file  # Take the first image

    # Ensure both images exist, otherwise return an error
    if 'neutral' not in images or 'older' not in images:
        st.error(f"Error: No se encontraron imágenes para el prompt '{prompt_formatted}'. Asegúrate de que existan en Google Drive.")
        return {}

    return images

#@st.cache_data()
def get_images_for_prompt(prompt):
    images = {}
    
    # Adjust the prompt name for file search
    prompt_formatted = prompt.replace(" ", "_")  # Replace spaces with underscores for filenames

    # Define expected filenames for neutral and older images
    neutral_filename = f"a_person_{prompt_formatted}.jpg"
    older_filename = f"an_older_person_{prompt_formatted}.jpg"
    
    # Folder IDs for "neutral" and "older"
    neutral_image_path = Path(__file__).parent / "IMAGES" / "neutral" / neutral_filename
    older_image_path = Path(__file__).parent / "IMAGES" / "older" / older_filename

    # Verificar si las imágenes existen en las rutas especificadas
    if os.path.exists(neutral_image_path):
        images['neutral'] = Image.open(neutral_image_path)  # Cargar la imagen neutral
    else:
        st.warning(f"No se encontró la imagen neutral para el prompt '{prompt_formatted}'.")

    if os.path.exists(older_image_path):
        images['older'] = Image.open(older_image_path)  # Cargar la imagen older
    else:
        st.warning(f"No se encontró la imagen older para el prompt '{prompt_formatted}'.")

    # Asegurarse de que ambas imágenes existan, de lo contrario retornar error
    if 'neutral' not in images or 'older' not in images:
        st.error(f"Error: No se encontraron ambas imágenes para el prompt '{prompt_formatted}'.")
        return {}

    return images

############### GOOGLE SHEETS #############
def save_responses_to_google_sheets(sheets_service, spreadsheet_id, user_id, user_age, image_responses):
    try:
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        values = []
        
        # Para cada imagen y sus respuestas
        for image_id, steps_data in image_responses.items():
            # Extraer información de la imagen
            image_path = Path(image_id)
            image_type = "older" if "older" in str(image_path) else "neutral"
            prompt = image_path.name.replace("a_person_", "").replace("an_older_person_", "").replace(".jpg", "")
            
            # Para cada paso (1-3) y sus respuestas
            for step_key, step_data in steps_data.items():
                # Guardar tags
                tags_str = "|".join(step_data.get("Tags", []))
                
                # Guardar palabras adicionales
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
        
        # Preparar el cuerpo de la solicitud
        body = {
            'values': values
        }
        
        # Enviar datos a Google Sheets
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A1',  # Asegúrate de que esto coincida con tu hoja
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
        
        # Si no hay encabezados, añadirlos
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

############### SENSE DRIVE ###############
# Función auxiliar para convertir una imagen a base64 (útil para preparar las imágenes)
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()
    
# Función auxiliar para guardar una imagen en base64
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

enable_scroll = """
<style>
.main {
    overflow: auto;
}
</style>
"""

def main():
    # Inicializar el estado de la sesión
    initialize_session_state()

    # Inicializar rutas
    #intro_image = Path("IMAGES/Imagen_intro.png")
    intro_image = Path(__file__).parent / "IMAGES" / "Imagen_intro.png"
    #pdf_path = Path("TERMS/TERMS.pdf")
    pdf_path = Path(__file__).parent / "TERMS" / "TERMS.pdf"

    drive_service, sheets_service = get_google_services()

    if not drive_service or not sheets_service:
        st.error("No se pudieron obtener los servicios de Google.")
        return

    drive_url = "https://drive.google.com/drive/u/0/folders/1GwfHfrsEH7jGisVdeUdGJOPG7TlbUyl8"
    parent_folder_name = "10_14_FALLING_WALLS"
    spreadsheet_id = "1kkpKzDOkwJ58vgvp0IIAhS-yOSJxId8VJ4Bjxj7MmJk"

    # Extraer el ID de la carpeta principal de Google Drive
    parent_folder_id = extract_folder_id(drive_url)

    # Inicializar estado de sesión
    if 'page' not in st.session_state:
        st.session_state.page = 'landing' #intro

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

    #st.write(f"Estado actual de la página: {st.session_state.page}")

    # Cargar archivos desde Google Drive (solo CSV o PDF, no imágenes) Si el folder ID de Google Drive se ha encontrado
    if parent_folder_id:
        # Buscar la carpeta de imágenes y el archivo CSV
        images_folder_id, csv_file_id = find_images_folder_and_csv_id(drive_service, parent_folder_name)
        # Verificar que la carpeta de imágenes fue encontrada (no se considera el CSV)
        if images_folder_id: #and csv_file_id:
            current_prompt = random.choice(prompts)  # Selecciona un prompt aleatorio
            #images = get_images_for_prompt(drive_service, current_prompt)  #DRIVE
            images = get_images_for_prompt(current_prompt)  # Implementa esta función
            if 'neutral' in images and 'older' in images:
                st.session_state.random_images = [images['neutral'], images['older']]
            else:
                st.error("No se encontraron imágenes adecuadas para el prompt.")
            
            if not st.session_state.all_files: # Crucial: Get all files, including the PDF
                results = drive_service.files().list(
                    q=f"'{parent_folder_id}' in parents",  # Query for files in the parent folder
                    fields="nextPageToken, files(id, name, mimeType)"
                ).execute()
                st.session_state.all_files = results.get('files', [])                
        else:
            st.error("No se pudieron encontrar las imágenes")  #o el archivo CSV.
    else:
        st.error("Could not obtain the parent folder ID.")

##########################################################################################################
# Página de landing
    if st.session_state.page == 'landing':
        #st.title("Welcome to the Ageism AI Project")

        components.html(particles_js, height=0, scrolling=False)

        st.markdown("<h1 style='text-align: center;'>Welcome to the Ageism AI Project</h1>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center;'>In this experience, you'll explore AI-generated images and analyze how age is represented. This study is part of the Ageism AI project funded by Volkswagen Foundation.</h5>", unsafe_allow_html=True)

        test_items = [
            dict(
                title="Slide 1",
                text="A tree in the savannah",
                img="https://img.freepik.com/free-photo/wide-angle-shot-single-tree-growing-clouded-sky-during-sunset-surrounded-by-grass_181624-22807.jpg?w=1380&t=st=1688825493~exp=1688826093~hmac=cb486d2646b48acbd5a49a32b02bda8330ad7f8a0d53880ce2da471a45ad08a4",
                link="https://discuss.streamlit.io/t/new-component-react-bootstrap-carousel/46819",
            ),
            dict(
                title="Slide 2",
                text="A wooden bridge in a forest in Autumn",
                img="https://img.freepik.com/free-photo/beautiful-wooden-pathway-going-breathtaking-colorful-trees-forest_181624-5840.jpg?w=1380&t=st=1688825780~exp=1688826380~hmac=dbaa75d8743e501f20f0e820fa77f9e377ec5d558d06635bd3f1f08443bdb2c1",
                link="https://github.com/thomasbs17/streamlit-contributions/tree/master/bootstrap_carousel",
            ),
            dict(
                title="Slide 3",
                text="A distant mountain chain preceded by a sea",
                img="https://img.freepik.com/free-photo/aerial-beautiful-shot-seashore-with-hills-background-sunset_181624-24143.jpg?w=1380&t=st=1688825798~exp=1688826398~hmac=f623f88d5ece83600dac7e6af29a0230d06619f7305745db387481a4bb5874a0",
                link="https://github.com/thomasbs17/streamlit-contributions/tree/master",
            ),
            dict(
                title="Slide 4",
                text="PANDAS",
                img="pandas.webp",
            ),
            dict(
                title="Slide 4",
                text="CAT",
                img="cat.jpg",
            ),
        ]

        carousel(items=test_items)
        
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
        
        if st.button("Go to Introduction", key="intro_button", use_container_width=False):
        # if st.button("Go to Introduction"):
            st.session_state.page = 'intro'
            st.rerun()

    if st.session_state.page == 'intro':

        components.html(particles_js, height=150, scrolling=False)

        #st.write("Estado de página: intro")  # Mensaje de depuración
        #st.markdown("<h1 style='text-align: center;'>AGEAI Project</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>How is age depicted in Generative AI?</h2>", unsafe_allow_html=True)
        #st.markdown("<h4 style='text-align: center;'></h4>", unsafe_allow_html=True)

        #col1, col2 = st.columns([2, 2]) 

        #with col1:
        #st.write("In this experience, you'll explore AI-generated images using prompts in Midjourney. Your task is to identify how age is represented in relation to emotions, roles and autonomy, by selecting different tags in each image and by describing the differences between the two age groups depicted.")
        #st.write("At the end, the collective insights from all participants will be revealed.")

        # with col2:
        #     if intro_image.exists():
        #         try:
        #             st.image(str(intro_image), width=250, use_column_width=False)
        #         except Exception as e:
        #             st.error(f"Error al cargar la imagen: {str(e)}")
        #     else:
        #         st.error("Imagen de introducción no encontrada")
        
        #st.write(f"Ruta absoluta de la imagen: {intro_image.resolve()}")

        st.markdown("""
        <center>
        <h5>In this experience, you'll explore AI-generated images using prompts in Midjourney. 
        Your task is to identify how age is represented in relation to emotions, roles and autonomy, 
        by selecting different tags in each image and by describing the differences between the two age groups depicted. 
        </h5>
        </center>
        """, unsafe_allow_html=True)

        st.write("")  # Mensaje de depuración

        st.markdown("""
        <center>
        <h5>At the end, the collective insights from all participants will be revealed.</h5>
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

        if st.button("Start"):
            #st.session_state.page = 'age_input' 
            st.session_state.page = 'prompt1'   
            st.rerun()

    elif st.session_state.page == 'prompt1':
        # Si current_prompt no está establecido, selecciona un prompt aleatorio
        if 'current_prompt' not in st.session_state:
            st.session_state.current_prompt = random.choice(prompts) 

        current_prompt = st.session_state.current_prompt  # Usar el prompt guardado

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"<h2 style='text-align: center;'>STEP {st.session_state.current_step} of 3</h2>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='text-align: center;'>How an older person and a person {current_prompt.replace('_', ' ')} are depicted in Midjourney ?</h4>", unsafe_allow_html=True)
            
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

            if st.button("Go!"):
                st.session_state.page = 'questionnaire'
                st.rerun()

        components.html(particles_js, height=350,width=1050, scrolling=False)


#QUESTIONNAIRE
    elif st.session_state.page == 'questionnaire':
        # st.markdown(
        # """
        # <style>
        # #root > div:nth-child(1) > div > div > div > div > section > div {
        #     padding-top: 0rem;
        # }
        # </style>
        # """, 
        # unsafe_allow_html=True)

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

        #st.title(f"Prompt: Person / Older person {st.session_state.current_prompt.replace('_', ' ')}")
        col1, col2, col3 = st.columns([2, 2, 1])
        # Obtener imágenes para el prompt actual
        current_prompt = st.session_state.current_prompt   
        images = st.session_state.image_handler.get_images_for_prompt(current_prompt)

        for i, (key, image_data) in enumerate(images.items()):
                    column = col1 if i == 0 else col2
                    with column:
                        if image_data['path'].exists():
                            image = Image.open(image_data['path'])
                            st.image(image, width=400,use_column_width=True,caption=f"Prompt: {image_data['name']}") #caption=image_data['name'])
                        else:
                            st.error(f"Image not found: {image_data['path']}")
                        
                        image_id = str(image_data['path'])
                        step_key = f"Step {st.session_state.current_step}"

                        if image_id not in st.session_state.image_responses:
                            st.session_state.image_responses[image_id] = {}

                        if step_key not in st.session_state.image_responses[image_id]:
                            st.session_state.image_responses[image_id][step_key] = {"Tags": [], "Comments": "", "Words": []}

                        # Tags
                        tags = {
                            1: ["Vulnerable", "Strong", "Hallucinated", "Realistic", "Passive", "Active",
                                "With limitations", "Capable", "Relaxed", "Worried"],
                            2: ["Vulnerable", "Strong", "Hallucinated", "Realistic", "Passive", "Active",
                                "With limitations", "Capable", "Relaxed", "Worried"],
                            3: ["Vulnerable", "Strong", "Hallucinated", "Realistic", "Passive", "Active",
                                "With limitations", "Capable", "Relaxed", "Worried"],
                        }

                        # Crear el multiselect encima de los botones
                        selected_tags = st.session_state.image_responses[image_id][step_key]["Tags"]

                        selected = selected_tags #AFEGIT PER LO D'ADALT

                        # Actualizar el estado de las etiquetas en función del multiselect
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

                        for j, tag in enumerate(tags[st.session_state.current_step]):
                            with btn_cols[j % 2]:
                                button_key = f"tag_button_{st.session_state.current_step}_{i}_{j}"
                                
                                # Determinar si la etiqueta está seleccionada
                                is_selected = tag in selected
                                
                                # Usar el parámetro 'type' de Streamlit para cambiar el estilo
                                if st.button(
                                    tag, 
                                    key=button_key, 
                                    use_container_width=True,
                                    type="secondary" if is_selected else "primary"
                                ):
                                    # Alternar la selección de la etiqueta
                                    if is_selected:
                                        selected.remove(tag)
                                    else:
                                        selected.append(tag)
                                    # Actualizar el estado de sesión con las etiquetas modificadas
                                    st.session_state.image_responses[image_id][step_key]["Tags"] = selected
                                    st.rerun()

                        # Formulario individual para cada imagen
                        form = st.form(key=f'form_step{st.session_state.current_step}_img{i}')
                        comment = form.text_input(
                            label='Describe the image in other words (20 characters):',
                            placeholder="Write here"
                        )
                        submit_button = form.form_submit_button(label='Submit')

                        if submit_button:
                            if comment:
                                # Asegurarse de que la lista de palabras esté inicializada
                                if "Words" not in st.session_state.image_responses[image_id][step_key]:
                                    st.session_state.image_responses[image_id][step_key]["Words"] = []
                    
                                # Asegurarse de que no se duplique la palabra
                                words_list = st.session_state.image_responses[image_id][step_key]["Words"]
                                if comment not in words_list:
                                    words_list.append(comment)
                                    st.session_state.image_responses[image_id][step_key]["Words"] = words_list

                       #Mostrar el multiselect con las palabras escritas
                        words_list = st.session_state.image_responses[image_id][step_key].get("Words", [])
                        st.multiselect(
                            "Submitted Words",  # Etiqueta para el multiselect de palabras
                            options=words_list,
                            key=f"words_multiselect_{image_id}_{st.session_state.current_step}",  # Clave única
                            default=words_list
                        )

        # Columna estrecha a la derecha
        with col3:
            # Añadir espacios en blanco para alinear con los botones de las otras columnas
            # for _ in range(46):  
            #     st.write("")
            
            components.html(particles_js, height=800,width=250, scrolling=False)

            # Texto "Step x of 3"
            st.markdown(f"<h4 style='text-align: center;'>Step {st.session_state.current_step} of 3</h4>", unsafe_allow_html=True)
            
            button_label = "Next Images" if st.session_state.current_step < 3 else "Finish"
            if st.button(button_label, key=f"next_button_step{st.session_state.current_step}_unique", use_container_width=True):
                if st.session_state.current_step < 3:
                    st.session_state.current_step += 1
                    st.session_state.current_prompt = random.choice(prompts)  # Cambiar el prompt para el siguiente paso
                else:
                    #st.session_state.page = 'end'  # Cambiar a la página de finalización
                    st.session_state.page = 'age_input'  # Cambiar a la página de finalización
                    st.session_state.current_step = 1  # Reiniciar el paso si es necesario para un nuevo flujo
                    st.session_state.current_prompt = random.choice(prompts)  # Seleccionar un nuevo prompt

                # Regresar a la página de prompt1 para mostrar el nuevo prompt
                #if st.session_state.page != 'end':  # Solo redirigir si no estamos en la página de finalización
                if st.session_state.page != 'age_input':  # Solo redirigir si no estamos en la página de finalización
                    st.session_state.page = 'prompt1'
                st.rerun()

# Nueva página para introducir la edad
    elif st.session_state.page == 'age_input':
        st.markdown("<h2 style='text-align: center;'>How old are you? (optional)</h2>", unsafe_allow_html=True)
        st.write("")

        #user_age = st.text_input("", value="", placeholder="...")  # Campo de texto para la edad (opcional)
        user_age = st.number_input("Enter your age", step=1)  # Campo de texto para la edad (opcional)

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
        if st.button("Continue"):
            st.session_state.user_age = user_age  # Guardar la edad (aunque puede estar en blanco)
            st.session_state.page = 'end'  # Cambiar a la siguiente página
            st.rerun()

    # Página final de agradecimiento
    elif st.session_state.page == 'end':
        try:
            # Mensaje de agradecimiento
            st.title("Thanks for participating! 😊")
            st.balloons()
            st.write("We appreciate your time and effort in completing this questionnaire.")
            
            # Mostrar Términos y Condiciones y el PDF
            with st.expander("Terms and Conditions", expanded=False):
                st.write("""
                * This study is part of the Ageism AI project funded by VolksWagen Foundation.
                * Data is anonymous and will be used for scientific studies.
                * If you agree, you accept to participate in the study.
                """)
                
                if pdf_path.exists():
                    display_pdf_from_file(pdf_path)
                else:
                    st.error("Terms and Conditions PDF not found.")
            
            # Checkbox para aceptar términos y condiciones
            agree = st.checkbox("I agree to the terms and conditions")
            
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
                            "agree" if agree else "none",  # Guardar el valor de aceptación
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

                # Marcar datos como guardados
                st.session_state.data_saved = True
                #st.success("✅ Data successfully saved to Google Sheets!")
            
            # Actualizar columna de aceptación en las filas del usuario si agree está marcado
            if agree:
                # Obtener el user_id del usuario actual
                user_id = st.session_state.user_id
                
                # Leer todos los datos para encontrar las filas del usuario actual
                sheet_data = sheets_service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range='Sheet1!A:D'  # Cambiar si las columnas de usuario/aceptación están en otro rango
                ).execute().get('values', [])
                
                # Encontrar las filas correspondientes al user_id actual y actualizar la columna de aceptación
                row_indices_to_update = []
                for i, row in enumerate(sheet_data):
                    if row[0] == user_id:  # Suponiendo que el user_id está en la columna A (índice 0)
                        row_indices_to_update.append(i + 1)  # Índices de fila en Google Sheets (1-based)
                
                # Realizar la actualización en la hoja
                for row_index in row_indices_to_update:
                    # Actualizar la cuarta columna (índice 3) a "agree"
                    sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'Sheet1!D{row_index}',  # Modificar la columna correcta
                        valueInputOption='USER_ENTERED',
                        body={'values': [['agree']]}
                    ).execute()

                #st.success("✅ Agreement successfully updated for your responses in Google Sheets!")
        
        except Exception as e:
            st.error(f"❌ Error saving to Google Sheets: {str(e)}")
            st.write("Error details:", str(e))
            st.write("Please contact support with the error message above.")
        
        # Botón para iniciar un nuevo cuestionario
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

        if st.button("Start New Questionnaire"):
            st.session_state.current_step = 1
            st.session_state.image_responses = {}
            st.session_state.page = 'landing'
            st.session_state.user_id = str(uuid.uuid4())
            st.session_state.user_age = None
            st.session_state.review_mode = False
            st.session_state.data_saved = False
            st.rerun()

if __name__ == "__main__":
    main()
