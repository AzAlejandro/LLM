# Lanzamiento 04 — Evaluación, servicios, modelos especializados y toolkit completo

## Propósito del lanzamiento

Este cuarto lanzamiento convierte el toolkit en una plataforma de trabajo real. En las etapas anteriores ya tienes clientes LLM, prompts, schemas, RAG, memoria, agentes y grafos. Ahora necesitas evaluar calidad, medir comportamiento, exponer servicios, integrar modelos especializados y dejar plantillas listas para nuevos proyectos.

La idea es pasar desde “funciona en notebooks” hacia “puedo reutilizarlo en proyectos reales”. Esto no significa abandonar notebooks. Significa que los notebooks pasan a ser laboratorios y demos, mientras que la lógica productiva queda en módulos, scripts, CLI o API.

Este lanzamiento también incorpora un patrón muy importante: no todos los problemas deben resolverse con el mismo LLM. Un sistema maduro puede usar un modelo local para preprocesar, un modelo pagado para razonar, un modelo RAG para responder con fuentes, un modelo fine-tuned para una tarea específica, un modelo clásico para predicción numérica y un evaluador para revisar calidad.

## Resultado esperado

Al terminar esta etapa deberías poder crear una aplicación mínima que use un grafo del toolkit, responder preguntas con RAG y memoria, registrar evaluación, exponer una API local y comparar modelos.

La experiencia de uso desde Python debería parecerse a esto:

```python
from llmkit.apps import LocalAgentApp

app = LocalAgentApp.from_project("industrial_report_agent")

result = app.run(
    query="Genera un reporte técnico del evento usando los documentos y memoria disponibles",
    graph="report_agent_graph"
)

print(result.final_answer)
print(result.metrics)
```

Y desde terminal debería ser posible algo como:

```bash
python scripts/run_graph.py --project industrial_report_agent --graph report_agent_graph --query "Resume los riesgos principales"
```

## Estructura que se agrega al repositorio

Este lanzamiento agrega evaluación, servicios de modelos, apps y plantillas de proyectos:

```text
src/llmkit/
├── evaluation/
│   ├── __init__.py
│   ├── datasets.py
│   ├── llm_judge.py
│   ├── rag_metrics.py
│   ├── agent_metrics.py
│   ├── regression_report.py
│   └── experiment_logger.py
├── model_services/
│   ├── __init__.py
│   ├── base_service.py
│   ├── local_llm_service.py
│   ├── remote_llm_service.py
│   ├── finetuned_openai_service.py
│   ├── modal_service.py
│   ├── embedding_service.py
│   └── classical_model_service.py
├── apps/
│   ├── __init__.py
│   ├── cli.py
│   ├── fastapi_app.py
│   ├── gradio_app.py
│   └── local_agent_app.py
└── templates/
    ├── rag_assistant/
    ├── report_agent/
    ├── evaluator_optimizer/
    └── industrial_agent/

notebooks/
├── 13_rag_evaluation.ipynb
├── 14_agent_evaluation.ipynb
├── 15_model_routing_comparison.ipynb
├── 16_specialist_model_service.ipynb
└── 17_end_to_end_demo.ipynb

scripts/
├── ingest_documents.py
├── run_graph.py
├── evaluate_rag.py
├── evaluate_agent.py
└── serve_api.py
```

Esta etapa ordena el toolkit para uso repetido. Ya no se trata solo de experimentar. Se trata de poder iniciar un nuevo proyecto copiando una plantilla y cambiando configuración, documentos, prompts y grafos.

## Evaluación como parte central del toolkit

La evaluación no debe ser un módulo decorativo. En sistemas LLM, si no evalúas, no sabes si una mejora realmente mejora. Puedes cambiar el prompt, el modelo, el chunking o el retriever y creer que el sistema funciona mejor solo porque una respuesta se ve bien.

El módulo `evaluation/` debe permitir crear datasets de preguntas, respuestas esperadas, criterios de evaluación y casos difíciles. Al principio puedes usar evaluación manual o LLM-as-judge, pero debe quedar guardada de forma estructurada.

La evaluación debe cubrir al menos tres niveles: recuperación RAG, respuesta final y comportamiento del agente.

## Evaluación de RAG

La evaluación de RAG debe revisar si el sistema recupera los documentos correctos y si la respuesta usa realmente el contexto. Una respuesta puede sonar bien y estar mal fundamentada. Por eso debes mirar chunks recuperados, fuentes, cobertura y groundedness.

El archivo `rag_metrics.py` debe incluir funciones simples para registrar preguntas, chunks recuperados, fuentes esperadas si existen, respuesta final y evaluación. No necesitas implementar métricas académicas complejas desde el inicio. Lo importante es crear el hábito de comparar configuraciones.

El notebook `13_rag_evaluation.ipynb` debe comparar al menos dos configuraciones, por ejemplo distinto `k`, distinto modelo de embeddings o distinto tamaño de chunk.

