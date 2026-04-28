# Lanzamiento 02 - RAG, documentos y memoria reutilizada

## Proposito del lanzamiento

Este segundo lanzamiento agrega RAG al toolkit sin intentar convertirlo todavia en una plataforma general de retrieval. Despues del primer lanzamiento ya tienes clientes LLM, prompts, configuracion, schemas y una base de memoria conversacional en SQLite. Ahora toca sumar un flujo concreto para trabajar con documentos locales: cargarlos, partirlos, vectorizarlos, recuperar contexto y responder usando ese contexto.

La idea principal de esta etapa es practicar el flujo real de RAG de forma visible. El notebook debe dejar claro que esta ocurriendo en cada paso. Primero se muestra la forma manual. Despues se mueve la parte reusable a `src/llmkit/`.

Este lanzamiento sigue la misma regla de los anteriores: robustez util sin complejidad temprana. No es momento de disenar un framework RAG para todos los casos posibles. Es momento de dejar una base pequena, clara y util que luego se pueda adaptar.

Tambien se reutiliza lo que ya existe en el repositorio. En particular:

- el toolkit ya tiene configuracion y clientes LLM;
- ya existe memoria conversacional persistente en SQLite;
- ya existe `render_memory_prompt(...)` para convertir historial reciente en contexto util.

En esta etapa, RAG es el foco principal. La memoria no se rediseña desde cero; se reaprovecha como una extension practica para algunos notebooks.

## Resultado esperado

Al terminar esta etapa deberias poder ejecutar notebooks que:

1. cargan documentos `.md` desde una carpeta local;
2. muestran su metadata basica;
3. los dividen en chunks con configuracion visible;
4. generan embeddings;
5. construyen un vectorstore local persistente;
6. recuperan chunks relevantes para una pregunta;
7. muestran esos chunks antes de llamar al modelo;
8. construyen un prompt con contexto y generan una respuesta;
9. reutilizan la memoria SQLite actual en un caso simple de continuidad conversacional.

La experiencia de uso esperada debe sentirse mas asi:

```python
from llmkit.rag.loaders import load_markdown_documents
from llmkit.rag.splitters import split_documents
from llmkit.rag.vectorstores import build_chroma_index, retrieve_chunks
from llmkit.rag.answer import answer_with_context

documents = load_markdown_documents("data/knowledge_base")
chunks = split_documents(documents, chunk_size=800, chunk_overlap=120)
build_chroma_index(chunks, persist_directory="data/vectorstores/local_docs")

results = retrieve_chunks(
    question="Who founded Insurellm?",
    persist_directory="data/vectorstores/local_docs",
    k=6,
)

answer = answer_with_context(
    question="Who founded Insurellm?",
    retrieved_chunks=results,
)

print(answer)
```

La experiencia no debe depender todavia de una clase central tipo `RAGPipeline`. Si mas adelante aparece una clase coordinadora, deberia nacer despues de que el flujo basico ya este probado y usado en notebooks.

## Estructura que se agrega al repositorio

La estructura recomendada para este lanzamiento debe ser corta y alineada con el uso real del notebook:

```text
src/llmkit/
|-- rag/
|   |-- __init__.py
|   |-- loaders.py
|   |-- splitters.py
|   |-- embeddings.py
|   |-- vectorstores.py
|   `-- answer.py
|-- memory/
|   |-- __init__.py
|   |-- sqlite_memory.py
|   `-- context.py
`-- schemas/
    `-- rag_outputs.py

notebooks/
|-- 07_document_ingestion.ipynb
|-- 08_basic_rag.ipynb
|-- 09_rag_debugging.ipynb
`-- 10_rag_with_memory.ipynb

data/
|-- knowledge_base/
`-- vectorstores/
```

La carpeta `rag/` concentra el flujo documental. La carpeta `memory/` ya existe y se reutiliza. En esta etapa no hace falta agregar nuevas capas de memoria como JSON memory, memory policies o summarizers si ningun notebook del release las necesita directamente.

