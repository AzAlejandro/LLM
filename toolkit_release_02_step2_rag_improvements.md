# Lanzamiento 02 - Step 2: mejoras de RAG sobre la base inicial

## Proposito

Este documento define la segunda etapa del Release 02. No reemplaza `toolkit_release_02_rag_memory.md`. Lo continua.

La idea es simple:

1. primero cierras un RAG basico, visible y reusable;
2. despues exploras mejoras reales sobre esa base;
3. cada mejora debe vivir en notebooks claros antes de consolidarse en `src/llmkit/`.

Este step 2 existe para evitar mezclar demasiado temprano complejidad con la base del release. Aqui ya se asume que el flujo inicial funciona:

- carga de documentos;
- chunking;
- embeddings;
- Chroma persistente;
- retrieval top-k;
- respuesta con contexto;
- memoria SQLite reutilizada cuando aporta.

Sobre esa base, este step 2 agrega mejoras de calidad de retrieval y respuesta.

La progresion recomendada toma como referencia la logica pedagogica de `week5`:

1. primero mirar mejor el indice y el espacio vectorial;
2. despues medir retrieval;
3. despues comparar mejoras avanzadas;
4. y solo al final consolidar lo que realmente aporta.

## Regla central de esta etapa

Ninguna mejora entra como obligatoria en el toolkit solo porque "suena avanzada". Entra si:

- el notebook muestra el problema que corrige;
- el comportamiento mejora de forma visible;
- la mejora se puede explicar de manera concreta;
- y no rompe la claridad del flujo base.

La prioridad sigue siendo pedagogia antes que abstraccion.

## Mejoras que se incorporan en este step 2

Este step 2 si puede explorar e implementar:

- query rewriting;
- reranking;
- multi-query retrieval;
- chunk enrichment por LLM;
- evaluacion sistematica de retrieval;
- comparacion controlada de estrategias de chunking;
- comparacion controlada de embeddings;
- visualizacion de embeddings con t-SNE o tecnicas similares;
- diagnostico grafico de clusters, vecinos y separacion documental;
- mejoras de memoria solo si ayudan al flujo RAG inmediato.

Todavia no hace falta abrir el diseño a muchos vectorstores ni a una arquitectura compleja de memoria.

## Resultado esperado

Al terminar este step 2 deberias poder responder preguntas como estas:

- cuando conviene reescribir la query antes de recuperar;
- cuando el reranking mejora el contexto final;
- cuando un chunk enriquecido con resumen y encabezado recupera mejor que un chunk crudo;
- como cambia retrieval al usar varias consultas derivadas;
- como medir si una mejora realmente ayuda o solo hace el flujo mas complejo.

La experiencia de uso esperada ya no es solo "hacer RAG", sino comparar variantes de RAG sobre una misma base documental.

## Estructura recomendada

La estructura debe crecer poco a poco sobre lo ya implementado en Release 02.

```text
src/llmkit/
|-- rag/
|   |-- __init__.py
|   |-- loaders.py
|   |-- splitters.py
|   |-- embeddings.py
|   |-- vectorstores.py
|   |-- answer.py
|   |-- query_rewrite.py
|   |-- reranking.py
|   |-- enrichment.py
|   `-- evaluation.py
`-- schemas/
    |-- rag_outputs.py
    `-- rag_eval.py

notebooks/
|-- 11_query_rewriting.ipynb
|-- 12_reranking.ipynb
|-- 13_multi_query_retrieval.ipynb
|-- 14_chunk_enrichment.ipynb
|-- 15_retrieval_evaluation.ipynb
|-- 16_rag_strategy_comparison.ipynb
|-- 17_embedding_visualization_tsne.ipynb
`-- 18_embedding_diagnostics.ipynb
```

No todos los modulos tienen que nacer de inmediato. Deben aparecer a medida que un notebook los necesite.

## Query rewriting

La primera mejora a explorar es query rewriting.

La idea es tomar una pregunta del usuario y transformarla en una consulta mas especifica para retrieval. Esto sirve especialmente cuando:

- la pregunta depende de contexto conversacional previo;
- la pregunta es corta o ambigua;
- la formulacion del usuario no usa las palabras que aparecen en los documentos.

En esta etapa, query rewriting debe tratarse como una mejora opcional sobre retrieval simple. El notebook debe comparar:

