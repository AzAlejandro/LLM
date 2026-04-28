# Lanzamiento 01 — Núcleo local del toolkit LLM

## Propósito del lanzamiento

Este primer lanzamiento construye la base del toolkit. La idea no es crear todavía agentes complejos ni RAG avanzado, sino dejar listo el núcleo que todos los proyectos posteriores van a reutilizar. Si esta etapa queda bien diseñada, después podrás crear notebooks, servicios, agentes y grafos sin repetir código de configuración, clientes LLM, prompts o estructuras de respuesta.

El objetivo principal es que puedas ejecutar modelos locales y modelos remotos desde una misma interfaz. En tu caso, esto significa partir con OpenAI porque ya lo conoces, pero dejar preparado el mismo flujo para Ollama, modelos compatibles con OpenAI API, LiteLLM o proveedores pagados. El toolkit debe permitir cambiar de modelo sin reescribir el resto del proyecto.

Este lanzamiento debe poder ejecutarse completamente en local. Los modelos pagados solo deben entrar como una opción configurable, no como una dependencia obligatoria.

## Resultado esperado

Al terminar este lanzamiento deberías tener una librería Python mínima, importable desde notebooks, capaz de cargar configuración, inicializar clientes LLM, seleccionar prompts reutilizables, ejecutar una llamada simple y devolver una respuesta estructurada cuando sea necesario.

La prueba real de este lanzamiento es que puedas abrir un notebook y escribir algo parecido a esto:

```python
from llmkit.config import settings
from llmkit.llms import LLMFactory
from llmkit.prompts import PromptRegistry

llm = LLMFactory.create("openai:gpt-4.1-mini")
prompt = PromptRegistry.get("chat.basic")

response = llm.invoke(
    system=prompt.system,
    user=prompt.render_user(topic="sensores virtuales en procesos papeleros")
)

print(response.content)
```

El código exacto puede cambiar, pero la experiencia de uso debe ser esa: importar, seleccionar modelo, seleccionar prompt, ejecutar.

## Estructura inicial del repositorio

La estructura recomendada para este primer lanzamiento es la siguiente:

```text
llm-agent-toolkit/
├── README.md
├── pyproject.toml
├── .env.example
├── notebooks/
│   ├── 01_llm_client_smoke_test.ipynb
│   ├── 02_prompt_registry_test.ipynb
│   └── 03_structured_output_test.ipynb
├── src/
│   └── llmkit/
│       ├── __init__.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py
│       │   └── logging.py
│       ├── llms/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── openai_client.py
│       │   ├── openai_compatible_client.py
│       │   ├── ollama_client.py
│       │   ├── model_registry.py
│       │   └── factory.py
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── prompt_template.py
│       │   ├── registry.py
│       │   ├── system_prompts.py
│       │   └── user_prompts.py
│       └── schemas/
│           ├── __init__.py
│           ├── base.py
│           └── llm_outputs.py
└── tests/
    ├── test_settings.py
    ├── test_llm_factory.py
    └── test_prompt_registry.py
```

Esta estructura es deliberadamente pequeña. En esta etapa no conviene crear carpetas para RAG, agentes o LangGraph todavía. El toolkit debe crecer por capas. Si se parte con demasiadas piezas al mismo tiempo, el repositorio se vuelve difícil de probar y aparece código duplicado.

## Configuración del proyecto

La configuración debe vivir en `src/llmkit/config/settings.py`. Esta parte debe leer variables de entorno desde `.env`, pero también entregar valores por defecto razonables para pruebas locales.

La configuración mínima debería incluir el modelo por defecto, proveedor por defecto, temperatura, ruta base para datos locales, ruta de logs, claves API opcionales y URL de servidores compatibles con OpenAI. Por ejemplo, si usas Ollama local, necesitas guardar su `base_url`. Si usas OpenRouter, Groq o DeepSeek mediante API compatible con OpenAI, también necesitas manejar `base_url` y `api_key`.

