# Propuesta de Trabajo Final de Máster

**Máster en Ingeniería y Desarrollo de Soluciones de IA Generativa — EBIS Business Techschool**

**Proyecto:** MarketMind AI — Framework de Inteligencia Comercial Basado en IA Generativa para la Identificación de Oportunidades de Mercado utilizando Datos Públicos Globales

**Integrantes:** Álvaro Augusto De Marco Neto · Miguel Antonio Blanco Salcedo
**Fecha:** Junio 2026

---

## 1. Descripción de la propuesta

MarketMind AI es una plataforma de inteligencia comercial basada en Inteligencia Artificial Generativa diseñada para identificar oportunidades de mercado utilizando catálogos de productos y fuentes públicas globales. El sistema permitirá analizar tendencias, comportamiento de consumidores, interés geográfico y factores estacionales para generar recomendaciones comerciales explicables.

Módulos principales:
- Ingestión de catálogos CSV y Excel.
- Adquisición de datos desde fuentes públicas globales.
- Cálculo del Market Opportunity Score (MOS).
- Generación de recomendaciones mediante arquitecturas multiagente y LLMs.

## 2. Motivaciones

Las organizaciones disponen cada vez de más información pública relacionada con tendencias y mercados, pero carecen de herramientas capaces de convertir estos datos en decisiones accionables. Problemas identificados: dificultad para analizar grandes catálogos, fragmentación de fuentes, ausencia de herramientas accesibles de inteligencia comercial, y necesidad de explicabilidad en las recomendaciones generadas por IA.

## 3. Objetivos

**General:** Desarrollar un MVP funcional capaz de analizar productos/catálogos utilizando fuentes públicas globales y generar recomendaciones comerciales explicables mediante IA Generativa.

**Específicos:**
1. Diseñar un sistema de ingestión de catálogos.
2. Implementar conectores para fuentes públicas globales.
3. Enriquecer información de productos y categorías.
4. Diseñar y validar el Market Opportunity Score (MOS).
5. Implementar una arquitectura multiagente.
6. Generar informes explicativos mediante LLMs.
7. Comparar oportunidades entre mercados geográficos.
8. Validar la utilidad de las recomendaciones.
9. Analizar costes, rendimiento y viabilidad técnica.

## 4. Market Opportunity Score (MOS)

Índice propio para evaluar oportunidades comerciales:

```
MOS = 30% Trend + 25% Growth + 20% Geographic Potential + 15% Seasonality + 10% Consumer Interest
```

> **Nota:** la arquitectura actual implementa el MOS de forma configurable y propone una reconciliación a un índice validado de 3 factores. Ver [architecture-plan.md](architecture-plan.md) §7.

## 5. Validación científica

Casos de estudio reales con diferentes categorías de productos; las recomendaciones se comparan con análisis manuales para evaluar relevancia, coherencia, utilidad práctica y calidad de las explicaciones generadas por IA.

## 6. Alcance del MVP

Importar productos/catálogos · obtener datos de fuentes públicas globales · calcular el MOS · identificar mercados con mayor potencial · generar recomendaciones explicables · visualizar resultados en una interfaz web interactiva. La arquitectura queda preparada para futuras integraciones (Meta Ads, Google Ads, Shopify, Amazon SP-API).

---

> Este documento es la propuesta original. El diseño técnico detallado, las decisiones de arquitectura y el roadmap viven en [architecture-plan.md](architecture-plan.md).