- retrieval con la pregunta original;
- retrieval con la pregunta reescrita;
- diferencias en chunks recuperados.

La mejora solo merece pasar a `src/llmkit/` si el notebook deja claro cuando ayuda y cuando no.

### Notebook 11: `11_query_rewriting.ipynb`

Debe mostrar:

- pregunta original;
- historial si aplica;
- query reescrita;
- top-k recuperado con la pregunta original;
- top-k recuperado con la query reescrita;
- respuesta final usando ambos caminos para comparar.

## Reranking

La segunda mejora a explorar es reranking.

La idea no es cambiar retrieval inicial, sino reordenar los chunks recuperados antes de construir el contexto final. Esto puede ayudar cuando:

- el chunk correcto aparece, pero demasiado abajo;
- top-k tiene ruido;
- la similitud vectorial sola no basta para ordenar bien.

El reranking debe implementarse de forma visible. El notebook debe mostrar:

- orden original de retrieval;
- orden luego del reranker;
- contexto final antes y despues.

### Notebook 12: `12_reranking.ipynb`

Debe mostrar:

- pregunta;
- retrieval base;
- reranked retrieval;
- comparacion de respuesta con y sin reranking.

## Multi-query retrieval

La tercera mejora es multi-query retrieval.

Aqui el sistema no busca con una sola consulta. Genera varias consultas relacionadas y recupera resultados para cada una. Luego mezcla y deduplica.

Esto ayuda especialmente en preguntas amplias, comparativas o de tipo "spanning", donde la respuesta vive repartida entre varios documentos.

En esta etapa no hace falta un sistema complejo. Basta con:

- generar 2 o 3 variantes de query;
- recuperar para cada una;
- unir resultados;
- quitar duplicados;
- comparar contra retrieval simple.

### Notebook 13: `13_multi_query_retrieval.ipynb`

Debe mostrar:

- pregunta original;
- queries derivadas;
- resultados por cada query;
- merge final;
- respuesta final con retrieval simple vs multi-query.

## Chunk enrichment por LLM

La cuarta mejora es chunk enrichment.

En vez de indexar solo texto crudo, el sistema puede indexar un chunk enriquecido con:

- un encabezado breve;
- un resumen corto;
- y el texto original.

Esto busca mejorar retrieval cuando el contenido importante no aparece de forma obvia en el texto plano.

Esta mejora debe entrar con cuidado porque agrega costo, latencia y mas complejidad al pipeline de ingesta.

La pregunta correcta no es "suena mas avanzado". La pregunta correcta es "recupera mejor en nuestros documentos reales".

### Notebook 14: `14_chunk_enrichment.ipynb`

Debe mostrar:

- chunk crudo;
- chunk enriquecido;
- retrieval con indice crudo;
- retrieval con indice enriquecido;
- comparacion de respuesta final.

## Evaluacion sistematica de retrieval

La quinta mejora es evaluacion sistematica.

En el release base bastaba con inspeccion visual. En este step 2 ya conviene introducir una evaluacion repetible. La leccion importante de `week5/day4` es que la evaluacion no debe quedar al final como detalle menor. Debe convertirse en una etapa explicita del trabajo.

No hace falta una plataforma completa de evaluacion. Basta con un conjunto pequeno de preguntas de prueba con:

- pregunta;
- keywords esperadas o pistas de contenido;
- fuente esperada si aplica;
- categoria.

Sobre eso se pueden medir cosas como:

- keyword coverage;
- MRR;
- nDCG;
- precision cualitativa de retrieval.

Esto no reemplaza la inspeccion visual. La complementa.

### Notebook 15: `15_retrieval_evaluation.ipynb`

Debe mostrar:

- dataset de pruebas;
- evaluacion de retrieval baseline;
- evaluacion de una o dos mejoras;
- comparacion de metricas.

Idealmente este notebook debe usarse como referencia comun antes de sacar conclusiones sobre query rewriting, reranking o chunk enrichment.

## Comparacion de estrategias

Al final de este step 2 debe existir un notebook de cierre que compare las estrategias exploradas.

No se trata de mostrar todas las combinaciones posibles. Se trata de responder con evidencia:

- que estrategia mejora recall;
- cual mejora orden;
- cual agrega mucho costo para poca ganancia;
- cual vale la pena consolidar en el toolkit.

### Notebook 16: `16_rag_strategy_comparison.ipynb`