La idea importante es que el resto del código no debe leer directamente `os.getenv`. Esa responsabilidad debe quedar encapsulada. Cuando un notebook necesite un modelo, debe pedirlo a la fábrica de modelos, no reconstruir manualmente clientes y variables de entorno.

## Logging

El logging debe quedar disponible desde el primer día. En proyectos LLM, el logging no es un detalle menor porque necesitas saber qué modelo se usó, qué prompt se ejecutó, cuánto tardó, si hubo error de parsing y qué proveedor respondió.

En este lanzamiento no necesitas trazabilidad avanzada ni MLflow. Basta con un logger central que escriba a consola y opcionalmente a archivo. Más adelante, este logger se puede conectar con evaluaciones, costos, latencia y experimentos.

El criterio correcto es que cada cliente LLM pueda registrar al menos el proveedor, nombre del modelo, duración aproximada y tipo de respuesta.

## Clientes LLM

El módulo `llms/` debe tener una clase base común. No tiene que ser compleja, pero sí debe forzar una interfaz compartida. Todos los clientes deberían poder hacer una llamada básica con un `system`, un `user` y parámetros opcionales.

El cliente de OpenAI debe ser el primero porque es el más estable para ti. Después debes crear un cliente compatible con OpenAI API para usar proveedores que imitan la API de OpenAI. Esta pieza es importante porque permite conectar Groq, OpenRouter, DeepSeek, Gemini mediante endpoint compatible, servidores vLLM o incluso algunos setups locales.

El cliente de Ollama debe quedar separado. Aunque Ollama puede exponerse con API compatible en algunos casos, conviene tener un wrapper propio porque en proyectos locales normalmente quieres controlar nombres de modelos, disponibilidad y errores de conexión.

El archivo `model_registry.py` debe funcionar como un mapa de modelos disponibles. No debería ser solo una lista. Debe guardar información útil como proveedor, nombre real del modelo, tipo de modelo, costo aproximado si aplica, si soporta tool calling, si soporta structured output y si es local o remoto.

## Fábrica de modelos

La fábrica es la pieza que hace cómodo el toolkit. El usuario del toolkit no debería instanciar manualmente `OpenAIClient`, `OllamaClient` o `OpenAICompatibleClient` cada vez. Debe poder pedir un modelo con un nombre simple.

Un patrón útil es usar identificadores como:

```text
openai:gpt-4.1-mini
openai:gpt-4.1-nano
ollama:qwen2.5:14b-instruct
openrouter:anthropic/claude-sonnet
local:qwen
```

La fábrica interpreta el prefijo, busca la configuración y devuelve el cliente correcto. Esta pieza se vuelve muy poderosa más adelante, porque tus agentes podrán recibir simplemente `model_id="ollama:qwen2.5:14b-instruct"` o `model_id="openai:gpt-4.1-mini"`.

## Registro de prompts

El registro de prompts debe ser una de las piezas centrales del toolkit. En proyectos LLM reales, gran parte del desorden aparece porque los prompts quedan escritos directamente dentro de notebooks, funciones o agentes. Eso hace difícil comparar versiones y reutilizar estilos.

En este lanzamiento debes crear una clase `PromptTemplate` y una clase `PromptRegistry`. Cada prompt debería tener nombre, descripción, system prompt, user prompt, variables requeridas y versión.

Un prompt no debería ser solo texto. Debe ser un objeto que sabe qué variables necesita y que puede renderizarse con seguridad. Si falta una variable, debe lanzar un error claro.

Un ejemplo de prompt básico sería `chat.basic`. Otro podría ser `code.explain_professor_style`. Otro podría ser `industrial.report_summary`. No necesitas crear muchos al comienzo; necesitas crear la estructura correcta para añadirlos después.

## Schemas y salidas estructuradas

Desde el primer lanzamiento conviene crear `schemas/`, aunque al principio tenga pocos modelos. La razón es que después tus agentes, evaluadores y grafos van a necesitar respuestas confiables. En vez de pedir “responde en JSON” sin validar, debes preparar modelos Pydantic para salidas estructuradas.