## Evaluación de agentes

La evaluación de agentes debe mirar más que la respuesta final. Debe revisar si el agente eligió bien la ruta, si usó herramientas cuando correspondía, si evitó herramientas innecesarias, si respetó el formato esperado y si corrigió errores cuando el evaluador pidió reintento.

El archivo `agent_metrics.py` puede registrar pasos del grafo, decisiones de routers, herramientas usadas, cantidad de iteraciones, errores y resultado final.

Esto es muy útil para LangGraph porque puedes comparar no solo qué respondió el sistema, sino cómo llegó a esa respuesta.

## LLM como juez

El módulo `llm_judge.py` debe contener evaluadores basados en LLM. Estos evaluadores deben usar schemas estrictos. Un juez que responde texto libre es difícil de analizar después.

Un buen juez debe devolver campos como `score`, `passed`, `reasoning_summary`, `critical_errors`, `missing_requirements` y `recommended_fix`.

No conviene usar siempre el mismo modelo para generar y evaluar. Cuando sea posible, usa un modelo distinto para juzgar. Para pruebas locales puedes usar un modelo local, pero para evaluación más seria puede convenir un modelo pagado más fuerte.

## Registro de experimentos

El archivo `experiment_logger.py` debe guardar resultados en JSONL, CSV o SQLite. No necesitas partir con una plataforma pesada. Lo importante es que cada corrida deje trazabilidad.

Cada experimento debería registrar fecha, modelo, prompt, versión del prompt, configuración RAG, grafo usado, duración, respuesta, evaluación y errores.

Este registro te permitirá comparar si un cambio de prompt, modelo o retriever realmente mejora el sistema.

## Servicios de modelos especializados

El módulo `model_services/` es una pieza clave de este lanzamiento. Aquí se formaliza la idea de que un sistema agentic no usa solo un LLM. Usa servicios de modelos.

Un servicio puede envolver un LLM local, un LLM remoto, un modelo fine-tuned de OpenAI, un modelo desplegado en Modal, un modelo clásico de scikit-learn, un modelo XGBoost, una red neuronal o un servicio de embeddings.

Todos estos servicios deberían tener una interfaz común. No significa que todos hagan lo mismo, sino que todos puedan inicializarse, ejecutarse y devolver una salida estructurada.

## Modelo local como servicio

El `local_llm_service.py` debe envolver modelos como Ollama. Este servicio es útil para tareas baratas: reescritura de consultas, clasificación simple, resumen de memoria, limpieza de texto, generación de borradores o preprocesamiento.

En tu caso, este patrón es importante porque puedes usar modelos Qwen locales como asistentes internos del sistema. No todo tiene que ir a OpenAI.

## Modelo remoto como servicio

El `remote_llm_service.py` debe envolver modelos pagados. Puede usar OpenAI o cualquier proveedor compatible. Este servicio se usa cuando necesitas mejor razonamiento, mejor seguimiento de instrucciones o mejor structured output.

La ventaja de encapsularlo es que tus agentes no quedan amarrados a un proveedor. Un agente puede pedir un servicio `reasoning_model` y la configuración decide si eso corresponde a OpenAI, Anthropic, OpenRouter u otro proveedor.

## Modelo fine-tuned como servicio

El `finetuned_openai_service.py` debe permitir llamar modelos fine-tuned. No tienes que entrenar uno inmediatamente, pero el toolkit debe tener el espacio conceptual para integrarlo.

Este patrón sirve cuando una tarea se repite mucho y tiene formato estable. Por ejemplo, clasificar eventos operacionales, transformar descripciones técnicas, estimar una variable textual o producir una salida en un estilo muy específico.

## Servicio remoto especializado

El `modal_service.py` representa un modelo desplegado como servicio remoto. Puede ser un modelo fine-tuned, un modelo open source grande, una red neuronal o una función pesada que no quieres ejecutar localmente.

Este patrón te permite mantener el toolkit local, pero delegar tareas costosas a infraestructura remota. El agente no necesita saber si el modelo está en Modal, una API propia o un servidor interno. Solo llama al servicio.

## Modelo clásico como servicio

El `classical_model_service.py` es especialmente relevante para ti como cientista de datos. Muchos sistemas LLM reales no son solo LLMs. Pueden combinar LLMs con modelos predictivos clásicos.

Por ejemplo, en un caso industrial, un modelo XGBoost puede estimar riesgo o calidad, mientras un LLM explica el resultado, recupera contexto documental y genera un reporte. El LLM no reemplaza al modelo numérico; lo coordina y comunica.

Este patrón es muy poderoso para sensores virtuales, mantenimiento predictivo, análisis de procesos y reportes operacionales.

## Routing entre modelos

El notebook `15_model_routing_comparison.ipynb` debe probar selección entre modelos. Una consulta simple puede ir a un modelo local. Una consulta técnica compleja puede ir a un modelo remoto. Una consulta documental puede ir a RAG. Una tarea numérica puede ir a un modelo clásico.

