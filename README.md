# Automatizar el encendido y apagado de nuestra capacidad en Fabric

Una de las principales tareas en el desarrollo con Microsoft Fabric es gestionar las capacidades de computación de manera eficiente. Es crucial encenderlas cuando las estamos utilizando y asegurarnos de apagarlas al terminar para evitar costos innecesarios, especialmente en casos como los fines de semana, cuando pueden quedar encendidas sin necesidad.

También existen escenarios en los que un cliente solo necesita usar la capacidad en ciertos periodos del día, durante días laborables o incluso solo en fines de semana. Para optimizar este proceso y evitar la gestión manual, la mejor solución es **automatizar el encendido y apagado** de la capacidad usando **las APIs de Fabric y Azure Functions**.

## Pasos para la automatización

1. **Generar una App Registration y obtener un token** para interactuar con la API.
2. **Escribir el código para llamar a la API de Fabric**.
3. **Crear una Azure Function con TimerTrigger**.
4. **Desarrollar la lógica en VSCode y configurar la ejecución en horarios específicos**.
5. **Utilizar variables de entorno en Azure para evitar valores hardcodeados**.
6. **Probar la solución en local y desplegarla en Azure**.

## Generar una App Registration

Un **App Registration** en Microsoft Entra ID permite que una aplicación pueda autenticarse y solicitar permisos para interactuar con APIs de Microsoft.

### 📌 Características:
- Se registra en **Microsoft Entra ID**.
- Genera un **Client ID** y permite configurar **secretos o certificados** para autenticación.
- Define **permisos y scopes** para acceder a APIs como Microsoft Graph o APIs personalizadas.
- Puede ser **multi-tenant o single-tenant**.
- Se configura con redirecciones de autenticación **(OAuth2, OpenID Connect)**.
- Se debe agregar a la capacidad de Fabric este **App Registration** con rol de **colaborador**.

Puedes generar una App Registration siguiendo esta guía oficial de Microsoft: [Quickstart: Register an app in Microsoft Entra ID](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app).

## Generación del Token

Después de registrar la aplicación, debemos generar un **token de acceso**. Este token será necesario para autenticar las solicitudes a la API de Fabric. El proceso implica:

1. **Obtener los datos de autenticación**: `tenant_id`, `client_id` y `client_secret`.
2. **Realizar una solicitud HTTP al endpoint de autenticación de Microsoft** para generar el token.
3. **Utilizar el token en las llamadas posteriores a la API**.

Este token tiene una validez limitada, por lo que es recomendable manejar su **renovación de manera automática** en el código.
```python
    TENANT_ID = "TENANT ID"
    CLIENT_ID = "CLIENT ID"
    CLIENT_SECRET = "CLIENT SECRET"
    AUTH_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

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
        raise Exception(f"Error obteniendo token: {response.text}")
```

## Código para llamar a la API de Fabric

Una vez tengamos nuestra App Registration configurada, podemos desarrollar el código en Python para interactuar con la API de Fabric.

El primer paso es generar un código para obtener un **token de acceso**. Luego, se implementa la lógica para realizar las llamadas necesarias a la API y controlar el **encendido** (`resume`) y **apagado** (`suspend`) de la capacidad.

Para realizar estas operaciones, necesitaremos:
- **El nombre de la capacidad**.
- **El ID de la suscripción de Azure**.
- **El nombre del grupo de recursos**.
- **La acción a realizar (encender o apagar)**.

Además, es recomendable incluir un **manejador de errores (try/except)** para evitar problemas al intentar apagar una capacidad que ya está desactivada o encender una que ya está en funcionamiento.