Debe mostrar al menos:

- baseline top-k;
- query rewriting;
- reranking;
- multi-query retrieval;
- y, si ya existe, chunk enrichment.

Cada comparacion debe incluir:

- retrieval visible;
- respuesta final;
- observacion breve de ventajas y limites.

## Visualizacion y diagnostico de embeddings

Una parte util de este step 2 es mirar el espacio vectorial, no solo sus respuestas.

Cuando el retrieval falla, a veces el problema no esta en el prompt ni en el modelo generativo, sino en como quedaron distribuidos los embeddings. Por eso conviene agregar notebooks de analisis visual.

La idea no es hacer investigacion matematica profunda. La idea es responder preguntas practicas como:

- los chunks del mismo tipo documental quedan cerca entre si;
- las consultas relevantes caen cerca de los chunks esperados;
- ciertos documentos forman clusters utiles o demasiado mezclados;
- cambiar embeddings o chunking cambia de forma visible la geometria del espacio.

La tecnica sugerida para esta etapa es `t-SNE`. Si mas adelante quieres comparar con `UMAP`, puede agregarse como extension, pero no es obligatoria en este step.

### Notebook 17: `17_embedding_visualization_tsne.ipynb`

Debe mostrar:

- seleccion de un subconjunto razonable de chunks;
- generacion o carga de embeddings;
- reduccion de dimension con `t-SNE`;
- scatter plot coloreado por tipo de documento, fuente o carpeta;
- observaciones breves sobre separacion o mezcla de grupos.

El objetivo no es solo "hacer un grafico bonito". El objetivo es inspeccionar si el espacio vectorial parece coherente con la estructura documental.

Tambien conviene incluir, si el notebook sigue siendo legible:

- una version 3D opcional;
- hover con fragmento de texto;
- comparacion entre dos configuraciones pequenas, por ejemplo dos embeddings o dos chunkings.

### Notebook 18: `18_embedding_diagnostics.ipynb`

Debe mostrar:

- una o mas preguntas reales convertidas a embeddings;
- vecinos mas cercanos para cada pregunta;
- visualizacion de la pregunta respecto de chunks cercanos;
- comparacion entre dos configuraciones, por ejemplo dos embeddings o dos chunkings;
- observacion breve de cuando la geometria ayuda a explicar un buen o mal retrieval.

Este notebook debe funcionar como puente entre visualizacion y debugging operativo.

## Orden sugerido de exploracion de notebooks

Aunque la numeracion ya esta definida, el orden conceptual recomendado para trabajarlos es este:

1. `15_retrieval_evaluation.ipynb`
2. `17_embedding_visualization_tsne.ipynb`
3. `18_embedding_diagnostics.ipynb`
4. `11_query_rewriting.ipynb`
5. `12_reranking.ipynb`
6. `13_multi_query_retrieval.ipynb`
7. `14_chunk_enrichment.ipynb`
8. `16_rag_strategy_comparison.ipynb`

La razon es practica:

- primero mides y observas;
- despues mejoras;
- al final comparas.

## Memoria en este step 2

La memoria sigue siendo secundaria.

Solo debe crecer si ayuda directamente a RAG. Ejemplos validos:

- usar historial para reescribir queries;
- usar historial para desambiguar preguntas;
- recuperar decisiones recientes del usuario para formular mejor la respuesta.

No corresponde todavia convertir memoria en un sistema complejo separado del flujo RAG.

## Criterio de termino

Este step 2 esta terminado cuando puedes:

- comparar retrieval simple contra al menos dos mejoras;
- mostrar visualmente que cambia en los chunks recuperados;
- medir al menos una mejora con evaluacion repetible;
- justificar cuales mejoras pasan a ser parte del toolkit y cuales quedan solo como exploracion.

No esta terminado si:

- agregaste muchas tecnicas pero no puedes mostrar cuando ayudan;
- el flujo mejorado se volvio una caja negra;
- los notebooks ya no permiten ver que se recupero y por que;
- o las mejoras se implementaron por adelantado sin un notebook que las necesite.

## Decision de diseno mas importante

La decision central de este step 2 es esta:

las mejoras avanzadas de RAG deben entrar como experimentos comparables, no como arquitectura obligatoria.

El toolkit solo deberia absorber las mejoras que demuestren valor real sobre la base del Release 02.
