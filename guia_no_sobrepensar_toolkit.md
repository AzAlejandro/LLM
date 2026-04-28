# Guía para no sobrepensar los releases del toolkit

Esta guía se debe leer antes de trabajar en los releases del toolkit. Su objetivo no es reemplazar los documentos técnicos, sino ayudarte a tomar decisiones con criterio práctico. La idea principal es simple: el toolkit debe crecer de forma secuencial, probada y útil. No estás construyendo una plataforma empresarial desde el día uno; estás construyendo una base personal/profesional que te permita crear chatbots, RAGs, agentes y grafos con rapidez, sin repetir siempre el mismo código.

## Principio central

El toolkit debe ser robusto, pero no debe ser complejo antes de tiempo.

Robusto significa que el flujo principal funciona, falla con mensajes claros y permite depurar rápido. Complejo significa que agregas abstracciones, opciones, proveedores, registries o validaciones que todavía no estás usando en ningún notebook real.

La pregunta correcta no es “¿esto se usa a nivel industrial?”. Muchas cosas sí se usan a nivel industrial. La pregunta correcta es: “¿esto mejora el flujo que estoy implementando ahora?”.

Si la respuesta es no, la pieza puede esperar.

## La regla de los notebooks

Cada release debe tener notebooks que prueben el toolkit desde afuera. Los notebooks no deben contener la lógica principal, pero sí deben demostrar que la lógica existe y funciona.

Una función, clase o módulo solo debería crearse si al menos un notebook del release lo usa directamente o si es necesario para que ese notebook funcione.

Por ejemplo, si en Release 01 solo vas a probar un chatbot básico, un prompt registry y un structured output, entonces no necesitas todavía un sistema avanzado de tags, costos por modelo, tool calling ni soporte para diez proveedores.

El notebook manda. Si no aparece en un notebook, probablemente no pertenece todavía al release actual.

## La regla de transparencia antes de abstracción

Antes de introducir una abstracción, el notebook debe mostrar la forma manual que esa abstracción reemplaza.

En llamadas LLM, esto significa que primero debe verse algo como:

```python
system_prompt = "..."
user_prompt = "..."
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt},
]
```

Solo después de mostrar eso tiene sentido usar helpers como `build_messages()`, `LLMFactory.create()`, `llm.invoke()` o `PromptRegistry.get()`.

Una abstracción es aceptable si el notebook deja claro qué oculta. Si una función oculta `system`, `user`, `messages`, `response_format`, parsing JSON o validación Pydantic, el notebook debe imprimirlo o explicarlo cerca de la celda donde se usa.

Esto es especialmente importante en structured output. Si el notebook usa `parse_json_output()`, debe quedar claro que el schema se está aplicando después de la generación. Si usa `invoke_structured(...)`, el notebook debe diferenciarlo explícitamente porque el nivel de garantía no es el mismo.

La regla práctica es esta: si después de leer el notebook no puedes responder "¿qué se le envió exactamente al modelo?", entonces el notebook está incompleto.

Esto también aplica a prompts. Un registry de prompts no debe crecer como una caja negra. Cada prompt registrado debe aparecer en un notebook del release actual, y el notebook debe mostrar su `system`, su `user_template`, las variables requeridas y el mensaje final renderizado.

En Release 01, la pedagogía importa tanto como la reutilización. Primero se enseña el cableado manual. Después se muestra la función que evita repetirlo.

## Robustez útil versus complejidad innecesaria

Robustez útil es validar que exista una API key antes de llamar a OpenAI. También es entregar un error claro si falta una variable del prompt, guardar el texto crudo si falla un JSON, devolver siempre una respuesta con la misma estructura y permitir cambiar el modelo desde configuración.

En structured output, robustez útil también significa no confundir "JSON válido" con "salida que cumple el schema". Un modelo puede devolver llaves correctas y aun así fallar porque puso un objeto donde se esperaba un `str`. Esa diferencia debe verse en notebooks y documentación.

Complejidad innecesaria es implementar desde el comienzo un registry completo de capacidades por modelo, costos aproximados, filtros avanzados de prompts, múltiples capas de secretos, todos los proveedores posibles y tests estrictos de documentación, antes de tener un chatbot y un RAG funcionando.

La robustez útil reduce errores. La complejidad innecesaria crea errores nuevos.

## Cómo decidir si una pieza se implementa ahora

Antes de agregar una clase, función o módulo, responde tres preguntas.

### ¿Lo necesito para el flujo actual?

Si la pieza no se usa en el notebook actual o en el siguiente notebook inmediato, no la implementes todavía.

