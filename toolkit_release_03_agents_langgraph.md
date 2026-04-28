# Lanzamiento 03 — Agentes, herramientas y grafos con LangGraph

## Propósito del lanzamiento

Este tercer lanzamiento transforma el toolkit desde un sistema de llamadas LLM y RAG hacia una arquitectura agentic. En las etapas anteriores ya existe configuración, clientes LLM, prompts, schemas, RAG y memoria. Ahora necesitas crear agentes especializados y conectarlos mediante grafos.

La idea no es construir un agente gigante que haga todo. La idea es crear componentes con responsabilidades claras: un agente planificador, un agente trabajador, un agente evaluador, un agente RAG, un agente reportero y un conjunto de herramientas. Luego LangGraph se encarga de orquestar el flujo.

Este lanzamiento debe mantener el enfoque local-first. Los agentes deben poder usar Ollama o modelos locales para tareas simples, y modelos pagados para tareas donde necesitas más calidad. La selección de modelo no debe estar fija dentro del agente. Debe venir desde configuración o desde el constructor.

## Resultado esperado

Al terminar esta etapa deberías poder ejecutar un grafo simple con LangGraph donde un usuario hace una consulta, el sistema decide si necesita RAG o no, ejecuta herramientas si corresponde, evalúa la respuesta y produce una salida final estructurada.

La experiencia esperada debería parecerse a esto:

```python
from llmkit.graphs import GraphFactory

app = GraphFactory.create("rag_evaluator_graph")

result = app.invoke({
    "user_query": "Resume los principales riesgos operacionales del proceso",
    "project_id": "industrial_demo"
})

print(result["final_answer"])
print(result["evaluation"])
```

La gracia de esta etapa es que el usuario del toolkit no debería armar manualmente todos los nodos en cada notebook. Debe poder usar builders o factories para crear grafos típicos.

## Estructura que se agrega al repositorio

En este lanzamiento se agregan carpetas para agentes, herramientas y grafos:

```text
src/llmkit/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── worker_agent.py
│   ├── planner_agent.py
│   ├── evaluator_agent.py
│   ├── rag_agent.py
│   ├── reporter_agent.py
│   ├── memory_agent.py
│   └── tool_agent.py
├── tools/
│   ├── __init__.py
│   ├── base_tool.py
│   ├── python_tool.py
│   ├── file_tool.py
│   ├── dataframe_tool.py
│   ├── rag_tool.py
│   └── model_tool.py
├── graphs/
│   ├── __init__.py
│   ├── states.py
│   ├── nodes.py
│   ├── routers.py
│   ├── graph_builders.py
│   ├── checkpointers.py
│   └── graph_factory.py
└── schemas/
    ├── agent_outputs.py
    ├── graph_state.py
    └── tool_outputs.py

notebooks/
├── 08_base_agent_test.ipynb
├── 09_tool_calling_test.ipynb
├── 10_langgraph_router.ipynb
├── 11_rag_graph.ipynb
└── 12_evaluator_optimizer_graph.ipynb
```

Esta etapa es donde el toolkit empieza a parecerse a una plataforma propia. Sin embargo, el principio sigue siendo el mismo: los notebooks prueban y demuestran; la lógica reusable vive en `src/llmkit/`.

## Agente base

El archivo `base_agent.py` debe definir una clase común para todos los agentes. Esta clase no debe hacer demasiado, pero sí debe estandarizar nombre del agente, modelo usado, prompt, logger y método de ejecución.

Un agente especializado debe saber construir su prompt, llamar al modelo y parsear su salida. No debería conocer detalles internos de otros agentes. Si un agente necesita usar RAG, debería recibir un componente RAG o una herramienta RAG, no construir todo desde cero.

Esta separación es importante porque después vas a querer usar el mismo `EvaluatorAgent` en varios grafos o el mismo `ReporterAgent` en varios proyectos.

## Worker Agent

El `WorkerAgent` es el agente general que responde o ejecuta una tarea principal. En un grafo simple, puede ser el nodo central. En un grafo más avanzado, puede recibir instrucciones del planner.

Este agente debe poder trabajar con contexto opcional. Si recibe contexto RAG, lo usa. Si recibe memoria, la incorpora. Si no recibe contexto, responde como un LLM normal.

El `WorkerAgent` no debería decidir todo. Si necesita decidir si usar una herramienta, esa decisión puede venir de un router o de un planner. Mantenerlo acotado evita que el agente se vuelva impredecible.

## Planner Agent

