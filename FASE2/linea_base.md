Consulta Execution Time (ms), tiempo de en medio ¿Aparece Seq Scan? ¿Sobre qué tabla? Qué columna creen que convendría indexar y por qué C7: Tendencia mensual de citas (citas con date_trunc y conteo) (Ejemplo típico en 10k filas: 12.4 ms — anota el tuyo) Sí, aparece Seq Scan on citas. Convendría indexar la columna fecha_hora (o una expresión indexada date_trunc('month', fecha_hora)), porque la consulta realiza un escaneo secuencial completo de toda la tabla para agrupar y ordenar cronológicamente las 10 000 filas. C8: Citas completadas por médico y mes (citas + medicos) (Ejemplo típico en 10k filas: 18.7 ms — anota el tuyo) Sí, aparece Seq Scan on citas (y posiblemente Seq Scan on medicos). Convendría indexar la columna estado (o un índice compuesto (estado, fecha_hora)), ya que el motor tiene que leer todas las filas de la tabla para aplicar el filtro WHERE lower(estado) = 'completada' antes de realizar el agrupamiento.

--Consulta7 by aless--
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    date_trunc('month', fecha_hora) AS mes,
    count(*) AS total_citas,
    count(*) FILTER (
        WHERE lower(estado) = 'completada'
    ) AS citas_completadas,
    count(*) FILTER (
        WHERE lower(estado) = 'cancelada'
    ) AS citas_canceladas,
    round(
        (
            count(*) FILTER (
                WHERE lower(estado) = 'completada'
            )::numeric
            / count(*)::numeric
        ) * 100,
        2
    ) AS porcentaje_efectividad
FROM citas
GROUP BY 1
ORDER BY 1;


--Consulta3 by sofus--
ANALYZE pacientes;


EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    date_trunc('month', fecha_registro) AS mes,
    count(*) AS total_pacientes,
    count(*) FILTER (WHERE lower(genero) = 'masculino') AS total_hombres,
    count(*) FILTER (WHERE lower(genero) = 'femenino') AS total_mujeres,
    round(
        (count(*) FILTER (WHERE lower(genero) = 'femenino')::numeric / count(*)::numeric) * 100, 
        2
    ) AS porcentaje_mujeres
FROM pacientes
GROUP BY 1
ORDER BY 1;
