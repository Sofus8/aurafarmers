-- C0 autor: BrayFlo Consulta de conteo de filas de la base de datos
SELECT table_name AS tabla,
  (xpath('/row/c/text()',
    query_to_xml(format('SELECT count(*) AS c FROM %I.%I',
      table_schema, table_name), false, true, '')))[1]::text::int AS filas
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY 1;

-- C1 autor: Dogbware ¿A qué hora el paciente x tiene una cita y por cuál médico?
SELECT 
    p.nombre AS nombre_paciente, 
    c.fecha_hora, 
    m.nombre AS nombre_medico
FROM citas c
JOIN pacientes p ON p.id_paciente = c.id_paciente
JOIN medicos m   ON m.id_medico   = c.id_medico
LIMIT 20;

-- C2 autor: BrayFlo ¿Qué paciente tiene menos citas o no tiene?
SELECT 
    p.nombre, 
    p.apellido_paterno, 
    COUNT(c.id_cita) AS total_citas
FROM pacientes p
LEFT JOIN citas c ON c.id_paciente = p.id_paciente
GROUP BY p.id_paciente, p.nombre, p.apellido_paterno
ORDER BY total_citas ASC
LIMIT 20;

-- C3 autor: Sofus8 ¿Qué médicos tuvieron más consultas durante 1 mes?
SELECT 
    m.nombre,
    m.apellido_paterno,
    date_trunc('month', c.fecha_hora) AS mes,
    count(c.id_cita) AS citas_atendidas
FROM citas c
JOIN medicos m ON m.id_medico = c.id_medico
WHERE c.estado = 'Completada'
GROUP BY m.id_medico, m.nombre, m.apellido_paterno, date_trunc('month', c.fecha_hora)
HAVING count(*) >= 1
ORDER BY mes, citas_atendidas DESC;

SELECT * FROM citas

-- C4 autor: Dogbware ¿Cuales son las personas propensas a sobrepeso y problemas cardiacos/metabolicos?
SELECT id_nota, id_expediente, fecha_consulta, peso, talla
FROM notas_consulta
WHERE peso > (SELECT AVG(peso) FROM notas_consulta WHERE peso IS NOT NULL)
ORDER BY peso DESC;

-- C5 autor: BrayFlo ¿Cuántas órdenes de análisis clínicos generó cada nota médica?
SELECT 
    nc.id_nota, 
    nc.fecha_consulta, 
    COUNT(el.id_estudio) AS total_estudios
FROM notas_consulta nc
LEFT JOIN estudios_laboratorio el ON el.id_nota = nc.id_nota
GROUP BY nc.id_nota, nc.fecha_consulta
ORDER BY total_estudios DESC
LIMIT 20;

--C6 autor: Sofus8 ¿Cuantas citas tuvo cada especialidad?
SELECT 
    e.nombre_especialidad AS especialidad,
    count(nc.id_nota) AS total_consultas
FROM especialidades e
JOIN medicos m          ON m.id_especialidad = e.id_especialidad
JOIN notas_consulta nc  ON nc.id_medico = m.id_medico
GROUP BY e.id_especialidad, e.nombre_especialidad
ORDER BY total_consultas DESC;

--C7 autor: BrayFlo ¿Cuantas citas tuvo cada especialidad?
SELECT 
    date_trunc('month', fecha_hora) AS mes,
    count(*) AS total_citas,
    count(*) FILTER (WHERE lower(estado) = 'completada') AS citas_completadas,
    count(*) FILTER (WHERE lower(estado) = 'cancelada') AS citas_canceladas,
    round(
        (count(*) FILTER (WHERE lower(estado) = 'completada')::numeric / count(*)::numeric) * 100, 
        2
    ) AS porcentaje_efectividad
FROM citas
GROUP BY 1
ORDER BY 1;

-- C8 autor:BrayFlo ¿Qué posición o lugar (ranking) ocupa cada médico en cada mes según la cantidad de citas completadas que atendió en el consultorio? 
SELECT 
    m.id_medico,
    m.nombre,
    m.apellido_paterno,
    date_trunc('month', c.fecha_hora) AS mes,
    count(c.id_cita) AS citas_atendidas,
    rank() OVER (
        PARTITION BY date_trunc('month', c.fecha_hora)
        ORDER BY count(c.id_cita) DESC
    ) AS lugar
FROM citas c
JOIN medicos m ON m.id_medico = c.id_medico
WHERE lower(c.estado) = 'completada'
GROUP BY m.id_medico, m.nombre, m.apellido_paterno, date_trunc('month', c.fecha_hora)
ORDER BY mes, lugar;


--Hola, hubo una confusion al haber creado el repositorio, pero ya está corregido y listo tanto en el perfil de bray como el mío
--08 de Octubre de 2026
-- C3 reescrita · autor: BrayFlo
SELECT 
    id_cita,
    id_paciente,
    id_medico,
    fecha_hora,
    estado
FROM citas
WHERE estado = 'Completada'
  AND fecha_hora >= '2026-01-01 00:00:00' 
  AND fecha_hora < '2026-07-01 00:00:00'
ORDER BY fecha_hora DESC;

-- Parte 3.1 · autor: Dogbware
-- Reescritura de filtro por mes para evitar aplicar una función sobre fecha_hora

SELECT *
FROM citas
WHERE fecha_hora >= '2026-10-01'
  AND fecha_hora < '2026-11-01';