El routing puede partir determinístico. Más adelante puede usar un LLM clasificador. Lo importante es que el sistema registre por qué eligió un modelo.

El objetivo no es usar siempre el mejor modelo, sino usar el modelo adecuado para cada tarea.

## Aplicación CLI

La CLI permite usar el toolkit sin abrir notebooks. El archivo `apps/cli.py` y el script `run_graph.py` deben permitir ejecutar grafos desde terminal.

Esto es útil para pruebas rápidas, automatización y eventualmente integración con pipelines. Un comando de terminal también obliga a que el toolkit esté bien empaquetado, porque ya no dependes del estado de un notebook.

## API local con FastAPI

El archivo `fastapi_app.py` debe exponer uno o más grafos mediante endpoints. No necesitas construir una API enorme. Basta con un endpoint `/run` que reciba proyecto, grafo y query.

La API debe cargar configuración, inicializar el grafo y devolver respuesta estructurada. Esta capa prepara el camino para conectar una interfaz web, una app interna o un sistema externo.

## Interfaz Gradio

La app Gradio es útil para demos y experimentación. Debe usar los mismos grafos que la CLI y la API. No debe tener lógica propia duplicada.

El objetivo de Gradio es permitir probar el sistema con usuarios, revisar respuestas y depurar comportamiento. Para tus casos industriales, puede servir como interfaz temprana para probar reportes, consultas documentales o agentes de diagnóstico.

## Plantillas de proyecto

La carpeta `templates/` debe contener proyectos iniciales que puedas copiar. Cada plantilla debe incluir configuración, prompts, notebooks mínimos y README propio.

Las plantillas recomendadas son `rag_assistant`, `report_agent`, `evaluator_optimizer` e `industrial_agent`.

La plantilla `industrial_agent` debería ser especialmente importante para ti. Puede incluir RAG documental, memoria de decisiones, modelo clásico opcional y reportero técnico.

## Notebook 13: evaluación RAG

Este notebook debe correr un conjunto pequeño de preguntas contra el pipeline RAG y guardar resultados. Debe comparar configuraciones y mostrar dónde falla la recuperación.

La salida debe ser una tabla con pregunta, respuesta, fuentes, evaluación y observaciones.

## Notebook 14: evaluación de agentes

Este notebook debe ejecutar un grafo agentic con varios casos de prueba. Debe registrar rutas tomadas, herramientas usadas, número de iteraciones y evaluación final.

El objetivo es entender el comportamiento del grafo, no solo leer la respuesta final.

## Notebook 15: comparación de routing de modelos

Este notebook debe probar modelos locales y remotos en tareas distintas. Debe mostrar cuándo conviene usar cada uno.

Este notebook es clave para controlar costos. Un toolkit útil no manda todo al modelo más caro. Usa modelos pequeños para tareas simples y reserva modelos fuertes para tareas que realmente lo justifican.

## Notebook 16: servicio especializado

Este notebook debe envolver un modelo especializado como servicio. Puede ser un modelo local, un modelo clásico guardado en disco, un endpoint remoto o un placeholder si todavía no tienes el modelo.

La idea es probar el patrón de integración. El agente debe poder llamar un servicio especializado sin conocer sus detalles internos.

## Notebook 17: demo end-to-end

Este notebook debe ser la demostración completa del toolkit. Debe cargar configuración, memoria, RAG, grafo, evaluación y respuesta final.

Este notebook no debe tener lógica reusable nueva. Si necesitas escribir funciones grandes dentro del notebook, significa que algo falta en el toolkit.

## Criterio de término del lanzamiento

Este lanzamiento está terminado cuando puedes ejecutar una demo end-to-end, evaluar resultados, comparar modelos, usar servicios especializados y exponer el sistema por CLI o API local.

No está terminado si la evaluación es manual y no queda registrada, si la API duplica lógica del notebook, si los modelos especializados se llaman con código ad hoc, o si cada plantilla requiere copiar y pegar demasiadas funciones internas.

## Decisión de diseño más importante

La decisión central es convertir el toolkit en una plataforma modular. Los LLMs, RAG, memoria, agentes, grafos, evaluadores y servicios deben poder combinarse sin reescribirlos. Esa modularidad es lo que te permitirá construir rápido proyectos nuevos sin perder calidad de ingeniería.

## Dirección posterior al lanzamiento 04

Después de este lanzamiento puedes avanzar hacia versionamiento de prompts, dashboards de evaluación, integración con MLflow, despliegue con Docker, servidores vLLM, colas de tareas, autenticación, permisos por usuario y monitoreo de costos.

Pero esas extensiones solo tienen sentido si los cuatro lanzamientos anteriores están firmes. Primero se construye el núcleo. Luego RAG y memoria. Después agentes y grafos. Finalmente evaluación, servicios y despliegue.