## Regla pedagogica del release

Antes de abstraer, el notebook debe mostrar el cableado manual.

Por ejemplo, en el notebook de RAG basico deberia verse algo como:

```python
question = "..."
retrieved_chunks = retrieve_chunks(question=question, persist_directory=..., k=4)

context = "\n\n".join(
    f"Source: {item.metadata['source']}\n{item.page_content}"
    for item in retrieved_chunks
)

system_prompt = (
    "Use the provided context when it is relevant. "
    "If the answer is not in the context, say so.\n\n"
    f"Context:\n{context}"
)
```

Solo despues de que el notebook muestre eso tiene sentido usar una funcion reusable como `answer_with_context(...)`.

La pregunta de control para cada notebook es: si alguien lo lee, puede responder "que se le envio exactamente al modelo" y "que chunks se recuperaron antes de responder". Si no puede, entonces el notebook todavia esta ocultando demasiado.

## Carga de documentos

El primer paso de este lanzamiento es cargar documentos locales. No necesitas soportar todos los formatos posibles. Para el primer corte, basta con `.md`. Si mas adelante aparece una necesidad real, se podran sumar `.txt`, `.pdf` o `.csv`.

La carga debe ser simple y visible. Un modulo como `loaders.py` deberia:

- recorrer una carpeta base;
- cargar archivos markdown;
- devolver documentos con texto y metadata minima.

La metadata minima que conviene conservar desde el comienzo es:

- `source`: ruta o nombre del archivo;
- `file_name`: nombre del archivo;
- `doc_type`: carpeta de origen si aplica.

No hace falta todavia crear un sistema complejo de documentos internos si el notebook no lo necesita. Lo importante es que la metadata exista y que luego se vea en retrieval y debugging.

## Division en chunks

El chunking debe ser configurable, pero no complejo. El release necesita una unica estrategia clara y reusable. Una buena base para esta etapa es un splitter recursivo con `chunk_size` y `chunk_overlap`.

Lo importante no es encontrar el chunking perfecto, sino poder inspeccionarlo.

El notebook de ingesta debe mostrar:

- cuantos documentos entraron;
- cuantos chunks salieron;
- que configuracion se uso;
- ejemplos de chunks reales.

Si luego una respuesta sale mal, este paso permite ver si el problema fue el modelo o si el chunking ya estaba rompiendo el contexto.

## Embeddings

En esta etapa, embeddings debe ser una capa pequena. No hace falta una factoria general para muchos proveedores.

La recomendacion practica para este lanzamiento es:

- camino principal: OpenAI embeddings;
- alternativa opcional: Hugging Face embeddings.

La razon es simple: OpenAI embeddings te deja avanzar rapido y con pocas piezas. Hugging Face puede quedar como segunda opcion si quieres experimentar localmente, pero no deberia ser obligatoria para cerrar la release.

El release debe dejar claro una regla importante: si cambias el modelo de embeddings, normalmente debes reconstruir el indice vectorial.

## Vectorstore local

Chroma debe ser el vectorstore local inicial de esta etapa. No hace falta abrir desde ahora una interfaz para todos los backends posibles.

Lo que si debe poder hacer `vectorstores.py` es:

- crear un indice persistente en disco;
- abrir un indice existente;
- resetearlo o reconstruirlo;
- recuperar top-k chunks para una pregunta.

Tambien conviene registrar metadata de construccion del indice si eso se puede hacer sin complejidad innecesaria. Lo minimo util es saber:

- que embedding model se uso;
- que `chunk_size` y `chunk_overlap` se usaron;
- desde que carpeta se construyo.

No hace falta un gran sistema de versionado de indices. Solo la informacion suficiente para no perder trazabilidad basica.

## Flujo RAG basico

Esta release debe dejar instalado un flujo RAG pequeno y completo:

1. cargar documentos;
2. partir documentos;
3. construir embeddings;
4. persistir vectorstore;
5. recuperar top-k chunks;
6. mostrar chunks recuperados;
7. construir contexto con separadores claros;
8. llamar al LLM con ese contexto;
9. devolver respuesta y fuentes.

La pieza reusable de answering puede vivir en `answer.py`. No tiene que ser una clase grande. Puede ser solo una funcion que reciba:

- `question`;
- `retrieved_chunks`;
- `history` opcional;
- `model_id` opcional.

La funcion debe encargarse de:

- construir el contexto;
- armar el prompt final;
- llamar al cliente LLM del toolkit;
- devolver una respuesta clara.

## Retrieval y debugging

En esta etapa basta con retrieval vectorial simple por top-k.

El valor del release no esta en agregar reranking, query rewriting o multi-query retrieval desde el dia uno. El valor esta en que puedas ver claramente:

- que chunks se recuperaron;
- desde que fuente vinieron;
- en que orden llegaron;
- como cambia la recuperacion al tocar los parametros.

Por eso el notebook `09_rag_debugging.ipynb` es obligatorio. Debe permitir experimentar con:

- `k`;
- `chunk_size`;
- `chunk_overlap`.

Y debe obligarte a mirar retrieval antes de mirar la respuesta final.

## Memoria reutilizada

La memoria en esta release no parte desde cero. Ya existe una base conversacional util en el repositorio:

- `src/llmkit/memory/sqlite_memory.py`
- `src/llmkit/memory/context.py`
- `apps/gradio_chat.py`

Eso significa que `release 02` no necesita proponer:

- un backend JSON nuevo;
- un `memory_policy.py`;
- un `summarizer.py`;
- ni una arquitectura de memoria por capas.

Lo correcto en esta etapa es reutilizar la memoria SQLite ya disponible para mostrar un caso simple de continuidad entre preguntas o sesiones. Por ejemplo:

- guardar turnos de una conversacion;
- recuperar los ultimos mensajes;
- combinarlos con una pregunta nueva;
- construir un prompt con `render_memory_prompt(...)`;
- mostrar como esa memoria ayuda a formular o contextualizar una llamada.

Esto sirve como base para futuros flujos RAG con continuidad, pero sin quitarle protagonismo al objetivo principal del release, que sigue siendo RAG documental.

## Notebook 07: ingesta de documentos

Este notebook debe probar la base documental del release.

La estructura recomendada de este notebook es pedagogica y se parece al flujo de `week5/day2`:

1. cargar documentos;
2. dividirlos en chunks;
3. generar embeddings y guardar en Chroma;
4. cerrar con una inspeccion visual corta del espacio vectorial.

Debe mostrar primero la forma manual y despues la forma reusable. Como minimo deberia incluir:

- recorrido de `data/knowledge_base`;
- carga de documentos markdown;
- inspeccion de metadata;
- aplicacion del splitter;
- conteo de chunks;
- ejemplos reales de chunks;
- construccion del vectorstore local.

Si el notebook sigue siendo claro, conviene cerrar con una visualizacion ligera del indice, por ejemplo una proyeccion 2D simple para inspeccion inicial. No hace falta que esa parte sea profunda en el release base, pero si puede servir como chequeo rapido de que el indice no es una caja negra.

El objetivo del notebook no es responder preguntas todavia. Es verificar que el conocimiento quede preparado para ser recuperado.

## Notebook 08: RAG basico

Este notebook debe cargar un indice ya construido y responder preguntas usando retrieval real.

Como minimo debe mostrar:

- la pregunta original;
- los chunks recuperados;
- el contexto final concatenado;
- el prompt o mensajes que se envian;
- la respuesta del modelo.

La regla del notebook es simple: no mirar nunca solo la respuesta. Siempre mirar tambien el contexto recuperado.

## Notebook 09: debugging de RAG