Ejemplo: `PromptRegistry.get()` sí se necesita pronto. `PromptRegistry.filter_by_tag()` puede esperar.

### ¿Evita un error frecuente y costoso?

Si la pieza evita un error que sabes que aparecerá muchas veces, vale la pena incluirla.

Ejemplo: una función que valide `OPENAI_API_KEY` sí vale la pena. Un sistema completo de fallback entre cinco proveedores puede esperar.

### ¿Simplifica el uso o solo ordena bonito?

Una abstracción vale la pena si hace que el uso sea más simple. Si solo hace que el código parezca más arquitectónico, pero no mejora el flujo, puede esperar.

Ejemplo: un `LLMClient.invoke()` común simplifica. Un `ModelRegistry` con metadata avanzada puede esperar hasta tener varios modelos realmente usados.

## Release 01 debe ser mínimo robusto

Release 01 no debe ser un prototipo frágil. Debe tener una base limpia, pero pequeña.

Debe permitir cargar configuración, crear un cliente LLM, obtener un prompt por nombre, ejecutar una llamada, devolver una respuesta consistente y validar al menos una salida estructurada.

No necesita resolver todavía RAG, memoria, LangGraph, tools, evaluación avanzada, costos, tracing, despliegue ni múltiples servicios remotos.

El objetivo no es impresionar con arquitectura. El objetivo es poder abrir un notebook y usar el toolkit sin escribir de nuevo todo desde cero.

## Qué sí implementar en Release 01

### Configuración simple y centralizada

Debe existir un lugar único para configuración. Puede ser un `settings.py` simple o una clase `Settings` con `pydantic-settings`.

Lo importante es que el resto del código no lea `os.getenv()` por todas partes. También es importante que si falta una API key, el error sea claro.

No necesitas una configuración perfecta. Necesitas una configuración suficiente para OpenAI, Ollama y rutas locales.

### Cliente LLM común

Debe existir una interfaz común para llamar modelos. Al principio puede ser solo OpenAI y Ollama. No es obligatorio soportar todos los proveedores desde el primer release.

Lo importante es que el notebook no cree manualmente el cliente de OpenAI cada vez.

### Respuesta común

La salida del modelo debe volver en una estructura consistente. Al menos debería incluir `content`, `model`, `provider`, `latency_seconds` y, si está disponible, `usage`.

Esto evita que después cada notebook dependa del formato interno de cada proveedor.

### PromptTemplate y PromptRegistry básico

Debe existir una forma de guardar prompts reutilizables y pedirlos por nombre.

En Release 01 basta con `get()` y `list()`. Los tags, filtros y búsquedas avanzadas pueden esperar.

### Structured output inicial

Debe existir al menos un ejemplo con Pydantic. No necesitas una gran colección de schemas. Necesitas demostrar que puedes pedir JSON, validarlo y manejar el caso en que el modelo responda mal.

La secuencia recomendada para Release 01 es esta:

1. Mostrar el prompt que pide JSON.
2. Mostrar el texto crudo que devolvió el modelo.
3. Validarlo con `parse_json_output(raw_text, Schema)`.
4. Explicar por qué falló si el JSON no coincide con el schema.

El toolkit debe tener una API separada para structured output nativo en providers que lo soporten. No conviene presentarlo como si fuera lo mismo que pedir JSON por prompt.

## Qué NO implementar en Release 01

No implementes RAG todavía. No implementes memoria todavía. No implementes LangGraph todavía. No implementes un sistema completo de herramientas. No implementes diez proveedores. No implementes costos por modelo. No implementes filtros sofisticados de prompts. No implementes evaluadores avanzados. No implementes deployment.

Si algo te parece “buena práctica”, pero no participa en el flujo actual, déjalo anotado para un release posterior.

## Release 02 debe agregar RAG y memoria de forma concreta

Release 02 debe aparecer cuando Release 01 ya permita llamar modelos y usar prompts sin fricción.

Aquí el foco debe ser documentos, chunking, embeddings, vectorstore, retrieval, generación con contexto y memoria simple.

No intentes resolver todos los tipos de RAG a la vez. Parte con un pipeline básico que cargue documentos locales, cree embeddings, recupere chunks y genere una respuesta con fuentes.

Después puedes agregar mejoras como reranking, metadata filtering, query rewriting o multi-query retrieval.

La memoria debe partir simple. Primero historial conversacional o resumen en JSON/SQLite. La memoria vectorial puede esperar si todavía no tienes un caso que la necesite.