```python
try:
        FABRIC_CAPACITY_NAME = "FABRIC_CAPACITY_NAME" #"5db2eccf-3daa-4112-a354-e7b85e2b85fe"  # ID de la capacidad de Fabric
        SUSCRIPTION_ID= "SUSCRIPTION_ID"
        RESOURCE_GROUP = "RESOURCE_GROUP"
        ACTION_CAPACITY = "suspend" # suspend/resume
        API_URL = f"https://management.azure.com/subscriptions/{SUSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Fabric/capacities/{FABRIC_CAPACITY_NAME}/{ACTION_CAPACITY}?api-version=2023-11-01"

        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(API_URL, headers=headers)
        
        if response.status_code == 202:
            logging.info(f"✅ La capacidad de Fabric se está {'reanudando' if ACTION_CAPACITY == 'resume' else 'suspendiendo'} correctamente.")
        else:
            logging.error(f"❌ Error reanudando la capacidad: {response.status_code} - {response.text}")
    
    except Exception as e:
        logging.error(f"❌ Error en la función: {str(e)}")
```

## Crear una Azure Function con TimerTrigger

**TimerTrigger** en **Azure Functions** permite la ejecución automática de una función sin necesidad de eventos externos. Es ideal para tareas programadas como:

- Encendido y apagado de recursos en horarios específicos.
- Limpieza de datos en bases de datos.
- Envío de informes periódicos.

La programación de la ejecución se define con **expresiones CRON**, asegurando que la función se ejecute en los momentos deseados. Aquí puedes encontrar una guía rápida para crear una Azure Function desde VSCode: [Creación de una función de Python con Visual Studio Code](https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python).

## Implementación en VSCode y configuración de horarios

Una vez tenemos la función desarrollada, debemos establecer los **horarios de ejecución**. En este ejemplo, programamos el **encendido** a las **23:00** y el **apagado** a la **01:00**. Esto se hace mediante la siguiente expresión CRON:

```python
@app.timer_trigger(schedule="0 23,1 * * *", arg_name="myTimer")
def manage_capacity(myTimer: func.TimerRequest):
    current_time = datetime.datetime.now().hour
    if current_time == 23:
        print("Encendiendo la capacidad...")
        # Llamada a la API para encender
    elif current_time == 1:
        print("Apagando la capacidad...")
        # Llamada a la API para apagar
```
Un ejemplo de más opciones para CRON: https://arminreiter.com/2017/02/azure-functions-time-trigger-cron-cheat-sheet/
## Uso de variables de entorno en Azure Functions

Para evitar **hardcodear** valores sensibles en el código, utilizamos **variables de entorno** en Azure. Estas variables se configuran en **Application Settings** dentro del **Portal de Azure** y se acceden mediante `os.getenv()` en Python.

```python
import os

tenant_id = os.getenv('TENANT_ID')
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
```

Esto nos permite mantener **seguridad y flexibilidad**, permitiendo cambios sin modificar el código.

## Pruebas y despliegue en Azure

Una vez configurada la función:
1. **Se prueba en local** usando Azure Functions Core Tools.
2. **Se despliega en Azure** mediante el comando:

```sh
func azure functionapp publish NOMBRE_FUNCION
```

3. **Se verifica el correcto funcionamiento** en Application Insights y logs de Azure.

## Conclusión

La automatización del encendido y apagado de capacidades en Microsoft Fabric con **Azure Functions y TimerTrigger** permite optimizar costos y evitar errores manuales en la gestión de recursos. Gracias al uso de **APIs de Fabric**, **App Registrations**, **variables de entorno** y **programaciones CRON**, podemos implementar una solución eficiente y escalable.

Este enfoque no solo simplifica la administración de recursos, sino que también garantiza **una mejor utilización del presupuesto en la nube** y una **gestión optimizada del rendimiento**. Además, el uso de **Azure Functions serverless** elimina la necesidad de mantener servidores activos para estas tareas, lo que lo convierte en una solución **ligera, eficiente y de bajo costo**.

Si te ha resultado útil este artículo y estás interesado en seguir automatizando Microsoft Fabric, te recomiendo el artículo donde se explica en detalle nuestro **#FabricMigrationFramework** de **ENCAMINA**. Este enfoque ayuda a definir una estrategia efectiva de migración, combinando **metodología y automatización** para reducir **tiempo y costos**, acelerando así el **#TimeToMarket** de tus proyectos en la nube. 🚀

## Recursos adicionales

- [Referencia para desarrolladores de Python para Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Desarrollo de Azure Functions con Visual Studio Code](https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python)

