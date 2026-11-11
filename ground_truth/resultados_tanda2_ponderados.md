# Metricas de tanda 2 ponderadas por el diseno muestral

Generado por `ponderar_tanda2.py` v1 (2026-11-10). Correccion C-04 de la
auditoria v5: la muestra de tanda 2 (526 de 1.956) estratifico por la salida
del propio pipeline (estrato A = las 276 phishing/ransomware que predijo el
sistema, inclusion con probabilidad 1; estrato B = 250 de 1.680, probabilidad
0,1488). Las metricas sin ponderar de esa muestra no estiman el desempeno sobre
el lote: se pondera por el inverso de la probabilidad de inclusion
(peso 1 en A, 6,72 en B).

## Control: censo de 639 sin ponderar (reproduccion de la tesis)

- F1 micro categoria: **0.552** | F1 macro: **0.511**
- F1 micro sentimiento: **0.218**
- Exhaustividad phishing: 0.875 | ransomware: 0.892 | vulnerabilidad: 0.579

## Tanda 2 (n = 526) sin ponderar / ponderada por diseno

- Estratos en la muestra: A = 276 (esperado 276), B = 250 (esperado 250)

| Metrica | Sin ponderar | Ponderada (IC 95 % bootstrap) |
|---|---|---|
| F1 micro categoria | 0.570 | **0.589** [0.536; 0.643] |
| F1 macro categoria | 0.518 | **0.518** [0.476; 0.560] |
| F1 micro sentimiento | 0.215 | **0.216** [0.172; 0.261] |
| Exhaustividad phishing | 0.878 | **0.516** [0.414; 0.650] |
| Exhaustividad ransomware | 0.879 | **0.749** [0.509; 0.971] |
| Exhaustividad vulnerabilidad | 0.677 | **0.714** [0.600; 0.826] |

Intervalos: bootstrap estratificado al 95 % (2000 remuestreos dentro de cada estrato, semilla 42).

## Totales poblacionales estimados por clase (lote de 1.956)

| Clase (consenso) | Casos en la muestra | Total estimado en el lote |
|---|---|---|
| no_clasificado | 117 | 609 |
| vulnerabilidad | 65 | 414 |
| malware | 91 | 457 |
| phishing | 139 | 236 |
| ransomware | 33 | 39 |
| otro | 81 | 201 |
| **Total** | **526** | **1956** |

## Nota metodologica

El estrato A incluye con probabilidad 1 todo lo que el propio sistema predijo
como phishing o ransomware; por eso la exhaustividad sin ponderar de esas
clases en la muestra (condicionada al diseno) no es la del lote. La ponderacion
por el inverso de la probabilidad de inclusion corrige ese sesgo: la
exhaustividad de phishing pasa de sobrestimada a su estimacion poblacional.
El conjunto de 639 NO es un censo del corpus ampliado: es el censo del corpus
analizado (113) mas una muestra estratificada de un lote distinto.