El `PlannerAgent` decide qué pasos conviene ejecutar. Este agente no debe hacer todo el trabajo, sino producir un plan estructurado. Por ejemplo, puede decidir que una consulta necesita recuperar documentos, ejecutar una herramienta de datos, pedir evaluación y luego generar reporte.

El output del planner debe ser un schema. No basta con texto libre. Un buen plan podría incluir objetivo, pasos, herramientas requeridas, tipo de respuesta esperada y riesgos.

En proyectos industriales, este agente puede decidir si una pregunta requiere datos históricos, documentos técnicos, análisis de dataframe o solo explicación conceptual.

## Evaluator Agent

El `EvaluatorAgent` revisa si una respuesta cumple criterios. Este patrón es muy importante para sistemas agentic porque permite ciclos de mejora. El evaluador puede revisar completitud, claridad, uso de fuentes, formato de salida, presencia de alucinaciones o cumplimiento de instrucciones.

El evaluador debe devolver una salida estructurada con campos como `success`, `score`, `feedback`, `needs_retry` y `missing_information`.

No conviene que el evaluador use siempre el modelo más caro. Puedes partir con un modelo pagado para calidad, pero dejar configurable un modelo local o barato para pruebas.

## RAG Agent

El `RAGAgent` es un envoltorio agentic sobre el pipeline RAG. Su trabajo es recibir una pregunta, recuperar contexto y producir una respuesta con fuentes. A diferencia del pipeline RAG puro, el agente puede interpretar mejor la intención del usuario y decidir cómo presentar la respuesta.

El `RAGAgent` debe usar los módulos del lanzamiento anterior. No debe duplicar loaders, embeddings o retrievers.

Esta pieza permite que RAG se use como agente independiente o como herramienta dentro de otros agentes.

## Reporter Agent

El `ReporterAgent` convierte resultados intermedios en una respuesta final útil. En proyectos reales, muchos agentes producen piezas parciales: chunks recuperados, análisis de datos, evaluación, memoria, decisiones. El reportero transforma todo eso en una salida legible.

Este agente es especialmente importante para tus casos industriales. Puede generar reportes diarios, resúmenes técnicos, explicaciones para operadores, informes de diagnóstico o bitácoras de eventos.

El reportero debe tener prompts específicos por estilo de salida. No es lo mismo responder a un usuario técnico que generar un informe ejecutivo o un reporte operacional.

## Herramientas

Las herramientas son funciones que el sistema puede ejecutar fuera del LLM. En este lanzamiento debes crear herramientas simples, pero bien encapsuladas. Una herramienta puede leer archivos, ejecutar Python controlado, consultar un dataframe, llamar el pipeline RAG o invocar otro modelo.

Es importante entender que una herramienta no siempre es una API externa. En tu toolkit, una herramienta también puede ser otro modelo. Por ejemplo, puedes tener un `model_tool.py` que use un LLM barato para reescribir una consulta, clasificar una intención o resumir un texto antes de enviarlo al agente principal.

Esta idea es clave porque permite crear arquitecturas más parecidas a sistemas reales. Un LLM principal puede coordinar modelos auxiliares, herramientas de datos y recuperación documental.

## Modelos como herramientas internas

Un patrón que debes incluir desde esta etapa es usar modelos auxiliares como piezas internas del flujo. Por ejemplo, un modelo local puede normalizar una entrada, otro modelo pagado puede hacer razonamiento complejo, un modelo fine-tuned puede resolver una tarea estrecha, y un evaluador puede revisar el resultado.

Esto no siempre se implementa como tool calling formal. A veces es simplemente una clase que llama a otro modelo y devuelve un resultado. Lo importante es que el toolkit lo trate como un componente reusable.

Una estructura útil es tener herramientas o servicios como `QueryRewriteTool`, `ClassificationTool`, `SummarizationTool`, `LocalPreprocessorTool` y `RemoteSpecialistTool`.

## Estado de LangGraph

Antes de crear nodos, debes diseñar el estado. Este es uno de los errores más comunes al trabajar con LangGraph. Si el estado está mal definido, el grafo se vuelve confuso.

El archivo `states.py` debe definir qué información viaja por el grafo. Por ejemplo, `user_query`, `messages`, `retrieved_context`, `memory_context`, `plan`, `tool_results`, `draft_answer`, `evaluation`, `final_answer` y `errors`.

El estado debe ser explícito. No conviene pasar diccionarios desordenados con cualquier cosa. Mientras más claro sea el estado, más fácil será depurar nodos y routers.

## Nodos

Los nodos son funciones que reciben estado y devuelven una actualización del estado. Un nodo puede llamar a un agente, ejecutar una herramienta, recuperar memoria o evaluar una respuesta.

