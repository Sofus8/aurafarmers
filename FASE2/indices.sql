--sofus 8 Indice 3
ANALYZE pacientes;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id_paciente, nombre, apellido_paterno, telefono
FROM pacientes
WHERE email IS NULL;

--Sofus8 Indice 4 
CREATE INDEX pacientes_genero_fecha_idx 
ON pacientes (lower(genero), fecha_registro DESC);
ANALYZE pacientes;
--explain
EXPLAIN (ANALYZE, BUFFERS)
SELECT id_paciente, nombre, apellido_paterno, fecha_registro
FROM pacientes
WHERE lower(genero) = 'femenino'
ORDER BY fecha_registro DESC
LIMIT 10;


-- C2 · autor: Dogbware · FK sin índice; se utiliza en el LEFT JOIN
CREATE INDEX citas_id_paciente_idx
ON citas (id_paciente);

-- Parte 3.1 · autor: Dogbware · fecha_hora se utiliza para filtrar por rangos de fechas
CREATE INDEX citas_fecha_hora_idx
ON citas (fecha_hora);