En esta etapa basta con tres schemas simples: una respuesta general, una respuesta de clasificación y una respuesta de evaluación mínima. Lo importante es probar que el LLM puede devolver una salida parseable y que el toolkit puede validarla.

No todas las llamadas necesitan structured output. El toolkit debe permitir texto libre y salida estructurada. Lo importante es que la opción exista desde el comienzo.

Tambien debe quedar explicita una distincion que evita errores de diseno:

- Pedir JSON por prompt y luego validarlo con `parse_json_output(...)` no significa que el schema fue impuesto durante la generacion.
- Un provider con structured output nativo si puede recibir el schema como contrato de salida.

Release 01 mantiene el primer enfoque como fallback didactico y agrega una ruta nativa para OpenAI mediante `invoke_structured(...)`. Si el modelo devuelve JSON valido con tipos incorrectos en el flujo manual, el parser debe fallar y el notebook debe mostrar ese caso.

## Notebook 01: prueba de clientes LLM

El primer notebook debe probar que puedes llamar modelos locales y remotos desde la misma interfaz. Este notebook no debe mezclar prompts complejos ni RAG. Solo debe validar que la configuración funciona.

La prueba esperada es llamar primero a OpenAI, luego a Ollama si está disponible, y después a un proveedor compatible con OpenAI si tienes clave configurada. El notebook debe mostrar claramente qué modelo respondió y qué ocurrió si un proveedor no está configurado.

Este notebook es tu prueba de humo. Cada vez que cambies el toolkit, deberías poder correrlo para confirmar que la base sigue funcionando.

## Notebook 02: prueba de prompts reutilizables

El segundo notebook debe probar `PromptRegistry`. Aquí debes cargar varios prompts, revisar sus variables requeridas y renderizar mensajes de prueba.

Este notebook debe demostrar que el mismo cliente LLM puede recibir distintos prompts sin cambiar código. Por ejemplo, puedes usar un prompt para resumir, otro para explicar código y otro para generar una respuesta técnica.

El aprendizaje central es que los prompts pasan a ser recursos versionables del proyecto, no texto escondido dentro del flujo.

## Notebook 03: prueba de salidas estructuradas

El tercer notebook debe probar Pydantic y structured outputs. Puedes pedirle al LLM que clasifique una consulta en categorías como `rag`, `agent`, `code`, `general`. Después validas la salida contra un schema.

Este notebook prepara el terreno para LangGraph. En un grafo, los routers y evaluadores necesitan salidas estructuradas. Si esta parte no funciona bien desde el comienzo, después los grafos se vuelven frágiles.

El notebook debe mostrar explicitamente el flujo real:

1. El prompt pide JSON.
2. El modelo responde texto.
3. `parse_json_output()` intenta convertir ese texto a un `BaseModel`.
4. Si la forma no coincide con el schema, se levanta error aunque el JSON sea sintacticamente valido.

Tambien conviene dejar una nota breve sobre los dos caminos del toolkit:

- `invoke()`: para texto libre o JSON pedido por prompt.
- `parse_json_output()`: para validacion local posterior.
- `invoke_structured(...)`: para providers con enforcement nativo del schema.

## Criterio de término del lanzamiento

Este lanzamiento está terminado cuando puedes ejecutar los tres notebooks sin modificar código interno del toolkit. Debes poder cambiar de modelo mediante configuración o identificador, reutilizar prompts desde el registry y validar al menos una salida estructurada.

No está terminado si todavía tienes prompts escritos directamente dentro de notebooks, si cada notebook crea su propio cliente OpenAI desde cero, o si la configuración está duplicada en varios archivos.

## Decisión de diseño más importante

La decisión central de este lanzamiento es separar uso de implementación. Los notebooks deben usar el toolkit, no contener el toolkit. Si un notebook tiene demasiadas funciones internas, probablemente esa lógica pertenece a `src/llmkit/`.

El notebook debe ser una demostración, una prueba o un experimento. El código reusable debe vivir en la librería.