Este notebook debe usarse para diagnosticar.

Debe comparar que ocurre cuando cambias:

- `k`;
- `chunk_size`;
- `chunk_overlap`.

Tambien conviene que incluya al menos uno o dos ejemplos de fallo, no solo ejemplos que salen bien. Esa es una buena leccion de `week5`: el valor del notebook no esta solo en mostrar que funciona, sino en mostrar por que a veces no funciona.

No necesita convertirse en un laboratorio completo de retrieval. Solo debe ayudarte a aprender a responder preguntas como:

- el problema esta en retrieval o en generation;
- el chunking esta demasiado fino o demasiado grueso;
- el contexto relevante aparece, pero demasiado abajo;
- el modelo esta respondiendo bien a un contexto malo o mal a un contexto bueno.

## Notebook 10: RAG con memoria reutilizada

Este notebook debe tomar la memoria SQLite ya existente y mostrar un uso pequeño y concreto.

No debe rediseñar memoria. Debe reutilizarla.

La prueba minima es algo como:

1. crear o cargar una conversacion;
2. guardar algunos turnos;
3. recuperar historial reciente;
4. componer una nueva pregunta con ese historial usando `render_memory_prompt(...)`;
5. usar ese contexto conversacional junto con RAG o en un flujo relacionado;
6. mostrar que el estado sigue disponible entre ejecuciones.

El objetivo es dejar claro que la memoria ya existente es suficiente como base para esta etapa.

## Criterio de termino del lanzamiento

Este lanzamiento esta terminado cuando:

- puedes construir un indice local desde documentos reales;
- puedes inspeccionar documentos, metadata y chunks;
- puedes recuperar top-k chunks y verlos antes de generar;
- puedes responder usando contexto recuperado y mostrar fuentes;
- puedes reutilizar la memoria SQLite ya existente en al menos un notebook simple.

No esta terminado si:

- el flujo solo funciona escondido dentro de una clase grande;
- el notebook no deja ver que se recupero;
- el vectorstore no deja claro con que embeddings y chunking fue creado;
- el release exige modulos o abstracciones que ningun notebook usa directamente.

## Mejoras que se dejan para despues

Este release no necesita cerrar todavia:

- query rewriting;
- reranking;
- multi-query retrieval;
- chunk enrichment por LLM;
- evaluacion sistematica de retrieval;
- multiples vectorstores;
- multiples backends nuevos de memoria.

Todo eso puede entrar mas adelante una vez que el flujo base ya este funcionando y sepas donde estan los problemas reales.

Para que esa continuidad no quede ambigua, estas mejoras se trabajaran como una extension explicita de esta etapa en `toolkit_release_02_step2_rag_improvements.md`.

Los notebooks previstos para explorar esas mejoras posteriores son:

- `11_query_rewriting.ipynb`
- `12_reranking.ipynb`
- `13_multi_query_retrieval.ipynb`
- `14_chunk_enrichment.ipynb`
- `15_retrieval_evaluation.ipynb`
- `16_rag_strategy_comparison.ipynb`
- `17_embedding_visualization_tsne.ipynb`
- `18_embedding_diagnostics.ipynb`

La separacion es deliberada:

- `toolkit_release_02_rag_memory.md` cierra la base de RAG;
- `toolkit_release_02_step2_rag_improvements.md` explora mejoras avanzadas sobre esa base.

## Decision de diseno mas importante

La decision central de este lanzamiento es esta:

primero construir un flujo RAG basico, visible y reutilizable; despues mejorarlo.

RAG debe entrar como una escalera corta, no como una arquitectura completa desde el primer dia. La memoria ya existente se reaprovecha como apoyo, pero no se vuelve el centro del release.

Si al final de esta etapa puedes abrir un notebook, cargar documentos, ver chunks, recuperar contexto, responder con fuentes y reutilizar memoria conversacional simple, entonces la base correcta quedo instalada.