## Release 03 debe agregar agentes y LangGraph

Release 03 debe venir después de tener RAG y structured outputs funcionando.

Un agente no es solo un prompt largo. Un agente debe tener rol, entrada, salida esperada, herramientas opcionales y criterios de decisión.

LangGraph debe entrar cuando ya tengas componentes que conectar: un clasificador, un nodo RAG, un nodo de respuesta, un evaluador o un nodo de herramientas.

No empieces por un grafo grande. Empieza con un router simple. Luego pasa a planner-executor. Después agrega evaluator o memoria.

## Release 04 debe agregar evaluación, servicios y modelos especializados

Release 04 es donde el toolkit se vuelve más cercano a una herramienta profesional.

Aquí sí tiene sentido agregar evaluación sistemática, trazabilidad, FastAPI, Gradio, servicios remotos, modelos especializados, endpoints compatibles con OpenAI, costos, métricas y quizás CI/CD.

Antes de Release 04, muchas de estas piezas son distracción. Después de Release 04, son necesarias porque ya estás pensando en uso repetible, comparación de modelos y despliegue.

## Cómo leer los releases sin confundirte

No leas los releases como una lista de obligaciones simultáneas. Léelos como un mapa.

Cuando estés en Release 01, solo te importa Release 01. Las menciones a Release 02, 03 o 04 sirven para no bloquear decisiones futuras, pero no para implementar todo ahora.

Si encuentras una sección que dice “esto será útil para LangGraph”, no significa que tengas que programar LangGraph ahora. Significa que debes evitar una decisión que luego impida usar LangGraph.

## La pregunta más importante durante el desarrollo

Cada vez que aparezca una idea nueva, pregunta:

“¿Esto ayuda a correr mejor el próximo notebook?”

Si ayuda, se implementa. Si no ayuda, se anota en `docs/backlog.md`.

El backlog es importante porque evita perder buenas ideas sin meterlas todas en el código.

## Señales de que estás sobrepensando

Estás sobrepensando si pasas más tiempo diseñando factories que usando el modelo. También si agregas soporte para proveedores que todavía no vas a probar, si escribes tests para funcionalidades que no existen, si tienes muchas clases pero ningún notebook útil, o si una función tiene más parámetros de los que tu caso actual necesita.

Otra señal clara es que necesitas leer cinco archivos para entender cómo hacer una llamada simple al LLM. En Release 01, una llamada simple debe sentirse simple.

También estás sobrepensando si tienes muchos prompts globales que no se ven en ninguna llamada real, si un archivo como `user_prompts.py` acumula strings que el notebook no explica, o si el usuario tiene que adivinar cómo `system_prompt` y `user_prompt` se convierten en `messages`.

## Señales de que estás avanzando bien

Vas bien si puedes abrir un notebook, importar el toolkit, elegir un prompt, elegir un modelo y obtener una respuesta.

Vas bien si los errores son claros. Vas bien si puedes cambiar de modelo sin reescribir el notebook. Vas bien si los prompts no están duplicados. Vas bien si el código reusable vive en `src/` y los notebooks solo lo usan.

Vas bien si cada release termina con un caso ejecutable, aunque sea pequeño.

## Criterio industrial realista

En industria y consultoría no gana el código más abstracto. Gana el código que permite entregar soluciones confiables, mantenerlas, depurarlas y extenderlas sin romper todo.

Eso no significa escribir código improvisado. Significa construir capas pequeñas, claras y probadas.

Un buen toolkit no nace completo. Se vuelve completo porque cada release resuelve un problema real y deja una base mejor para el siguiente.

## Decisión práctica recomendada

Para este toolkit, usa esta regla:

### Release actual

Implementa solo lo que el release necesita para funcionar.

### Release siguiente

Diseña lo mínimo para que el siguiente release no obligue a romper todo.

### Releases futuros

Anota ideas, pero no las programes todavía.

## Checklist antes de cerrar un release

Antes de dar un release por terminado, verifica que exista al menos un notebook que lo use de principio a fin. Verifica que el código reusable no esté dentro del notebook. Verifica que los errores principales sean claros. Verifica que haya al menos algunos tests locales. Verifica que puedas explicar en pocas frases para qué existe cada archivo nuevo.

Si no puedes explicar por qué existe un archivo, probablemente sobra o llegó demasiado temprano.

## Frase guía

Construye el toolkit como una escalera, no como un edificio completo desde el primer día.

Cada release debe dejarte en un punto más alto, con algo funcionando, probado y fácil de reutilizar.