El archivo `nodes.py` no debería tener lógica compleja escondida. Cada nodo debe ser pequeño y usar componentes ya definidos. Por ejemplo, un nodo `retrieve_context_node` llama al `RAGAgent` o al retriever, pero no implementa desde cero la recuperación.

El patrón correcto es que los nodos conectan piezas. No son el lugar para escribir prompts largos o lógica de negocio extensa.

## Routers

Los routers deciden el próximo paso del grafo. En esta etapa debes crear routers simples. Por ejemplo, un router puede decidir si una consulta necesita RAG, si una respuesta debe reintentarse o si el sistema puede finalizar.

Los routers pueden ser determinísticos o basados en LLM. Al principio conviene crear routers determinísticos cuando sea posible, porque son más fáciles de probar. Si usas un router LLM, su salida debe estar validada con schema.

Un buen router no debe devolver texto libre. Debe devolver una etiqueta controlada como `use_rag`, `answer_directly`, `retry`, `finish`.

## Graph builders

Los builders son funciones que arman grafos reutilizables. No quieres copiar y pegar el armado de LangGraph en cada notebook. Debes tener builders para patrones comunes.

Los primeros grafos recomendados son `simple_worker_graph`, `router_graph`, `rag_graph` y `evaluator_optimizer_graph`.

El grafo `evaluator_optimizer_graph` es especialmente útil. El worker genera una respuesta, el evaluator la revisa y el router decide si terminar o volver a intentar con feedback. Este patrón se puede usar para generación de código, respuestas RAG, reportes y análisis técnicos.

## Checkpointing y memoria en grafos

LangGraph permite guardar estado entre pasos o conversaciones mediante checkpointers. En esta etapa no necesitas una arquitectura compleja, pero sí debes dejar preparada la integración.

Para pruebas locales, SQLite es una buena opción. La memoria del lanzamiento anterior puede convivir con el checkpointing. La diferencia es que el checkpoint guarda estado del grafo, mientras que la memoria guarda conocimiento útil para futuras ejecuciones.

No debes mezclar ambos conceptos. Un checkpoint responde a “dónde iba el flujo”. La memoria responde a “qué aprendió o decidió el sistema”.

## Notebook 08: prueba de agente base

Este notebook debe crear un `WorkerAgent`, pasarle un prompt simple y revisar su respuesta. Debe confirmar que el agente usa el modelo correcto, el prompt correcto y devuelve una estructura esperada.

El objetivo es probar agentes sin LangGraph todavía. Si un agente no funciona solo, no va a funcionar mejor dentro de un grafo.

## Notebook 09: prueba de herramientas

Este notebook debe probar herramientas simples. Puede incluir una herramienta de lectura de archivos, una herramienta RAG y una herramienta que llama a otro modelo para reescribir una consulta.

La idea es validar que una herramienta tiene input claro, output claro y errores controlados.

## Notebook 10: router con LangGraph

Este notebook debe crear un grafo mínimo con router. Una consulta simple puede ir directo al worker. Una consulta documental puede ir al nodo RAG. El notebook debe mostrar el estado final y los pasos ejecutados.

Este notebook es el primer puente real entre componentes y orquestación.

## Notebook 11: grafo RAG

Este notebook debe crear un grafo que combine memoria, RAG, generación y respuesta final. La consulta entra, el sistema recupera memoria relevante, recupera documentos, construye respuesta y entrega fuentes.

Este grafo debe parecerse a lo que usarías en un asistente documental real.

## Notebook 12: evaluator-optimizer

Este notebook debe implementar el ciclo de evaluación. El worker genera respuesta, el evaluator revisa, el router decide si reintentar y el worker mejora usando el feedback.

El criterio de éxito es que puedas ver claramente cuándo el sistema termina y cuándo decide mejorar. Este patrón será fundamental para generación de reportes y código.

## Criterio de término del lanzamiento

Este lanzamiento está terminado cuando tienes agentes reutilizables, herramientas simples, estados definidos, nodos pequeños, routers claros y al menos tres grafos funcionando desde notebooks.

No está terminado si cada notebook arma sus propios agentes desde cero, si los nodos contienen prompts largos, si el estado del grafo es un diccionario desordenado, o si los routers devuelven texto libre difícil de controlar.

## Decisión de diseño más importante

La decisión central es que LangGraph debe orquestar componentes, no reemplazarlos. Los agentes, herramientas, RAG y memoria deben funcionar fuera del grafo. El grafo solo decide el orden, las condiciones y los ciclos.
