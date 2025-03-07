import logging
import azure.functions as func 
import requests
import os
import datetime

app = func.FunctionApp()

@app.timer_trigger(schedule="0 23,1 * * 0", arg_name="myTimer", run_on_startup=False,
                   use_monitor=False) 
def fnc_trigger_capacity(myTimer: func.TimerRequest) -> None:

    # Obtenemos la hora de ejecución de la función. 
    current_time = datetime.datetime.now().hour    

    # Variables
    TENANT_ID = os.getenv('var_TENANT_ID') 
    CLIENT_ID = os.getenv('var_CLIENT_ID') 
    CLIENT_SECRET = os.getenv('var_CLIENT_SECRET') 
    FABRIC_CAPACITY_NAME = os.getenv('var_FABRIC_CAPACITY_NAME') 
    SUSCRIPTION_ID= os.getenv('var_SUSCRIPTION_ID') 
    RESOURCE_GROUP = os.getenv('var_RESOURCE_GROUP') 
    AUTH_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    ACTION_CAPACITY = 'resume' if current_time == 23 else 'suspend'
    API_URL = f"https://management.azure.com/subscriptions/{SUSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Fabric/capacities/{FABRIC_CAPACITY_NAME}/{ACTION_CAPACITY}?api-version=2023-11-01"

    # Obtención del token. 
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://management.core.windows.net/.default"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    response = requests.post(AUTH_URL, data=payload, headers=headers)

    if response.status_code == 200:
        token = response.json().get("access_token")
    else:
        logging.info(f"Error obteniendo token: {response.text}")            
      
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(API_URL, headers=headers)
        
        if response.status_code == 202:
            logging.info(f"La capacidad de Fabric se está {'reanudando' if ACTION_CAPACITY == 'resume' else 'suspendiendo'} correctamente.")
        else:
            logging.info(f"Error {'reanudando' if ACTION_CAPACITY == 'resume' else 'suspendiendo'} la capacidad: {response.status_code} - {response.text}")
    except Exception as e:
         logging.error(f"Error en la función: {str(e)}")
